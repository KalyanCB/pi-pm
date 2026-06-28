#!/usr/bin/env python3
"""Compute the lifecycle signals per stock per day — rank the strategies the
regime-aware lifecycle needs:

    breakout_v2   B2  — coil / breakout ENTRY
    breakout_v1   B1  — active break, the EXIT handoff for breakout
    momentum_v3   M3  — 12-month durable trend
    reversion_v3  R1  — fresh-washout, the reversion EARLY ENTRY (precedes reversal_v1)
    reversal_v1   RV1 — chronic oversold, the reversion EXIT handoff

Ranking-only (no recommendations, no paper). Each strategy's rank in ranking_results
IS the cross-sectional signal (percentile = rank / run_size). Reuses the daily-batch
ranking machinery + its dedup (force_recompute=False skips already-ranked days), so it
is idempotent and safe to re-run.

Usage:
    # back-compute a historical range
    uv run python scripts/compute_lifecycle_signals.py --from 2019-01-01 --to 2026-06-30
    # daily batch (one day; cron-friendly)
    uv run python scripts/compute_lifecycle_signals.py --day today
    uv run python scripts/compute_lifecycle_signals.py --day 2026-06-25

Env: MARKET_DATA_PROVIDER=kite, REGIME_DYNAMIC_STOPS_ENABLED=true (as the batch expects).
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date

sys.path.insert(0, ".")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # so `import replay_fast` works

os.environ.setdefault("MARKET_DATA_PROVIDER", "kite")

import replay_fast as rf  # noqa: E402  reuse _build_batch_service/_base_request/_spec/deps
from app.schemas.daily_batch import DailyBatchPhaseFlags  # noqa: E402

# The five strategies the lifecycle reads. breakout_v1/reversal_v1 already exist; the
# rest are the committed v2/v3 set. Keep in sync with the lifecycle routing/exit.
LIFECYCLE_STRATEGIES: list[str] = [
    "breakout_v2",
    "breakout_v1",
    "momentum_v3",
    "reversion_v3",
    "reversal_v1",
]

# Ranking-only: compute & store the regime + rank the strategies; no recs, no portfolio.
_PHASES = DailyBatchPhaseFlags(
    ingest=False,
    rankings=True,
    validation=False,          # set True to also compute forward-IC per strategy
    recommendations=False,
    regime_history=True,        # persists market_regime_3way for the day
    regime_performance=False,
    factor_ic=False,
    research_intelligence=False,
    exit_research=False,
    portfolio=False,
)


def compute_day(day: date) -> str:
    db = rf.get_session_factory()()
    try:
        # Regime first (also persists the 3-way market_regime_3way for this day).
        rf.RegimeAnalyticsService(
            db,
            rf.get_settings(),
            rf.RegimeAnalyticsRepository(db),
            rf.StockRepository(db),
            rf.MarketDataRepository(db),
        ).compute_and_store_regime(as_of_date=day, benchmark_symbol=rf.BENCHMARK)
        db.commit()

        batch = rf._build_batch_service(db)
        request = rf._base_request(
            day, [rf._spec(s) for s in LIFECYCLE_STRATEGIES], _PHASES
        )
        resp = batch.create_and_execute(request)
        return resp.status
    finally:
        db.close()


def _trading_days(frm: date, to: date) -> list[date]:
    db = rf.get_session_factory()()
    try:
        bench = rf.StockRepository(db).get_by_symbol(rf.BENCHMARK)
        days = rf.MarketDataRepository(db).list_distinct_trading_dates(
            [bench.id], start_date=frm, end_date=to, source="kite"
        )
        return sorted(days)
    finally:
        db.close()


def main() -> int:
    ap = argparse.ArgumentParser(description="Compute lifecycle strategy signals.")
    ap.add_argument("--from", dest="frm", help="back-compute range start (YYYY-MM-DD)")
    ap.add_argument("--to", dest="to", help="back-compute range end (YYYY-MM-DD)")
    ap.add_argument("--day", help="single day (YYYY-MM-DD or 'today') — daily batch")
    args = ap.parse_args()

    if args.day:
        days = [date.today() if args.day == "today" else date.fromisoformat(args.day)]
    elif args.frm and args.to:
        days = _trading_days(date.fromisoformat(args.frm), date.fromisoformat(args.to))
    else:
        ap.error("provide --day, or both --from and --to")
        return 2

    print(f"lifecycle signals: {len(days)} day(s) x {LIFECYCLE_STRATEGIES}")
    for i, d in enumerate(days):
        status = compute_day(d)
        if i % 20 == 0 or i == len(days) - 1:
            print(f"  [{i + 1}/{len(days)}] {d} -> {status}")
    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
