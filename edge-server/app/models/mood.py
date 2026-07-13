"""Mood / emotion — lightweight lexical text + real prosody-from-audio heuristic.
A heavier model (e.g. wav2vec2 SER) can drop into infer_audio() later.
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0"""
from __future__ import annotations
import wave
import struct
import math

_POS = {"good", "great", "love", "happy", "thanks", "awesome", "yes", "nice", "cool"}
_NEG = {"bad", "hate", "angry", "sad", "no", "annoyed", "broken", "wrong", "terrible"}


class Mood:
    available = True  # heuristic always available; upgradeable

    def infer_text(self, text: str) -> dict:
        toks = set(text.lower().split())
        pos, neg = len(toks & _POS), len(toks & _NEG)
        if pos == neg == 0:
            label, score = "neutral", 0.5
        elif pos >= neg:
            label, score = "positive", min(1.0, 0.5 + 0.1 * (pos - neg))
        else:
            label, score = "negative", min(1.0, 0.5 + 0.1 * (neg - pos))
        return {"mood": label, "score": round(score, 2), "backend": "lexical"}

    def infer_audio(self, wav_path: str) -> dict:
        """Real prosody heuristic from the utterance itself: loud + sustained energy
        with high variability reads as agitated/negative; quiet + steady reads as calm.
        Pure stdlib (wave/struct) — no model download. Upgradeable to a SER model."""
        try:
            with wave.open(wav_path, "rb") as w:
                n = w.getnframes()
                sw = w.getsampwidth()
                ch = w.getnchannels() or 1
                raw = w.readframes(n)
            if sw != 2 or not raw:
                return {"mood": "neutral", "score": 0.5, "backend": "audio-nrg", "note": "unsupported/empty"}
            count = len(raw) // 2
            samples = struct.unpack("<%dh" % count, raw[: count * 2])
            if ch > 1:
                samples = samples[::ch]  # take first channel
            if not samples:
                return {"mood": "neutral", "score": 0.5, "backend": "audio-nrg"}
            # windowed RMS -> normalized energy + how much it fluctuates (agitation cue)
            win = max(1, len(samples) // 40)
            rms = []
            for i in range(0, len(samples), win):
                chunk = samples[i:i + win]
                if chunk:
                    rms.append(math.sqrt(sum(s * s for s in chunk) / len(chunk)))
            if not rms:
                return {"mood": "neutral", "score": 0.5, "backend": "audio-nrg"}
            mean = sum(rms) / len(rms)
            var = sum((r - mean) ** 2 for r in rms) / len(rms)
            energy = min(1.0, mean / 8000.0)                 # 0..1 loudness
            flux = min(1.0, math.sqrt(var) / 4000.0)         # 0..1 variability
            agit = max(0.0, min(1.0, 0.6 * energy + 0.4 * flux))
            if agit >= 0.6:
                label, score = "negative", round(0.5 + 0.5 * (agit - 0.6) / 0.4, 2)
            elif agit <= 0.25:
                label, score = "calm", round(0.5 + 0.4 * (0.25 - agit) / 0.25, 2)
            else:
                label, score = "neutral", 0.5
            return {"mood": label, "score": score, "backend": "audio-nrg",
                    "energy": round(energy, 3), "flux": round(flux, 3)}
        except Exception as e:
            return {"mood": "neutral", "score": 0.5, "backend": "audio-nrg", "note": str(e)}
