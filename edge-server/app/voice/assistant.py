"""Voice home-assistant state machine + conversation turn.

The AI STATE (sleeping|idle|listening|thinking|speaking) and the reply TONE drive the
orb colour that the server renders and streams to the K10 (and the dashboard). This is the
"lights change to the tone of the AI and the AI indication" behaviour.

Turn: mic audio (streamed from the node / uploaded from the dashboard) -> STT -> brain
(Claude web-bridge, else gemma4:e2b) -> reply -> TTS + tone. All compute on the EDGE (server).
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
"""
from __future__ import annotations
import threading
import time
from pathlib import Path

from app.config import settings
from app.voice import tts_sapi

STATES = ("sleeping", "idle", "listening", "thinking", "speaking")

# AI-state indication colours (RRGGBB, no '#').
STATE_COLORS = {
    "sleeping":  "0A1E38",   # deep dim blue
    "idle":      "0E5A86",   # calm teal
    "listening": "00D2FF",   # bright cyan — I'm hearing you
    "thinking":  "B06CF0",   # violet — processing
    "speaking":  "26DE81",   # green — talking (overridden by reply tone below)
}
# Reply-tone colours (sentiment of what the AI says).
TONE_COLORS = {
    "calm":     "1E7BFF",
    "neutral":  "00D2FF",
    "positive": "26DE81",
    "negative": "E23B4E",
    "urgent":   "FF3B30",
}


class Assistant:
    def __init__(self, orchestrator, mood) -> None:
        self.orc = orchestrator
        self.mood = mood
        self.telemetry = None            # wired by main.py — enables instant sensor answers
        try:
            from app.home.controller import HomeController
            self.home = HomeController()
        except Exception:
            self.home = None
        self.state = "idle"
        self.level = 0.0          # live audio envelope 0..1 (mic while listening, TTS while speaking)
        self.tone = "neutral"
        self.last_user = ""
        self.last_reply = ""
        self.last_audio: str | None = None   # path to the last TTS wav (if any)
        self.audio_seq = 0                     # bumped whenever new TTS audio is ready (device polls this)
        self.last_ts = time.time()
        self.awake_until = 0.0                 # stays awake for follow-ups after a wake/interaction
        self.transcript: list[dict] = []      # [{role, text, ts}]
        self._lock = threading.Lock()

    def _sensor_answer(self, text: str) -> str | None:
        """Answer sensor questions INSTANTLY from live telemetry (no LLM round-trip)."""
        if self.telemetry is None:
            return None
        low = text.lower()
        # require a real question about the environment (avoid "warm hello" false positives)
        is_q = any(w in low for w in ("what", "how", "is it", "'s the", "tell me", "?"))
        want_t = any(w in low for w in ("temperature", "temp ", "degrees", "how hot", "how cold", "how warm"))
        want_h = "humid" in low
        want_l = ("light level" in low) or ("how bright" in low) or ("how dark" in low)
        if not (is_q and (want_t or want_h or want_l)):
            return None
        try:
            devs = list(self.telemetry.latest.keys())
            l = self.telemetry.latest.get("ionity-k10") or (self.telemetry.latest.get(devs[0]) if devs else {})
        except Exception:
            return None
        if not l:
            return None
        parts = []
        if want_t and l.get("temp_c") is not None:
            parts.append(f"it's {float(l['temp_c']):.1f} degrees")
        if want_h and l.get("humidity") is not None:
            parts.append(f"humidity is {float(l['humidity']):.0f} percent")
        if want_l and l.get("light") is not None:
            parts.append(f"light level is {int(l['light'])}")
        return ("Right now " + " and ".join(parts) + ".") if parts else None

    # ---- state helpers ----
    def set_state(self, s: str) -> None:
        if s in STATES:
            self.state = s
            self.last_ts = time.time()

    def set_level(self, lvl) -> None:
        try:
            self.level = max(0.0, min(1.0, float(lvl)))
        except Exception:
            pass

    def color(self) -> str:
        if self.state == "speaking":
            return TONE_COLORS.get(self.tone, STATE_COLORS["speaking"])
        return STATE_COLORS.get(self.state, "00D2FF")

    def awake(self) -> bool:
        return time.time() < self.awake_until

    def snapshot(self) -> dict:
        return {
            "state": self.state, "tone": self.tone, "color": self.color(),
            "level": round(self.level, 3), "name": settings.assistant_name,
            "user": self.last_user, "reply": self.last_reply,
            "audio": ("/api/say.wav" if self.last_audio else None),
            "audio_seq": self.audio_seq, "awake": self.awake(),
            "screen_on": self.awake() or self.state in ("listening", "thinking", "speaking"),
            "ts": self.last_ts, "transcript": self.transcript[-14:],
        }

    def _tone_of(self, reply: str) -> str:
        lab = self.mood.infer_text(reply).get("mood", "neutral")
        low = reply.lower()
        if any(w in low for w in ("emergency", "warning", "urgent", "danger", "immediately")):
            return "urgent"
        return {"positive": "positive", "negative": "negative", "neutral": "neutral"}.get(lab, "neutral")

    def _speak(self, text: str) -> None:
        """Server-side TTS -> 16 kHz mono wav on disk. Piper if configured, else Windows SAPI.
        The device fetches /api/say.wav and plays it through the ESP speaker.
        Spoken text is clipped short — she answers, she doesn't lecture (and [B] stops her)."""
        self.last_audio = None
        if not text:
            return
        if len(text) > 260:
            cut = text[:260]
            text = cut[: cut.rfind(".") + 1] if "." in cut[80:] else cut + "…"
        out = str(Path(settings.data_dir) / "say.wav")
        p = None
        try:
            if self.orc.tts.available:
                p = self.orc.speak(text, out)
            if not p:
                p = tts_sapi.synth(text, out)   # real voice on Windows, no install
        except Exception:
            p = None
        if p and Path(p).exists():
            self.last_audio = out
            self.audio_seq += 1

    # ---- a full conversation turn ----
    def handle_text(self, text: str) -> dict:
        text = (text or "").strip()
        if not text:
            self.set_state("idle")
            return {"ok": False, "note": "empty"}
        with self._lock:
            self.awake_until = time.time() + 15
            self.last_user = text
            self.transcript.append({"role": "user", "text": text, "ts": time.time()})
            self.set_state("thinking")
            # 1) learning: "Peper, remember <fact>" -> stored in the profile, used in every prompt
            source = "memory"
            reply = ""
            try:
                from app.brain import persona as _p
                ack = _p.maybe_remember(text)
                if ack:
                    reply = ack
            except Exception:
                pass
            # 2) live sensor question -> INSTANT answer from telemetry (no LLM)
            if not reply:
                sa = self._sensor_answer(text)
                if sa:
                    source = "sensors"; reply = sa
            # 3) smart-home intent (lights/media/scenes/MQTT) — act locally before the LLM
            if not reply and self.home is not None:
                source = "home"
                act = self.home.parse_and_act(text)
                if act.get("handled"):
                    reply = act.get("spoken", "")
            # 3) otherwise ask the brain (Claude bridge -> gemma4:e2b, Ionity persona attached)
            if not reply:
                res = self.orc.ask(text)
                reply = (res.get("text") or "").strip() or "…"
                source = res.get("source")
            self.last_reply = reply
            self.tone = self._tone_of(reply)
            self.transcript.append({"role": "assistant", "text": reply, "ts": time.time()})
            self._speak(reply)
            self.set_state("speaking")
            return {"ok": True, "user": text, "reply": reply, "tone": self.tone,
                    "state": "speaking", "source": source,
                    "audio": ("/api/say.wav" if self.last_audio else None)}

    def handle_wav(self, wav_path: str, gate: bool = True) -> dict:
        """Turn from a streamed utterance: STT -> wake-word gate -> brain.

        Continuous listening: the device streams audio; the SERVER detects the wake word
        ("hello") on the edge. Ambient speech is ignored until woken; once woken we stay
        awake ~15 s for follow-ups. `gate=False` bypasses the wake gate (dashboard push-to-talk)."""
        if not self.orc.stt.available:
            self.set_state("idle")
            return {"ok": False, "note": "STT not installed (pip install faster-whisper)"}
        try:
            tr = self.orc.stt.transcribe(wav_path)
        except Exception as e:
            self.set_state("idle")
            return {"ok": False, "note": f"STT error: {e}"}
        text = (tr.get("text") or "").strip()
        if not text:
            return {"ok": False, "note": "no speech", "transcript": ""}

        # ECHO SUPPRESSION: the device mic hears its own speaker. If the transcript looks like
        # what we just said (within ~14 s of speaking), drop it — otherwise the assistant
        # answers itself in an infinite loop.
        def _norm(s): return "".join(c for c in s.lower() if c.isalnum() or c == " ").split()
        if self.last_reply and (time.time() - self.last_ts) < 14:
            a, b = set(_norm(text)), set(_norm(self.last_reply))
            if a and b and (len(a & b) / max(1, len(a))) > 0.6:
                return {"ok": False, "ignored": True, "echo": True, "transcript": text}

        low = text.lower()
        # Custom wake words (Settings -> wake_words CSV, e.g. "hi pepper"), longest match first
        # so "hi pepper" wins over "pepper". Learnable: accepted clips are archived for training.
        variants = [w.strip().lower() for w in
                    (settings.wake_words or settings.wake_word).split(",") if w.strip()]
        variants = sorted(set(variants + [settings.wake_word.lower()]), key=len, reverse=True)
        wake, widx, wlen = False, -1, 0
        for v in variants:
            j = low.find(v)
            if j >= 0:
                wake, widx, wlen = True, j, len(v); break
        if gate and not self.awake() and not wake:
            return {"ok": False, "ignored": True, "transcript": text}   # not addressed — stay dim

        self.set_state("listening")
        self.awake_until = time.time() + 15
        cmd = text
        if wake:
            cmd = text[widx + wlen:].strip(" ,.!?:;-")
            # voice learning: archive the accepted wake clip (data/voice_samples) so the
            # wake model can be trained/tuned on YOUR voice over time
            try:
                import shutil
                vs = Path(settings.data_dir) / "voice_samples"
                vs.mkdir(exist_ok=True)
                shutil.copy(wav_path, vs / f"wake_{int(time.time())}.wav")
                olds = sorted(vs.glob("wake_*.wav"))
                for f in olds[:-50]:
                    f.unlink()                       # keep the newest 50 samples
            except Exception:
                pass
        if not cmd:
            # bare wake word -> acknowledge, screen wakes
            with self._lock:
                self.last_user = text
                self.transcript.append({"role": "user", "text": text, "ts": time.time()})
                self.last_reply = "Yes?"; self.tone = "positive"
                self.transcript.append({"role": "assistant", "text": "Yes?", "ts": time.time()})
                self._speak("Yes?"); self.set_state("speaking")
            return {"ok": True, "woke": True, "reply": "Yes?", "transcript": text}
        out = self.handle_text(cmd)
        out["transcript"] = text; out["woke"] = wake; out["lang"] = tr.get("lang")
        return out

    def tick(self) -> None:
        """Relax state over time: speaking/thinking -> idle -> sleeping."""
        dt = time.time() - self.last_ts
        if self.state in ("listening", "thinking", "speaking") and dt > 3.0:
            self.state = "idle"
        elif self.state == "idle" and dt > settings.idle_sleep_s:
            self.state = "sleeping"
