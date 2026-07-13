"""Local LLM via Ollama HTTP API. Returns availability + confidence heuristic.
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0"""
from __future__ import annotations
import json
import urllib.request
import urllib.error


class LocalLLM:
    def __init__(self, url: str, model: str) -> None:
        self.url = url.rstrip("/")
        self.model = model

    @property
    def available(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.url}/api/tags", timeout=1.5) as r:
                return r.status == 200
        except Exception:
            return False

    def ask(self, prompt: str, system: str | None = None) -> dict:
        body = {
            "model": self.model,
            "prompt": prompt,
            "system": system or "You are Ionity Edge, a concise local assistant.",
            "stream": False,
        }
        req = urllib.request.Request(
            f"{self.url}/api/generate",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
            text = (data.get("response") or "").strip()
            # crude confidence: longer, non-hedging answers score higher
            conf = 0.8 if len(text) > 40 and "i don't know" not in text.lower() else 0.4
            return {"text": text, "confidence": conf, "backend": "ollama"}
        except Exception as e:
            return {"text": "", "confidence": 0.0, "backend": "ollama", "error": str(e)}
