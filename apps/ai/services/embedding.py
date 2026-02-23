from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from typing import Sequence

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - fallback only used if dependency missing
    SentenceTransformer = None  # type: ignore


MODEL_NAME = os.getenv("ST_MODEL_NAME", "paraphrase-multilingual-MiniLM-L12-v2")
FALLBACK_DIM = 384


@lru_cache(maxsize=1)
def _get_model():
    if SentenceTransformer is None:
        return None
    return SentenceTransformer(MODEL_NAME)


def _fallback_embedding(text: str, dim: int = FALLBACK_DIM) -> list[float]:
    # Deterministic hash-based embedding so local dev still works without model download.
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = np.frombuffer(digest, dtype=np.uint8).astype(np.float32)
    repeated = np.resize(values, dim)
    norm = np.linalg.norm(repeated)
    if norm == 0:
        return repeated.tolist()
    return (repeated / norm).tolist()


def encode_text(text: str) -> list[float]:
    model = _get_model()
    if model is None:
        return _fallback_embedding(text)
    vector = model.encode(text, normalize_embeddings=True)
    return np.asarray(vector, dtype=np.float32).tolist()


def batch_encode_text(texts: Sequence[str]) -> list[list[float]]:
    model = _get_model()
    if model is None:
        return [_fallback_embedding(text) for text in texts]
    vectors = model.encode(list(texts), normalize_embeddings=True)
    return [np.asarray(vector, dtype=np.float32).tolist() for vector in vectors]


def cosine_similarity(vector1: Sequence[float], vector2: Sequence[float]) -> float:
    a = np.asarray(vector1, dtype=np.float32)
    b = np.asarray(vector2, dtype=np.float32)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    similarity = float(np.dot(a, b) / denom)
    return max(0.0, min(1.0, similarity))
