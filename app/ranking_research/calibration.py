from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from statistics import mean

from app.outcome_attribution.constants import REGIME_LABEL_ALL
from app.outcome_attribution.statistics import mean_or_none
from app.ranking_research.constants import (
    DEFAULT_CALIBRATION_WEIGHTS,
    EXACT_RANKS,
    RESEARCH_HORIZONS,
    STRATEGY_FACTOR_KEYS,
)
from app.ranking_research.factor_reliability import _extract_normalized
from app.ranking_research.models import EnrichedStockObservation
from app.outcome_attribution.models import RunBenchmark


@dataclass(frozen=True)
class CalibrationWeights:
    """Research-only weights; not deployed to production ranking."""

    raw_score: float = DEFAULT_CALIBRATION_WEIGHTS["raw_score"]
    regime_reliability: float = DEFAULT_CALIBRATION_WEIGHTS["regime_reliability"]
    factor_reliability: float = DEFAULT_CALIBRATION_WEIGHTS["factor_reliability"]
    historical_rank_reliability: float = DEFAULT_CALIBRATION_WEIGHTS[
        "historical_rank_reliability"
    ]

    def as_dict(self) -> dict[str, float]:
        return {
            "raw_score": self.raw_score,
            "regime_reliability": self.regime_reliability,
            "factor_reliability": self.factor_reliability,
            "historical_rank_reliability": self.historical_rank_reliability,
        }


@dataclass
class CalibrationTables:
    """
    Lookup tables built from the same historical window as the backtest.

    Data sources (read-only):
    - ranking_results.score, score_components
    - ranking_performance_snapshots forward returns
    - ranking_validation_reports.regime_label
    """

    # strategy -> regime -> rank -> mean alpha at 20d
    regime_rank_alpha: dict[str, dict[str, dict[int, float]]]
    # strategy -> rank -> mean alpha at 20d (all regimes)
    historical_rank_alpha: dict[str, dict[int, float]]
    # strategy -> factor -> reliability spread (winners vs losers normalized)
    factor_reliability: dict[str, dict[str, float]]
    weights: CalibrationWeights
    calibration_horizon: int = 20


def build_calibration_tables(
    observations: list[EnrichedStockObservation],
    benchmarks: list[RunBenchmark],
    *,
    weights: CalibrationWeights | None = None,
    horizon: int = 20,
) -> CalibrationTables:
    weights = weights or CalibrationWeights()
    benchmark_by_run = {b.run_id: b for b in benchmarks}

    regime_rank_returns: dict[str, dict[str, dict[int, list[float]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    historical_rank_returns: dict[str, dict[int, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    factor_winner: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    factor_loser: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    by_run: dict = defaultdict(list)
    for obs in observations:
        by_run[(obs.strategy_name, obs.run_id)].append(obs)

    for (strategy, run_id), run_obs in by_run.items():
        bench = benchmark_by_run.get(run_id)
        bench_ret = bench.returns.get(horizon) if bench else None
        regime = run_obs[0].regime_label or REGIME_LABEL_ALL

        returns = [o.returns.get(horizon) for o in run_obs if o.returns.get(horizon) is not None]
        if not returns:
            continue
        median_ret = sorted(returns)[len(returns) // 2]

        for obs in run_obs:
            ret = obs.returns.get(horizon)
            if ret is None or obs.rank > 20:
                continue
            alpha = ret - bench_ret if bench_ret is not None else ret
            regime_key = regime or REGIME_LABEL_ALL
            regime_rank_returns[strategy][regime_key][obs.rank].append(alpha)
            historical_rank_returns[strategy][obs.rank].append(alpha)

            for factor in STRATEGY_FACTOR_KEYS.get(strategy, ()):
                norm = _extract_normalized(obs.score_components, factor)
                if norm is None:
                    continue
                if ret >= median_ret:
                    factor_winner[strategy][factor].append(norm)
                else:
                    factor_loser[strategy][factor].append(norm)

    def _mean_alpha(groups: dict[int, list[float]]) -> dict[int, float]:
        return {rank: mean(vals) for rank, vals in groups.items() if vals}

    regime_rank_alpha: dict[str, dict[str, dict[int, float]]] = {}
    for strategy, regimes in regime_rank_returns.items():
        regime_rank_alpha[strategy] = {
            regime: _mean_alpha(ranks) for regime, ranks in regimes.items()
        }

    historical_rank_alpha: dict[str, dict[int, float]] = {
        strategy: _mean_alpha(ranks) for strategy, ranks in historical_rank_returns.items()
    }

    factor_reliability: dict[str, dict[str, float]] = {}
    for strategy in set(factor_winner) | set(factor_loser):
        factor_reliability[strategy] = {}
        for factor in STRATEGY_FACTOR_KEYS.get(strategy, ()):
            w = factor_winner[strategy].get(factor, [])
            l = factor_loser[strategy].get(factor, [])
            if w and l:
                factor_reliability[strategy][factor] = mean(w) - mean(l)

    return CalibrationTables(
        regime_rank_alpha=regime_rank_alpha,
        historical_rank_alpha=historical_rank_alpha,
        factor_reliability=factor_reliability,
        weights=weights,
        calibration_horizon=horizon,
    )


def compute_calibrated_score(
    *,
    raw_score: float,
    rank: int,
    strategy_name: str,
    regime_label: str | None,
    score_components: dict | None,
    tables: CalibrationTables,
) -> float:
    """
    Research calibration formula (not deployed):

    calibrated_score = w_raw * raw_score
        + w_regime * regime_reliability
        + w_factor * factor_reliability
        + w_rank * historical_rank_reliability

    Reliability terms are historical mean alphas (20d) centered to zero mean per strategy.
    """
    w = tables.weights
    regime_key = regime_label or REGIME_LABEL_ALL

    regime_alpha = (
        tables.regime_rank_alpha.get(strategy_name, {})
        .get(regime_key, {})
        .get(rank)
    )
    if regime_alpha is None:
        regime_alpha = (
            tables.regime_rank_alpha.get(strategy_name, {})
            .get(REGIME_LABEL_ALL, {})
            .get(rank, 0.0)
        )
    regime_alpha = regime_alpha or 0.0

    hist_alpha = tables.historical_rank_alpha.get(strategy_name, {}).get(rank, 0.0) or 0.0

    factor_term = 0.0
    factors = STRATEGY_FACTOR_KEYS.get(strategy_name, ())
    rel_map = tables.factor_reliability.get(strategy_name, {})
    if factors and rel_map:
        terms: list[float] = []
        for factor in factors:
            norm = _extract_normalized(score_components, factor)
            spread = rel_map.get(factor)
            if norm is not None and spread is not None:
                terms.append(norm * spread)
        factor_term = mean_or_none(terms) or 0.0

    return (
        w.raw_score * raw_score
        + w.regime_reliability * regime_alpha
        + w.factor_reliability * factor_term
        + w.historical_rank_reliability * hist_alpha
    )

