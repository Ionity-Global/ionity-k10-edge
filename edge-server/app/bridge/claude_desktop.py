"""Claude-desktop bridge.

Honours the wish to use YOUR Claude (via YOUR Google login, your subscription) instead
of a paid API key. It does NOT call the Anthropic API. Instead it relays a prompt to a
small local *companion relay* that you run on the same PC where Claude Desktop / Cowork is
open; that relay is responsible for handing the prompt to Claude and returning the text.

Modes:
  off  — disabled (local models only). Default and always-safe.
  http — POST {"prompt": ...} to BRIDGE_URL and read {"text": ...} back.

This keeps the design honest: an ESP32 cannot authenticate to Claude, and there is no
public "Claude account via Google" endpoint. The bridge is best-effort and only used when
enabled AND reachable; the orchestrator always falls back to local models.
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
"""
from __future__ import annotations
import json
import urllib.request


class ClaudeBridge:
    def __init__(self, mode: str, url: str) -> None:
        self.mode = (mode or "off").lower()
        self.url = url

    @property
    def enabled(self) -> bool:
        return self.mode == "http"

    def available(self) -> bool:
        if not self.enabled:
            return False
        try:
            req = urllib.request.Request(self.url, method="OPTIONS")
            urllib.request.urlopen(req, timeout=1.0)
            return True
        except Exception:
            # Some relays don't implement OPTIONS; treat as maybe-available.
            return True

    def ask(self, prompt: str, context: dict | None = None) -> dict:
        if not self.enabled:
            return {"text": "", "ok": False, "note": "bridge off"}
        body = json.dumps({"prompt": prompt, "context": context or {}}).encode()
        req = urllib.request.Request(
            self.url, data=body, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.loads(r.read())
            return {"text": (data.get("text") or "").strip(), "ok": True, "backend": "claude-bridge"}
        except Exception as e:
            return {"text": "", "ok": False, "error": str(e)}
