#!/usr/bin/env python3
"""
Backtest: reversal_v1 strategy — Jan 2022 to Jun 2026
Capital: ₹1,00,000

Rules:
  - Entry: BUY signal date (next open, approximated as that day's close)
  - Position sizing: equal weight across max 5 open positions
  - Exit: earliest of (a) EXIT_APPROVED signal, (b) 30-day time stop, (c) rank > 40
  - Max 5 concurrent positions (slots)
  - No short selling, no leverage
  - Transaction cost: 0.1% per side (brokerage + STT approximation)
  - Only reversal_v1 BUY signals
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

import psycopg

DB_URL = os.getenv("DATABASE_URL", "host=localhost port=5432 dbname=pipm user=pipm password=pipm")
CAPITAL = 100_000
MAX_SLOTS = 5
MAX_HOLDING_DAYS = 30
RANK_EXIT_THRESHOLD = 40
TXN_COST = 0.001  # 0.1% per side


@dataclass
class Position:
    symbol: str
    stock_id: str
    entry_date: date
    entry_price: float
    shares: int
    cost_basis: float  # total invested including costs
    rank_at_entry: int


@dataclass
class Trade:
    symbol: str
    entry_date: date
    exit_date: date
    entry_price: float
    exit_price: float
    shares: int
    pnl: float
    pnl_pct: float
    holding_days: int
    exit_reason: str


def load_buy_signals(cur) -> dict[date, list[dict]]:
    """Load all reversal_v1 BUY signals grouped by date."""
    cur.execute("""
        SELECT
            rrun.as_of_date,
            s.symbol,
            rr.stock_id::text,
            rr.rank,
            rr.conviction_score
        FROM recommendation_results rr
        JOIN recommendation_runs rrun ON rr.recommendation_run_id = rrun.id
        JOIN ranking_runs r ON rrun.ranking_run_id = r.id
        JOIN stocks s ON rr.stock_id = s.id
        WHERE r.strategy_name = 'reversal_v1'
          AND rr.action = 'BUY'
          AND rrun.as_of_date >= '2022-01-01'
        ORDER BY rrun.as_of_date, rr.rank
    """)
    signals: dict[date, list[dict]] = defaultdict(list)
    for row in cur.fetchall():
        signals[row[0]].append({
            "symbol": row[1],
            "stock_id": row[2],
            "rank": row[3],
            "conviction": row[4],
        })
    return signals


def load_exit_signals(cur) -> dict[date, set[str]]:
    """Load EXIT_APPROVED signals grouped by date → set of stock_ids."""
    cur.execute("""
        SELECT rrun.as_of_date, rr.stock_id::text
        FROM recommendation_results rr
        JOIN recommendation_runs rrun ON rr.recommendation_run_id = rrun.id
        JOIN ranking_runs r ON rrun.ranking_run_id = r.id
        WHERE r.strategy_name = 'reversal_v1'
          AND rr.action = 'EXIT_APPROVED'
          AND rrun.as_of_date >= '2022-01-01'
    """)
    exits: dict[date, set[str]] = defaultdict(set)
    for row in cur.fetchall():
        exits[row[0]].add(row[1])
    return exits


def load_rank_signals(cur) -> dict[date, dict[str, int]]:
    """Load all reversal_v1 rankings per date for rank-deterioration exit."""
    cur.execute("""
        SELECT rrun.as_of_date, rr.stock_id::text, rr.rank
        FROM recommendation_results rr
        JOIN recommendation_runs rrun ON rr.recommendation_run_id = rrun.id
        JOIN ranking_runs r ON rrun.ranking_run_id = r.id
        WHERE r.strategy_name = 'reversal_v1'
          AND rrun.as_of_date >= '2022-01-01'
          AND rr.rank IS NOT NULL
    """)
    ranks: dict[date, dict[str, int]] = defaultdict(dict)
    for row in cur.fetchall():
        ranks[row[0]][row[1]] = row[2]
    return ranks


def load_prices(cur, symbols: set[str]) -> dict[str, dict[date, float]]:
    """Load close prices for all symbols in backtest period."""
    if not symbols:
        return {}
    sym_list = list(symbols)
    cur.execute("""
        SELECT s.symbol, md.date, md.close
        FROM market_data md
        JOIN stocks s ON md.stock_id = s.id
        WHERE s.symbol = ANY(%s)
          AND md.date >= '2022-01-01'
        ORDER BY s.symbol, md.date
    """, (sym_list,))
    prices: dict[str, dict[date, float]] = defaultdict(dict)
    for row in cur.fetchall():
        prices[row[0]][row[1]] = float(row[2])
    return prices


def get_price_on_or_after(prices: dict[date, float], target: date) -> tuple[float, date] | None:
    """Get the first available price on or after target date."""
    for d in sorted(prices.keys()):
        if d >= target:
            return prices[d], d
    return None


def get_price_on_or_before(prices: dict[date, float], target: date) -> tuple[float, date] | None:
    """Get the last available price on or before target date."""
    result = None
    for d in sorted(prices.keys()):
        if d <= target:
            result = (prices[d], d)
        else:
            break
    return result


def get_trading_days_between(prices: dict[date, float], start: date, end: date) -> int:
    """Count trading days (days with price data) between two dates."""
    return sum(1 for d in prices if start <= d <= end)


def run_backtest():
    conn = psycopg.connect(DB_URL)
    cur = conn.cursor()

    print("Loading signals and price data...")
    buy_signals = load_buy_signals(cur)
    exit_signals = load_exit_signals(cur)
    rank_signals = load_rank_signals(cur)

    # Collect all symbols we need prices for
    all_symbols = set()
    for signals in buy_signals.values():
        for s in signals:
            all_symbols.add(s["symbol"])

    prices = load_prices(cur, all_symbols)
    conn.close()

    print(f"  {len(buy_signals)} signal dates, {len(all_symbols)} unique symbols")

    # ── Simulation ────────────────────────────────────────────────────────────
    capital = float(CAPITAL)
    cash = capital
    open_positions: list[Position] = []
    completed_trades: list[Trade] = []

    all_dates = sorted(set(list(buy_signals.keys()) + list(exit_signals.keys())))
    if not all_dates:
        print("No signal dates found!")
        return

    # Extend to cover exit dates for open positions
    sim_end = date(2026, 6, 5)
    sim_dates = sorted(set(
        d for sym_prices in prices.values() for d in sym_prices
        if d >= all_dates[0] and d <= sim_end
    ))

    portfolio_values: list[tuple[date, float]] = []

    for today in sim_dates:
        # ── 1. Check exits for open positions ─────────────────────────────
        still_open = []
        for pos in open_positions:
            sym_prices = prices.get(pos.symbol, {})
            price_info = get_price_on_or_before(sym_prices, today)
            current_price = price_info[0] if price_info else pos.entry_price

            holding_days = get_trading_days_between(sym_prices, pos.entry_date, today)

            # Determine exit reason
            exit_reason = None
            if pos.stock_id in exit_signals.get(today, set()):
                exit_reason = "EXIT_APPROVED"
            elif holding_days >= MAX_HOLDING_DAYS:
                exit_reason = "TIME_STOP_30D"
            elif rank_signals.get(today, {}).get(pos.stock_id, 0) > RANK_EXIT_THRESHOLD:
                exit_reason = "RANK_DETERIORATION"

            if exit_reason:
                exit_price_info = get_price_on_or_before(sym_prices, today)
                exit_price = exit_price_info[0] if exit_price_info else current_price
                exit_price_after_cost = exit_price * (1 - TXN_COST)

                proceeds = pos.shares * exit_price_after_cost
                pnl = proceeds - pos.cost_basis
                pnl_pct = pnl / pos.cost_basis * 100

                cash += proceeds
                completed_trades.append(Trade(
                    symbol=pos.symbol,
                    entry_date=pos.entry_date,
                    exit_date=today,
                    entry_price=pos.entry_price,
                    exit_price=exit_price,
                    shares=pos.shares,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                    holding_days=holding_days,
                    exit_reason=exit_reason,
                ))
            else:
                still_open.append(pos)

        open_positions = still_open

        # ── 2. Enter new positions from BUY signals ────────────────────────
        if today in buy_signals:
            open_symbols = {p.symbol for p in open_positions}
            slots_available = MAX_SLOTS - len(open_positions)

            for signal in buy_signals[today]:
                if slots_available <= 0:
                    break
                if signal["symbol"] in open_symbols:
                    continue  # already holding

                sym_prices = prices.get(signal["symbol"], {})
                price_info = get_price_on_or_after(sym_prices, today)
                if not price_info:
                    continue

                entry_price, actual_entry_date = price_info
                entry_price_with_cost = entry_price * (1 + TXN_COST)

                # Equal weight: allocate 1/MAX_SLOTS of total capital per position
                alloc = capital / MAX_SLOTS
                if alloc > cash:
                    alloc = cash
                if alloc < entry_price_with_cost:
                    continue  # can't afford even 1 share

                shares = int(alloc / entry_price_with_cost)
                if shares == 0:
                    continue

                cost_basis = shares * entry_price_with_cost
                cash -= cost_basis
                open_positions.append(Position(
                    symbol=signal["symbol"],
                    stock_id=signal["stock_id"],
                    entry_date=actual_entry_date,
                    entry_price=entry_price,
                    shares=shares,
                    cost_basis=cost_basis,
                    rank_at_entry=signal["rank"],
                ))
                open_symbols.add(signal["symbol"])
                slots_available -= 1

        # ── 3. Mark-to-market portfolio value ─────────────────────────────
        mtm = cash
        for pos in open_positions:
            sym_prices = prices.get(pos.symbol, {})
            price_info = get_price_on_or_before(sym_prices, today)
            if price_info:
                mtm += pos.shares * price_info[0]
            else:
                mtm += pos.cost_basis
        portfolio_values.append((today, mtm))

    # ── Force-close any remaining open positions at last price ────────────
    for pos in open_positions:
        sym_prices = prices.get(pos.symbol, {})
        price_info = get_price_on_or_before(sym_prices, sim_end)
        exit_price = price_info[0] if price_info else pos.entry_price
        exit_price_after_cost = exit_price * (1 - TXN_COST)
        proceeds = pos.shares * exit_price_after_cost
        pnl = proceeds - pos.cost_basis
        pnl_pct = pnl / pos.cost_basis * 100
        cash += proceeds
        holding_days = get_trading_days_between(sym_prices, pos.entry_date, sim_end)
        completed_trades.append(Trade(
            symbol=pos.symbol,
            entry_date=pos.entry_date,
            exit_date=sim_end,
            entry_price=pos.entry_price,
            exit_price=exit_price,
            shares=pos.shares,
            pnl=pnl,
            pnl_pct=pnl_pct,
            holding_days=holding_days,
            exit_reason="FORCE_CLOSE_END",
        ))

    # ── Results ───────────────────────────────────────────────────────────────
    final_value = cash + sum(
        pos.shares * (get_price_on_or_before(prices.get(pos.symbol, {}), sim_end) or (pos.entry_price, None))[0]
        for pos in open_positions
    )
    # Actually cash already includes all closed positions at this point
    final_value = cash

    total_pnl = final_value - CAPITAL
    total_return_pct = total_pnl / CAPITAL * 100
    years = (sim_end - all_dates[0]).days / 365.25
    cagr = ((final_value / CAPITAL) ** (1 / years) - 1) * 100 if years > 0 else 0

    wins = [t for t in completed_trades if t.pnl > 0]
    losses = [t for t in completed_trades if t.pnl <= 0]
    win_rate = len(wins) / len(completed_trades) * 100 if completed_trades else 0
    avg_win_pct = sum(t.pnl_pct for t in wins) / len(wins) if wins else 0
    avg_loss_pct = sum(t.pnl_pct for t in losses) / len(losses) if losses else 0
    profit_factor = (
        sum(t.pnl for t in wins) / abs(sum(t.pnl for t in losses))
        if losses and sum(t.pnl for t in losses) != 0 else float("inf")
    )
    avg_holding = sum(t.holding_days for t in completed_trades) / len(completed_trades) if completed_trades else 0

    # Max drawdown from portfolio values
    peak = CAPITAL
    max_dd = 0.0
    for _, val in portfolio_values:
        if val > peak:
            peak = val
        dd = (peak - val) / peak * 100
        if dd > max_dd:
            max_dd = dd

    # Exit reason breakdown
    exit_reasons: dict[str, int] = defaultdict(int)
    for t in completed_trades:
        exit_reasons[t.exit_reason] += 1

    # Best and worst trades
    sorted_trades = sorted(completed_trades, key=lambda t: t.pnl_pct)
    worst5 = sorted_trades[:5]
    best5 = sorted_trades[-5:][::-1]

    # Yearly P&L
    yearly: dict[int, float] = defaultdict(float)
    for t in completed_trades:
        yearly[t.exit_date.year] += t.pnl

    print("\n" + "=" * 60)
    print("  REVERSAL_V1 BACKTEST — Jan 2022 to Jun 2026")
    print("  Capital: ₹1,00,000  |  Max 5 slots  |  30-day time stop")
    print("=" * 60)

    print(f"\n{'─'*40}")
    print("  PORTFOLIO SUMMARY")
    print(f"{'─'*40}")
    print(f"  Starting Capital  : ₹{CAPITAL:>10,.0f}")
    print(f"  Final Value       : ₹{final_value:>10,.0f}")
    print(f"  Total P&L         : ₹{total_pnl:>+10,.0f}")
    print(f"  Total Return      : {total_return_pct:>+8.1f}%")
    print(f"  CAGR              : {cagr:>+8.1f}%  ({years:.1f} years)")
    print(f"  Max Drawdown      : {max_dd:>8.1f}%")

    print(f"\n{'─'*40}")
    print("  TRADE STATISTICS")
    print(f"{'─'*40}")
    print(f"  Total Trades      : {len(completed_trades):>6}")
    print(f"  Win Rate          : {win_rate:>7.1f}%  ({len(wins)}W / {len(losses)}L)")
    print(f"  Avg Win           : {avg_win_pct:>+7.1f}%")
    print(f"  Avg Loss          : {avg_loss_pct:>+7.1f}%")
    print(f"  Profit Factor     : {profit_factor:>7.2f}x")
    print(f"  Avg Holding Days  : {avg_holding:>7.1f}  (trading days)")

    print(f"\n{'─'*40}")
    print("  EXIT REASONS")
    print(f"{'─'*40}")
    for reason, count in sorted(exit_reasons.items(), key=lambda x: -x[1]):
        print(f"  {reason:<25}: {count:>4}")

    print(f"\n{'─'*40}")
    print("  YEARLY P&L")
    print(f"{'─'*40}")
    for yr in sorted(yearly):
        bar = "█" * int(abs(yearly[yr]) / 1000)
        sign = "+" if yearly[yr] >= 0 else ""
        print(f"  {yr}  ₹{sign}{yearly[yr]:>+8,.0f}  {bar}")

    print(f"\n{'─'*40}")
    print("  TOP 5 BEST TRADES")
    print(f"{'─'*40}")
    for t in best5:
        print(f"  {t.symbol:<18} {t.entry_date} → {t.exit_date}  {t.pnl_pct:>+6.1f}%  ₹{t.pnl:>+7,.0f}  [{t.exit_reason}]")

    print(f"\n{'─'*40}")
    print("  TOP 5 WORST TRADES")
    print(f"{'─'*40}")
    for t in worst5:
        print(f"  {t.symbol:<18} {t.entry_date} → {t.exit_date}  {t.pnl_pct:>+6.1f}%  ₹{t.pnl:>+7,.0f}  [{t.exit_reason}]")

    print(f"\n{'─'*40}")
    print("  NIFTY 500 BENCHMARK (approx)")
    print(f"{'─'*40}")
    # NIFTY 500 Jan 2022 ~17,500  Jun 2026 ~estimate — use market_data for NIFTY
    print("  (compare against ~12-15% CAGR for NIFTY 500 over same period)")
    print()


if __name__ == "__main__":
    run_backtest()
