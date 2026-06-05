"""Deterministic analytics calculators for recommendation performance.

All functions are pure (take data, return metrics). No DB access, no LLM.
Same inputs → same outputs (AC-RP-08, AC-RP-09).
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from app.recommendation_analytics.dtos import (
    CommitteeAdvisoryMetricsDTO,
    ConvictionBandMetricsDTO,
    QualityMetricsDTO,
    RegimeMetricsDTO,
)

# ── Outcome row shape expected by calculators ─────────────────────────────────
# Callers pass plain dicts or dataclasses with these keys.
# This avoids coupling to ORM models in the pure layer.


@dataclass(frozen=True)
class OutcomeRow:
    outcome_status: str  # OPEN | WIN | LOSS | BREAKEVEN
    alpha_pct: float | None
    pnl_pct: float | None
    benchmark_return_pct: float | None
    target_hit: bool | None
    stop_hit: bool | None
    days_held: int | None
    conviction_band: str | None
    regime_label: str | None
    strategy_name: str | None
    committee_advisory: str | None
    symbol: str | None


# ── Helpers ───────────────────────────────────────────────────────────────────


def _closed(rows: list[OutcomeRow]) -> list[OutcomeRow]:
    return [r for r in rows if r.outcome_status in ("WIN", "LOSS", "BREAKEVEN")]


def _safe_mean(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None


def _safe_median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def _safe_div(num: float, den: float) -> float | None:
    return num / den if den else None


# ── Core quality metrics ──────────────────────────────────────────────────────


def compute_quality_metrics(rows: list[OutcomeRow]) -> QualityMetricsDTO:
    closed = _closed(rows)
    wins = [r for r in closed if r.outcome_status == "WIN"]
    losses = [r for r in closed if r.outcome_status == "LOSS"]
    be = [r for r in closed if r.outcome_status == "BREAKEVEN"]
    opens = [r for r in rows if r.outcome_status == "OPEN"]

    win_rate = _safe_div(len(wins), len(closed))

    gain_alphas = [float(r.alpha_pct) for r in wins if r.alpha_pct is not None]
    loss_alphas = [float(r.alpha_pct) for r in losses if r.alpha_pct is not None]
    all_alphas = [float(r.alpha_pct) for r in closed if r.alpha_pct is not None]

    profit_sum = sum(a for a in gain_alphas if a > 0)
    loss_sum = abs(sum(a for a in loss_alphas if a < 0))
    profit_factor = _safe_div(profit_sum, loss_sum)

    target_hits = [r for r in closed if r.target_hit is True]
    stop_hits = [r for r in closed if r.stop_hit is True]

    days_vals = [r.days_held for r in closed if r.days_held is not None]

    return QualityMetricsDTO(
        recommendation_count=len(rows),
        closed_count=len(closed),
        open_count=len(opens),
        win_count=len(wins),
        loss_count=len(losses),
        breakeven_count=len(be),
        win_rate=win_rate,
        avg_gain_pct=_safe_mean(gain_alphas),
        avg_loss_pct=_safe_mean(loss_alphas),
        profit_factor=profit_factor,
        avg_alpha_pct=_safe_mean(all_alphas),
        median_alpha_pct=_safe_median(all_alphas),
        target_hit_rate=_safe_div(len(target_hits), len(closed)),
        stop_hit_rate=_safe_div(len(stop_hits), len(closed)),
        avg_days_held=_safe_mean([float(d) for d in days_vals]) if days_vals else None,
    )


# ── Conviction band breakdown ──────────────────────────────────────────────────

_BAND_ORDER = ["EXCEPTIONAL", "HIGH", "MEDIUM", "LOW", "BLOCKED"]


def compute_conviction_breakdown(rows: list[OutcomeRow]) -> list[ConvictionBandMetricsDTO]:
    by_band: dict[str, list[OutcomeRow]] = {}
    for r in rows:
        band = r.conviction_band or "UNKNOWN"
        by_band.setdefault(band, []).append(r)

    results: list[ConvictionBandMetricsDTO] = []
    for band in _BAND_ORDER + [b for b in by_band if b not in _BAND_ORDER]:
        band_rows = by_band.get(band, [])
        if not band_rows:
            continue
        closed = _closed(band_rows)
        wins = [r for r in closed if r.outcome_status == "WIN"]
        losses = [r for r in closed if r.outcome_status == "LOSS"]
        alphas = [float(r.alpha_pct) for r in closed if r.alpha_pct is not None]
        gain_sum = sum(a for a in alphas if a > 0)
        loss_sum = abs(sum(a for a in alphas if a < 0))
        targets = [r for r in closed if r.target_hit is True]

        results.append(
            ConvictionBandMetricsDTO(
                band=band,
                count=len(band_rows),
                closed_count=len(closed),
                win_rate=_safe_div(len(wins), len(closed)),
                avg_alpha_pct=_safe_mean(alphas),
                profit_factor=_safe_div(gain_sum, loss_sum),
                target_hit_rate=_safe_div(len(targets), len(closed)),
            )
        )
    return results


def check_conviction_calibration(
    band_metrics: list[ConvictionBandMetricsDTO],
) -> tuple[bool | None, float | None]:
    """Return (is_calibrated, rank_correlation).

    Checks whether win_rate decreases monotonically from EXCEPTIONAL→HIGH→MEDIUM→LOW.
    Uses Spearman rank correlation: expected ranks [1,2,3,4] vs actual win_rate ranks.
    """
    ordered = ["EXCEPTIONAL", "HIGH", "MEDIUM", "LOW"]
    band_map = {m.band: m for m in band_metrics}
    rates = []
    for b in ordered:
        m = band_map.get(b)
        if m and m.win_rate is not None and m.closed_count > 0:
            rates.append((b, m.win_rate))

    if len(rates) < 2:
        return None, None

    # Spearman: rank the actual win rates (higher win_rate = rank 1)
    sorted_by_rate = sorted(rates, key=lambda x: x[1], reverse=True)
    actual_rank = {b: i + 1 for i, (b, _) in enumerate(sorted_by_rate)}
    expected_rank = {b: i + 1 for i, (b, _) in enumerate(rates)}

    n = len(rates)
    d_sq_sum = sum((expected_rank[b] - actual_rank[b]) ** 2 for b, _ in rates)
    rho = 1 - (6 * d_sq_sum) / (n * (n**2 - 1))
    is_calibrated = rho >= 0.6
    return is_calibrated, round(rho, 4)


# ── Regime breakdown ──────────────────────────────────────────────────────────

_REGIME_POSTURE_MAP = {
    "BULL_LOW_VOL": "risk_on",
    "BULL_HIGH_VOL": "neutral",
    "BEAR_LOW_VOL": "defensive",
    "BEAR_HIGH_VOL": "defensive",
}


def compute_regime_breakdown(rows: list[OutcomeRow]) -> list[RegimeMetricsDTO]:
    by_regime: dict[str, list[OutcomeRow]] = {}
    for r in rows:
        label = r.regime_label or "UNKNOWN"
        by_regime.setdefault(label, []).append(r)

    results: list[RegimeMetricsDTO] = []
    for label, regime_rows in sorted(by_regime.items()):
        closed = _closed(regime_rows)
        wins = [r for r in closed if r.outcome_status == "WIN"]
        alphas = [float(r.alpha_pct) for r in closed if r.alpha_pct is not None]
        returns = [float(r.pnl_pct) for r in closed if r.pnl_pct is not None]
        results.append(
            RegimeMetricsDTO(
                regime_label=label,
                regime_posture=_REGIME_POSTURE_MAP.get(label),
                recommendation_count=len(regime_rows),
                closed_count=len(closed),
                win_rate=_safe_div(len(wins), len(closed)),
                avg_alpha_pct=_safe_mean(alphas),
                avg_return_pct=_safe_mean(returns),
            )
        )
    return results


# ── Committee effectiveness ────────────────────────────────────────────────────

_ADVISORY_ORDER = ["supportive", "neutral", "cautious", "HIGH_CONCERN", "unknown"]


def compute_committee_breakdown(rows: list[OutcomeRow]) -> list[CommitteeAdvisoryMetricsDTO]:
    by_advisory: dict[str, list[OutcomeRow]] = {}
    for r in rows:
        adv = (r.committee_advisory or "unknown").lower()
        by_advisory.setdefault(adv, []).append(r)

    results: list[CommitteeAdvisoryMetricsDTO] = []
    for adv in _ADVISORY_ORDER + [a for a in by_advisory if a not in _ADVISORY_ORDER]:
        adv_rows = by_advisory.get(adv, [])
        if not adv_rows:
            continue
        closed = _closed(adv_rows)
        wins = [r for r in closed if r.outcome_status == "WIN"]
        alphas = [float(r.alpha_pct) for r in closed if r.alpha_pct is not None]

        # Agreement: advisory "supportive" → machine action BUY — we can only
        # approximate this from the outcome set (all outcomes here are for BUY
        # recommendations that were approved); supportive = agrees with BUY
        agreement = (
            1.0 if adv == "supportive" else (0.0 if adv in ("cautious", "high_concern") else None)
        )

        results.append(
            CommitteeAdvisoryMetricsDTO(
                advisory=adv,
                count=len(adv_rows),
                win_rate=_safe_div(len(wins), len(closed)),
                avg_alpha_pct=_safe_mean(alphas),
                agreement_with_machine=agreement,
            )
        )
    return results
