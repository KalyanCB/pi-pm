#!/usr/bin/env bash
# poll_rankings.sh — Monitor ranking run progress across year windows
# Usage: ./scripts/poll_rankings.sh [interval_seconds]
# Example: ./scripts/poll_rankings.sh 30
#
# Polls every N seconds (default 30), clears screen each cycle.
# Exits automatically when all windows are complete.
# Zero Claude tokens — runs entirely locally.

set -e

INTERVAL=${1:-30}
DB_URL="${DATABASE_URL:-postgresql+psycopg://pipm:pipm@localhost:5432/pipm}"

PYTHON=$(find "$(dirname "$0")/../.venv/bin" -name "python*" | head -1)
if [ -z "$PYTHON" ]; then
  PYTHON=python3
fi

$PYTHON - "$DB_URL" "$INTERVAL" <<'PYEOF'
import sys
import time
from datetime import datetime
from sqlalchemy import create_engine, text

db_url   = sys.argv[1]
interval = int(sys.argv[2])

engine = create_engine(db_url)

WINDOWS = [
    ("A", "2021-06-05", "2022-06-04"),
    ("B", "2022-06-05", "2023-06-04"),
    ("C", "2023-06-05", "2024-06-04"),
    ("D", "2024-06-05", "2025-06-04"),
    ("E", "2025-05-05", "2026-06-05"),
]

def bar(pct, width=20):
    filled = int(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)

cycle = 0
while True:
    cycle += 1
    print("\033[H\033[J", end="")   # clear screen
    print(f"Pi-PM Ranking Status  [{datetime.now().strftime('%H:%M:%S')}]  poll #{cycle}  (Ctrl+C to stop)\n")

    all_done = True
    total_runs = 0

    with engine.connect() as conn:
        for label, from_d, to_d in WINDOWS:
            runs = conn.execute(text("""
                SELECT COUNT(*) FROM ranking_runs
                WHERE as_of_date BETWEEN :f AND :t AND status = 'completed'
            """), {"f": from_d, "t": to_d}).scalar()

            expected_days = conn.execute(text("""
                SELECT COUNT(DISTINCT date) FROM market_data
                WHERE date BETWEEN :f AND :t
            """), {"f": from_d, "t": to_d}).scalar()

            expected_runs = expected_days * 2
            pct = round(runs / expected_runs * 100, 1) if expected_runs else 0.0
            done = runs >= expected_runs
            icon = "✅" if done else "🔄"
            total_runs += runs
            if not done:
                all_done = False

            print(f"  Year {label}  {from_d} → {to_d}")
            print(f"         [{bar(pct)}] {pct:5.1f}%  {runs}/{expected_runs}  {icon}")
            print()

        print(f"  Total ranking_runs completed: {total_runs}")

    if all_done:
        print("\n  🎉 ALL YEARS COMPLETE! Rankings done.\n")
        sys.exit(0)

    print(f"\n  Next check in {interval}s...")
    time.sleep(interval)
PYEOF
