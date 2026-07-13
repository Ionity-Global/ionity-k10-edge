"""Orchestrator — ties models, router, cache, provenance into one pipeline.
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0"""
from __future__ import annotations
from pathlib import Path

from app.config import settings
from app.cache.semantic_cache import SemanticCache
from app.models.stt import STT
from app.models.tts import TTS
from app.models.ocr import OCR
from app.models.vision import Vision
from app.models.mood import Mood
from app.models.llm_local import LocalLLM
from app.bridge.claude_desktop import ClaudeBridge
from app.brain.router import Router
from app.brain import persona
from app.meta import provenance


class Orchestrator:
    def __init__(self) -> None:
        self.cache = SemanticCache(settings.data_dir / "semantic_cache.json",
                                   settings.cache_threshold, settings.cache_max)
        self.stt = STT()
        self.tts = TTS(settings.tts_voice or settings.piper_voice or None)
        self.ocr = OCR()
        self.vision = Vision()
        self.mood = Mood()
        self.llm = LocalLLM(settings.ollama_url, settings.ollama_model)
        self.bridge = ClaudeBridge(settings.bridge_mode, settings.bridge_url)
        self.router = Router(self.cache, self.llm, self.bridge, settings.bridge_min_confidence)

    # ---- text query ----
    def ask(self, query: str, context: dict | None = None) -> dict:
        ctx = dict(context or {})
        ctx.setdefault("system", persona.system_prompt())   # Ionity-personalised, with learned facts
        route = self.router.answer(query, ctx)
        mood = self.mood.infer_text(query)
        result = {
            "text": route.answer, "source": route.source,
            "confidence": route.confidence, "mood": mood,
        }
        result["provenance"] = provenance.stamp("answer", result)
        return result

    # ---- audio: STT -> ask ----
    def ask_audio(self, wav_path: str) -> dict:
        tr = self.stt.transcribe(wav_path)
        query = tr.get("text", "")
        if not query:
            return {"text": "", "source": "stt", "note": tr.get("note", "no speech")}
        out = self.ask(query)
        out["transcript"] = query
        out["mood_audio"] = self.mood.infer_audio(wav_path)
        return out

    # ---- image: OCR + vision ----
    def analyze_image(self, image_path: str, want_ocr: bool = True) -> dict:
        out: dict = {}
        if settings.feat_ocr and want_ocr:
            out["ocr"] = self.ocr.read(image_path)
        if settings.feat_vision:
            out["vision"] = self.vision.analyze(image_path)
        out["provenance"] = provenance.stamp("image_analysis", out)
        return out

    # ---- TTS ----
    def speak(self, text: str, out_wav: str) -> str | None:
        return self.tts.synth(text, out_wav)

    # ---- status for the installer dashboard ----
    def status(self) -> dict:
        return {
            "models": {
                "stt": self.stt.available, "tts": self.tts.available,
                "ocr": self.ocr.available, "vision": self.vision.available,
                "mood": self.mood.available, "local_llm": self.llm.available,
            },
            "bridge": {"enabled": self.bridge.enabled, "mode": self.bridge.mode},
            "cache": self.cache.stats(),
        }
