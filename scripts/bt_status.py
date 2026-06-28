#!/usr/bin/env python3
"""Quick backtest status — progress + P&L. Run anytime against the local (or any) db.

    uv run python scripts/bt_status.py
    LOG=/tmp/honest_breakout_v2.log uv run python scripts/bt_status.py   # also show ETA

Env: DATABASE_URL (default local), LOG (optional replay log to read ETA/active line).
"""
from __future__ import annotations

import os
from sqlalchemy import create_engine, text

DB = os.getenv("DATABASE_URL", "postgresql+psycopg://pipm:pipm@localhost:5432/pipm")
LOG = os.getenv("LOG", "/tmp/honest_breakout_v2.log")


def main() -> None:
    eng = create_engine(DB)

    def one(sql: str):
        with eng.connect() as c:
            return c.execute(text(sql)).first()

    def scalar(sql: str, default=0):
        try:
            with eng.connect() as c:
                v = c.execute(text(sql)).scalar()
            return v if v is not None else default
        except Exception:
            return default

    # ---- progress ----
    rk = one("SELECT count(distinct as_of_date), min(as_of_date), max(as_of_date) FROM ranking_runs")
    print("═" * 52)
    print(f"  RANKING   {rk[0] or 0} days   {rk[1]} → {rk[2]}")

    # ETA / active strategy from the log tail
    if os.path.exists(LOG):
        try:
            last = [ln for ln in open(LOG).read().splitlines() if "] " in ln and "completed" in ln]
            if last:
                print(f"  LOG       {last[-1].strip()[:78]}")
        except Exception:
            pass

    # ---- paper / P&L ----
    nav = one("SELECT count(*), min(as_of_date), max(as_of_date) FROM portfolio_nav_history")
    if not nav or not nav[0]:
        print("  PAPER     not started yet (warm-up)")
        print("═" * 52)
        return

    base = float(one("SELECT total_equity FROM portfolio_nav_history ORDER BY as_of_date ASC LIMIT 1")[0])
    cur = one("SELECT total_equity, cash_pct FROM portfolio_nav_history ORDER BY as_of_date DESC LIMIT 1")
    cur_nav, cash = float(cur[0]), float(cur[1] or 0)
    pnl = cur_nav - base
    days = (nav[2] - nav[1]).days
    yrs = days / 365.25 if days else 0
    cagr = ((cur_nav / base) ** (1 / yrs) - 1) * 100 if yrs > 0.05 and base > 0 else float("nan")

    # max drawdown
    dd = scalar("""WITH n AS (SELECT total_equity, max(total_equity) OVER (ORDER BY as_of_date) pk
                   FROM portfolio_nav_history)
                   SELECT round(min((total_equity-pk)/pk*100)::numeric,1) FROM n""")

    cl = one("""SELECT count(*), coalesce(sum(realized_pnl),0),
                round(100.0*count(*) FILTER (WHERE realized_pnl>0)/NULLIF(count(*),0),0)
                FROM portfolio_positions WHERE position_status='CLOSED' AND strategy_name<>'gold_rotation'""")
    op = scalar("SELECT count(*) FROM portfolio_positions WHERE position_status='OPEN'")

    print(f"  PAPER     {nav[0]} days   {nav[1]} → {nav[2]}  ({yrs:.2f}yr)")
    print("─" * 52)
    print(f"  NAV       ₹{cur_nav:,.0f}   (base ₹{base:,.0f})")
    print(f"  P&L       ₹{pnl:,.0f}   ({pnl/base*100:+.2f}%)")
    cagr_s = f"{cagr:+.1f}%/yr" if cagr == cagr else "n/a"
    print(f"  CAGR      {cagr_s}      maxDD {dd}%")
    print(f"  TRADES    {cl[0]} closed, win {cl[2]}%   |  {op} open, cash {cash*100:.0f}%")

    print("  EXITS    ", end="")
    with eng.connect() as c:
        rows = c.execute(text("""SELECT exit_reason, count(*),
            round(avg(realized_pnl/NULLIF(quantity*entry_price,0)*100)::numeric,1)
            FROM portfolio_positions WHERE position_status='CLOSED' AND strategy_name<>'gold_rotation'
            GROUP BY 1 ORDER BY 2 DESC""")).fetchall()
    print("  ".join(f"{r[0].replace('EXIT_','')}={r[1]}({r[2]}%)" for r in rows) or "—")
    print("═" * 52)


if __name__ == "__main__":
    main()
