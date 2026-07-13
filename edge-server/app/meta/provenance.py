"""AEDI / Policy 986 provenance stamping (Forensic Output Standards).
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone, timedelta

SAST = timezone(timedelta(hours=2))  # UTC+2, Centurion

AUTHOR = "Johan Wilhelm van Antwerp"
ENTITY = "Ionity (Pty) Ltd / Antwerp Designs (AEDI)"
POLICY = "Policy 986 AED"
LICENSE = "CC BY-SA 4.0"


def stamp(kind: str, payload: dict | str | bytes) -> dict:
    """Return an AEDI provenance block for any artefact."""
    if isinstance(payload, (dict, list)):
        raw = json.dumps(payload, sort_keys=True, default=str).encode()
    elif isinstance(payload, str):
        raw = payload.encode()
    else:
        raw = payload
    digest = hashlib.sha256(raw).hexdigest()
    now = datetime.now(SAST)
    return {
        "kind": kind,
        "author": AUTHOR,
        "entity": ENTITY,
        "policy": POLICY,
        "license": LICENSE,
        "ts": now.isoformat(),
        "tz": "UTC+2",
        "sha256": digest,
        "sig": f"AEDI:{digest[:16]}",
    }
