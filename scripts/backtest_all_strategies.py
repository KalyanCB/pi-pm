#!/usr/bin/env python3
"""
Pi-PM Multi-Strategy Backtest — Simulating live trading from Jan 2022.

Capital allocation design (mirrors live system intent):
  - Total capital: ₹1,00,000
  - BULL regime  : breakout_v1 + momentum_v1 share 5 slots (combined pool)
  - BEAR_LOW_VOL : reversal_v1 gets all 5 slots
  - BEAR_HIGH_VOL / BULL_HIGH_VOL : no active strategy → idle in cash
  - Cross-strategy dedup: if same stock appears in multiple strategies,
    keep highest conviction (mirrors live dedup logic)

Exit rules (per strategy):
  - EXIT_APPROVED signal in recommendation_results
  - 30-day time stop (trading days)
  - Rank > 40 deterioration
  - Regime flip: if strategy's regime no longer active, exit all its positions

Transaction costs: 0.1% per side (brokerage + STT)
"""
from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

import psycopg

DB_URL = os.getenv("DATABASE_URL", "host=localhost port=5432 dbname=pipm user=pipm password=pipm")
CAPITAL = 100_000
MAX_SLOTS = 5
MAX_HOLDING_DAYS = 30
RANK_EXIT_THRESHOLD = 40
TXN_COST = 0.001


@dataclass
class Position:
    symbol: str
    stock_id: str
    strategy: str
    entry_date: date
    entry_price: float
    shares: int
    cost_basis: float
    rank_at_entry: int
    conviction: int


@dataclass
class Trade:
    symbol: str
    strategy: str
    entry_date: date
    exit_date: date
    entry_price: float
    exit_price: float
    shares: int
    pnl: float
    pnl_pct: float
    holding_days: int
    exit_reason: str
    conviction: int


def load_buy_signals(cur) -> dict[date, list[dict]]:
    cur.execute("""
        SELECT rrun.as_of_date, s.symbol, rr.stock_id::text,
               r.strategy_name, rr.rank, rr.conviction_score
        FROM recommendation_results rr
        JOIN recommendation_runs rrun ON rr.recommendation_run_id = rrun.id
        JOIN ranking_runs r ON rrun.ranking_run_id = r.id
        JOIN stocks s ON rr.stock_id = s.id
        WHERE rr.action = 'BUY' AND rrun.as_of_date >= '2022-01-01'
        ORDER BY rrun.as_of_date, rr.conviction_score DESC, rr.rank
    """)
    signals: dict[date, list[dict]] = defaultdict(list)
    for row in cur.fetchall():
        signals[row[0]].append({
            "symbol": row[1], "stock_id": row[2],
            "strategy": row[3], "rank": row[4], "conviction": row[5],
        })
    return signals


def load_exit_signals(cur) -> dict[date, set[str]]:
    cur.execute("""
        SELECT rrun.as_of_date, rr.stock_id::text
        FROM recommendation_results rr
        JOIN recommendation_runs rrun ON rr.recommendation_run_id = rrun.id
        WHERE rr.action = 'EXIT_APPROVED' AND rrun.as_of_date >= '2022-01-01'
    """)
    exits: dict[date, set[str]] = defaultdict(set)
    for row in cur.fetchall():
        exits[row[0]].add(row[1])
    return exits


def load_all_ranks(cur) -> dict[date, dict[str, int]]:
    """All ranks across all strategies — used for deterioration exit."""
    cur.execute("""
        SELECT rrun.as_of_date, rr.stock_id::text, MIN(rr.rank) as best_rank
        FROM recommendation_results rr
        JOIN recommendation_runs rrun ON rr.recommendation_run_id = rrun.id
        WHERE rrun.as_of_date >= '2022-01-01' AND rr.rank IS NOT NULL
        GROUP BY rrun.as_of_date, rr.stock_id
    """)
    ranks: dict[date, dict[str, int]] = defaultdict(dict)
    for row in cur.fetchall():
        ranks[row[0]][row[1]] = row[2]
    return ranks


def load_active_strategy_dates(cur) -> dict[date, set[str]]:
    """Which strategies had BUY signals on each date (proxy for regime)."""
    cur.execute("""
        SELECT DISTINCT rrun.as_of_date, r.strategy_name
        FROM recommendation_runs rrun
        JOIN ranking_runs r ON rrun.ranking_run_id = r.id
        WHERE rrun.as_of_date >= '2022-01-01'
    """)
    active: dict[date, set[str]] = defaultdict(set)
    for row in cur.fetchall():
        active[row[0]].add(row[1])
    return active


def load_prices(cur, symbols: set[str]) -> dict[str, dict[date, float]]:
    if not symbols:
        return {}
    cur.execute("""
        SELECT s.symbol, md.date, md.close
        FROM market_data md
        JOIN stocks s ON md.stock_id = s.id
        WHERE s.symbol = ANY(%s) AND md.date >= '2022-01-01'
        ORDER BY s.symbol, md.date
    """, (list(symbols),))
    prices: dict[str, dict[date, float]] = defaultdict(dict)
    for row in cur.fetchall():
        prices[row[0]][row[1]] = float(row[2])
    return prices


def get_price_on_or_after(prices: dict[date, float], target: date):
    for d in sorted(prices.keys()):
        if d >= target:
            return prices[d], d
    return None


def get_price_on_or_before(prices: dict[date, float], target: date):
    result = None
    for d in sorted(prices.keys()):
        if d <= target:
            result = (prices[d], d)
        else:
            break
    return result


def trading_days_between(prices: dict[date, float], start: date, end: date) -> int:
    return sum(1 for d in prices if start <= d <= end)


def dedup_signals(signals: list[dict]) -> list[dict]:
    """Keep highest conviction per stock across strategies (mirrors live dedup)."""
    best: dict[str, dict] = {}
    for sig in signals:
        sym = sig["symbol"]
        if sym not in best or sig["conviction"] > best[sym]["conviction"]:
            best[sym] = sig
    return sorted(best.values(), key=lambda x: -x["conviction"])


def run_backtest():
    conn = psycopg.connect(DB_URL)
    cur = conn.cursor()

    print("Loading all strategy signals and price data...")
    buy_signals = load_buy_signals(cur)
    exit_signals = load_exit_signals(cur)
    all_ranks = load_all_ranks(cur)
    active_strategy_dates = load_active_strategy_dates(cur)

    all_symbols = {s["symbol"] for sigs in buy_signals.values() for s in sigs}
    prices = load_prices(cur, all_symbols)
    conn.close()

    total_signals = sum(len(v) for v in buy_signals.values())
    print(f"  {len(buy_signals)} signal dates | {total_signals} BUY signals | {len(all_symbols)} symbols")

    # ── Simulation ────────────────────────────────────────────────────────────
    cash = float(CAPITAL)
    open_positions: list[Position] = []
    completed_trades: list[Trade] = []

    sim_end = date(2026, 6, 5)
    sim_dates = sorted({
        d for sym_prices in prices.values() for d in sym_prices
        if d >= date(2022, 1, 3) and d <= sim_end
    })

    portfolio_values: list[tuple[date, float]] = []
    idle_days = 0
    active_days = 0

    for today in sim_dates:
        active_strategies_today = active_strategy_dates.get(today, set())
        has_any_signal = today in buy_signals

        # ── 1. Exit open positions ─────────────────────────────────────────
        still_open = []
        for pos in open_positions:
            sym_prices = prices.get(pos.symbol, {})
            hold_days = trading_days_between(sym_prices, pos.entry_date, today)

            # Determine exit
            exit_reason = None
            if pos.stock_id in exit_signals.get(today, set()):
                exit_reason = "EXIT_SIGNAL"
            elif hold_days >= MAX_HOLDING_DAYS:
                exit_reason = "TIME_STOP_30D"
            elif all_ranks.get(today, {}).get(pos.stock_id, 0) > RANK_EXIT_THRESHOLD:
                exit_reason = "RANK_DETERIORATION"
            elif (pos.strategy not in active_strategies_today
                  and len(active_strategies_today) > 0
                  and hold_days > 5):
                # Regime flip: strategy no longer running → exit after grace period
                exit_reason = "REGIME_FLIP"

            if exit_reason:
                ep_info = get_price_on_or_before(sym_prices, today)
                exit_price = ep_info[0] if ep_info else pos.entry_price
                proceeds = pos.shares * exit_price * (1 - TXN_COST)
                pnl = proceeds - pos.cost_basis
                cash += proceeds
                completed_trades.append(Trade(
                    symbol=pos.symbol, strategy=pos.strategy,
                    entry_date=pos.entry_date, exit_date=today,
                    entry_price=pos.entry_price, exit_price=exit_price,
                    shares=pos.shares, pnl=pnl,
                    pnl_pct=pnl / pos.cost_basis * 100,
                    holding_days=hold_days, exit_reason=exit_reason,
                    conviction=pos.conviction,
                ))
            else:
                still_open.append(pos)

        open_positions = still_open

        # ── 2. Enter new positions ─────────────────────────────────────────
        if today in buy_signals:
            open_syms = {p.symbol for p in open_positions}
            slots_free = MAX_SLOTS - len(open_positions)

            # Dedup across strategies, sort by conviction desc
            todays_signals = dedup_signals(buy_signals[today])

            for sig in todays_signals:
                if slots_free <= 0:
                    break
                if sig["symbol"] in open_syms:
                    continue

                sym_prices = prices.get(sig["symbol"], {})
                p_info = get_price_on_or_after(sym_prices, today)
                if not p_info:
                    continue

                entry_price, _ = p_info
                alloc = CAPITAL / MAX_SLOTS
                alloc = min(alloc, cash)
                if alloc < entry_price * (1 + TXN_COST):
                    continue

                shares = int(alloc / (entry_price * (1 + TXN_COST)))
                if shares == 0:
                    continue

                cost = shares * entry_price * (1 + TXN_COST)
                cash -= cost
                open_positions.append(Position(
                    symbol=sig["symbol"], stock_id=sig["stock_id"],
                    strategy=sig["strategy"], entry_date=today,
                    entry_price=entry_price, shares=shares,
                    cost_basis=cost, rank_at_entry=sig["rank"],
                    conviction=sig["conviction"],
                ))
                open_syms.add(sig["symbol"])
                slots_free -= 1

        # ── 3. MTM ─────────────────────────────────────────────────────────
        mtm = cash
        for pos in open_positions:
            p_info = get_price_on_or_before(prices.get(pos.symbol, {}), today)
            mtm += pos.shares * (p_info[0] if p_info else pos.entry_price)
        portfolio_values.append((today, mtm))

        if open_positions or has_any_signal:
            active_days += 1
        else:
            idle_days += 1

    # Force-close remaining positions
    for pos in open_positions:
        sym_prices = prices.get(pos.symbol, {})
        p_info = get_price_on_or_before(sym_prices, sim_end)
        exit_price = p_info[0] if p_info else pos.entry_price
        proceeds = pos.shares * exit_price * (1 - TXN_COST)
        pnl = proceeds - pos.cost_basis
        cash += proceeds
        completed_trades.append(Trade(
            symbol=pos.symbol, strategy=pos.strategy,
            entry_date=pos.entry_date, exit_date=sim_end,
            entry_price=pos.entry_price, exit_price=exit_price,
            shares=pos.shares, pnl=pnl,
            pnl_pct=pnl / pos.cost_basis * 100,
            holding_days=trading_days_between(sym_prices, pos.entry_date, sim_end),
            exit_reason="FORCE_CLOSE_END", conviction=pos.conviction,
        ))

    final_value = cash

    # ── Analytics ────────────────────────────────────────────────────────────
    total_return = (final_value - CAPITAL) / CAPITAL * 100
    years = (sim_end - date(2022, 1, 3)).days / 365.25
    cagr = ((final_value / CAPITAL) ** (1 / years) - 1) * 100

    wins = [t for t in completed_trades if t.pnl > 0]
    losses = [t for t in completed_trades if t.pnl <= 0]
    win_rate = len(wins) / len(completed_trades) * 100 if completed_trades else 0
    avg_win = sum(t.pnl_pct for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t.pnl_pct for t in losses) / len(losses) if losses else 0
    gross_profit = sum(t.pnl for t in wins)
    gross_loss = abs(sum(t.pnl for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    avg_hold = sum(t.holding_days for t in completed_trades) / len(completed_trades) if completed_trades else 0

    # Max drawdown
    peak, max_dd = CAPITAL, 0.0
    for _, val in portfolio_values:
        if val > peak:
            peak = val
        dd = (peak - val) / peak * 100
        if dd > max_dd:
            max_dd = dd

    # Per-strategy stats
    strat_stats: dict[str, dict] = {}
    for strat in ["breakout_v1", "momentum_v1", "reversal_v1"]:
        st = [t for t in completed_trades if t.strategy == strat]
        if not st:
            continue
        sw = [t for t in st if t.pnl > 0]
        sl = [t for t in st if t.pnl <= 0]
        strat_stats[strat] = {
            "trades": len(st),
            "win_rate": len(sw) / len(st) * 100,
            "total_pnl": sum(t.pnl for t in st),
            "avg_win": sum(t.pnl_pct for t in sw) / len(sw) if sw else 0,
            "avg_loss": sum(t.pnl_pct for t in sl) / len(sl) if sl else 0,
            "avg_hold": sum(t.holding_days for t in st) / len(st),
            "pf": sum(t.pnl for t in sw) / abs(sum(t.pnl for t in sl)) if sl and sum(t.pnl for t in sl) != 0 else 99,
        }

    # Yearly P&L
    yearly_pnl: dict[int, dict] = defaultdict(lambda: defaultdict(float))
    for t in completed_trades:
        yearly_pnl[t.exit_date.year]["total"] += t.pnl
        yearly_pnl[t.exit_date.year][t.strategy] += t.pnl

    # Exit reasons
    exit_counts: dict[str, int] = defaultdict(int)
    for t in completed_trades:
        exit_counts[t.exit_reason] += 1

    # Best/worst trades
    by_pct = sorted(completed_trades, key=lambda t: t.pnl_pct)

    # ── Print Report ─────────────────────────────────────────────────────────
    W = 62
    print("\n" + "=" * W)
    print("  PI-PM MULTI-STRATEGY BACKTEST  |  Jan 2022 → Jun 2026")
    print("  Strategies: breakout_v1 + momentum_v1 + reversal_v1")
    print("  Capital: ₹1,00,000  |  5 slots  |  Cross-strategy dedup ON")
    print("=" * W)

    print(f"\n{'─'*W}")
    print("  OVERALL PORTFOLIO")
    print(f"{'─'*W}")
    print(f"  Starting Capital  : ₹{CAPITAL:>10,.0f}")
    print(f"  Final Value       : ₹{final_value:>10,.0f}")
    print(f"  Total P&L         : ₹{final_value - CAPITAL:>+10,.0f}")
    print(f"  Total Return      : {total_return:>+9.1f}%")
    print(f"  CAGR              : {cagr:>+9.1f}%   ({years:.1f} years)")
    print(f"  Max Drawdown      : {max_dd:>9.1f}%")
    print(f"  Active / Idle Days: {active_days:>4} / {idle_days:<4}  ({active_days/(active_days+idle_days)*100:.0f}% deployed)")

    print(f"\n{'─'*W}")
    print("  TRADE STATISTICS (all strategies combined)")
    print(f"{'─'*W}")
    print(f"  Total Trades      : {len(completed_trades):>5}")
    print(f"  Win Rate          : {win_rate:>8.1f}%   ({len(wins)}W / {len(losses)}L)")
    print(f"  Avg Winning Trade : {avg_win:>+8.1f}%")
    print(f"  Avg Losing Trade  : {avg_loss:>+8.1f}%")
    print(f"  Profit Factor     : {profit_factor:>8.2f}x")
    print(f"  Avg Holding Days  : {avg_hold:>8.1f}")

    print(f"\n{'─'*W}")
    print("  PER-STRATEGY BREAKDOWN")
    print(f"{'─'*W}")
    print(f"  {'Strategy':<16} {'Trades':>6} {'Win%':>6} {'AvgW':>7} {'AvgL':>7} {'PF':>5} {'P&L':>10}")
    print(f"  {'─'*16} {'─'*6} {'─'*6} {'─'*7} {'─'*7} {'─'*5} {'─'*10}")
    for strat, s in strat_stats.items():
        print(f"  {strat:<16} {s['trades']:>6} {s['win_rate']:>5.1f}% {s['avg_win']:>+6.1f}% {s['avg_loss']:>+6.1f}% {s['pf']:>5.2f} ₹{s['total_pnl']:>+8,.0f}")

    print(f"\n{'─'*W}")
    print("  YEARLY P&L BY STRATEGY")
    print(f"{'─'*W}")
    print(f"  {'Year':<6} {'breakout_v1':>12} {'momentum_v1':>12} {'reversal_v1':>12} {'TOTAL':>10}")
    for yr in sorted(yearly_pnl):
        b = yearly_pnl[yr].get("breakout_v1", 0)
        m = yearly_pnl[yr].get("momentum_v1", 0)
        rv = yearly_pnl[yr].get("reversal_v1", 0)
        tot = yearly_pnl[yr]["total"]
        bar = ("▲" if tot >= 0 else "▼") * min(int(abs(tot) / 5000), 10)
        print(f"  {yr:<6} ₹{b:>+9,.0f}  ₹{m:>+9,.0f}  ₹{rv:>+9,.0f}  ₹{tot:>+8,.0f} {bar}")

    print(f"\n{'─'*W}")
    print("  EXIT REASON BREAKDOWN")
    print(f"{'─'*W}")
    for reason, cnt in sorted(exit_counts.items(), key=lambda x: -x[1]):
        pct = cnt / len(completed_trades) * 100
        print(f"  {reason:<25}: {cnt:>4}  ({pct:.0f}%)")

    print(f"\n{'─'*W}")
    print("  TOP 10 BEST TRADES")
    print(f"{'─'*W}")
    for t in by_pct[-10:][::-1]:
        print(f"  {t.symbol:<18} {t.strategy:<12} {t.entry_date}→{t.exit_date}  {t.pnl_pct:>+6.1f}%  ₹{t.pnl:>+7,.0f}")

    print(f"\n{'─'*W}")
    print("  TOP 10 WORST TRADES")
    print(f"{'─'*W}")
    for t in by_pct[:10]:
        print(f"  {t.symbol:<18} {t.strategy:<12} {t.entry_date}→{t.exit_date}  {t.pnl_pct:>+6.1f}%  ₹{t.pnl:>+7,.0f}")

    print(f"\n{'─'*W}")
    print("  BENCHMARK COMPARISON")
    print(f"{'─'*W}")
    print(f"  Pi-PM System     : {total_return:>+7.1f}% total  |  {cagr:>+5.1f}% CAGR  |  {max_dd:.1f}% max DD")
    print(f"  NIFTY 500 (est.) :   +50-55% total  |   +11-12% CAGR  |  ~20% max DD")
    print(f"  Fixed Deposit    :   +28-30% total  |    +7% CAGR     |   0% max DD")
    print()


if __name__ == "__main__":
    run_backtest()
