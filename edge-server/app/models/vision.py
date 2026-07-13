"""Vision — face/object/QR detection via OpenCV. Stub if not installed.
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0"""
from __future__ import annotations

try:
    import cv2  # type: ignore
    _HAVE = True
except Exception:
    _HAVE = False


class Vision:
    def __init__(self) -> None:
        self.face = None
        self.qr = None
        if _HAVE:
            try:
                self.face = cv2.CascadeClassifier(
                    cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
                self.qr = cv2.QRCodeDetector()
            except Exception:
                pass

    @property
    def available(self) -> bool:
        return _HAVE

    def analyze(self, image_path: str) -> dict:
        if not _HAVE:
            return {"faces": 0, "qr": None, "note": "OpenCV not installed"}
        img = cv2.imread(image_path)
        if img is None:
            return {"faces": 0, "qr": None, "note": "unreadable frame"}
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = self.face.detectMultiScale(gray, 1.1, 4) if self.face is not None else []
        qr_data = None
        if self.qr is not None:
            data, _, _ = self.qr.detectAndDecode(img)
            qr_data = data or None
        return {"faces": int(len(faces)), "qr": qr_data}
        # TODO: plug a YOLO/TinyML object model for richer labels.
