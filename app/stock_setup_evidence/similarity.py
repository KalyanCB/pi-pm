from __future__ import annotations

import math
from datetime import date

from app.stock_setup_evidence.constants import SEE_FACTOR_NAMES


def similarity_score(
    reference: dict[str, float],
    candidate: dict[str, float],
    *,
    factor_names: tuple[str, ...] = SEE_FACTOR_NAMES,
) -> float:
    """Cosine similarity on overlapping normalized factors (0–1)."""
    if not reference or not candidate:
        return 0.0
    dot = 0.0
    ref_norm = 0.0
    cand_norm = 0.0
    used = 0
    for name in factor_names:
        a = reference.get(name)
        b = candidate.get(name)
        if a is None or b is None:
            continue
        used += 1
        dot += a * b
        ref_norm += a * a
        cand_norm += b * b
    if used < 3 or ref_norm <= 0 or cand_norm <= 0:
        return 0.0
    return dot / (math.sqrt(ref_norm) * math.sqrt(cand_norm))


def select_nearest_setups(
    reference: dict[str, float],
    historical: dict[date, dict[str, float]],
    *,
    nearest_n: int,
    min_similarity: float,
) -> list[tuple[date, float, dict[str, float]]]:
    scored: list[tuple[date, float, dict[str, float]]] = []
    for setup_date, profile in historical.items():
        score = similarity_score(reference, profile)
        if score >= min_similarity:
            scored.append((setup_date, score, profile))
    scored.sort(key=lambda row: (-row[1], row[0]))
    return scored[:nearest_n]
