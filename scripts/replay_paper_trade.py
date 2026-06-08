#!/usr/bin/env python3
"""
Pi-PM Paper Trade Replay — Jan 2022 → Jun 2026
Capital: ₹1,00,000  |  Aggressive mode  |  No HITL, No AI Committee

Replay rules:
  - BUY: auto-execute all BUY signals, ranked by conviction desc
  - EXIT: ExitMonitorService (same as daily pilot / paper UI) — rank drop, time stop, etc.
    Creates portfolio_exit_recommendations rows, then auto-executes paper SELL for simulation continuity.
  - Max 5 concurrent positions (slots)
  - Position size: equal weight (₹20,000 per slot base)
  - Conviction multiplier: EXCEPTIONAL=1.15×, HIGH=1.0×, MEDIUM=0.75×
  - Slippage: +5 bps BUY, -5 bps SELL
  - Fee: ₹20 per leg flat

Uses the actual service layer — trades land in DB tables:
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
from app.db.repositories.market_data_repository import MarketDataRepository
from app.models.auth import Portfolio
from app.models.paper_trade import PaperTrade
from app.models.portfolio_analytics import PortfolioNavHistory
from app.models.portfolio_position import PortfolioConfig, PortfolioPosition
from app.models.recommendation import RecommendationResult, RecommendationRun
from app.models.stock import Stock
from app.portfolio.exit_monitor.service import ExitMonitorService
from app.services.paper_trade_service import PaperTradeService
from app.services.portfolio_service import PortfolioService

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://pipm:pipm@localhost:5432/pipm",
)
PORTFOLIO_ID = UUID("00000000-0000-4000-8000-000000000010")
INITIAL_CAPITAL = 100_000.0
MAX_SLOTS = 5
MAX_HOLDING_DAYS = 30
RANK_EXIT_THRESHOLD = 40
SLOT_BUDGET = INITIAL_CAPITAL / MAX_SLOTS  # ₹20,000 per slot
CONVICTION_MULT = {"EXCEPTIONAL": 1.15, "HIGH": 1.00, "MEDIUM": 0.75}
SLIPPAGE_BPS = 5.0
FEE_PER_LEG = 20.0


def clean_portfolio(db: Session) -> None:
    """Wipe all portfolio state for a clean replay."""
    print("  Cleaning portfolio state...")
    db.execute(text("DELETE FROM portfolio_nav_history"))
    db.execute(text("DELETE FROM portfolio_cash_ledger"))
    db.execute(text("DELETE FROM portfolio_exit_recommendations"))
    db.execute(text("DELETE FROM portfolio_positions WHERE portfolio_id = :pid"),
               {"pid": str(PORTFOLIO_ID)})
    db.execute(text("DELETE FROM paper_trades"))
    db.execute(text("DELETE FROM portfolio_configs WHERE portfolio_id = :pid"),
               {"pid": str(PORTFOLIO_ID)})
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
        notes="Aggressive replay 2022-01-01 | 1,00,000 | No HITL",
    )
    db.add(cfg)
    db.flush()
    return cfg


def load_all_buy_signals(db: Session) -> dict[date, list[dict]]:
    """Load all BUY recommendation_results grouped by as_of_date."""
    rows = db.execute(text("""
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
          AND rrun.as_of_date >= '2022-01-01'
        ORDER BY rrun.as_of_date, rr.conviction_score DESC, rr.rank
    """)).fetchall()

    signals: dict[date, list[dict]] = defaultdict(list)
    seen: dict[date, set[str]] = defaultdict(set)  # dedup same stock/date cross-strategy
    for row in rows:
        key = (row[0], row[2])  # (date, stock_id)
        if key not in seen:
            seen[key].add(key)
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


def load_all_ranks(db: Session) -> dict[date, dict[str, int]]:
    """Best rank per stock per date across all strategies."""
    rows = db.execute(text("""
        SELECT rrun.as_of_date, rr.stock_id::text, MIN(rr.rank)
        FROM recommendation_results rr
        JOIN recommendation_runs rrun ON rr.recommendation_run_id = rrun.id
        WHERE rrun.as_of_date >= '2022-01-01' AND rr.rank IS NOT NULL
        GROUP BY rrun.as_of_date, rr.stock_id
    """)).fetchall()
    ranks: dict[date, dict[str, int]] = defaultdict(dict)
    for row in rows:
        ranks[row[0]][row[1]] = row[2]
    return ranks


def get_price(db: Session, stock_id: UUID, target_date: date, side: str = "BUY") -> tuple[float, date] | None:
    """Get fill price (close ± slippage) for a stock on or before target_date."""
    row = db.execute(text("""
        SELECT close, date FROM market_data
        WHERE stock_id = :sid AND date <= :d
        ORDER BY date DESC LIMIT 1
    """), {"sid": str(stock_id), "d": target_date}).fetchone()
    if not row:
        return None
    close = float(row[0])
    slip = SLIPPAGE_BPS / 10_000
    fill = close * (1 + slip) if side == "BUY" else close * (1 - slip)
    return fill, row[1]


def get_trading_days(db: Session, stock_id: UUID, start: date, end: date) -> int:
    row = db.execute(text("""
        SELECT COUNT(*) FROM market_data
        WHERE stock_id = :sid AND date > :s AND date <= :e
    """), {"sid": str(stock_id), "s": start, "e": end}).fetchone()
    return int(row[0]) if row else 0


_cash_balance: float = 0.0  # track running balance for cash ledger


def record_cash(db: Session, portfolio_id: UUID, entry_type: str,
                amount: float, as_of_date: date, description: str) -> None:
    global _cash_balance
    _cash_balance += amount
    db.execute(text("""
        INSERT INTO portfolio_cash_ledger
            (id, entry_type, amount, balance_after, as_of_date, description, created_at, updated_at)
        VALUES
            (:id, :etype, :amt, :bal, :aod, :desc, NOW(), NOW())
    """), {
        "id": str(uuid4()),
        "etype": entry_type, "amt": round(amount, 2),
        "bal": round(_cash_balance, 2),
        "aod": as_of_date, "desc": description,
    })


def run_replay():
    engine = create_engine(DATABASE_URL)

    with Session(engine) as db:
        # ── Setup ─────────────────────────────────────────────────────────────
        print("\n=== PI-PM PAPER TRADE REPLAY ===")
        print(f"    Capital: ₹{INITIAL_CAPITAL:,.0f}  |  Aggressive  |  No HITL")
        print(f"    Period : 2022-01-01 → 2026-06-05\n")

        clean_portfolio(db)
        cfg = setup_aggressive_config(db)

        # Seed initial cash
        record_cash(db, PORTFOLIO_ID, "INITIAL_CAPITAL", INITIAL_CAPITAL,
                    date(2022, 1, 1), "Initial capital ₹1,00,000")
        db.commit()

        # ── Load signals ──────────────────────────────────────────────────────
        print("  Loading signals...")
        buy_signals = load_all_buy_signals(db)
        all_ranks = load_all_ranks(db)

        # Get all trading days
        trading_days = [
            row[0] for row in db.execute(text("""
                SELECT DISTINCT date FROM market_data
                WHERE date >= '2022-01-01' AND date <= '2026-06-05'
                ORDER BY date
            """)).fetchall()
        ]
        print(f"  {len(trading_days)} trading days | {sum(len(v) for v in buy_signals.values())} BUY signals\n")

        # ── Simulation state ──────────────────────────────────────────────────
        cash = INITIAL_CAPITAL
        open_positions: list[dict] = []  # {stock_id, symbol, strategy, entry_date, entry_price, qty, cost, conviction_band}
        completed_trades: list[dict] = []
        nav_by_date: list[tuple[date, float]] = []

        total_fees = 0.0
        day_count = 0
        portfolio_svc = PortfolioService(db, portfolio_id=PORTFOLIO_ID)
        paper_svc = PaperTradeService(db, portfolio_service=portfolio_svc)
        exit_monitor = ExitMonitorService(db)

        for today in trading_days:
            day_count += 1
            if day_count % 250 == 0:
                print(f"  Processing {today} — {len(open_positions)} open, ₹{cash:,.0f} cash")

            # ── 1. Exits via ExitMonitorService (same path as daily pilot / UI) ──
            exited_stock_ids: set[str] = set()
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
                    exited_stock_ids.add(str(exit_rec.stock_id))

                    exit_price = float(trade.fill_price)
                    qty = float(trade.fill_quantity)
                    proceeds = qty * exit_price - FEE_PER_LEG
                    cash += proceeds
                    total_fees += FEE_PER_LEG

                    if mem_pos:
                        realized_pnl = proceeds - mem_pos["cost"]
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
                            "hold_days": exit_rec.days_held,
                            "exit_reason": ",".join(exit_rec.triggers or []),
                            "conviction_band": mem_pos["conviction_band"],
                        })
                except Exception as exc:
                    print(f"  ⚠ Exit monitor sell failed {exit_rec.stock_id} on {today}: {exc}")

            open_positions = [p for p in open_positions if p["stock_id"] not in exited_stock_ids]
            db.flush()

            # ── 2. Process entries ─────────────────────────────────────────
            if today in buy_signals:
                open_syms = {p["stock_id"] for p in open_positions}
                slots_free = MAX_SLOTS - len(open_positions)

                for sig in buy_signals[today]:
                    if slots_free <= 0:
                        break
                    if sig["stock_id"] in open_syms:
                        continue

                    stock_id = UUID(sig["stock_id"])
                    price_info = get_price(db, stock_id, today, side="BUY")
                    if not price_info:
                        continue

                    entry_price, _ = price_info

                    # Aggressive sizing: conviction multiplier applied
                    mult = CONVICTION_MULT.get(sig["conviction_band"], 0.75)
                    alloc = min(SLOT_BUDGET * mult, cash * 0.95)  # never use last 5% of cash
                    if alloc < entry_price:
                        continue

                    qty = alloc / entry_price  # fractional shares for paper trade
                    cost = qty * entry_price + FEE_PER_LEG
                    if cost > cash:
                        qty = (cash - FEE_PER_LEG) / entry_price
                        cost = qty * entry_price + FEE_PER_LEG
                    if qty <= 0:
                        continue

                    cash -= cost
                    total_fees += FEE_PER_LEG

                    # Open portfolio position
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
                        as_of=datetime(today.year, today.month, today.day, 15, 0, tzinfo=UTC),
                        is_current=True,
                        position_status="OPEN",
                    )
                    db.add(pp)

                    # Paper trade record
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
                        },
                    )
                    db.add(pt)

                    record_cash(db, PORTFOLIO_ID, "TRADE_BUY", -cost, today,
                                f"BUY {sig['symbol']} {qty:.2f}@{entry_price:.2f} [{sig['conviction_band']}]")

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

            # ── 3. Mark-to-market NAV ──────────────────────────────────────
            mtm = cash
            for pos in open_positions:
                row = db.execute(text("""
                    SELECT close FROM market_data
                    WHERE stock_id = :sid AND date <= :d
                    ORDER BY date DESC LIMIT 1
                """), {"sid": pos["stock_id"], "d": today}).fetchone()
                if row:
                    mtm += pos["qty"] * float(row[0])
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

        # Force-close all remaining positions at last price
        print(f"\n  Force-closing {len(open_positions)} remaining positions...")
        sim_end = trading_days[-1]
        for pos in open_positions:
            stock_id = UUID(pos["stock_id"])
            price_info = get_price(db, stock_id, sim_end, side="SELL")
            if not price_info:
                continue
            exit_price, _ = price_info
            proceeds = pos["qty"] * exit_price - FEE_PER_LEG
            realized_pnl = proceeds - pos["cost"]
            cash += proceeds
            total_fees += FEE_PER_LEG
            hold_days = get_trading_days(db, stock_id, pos["entry_date"], sim_end)

            pp = db.scalar(select(PortfolioPosition).where(
                PortfolioPosition.stock_id == stock_id,
                PortfolioPosition.is_current.is_(True),
                PortfolioPosition.portfolio_id == PORTFOLIO_ID,
            ))
            if pp:
                pp.exit_price = exit_price
                pp.exit_date = sim_end
                pp.realized_pnl = realized_pnl
                pp.unrealized_pnl = 0.0
                pp.is_current = False
                pp.position_status = "CLOSED"

            completed_trades.append({
                "symbol": pos["symbol"], "strategy": pos["strategy"],
                "entry_date": pos["entry_date"], "exit_date": sim_end,
                "entry_price": pos["entry_price"], "exit_price": exit_price,
                "qty": pos["qty"], "pnl": realized_pnl,
                "pnl_pct": realized_pnl / pos["cost"] * 100,
                "hold_days": hold_days, "exit_reason": "FORCE_CLOSE_END",
                "conviction_band": pos["conviction_band"],
            })

        db.commit()

        # ── Final Report ───────────────────────────────────────────────────
        final_value = cash
        total_pnl = final_value - INITIAL_CAPITAL
        total_return = total_pnl / INITIAL_CAPITAL * 100
        years = (sim_end - date(2022, 1, 3)).days / 365.25
        cagr = ((final_value / INITIAL_CAPITAL) ** (1 / years) - 1) * 100

        wins = [t for t in completed_trades if t["pnl"] > 0]
        losses = [t for t in completed_trades if t["pnl"] <= 0]
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

        # Per-strategy
        strats = {}
        for s in ["breakout_v1", "momentum_v1", "reversal_v1"]:
            st = [t for t in completed_trades if t["strategy"] == s]
            if not st:
                continue
            sw = [t for t in st if t["pnl"] > 0]
            sl = [t for t in st if t["pnl"] <= 0]
            strats[s] = {
                "n": len(st), "wr": len(sw)/len(st)*100,
                "pnl": sum(t["pnl"] for t in st),
                "aw": sum(t["pnl_pct"] for t in sw)/len(sw) if sw else 0,
                "al": sum(t["pnl_pct"] for t in sl)/len(sl) if sl else 0,
                "pf": sum(t["pnl"] for t in sw) / abs(sum(t["pnl"] for t in sl))
                      if sl and sum(t["pnl"] for t in sl) != 0 else 99,
            }

        yearly: dict[int, dict] = defaultdict(lambda: defaultdict(float))
        for t in completed_trades:
            yearly[t["exit_date"].year]["total"] += t["pnl"]
            yearly[t["exit_date"].year][t["strategy"]] += t["pnl"]

        by_pct = sorted(completed_trades, key=lambda t: t["pnl_pct"])

        W = 65
        print("\n" + "=" * W)
        print("  PI-PM PAPER TRADE REPLAY  |  Jan 2022 → Jun 2026")
        print(f"  Capital: ₹{INITIAL_CAPITAL:,.0f}  |  Aggressive  |  All trades in DB ✓")
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

        print(f"\n{'─'*W}")
        print("  PER-STRATEGY")
        print(f"{'─'*W}")
        print(f"  {'Strategy':<16} {'N':>4} {'Win%':>6} {'AvgW':>7} {'AvgL':>7} {'PF':>5} {'P&L':>10}")
        for s, v in strats.items():
            print(f"  {s:<16} {v['n']:>4} {v['wr']:>5.1f}% {v['aw']:>+6.1f}% {v['al']:>+6.1f}% {v['pf']:>5.2f} ₹{v['pnl']:>+8,.0f}")

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
            print(f"  {t['symbol']:<18} {t['strategy']:<12} {t['entry_date']}→{t['exit_date']}  {t['pnl_pct']:>+6.1f}%  ₹{t['pnl']:>+8,.0f}")

        print(f"\n{'─'*W}")
        print("  TOP 5 WORST TRADES")
        print(f"{'─'*W}")
        for t in by_pct[:5]:
            print(f"  {t['symbol']:<18} {t['strategy']:<12} {t['entry_date']}→{t['exit_date']}  {t['pnl_pct']:>+6.1f}%  ₹{t['pnl']:>+8,.0f}")

        print(f"\n{'─'*W}")
        print("  DATABASE STATE")
        print(f"{'─'*W}")
        pt_count = db.scalar(text("SELECT COUNT(*) FROM paper_trades"))
        pp_count = db.scalar(text("SELECT COUNT(*) FROM portfolio_positions WHERE portfolio_id = :pid"),
                             {"pid": str(PORTFOLIO_ID)})
        cl_count = db.scalar(text("SELECT COUNT(*) FROM portfolio_cash_ledger"))
        print(f"  paper_trades            : {pt_count:>5} rows")
        print(f"  portfolio_positions     : {pp_count:>5} rows (OPEN + CLOSED)")
        print(f"  portfolio_cash_ledger   : {cl_count:>5} rows")
        open_now = db.scalar(text(
            "SELECT COUNT(*) FROM portfolio_positions WHERE portfolio_id=:pid AND position_status='OPEN'"),
            {"pid": str(PORTFOLIO_ID)})
        print(f"  Open positions today    : {open_now:>5}")
        print()


if __name__ == "__main__":
    run_replay()
