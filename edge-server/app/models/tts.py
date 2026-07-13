"""Text-to-speech (Piper) — fluent, natural local voice. 16 kHz mono WAV (plays on the
K10 speaker as-is). Auto-discovers a voice under models/piper/ if no path is configured.
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0"""
from __future__ import annotations
import wave
from pathlib import Path

try:
    from piper import PiperVoice  # piper-tts >= 1.4
    _HAVE = True
except Exception:
    _HAVE = False

from app.config import settings


def _discover_voice(explicit: str | None) -> str | None:
    if explicit and Path(explicit).exists():
        return explicit
    for d in (Path(settings.models_dir) / "piper", Path(settings.models_dir)):
        if d.exists():
            onnx = sorted(d.glob("*.onnx"))
            if onnx:
                return str(onnx[0])
    return None


class TTS:
    def __init__(self, voice_path: str | None = None) -> None:
        self.voice = None
        self.voice_path = _discover_voice(voice_path)
        if _HAVE and self.voice_path:
            try:
                self.voice = PiperVoice.load(self.voice_path)
            except Exception:
                self.voice = None

    @property
    def available(self) -> bool:
        return self.voice is not None

    def synth(self, text: str, out_wav: str) -> str | None:
        if not self.available or not text.strip():
            return None
        try:
            with wave.open(out_wav, "wb") as wf:
                self.voice.synthesize_wav(text, wf)   # Piper writes 16-bit mono (often 22050 Hz)
            _resample_16k_mono(out_wav)               # the K10 speaker runs at 16 kHz
            return out_wav if Path(out_wav).exists() and Path(out_wav).stat().st_size > 44 else None
        except Exception:
            return None


def _resample_16k_mono(path: str) -> None:
    """Rewrite a WAV to 16 kHz / mono / 16-bit so it plays correctly on the K10 I2S."""
    try:
        with wave.open(path, "rb") as w:
            sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
            raw = w.readframes(n)
        if sr == 16000 and ch == 1:
            return
        import numpy as np
        a = np.frombuffer(raw, dtype=np.int16)
        if ch > 1:
            a = a[::ch]
        if sr != 16000 and len(a):
            newn = int(len(a) * 16000 / sr)
            a = np.interp(np.linspace(0, len(a) - 1, newn), np.arange(len(a)), a).astype(np.int16)
        with wave.open(path, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(a.tobytes())
    except Exception:
        pass
