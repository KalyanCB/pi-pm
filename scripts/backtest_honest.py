#!/usr/bin/env python3
"""
Honest Paper-Trade Backtest
============================
Rules:
  - Day N decisions use ONLY data available as of close of day N-1
  - BUY signals: from recommendation_results with as_of_date = N-1, executed at N's close
  - STOP-LOSS: pre-committed stop price set at entry (entry * 0.99 for 1% stop)
               triggered if N's close <= stop_price, exits at stop_price (capped)
  - TIME-STOP: exit after 30 trading days at N's close
  - RANK-DROP: N-1's ranking shows rank > 40 → exit at N's close
  - NO look-ahead: zero use of N's data to make a trading decision
  - Writes to: portfolio_positions, paper_trades, portfolio_cash_ledger, portfolio_nav_history

Config:
  - Start: 2022-06-06
  - Capital: ₹1,00,00,000 (10M)
  - Max slots: 10
  - Max per slot: ₹5,00,000
  - Stop-loss: 1%
  - Slippage: 5 bps per leg
  - No fees
"""
from __future__ import annotations

import hashlib, json, os, sys, uuid
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://pipm:pipm@localhost:5432/pipm")

# ── Config ────────────────────────────────────────────────────────────────────
START_DATE      = date(2022, 6, 6)
INITIAL_CAPITAL = 10_000_000.0
MAX_SLOTS       = 10
MAX_SLOT_ALLOC  = 500_000.0
STOP_LOSS_PCT   = -1.0            # -1%
STOP_LOSS_FACTOR = 1.0 + (STOP_LOSS_PCT / 100)   # 0.99
MAX_HOLD_DAYS   = 30
RANK_DROP_THRESH = 40
SLIPPAGE_BPS    = 5.0
CONVICTION_MULT = {"EXCEPTIONAL": 1.15, "HIGH": 1.00, "MEDIUM": 0.75}
PORTFOLIO_ID    = uuid.UUID("00000000-0000-4000-8000-000000000010")
RUN_TAG         = "backtest_honest_v1"   # stored in paper_trades.metadata for traceability

# ── Data classes ──────────────────────────────────────────────────────────────
@dataclass
class Position:
    pos_id: uuid.UUID
    stock_id: uuid.UUID
    symbol: str
    strategy: str
    sector: str
    entry_date: date
    entry_price: float
    stop_price: float
    qty: float
    cost: float
    conviction_band: str
    recommendation_result_id: uuid.UUID | None
    trading_days_held: int = 0

@dataclass
class ClosedTrade:
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

# ── Helpers ───────────────────────────────────────────────────────────────────
def slip(price: float, side: str) -> float:
    s = SLIPPAGE_BPS / 10_000
    return price * (1 + s) if side == "BUY" else price * (1 - s)

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def gen_id() -> uuid.UUID:
    return uuid.uuid4()

# ── Load all data upfront ─────────────────────────────────────────────────────
def load_data(conn, start: date):
    print("  Loading BUY signals …")
    rows = conn.execute(text("""
        SELECT rrun.as_of_date,
               rr.id::text              AS rec_result_id,
               rr.stock_id::text,
               s.id::text               AS stock_uuid,
               s.symbol,
               s.sector,
               rk.strategy_name,
               rr.conviction_score,
               rr.conviction_band,
               rr.rank
        FROM   recommendation_results rr
        JOIN   recommendation_runs rrun ON rr.recommendation_run_id = rrun.id
        JOIN   ranking_runs rk          ON rrun.ranking_run_id = rk.id
        JOIN   stocks s                 ON rr.stock_id = s.id
        WHERE  rr.action = 'BUY'
          AND  rrun.as_of_date >= :start
        ORDER  BY rrun.as_of_date, rr.conviction_score DESC NULLS LAST, rr.rank
    """), {"start": start}).fetchall()

    signals: dict[date, list[dict]] = defaultdict(list)
    seen: set = set()
    for row in rows:
        key = (row[0], row[2])   # (date, stock_id text)
        if key not in seen:
            seen.add(key)
            signals[row[0]].append({
                "rec_result_id": uuid.UUID(row[1]),
                "stock_id":      uuid.UUID(row[3]),
                "symbol":        row[4],
                "sector":        row[5],
                "strategy":      row[6],
                "conviction":    float(row[7]) if row[7] else 0.0,
                "conviction_band": row[8] or "MEDIUM",
            })
    print(f"    {sum(len(v) for v in signals.values()):,} signals across {len(signals)} days")

    print("  Loading ranks …")
    rank_rows = conn.execute(text("""
        SELECT rrun.as_of_date, rr.stock_id::text, MIN(rr.rank)
        FROM   recommendation_results rr
        JOIN   recommendation_runs rrun ON rr.recommendation_run_id = rrun.id
        WHERE  rrun.as_of_date >= :start AND rr.rank IS NOT NULL
        GROUP  BY rrun.as_of_date, rr.stock_id
    """), {"start": start}).fetchall()
    all_ranks: dict[date, dict[str, int]] = defaultdict(dict)
    for row in rank_rows:
        all_ranks[row[0]][row[1]] = int(row[2])

    print("  Loading trading calendar …")
    trading_days = [row[0] for row in conn.execute(text("""
        SELECT DISTINCT date FROM market_data
        WHERE  date >= :start ORDER BY date
    """), {"start": start}).fetchall()]
    print(f"    {len(trading_days)} trading days from {trading_days[0]} to {trading_days[-1]}")

    print("  Loading market data (prices) …")
    price_rows = conn.execute(text("""
        SELECT stock_id::text, date, close FROM market_data
        WHERE  date >= :start ORDER BY stock_id, date
    """), {"start": start}).fetchall()

    prices: dict[str, dict[date, float]] = defaultdict(dict)
    for sid, dt, cl in price_rows:
        prices[sid][dt] = float(cl)
    for sid in prices:
        prices[sid] = dict(sorted(prices[sid].items()))
    print(f"    {len(prices)} stocks, {sum(len(v) for v in prices.values()):,} price points")

    return signals, all_ranks, trading_days, prices


def get_close(prices: dict, stock_id_str: str, as_of: date) -> float | None:
    p = prices.get(stock_id_str)
    if not p:
        return None
    result = None
    for d, v in p.items():
        if d <= as_of:
            result = v
        else:
            break
    return result


# ── DB write helpers ──────────────────────────────────────────────────────────
def db_insert_position(db, pos: Position):
    db.execute(text("""
        INSERT INTO portfolio_positions
            (id, portfolio_id, stock_id, quantity, avg_cost, entry_price, entry_date,
             position_status, conviction_band, strategy_name, sector,
             recommendation_result_id, stop_loss_price, is_current,
             as_of, created_at, updated_at)
        VALUES
            (:id, :pid, :sid, :qty, :avg_cost, :ep, :ed,
             'OPEN', :cb, :strat, :sector,
             :rec_id, :sl, true,
             :as_of, :now, :now)
    """), {
        "id":      pos.pos_id,
        "pid":     PORTFOLIO_ID,
        "sid":     pos.stock_id,
        "qty":     Decimal(str(round(pos.qty, 6))),
        "avg_cost":Decimal(str(round(pos.cost, 2))),
        "ep":      Decimal(str(round(pos.entry_price, 4))),
        "ed":      pos.entry_date,
        "cb":      pos.conviction_band,
        "strat":   pos.strategy,
        "sector":  pos.sector or "",
        "rec_id":  pos.recommendation_result_id,
        "sl":      Decimal(str(round(pos.stop_price, 4))),
        "as_of":   datetime.combine(pos.entry_date, datetime.min.time()).replace(tzinfo=timezone.utc),
        "now":     now_utc(),
    })


def db_close_position(db, pos: Position, exit_price: float, exit_date: date,
                       realized_pnl: float, exit_reason: str):
    db.execute(text("""
        UPDATE portfolio_positions
        SET exit_price      = :ep,
            exit_date       = :ed,
            realized_pnl    = :pnl,
            position_status = 'CLOSED',
            exit_reason     = :reason,
            is_current      = false,
            updated_at      = :now
        WHERE id = :id
    """), {
        "id":     pos.pos_id,
        "ep":     Decimal(str(round(exit_price, 4))),
        "ed":     exit_date,
        "pnl":    Decimal(str(round(realized_pnl, 2))),
        "reason": exit_reason,
        "now":    now_utc(),
    })


def db_paper_trade(db, stock_id: uuid.UUID, side: str,
                   qty: float, fill_price: float, trade_date: date,
                   extra_meta: dict) -> uuid.UUID:
    trade_id = gen_id()
    raw_key = f"{RUN_TAG}_{trade_date}_{stock_id}_{side}_{trade_id}"
    ikey = hashlib.sha256(raw_key.encode()).hexdigest()[:64]
    meta = {"run_tag": RUN_TAG, "trade_date": str(trade_date), **extra_meta}
    db.execute(text("""
        INSERT INTO paper_trades
            (id, stock_id, side, quantity, fill_price, fill_quantity,
             status, idempotency_key, requested_at, filled_at, metadata)
        VALUES
            (:id, :sid, :side, :qty, :fp, :fq,
             'FILLED', :ikey, :req, :fill, :meta)
    """), {
        "id":   trade_id,
        "sid":  stock_id,
        "side": side,
        "qty":  Decimal(str(round(qty, 6))),
        "fp":   Decimal(str(round(fill_price, 4))),
        "fq":   Decimal(str(round(qty, 6))),
        "ikey": ikey,
        "req":  datetime.combine(trade_date, datetime.min.time()).replace(tzinfo=timezone.utc),
        "fill": datetime.combine(trade_date, datetime.min.time()).replace(tzinfo=timezone.utc),
        "meta": json.dumps(meta),
    })
    return trade_id


def db_cash_entry(db, entry_type: str, amount: float, balance_after: float,
                  ref_id: uuid.UUID | None, ref_type: str | None,
                  description: str, as_of: date):
    db.execute(text("""
        INSERT INTO portfolio_cash_ledger
            (id, entry_type, amount, balance_after, reference_id, reference_type,
             description, as_of_date, created_at, updated_at)
        VALUES
            (:id, :etype, :amt, :bal, :ref, :rtype, :desc, :aod, :now, :now)
    """), {
        "id":    gen_id(),
        "etype": entry_type,
        "amt":   Decimal(str(round(amount, 2))),
        "bal":   Decimal(str(round(balance_after, 2))),
        "ref":   ref_id,
        "rtype": ref_type,
        "desc":  description,
        "aod":   as_of,
        "now":   now_utc(),
    })


def db_nav_history(db, as_of: date, total_equity: float, cash: float,
                   market_value: float, unrealized_pnl: float,
                   realized_pnl_cum: float, open_positions: int,
                   day_return_pct: float | None):
    db.execute(text("""
        INSERT INTO portfolio_nav_history
            (id, as_of_date, total_equity, cash_balance, market_value,
             unrealized_pnl, realized_pnl_cumulative, open_positions,
             cash_pct, day_return_pct, created_at, updated_at)
        VALUES
            (:id, :aod, :te, :cash, :mv, :upnl, :rpnl, :op,
             :cpct, :dr, :now, :now)
        ON CONFLICT (as_of_date) DO UPDATE
        SET total_equity = EXCLUDED.total_equity,
            cash_balance = EXCLUDED.cash_balance,
            market_value = EXCLUDED.market_value,
            unrealized_pnl = EXCLUDED.unrealized_pnl,
            realized_pnl_cumulative = EXCLUDED.realized_pnl_cumulative,
            open_positions = EXCLUDED.open_positions,
            cash_pct = EXCLUDED.cash_pct,
            day_return_pct = EXCLUDED.day_return_pct,
            updated_at = EXCLUDED.updated_at
    """), {
        "id":   gen_id(),
        "aod":  as_of,
        "te":   Decimal(str(round(total_equity, 2))),
        "cash": Decimal(str(round(cash, 2))),
        "mv":   Decimal(str(round(market_value, 2))),
        "upnl": Decimal(str(round(unrealized_pnl, 2))),
        "rpnl": Decimal(str(round(realized_pnl_cum, 2))),
        "op":   open_positions,
        "cpct": Decimal(str(round(cash / total_equity if total_equity else 1.0, 4))),
        "dr":   Decimal(str(round(day_return_pct, 4))) if day_return_pct is not None else None,
        "now":  now_utc(),
    })


# ── Clean old backtest data ───────────────────────────────────────────────────
def clean_old_data(db):
    print("\nCleaning previous backtest data …")
    # Delete in FK-safe order: paper_trades → positions → cash_ledger → nav_history
    # portfolio_positions FK: recommendation_results.portfolio_position_id → set NULL first
    db.execute(text("""
        UPDATE recommendation_results SET portfolio_position_id = NULL
        WHERE portfolio_position_id IN (
            SELECT id FROM portfolio_positions WHERE portfolio_id = :pid
        )
    """), {"pid": PORTFOLIO_ID})
    r1 = db.execute(text("DELETE FROM paper_trades WHERE metadata->>'run_tag' = :tag OR metadata IS NULL"),
                      {"tag": RUN_TAG}).rowcount
    r2 = db.execute(text("DELETE FROM portfolio_positions WHERE portfolio_id = :pid"),
                      {"pid": PORTFOLIO_ID}).rowcount
    r3 = db.execute(text("DELETE FROM portfolio_cash_ledger")).rowcount
    r4 = db.execute(text("DELETE FROM portfolio_nav_history")).rowcount
    print(f"  Cleared: {r1} paper_trades, {r2} positions, {r3} cash_ledger, {r4} nav_history rows")


# ── Main backtest ─────────────────────────────────────────────────────────────
def run_backtest():
    engine = create_engine(DATABASE_URL)

    with Session(engine) as session:
        # Use session directly — conn reference goes stale after commit
        db = session

        # Load all data (read-only phase)
        print("\n[1/3] Loading data …")
        signals, all_ranks, trading_days, prices = load_data(db, START_DATE)

        # Build next-day map
        next_day: dict[date, date] = {trading_days[i]: trading_days[i+1]
                                       for i in range(len(trading_days)-1)}

        # Clean old data
        print("\n[2/3] Cleaning old backtest records …")
        clean_old_data(db)
        session.flush()

        # Seed initial capital in cash ledger
        db_cash_entry(db, "INITIAL_CAPITAL", INITIAL_CAPITAL, INITIAL_CAPITAL,
                      None, None, f"Backtest start ₹{INITIAL_CAPITAL:,.0f}", START_DATE)
        session.flush()

        # ── Simulation ────────────────────────────────────────────────────────
        print("\n[3/3] Running simulation …")
        cash             = INITIAL_CAPITAL
        positions: list[Position] = []
        closed_trades: list[ClosedTrade] = []
        realized_pnl_cum = 0.0
        pending_signals: list[dict] = []   # signals from N-1, execute on N
        prev_nav = INITIAL_CAPITAL
        commit_every = 50   # commit every N days to avoid huge transactions

        for day_idx, today in enumerate(trading_days):
            # Skip days before START_DATE
            if today < START_DATE:
                continue

            # ── Execute pending entries from yesterday's signals (T+1 entry) ──
            if pending_signals:
                open_stock_ids = {str(p.stock_id) for p in positions}
                slots_free = MAX_SLOTS - len(positions)
                for sig in pending_signals:
                    if slots_free <= 0:
                        break
                    sid_str = str(sig["stock_id"])
                    if sid_str in open_stock_ids:
                        continue
                    ep_raw = get_close(prices, sid_str, today)
                    if ep_raw is None:
                        continue
                    ep = slip(ep_raw, "BUY")
                    mult = CONVICTION_MULT.get(sig["conviction_band"], 0.75)
                    alloc = min(MAX_SLOT_ALLOC * mult, cash * 0.95)
                    if alloc < ep:
                        continue
                    qty = alloc / ep
                    cost = qty * ep
                    if cost > cash:
                        qty = (cash * 0.95) / ep
                        cost = qty * ep
                    if qty <= 0:
                        continue

                    pos_id = gen_id()
                    stop_price = round(ep * STOP_LOSS_FACTOR, 4)
                    pos = Position(
                        pos_id=pos_id,
                        stock_id=sig["stock_id"],
                        symbol=sig["symbol"],
                        strategy=sig["strategy"],
                        sector=sig["sector"],
                        entry_date=today,
                        entry_price=ep,
                        stop_price=stop_price,
                        qty=qty,
                        cost=cost,
                        conviction_band=sig["conviction_band"],
                        recommendation_result_id=sig["rec_result_id"],
                    )
                    positions.append(pos)
                    open_stock_ids.add(sid_str)
                    slots_free -= 1
                    cash -= cost

                    # DB writes
                    db_insert_position(db, pos)
                    trade_id = db_paper_trade(db, sig["stock_id"], "BUY", qty, ep, today,
                        {"symbol": sig["symbol"], "strategy": sig["strategy"],
                         "conviction_band": sig["conviction_band"],
                         "stop_price": stop_price})
                    db_cash_entry(db, "BUY", -cost, cash, trade_id, "paper_trade",
                                  f"BUY {sig['symbol']} {qty:.2f}@{ep:.2f}", today)
                pending_signals = []

            # ── Age all positions by 1 trading day ──
            for pos in positions:
                pos.trading_days_held += 1

            exited_ids: set[str] = set()

            # ── STOP-LOSS: triggered by today's close vs pre-set stop price ──
            for pos in list(positions):
                sid_str = str(pos.stock_id)
                if sid_str in exited_ids:
                    continue
                close = get_close(prices, sid_str, today)
                if close is None:
                    continue
                if close <= pos.stop_price:
                    # Exit at capped stop price (not worse than stop)
                    exit_price = pos.stop_price
                    proceeds = pos.qty * exit_price
                    pnl = proceeds - pos.cost
                    realized_pnl_cum += pnl
                    cash += proceeds

                    db_close_position(db, pos, exit_price, today, pnl, "STOP_LOSS")
                    trade_id = db_paper_trade(db, pos.stock_id, "SELL", pos.qty, exit_price, today,
                        {"symbol": pos.symbol, "exit_reason": "STOP_LOSS",
                         "entry_price": pos.entry_price, "pnl": round(pnl, 2)})
                    db_cash_entry(db, "SELL", proceeds, cash, trade_id, "paper_trade",
                                  f"STOP {pos.symbol} {pos.qty:.2f}@{exit_price:.2f} PnL={pnl:+.2f}", today)

                    closed_trades.append(ClosedTrade(
                        pos.symbol, pos.strategy, pos.entry_date, today,
                        pos.entry_price, exit_price, pos.qty, pos.cost,
                        pnl, pnl/pos.cost*100, pos.trading_days_held, "STOP_LOSS", pos.conviction_band
                    ))
                    exited_ids.add(sid_str)

            positions = [p for p in positions if str(p.stock_id) not in exited_ids]

            # ── TIME-STOP: exit after MAX_HOLD_DAYS ──
            for pos in list(positions):
                sid_str = str(pos.stock_id)
                if sid_str in exited_ids or pos.trading_days_held <= MAX_HOLD_DAYS:
                    continue
                close = get_close(prices, sid_str, today)
                if close is None:
                    continue
                exit_price = slip(close, "SELL")
                proceeds = pos.qty * exit_price
                pnl = proceeds - pos.cost
                realized_pnl_cum += pnl
                cash += proceeds

                db_close_position(db, pos, exit_price, today, pnl, "TIME_STOP")
                trade_id = db_paper_trade(db, pos.stock_id, "SELL", pos.qty, exit_price, today,
                    {"symbol": pos.symbol, "exit_reason": "TIME_STOP",
                     "entry_price": pos.entry_price, "hold_days": pos.trading_days_held, "pnl": round(pnl, 2)})
                db_cash_entry(db, "SELL", proceeds, cash, trade_id, "paper_trade",
                              f"TIME {pos.symbol} {pos.qty:.2f}@{exit_price:.2f} PnL={pnl:+.2f}", today)

                closed_trades.append(ClosedTrade(
                    pos.symbol, pos.strategy, pos.entry_date, today,
                    pos.entry_price, exit_price, pos.qty, pos.cost,
                    pnl, pnl/pos.cost*100, pos.trading_days_held, "TIME_STOP", pos.conviction_band
                ))
                exited_ids.add(sid_str)

            positions = [p for p in positions if str(p.stock_id) not in exited_ids]

            # ── RANK-DROP: use YESTERDAY'S ranks (N-1), not today ──
            yesterday = trading_days[day_idx - 1] if day_idx > 0 else None
            yesterday_ranks = all_ranks.get(yesterday, {}) if yesterday else {}
            for pos in list(positions):
                sid_str = str(pos.stock_id)
                if sid_str in exited_ids:
                    continue
                rank = yesterday_ranks.get(sid_str)
                if rank is None or rank <= RANK_DROP_THRESH:
                    continue
                close = get_close(prices, sid_str, today)
                if close is None:
                    continue
                exit_price = slip(close, "SELL")
                proceeds = pos.qty * exit_price
                pnl = proceeds - pos.cost
                realized_pnl_cum += pnl
                cash += proceeds

                db_close_position(db, pos, exit_price, today, pnl, "RANK_DROP")
                trade_id = db_paper_trade(db, pos.stock_id, "SELL", pos.qty, exit_price, today,
                    {"symbol": pos.symbol, "exit_reason": "RANK_DROP",
                     "rank": rank, "entry_price": pos.entry_price, "pnl": round(pnl, 2)})
                db_cash_entry(db, "SELL", proceeds, cash, trade_id, "paper_trade",
                              f"RANK {pos.symbol} rank={rank} {pos.qty:.2f}@{exit_price:.2f} PnL={pnl:+.2f}", today)

                closed_trades.append(ClosedTrade(
                    pos.symbol, pos.strategy, pos.entry_date, today,
                    pos.entry_price, exit_price, pos.qty, pos.cost,
                    pnl, pnl/pos.cost*100, pos.trading_days_held, "RANK_DROP", pos.conviction_band
                ))
                exited_ids.add(sid_str)

            positions = [p for p in positions if str(p.stock_id) not in exited_ids]

            # ── Queue TODAY's signals for execution TOMORROW (T+1) ──
            if today in signals:
                open_stock_ids = {str(p.stock_id) for p in positions}
                for sig in signals[today]:
                    if str(sig["stock_id"]) not in open_stock_ids:
                        pending_signals.append(sig)

            # ── MTM NAV for today ──
            market_value = 0.0
            unrealized_pnl = 0.0
            for pos in positions:
                close = get_close(prices, str(pos.stock_id), today)
                if close:
                    mv = pos.qty * close
                    market_value += mv
                    unrealized_pnl += mv - pos.cost
                else:
                    market_value += pos.cost
            total_equity = cash + market_value
            day_ret = (total_equity - prev_nav) / prev_nav * 100 if prev_nav > 0 else 0.0
            prev_nav = total_equity

            db_nav_history(db, today, total_equity, cash, market_value,
                           unrealized_pnl, realized_pnl_cum, len(positions), day_ret)

            # Periodic commit + progress
            if (day_idx + 1) % commit_every == 0:
                session.flush()
                session.commit()
                print(f"  Day {day_idx+1:>4}/{len(trading_days)} | {today} | "
                      f"NAV ₹{total_equity/1e6:.3f}M | Cash ₹{cash/1e6:.2f}M | "
                      f"Positions {len(positions)} | Trades {len(closed_trades)}")

        # ── Force-close all remaining positions at last trading day ──
        last_day = trading_days[-1]
        print(f"\nForce-closing {len(positions)} open positions at {last_day} …")
        for pos in positions:
            close = get_close(prices, str(pos.stock_id), last_day)
            if not close:
                continue
            exit_price = slip(close, "SELL")
            proceeds = pos.qty * exit_price
            pnl = proceeds - pos.cost
            realized_pnl_cum += pnl
            cash += proceeds

            db_close_position(db, pos, exit_price, last_day, pnl, "FORCE_CLOSE")
            trade_id = db_paper_trade(db, pos.stock_id, "SELL", pos.qty, exit_price, last_day,
                {"symbol": pos.symbol, "exit_reason": "FORCE_CLOSE",
                 "entry_price": pos.entry_price, "pnl": round(pnl, 2)})
            db_cash_entry(db, "SELL", proceeds, cash, trade_id, "paper_trade",
                          f"CLOSE {pos.symbol} {pos.qty:.2f}@{exit_price:.2f} PnL={pnl:+.2f}", last_day)
            closed_trades.append(ClosedTrade(
                pos.symbol, pos.strategy, pos.entry_date, last_day,
                pos.entry_price, exit_price, pos.qty, pos.cost,
                pnl, pnl/pos.cost*100, pos.trading_days_held, "FORCE_CLOSE", pos.conviction_band
            ))

        session.commit()
        print("  All committed to DB ✓")

        # ── Final report ──────────────────────────────────────────────────────
        print_report(closed_trades, cash, last_day)


def print_report(trades: list[ClosedTrade], final_cash: float, last_day: date):
    if not trades:
        print("No trades executed.")
        return

    final = final_cash
    wins   = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    stops  = [t for t in trades if t.exit_reason == "STOP_LOSS"]
    times  = [t for t in trades if t.exit_reason == "TIME_STOP"]
    ranks  = [t for t in trades if t.exit_reason == "RANK_DROP"]
    closes = [t for t in trades if t.exit_reason == "FORCE_CLOSE"]

    gp = sum(t.pnl for t in wins)
    gl = abs(sum(t.pnl for t in losses))
    pf = gp / gl if gl > 0 else 999.0
    wr = len(wins) / len(trades) * 100
    aw = sum(t.pnl_pct for t in wins) / len(wins) if wins else 0
    al = sum(t.pnl_pct for t in losses) / len(losses) if losses else 0
    years = (last_day - START_DATE).days / 365.25
    cagr  = ((final / INITIAL_CAPITAL) ** (1 / years) - 1) * 100
    total_ret = (final - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100

    print("\n" + "=" * 65)
    print("  HONEST BACKTEST RESULTS — 1% STOP-LOSS (T+1 Entry)")
    print("=" * 65)
    print(f"  Period        : {START_DATE}  →  {last_day}  ({years:.2f} yrs)")
    print(f"  Initial NAV   : ₹{INITIAL_CAPITAL/1e6:.2f}M")
    print(f"  Final NAV     : ₹{final/1e6:.3f}M")
    print(f"  Total Return  : {total_ret:+.2f}%")
    print(f"  CAGR          : {cagr:+.2f}%")
    print()
    print(f"  Total Trades  : {len(trades)}")
    print(f"    Stop-Loss   : {len(stops)} ({len(stops)/len(trades)*100:.1f}%)")
    print(f"    Time-Stop   : {len(times)} ({len(times)/len(trades)*100:.1f}%)")
    print(f"    Rank-Drop   : {len(ranks)} ({len(ranks)/len(trades)*100:.1f}%)")
    print(f"    Force-Close : {len(closes)} ({len(closes)/len(trades)*100:.1f}%)")
    print()
    print(f"  Win Rate      : {wr:.1f}%   ({len(wins)}W / {len(losses)}L)")
    print(f"  Profit Factor : {pf:.2f}x")
    print(f"  Avg Win       : {aw:+.2f}%")
    print(f"  Avg Loss      : {al:+.2f}%")
    print(f"  Gross Profit  : ₹{gp/1e6:.3f}M")
    print(f"  Gross Loss    : ₹{gl/1e6:.3f}M")

    # Monthly P&L
    print("\n  Monthly P&L:")
    print(f"  {'Month':>8} {'Trades':>7} {'PnL ₹':>12} {'PnL%':>8} {'WR%':>6}")
    print("  " + "-" * 46)
    from collections import defaultdict
    monthly: dict[str, list[ClosedTrade]] = defaultdict(list)
    for t in trades:
        monthly[t.exit_date.strftime("%Y-%m")].append(t)
    for ym in sorted(monthly):
        mt = monthly[ym]
        mpnl = sum(t.pnl for t in mt)
        mwr  = sum(1 for t in mt if t.pnl > 0) / len(mt) * 100
        mpct = mpnl / (INITIAL_CAPITAL + sum(t.pnl for t in trades
               if t.exit_date.strftime("%Y-%m") < ym)) * 100
        print(f"  {ym:>8}  {len(mt):>6}  ₹{mpnl/1e3:>+9.1f}k  {mpct:>+7.2f}%  {mwr:>5.1f}%")

    print("=" * 65)


if __name__ == "__main__":
    run_backtest()
