#!/usr/bin/env python3
"""Resume rebuild from validation onward after pruning stale ranking runs."""

from __future__ import annotations

import sys
from datetime import date

from scripts.run_full_rebuild_from_date import _build_daily_batch, parse_args
from app.schemas.daily_batch import DailyBatchPhaseFlags, DailyBatchRunCreateRequest


def main() -> int:
    request = DailyBatchRunCreateRequest(
        from_date=date(2024, 6, 1),
        force_from_date=False,
        force_recompute=False,
        holdout_start_date=date(2024, 6, 1),
        phases=DailyBatchPhaseFlags(
            ingest=False,
            rankings=False,
            validation=True,
            regime_history=True,
            regime_performance=True,
            factor_ic=True,
            research_intelligence=True,
            exit_research=True,
        ),
    )

    from app.db.session import get_session_factory

    Session = get_session_factory()
    with Session() as db:
        batch = _build_daily_batch(db)
        print("Resuming: validation + downstream quant phases only")
        response = batch.create_and_execute(request)
        print(f"status={response.status} phases={list((response.phases or {}).keys())}")
        if response.status != "completed":
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
