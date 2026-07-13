"""Recording store — persists camera/screen/audio streams per device session.
Artefacts are stamped with AEDI provenance and indexed for the installer.
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0"""
from __future__ import annotations
import json
import time
from pathlib import Path

from app.config import settings
from app.meta import provenance


class Recorder:
    def __init__(self) -> None:
        self.root = Path(settings.recordings_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.sessions: dict[str, dict] = {}   # device_id -> {dir, files}

    def _session(self, device_id: str) -> dict:
        s = self.sessions.get(device_id)
        if not s:
            d = self.root / f"{device_id}_{int(time.time())}"
            d.mkdir(parents=True, exist_ok=True)
            s = {"dir": d, "files": {}, "started": time.time()}
            self.sessions[device_id] = s
        return s

    def write_frame(self, device_id: str, kind: str, data: bytes) -> None:
        s = self._session(device_id)
        ext = {"cam": "mjpeg", "screen": "mjpeg", "audio": "pcm"}.get(kind, "bin")
        f = s["files"].get(kind)
        if f is None:
            f = open(s["dir"] / f"{kind}.{ext}", "ab")
            s["files"][kind] = f
        f.write(data)

    def stop(self, device_id: str) -> dict | None:
        s = self.sessions.pop(device_id, None)
        if not s:
            return None
        for f in s["files"].values():
            try:
                f.close()
            except Exception:
                pass
        manifest = {
            "device_id": device_id,
            "dir": str(s["dir"]),
            "kinds": list(s["files"].keys()),
            "duration_s": round(time.time() - s["started"], 1),
        }
        manifest["provenance"] = provenance.stamp("recording", manifest)
        (s["dir"] / "manifest.json").write_text(json.dumps(manifest, indent=2))
        return manifest

    def list(self) -> list[dict]:
        out = []
        for d in sorted(self.root.glob("*"), reverse=True):
            m = d / "manifest.json"
            if m.exists():
                try:
                    out.append(json.loads(m.read_text()))
                except Exception:
                    pass
        return out
