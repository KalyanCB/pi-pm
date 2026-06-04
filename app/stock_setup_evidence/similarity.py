from __future__ import annotations

import math
from datetime import date


def similarity_score(
    reference: dict[str, float],
    candidate: dict[str, float],
    *,
    factor_names: tuple[str, ...],
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


def select_qualifying_setups(
    reference: dict[str, float],
    historical: dict[date, dict[str, float]],
    *,
    factor_names: tuple[str, ...],
    min_similarity: float,
) -> tuple[list[tuple[date, float, dict[str, float]]], int]:
    """
    Return all historical setups with similarity >= threshold (no fixed-N cap).

    Returns (qualifying_matches, total_scored_candidates).
    """
    scored: list[tuple[date, float, dict[str, float]]] = []
    for setup_date, profile in historical.items():
        score = similarity_score(reference, profile, factor_names=factor_names)
        scored.append((setup_date, score, profile))
    total_scored = len(scored)
    qualifying = [row for row in scored if row[1] >= min_similarity]
    qualifying.sort(key=lambda row: (-row[1], row[0]))
    return qualifying, total_scored


def select_nearest_setups(
    reference: dict[str, float],
    historical: dict[date, dict[str, float]],
    *,
    factor_names: tuple[str, ...],
    nearest_n: int,
    min_similarity: float,
) -> list[tuple[date, float, dict[str, float]]]:
    """Backward-compatible v1 helper; prefer select_qualifying_setups in v2."""
    qualifying, _ = select_qualifying_setups(
        reference,
        historical,
        factor_names=factor_names,
        min_similarity=min_similarity,
    )
    if nearest_n > 0:
        return qualifying[:nearest_n]
    return qualifying
