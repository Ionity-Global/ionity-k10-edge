"""Ionity Edge MCP server — control the home assistant from Claude (or any MCP client).

Exposes the RUNNING Edge Brain (http://127.0.0.1:8765) as MCP tools over stdio:
chat, speak, home, ocr_now, get_vision, get_stats, get_history, remember.

Register with Claude Code / Desktop:
    claude mcp add ionity-edge -- py -3.12 "<repo>/edge-server/mcp_server.py"
or run START-MCP.bat. Requires: pip install mcp  (and the Edge Brain running).
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
"""
from __future__ import annotations
import json
import os
import urllib.parse
import urllib.request

from mcp.server.fastmcp import FastMCP

BASE = os.environ.get("IONITY_EDGE_URL", "http://127.0.0.1:8765")
mcp = FastMCP("ionity-edge")


def _get(path: str) -> dict:
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return json.loads(r.read())


def _post(path: str, obj: dict | None = None, timeout: int = 120) -> dict:
    data = json.dumps(obj or {}).encode()
    req = urllib.request.Request(BASE + path, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


@mcp.tool()
def chat(text: str) -> str:
    """Ask the Ionity home assistant (Peper). The reply is also spoken on the K10 speaker."""
    d = _post("/api/chat", {"text": text})
    return f"[{d.get('source')}] {d.get('reply', '')}"


@mcp.tool()
def speak(text: str) -> str:
    """Make the K10 device say something out loud (TTS through the ESP speaker)."""
    d = _post("/api/chat", {"text": f"Say exactly: {text}"})
    return d.get("reply", "")


@mcp.tool()
def home(command: str) -> str:
    """Run a smart-home command (e.g. 'turn on the lights', 'play music', 'activate movie scene')."""
    d = _post("/api/dispatch", {"command": command})
    return json.dumps(d)


@mcp.tool()
def ocr_now() -> str:
    """Trigger the K10 camera to capture a frame; Gemma vision reads what it sees (~10 s)."""
    _post("/api/ocr-now")
    return "capture requested — call get_vision() in ~10 seconds for the result"


@mcp.tool()
def get_vision() -> str:
    """Latest camera OCR / vision result from the device."""
    d = _get("/api/vision")
    return f"[{d.get('backend') or 'none'}] {d.get('text') or '(no vision result yet)'}"


@mcp.tool()
def get_stats() -> str:
    """Live status: assistant state, device sensors, brain models, cache."""
    a = _get("/api/assistant"); s = _get("/api/status"); l = _get("/api/live")
    dev = (l.get("devices") or {}).get("ionity-k10", {})
    return json.dumps({
        "assistant": {k: a.get(k) for k in ("state", "tone", "reply", "awake")},
        "device": dev.get("latest", {}),
        "brain": s.get("brain", {}),
    }, indent=1)


@mcp.tool()
def get_history(hours: float = 24) -> str:
    """Stored telemetry + event history from the SQLite store (temperature, humidity, chats, vision)."""
    d = _get(f"/api/history?hours={urllib.parse.quote(str(hours))}")
    tel = d.get("telemetry", [])
    out = {"rows": len(tel), "events": d.get("events", [])[:20]}
    if tel:
        temps = [t["temp_c"] for t in tel if t.get("temp_c") is not None]
        if temps:
            out["temp_c"] = {"min": min(temps), "max": max(temps), "last": temps[-1]}
    return json.dumps(out, indent=1)


@mcp.tool()
def remember(fact: str) -> str:
    """Teach the assistant a fact about the user (persisted, used in every future answer)."""
    d = _post("/api/chat", {"text": f"Remember {fact}"})
    return d.get("reply", "stored")


if __name__ == "__main__":
    mcp.run()
