#!/usr/bin/env python3
"""
Pi-PM In-Memory Backtest — no DB writes, pure simulation.

Config:
  Capital     : ₹1,00,00,000
  Max slots   : 10 concurrent positions
  Max/slot    : ₹5,00,000
  Stop-loss   : -8% capped (exit at entry × 0.92)
  HITL        : false (auto-execute buys AND exits)
  Fees        : excluded
  Slippage    : 5 bps BUY / 5 bps SELL

Exit triggers (in priority order each day):
  1. Stop-loss   : EOD close ≤ entry × 0.92  → exit at entry × 0.92 (capped)
  2. Time-stop   : held > 30 trading days     → exit at EOD close
  3. Rank-drop   : current rank > 40          → exit at EOD close
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from uuid import UUID

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://pipm:pipm@localhost:5432/pipm")

# ── Config ────────────────────────────────────────────────────────────────────
INITIAL_CAPITAL   = 10_000_000.0   # ₹1 crore
MAX_SLOTS         = 10
MAX_SLOT_ALLOC    = 500_000.0      # ₹5 lakh per slot
STOP_LOSS_PCT     = -4.0           # -4%
STOP_LOSS_FACTOR  = 1.0 + (STOP_LOSS_PCT / 100)   # 0.96
MAX_HOLD_DAYS     = 30             # trading days
RANK_DROP_THRESH  = 40
SLIPPAGE_BPS      = 5.0
START_DATE        = "2022-06-01"
END_DATE          = "2026-06-07"
CONVICTION_MULT   = {"EXCEPTIONAL": 1.15, "HIGH": 1.00, "MEDIUM": 0.75}


@dataclass
class Position:
    stock_id:       str
    symbol:         str
    strategy:       str
    sector:         str
    entry_date:     date
    entry_price:    float
    qty:            float
    cost:           float          # qty × entry_price (no fees)
    conviction_band: str
    trading_days_held: int = 0


@dataclass
class Trade:
    symbol:         str
    strategy:       str
    entry_date:     date
    exit_date:      date
    entry_price:    float
    exit_price:     float
    qty:            float
    cost:           float
    pnl:            float
    pnl_pct:        float
    hold_days:      int
    exit_reason:    str
    conviction_band: str


def load_buy_signals(conn, start: str, end: str) -> dict[date, list[dict]]:
    """Load all BUY recommendation_results grouped by as_of_date."""
    rows = conn.execute(text(f"""
        SELECT
            rrun.as_of_date,
            rr.id::text,
            rr.stock_id::text,
            s.symbol,
            s.sector,
            rk.strategy_name,
            rr.rank,
            rr.conviction_score,
            rr.conviction_band
        FROM recommendation_results rr
        JOIN recommendation_runs rrun ON rr.recommendation_run_id = rrun.id
        JOIN ranking_runs rk          ON rrun.ranking_run_id = rk.id
        JOIN stocks s                 ON rr.stock_id = s.id
        WHERE rr.action = 'BUY'
          AND rrun.as_of_date >= '{start}'
          AND rrun.as_of_date <= '{end}'
        ORDER BY rrun.as_of_date, rr.conviction_score DESC, rr.rank
    """)).fetchall()

    signals: dict[date, list[dict]] = defaultdict(list)
    seen: set = set()
    for row in rows:
        key = (row[0], row[2])   # (date, stock_id) — dedup cross-strategy
        if key not in seen:
            seen.add(key)
            signals[row[0]].append({
                "stock_id": row[2], "symbol": row[3], "sector": row[4],
                "strategy": row[5], "rank": row[6],
                "conviction": row[7], "conviction_band": row[8],
            })
    return signals


def load_all_ranks(conn, start: str, end: str) -> dict[date, dict[str, int]]:
    """Best rank per stock per date (for rank-drop exit check)."""
    rows = conn.execute(text(f"""
        SELECT rrun.as_of_date, rr.stock_id::text, MIN(rr.rank)
        FROM recommendation_results rr
        JOIN recommendation_runs rrun ON rr.recommendation_run_id = rrun.id
        WHERE rrun.as_of_date >= '{start}' AND rrun.as_of_date <= '{end}'
          AND rr.rank IS NOT NULL
        GROUP BY rrun.as_of_date, rr.stock_id
    """)).fetchall()
    ranks: dict[date, dict[str, int]] = defaultdict(dict)
    for row in rows:
        ranks[row[0]][row[1]] = int(row[2])
    return ranks


def get_eod_close(conn, stock_id: str, as_of: date) -> float | None:
    row = conn.execute(text("""
        SELECT close FROM market_data
        WHERE stock_id = :sid AND date <= :d
        ORDER BY date DESC LIMIT 1
    """), {"sid": stock_id, "d": as_of}).fetchone()
    return float(row[0]) if row else None


def get_trading_days(conn, stock_id: str, entry: date, exit_d: date) -> int:
    row = conn.execute(text("""
        SELECT COUNT(*) FROM market_data
        WHERE stock_id = :sid AND date > :s AND date <= :e
    """), {"sid": stock_id, "s": entry, "e": exit_d}).fetchone()
    return int(row[0]) if row else 0


def slip(price: float, side: str) -> float:
    s = SLIPPAGE_BPS / 10_000
    return price * (1 + s) if side == "BUY" else price * (1 - s)


def run():
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        print("\n=== PI-PM IN-MEMORY BACKTEST ===")
        print(f"    Capital   : ₹{INITIAL_CAPITAL:,.0f}")
        print(f"    Slots     : {MAX_SLOTS}  |  Max/slot: ₹{MAX_SLOT_ALLOC:,.0f}")
        print(f"    Stop-loss : {STOP_LOSS_PCT}% capped")
        print(f"    HITL      : OFF (auto buy + exit)")
        print(f"    Period    : {START_DATE} → {END_DATE}\n")

        # ── Load data ─────────────────────────────────────────────────────────
        print("  Loading signals and ranks...")
        buy_signals = load_buy_signals(conn, START_DATE, END_DATE)
        all_ranks   = load_all_ranks(conn, START_DATE, END_DATE)

        trading_days = [
            row[0] for row in conn.execute(text(f"""
                SELECT DISTINCT date FROM market_data
                WHERE date >= '{START_DATE}' AND date <= '{END_DATE}'
                ORDER BY date
            """)).fetchall()
        ]
        print(f"  {len(trading_days)} trading days | "
              f"{sum(len(v) for v in buy_signals.values())} BUY signals\n")

        # ── Simulation ────────────────────────────────────────────────────────
        cash: float = INITIAL_CAPITAL
        positions: list[Position] = []
        trades:    list[Trade]    = []
        nav_curve: list[tuple[date, float]] = []
        monthly_nav: dict[str, float] = {}   # "YYYY-MM" → end-of-month NAV

        stop_exits = 0
        time_exits = 0
        rank_exits = 0
        day_num    = 0
        prev_month = ""

        for today in trading_days:
            day_num += 1
            exited_ids: set[str] = set()

            # ── 1. Update trading_days_held for open positions ─────────────────
            for pos in positions:
                pos.trading_days_held += 1

            # ── 2. Stop-loss (capped at -8%) ──────────────────────────────────
            for pos in list(positions):
                close = get_eod_close(conn, pos.stock_id, today)
                if close is None:
                    continue
                unreal_pct = (close - pos.entry_price) / pos.entry_price * 100
                if unreal_pct <= STOP_LOSS_PCT:
                    exit_price = round(pos.entry_price * STOP_LOSS_FACTOR, 4)
                    proceeds   = pos.qty * exit_price
                    pnl        = proceeds - pos.cost
                    trades.append(Trade(
                        symbol=pos.symbol, strategy=pos.strategy,
                        entry_date=pos.entry_date, exit_date=today,
                        entry_price=pos.entry_price, exit_price=exit_price,
                        qty=pos.qty, cost=pos.cost, pnl=pnl,
                        pnl_pct=pnl / pos.cost * 100,
                        hold_days=pos.trading_days_held,
                        exit_reason="STOP_LOSS",
                        conviction_band=pos.conviction_band,
                    ))
                    cash += proceeds
                    exited_ids.add(pos.stock_id)
                    stop_exits += 1

            positions = [p for p in positions if p.stock_id not in exited_ids]

            # ── 3. Time-stop (> 30 trading days) ──────────────────────────────
            for pos in list(positions):
                if pos.trading_days_held <= MAX_HOLD_DAYS:
                    continue
                close = get_eod_close(conn, pos.stock_id, today)
                if close is None:
                    continue
                exit_price = slip(close, "SELL")
                proceeds   = pos.qty * exit_price
                pnl        = proceeds - pos.cost
                trades.append(Trade(
                    symbol=pos.symbol, strategy=pos.strategy,
                    entry_date=pos.entry_date, exit_date=today,
                    entry_price=pos.entry_price, exit_price=exit_price,
                    qty=pos.qty, cost=pos.cost, pnl=pnl,
                    pnl_pct=pnl / pos.cost * 100,
                    hold_days=pos.trading_days_held,
                    exit_reason="TIME_STOP",
                    conviction_band=pos.conviction_band,
                ))
                cash += proceeds
                exited_ids.add(pos.stock_id)
                time_exits += 1

            positions = [p for p in positions if p.stock_id not in exited_ids]

            # ── 4. Rank-drop exit (rank > 40) ─────────────────────────────────
            today_ranks = all_ranks.get(today, {})
            for pos in list(positions):
                if pos.stock_id not in today_ranks:
                    continue
                if today_ranks[pos.stock_id] <= RANK_DROP_THRESH:
                    continue
                close = get_eod_close(conn, pos.stock_id, today)
                if close is None:
                    continue
                exit_price = slip(close, "SELL")
                proceeds   = pos.qty * exit_price
                pnl        = proceeds - pos.cost
                trades.append(Trade(
                    symbol=pos.symbol, strategy=pos.strategy,
                    entry_date=pos.entry_date, exit_date=today,
                    entry_price=pos.entry_price, exit_price=exit_price,
                    qty=pos.qty, cost=pos.cost, pnl=pnl,
                    pnl_pct=pnl / pos.cost * 100,
                    hold_days=pos.trading_days_held,
                    exit_reason="RANK_DROP",
                    conviction_band=pos.conviction_band,
                ))
                cash += proceeds
                exited_ids.add(pos.stock_id)
                rank_exits += 1

            positions = [p for p in positions if p.stock_id not in exited_ids]

            # ── 5. Entries ─────────────────────────────────────────────────────
            if today in buy_signals:
                open_ids   = {p.stock_id for p in positions}
                slots_free = MAX_SLOTS - len(positions)

                for sig in buy_signals[today]:
                    if slots_free <= 0:
                        break
                    if sig["stock_id"] in open_ids:
                        continue

                    close = get_eod_close(conn, sig["stock_id"], today)
                    if close is None:
                        continue
                    entry_price = slip(close, "BUY")

                    mult  = CONVICTION_MULT.get(sig["conviction_band"], 0.75)
                    alloc = min(MAX_SLOT_ALLOC * mult, cash * 0.95)
                    if alloc < entry_price:
                        continue

                    qty  = alloc / entry_price
                    cost = qty * entry_price

                    if cost > cash:
                        qty  = cash * 0.95 / entry_price
                        cost = qty * entry_price
                    if qty <= 0:
                        continue

                    cash -= cost
                    positions.append(Position(
                        stock_id=sig["stock_id"], symbol=sig["symbol"],
                        strategy=sig["strategy"], sector=sig["sector"],
                        entry_date=today, entry_price=entry_price,
                        qty=qty, cost=cost,
                        conviction_band=sig["conviction_band"],
                    ))
                    open_ids.add(sig["stock_id"])
                    slots_free -= 1

            # ── 6. Mark-to-market NAV ─────────────────────────────────────────
            mtm = cash
            for pos in positions:
                c2 = get_eod_close(conn, pos.stock_id, today)
                mtm += pos.qty * c2 if c2 else pos.cost
            nav_curve.append((today, mtm))

            # Track month-end NAV (last trading day of each month)
            ym = today.strftime("%Y-%m")
            monthly_nav[ym] = mtm   # overwrites each day → keeps last day of month

            if day_num % 250 == 0:
                print(f"  [{today}] {len(positions)} open | "
                      f"₹{cash:,.0f} cash | NAV ₹{mtm:,.0f} | "
                      f"stops={stop_exits} time={time_exits} rank={rank_exits}")

        # ── Force-close remaining at last price ───────────────────────────────
        last_day = trading_days[-1]
        for pos in positions:
            close = get_eod_close(conn, pos.stock_id, last_day)
            if not close:
                continue
            exit_price = slip(close, "SELL")
            proceeds   = pos.qty * exit_price
            pnl        = proceeds - pos.cost
            trades.append(Trade(
                symbol=pos.symbol, strategy=pos.strategy,
                entry_date=pos.entry_date, exit_date=last_day,
                entry_price=pos.entry_price, exit_price=exit_price,
                qty=pos.qty, cost=pos.cost, pnl=pnl,
                pnl_pct=pnl / pos.cost * 100,
                hold_days=pos.trading_days_held,
                exit_reason="FORCE_CLOSE",
                conviction_band=pos.conviction_band,
            ))
            cash += proceeds

        # ── Stats ─────────────────────────────────────────────────────────────
        final_nav   = cash
        total_pnl   = final_nav - INITIAL_CAPITAL
        total_ret   = total_pnl / INITIAL_CAPITAL * 100
        years       = (last_day - date(2022, 6, 1)).days / 365.25
        cagr        = ((final_nav / INITIAL_CAPITAL) ** (1 / years) - 1) * 100 if years > 0 else 0

        wins   = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]
        wr     = len(wins) / len(trades) * 100 if trades else 0
        aw     = sum(t.pnl_pct for t in wins)   / len(wins)   if wins   else 0
        al     = sum(t.pnl_pct for t in losses) / len(losses) if losses else 0
        gp     = sum(t.pnl for t in wins)
        gl     = abs(sum(t.pnl for t in losses))
        pf     = gp / gl if gl > 0 else 999.0

        peak = INITIAL_CAPITAL; max_dd = 0.0
        for _, nav in nav_curve:
            if nav > peak: peak = nav
            dd = (peak - nav) / peak * 100
            if dd > max_dd: max_dd = dd

        # Per-strategy
        strats: dict[str, dict] = {}
        for s in ["breakout_v1", "momentum_v1", "reversal_v1", "low_vol_v1"]:
            st = [t for t in trades if t.strategy == s]
            if not st: continue
            sw = [t for t in st if t.pnl > 0]
            sl = [t for t in st if t.pnl <= 0]
            ss = [t for t in st if t.exit_reason == "STOP_LOSS"]
            strats[s] = {
                "n": len(st), "wr": len(sw)/len(st)*100,
                "pnl": sum(t.pnl for t in st),
                "aw": sum(t.pnl_pct for t in sw)/len(sw) if sw else 0,
                "al": sum(t.pnl_pct for t in sl)/len(sl) if sl else 0,
                "pf": (sum(t.pnl for t in sw) / abs(sum(t.pnl for t in sl)))
                       if sl and sum(t.pnl for t in sl) != 0 else 99.0,
                "stops": len(ss),
            }

        # Exit reasons
        exit_counts: dict[str, int] = defaultdict(int)
        for t in trades:
            exit_counts[t.exit_reason] += 1

        yearly: dict[int, dict] = defaultdict(lambda: defaultdict(float))
        for t in trades:
            yearly[t.exit_date.year]["total"] += t.pnl
            yearly[t.exit_date.year][t.strategy] += t.pnl

        by_pct = sorted(trades, key=lambda t: t.pnl_pct)

        W = 72
        print("\n" + "=" * W)
        print("  PI-PM IN-MEMORY BACKTEST  |  Jun 2022 → Jun 2026")
        print(f"  ₹{INITIAL_CAPITAL:,.0f}  |  {MAX_SLOTS} slots  |  ₹{MAX_SLOT_ALLOC:,.0f}/slot  |  Stop {STOP_LOSS_PCT}%  |  No fees")
        print("=" * W)

        print(f"\n{'─'*W}")
        print("  PORTFOLIO OUTCOME")
        print(f"{'─'*W}")
        print(f"  Starting Capital  : ₹{INITIAL_CAPITAL:>14,.0f}")
        print(f"  Final NAV         : ₹{final_nav:>14,.0f}")
        print(f"  Total P&L         : ₹{total_pnl:>+14,.0f}")
        print(f"  Total Return      : {total_ret:>+12.2f}%")
        print(f"  CAGR              : {cagr:>+12.2f}%   ({years:.1f} yrs)")
        print(f"  Max Drawdown      : {max_dd:>12.2f}%")

        print(f"\n{'─'*W}")
        print("  TRADE STATISTICS")
        print(f"{'─'*W}")
        print(f"  Total Trades      : {len(trades):>6}  ({len(wins)}W / {len(losses)}L)")
        print(f"  Win Rate          : {wr:>+10.1f}%")
        print(f"  Avg Win           : {aw:>+10.2f}%")
        print(f"  Avg Loss          : {al:>+10.2f}%")
        print(f"  Profit Factor     : {pf:>10.2f}x")

        print(f"\n{'─'*W}")
        print("  EXIT BREAKDOWN")
        print(f"{'─'*W}")
        for reason, cnt in sorted(exit_counts.items(), key=lambda x: -x[1]):
            pct = cnt / len(trades) * 100 if trades else 0
            print(f"  {reason:<18}: {cnt:>5}  ({pct:.1f}%)")

        print(f"\n{'─'*W}")
        print("  PER-STRATEGY")
        print(f"{'─'*W}")
        print(f"  {'Strategy':<16} {'N':>5} {'Win%':>6} {'AvgW':>7} {'AvgL':>7} {'PF':>6} {'Stops':>6}  {'P&L':>14}")
        for s, v in strats.items():
            print(f"  {s:<16} {v['n']:>5} {v['wr']:>5.1f}% "
                  f"{v['aw']:>+6.1f}% {v['al']:>+6.1f}% "
                  f"{v['pf']:>6.2f} {v['stops']:>6}  ₹{v['pnl']:>+12,.0f}")

        print(f"\n{'─'*W}")
        print("  YEARLY P&L")
        print(f"{'─'*W}")
        for yr in sorted(yearly):
            tot = yearly[yr]["total"]
            bar = ("▲" if tot >= 0 else "▼") * min(int(abs(tot) / 100_000), 20)
            b = yearly[yr].get("breakout_v1", 0)
            m = yearly[yr].get("momentum_v1", 0)
            r = yearly[yr].get("reversal_v1", 0)
            lv= yearly[yr].get("low_vol_v1", 0)
            print(f"  {yr}  ₹{tot:>+12,.0f}  "
                  f"[B:{b:>+9,.0f} M:{m:>+9,.0f} R:{r:>+9,.0f} LV:{lv:>+9,.0f}]  {bar}")

        print(f"\n{'─'*W}")
        print("  TOP 5 BEST TRADES")
        print(f"{'─'*W}")
        for t in by_pct[-5:][::-1]:
            print(f"  {t.symbol:<20} {t.strategy:<14} "
                  f"{t.entry_date}→{t.exit_date}  "
                  f"{t.pnl_pct:>+7.2f}%  ₹{t.pnl:>+12,.0f}")

        print(f"\n{'─'*W}")
        print("  TOP 5 WORST TRADES")
        print(f"{'─'*W}")
        for t in by_pct[:5]:
            stop = " [STOP]" if t.exit_reason == "STOP_LOSS" else ""
            print(f"  {t.symbol:<20} {t.strategy:<14} "
                  f"{t.entry_date}→{t.exit_date}  "
                  f"{t.pnl_pct:>+7.2f}%  ₹{t.pnl:>+12,.0f}{stop}")

        # ── Monthly NAV & returns ─────────────────────────────────────────────
        print(f"\n{'─'*W}")
        print("  MONTHLY NAV & RETURNS")
        print(f"{'─'*W}")
        print(f"  {'Month':<10} {'NAV':>15} {'MoM ₹':>13} {'MoM%':>7}  {'Bar'}")
        print(f"  {'─'*10} {'─'*15} {'─'*13} {'─'*7}  {'─'*20}")
        sorted_months = sorted(monthly_nav.keys())
        prev_nav = INITIAL_CAPITAL
        for ym in sorted_months:
            nav = monthly_nav[ym]
            mom_pnl = nav - prev_nav
            mom_pct = mom_pnl / prev_nav * 100 if prev_nav > 0 else 0
            bar_len = min(int(abs(mom_pct) * 1.5), 20)
            bar = ("▲" if mom_pct >= 0 else "▼") * bar_len
            print(f"  {ym:<10} ₹{nav:>13,.0f} ₹{mom_pnl:>+11,.0f} {mom_pct:>+6.2f}%  {bar}")
            prev_nav = nav
        print()


if __name__ == "__main__":
    run()
