from __future__ import annotations

from statistics import mean

from app.outcome_attribution.constants import REGIME_LABEL_ALL
from app.ranking_research.constants import (
    MIN_OBS_FOR_FACTOR_ANALYSIS,
    RESEARCH_HORIZONS,
    STRATEGY_FACTOR_KEYS,
)
from app.ranking_research.models import (
    EnrichedStockObservation,
    FactorReliabilityRow,
    FactorReliabilitySegment,
)


def _extract_normalized(components: dict | None, factor: str) -> float | None:
    if not components:
        return None
    block = components.get(factor)
    if not isinstance(block, dict):
        return None
    raw = block.get("normalized")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def build_factor_reliability_segment(
    *,
    strategy_name: str,
    regime_label: str,
    horizon: int,
    observations: list[EnrichedStockObservation],
) -> FactorReliabilitySegment | None:
    if regime_label == REGIME_LABEL_ALL:
        subset = [o for o in observations if o.strategy_name == strategy_name and o.rank <= 20]
    else:
        subset = [
            o
            for o in observations
            if o.strategy_name == strategy_name
            and o.regime_label == regime_label
            and o.rank <= 20
        ]
    if not subset:
        return None

    factor_keys = STRATEGY_FACTOR_KEYS.get(strategy_name, ())
    if not factor_keys:
        return None

    by_run: dict = {}
    for obs in subset:
        ret = obs.returns.get(horizon)
        if ret is None:
            continue
        by_run.setdefault(obs.run_id, []).append(obs)

    rows: list[FactorReliabilityRow] = []
    for factor in factor_keys:
        winner_norms: list[float] = []
        loser_norms: list[float] = []

        for _run_id, run_obs in by_run.items():
            returns = [o.returns[horizon] for o in run_obs if o.returns.get(horizon) is not None]
            if not returns:
                continue
            median_ret = sorted(returns)[len(returns) // 2]
            for obs in run_obs:
                ret = obs.returns.get(horizon)
                norm = _extract_normalized(obs.score_components, factor)
                if ret is None or norm is None:
                    continue
                if ret >= median_ret:
                    winner_norms.append(norm)
                else:
                    loser_norms.append(norm)

        w_mean = mean(winner_norms) if winner_norms else None
        l_mean = mean(loser_norms) if loser_norms else None
        spread = (w_mean - l_mean) if w_mean is not None and l_mean is not None else None
        reliability = None
        if spread is not None and len(winner_norms) + len(loser_norms) >= MIN_OBS_FOR_FACTOR_ANALYSIS:
            reliability = spread

        rows.append(
            FactorReliabilityRow(
                factor_name=factor,
                horizon=horizon,
                winner_mean_normalized=w_mean,
                loser_mean_normalized=l_mean,
                spread=spread,
                winner_count=len(winner_norms),
                loser_count=len(loser_norms),
                reliability_score=reliability,
            )
        )

    return FactorReliabilitySegment(
        strategy_name=strategy_name,
        regime_label=regime_label,
        horizon=horizon,
        rows=tuple(rows),
    )
