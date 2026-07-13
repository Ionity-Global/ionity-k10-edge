"""Opt-in, brand-safe on-device notices / ads.

No third-party tracking, no external calls. Slots are local, rotate fairly, and
respect a 'sensitive' context flag (never target on sensitive content).
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0"""
from __future__ import annotations
import json
import time
from pathlib import Path

from app.config import settings

_DEFAULT_SLOTS = [
    {"id": "ionity-1", "title": "IonityEdge", "body": "Building Tomorrow, Today — ionity.today",
     "tags": ["ionity", "brand"]},
    {"id": "aedi-1", "title": "True Edge AI", "body": "AEDI turns small devices into big minds.",
     "tags": ["edge", "ai"]},
    {"id": "shop-1", "title": "Ionity Earth", "body": "Explore the ecosystem — ionity.co.za",
     "tags": ["shop"]},
]


class AdEngine:
    def __init__(self) -> None:
        self.enabled = settings.feat_ads
        self._i = 0
        p = Path(settings.data_dir) / "ads.json"
        if p.exists():
            try:
                self.slots = json.loads(p.read_text())
            except Exception:
                self.slots = list(_DEFAULT_SLOTS)
        else:
            self.slots = list(_DEFAULT_SLOTS)

    def next(self, context: dict | None = None) -> dict | None:
        if not self.enabled or not self.slots:
            return None
        if context and context.get("sensitive"):
            return None                      # never advertise on sensitive content
        slot = self.slots[self._i % len(self.slots)]
        self._i += 1
        return {**slot, "ts": int(time.time()), "kind": "ad"}
