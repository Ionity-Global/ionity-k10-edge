"""Speech-to-text (faster-whisper). Falls back to a stub if not installed.
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0"""
from __future__ import annotations

try:
    from faster_whisper import WhisperModel  # type: ignore
    _HAVE = True
except Exception:
    _HAVE = False


class STT:
    def __init__(self, model_size: str = "base") -> None:
        self.model = None
        if _HAVE:
            # Prefer CPU int8 — robust everywhere (GPU path needs CUDA cuBLAS DLLs that
            # aren't always present on Windows and crash at encode time).
            for dev, ct in (("cpu", "int8"), ("auto", "int8")):
                try:
                    self.model = WhisperModel(model_size, device=dev, compute_type=ct)
                    break
                except Exception:
                    self.model = None

    @property
    def available(self) -> bool:
        return self.model is not None

    def transcribe(self, wav_path: str) -> dict:
        if not self.available:
            return {"text": "", "lang": None, "note": "STT model not installed"}
        segments, info = self.model.transcribe(wav_path, vad_filter=True)
        text = " ".join(s.text.strip() for s in segments).strip()
        return {"text": text, "lang": info.language, "confidence": info.language_probability}
