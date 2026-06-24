#!/usr/bin/env python
"""Replay status dashboard — run anytime during or after replay."""
from __future__ import annotations

import os
import subprocess
from sqlalchemy import text
from app.db.session import get_session_factory

INITIAL_EQUITY = 10_000_000
LOG_FILE = "logs/replay_2021_v17.log"
TOTAL_DAYS = 1348


def main() -> None:
    db = get_session_factory()()

    # ── Replay progress ───────────────────────────────────────────────────────
    progress = db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE status = 'completed') AS completed,
            MAX(target_trading_day) FILTER (WHERE status = 'completed') AS latest_date,
            COUNT(*) FILTER (WHERE status = 'failed') AS failed
        FROM daily_batch_runs
    """)).fetchone()

    pct = progress.completed / TOTAL_DAYS * 100 if TOTAL_DAYS else 0

    print("=" * 60)
    print("  REPLAY STATUS")
    print("=" * 60)
    print(f"  Completed days : {progress.completed} / {TOTAL_DAYS}  ({pct:.1f}%)")
    print(f"  Latest date    : {progress.latest_date}")
    print(f"  Failed days    : {progress.failed}")

    # ── Current regime — scoped to replay progress ────────────────────────────
    regime = db.execute(text("""
        SELECT rh.as_of_date, rh.regime_label, rh.trend_regime, rh.vol_regime
        FROM regime_history rh
        WHERE rh.as_of_date <= (
            SELECT COALESCE(MAX(target_trading_day), '2021-01-01')
            FROM daily_batch_runs WHERE status = 'completed'
        )
        ORDER BY rh.as_of_date DESC LIMIT 1
    """)).fetchone()

    print()
    print("  REGIME (at replay date)")
    print("-" * 60)
    if regime:
        print(f"  Date    : {regime.as_of_date}")
        print(f"  Label   : {regime.regime_label}")
        print(f"  Trend   : {regime.trend_regime}   Vol: {regime.vol_regime}")
    else:
        print("  No regime data yet")

    # ── Portfolio NAV ─────────────────────────────────────────────────────────
    nav = db.execute(text("""
        SELECT as_of_date, total_equity, cash_balance, market_value,
               realized_pnl_cumulative, unrealized_pnl, open_positions
        FROM portfolio_nav_history
        ORDER BY as_of_date DESC LIMIT 1
    """)).fetchone()

    print()
    print("  PORTFOLIO NAV")
    print("-" * 60)
    if nav:
        equity = float(nav.total_equity)
        ret = (equity - INITIAL_EQUITY) / INITIAL_EQUITY * 100
        print(f"  As of          : {nav.as_of_date}")
        print(f"  Total equity   : {equity:>14,.0f}  ({ret:+.2f}%)")
        print(f"  Cash           : {float(nav.cash_balance):>14,.0f}")
        print(f"  Market value   : {float(nav.market_value or 0):>14,.0f}")
        print(f"  Realized PnL   : {float(nav.realized_pnl_cumulative or 0):>14,.0f}")
        print(f"  Unrealized PnL : {float(nav.unrealized_pnl or 0):>14,.0f}")
        print(f"  Open positions : {nav.open_positions}")
    else:
        print("  No NAV data yet")

    # ── Open positions ────────────────────────────────────────────────────────
    positions = db.execute(text("""
        SELECT s.symbol, pp.entry_date, pp.avg_cost, pp.quantity,
               pp.unrealized_pnl, pp.strategy_name, pp.market_value
        FROM portfolio_positions pp
        JOIN stocks s ON s.id = pp.stock_id
        WHERE pp.is_current = true AND pp.position_status = 'OPEN'
        ORDER BY pp.entry_date
    """)).fetchall()

    print()
    print(f"  OPEN POSITIONS ({len(positions)})")
    print("-" * 60)
    if positions:
        for p in positions:
            avg_cost = float(p.avg_cost or 0)
            qty = float(p.quantity or 1)
            cost_basis = avg_cost * qty
            pnl_pct = float(p.unrealized_pnl or 0) / cost_basis * 100 if cost_basis else 0
            mv = float(p.market_value or 0)
            cur_price = mv / qty if qty else 0
            print(f"  {p.symbol:<22}  entry={p.entry_date}  avg={avg_cost:.1f}"
                  f"  cur={cur_price:.1f}  pnl={pnl_pct:+.1f}%  [{p.strategy_name}]")
    else:
        print("  No open positions")

    # ── Closed trade stats ────────────────────────────────────────────────────
    stats = db.execute(text("""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE exit_price > entry_price) AS wins,
            COUNT(*) FILTER (WHERE exit_price <= entry_price) AS losses,
            SUM(realized_pnl) AS total_pnl,
            AVG(CASE WHEN exit_price > entry_price
                THEN (exit_price - entry_price) / entry_price * 100 END) AS avg_win_pct,
            AVG(CASE WHEN exit_price <= entry_price
                THEN (exit_price - entry_price) / entry_price * 100 END) AS avg_loss_pct,
            AVG(exit_date - entry_date) FILTER (WHERE exit_date IS NOT NULL) AS avg_hold_days
        FROM portfolio_positions
        WHERE position_status = 'CLOSED'
          AND exit_price IS NOT NULL AND entry_price IS NOT NULL
    """)).fetchone()

    print()
    print("  CLOSED TRADE STATS")
    print("-" * 60)
    if stats and stats.total:
        win_rate = stats.wins / stats.total * 100 if stats.total else 0
        avg_win = float(stats.avg_win_pct or 0)
        avg_loss = float(stats.avg_loss_pct or 0)
        pf = abs(avg_win / avg_loss) if avg_loss else 0
        print(f"  Total trades   : {stats.total}  (wins={stats.wins}  losses={stats.losses})")
        print(f"  Win rate       : {win_rate:.1f}%")
        print(f"  Total PnL      : {float(stats.total_pnl or 0):>14,.0f}")
        print(f"  Avg win        : {avg_win:+.2f}%")
        print(f"  Avg loss       : {avg_loss:+.2f}%")
        print(f"  Profit factor  : {pf:.2f}x")
        print(f"  Avg hold       : {float(stats.avg_hold_days or 0):.1f} days")
    else:
        print("  No closed trades yet")

    # ── Strategy mix ──────────────────────────────────────────────────────────
    mix = db.execute(text("""
        SELECT strategy_name, COUNT(*) as trades,
               COUNT(*) FILTER (WHERE exit_price > entry_price) as wins
        FROM portfolio_positions
        WHERE position_status = 'CLOSED' AND exit_price IS NOT NULL
        GROUP BY strategy_name ORDER BY trades DESC
    """)).fetchall()

    if mix:
        print()
        print("  STRATEGY MIX (closed)")
        print("-" * 60)
        for m in mix:
            wr = m.wins / m.trades * 100 if m.trades else 0
            print(f"  {m.strategy_name:<20}  {m.trades:>4} trades  {wr:.0f}% win")

    # ── Log tail ──────────────────────────────────────────────────────────────
    for log in [LOG_FILE, "logs/replay_2021_v5.log", "logs/replay_2021_v4.log"]:
        if os.path.exists(log):
            tail = subprocess.check_output(["tail", "-5", log]).decode().strip()
            print()
            print(f"  REPLAY LOG ({log})")
            print("-" * 60)
            for line in tail.splitlines():
                print(f"  {line}")
            break

    print("=" * 60)
    db.close()


if __name__ == "__main__":
    main()
