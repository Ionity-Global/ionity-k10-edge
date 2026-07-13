"""WiFi geolocation — resolve a BSSID/RSSI scan to coordinates.

Fully local by default: looks up BSSIDs in an optional local database
(data/bssid_db.json: {bssid: [lat, lon]}). If none match, returns an RSSI-weighted
'unknown' result rather than calling any cloud service (LOCAL SAVED, no API).
Plug a provider in resolve() if you want online positioning.
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
"""
from __future__ import annotations
import json
from pathlib import Path

from app.config import settings


class Geolocator:
    def __init__(self) -> None:
        self.db: dict[str, list[float]] = {}
        p = Path(settings.data_dir) / "bssid_db.json"
        if p.exists():
            try:
                self.db = json.loads(p.read_text())
            except Exception:
                self.db = {}

    def resolve(self, aps: list[dict]) -> dict:
        pts, weights = [], []
        for ap in aps:
            b = (ap.get("bssid") or "").upper()
            if b in self.db:
                lat, lon = self.db[b]
                # RSSI -> weight (closer AP = stronger signal = higher weight)
                w = max(1, 100 + int(ap.get("rssi", -80)))
                pts.append((lat, lon)); weights.append(w)
        if pts:
            tw = sum(weights)
            lat = sum(p[0] * w for p, w in zip(pts, weights)) / tw
            lon = sum(p[1] * w for p, w in zip(pts, weights)) / tw
            return {"lat": round(lat, 6), "lon": round(lon, 6),
                    "method": "wifi-local-db", "matched": len(pts)}
        return {"lat": None, "lon": None, "method": "unknown",
                "seen": len(aps), "note": "no BSSID match in local DB"}
