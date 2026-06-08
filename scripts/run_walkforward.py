#!/usr/bin/env python3
"""Walk-Forward OOS Evaluation CLI.

Usage:
    uv run python scripts/run_walkforward.py
    uv run python scripts/run_walkforward.py --train-end 2023-12-31 --oos-start 2024-01-01
    uv run python scripts/run_walkforward.py --strategies breakout_v1 reversal_v1 --verbose
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--train-start", type=date.fromisoformat, default=date(2022, 1, 1))
    p.add_argument("--train-end",   type=date.fromisoformat, default=date(2023, 12, 31))
    p.add_argument("--oos-start",   type=date.fromisoformat, default=date(2024, 1, 1))
    p.add_argument("--oos-end",     type=date.fromisoformat, default=date(2026, 6, 5))
    p.add_argument("--strategies",  nargs="+",
                   default=["breakout_v1", "momentum_v1", "reversal_v1"])
    p.add_argument("--capital",     type=float, default=1_000_000)
    p.add_argument("--verbose",     action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    from app.replay.walkforward import WalkForwardEngine

    engine = WalkForwardEngine(
        train_start=args.train_start,
        train_end=args.train_end,
        oos_start=args.oos_start,
        oos_end=args.oos_end,
        strategies=args.strategies,
        initial_cash=args.capital,
        verbose=args.verbose,
    )

    result = engine.run()

    # Write summary to file
    summary_path = "docs/experiments/WF_OOS_SUMMARY.md"
    import pathlib
    pathlib.Path(summary_path).write_text(
        f"# Walk-Forward OOS Evaluation\n\n```\n{result.summary_table()}\n```\n"
    )
    print(f"\nSummary written to {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
