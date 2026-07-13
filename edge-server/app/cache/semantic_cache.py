"""Semantic cache — instant, offline-capable answers for similar questions.

Uses sentence-transformers when installed; otherwise falls back to a deterministic
hashing embedding so the cache still works (lower quality) out of the box.
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
"""
from __future__ import annotations
import json
import math
import hashlib
from pathlib import Path
from typing import Optional

import numpy as np

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
    _HAVE_ST = True
except Exception:  # pragma: no cover
    _HAVE_ST = False


class _Embedder:
    def __init__(self) -> None:
        self.model = None
        self._tried = False   # lazy: don't load/download the model until first actual use

    def _ensure(self) -> None:
        if self._tried:
            return
        self._tried = True
        if _HAVE_ST:
            try:
                self.model = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception:
                self.model = None

    def embed(self, text: str) -> np.ndarray:
        self._ensure()
        if self.model is not None:
            return np.asarray(self.model.encode(text), dtype=np.float32)
        # Fallback: 256-dim hashing bag-of-words (deterministic, offline).
        vec = np.zeros(256, dtype=np.float32)
        for tok in text.lower().split():
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            vec[h % 256] += 1.0
        n = np.linalg.norm(vec)
        return vec / n if n else vec

    @property
    def quality(self) -> str:
        if not self._tried:
            return "lazy (hashing until first query)"
        return "sentence-transformers" if self.model is not None else "hashing-fallback"


def _cos(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if not na or not nb:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


class SemanticCache:
    def __init__(self, path: Path, threshold: float = 0.92, max_items: int = 5000) -> None:
        self.path = Path(path)
        self.threshold = threshold
        self.max_items = max_items
        self.embedder = _Embedder()
        self.items: list[dict] = []      # {q, a, emb, meta, hits}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text())
                for it in data:
                    it["emb"] = np.asarray(it["emb"], dtype=np.float32)
                self.items = data
            except Exception:
                self.items = []

    def _save(self) -> None:
        out = [{**it, "emb": it["emb"].tolist()} for it in self.items]
        self.path.write_text(json.dumps(out))

    def lookup(self, query: str) -> Optional[dict]:
        if not self.items:
            return None
        qe = self.embedder.embed(query)
        best, score = None, 0.0
        for it in self.items:
            s = _cos(qe, it["emb"])
            if s > score:
                best, score = it, s
        if best and score >= self.threshold:
            best["hits"] = best.get("hits", 0) + 1
            return {"answer": best["a"], "score": score, "meta": best.get("meta"), "cached": True}
        return None

    def store(self, query: str, answer: str, meta: dict | None = None) -> None:
        self.items.append({
            "q": query, "a": answer,
            "emb": self.embedder.embed(query),
            "meta": meta or {}, "hits": 0,
        })
        if len(self.items) > self.max_items:                 # LRU-ish: drop least-hit
            self.items.sort(key=lambda x: x.get("hits", 0))
            self.items = self.items[-self.max_items:]
        self._save()

    def stats(self) -> dict:
        return {
            "items": len(self.items),
            "threshold": self.threshold,
            "embedder": self.embedder.quality,
            "top": sorted(
                ({"q": i["q"], "hits": i.get("hits", 0)} for i in self.items),
                key=lambda x: x["hits"], reverse=True,
            )[:10],
        }
