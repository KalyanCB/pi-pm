"""Portfolio attribution — where did returns come from?

Break down by: strategy, conviction band, regime, sector, holding duration, committee advisory.
Pure functions. Deterministic. No LLM.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AttributionBucket:
    label: str
    count: int
    total_return_pct: float | None
    avg_return_pct: float | None
    avg_alpha_pct: float | None
    win_rate: float | None
    contribution_pct: float | None  # bucket return × position weight contribution


@dataclass
class AttributionReport:
    by_strategy: list[AttributionBucket]
    by_conviction_band: list[AttributionBucket]
    by_regime: list[AttributionBucket]
    by_sector: list[AttributionBucket]
    by_holding_duration: list[AttributionBucket]
    by_committee_advisory: list[AttributionBucket]
    total_alpha_pct: float | None
    note: str


def _bucket(
    rows: list[dict],
    key: str,
    buckets: list[str] | None = None,
) -> list[AttributionBucket]:
    groups: dict[str, list[dict]] = {}
    for row in rows:
        label = str(row.get(key) or "Unknown")
        groups.setdefault(label, []).append(row)

    order = buckets or sorted(groups.keys())
    result = []
    for label in order:
        group_rows = groups.get(label, [])
        if not group_rows:
            continue
        closed = [r for r in group_rows if r.get("outcome_status") in ("WIN", "LOSS", "BREAKEVEN")]
        wins = [r for r in closed if r.get("outcome_status") == "WIN"]
        alphas = [r["alpha_pct"] for r in closed if r.get("alpha_pct") is not None]
        pnls = [r["pnl_pct"] for r in closed if r.get("pnl_pct") is not None]

        result.append(
            AttributionBucket(
                label=label,
                count=len(group_rows),
                total_return_pct=round(sum(pnls), 4) if pnls else None,
                avg_return_pct=round(sum(pnls) / len(pnls), 4) if pnls else None,
                avg_alpha_pct=round(sum(alphas) / len(alphas), 4) if alphas else None,
                win_rate=round(len(wins) / len(closed) * 100, 2) if closed else None,
                contribution_pct=round(sum(alphas), 4) if alphas else None,
            )
        )
    return result


def _duration_bucket(days_held: int | None) -> str:
    if days_held is None:
        return "Unknown"
    if days_held <= 5:
        return "1–5 days"
    if days_held <= 10:
        return "6–10 days"
    if days_held <= 20:
        return "11–20 days"
    return "21+ days"


def compute_attribution(outcomes: list[dict]) -> AttributionReport:
    """
    outcomes: list of dicts with keys:
      strategy_name, conviction_band, regime_label, sector, days_held,
      committee_advisory, pnl_pct, alpha_pct, outcome_status
    """
    # Add duration bucket to each row
    augmented = [{**row, "_duration": _duration_bucket(row.get("days_held"))} for row in outcomes]

    all_alphas = [r["alpha_pct"] for r in outcomes if r.get("alpha_pct") is not None]
    total_alpha = round(sum(all_alphas), 4) if all_alphas else None

    return AttributionReport(
        by_strategy=_bucket(augmented, "strategy_name", ["momentum_v1", "breakout_v1"]),
        by_conviction_band=_bucket(
            augmented, "conviction_band", ["EXCEPTIONAL", "HIGH", "MEDIUM", "LOW"]
        ),
        by_regime=_bucket(augmented, "regime_label"),
        by_sector=_bucket(augmented, "sector"),
        by_holding_duration=_bucket(
            augmented, "_duration", ["1–5 days", "6–10 days", "11–20 days", "21+ days"]
        ),
        by_committee_advisory=_bucket(
            augmented,
            "committee_advisory",
            ["supportive", "neutral", "cautious", "HIGH_CONCERN", "Unknown"],
        ),
        total_alpha_pct=total_alpha,
        note="Attribution is post-hoc observation only. Committee advisory measured for signal value — not used in recommendation generation.",
    )
