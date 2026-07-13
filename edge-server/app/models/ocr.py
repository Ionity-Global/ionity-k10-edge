"""OCR — PaddleOCR preferred, pytesseract fallback, then stub.
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0"""
from __future__ import annotations

_BACKEND = None
try:
    from paddleocr import PaddleOCR  # type: ignore
    _BACKEND = "paddle"
except Exception:
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
        _BACKEND = "tesseract"
    except Exception:
        _BACKEND = None


class OCR:
    def __init__(self) -> None:
        self.engine = None
        if _BACKEND == "paddle":
            try:
                self.engine = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
            except Exception:
                self.engine = None

    @property
    def available(self) -> bool:
        return _BACKEND is not None and (self.engine is not None or _BACKEND == "tesseract")

    def read(self, image_path: str) -> dict:
        if _BACKEND == "paddle" and self.engine is not None:
            res = self.engine.ocr(image_path, cls=True)
            lines = [ln[1][0] for page in res for ln in page] if res else []
            return {"text": "\n".join(lines), "backend": "paddle"}
        if _BACKEND == "tesseract":
            import pytesseract
            from PIL import Image
            return {"text": pytesseract.image_to_string(Image.open(image_path)), "backend": "tesseract"}
        return {"text": "", "backend": None, "note": "OCR backend not installed"}
