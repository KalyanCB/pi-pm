#!/usr/bin/env python3
"""
Pi-PM In-Memory Backtest with REGIME-DYNAMIC STOP-LOSS — no DB writes.

Same isolated, day-by-day walk-forward simulation as backtest_inmemory.py, but the
stop-loss threshold is keyed to the market regime (BULL/BEAR × LOW/HIGH vol) read
from regime_history (benchmark ^NSEI). The stop is RE-EVALUATED DAILY against the
current day's regime — as the regime shifts while a position is held, its stop
tightens/loosens accordingly.

Reads only: recommendation_results, recommendation_runs, ranking_runs, stocks,
market_data, regime_history. NEVER writes, and NEVER touches portfolio_positions
or portfolio_configs.

Regime → stop map (defaults; override with env REGIME_STOP_MAP as JSON, e.g.
  REGIME_STOP_MAP='{"BULL_LOW_VOL":-4,"BEAR_LOW_VOL":-1,"BULL_HIGH_VOL":-6,"BEAR_HIGH_VOL":-2}'):
  BULL_LOW_VOL   : -4%   (calm uptrend — let winners breathe)   [user-specified]
  BULL_HIGH_VOL  : -6%   (uptrend but choppy — widen vs noise)  [default]
  BEAR_LOW_VOL   : -1%   (downtrend — cut fast)                 [user-specified]
  BEAR_HIGH_VOL  : -2%   (downtrend + choppy — tight, a touch wider) [default]
  <unknown/gap>  : forward-filled last regime, else DEFAULT_STOP_PCT

Other exit triggers (unchanged from backtest_inmemory.py), priority order each day:
  1. Regime stop-loss : EOD close ≤ entry × (1 + stop%/100) → exit at that level (capped)
  2. Time-stop        : held > 30 trading days  → exit at EOD close
  3. Rank-drop        : current rank > 40       → exit at EOD close
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://pipm:pipm@localhost:5432/pipm")
BENCHMARK = "^NSEI"

# ── Portfolio config (matches backtest_inmemory.py for comparability) ──────────
INITIAL_CAPITAL = 10_000_000.0   # ₹1 crore
MAX_SLOTS = 10
MAX_SLOT_ALLOC = 500_000.0       # ₹5 lakh per slot
MAX_HOLD_DAYS = int(os.getenv("MAX_HOLD_DAYS", "30"))   # trading days
RANK_DROP_THRESH = 40
# Lever: skip NEW entries while regime is BEAR_* (existing positions still managed).
BLOCK_BEAR_ENTRIES = os.getenv("BLOCK_BEAR_ENTRIES", "0") == "1"
# Lever: trailing stop — measure the regime stop%% from the position's PEAK close
# instead of entry price, so winners ratchet their stop up as they run.
TRAILING_STOP = os.getenv("TRAILING_STOP", "0") == "1"
# Lever: re-entry after stop-out. For REENTRY_WINDOW trading days after a
# STOP_LOSS exit the stock sits on a watchlist; if its close recovers above
# exit_price × (1 + REENTRY_TRIGGER_PCT/100) while still ranked ≤ RANK_DROP_THRESH,
# re-enter (slot permitting) — targets winners shaken out by noise.
# REENTRY_REQUIRE_SIGNAL=1 is the conservative variant: no watchlist entries;
# instead a fresh BUY re-signal from a recently stopped-out name that recovered
# its exit price jumps to the FRONT of the day's signal queue.
REENTRY_WINDOW = int(os.getenv("REENTRY_WINDOW", "0"))          # 0 = off
REENTRY_TRIGGER_PCT = float(os.getenv("REENTRY_TRIGGER_PCT", "0"))
REENTRY_REQUIRE_SIGNAL = os.getenv("REENTRY_REQUIRE_SIGNAL", "0") == "1"
# Lever: regime debounce — the EFFECTIVE regime (driving stop thresholds and
# entry tagging) only switches after the raw label persists this many consecutive
# trading days. Filters the 1–2 day BULL↔BEAR flickers that retoggle stops.
REGIME_DEBOUNCE_DAYS = int(os.getenv("REGIME_DEBOUNCE_DAYS", "0"))  # 0/1 = off
SLIPPAGE_BPS = float(os.getenv("SLIPPAGE_BPS", "5"))   # per-side slippage
FEE_BPS = float(os.getenv("FEE_BPS", "0"))             # per-side round-trip cost
# Honest mode: stops fill at the ACTUAL slipped close (gap-through), not capped at
# the stop level. The capped fill (default) is optimistic — it pretends every stop
# fills exactly at entry × (1+stop%), which most favours ultra-tight stops.
REALISTIC_STOP_FILL = os.getenv("REALISTIC_STOP_FILL", "0") == "1"
CONVICTION_MULT = {"EXCEPTIONAL": 1.15, "HIGH": 1.00, "MEDIUM": 0.75}

# ── Regime-dynamic stop map (negative percents) ───────────────────────────────
DEFAULT_REGIME_STOP_MAP: dict[str, float] = {
    "BULL_LOW_VOL": -4.0,
    "BULL_HIGH_VOL": -6.0,
    "BEAR_LOW_VOL": -1.0,
    "BEAR_HIGH_VOL": -2.0,
}
DEFAULT_STOP_PCT = -4.0  # fallback when a day has no resolvable regime


def regime_stop_map() -> dict[str, float]:
    raw = os.getenv("REGIME_STOP_MAP")
    if not raw:
        return dict(DEFAULT_REGIME_STOP_MAP)
    overrides = {k: float(v) for k, v in json.loads(raw).items()}
    return {**DEFAULT_REGIME_STOP_MAP, **overrides}


@dataclass
class Position:
    stock_id: str
    symbol: str
    strategy: str
    sector: str
    entry_date: date
    entry_price: float
    qty: float
    cost: float
    conviction_band: str
    entry_regime: str
    trading_days_held: int = 0
    peak_price: float = 0.0  # highest close seen (trailing-stop reference)


@dataclass
class Trade:
    symbol: str
    strategy: str
    entry_date: date
    exit_date: date
    entry_price: float
    exit_price: float
    qty: float
    cost: float
    pnl: float
    pnl_pct: float
    hold_days: int
    exit_reason: str
    conviction_band: str
    exit_regime: str = ""


# ── Loaders (read-only) ───────────────────────────────────────────────────────


def load_regime_by_date(conn, start: str, end: str) -> dict[date, str]:
    """Per-day regime label from regime_history (benchmark ^NSEI)."""
    rows = conn.execute(
        text("""
            SELECT as_of_date, regime_label
            FROM regime_history
            WHERE benchmark_symbol = :bm AND regime_label IS NOT NULL
              AND as_of_date >= :s AND as_of_date <= :e
            ORDER BY as_of_date
        """),
        {"bm": BENCHMARK, "s": start, "e": end},
    ).fetchall()
    return {r[0]: r[1] for r in rows}


def load_buy_signals(conn, start: str, end: str) -> dict[date, list[dict]]:
    rows = conn.execute(
        text("""
            SELECT rrun.as_of_date, rr.id::text, rr.stock_id::text, s.symbol, s.sector,
                   rk.strategy_name, rr.rank, rr.conviction_score, rr.conviction_band
            FROM recommendation_results rr
            JOIN recommendation_runs rrun ON rr.recommendation_run_id = rrun.id
            JOIN ranking_runs rk          ON rrun.ranking_run_id = rk.id
            JOIN stocks s                 ON rr.stock_id = s.id
            WHERE rr.action = 'BUY' AND rrun.as_of_date >= :s AND rrun.as_of_date <= :e
            ORDER BY rrun.as_of_date, rr.conviction_score DESC, rr.rank, rr.id
        """),
        {"s": start, "e": end},
    ).fetchall()
    signals: dict[date, list[dict]] = defaultdict(list)
    seen: set = set()
    for row in rows:
        key = (row[0], row[2])  # dedup cross-strategy on (date, stock)
        if key in seen:
            continue
        seen.add(key)
        signals[row[0]].append({
            "stock_id": row[2], "symbol": row[3], "sector": row[4],
            "strategy": row[5], "rank": row[6],
            "conviction": row[7], "conviction_band": row[8],
        })
    return signals


def load_all_ranks(conn, start: str, end: str) -> dict[date, dict[str, int]]:
    rows = conn.execute(
        text("""
            SELECT rrun.as_of_date, rr.stock_id::text, MIN(rr.rank)
            FROM recommendation_results rr
            JOIN recommendation_runs rrun ON rr.recommendation_run_id = rrun.id
            WHERE rrun.as_of_date >= :s AND rrun.as_of_date <= :e AND rr.rank IS NOT NULL
            GROUP BY rrun.as_of_date, rr.stock_id
        """),
        {"s": start, "e": end},
    ).fetchall()
    ranks: dict[date, dict[str, int]] = defaultdict(dict)
    for row in rows:
        ranks[row[0]][row[1]] = int(row[2])
    return ranks


def get_eod_close(conn, stock_id: str, as_of: date) -> float | None:
    row = conn.execute(
        text("SELECT close FROM market_data WHERE stock_id = :sid AND date <= :d "
             "ORDER BY date DESC LIMIT 1"),
        {"sid": stock_id, "d": as_of},
    ).fetchone()
    return float(row[0]) if row else None


def slip(price: float, side: str) -> float:
    s = SLIPPAGE_BPS / 10_000
    return price * (1 + s) if side == "BUY" else price * (1 - s)


def buy_cost(qty: float, price: float) -> float:
    """Cash out on entry, including per-side fee (price already slipped)."""
    return qty * price * (1 + FEE_BPS / 10_000)


def sell_proceeds(qty: float, price: float) -> float:
    """Cash in on exit, net of per-side fee (price already slipped)."""
    return qty * price * (1 - FEE_BPS / 10_000)


def run(start: str, end: str) -> None:
    stop_map = regime_stop_map()
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        print("\n=== PI-PM REGIME-DYNAMIC STOP BACKTEST (in-memory, no DB writes) ===")
        print(f"    Period   : {start} → {end}")
        print(f"    Capital  : ₹{INITIAL_CAPITAL:,.0f} | {MAX_SLOTS} slots | ₹{MAX_SLOT_ALLOC:,.0f}/slot")
        print(f"    Costs    : fee {FEE_BPS:.0f}bps/side | slippage {SLIPPAGE_BPS:.0f}bps/side | "
              f"stop fill = {'REALISTIC (gap-through)' if REALISTIC_STOP_FILL else 'capped (optimistic)'}")
        print("    Regime stops:")
        for k in ("BULL_LOW_VOL", "BULL_HIGH_VOL", "BEAR_LOW_VOL", "BEAR_HIGH_VOL"):
            print(f"      {k:<14}: {stop_map.get(k, DEFAULT_STOP_PCT):>5.1f}%")
        print(f"      <fallback>    : {DEFAULT_STOP_PCT:>5.1f}%\n")

        print("  Loading signals, ranks, regime...")
        buy_signals = load_buy_signals(conn, start, end)
        all_ranks = load_all_ranks(conn, start, end)
        regime_by_date = load_regime_by_date(conn, start, end)

        trading_days = [
            r[0] for r in conn.execute(
                text("SELECT DISTINCT date FROM market_data WHERE date >= :s AND date <= :e "
                     "ORDER BY date"), {"s": start, "e": end},
            ).fetchall()
        ]
        print(f"  {len(trading_days)} trading days | "
              f"{sum(len(v) for v in buy_signals.values())} BUY signals | "
              f"{len(regime_by_date)} regime-labelled days\n")

        cash = INITIAL_CAPITAL
        positions: list[Position] = []
        trades: list[Trade] = []
        nav_curve: list[tuple[date, float]] = []
        monthly_nav: dict[str, float] = {}

        stops_by_regime: dict[str, int] = defaultdict(int)
        regime_day_count: dict[str, int] = defaultdict(int)
        time_exits = rank_exits = day_num = 0
        last_regime = ""        # EFFECTIVE regime (drives stops/entries)
        last_raw = ""           # last raw label seen (forward-fill)
        pending_regime: str | None = None
        pending_count = 0
        flickers_ignored = 0
        stopouts: dict[str, dict] = {}          # stock_id -> stop-out watchlist row
        reentry_keys: set[tuple] = set()        # (symbol, entry_date) of re-entries

        for today in trading_days:
            day_num += 1
            # Resolve today's regime (forward-fill gaps with last known raw label).
            raw = regime_by_date.get(today, last_raw)
            if raw:
                last_raw = raw
            if REGIME_DEBOUNCE_DAYS > 1 and last_regime:
                # Effective regime switches only after N consecutive days of the
                # new raw label; shorter flickers never retoggle the stops.
                if raw == last_regime:
                    if pending_regime is not None:
                        flickers_ignored += 1
                    pending_regime, pending_count = None, 0
                elif raw == pending_regime:
                    pending_count += 1
                    if pending_count >= REGIME_DEBOUNCE_DAYS:
                        last_regime, pending_regime, pending_count = raw, None, 0
                else:
                    pending_regime, pending_count = raw, 1
                regime = last_regime
            else:
                regime = raw
                if regime:
                    last_regime = regime
            regime_day_count[regime or "UNKNOWN"] += 1
            stop_pct = stop_map.get(regime, DEFAULT_STOP_PCT)
            stop_factor = 1.0 + (stop_pct / 100.0)

            exited_ids: set[str] = set()
            for pos in positions:
                pos.trading_days_held += 1

            # 1. Regime-dynamic stop-loss (re-evaluated against TODAY's regime)
            for pos in list(positions):
                close = get_eod_close(conn, pos.stock_id, today)
                if close is None:
                    continue
                if TRAILING_STOP:
                    pos.peak_price = max(pos.peak_price or pos.entry_price, close)
                    ref_price = pos.peak_price
                else:
                    ref_price = pos.entry_price
                unreal_pct = (close - ref_price) / ref_price * 100
                if unreal_pct <= stop_pct:
                    if REALISTIC_STOP_FILL:
                        # Honest: fill at the actual slipped close (gap-through).
                        exit_price = slip(close, "SELL")
                    else:
                        # Capped at the stop level (optimistic; parity with backtest_inmemory.py).
                        exit_price = round(ref_price * stop_factor, 4)
                    proceeds = sell_proceeds(pos.qty, exit_price)
                    pnl = proceeds - pos.cost
                    trades.append(Trade(
                        symbol=pos.symbol, strategy=pos.strategy, entry_date=pos.entry_date,
                        exit_date=today, entry_price=pos.entry_price, exit_price=exit_price,
                        qty=pos.qty, cost=pos.cost, pnl=pnl, pnl_pct=pnl / pos.cost * 100,
                        hold_days=pos.trading_days_held, exit_reason="STOP_LOSS",
                        conviction_band=pos.conviction_band, exit_regime=regime or "UNKNOWN",
                    ))
                    cash += proceeds
                    exited_ids.add(pos.stock_id)
                    stops_by_regime[regime or "UNKNOWN"] += 1
                    if REENTRY_WINDOW:
                        stopouts[pos.stock_id] = {
                            "day": day_num, "exit_price": exit_price,
                            "symbol": pos.symbol, "strategy": pos.strategy,
                            "sector": pos.sector, "band": pos.conviction_band,
                        }
            positions = [p for p in positions if p.stock_id not in exited_ids]

            # 2. Time-stop
            for pos in list(positions):
                if pos.trading_days_held <= MAX_HOLD_DAYS:
                    continue
                close = get_eod_close(conn, pos.stock_id, today)
                if close is None:
                    continue
                exit_price = slip(close, "SELL")
                proceeds = sell_proceeds(pos.qty, exit_price)
                pnl = proceeds - pos.cost
                trades.append(Trade(
                    symbol=pos.symbol, strategy=pos.strategy, entry_date=pos.entry_date,
                    exit_date=today, entry_price=pos.entry_price, exit_price=exit_price,
                    qty=pos.qty, cost=pos.cost, pnl=pnl, pnl_pct=pnl / pos.cost * 100,
                    hold_days=pos.trading_days_held, exit_reason="TIME_STOP",
                    conviction_band=pos.conviction_band, exit_regime=regime or "UNKNOWN",
                ))
                cash += proceeds
                exited_ids.add(pos.stock_id)
                time_exits += 1
            positions = [p for p in positions if p.stock_id not in exited_ids]

            # 3. Rank-drop
            today_ranks = all_ranks.get(today, {})
            for pos in list(positions):
                r = today_ranks.get(pos.stock_id)
                if r is None or r <= RANK_DROP_THRESH:
                    continue
                close = get_eod_close(conn, pos.stock_id, today)
                if close is None:
                    continue
                exit_price = slip(close, "SELL")
                proceeds = sell_proceeds(pos.qty, exit_price)
                pnl = proceeds - pos.cost
                trades.append(Trade(
                    symbol=pos.symbol, strategy=pos.strategy, entry_date=pos.entry_date,
                    exit_date=today, entry_price=pos.entry_price, exit_price=exit_price,
                    qty=pos.qty, cost=pos.cost, pnl=pnl, pnl_pct=pnl / pos.cost * 100,
                    hold_days=pos.trading_days_held, exit_reason="RANK_DROP",
                    conviction_band=pos.conviction_band, exit_regime=regime or "UNKNOWN",
                ))
                cash += proceeds
                exited_ids.add(pos.stock_id)
                rank_exits += 1
            positions = [p for p in positions if p.stock_id not in exited_ids]

            # 4. Entries (optionally gated off during BEAR regimes)
            entries_blocked = BLOCK_BEAR_ENTRIES and (regime or "").startswith("BEAR")
            candidates: list[dict] = []
            if REENTRY_WINDOW and not entries_blocked:
                # Expire stale watchlist rows, then collect recovered stop-outs.
                open_now = {p.stock_id for p in positions}
                for sid in [s for s, i in stopouts.items()
                            if day_num - i["day"] > REENTRY_WINDOW or s in open_now]:
                    stopouts.pop(sid)
                if not REENTRY_REQUIRE_SIGNAL:
                    for sid, info in stopouts.items():
                        close = get_eod_close(conn, sid, today)
                        if close is None:
                            continue
                        if close < info["exit_price"] * (1 + REENTRY_TRIGGER_PCT / 100.0):
                            continue
                        r = today_ranks.get(sid)
                        if r is None or r > RANK_DROP_THRESH:
                            continue
                        candidates.append({
                            "stock_id": sid, "symbol": info["symbol"],
                            "sector": info["sector"], "strategy": info["strategy"],
                            "rank": r, "conviction": None,
                            "conviction_band": info["band"], "reentry": True,
                        })
            day_signals = [] if entries_blocked else buy_signals.get(today, [])
            if REENTRY_WINDOW and REENTRY_REQUIRE_SIGNAL and day_signals:
                # Conservative variant: recovered re-signals jump the queue.
                def _is_recovered_resignal(s: dict) -> bool:
                    info = stopouts.get(s["stock_id"])
                    if not info:
                        return False
                    close = get_eod_close(conn, s["stock_id"], today)
                    return bool(close) and close >= info["exit_price"] * (
                        1 + REENTRY_TRIGGER_PCT / 100.0
                    )
                day_signals = sorted(day_signals, key=lambda s: not _is_recovered_resignal(s))
            candidates.extend(day_signals)

            if candidates:
                open_ids = {p.stock_id for p in positions}
                slots_free = MAX_SLOTS - len(positions)
                for sig in candidates:
                    if slots_free <= 0:
                        break
                    if sig["stock_id"] in open_ids:
                        continue
                    close = get_eod_close(conn, sig["stock_id"], today)
                    if close is None:
                        continue
                    entry_price = slip(close, "BUY")
                    mult = CONVICTION_MULT.get(sig["conviction_band"], 0.75)
                    alloc = min(MAX_SLOT_ALLOC * mult, cash * 0.95)
                    if alloc < entry_price:
                        continue
                    qty = alloc / entry_price
                    cost = buy_cost(qty, entry_price)
                    if cost > cash:
                        qty = cash * 0.95 / entry_price
                        cost = buy_cost(qty, entry_price)
                    if qty <= 0:
                        continue
                    cash -= cost
                    positions.append(Position(
                        stock_id=sig["stock_id"], symbol=sig["symbol"], strategy=sig["strategy"],
                        sector=sig["sector"], entry_date=today, entry_price=entry_price,
                        qty=qty, cost=cost, conviction_band=sig["conviction_band"],
                        entry_regime=regime or "UNKNOWN",
                    ))
                    if REENTRY_WINDOW and sig["stock_id"] in stopouts:
                        reentry_keys.add((sig["symbol"], today))
                        stopouts.pop(sig["stock_id"], None)
                    open_ids.add(sig["stock_id"])
                    slots_free -= 1

            # 5. Mark-to-market NAV
            mtm = cash
            for pos in positions:
                c2 = get_eod_close(conn, pos.stock_id, today)
                mtm += pos.qty * c2 if c2 else pos.cost
            nav_curve.append((today, mtm))
            monthly_nav[today.strftime("%Y-%m")] = mtm

            if day_num % 250 == 0:
                print(f"  [{today}] {regime:<13} | {len(positions)} open | "
                      f"NAV ₹{mtm:,.0f} | stops={sum(stops_by_regime.values())}")

        # Force-close residual
        last_day = trading_days[-1]
        for pos in positions:
            close = get_eod_close(conn, pos.stock_id, last_day)
            if not close:
                continue
            exit_price = slip(close, "SELL")
            proceeds = sell_proceeds(pos.qty, exit_price)
            pnl = proceeds - pos.cost
            trades.append(Trade(
                symbol=pos.symbol, strategy=pos.strategy, entry_date=pos.entry_date,
                exit_date=last_day, entry_price=pos.entry_price, exit_price=exit_price,
                qty=pos.qty, cost=pos.cost, pnl=pnl, pnl_pct=pnl / pos.cost * 100,
                hold_days=pos.trading_days_held, exit_reason="FORCE_CLOSE",
                conviction_band=pos.conviction_band, exit_regime=last_regime or "UNKNOWN",
            ))
            cash += proceeds

        if REGIME_DEBOUNCE_DAYS > 1:
            print(f"\n  DEBOUNCE: {REGIME_DEBOUNCE_DAYS}d confirmation | "
                  f"flickers ignored (raw switches suppressed): {flickers_ignored}")

        if REENTRY_WINDOW:
            re_trades = [t for t in trades if (t.symbol, t.entry_date) in reentry_keys]
            re_pnl = sum(t.pnl for t in re_trades)
            re_wins = sum(1 for t in re_trades if t.pnl > 0)
            print(f"\n  RE-ENTRY: window={REENTRY_WINDOW}d trigger=+{REENTRY_TRIGGER_PCT}% "
                  f"{'(signal-priority)' if REENTRY_REQUIRE_SIGNAL else '(price watchlist)'} | "
                  f"taken={len(re_trades)} wins={re_wins} pnl=₹{re_pnl:+,.0f}")

        dump = os.getenv("TRADE_DUMP")
        if dump:
            import csv
            with open(dump, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["symbol", "strategy", "entry_date", "exit_date", "entry_price",
                            "exit_price", "qty", "cost", "pnl", "pnl_pct", "hold_days",
                            "exit_reason", "conviction_band", "exit_regime"])
                for t in trades:
                    w.writerow([t.symbol, t.strategy, t.entry_date, t.exit_date,
                                t.entry_price, t.exit_price, t.qty, t.cost, t.pnl,
                                t.pnl_pct, t.hold_days, t.exit_reason,
                                t.conviction_band, t.exit_regime])
            print(f"  [trade log written to {dump}]")

        _report(trades, nav_curve, monthly_nav, cash, last_day, start,
                 stops_by_regime, regime_day_count, stop_map)


def _report(trades, nav_curve, monthly_nav, final_nav, last_day, start,
            stops_by_regime, regime_day_count, stop_map) -> None:
    W = 74
    total_pnl = final_nav - INITIAL_CAPITAL
    total_ret = total_pnl / INITIAL_CAPITAL * 100
    start_d = date.fromisoformat(start)
    years = max((last_day - start_d).days / 365.25, 1e-9)
    cagr = ((final_nav / INITIAL_CAPITAL) ** (1 / years) - 1) * 100

    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    wr = len(wins) / len(trades) * 100 if trades else 0
    aw = sum(t.pnl_pct for t in wins) / len(wins) if wins else 0
    al = sum(t.pnl_pct for t in losses) / len(losses) if losses else 0
    gl = abs(sum(t.pnl for t in losses))
    pf = sum(t.pnl for t in wins) / gl if gl > 0 else 999.0

    peak = INITIAL_CAPITAL
    max_dd = 0.0
    for _, nav in nav_curve:
        peak = max(peak, nav)
        max_dd = max(max_dd, (peak - nav) / peak * 100)

    print("\n" + "=" * W)
    print("  REGIME-DYNAMIC STOP BACKTEST RESULTS")
    print("=" * W)
    print(f"  Final NAV     : ₹{final_nav:>14,.0f}")
    print(f"  Total P&L     : ₹{total_pnl:>+14,.0f}   ({total_ret:+.2f}%)")
    print(f"  CAGR          : {cagr:>+13.2f}%   ({years:.1f} yrs)")
    print(f"  Max Drawdown  : {max_dd:>13.2f}%")
    print(f"  Trades        : {len(trades)}  ({len(wins)}W / {len(losses)}L, win {wr:.1f}%)")
    print(f"  Avg W / Avg L : {aw:+.2f}% / {al:+.2f}%   |  PF {pf:.2f}x")

    print(f"\n{'─'*W}\n  EXIT BREAKDOWN\n{'─'*W}")
    exit_counts: dict[str, int] = defaultdict(int)
    for t in trades:
        exit_counts[t.exit_reason] += 1
    for reason, cnt in sorted(exit_counts.items(), key=lambda x: -x[1]):
        print(f"  {reason:<14}: {cnt:>5}  ({cnt/len(trades)*100:.1f}%)")

    print(f"\n{'─'*W}\n  REGIME STOP-LOSS BREAKDOWN  (stop% per regime, days in regime, stops fired)\n{'─'*W}")
    print(f"  {'Regime':<15} {'Stop%':>7} {'Days':>7} {'Stops':>7}  {'Stop P&L':>14}")
    for reg in ("BULL_LOW_VOL", "BULL_HIGH_VOL", "BEAR_LOW_VOL", "BEAR_HIGH_VOL", "UNKNOWN"):
        days = regime_day_count.get(reg, 0)
        stops = stops_by_regime.get(reg, 0)
        if days == 0 and stops == 0:
            continue
        stop_pnl = sum(t.pnl for t in trades if t.exit_reason == "STOP_LOSS" and t.exit_regime == reg)
        sp = stop_map.get(reg, DEFAULT_STOP_PCT)
        print(f"  {reg:<15} {sp:>6.1f}% {days:>7} {stops:>7}  ₹{stop_pnl:>+12,.0f}")

    print(f"\n{'─'*W}\n  YEARLY P&L\n{'─'*W}")
    yearly: dict[int, float] = defaultdict(float)
    for t in trades:
        yearly[t.exit_date.year] += t.pnl
    for yr in sorted(yearly):
        tot = yearly[yr]
        bar = ("▲" if tot >= 0 else "▼") * min(int(abs(tot) / 100_000), 24)
        print(f"  {yr}  ₹{tot:>+13,.0f}  {bar}")

    print(f"\n{'─'*W}\n  PER-STRATEGY\n{'─'*W}")
    print(f"  {'Strategy':<16} {'N':>5} {'Win%':>6} {'AvgW':>8} {'AvgL':>8} {'Stops':>6}  {'P&L':>14}")
    strat_names = sorted({t.strategy for t in trades})
    for s in strat_names:
        st = [t for t in trades if t.strategy == s]
        sw = [t for t in st if t.pnl > 0]
        sl = [t for t in st if t.pnl <= 0]
        ss = sum(1 for t in st if t.exit_reason == "STOP_LOSS")
        awp = sum(t.pnl_pct for t in sw) / len(sw) if sw else 0
        alp = sum(t.pnl_pct for t in sl) / len(sl) if sl else 0
        print(f"  {s:<16} {len(st):>5} {len(sw)/len(st)*100:>5.1f}% "
              f"{awp:>+7.1f}% {alp:>+7.1f}% {ss:>6}  ₹{sum(t.pnl for t in st):>+12,.0f}")

    by_pct = sorted(trades, key=lambda t: t.pnl_pct)
    print(f"\n{'─'*W}\n  TOP 5 BEST TRADES\n{'─'*W}")
    for t in by_pct[-5:][::-1]:
        print(f"  {t.symbol:<18} {t.strategy:<13} {t.entry_date}→{t.exit_date} "
              f"({t.hold_days:>3}d, {t.exit_reason:<10}) {t.pnl_pct:>+8.2f}%  ₹{t.pnl:>+12,.0f}")
    print(f"\n{'─'*W}\n  TOP 5 WORST TRADES\n{'─'*W}")
    for t in by_pct[:5]:
        print(f"  {t.symbol:<18} {t.strategy:<13} {t.entry_date}→{t.exit_date} "
              f"({t.hold_days:>3}d, {t.exit_reason:<10}) {t.pnl_pct:>+8.2f}%  ₹{t.pnl:>+12,.0f}")

    print(f"\n{'─'*W}\n  MONTHLY NAV & RETURNS\n{'─'*W}")
    print(f"  {'Month':<9} {'NAV':>15} {'MoM%':>8}  Bar")
    prev_nav = INITIAL_CAPITAL
    for ym in sorted(monthly_nav):
        nav = monthly_nav[ym]
        mom = (nav - prev_nav) / prev_nav * 100 if prev_nav > 0 else 0
        bar = ("▲" if mom >= 0 else "▼") * min(int(abs(mom) * 1.5), 20)
        print(f"  {ym:<9} ₹{nav:>13,.0f} {mom:>+7.2f}%  {bar}")
        prev_nav = nav
    print()


def parse_args() -> argparse.Namespace:
    today = date.today()
    p = argparse.ArgumentParser(description="Regime-dynamic stop-loss in-memory backtest")
    p.add_argument("--start", default=(today - timedelta(days=5 * 365)).isoformat(),
                   help="Backtest start (default: ~5 years ago)")
    p.add_argument("--end", default=today.isoformat(), help="Backtest end (default: today)")
    p.add_argument("--honest", action="store_true",
                   help="Realistic stop fills (gap-through, no cap) + default fees/slippage "
                        "(fee 20bps/side, slippage 15bps) unless overridden below.")
    p.add_argument("--fee-bps", type=float, default=None, help="Per-side fee in bps")
    p.add_argument("--slippage-bps", type=float, default=None, help="Per-side slippage in bps")
    p.add_argument("--capital", type=float, default=None, help="Initial capital (₹)")
    p.add_argument("--slots", type=int, default=None, help="Max concurrent position slots")
    p.add_argument("--slot-alloc", type=float, default=None,
                   help="₹ per slot (default: capital / slots = full deployment)")
    return p.parse_args()


if __name__ == "__main__":
    a = parse_args()
    if a.capital is not None:
        INITIAL_CAPITAL = a.capital
    if a.slots is not None:
        MAX_SLOTS = a.slots
    if a.slot_alloc is not None:
        MAX_SLOT_ALLOC = a.slot_alloc
    elif a.capital is not None or a.slots is not None:
        MAX_SLOT_ALLOC = INITIAL_CAPITAL / MAX_SLOTS  # full deployment when capital/slots set
    if a.honest:
        REALISTIC_STOP_FILL = True
        if FEE_BPS == 0:
            FEE_BPS = 20.0
        if SLIPPAGE_BPS == 5.0:
            SLIPPAGE_BPS = 15.0
    if a.fee_bps is not None:
        FEE_BPS = a.fee_bps
    if a.slippage_bps is not None:
        SLIPPAGE_BPS = a.slippage_bps
    run(a.start, a.end)
