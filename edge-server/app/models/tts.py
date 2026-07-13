"""Text-to-speech (Piper). Falls back to writing a marker if not installed.
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0"""
from __future__ import annotations
from pathlib import Path

try:
    from piper import PiperVoice  # type: ignore
    _HAVE = True
except Exception:
    _HAVE = False


class TTS:
    def __init__(self, voice_path: str | None = None) -> None:
        self.voice = None
        if _HAVE and voice_path and Path(voice_path).exists():
            try:
                self.voice = PiperVoice.load(voice_path)
            except Exception:
                self.voice = None

    @property
    def available(self) -> bool:
        return self.voice is not None

    def synth(self, text: str, out_wav: str) -> str | None:
        if not self.available:
            return None
        with open(out_wav, "wb") as f:
            self.voice.synthesize(text, f)
        return out_wav
