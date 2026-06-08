#!/usr/bin/env python3
"""
Pi-PM Paper Trade Replay v2 — Jun 2022 → Jun 2026
Capital: ₹1,00,000  |  Aggressive mode  |  No HITL, No AI Committee

Stop-loss rule (new in v2):
  - If EOD close ≤ entry_price × 0.92 (loss ≥ 8%), exit at exactly
    entry_price × 0.92 (capped fill — NOT the actual worse close).
  - Stop-loss exits run FIRST each day, before ExitMonitorService.
  - This matches ADR-033 advisory_stop_pct = -8% with price-floor capping.

Replay rules:
  - BUY: auto-execute all BUY signals, ranked by conviction desc
  - EXIT (in order): stop-loss cap → ExitMonitorService swing triggers
  - Max 5 concurrent positions (slots)
  - Position size: equal weight (₹20,000 per slot base)
  - Conviction multiplier: EXCEPTIONAL=1.15×, HIGH=1.0×, MEDIUM=0.75×
  - Slippage: +5 bps BUY, -5 bps SELL (NOT applied to stop-loss exit —
    stop price already factors in the -8% cap; we use the capped price as-is)
  - Fee: ₹20 per leg flat

All trades land in DB tables:
  paper_trades, portfolio_positions, portfolio_cash_ledger, portfolio_nav_history
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.constants import TradeSide, TradeStatus
from app.models.portfolio_analytics import PortfolioNavHistory
from app.models.portfolio_position import PortfolioConfig, PortfolioPosition
from app.models.paper_trade import PaperTrade
from app.portfolio.exit_monitor.service import ExitMonitorService
from app.services.paper_trade_service import PaperTradeService
from app.services.portfolio_service import PortfolioService

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://pipm:pipm@localhost:5432/pipm",
)
PORTFOLIO_ID = UUID("00000000-0000-4000-8000-000000000010")
INITIAL_CAPITAL = 1_000_000.0
MAX_SLOTS = 10
MAX_TRADE_CAPITAL = 50_000.0                       # per-trade cap
START_DATE = "2022-06-01"
END_DATE = "2026-06-07"
MAX_HOLDING_DAYS = 30
CONVICTION_MULT = {"EXCEPTIONAL": 1.15, "HIGH": 1.00, "MEDIUM": 0.75}
SLIPPAGE_BPS = 5.0
FEE_PER_LEG = 0.0                                  # fees excluded
STOP_LOSS_PCT = -8.0                               # advisory stop
STOP_LOSS_FACTOR = 1.0 + (STOP_LOSS_PCT / 100)    # 0.92 — capped exit price


def clean_portfolio(db: Session) -> None:
    """Wipe all portfolio state for a clean replay.

    Uses TRUNCATE (instant) for all tables — avoids dead-tuple scan hell
    that makes DELETE hang for minutes on bloated tables.
    TRUNCATE CASCADE handles FK dependencies automatically.
    """
    print("  Cleaning portfolio state...")
    # Single TRUNCATE cascade — instant regardless of row count or bloat
    db.execute(text("""
        TRUNCATE TABLE
            portfolio_nav_history,
            portfolio_cash_ledger,
            portfolio_exit_recommendations,
            portfolio_reconciliation_reports,
            paper_trades,
            portfolio_positions,
            portfolio_configs
        RESTART IDENTITY CASCADE
    """))
    db.commit()
    print("  ✓ Portfolio cleaned")


def setup_aggressive_config(db: Session) -> PortfolioConfig:
    """Create aggressive portfolio config: ₹1,00,000, full deploy, max slots."""
    cfg = PortfolioConfig(
        portfolio_id=PORTFOLIO_ID,
        is_active=True,
        total_equity=INITIAL_CAPITAL,
        deploy_pct=1.0,
        cash_floor_pct=0.0,
        reserve_pct=0.0,
        regime_slots={
            "risk_on":   {"max_positions": MAX_SLOTS, "max_buy_per_day": MAX_SLOTS},
            "neutral":   {"max_positions": MAX_SLOTS, "max_buy_per_day": MAX_SLOTS},
            "defensive": {"max_positions": MAX_SLOTS, "max_buy_per_day": MAX_SLOTS},
            "crisis":    {"max_positions": MAX_SLOTS, "max_buy_per_day": MAX_SLOTS},
        },
        single_name_cap_pct=0.25,
        sector_cap_pct=1.0,
        slippage_bps=SLIPPAGE_BPS,
        fee_per_leg=FEE_PER_LEG,
        execution_mode="PAPER",
        notes=f"Aggressive replay {START_DATE}→{END_DATE} | ₹10,00,000 | 10 slots | ₹50k/trade | No fees | Stop -8% capped | v2",
    )
    db.add(cfg)
    db.flush()
    return cfg


def load_all_buy_signals(db: Session) -> dict[date, list[dict]]:
    """Load all BUY recommendation_results grouped by as_of_date."""
    rows = db.execute(text(f"""
        SELECT rrun.as_of_date,
               rr.id::text,
               rr.stock_id::text,
               s.symbol,
               s.sector,
               r.strategy_name,
               rr.rank,
               rr.conviction_score,
               rr.conviction_band
        FROM recommendation_results rr
        JOIN recommendation_runs rrun ON rr.recommendation_run_id = rrun.id
        JOIN ranking_runs r ON rrun.ranking_run_id = r.id
        JOIN stocks s ON rr.stock_id = s.id
        WHERE rr.action = 'BUY'
          AND rrun.as_of_date >= '{START_DATE}'
          AND rrun.as_of_date <= '{END_DATE}'
        ORDER BY rrun.as_of_date, rr.conviction_score DESC, rr.rank
    """)).fetchall()

    signals: dict[date, list[dict]] = defaultdict(list)
    seen: set = set()
    for row in rows:
        key = (row[0], row[2])  # (date, stock_id) — dedup cross-strategy
        if key not in seen:
            seen.add(key)
            signals[row[0]].append({
                "rec_result_id": row[1],
                "stock_id": row[2],
                "symbol": row[3],
                "sector": row[4],
                "strategy": row[5],
                "rank": row[6],
                "conviction": row[7],
                "conviction_band": row[8],
            })
    return signals


def get_eod_close(db: Session, stock_id: str, target_date: date) -> float | None:
    """Get EOD close for a stock on or before target_date (no slippage)."""
    row = db.execute(text("""
        SELECT close FROM market_data
        WHERE stock_id = :sid AND date <= :d
        ORDER BY date DESC LIMIT 1
    """), {"sid": stock_id, "d": target_date}).fetchone()
    return float(row[0]) if row else None


def get_fill_price(db: Session, stock_id: str, target_date: date, side: str) -> float | None:
    """Get fill price (close ± slippage) for BUY/SELL entries."""
    close = get_eod_close(db, stock_id, target_date)
    if close is None:
        return None
    slip = SLIPPAGE_BPS / 10_000
    return close * (1 + slip) if side == "BUY" else close * (1 - slip)


def get_trading_days(db: Session, stock_id: str, start: date, end: date) -> int:
    row = db.execute(text("""
        SELECT COUNT(*) FROM market_data
        WHERE stock_id = :sid AND date > :s AND date <= :e
    """), {"sid": stock_id, "s": start, "e": end}).fetchone()
    return int(row[0]) if row else 0


_cash_balance: float = 0.0


def record_cash(
    db: Session, entry_type: str, amount: float, as_of_date: date, description: str
) -> None:
    global _cash_balance
    _cash_balance += amount
    db.execute(text("""
        INSERT INTO portfolio_cash_ledger
            (id, entry_type, amount, balance_after, as_of_date, description, created_at, updated_at)
        VALUES
            (:id, :etype, :amt, :bal, :aod, :desc, NOW(), NOW())
    """), {
        "id": str(uuid4()),
        "etype": entry_type,
        "amt": round(amount, 2),
        "bal": round(_cash_balance, 2),
        "aod": as_of_date,
        "desc": description,
    })


def close_position_stop_loss(
    db: Session,
    pos: dict,
    today: date,
    completed_trades: list[dict],
    cash: float,
) -> tuple[float, bool]:
    """
    Execute a stop-loss exit at the CAPPED price (entry_price × 0.92).

    Returns (updated_cash, success).
    """
    entry_price = pos["entry_price"]
    capped_exit_price = round(entry_price * STOP_LOSS_FACTOR, 4)   # -8% cap
    qty = pos["qty"]
    proceeds = qty * capped_exit_price - FEE_PER_LEG
    realized_pnl = proceeds - pos["cost"]
    hold_days = get_trading_days(db, pos["stock_id"], pos["entry_date"], today)

    # Close the DB portfolio_position row
    pp = db.scalar(
        select(PortfolioPosition).where(
            PortfolioPosition.stock_id == UUID(pos["stock_id"]),
            PortfolioPosition.is_current.is_(True),
            PortfolioPosition.portfolio_id == PORTFOLIO_ID,
            PortfolioPosition.position_status == "OPEN",
        )
    )
    if pp:
        pp.exit_price = capped_exit_price
        pp.exit_date = today
        pp.realized_pnl = realized_pnl
        pp.unrealized_pnl = 0.0
        pp.is_current = False
        pp.position_status = "CLOSED"

    # Write SELL paper trade
    idem = f"stoploss-{pos['stock_id']}-{today}"
    pt = PaperTrade(
        stock_id=UUID(pos["stock_id"]),
        side=TradeSide.SELL.value,
        quantity=qty,
        fill_price=capped_exit_price,
        fill_quantity=qty,
        status=TradeStatus.FILLED.value,
        idempotency_key=idem,
        requested_at=datetime(today.year, today.month, today.day, 15, 30, tzinfo=UTC),
        filled_at=datetime(today.year, today.month, today.day, 15, 30, tzinfo=UTC),
        metadata_={
            "symbol": pos["symbol"],
            "strategy": pos["strategy"],
            "exit_reason": "EXIT_STOP_LOSS",
            "entry_price": entry_price,
            "capped_exit_price": capped_exit_price,
            "stop_loss_pct": STOP_LOSS_PCT,
            "hold_days": hold_days,
        },
    )
    db.add(pt)

    record_cash(
        db, "TRADE_SELL", proceeds, today,
        f"STOP-LOSS {pos['symbol']} {qty:.2f}@{capped_exit_price:.2f} "
        f"[cap={STOP_LOSS_PCT}% entry={entry_price:.2f}]"
    )

    completed_trades.append({
        "symbol": pos["symbol"],
        "strategy": pos["strategy"],
        "entry_date": pos["entry_date"],
        "exit_date": today,
        "entry_price": entry_price,
        "exit_price": capped_exit_price,
        "qty": qty,
        "pnl": realized_pnl,
        "pnl_pct": realized_pnl / pos["cost"] * 100,
        "hold_days": hold_days,
        "exit_reason": "EXIT_STOP_LOSS",
        "conviction_band": pos["conviction_band"],
    })

    return cash + proceeds, True


def run_replay():
    global _cash_balance
    engine = create_engine(DATABASE_URL)

    with Session(engine) as db:
        print("\n=== PI-PM PAPER TRADE REPLAY v2 ===")
        print(f"    Capital : ₹{INITIAL_CAPITAL:,.0f}  |  {MAX_SLOTS} slots  |  ₹{MAX_TRADE_CAPITAL:,.0f}/trade  |  No fees")
        print(f"    Period  : {START_DATE} → {END_DATE}")
        print(f"    Stop-loss: {STOP_LOSS_PCT}% capped (exit at entry × {STOP_LOSS_FACTOR})\n")

        # ── Setup ──────────────────────────────────────────────────────────────
        clean_portfolio(db)
        _cash_balance = 0.0  # reset global after clean
        cfg = setup_aggressive_config(db)

        record_cash(
            db, "INITIAL_CAPITAL", INITIAL_CAPITAL,
            date(2022, 6, 1), f"Initial capital ₹{INITIAL_CAPITAL:,.0f}"
        )
        db.commit()

        # ── Load signals ───────────────────────────────────────────────────────
        print("  Loading signals...")
        buy_signals = load_all_buy_signals(db)

        trading_days = [
            row[0] for row in db.execute(text(f"""
                SELECT DISTINCT date FROM market_data
                WHERE date >= '{START_DATE}' AND date <= '{END_DATE}'
                ORDER BY date
            """)).fetchall()
        ]
        print(
            f"  {len(trading_days)} trading days | "
            f"{sum(len(v) for v in buy_signals.values())} BUY signals\n"
        )

        # ── Simulation state ───────────────────────────────────────────────────
        cash = INITIAL_CAPITAL
        open_positions: list[dict] = []
        completed_trades: list[dict] = []
        nav_by_date: list[tuple[date, float]] = []
        stop_loss_count = 0
        total_fees = 0.0
        day_count = 0

        portfolio_svc = PortfolioService(db, portfolio_id=PORTFOLIO_ID)
        paper_svc = PaperTradeService(db, portfolio_service=portfolio_svc)
        exit_monitor = ExitMonitorService(db)

        for today in trading_days:
            day_count += 1
            if day_count % 250 == 0:
                print(
                    f"  [{today}] {len(open_positions)} open | "
                    f"₹{cash:,.0f} cash | {stop_loss_count} stops so far"
                )

            exited_stock_ids: set[str] = set()

            # ── 1. Stop-loss exits (FIRST — capped at -8%) ────────────────────
            for pos in list(open_positions):
                if pos["stock_id"] in exited_stock_ids:
                    continue
                eod_close = get_eod_close(db, pos["stock_id"], today)
                if eod_close is None:
                    continue

                unrealized_pct = (eod_close - pos["entry_price"]) / pos["entry_price"] * 100
                if unrealized_pct <= STOP_LOSS_PCT:
                    cash, ok = close_position_stop_loss(db, pos, today, completed_trades, cash)
                    if ok:
                        exited_stock_ids.add(pos["stock_id"])
                        total_fees += FEE_PER_LEG
                        stop_loss_count += 1

            open_positions = [p for p in open_positions if p["stock_id"] not in exited_stock_ids]
            db.flush()

            # ── 2. Swing exits via ExitMonitorService ─────────────────────────
            swing_exited: set[str] = set()
            exit_recs = exit_monitor.run(today)
            db.flush()

            for exit_rec in exit_recs:
                if exit_rec.status != "PENDING":
                    continue
                pos_row = db.get(PortfolioPosition, exit_rec.portfolio_position_id)
                if pos_row is None or pos_row.position_status != "OPEN":
                    continue
                mem_pos = next(
                    (p for p in open_positions if p["stock_id"] == str(exit_rec.stock_id)),
                    None,
                )
                try:
                    trade = paper_svc.execute_position_exit(
                        stock_id=exit_rec.stock_id,
                        as_of_date=today,
                        exit_triggers=list(exit_rec.triggers or []),
                        portfolio_exit_recommendation_id=exit_rec.id,
                        idempotency_key=f"replay-exit-monitor:{exit_rec.id}",
                    )
                    exit_monitor.confirm(exit_rec.id)
                    swing_exited.add(str(exit_rec.stock_id))

                    exit_price = float(trade.fill_price)
                    qty = float(trade.fill_quantity)
                    proceeds = qty * exit_price - FEE_PER_LEG
                    cash += proceeds
                    total_fees += FEE_PER_LEG

                    if mem_pos:
                        realized_pnl = proceeds - mem_pos["cost"]
                        hold_days = (
                            exit_rec.days_held
                            or get_trading_days(db, mem_pos["stock_id"], mem_pos["entry_date"], today)
                        )
                        completed_trades.append({
                            "symbol": mem_pos["symbol"],
                            "strategy": mem_pos["strategy"],
                            "entry_date": mem_pos["entry_date"],
                            "exit_date": today,
                            "entry_price": mem_pos["entry_price"],
                            "exit_price": exit_price,
                            "qty": qty,
                            "pnl": realized_pnl,
                            "pnl_pct": realized_pnl / mem_pos["cost"] * 100,
                            "hold_days": hold_days,
                            "exit_reason": ",".join(exit_rec.triggers or []),
                            "conviction_band": mem_pos["conviction_band"],
                        })
                except Exception as exc:
                    print(f"  ⚠ Swing exit failed {exit_rec.stock_id} on {today}: {exc}")

            open_positions = [p for p in open_positions if p["stock_id"] not in swing_exited]
            db.flush()

            # ── 3. Process entries ─────────────────────────────────────────────
            if today in buy_signals:
                open_syms = {p["stock_id"] for p in open_positions}
                slots_free = MAX_SLOTS - len(open_positions)

                for sig in buy_signals[today]:
                    if slots_free <= 0:
                        break
                    if sig["stock_id"] in open_syms:
                        continue

                    stock_id = UUID(sig["stock_id"])
                    entry_price = get_fill_price(db, sig["stock_id"], today, side="BUY")
                    if not entry_price:
                        continue

                    mult = CONVICTION_MULT.get(sig["conviction_band"], 0.75)
                    alloc = min(MAX_TRADE_CAPITAL * mult, cash * 0.95)
                    if alloc < entry_price:
                        continue

                    qty = alloc / entry_price
                    cost = qty * entry_price + FEE_PER_LEG
                    if cost > cash:
                        qty = (cash - FEE_PER_LEG) / entry_price
                        cost = qty * entry_price + FEE_PER_LEG
                    if qty <= 0:
                        continue

                    cash -= cost
                    total_fees += FEE_PER_LEG

                    # Compute stop-loss price stored on position for reference
                    stop_price = round(entry_price * STOP_LOSS_FACTOR, 4)

                    pp = PortfolioPosition(
                        id=uuid4(),
                        portfolio_id=PORTFOLIO_ID,
                        stock_id=stock_id,
                        recommendation_result_id=UUID(sig["rec_result_id"]),
                        quantity=qty,
                        avg_cost=entry_price,
                        entry_price=entry_price,
                        entry_date=today,
                        market_value=qty * entry_price,
                        unrealized_pnl=0.0,
                        conviction_band=sig["conviction_band"],
                        strategy_name=sig["strategy"],
                        sector=sig["sector"],
                        stop_loss_price=stop_price,
                        as_of=datetime(today.year, today.month, today.day, 15, 0, tzinfo=UTC),
                        is_current=True,
                        position_status="OPEN",
                    )
                    db.add(pp)

                    idem = f"entry-{sig['stock_id']}-{today}"
                    pt = PaperTrade(
                        stock_id=stock_id,
                        side=TradeSide.BUY.value,
                        quantity=qty,
                        fill_price=entry_price,
                        fill_quantity=qty,
                        status=TradeStatus.FILLED.value,
                        idempotency_key=idem,
                        requested_at=datetime(today.year, today.month, today.day, 15, 0, tzinfo=UTC),
                        filled_at=datetime(today.year, today.month, today.day, 15, 0, tzinfo=UTC),
                        metadata_={
                            "symbol": sig["symbol"],
                            "strategy": sig["strategy"],
                            "conviction_band": sig["conviction_band"],
                            "conviction_score": sig["conviction"],
                            "alloc": round(alloc, 2),
                            "mult": mult,
                            "stop_loss_price": stop_price,
                        },
                    )
                    db.add(pt)

                    record_cash(
                        db, "TRADE_BUY", -cost, today,
                        f"BUY {sig['symbol']} {qty:.2f}@{entry_price:.2f} "
                        f"[{sig['conviction_band']}] stop@{stop_price:.2f}"
                    )

                    open_positions.append({
                        "stock_id": sig["stock_id"],
                        "symbol": sig["symbol"],
                        "strategy": sig["strategy"],
                        "entry_date": today,
                        "entry_price": entry_price,
                        "qty": qty,
                        "cost": cost,
                        "conviction_band": sig["conviction_band"],
                    })
                    open_syms.add(sig["stock_id"])
                    slots_free -= 1

                db.flush()

            # ── 4. Mark-to-market NAV ──────────────────────────────────────────
            mtm = cash
            for pos in open_positions:
                eod = get_eod_close(db, pos["stock_id"], today)
                if eod:
                    mtm += pos["qty"] * eod
                else:
                    mtm += pos["cost"]

            nav_by_date.append((today, mtm))

            # Record NAV monthly (reduce DB writes)
            if today.day == 1 or today == trading_days[-1]:
                invested = mtm - cash
                rpnl = sum(t["pnl"] for t in completed_trades)
                cash_pct = cash / mtm if mtm > 0 else 0
                db.execute(text("""
                    INSERT INTO portfolio_nav_history
                        (id, as_of_date, total_equity, cash_balance, market_value,
                         unrealized_pnl, realized_pnl_cumulative, open_positions,
                         cash_pct, created_at, updated_at)
                    VALUES
                        (:id, :aod, :nav, :cash, :mv, :upnl, :rpnl, :npos, :cpct, NOW(), NOW())
                    ON CONFLICT DO NOTHING
                """), {
                    "id": str(uuid4()), "aod": today,
                    "nav": round(mtm, 2), "cash": round(cash, 2),
                    "mv": round(invested, 2),
                    "upnl": round(invested - sum(p["cost"] for p in open_positions), 2),
                    "rpnl": round(rpnl, 2),
                    "npos": len(open_positions),
                    "cpct": round(cash_pct, 4),
                })

        # ── Force-close remaining positions at last EOD price ──────────────────
        print(f"\n  Force-closing {len(open_positions)} remaining open positions...")
        sim_end = trading_days[-1]
        for pos in open_positions:
            fill = get_fill_price(db, pos["stock_id"], sim_end, side="SELL")
            if not fill:
                continue
            proceeds = pos["qty"] * fill - FEE_PER_LEG
            realized_pnl = proceeds - pos["cost"]
            cash += proceeds
            total_fees += FEE_PER_LEG
            hold_days = get_trading_days(db, pos["stock_id"], pos["entry_date"], sim_end)

            pp = db.scalar(
                select(PortfolioPosition).where(
                    PortfolioPosition.stock_id == UUID(pos["stock_id"]),
                    PortfolioPosition.is_current.is_(True),
                    PortfolioPosition.portfolio_id == PORTFOLIO_ID,
                )
            )
            if pp:
                pp.exit_price = fill
                pp.exit_date = sim_end
                pp.realized_pnl = realized_pnl
                pp.unrealized_pnl = 0.0
                pp.is_current = False
                pp.position_status = "CLOSED"

            completed_trades.append({
                "symbol": pos["symbol"], "strategy": pos["strategy"],
                "entry_date": pos["entry_date"], "exit_date": sim_end,
                "entry_price": pos["entry_price"], "exit_price": fill,
                "qty": pos["qty"], "pnl": realized_pnl,
                "pnl_pct": realized_pnl / pos["cost"] * 100,
                "hold_days": hold_days, "exit_reason": "FORCE_CLOSE_END",
                "conviction_band": pos["conviction_band"],
            })

        db.commit()

        # ── Final Report ───────────────────────────────────────────────────────
        final_value = cash
        total_pnl = final_value - INITIAL_CAPITAL
        total_return = total_pnl / INITIAL_CAPITAL * 100
        years = (sim_end - date(2022, 6, 1)).days / 365.25
        cagr = ((final_value / INITIAL_CAPITAL) ** (1 / years) - 1) * 100 if years > 0 else 0

        wins = [t for t in completed_trades if t["pnl"] > 0]
        losses = [t for t in completed_trades if t["pnl"] <= 0]
        stop_exits = [t for t in completed_trades if t["exit_reason"] == "EXIT_STOP_LOSS"]
        win_rate = len(wins) / len(completed_trades) * 100 if completed_trades else 0
        avg_win = sum(t["pnl_pct"] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t["pnl_pct"] for t in losses) / len(losses) if losses else 0
        gross_profit = sum(t["pnl"] for t in wins)
        gross_loss = abs(sum(t["pnl"] for t in losses))
        pf = gross_profit / gross_loss if gross_loss > 0 else 999

        peak, max_dd = INITIAL_CAPITAL, 0.0
        for _, val in nav_by_date:
            if val > peak:
                peak = val
            dd = (peak - val) / peak * 100
            if dd > max_dd:
                max_dd = dd

        # Per-strategy breakdown
        strats = {}
        for s in ["breakout_v1", "momentum_v1", "reversal_v1"]:
            st = [t for t in completed_trades if t["strategy"] == s]
            if not st:
                continue
            sw = [t for t in st if t["pnl"] > 0]
            sl = [t for t in st if t["pnl"] <= 0]
            ss = [t for t in st if t["exit_reason"] == "EXIT_STOP_LOSS"]
            strats[s] = {
                "n": len(st), "wr": len(sw)/len(st)*100,
                "pnl": sum(t["pnl"] for t in st),
                "aw": sum(t["pnl_pct"] for t in sw)/len(sw) if sw else 0,
                "al": sum(t["pnl_pct"] for t in sl)/len(sl) if sl else 0,
                "pf": (sum(t["pnl"] for t in sw) /
                       abs(sum(t["pnl"] for t in sl)))
                      if sl and sum(t["pnl"] for t in sl) != 0 else 99,
                "stops": len(ss),
            }

        yearly: dict[int, dict] = defaultdict(lambda: defaultdict(float))
        for t in completed_trades:
            yearly[t["exit_date"].year]["total"] += t["pnl"]
            yearly[t["exit_date"].year][t["strategy"]] += t["pnl"]

        by_pct = sorted(completed_trades, key=lambda t: t["pnl_pct"])

        W = 70
        print("\n" + "=" * W)
        print("  PI-PM PAPER TRADE REPLAY v2  |  Jun 2022 → Jun 2026")
        print(f"  Capital: ₹{INITIAL_CAPITAL:,.0f}  |  Stop-loss: {STOP_LOSS_PCT}% capped")
        print("=" * W)

        print(f"\n{'─'*W}")
        print("  PORTFOLIO OUTCOME")
        print(f"{'─'*W}")
        print(f"  Starting Capital  : ₹{INITIAL_CAPITAL:>10,.0f}")
        print(f"  Final Value       : ₹{final_value:>10,.0f}")
        print(f"  Total P&L         : ₹{total_pnl:>+10,.0f}")
        print(f"  Total Return      : {total_return:>+9.1f}%")
        print(f"  CAGR              : {cagr:>+9.1f}%   ({years:.1f} yrs)")
        print(f"  Max Drawdown      : {max_dd:>9.1f}%")
        print(f"  Total Fees Paid   : ₹{total_fees:>10,.0f}")

        print(f"\n{'─'*W}")
        print("  TRADE STATISTICS")
        print(f"{'─'*W}")
        print(f"  Total Trades      : {len(completed_trades):>5}  ({len(wins)}W / {len(losses)}L)")
        print(f"  Win Rate          : {win_rate:>8.1f}%")
        print(f"  Avg Win           : {avg_win:>+8.1f}%")
        print(f"  Avg Loss          : {avg_loss:>+8.1f}%")
        print(f"  Profit Factor     : {pf:>8.2f}x")
        print(f"  Stop-loss exits   : {len(stop_exits):>5}  ({len(stop_exits)/len(completed_trades)*100:.1f}% of all trades)" if completed_trades else "")
        print(f"  Stop-loss cap     : {STOP_LOSS_PCT}%  (floor = entry × {STOP_LOSS_FACTOR})")

        print(f"\n{'─'*W}")
        print("  PER-STRATEGY")
        print(f"{'─'*W}")
        print(f"  {'Strategy':<16} {'N':>4} {'Win%':>6} {'AvgW':>7} {'AvgL':>7} {'PF':>5} {'Stops':>6} {'P&L':>10}")
        for s, v in strats.items():
            print(
                f"  {s:<16} {v['n']:>4} {v['wr']:>5.1f}% "
                f"{v['aw']:>+6.1f}% {v['al']:>+6.1f}% "
                f"{v['pf']:>5.2f} {v['stops']:>6} ₹{v['pnl']:>+8,.0f}"
            )

        print(f"\n{'─'*W}")
        print("  YEARLY P&L")
        print(f"{'─'*W}")
        for yr in sorted(yearly):
            tot = yearly[yr]["total"]
            bar = ("▲" if tot >= 0 else "▼") * min(int(abs(tot) / 3000), 15)
            b = yearly[yr].get("breakout_v1", 0)
            m = yearly[yr].get("momentum_v1", 0)
            r = yearly[yr].get("reversal_v1", 0)
            print(f"  {yr}  ₹{tot:>+9,.0f}  [B:{b:>+7,.0f} M:{m:>+7,.0f} R:{r:>+7,.0f}]  {bar}")

        print(f"\n{'─'*W}")
        print("  TOP 5 BEST TRADES")
        print(f"{'─'*W}")
        for t in by_pct[-5:][::-1]:
            print(
                f"  {t['symbol']:<18} {t['strategy']:<12} "
                f"{t['entry_date']}→{t['exit_date']}  "
                f"{t['pnl_pct']:>+6.1f}%  ₹{t['pnl']:>+8,.0f}"
            )

        print(f"\n{'─'*W}")
        print("  TOP 5 WORST TRADES (stop-loss shown)")
        print(f"{'─'*W}")
        for t in by_pct[:5]:
            stop_tag = " [STOP]" if t["exit_reason"] == "EXIT_STOP_LOSS" else ""
            print(
                f"  {t['symbol']:<18} {t['strategy']:<12} "
                f"{t['entry_date']}→{t['exit_date']}  "
                f"{t['pnl_pct']:>+6.1f}%  ₹{t['pnl']:>+8,.0f}{stop_tag}"
            )

        print(f"\n{'─'*W}")
        print("  DATABASE STATE")
        print(f"{'─'*W}")
        pt_count = db.scalar(text("SELECT COUNT(*) FROM paper_trades"))
        pp_count = db.scalar(
            text("SELECT COUNT(*) FROM portfolio_positions WHERE portfolio_id = :pid"),
            {"pid": str(PORTFOLIO_ID)},
        )
        cl_count = db.scalar(text("SELECT COUNT(*) FROM portfolio_cash_ledger"))
        open_now = db.scalar(
            text("SELECT COUNT(*) FROM portfolio_positions WHERE portfolio_id=:pid AND position_status='OPEN'"),
            {"pid": str(PORTFOLIO_ID)},
        )
        print(f"  paper_trades            : {pt_count:>5} rows")
        print(f"  portfolio_positions     : {pp_count:>5} rows (OPEN + CLOSED)")
        print(f"  portfolio_cash_ledger   : {cl_count:>5} rows")
        print(f"  Open positions today    : {open_now:>5}")
        print()


if __name__ == "__main__":
    run_replay()
