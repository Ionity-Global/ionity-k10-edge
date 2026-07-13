"""In-memory event log ring buffer — powers the dashboard Logs panel.
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0"""
from __future__ import annotations
import time
from collections import deque

_BUF: deque = deque(maxlen=400)


def add(kind: str, msg: str) -> None:
    _BUF.append({"ts": time.time(), "kind": kind, "msg": str(msg)[:400]})


def recent(n: int = 120) -> list[dict]:
    return list(_BUF)[-n:]
