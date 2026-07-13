"""Peper's persona + learned memory — personalises the brain to Ionity.

Builds the system prompt from the project's metadata.json (Ionity (Pty) Ltd, Johan
Wilhelm van Antwerp, ionity.co.za / ionity.today, Policy 986 AED, Centurion SA) plus
facts the assistant LEARNS over time ("Peper, remember ..."), persisted in
data/profile.json. Injected into every brain call (Ollama system prompt + Claude
bridge context) — all on the server.
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
"""
from __future__ import annotations
import json
import re
import time
from pathlib import Path

from app.config import settings

_META_PATH = Path(__file__).resolve().parents[3] / "metadata.json"
_PROFILE = Path(settings.data_dir) / "profile.json"


def _meta() -> dict:
    try:
        return json.loads(_META_PATH.read_text())
    except Exception:
        return {}


def facts() -> list[dict]:
    try:
        return json.loads(_PROFILE.read_text())
    except Exception:
        return []


def remember(fact: str) -> None:
    f = facts()
    f.append({"fact": fact.strip()[:200], "ts": time.time()})
    _PROFILE.write_text(json.dumps(f[-60:], indent=1))   # keep the newest 60 facts


def forget_all() -> int:
    n = len(facts())
    _PROFILE.write_text("[]")
    return n


_REMEMBER_RE = re.compile(r"\b(?:remember|onthou)(?:\s+that)?\s+(.{3,})", re.IGNORECASE)


def maybe_remember(text: str) -> str | None:
    """If the utterance is a 'remember ...' instruction, store it and return an ack."""
    m = _REMEMBER_RE.search(text or "")
    if m:
        remember(m.group(1))
        return "Okay, I'll remember that."
    return None


def system_prompt() -> str:
    m = _meta()
    author = (m.get("author") or {}).get("name", "Johan Wilhelm van Antwerp")
    entity = m.get("entity", "Ionity (Pty) Ltd (AEDI)")
    sites = ", ".join(m.get("websites", ["ionity.co.za", "ionity.today"]))
    loc = m.get("location") or {}
    lines = [
        f"You are {settings.assistant_name or 'Peper'}, the Ionity home assistant — a voice AI "
        f"running fully on the local edge server (no cloud) for {entity}.",
        f"You were created by {author} in {loc.get('city','Centurion')}, {loc.get('country','South Africa')}. "
        f"Websites: {sites}. Governance: {m.get('governance','Policy 986 AED')}. "
        f"Tagline: {m.get('tagline','Building Tomorrow, Today.')}",
        "Your answers are SPOKEN ALOUD through a small speaker: keep them to 1–2 short sentences, "
        "warm and direct. Never read out URLs or markdown. You can control the smart home "
        "(lights, media, scenes), read text through your camera, and learn facts when asked to remember.",
    ]
    fs = facts()
    if fs:
        lines.append("Facts you have learned about your user (use them naturally): " +
                     "; ".join(f["fact"] for f in fs[-20:]))
    return "\n".join(lines)
