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
        self.state = "idle"
        self.level = 0.0          # live audio envelope 0..1 (mic while listening, TTS while speaking)
        self.tone = "neutral"
        self.last_user = ""
        self.last_reply = ""
        self.last_audio: str | None = None   # path to the last TTS wav (if any)
        self.last_ts = time.time()
        self.transcript: list[dict] = []      # [{role, text, ts}]
        self._lock = threading.Lock()

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

    def snapshot(self) -> dict:
        return {
            "state": self.state, "tone": self.tone, "color": self.color(),
            "level": round(self.level, 3), "name": settings.assistant_name,
            "user": self.last_user, "reply": self.last_reply,
            "audio": ("/api/say.wav" if self.last_audio else None),
            "ts": self.last_ts, "transcript": self.transcript[-14:],
        }

    def _tone_of(self, reply: str) -> str:
        lab = self.mood.infer_text(reply).get("mood", "neutral")
        low = reply.lower()
        if any(w in low for w in ("emergency", "warning", "urgent", "danger", "immediately")):
            return "urgent"
        return {"positive": "positive", "negative": "negative", "neutral": "neutral"}.get(lab, "neutral")

    def _speak(self, text: str) -> None:
        """Best-effort server-side TTS -> wav on disk (played by the device / dashboard)."""
        self.last_audio = None
        if not text or not self.orc.tts.available:
            return
        out = str(Path(settings.data_dir) / "say.wav")
        try:
            if self.orc.speak(text, out) and Path(out).exists():
                self.last_audio = out
        except Exception:
            self.last_audio = None

    # ---- a full conversation turn ----
    def handle_text(self, text: str) -> dict:
        text = (text or "").strip()
        if not text:
            self.set_state("idle")
            return {"ok": False, "note": "empty"}
        with self._lock:
            self.last_user = text
            self.transcript.append({"role": "user", "text": text, "ts": time.time()})
            self.set_state("thinking")
            res = self.orc.ask(text)
            reply = (res.get("text") or "").strip() or "…"
            self.last_reply = reply
            self.tone = self._tone_of(reply)
            self.transcript.append({"role": "assistant", "text": reply, "ts": time.time()})
            self._speak(reply)
            self.set_state("speaking")
            return {"ok": True, "user": text, "reply": reply, "tone": self.tone,
                    "state": "speaking", "source": res.get("source"),
                    "audio": ("/api/say.wav" if self.last_audio else None)}

    def handle_wav(self, wav_path: str) -> dict:
        """Turn from an uploaded/streamed utterance: STT -> handle_text."""
        self.set_state("listening")
        if not self.orc.stt.available:
            self.set_state("idle")
            return {"ok": False, "note": "STT not installed (pip install faster-whisper)"}
        try:
            tr = self.orc.stt.transcribe(wav_path)
        except Exception as e:
            self.set_state("idle")
            return {"ok": False, "note": f"STT error: {e}"}
        text = (tr.get("text") or "").strip()
        # optional wake-word gate for always-on streaming (dashboard push-to-talk bypasses)
        out = self.handle_text(text) if text else {"ok": False, "note": "no speech"}
        out["transcript"] = text
        out["lang"] = tr.get("lang")
        return out

    def heard_wake(self, text: str) -> bool:
        return settings.wake_word.lower() in (text or "").lower()

    def tick(self) -> None:
        """Relax state over time: speaking/thinking -> idle -> sleeping."""
        dt = time.time() - self.last_ts
        if self.state in ("listening", "thinking", "speaking") and dt > 3.0:
            self.state = "idle"
        elif self.state == "idle" and dt > settings.idle_sleep_s:
            self.state = "sleeping"
