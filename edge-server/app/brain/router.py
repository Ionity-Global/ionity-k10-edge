"""Decide how to answer: cache -> local LLM -> Claude bridge (escalation).
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Route:
    source: str      # "cache" | "local" | "bridge" | "local-lowconf"
    answer: str
    confidence: float
    meta: dict


class Router:
    def __init__(self, cache, local_llm, bridge, min_conf: float) -> None:
        self.cache = cache
        self.local = local_llm
        self.bridge = bridge
        self.min_conf = min_conf

    def answer(self, query: str, context: dict | None = None) -> Route:
        # 1) Semantic cache — instant, offline-capable
        hit = self.cache.lookup(query)
        if hit:
            return Route("cache", hit["answer"], hit["score"], {"cached": True})

        # 2) Local LLM
        local = self.local.ask(query) if self.local.available else {"text": "", "confidence": 0.0}
        conf = float(local.get("confidence", 0.0))
        text = local.get("text", "")

        # 3) Escalate to the Claude bridge when confidence is low and the bridge is up
        if conf < self.min_conf and self.bridge.enabled and self.bridge.available():
            br = self.bridge.ask(query, context)
            if br.get("ok") and br.get("text"):
                self.cache.store(query, br["text"], {"source": "bridge"})
                return Route("bridge", br["text"], 0.9, {"escalated": True})

        if text:
            self.cache.store(query, text, {"source": "local"})
            src = "local" if conf >= self.min_conf else "local-lowconf"
            return Route(src, text, conf, {})

        return Route("local-lowconf",
                     "Enable a local model (ollama pull gemma2) or the Claude bridge to chat.",
                     0.1, {"empty": True})
