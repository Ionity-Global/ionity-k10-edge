"""Sensor telemetry store + simple alerting. © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0"""
from __future__ import annotations
import time
from collections import deque, defaultdict


class Telemetry:
    def __init__(self, history: int = 300) -> None:
        self.latest: dict[str, dict] = {}
        self.history: dict[str, deque] = defaultdict(lambda: deque(maxlen=history))
        self.location: dict[str, dict] = {}
        self.state: dict[str, dict] = {}   # server-computed orb render per device

    def ingest(self, device_id: str, reading: dict) -> None:
        reading = {**reading, "_ts": time.time()}
        self.latest[device_id] = reading
        self.history[device_id].append(reading)

    def set_location(self, device_id: str, loc: dict) -> None:
        self.location[device_id] = loc

    def set_state(self, device_id: str, state: dict) -> None:
        self.state[device_id] = state

    def get(self, device_id: str) -> dict:
        return {
            "latest": self.latest.get(device_id, {}),
            "location": self.location.get(device_id, {}),
            "state": self.state.get(device_id, {}),
            "samples": len(self.history.get(device_id, [])),
        }

    def check_alerts(self, device_id: str, reading: dict) -> dict | None:
        t = reading.get("temp_c")
        if isinstance(t, (int, float)) and t >= 45:
            return {"title": "High temperature", "body": f"{t:.1f}°C on {device_id}",
                    "level": "warn", "kind": "notify"}
        return None
