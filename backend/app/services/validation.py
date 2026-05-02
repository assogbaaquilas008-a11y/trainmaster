"""
Hybrid Answer Validation Engine
================================
Layer 1 – Exact / fuzzy string matching (local, zero cost)
  • Case + punctuation insensitive
  • Levenshtein-based ratio via `rapidfuzz`
  • Checks against correct_answer AND any pipe-separated alt_answers

Layer 2 – Semantic similarity (local SBERT model OR HuggingFace API)
  • Only runs when fuzzy score is inconclusive (below threshold)
  • Uses `sentence-transformers` paraphrase-MiniLM-L6-v2 (~80 MB, Apache 2)
  • Falls back to HuggingFace Inference API if VALIDATION_BACKEND=huggingface

Result dataclass contains: is_correct, confidence (0-1), method name.
"""

from __future__ import annotations

import re
import string
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import httpx
import structlog
from rapidfuzz import fuzz

from app.core.config import settings

log = structlog.get_logger()

_PUNCTUATION_TABLE = str.maketrans("", "", string.punctuation)


def _normalise(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower().translate(_PUNCTUATION_TABLE)
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class ValidationResult:
    is_correct: bool
    confidence: float          # 0.0 – 1.0
    method: str                # "exact" | "fuzzy" | "semantic_local" | "semantic_api"
    explanation: Optional[str] = None


# ---------------------------------------------------------------------------
# Layer 1 – Fuzzy matching
# ---------------------------------------------------------------------------

def _fuzzy_validate(submitted: str, correct: str, alts: Optional[str]) -> ValidationResult:
    """Return the best fuzzy match across correct answer and all alternatives."""
    candidates = [correct]
    if alts:
        candidates.extend(a.strip() for a in alts.split("|") if a.strip())

    norm_sub = _normalise(submitted)
    best_ratio = 0.0

    for candidate in candidates:
        norm_cand = _normalise(candidate)

        # Exact match after normalisation
        if norm_sub == norm_cand:
            return ValidationResult(True, 1.0, "exact", "Exact match after normalisation")

        # Token-set ratio handles word-order differences
        ratio = max(
            fuzz.ratio(norm_sub, norm_cand),
            fuzz.token_set_ratio(norm_sub, norm_cand),
            fuzz.partial_ratio(norm_sub, norm_cand),
        )
        best_ratio = max(best_ratio, ratio)

    confidence = best_ratio / 100.0
    is_correct = best_ratio >= settings.FUZZY_THRESHOLD

    return ValidationResult(
        is_correct=is_correct,
        confidence=confidence,
        method="fuzzy",
        explanation=f"Best fuzzy ratio: {best_ratio:.1f}",
    )


# ---------------------------------------------------------------------------
# Layer 2a – Local SBERT
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _get_sbert_model():
    """Lazy-load SBERT model once; cached for the process lifetime."""
    try:
        from sentence_transformers import SentenceTransformer
        log.info("validation.sbert_loading")
        model = SentenceTransformer("paraphrase-MiniLM-L6-v2")
        log.info("validation.sbert_ready")
        return model
    except ImportError:
        log.warning("validation.sbert_unavailable", reason="sentence-transformers not installed")
        return None


def _semantic_local(submitted: str, correct: str) -> Optional[ValidationResult]:
    model = _get_sbert_model()
    if model is None:
        return None

    try:
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np

        emb = model.encode([_normalise(submitted), _normalise(correct)])
        sim = float(cosine_similarity([emb[0]], [emb[1]])[0][0])
        is_correct = sim >= settings.SEMANTIC_THRESHOLD

        return ValidationResult(
            is_correct=is_correct,
            confidence=sim,
            method="semantic_local",
            explanation=f"Cosine similarity: {sim:.3f}",
        )
    except Exception as exc:
        log.error("validation.sbert_error", exc=str(exc))
        return None


# ---------------------------------------------------------------------------
# Layer 2b – HuggingFace Inference API
# ---------------------------------------------------------------------------

async def _semantic_huggingface(submitted: str, correct: str) -> Optional[ValidationResult]:
    """
    Uses HF sentence-similarity endpoint (free tier, rate-limited).
    Model: sentence-transformers/paraphrase-MiniLM-L6-v2
    """
    if not settings.HUGGINGFACE_API_KEY:
        return None

    url = "https://api-inference.huggingface.co/models/sentence-transformers/paraphrase-MiniLM-L6-v2"
    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}
    payload = {
        "inputs": {
            "source_sentence": _normalise(correct),
            "sentences": [_normalise(submitted)],
        }
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            scores = response.json()
            sim = float(scores[0]) if isinstance(scores, list) else 0.0

        is_correct = sim >= settings.SEMANTIC_THRESHOLD
        return ValidationResult(
            is_correct=is_correct,
            confidence=sim,
            method="semantic_api",
            explanation=f"HuggingFace similarity: {sim:.3f}",
        )
    except Exception as exc:
        log.error("validation.hf_error", exc=str(exc))
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def validate_answer(
    submitted: str,
    correct: str,
    alt_answers: Optional[str] = None,
) -> ValidationResult:
    """
    Full hybrid validation pipeline.

    1. Try fuzzy – if confident (>=threshold), return immediately.
    2. If inconclusive, escalate to semantic layer.
    3. Semantic result overrides fuzzy only when fuzzy was inconclusive.
    """
    fuzzy_result = _fuzzy_validate(submitted, correct, alt_answers)

    # Clear accept or clear reject from fuzzy – skip semantic
    if fuzzy_result.confidence >= (settings.FUZZY_THRESHOLD / 100.0):
        return fuzzy_result

    # Short / empty submissions – no point running expensive model
    if len(submitted.strip()) < 2:
        return ValidationResult(False, 0.0, "fuzzy", "Answer too short")

    # Semantic fallback
    sem_result: Optional[ValidationResult] = None

    if settings.VALIDATION_BACKEND == "huggingface":
        sem_result = await _semantic_huggingface(submitted, correct)
    else:
        sem_result = _semantic_local(submitted, correct)

    if sem_result is not None:
        log.debug(
            "validation.semantic_used",
            fuzzy_conf=fuzzy_result.confidence,
            semantic_conf=sem_result.confidence,
        )
        return sem_result

    # Semantic unavailable – fall back to fuzzy verdict
    return fuzzy_result
