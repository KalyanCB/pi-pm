from __future__ import annotations

import logging
from collections import defaultdict
from decimal import Decimal
from statistics import median

from app.core.exceptions import StrategyNotFoundError
from app.models.ranking_run import RankingRun
from app.ranking.registry import RankingStrategyRegistry

logger = logging.getLogger(__name__)


def resolve_factor_weights(
    strategy_name: str,
    strategy_version: str,
    ranking_runs: list[RankingRun],
    registry: RankingStrategyRegistry | None = None,
) -> dict[str, float]:
    """Primary: metadata.effective_weights; fallback: strategy registry defaults."""
    registry = registry or RankingStrategyRegistry()
    collected: dict[str, list[float]] = defaultdict(list)

    for run in ranking_runs:
        metadata = run.metadata_ or {}
        weights = metadata.get("effective_weights") or {}
        if not weights:
            continue
        for factor, weight in weights.items():
            try:
                collected[factor].append(float(Decimal(str(weight))))
            except Exception:
                continue

    if collected:
        return {factor: median(values) for factor, values in collected.items()}

    try:
        strategy = registry.get(strategy_name, strategy_version)
        weights = strategy.base_weights()
        return {name: float(weight) for name, weight in weights.items()}
    except StrategyNotFoundError:
        logger.warning(
            "Could not resolve factor weights for %s@%s",
            strategy_name,
            strategy_version,
        )
        return {}
