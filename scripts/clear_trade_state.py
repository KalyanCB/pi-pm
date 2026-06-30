"""Clear paper-trade state for a fresh replay — DELETE-safe (never TRUNCATE CASCADE
portfolio_positions; that wipes recommendation_results via the SET-NULL FK as a cascade).

Deletes child->parent in FK order, clears the approval/idempotency tables (re-approving
the same recs over stale rows fails on the idempotency key), and KEEPS portfolio_configs
so the engine reseeds initial capital via nav_service.ensure_initial_capital on day 1.
Leaves market_data, rankings, recommendation_results untouched.
"""
from __future__ import annotations

from sqlalchemy import text

from app.db.session import get_session_factory

# child -> parent; portfolio_configs intentionally preserved
ORDER = [
    "execution_orders",                  # FK -> recommendation_approvals
    "recommendation_approvals",          # idempotency-key table
    "portfolio_exit_recommendations",    # FK -> portfolio_positions
    "portfolio_nav_history",
    "portfolio_cash_ledger",
    "portfolio_reconciliation_reports",
    "paper_trades",                      # FK -> portfolio_positions
    "portfolio_positions",               # recommendation_results.portfolio_position_id -> SET NULL
]


def main() -> int:
    db = get_session_factory()()
    try:
        for tbl in ORDER:
            n = db.execute(text(f"DELETE FROM {tbl}")).rowcount
            print(f"  cleared {tbl:<34} {n:>7} rows")
        db.commit()
        kept = db.scalar(text("SELECT count(*) FROM portfolio_configs"))
        print(f"  kept    portfolio_configs                  {kept:>7} rows")
        print("trade state cleared (DELETE-safe).")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
