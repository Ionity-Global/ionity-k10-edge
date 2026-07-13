"""Persistent data store (SQLite, stdlib) — telemetry + event history that survives restarts.

- telemetry: one row per device per ~5 s (ts, device, temp_c, humidity, light, level)
- events:    chat turns, vision results, home commands (ts, kind, text)
Read back via GET /api/history for the dashboard sparkline and the MCP get_history tool.
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
"""
from __future__ import annotations
import sqlite3
import threading
import time
from pathlib import Path

from app.config import settings

_DB = Path(settings.data_dir) / "ionity.db"
_lock = threading.Lock()
_last_write: dict[str, float] = {}


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_DB, timeout=5)
    c.execute("""CREATE TABLE IF NOT EXISTS telemetry(
        ts REAL, device TEXT, temp_c REAL, humidity REAL, light REAL, level REAL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS events(ts REAL, kind TEXT, text TEXT)""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_tel_ts ON telemetry(ts)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_evt_ts ON events(ts)")
    return c


def add_telemetry(device: str, tel: dict) -> None:
    now = time.time()
    if now - _last_write.get(device, 0) < 5:          # sample: at most 1 row / 5 s / device
        return
    _last_write[device] = now
    try:
        with _lock, _conn() as c:
            c.execute("INSERT INTO telemetry VALUES (?,?,?,?,?,?)",
                      (now, device,
                       _f(tel.get("temp_c")), _f(tel.get("humidity")),
                       _f(tel.get("light")), _f(tel.get("level"))))
    except Exception:
        pass


def add_event(kind: str, text: str) -> None:
    try:
        with _lock, _conn() as c:
            c.execute("INSERT INTO events VALUES (?,?,?)", (time.time(), kind, str(text)[:500]))
    except Exception:
        pass


def history(hours: float = 24, device: str | None = None) -> dict:
    since = time.time() - hours * 3600
    try:
        with _lock, _conn() as c:
            q = "SELECT ts,device,temp_c,humidity,light,level FROM telemetry WHERE ts>=?"
            args: list = [since]
            if device:
                q += " AND device=?"; args.append(device)
            tel = [dict(zip(("ts", "device", "temp_c", "humidity", "light", "level"), r))
                   for r in c.execute(q + " ORDER BY ts", args)]
            ev = [dict(zip(("ts", "kind", "text"), r))
                  for r in c.execute("SELECT ts,kind,text FROM events WHERE ts>=? ORDER BY ts DESC LIMIT 200", (since,))]
        return {"telemetry": tel, "events": ev, "hours": hours}
    except Exception as e:
        return {"telemetry": [], "events": [], "error": str(e)}


def _f(v):
    try:
        return float(v)
    except Exception:
        return None
