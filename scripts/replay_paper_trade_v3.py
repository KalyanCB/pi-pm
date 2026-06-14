#!/usr/bin/env python3
"""
Pi-PM Paper Trade Replay v3 — ADR-035 best-outcome config, through the REAL DB.

Config (ADR-035 evidence base):
  Capital        : ₹1,00,00,000 (1 Cr)
  Slots          : 5 concurrent | ₹20,00,000 base per slot (capital/slots)
  Stop-loss      : REGIME-DYNAMIC via app.portfolio.regime_stops resolver
                   (BULL_LOW −6 / BULL_HIGH −8 / BEAR_LOW −2 / BEAR_HIGH −3,
                   fallback −4) — requires REGIME_DYNAMIC_STOPS_ENABLED=true
  Stop fill      : REALISTIC — slipped EOD close (gap-through), NOT capped
  Time stop      : DISABLED — requires TIME_STOP_ENABLED=false (T2 EXIT_TIME gated)
  Other exits    : rank-drop (MIN rank across strategies > 40) — validated set.
                   T2 monitor NOT used (EXIT_REGIME daily-fire + cross-strategy
                   rank lookup churned NAV to zero; ADR-035 findings)
  Fees           : 15 bps/side (≈ STT + stamp + charges, delivery)
  Slippage       : 30 bps/side
  Conviction mult: EXCEPTIONAL 1.15 / HIGH 1.00 / MEDIUM 0.75

Writes (and wipes first): paper_trades, portfolio_positions, portfolio_cash_ledger,
portfolio_nav_history (DAILY rows), portfolio_exit_recommendations,
portfolio_reconciliation_reports, execution_orders, portfolio_configs.

NEVER touches: stocks, market_data, recommendations, validations, committee tables.
Wipe uses row DELETEs (NOT TRUNCATE CASCADE — that would truncate
recommendation_results via its portfolio_position_id FK).
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

from app.core.config import get_settings
from app.core.constants import TradeSide, TradeStatus
from app.db.repositories.regime_analytics_repository import RegimeAnalyticsRepository
from app.models.paper_trade import PaperTrade
from app.models.portfolio_position import PortfolioConfig, PortfolioPosition
from app.portfolio.regime_stops import resolve_stop_pcts

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://pipm:pipm@localhost:5432/pipm")
PORTFOLIO_ID = UUID("00000000-0000-4000-8000-000000000010")

INITIAL_CAPITAL = 10_000_000.0          # ₹1 Cr (user-specified)
MAX_SLOTS = 5                            # ADR-035 concentration
MAX_TRADE_CAPITAL = INITIAL_CAPITAL / MAX_SLOTS   # ₹20L/slot
START_DATE = "2022-01-01"
END_DATE = os.getenv("REPLAY_END", date.today().isoformat())
CONVICTION_MULT = {"EXCEPTIONAL": 1.15, "HIGH": 1.00, "MEDIUM": 0.75}
SLIPPAGE_BPS = 30.0                      # honest Indian frictions
FEE_BPS = 15.0                           # per-side %, replaces flat fee

_cash_balance = 0.0


def slip(price: float, side: str) -> float:
    s = SLIPPAGE_BPS / 10_000
    return price * (1 + s) if side == "BUY" else price * (1 - s)


def fee_on(value: float) -> float:
    return abs(value) * FEE_BPS / 10_000


def clean_portfolio(db: Session) -> None:
    """Row-DELETE wipe of portfolio/trade state. Recommendations untouched:
    portfolio_positions deletes SET NULL recommendation_results.portfolio_position_id
    and CASCADE-delete exit recommendations (FK delete rules verified)."""
    print("  Wiping portfolio state (row deletes, FK-safe)...")
    for stmt in (
        "DELETE FROM portfolio_exit_recommendations",
        "DELETE FROM execution_orders",
        "DELETE FROM paper_trades",
        "DELETE FROM portfolio_reconciliation_reports",
        "DELETE FROM portfolio_nav_history",
        "DELETE FROM portfolio_cash_ledger",
        "DELETE FROM portfolio_positions",
        "DELETE FROM portfolio_configs",
    ):
        db.execute(text(stmt))
    db.commit()
    # Paranoia: recommendations must be intact.
    n = db.execute(text("SELECT count(*) FROM recommendation_results")).scalar()
    print(f"  ✓ wiped. recommendation_results intact: {n:,} rows")


def setup_config(db: Session) -> PortfolioConfig:
    cfg = PortfolioConfig(
        portfolio_id=PORTFOLIO_ID,
        is_active=True,
        total_equity=INITIAL_CAPITAL,
        deploy_pct=1.0,
        cash_floor_pct=0.0,
        reserve_pct=0.0,
        regime_slots={
            posture: {"max_positions": MAX_SLOTS, "max_buy_per_day": MAX_SLOTS}
            for posture in ("risk_on", "neutral", "defensive", "crisis")
        },
        single_name_cap_pct=0.25,
        sector_cap_pct=1.0,
        slippage_bps=SLIPPAGE_BPS,
        fee_per_leg=0.0,  # fees are % in-script (FEE_BPS)
        execution_mode="PAPER",
        notes=(
            f"ADR-035 best-outcome replay {START_DATE}->{END_DATE} | ₹1Cr | 5 slots | "
            f"regime stops 6/8/2/3 | no time stop | fee {FEE_BPS}bps + slip {SLIPPAGE_BPS}bps"
        ),
    )
    db.add(cfg)
    db.flush()
    return cfg


def load_all_buy_signals(db: Session) -> dict[date, list[dict]]:
    rows = db.execute(text("""
        SELECT rrun.as_of_date, rr.id::text, rr.stock_id::text, s.symbol, s.sector,
               r.strategy_name, rr.rank, rr.conviction_score, rr.conviction_band
        FROM recommendation_results rr
        JOIN recommendation_runs rrun ON rr.recommendation_run_id = rrun.id
        JOIN ranking_runs r ON rrun.ranking_run_id = r.id
        JOIN stocks s ON rr.stock_id = s.id
        WHERE rr.action = 'BUY' AND rrun.as_of_date >= :s AND rrun.as_of_date <= :e
        ORDER BY rrun.as_of_date, rr.conviction_score DESC, rr.rank, rr.id
    """), {"s": START_DATE, "e": END_DATE}).fetchall()
    signals: dict[date, list[dict]] = defaultdict(list)
    seen: set = set()
    for row in rows:
        key = (row[0], row[2])
        if key in seen:
            continue
        seen.add(key)
        signals[row[0]].append({
            "rec_result_id": row[1], "stock_id": row[2], "symbol": row[3],
            "sector": row[4], "strategy": row[5], "rank": row[6],
            "conviction": row[7], "conviction_band": row[8],
        })
    return signals


def load_all_ranks(db: Session) -> dict[date, dict[str, int]]:
    """Best (MIN) rank per stock per date across ALL strategies — the validated
    rank-drop basis. (T2's _get_current_rank reads the single latest ranking run
    of any strategy, which misfires cross-strategy — see ADR-035 findings.)"""
    rows = db.execute(text("""
        SELECT rrun.as_of_date, rr.stock_id::text, MIN(rr.rank)
        FROM recommendation_results rr
        JOIN recommendation_runs rrun ON rr.recommendation_run_id = rrun.id
        WHERE rrun.as_of_date >= :s AND rrun.as_of_date <= :e AND rr.rank IS NOT NULL
        GROUP BY rrun.as_of_date, rr.stock_id
    """), {"s": START_DATE, "e": END_DATE}).fetchall()
    ranks: dict[date, dict[str, int]] = defaultdict(dict)
    for r in rows:
        ranks[r[0]][r[1]] = int(r[2])
    return ranks


RANK_DROP_THRESH = 40


def get_eod_close(db: Session, stock_id: str, d: date) -> float | None:
    row = db.execute(text(
        "SELECT close FROM market_data WHERE stock_id = :sid AND date <= :d "
        "ORDER BY date DESC LIMIT 1"), {"sid": stock_id, "d": d}).fetchone()
    return float(row[0]) if row else None


def get_trading_days(db: Session, stock_id: str, start: date, end: date) -> int:
    row = db.execute(text(
        "SELECT COUNT(*) FROM market_data WHERE stock_id = :sid AND date > :s AND date <= :e"),
        {"sid": stock_id, "s": start, "e": end}).fetchone()
    return int(row[0]) if row else 0


def record_cash(db: Session, entry_type: str, amount: float, as_of: date, desc: str) -> None:
    global _cash_balance
    _cash_balance += amount
    db.execute(text("""
        INSERT INTO portfolio_cash_ledger
            (id, entry_type, amount, balance_after, as_of_date, description,
             created_at, updated_at)
        VALUES (:id, :etype, :amt, :bal, :aod, :desc, NOW(), NOW())
    """), {"id": str(uuid4()), "etype": entry_type, "amt": round(amount, 2),
           "bal": round(_cash_balance, 2), "aod": as_of, "desc": desc[:500]})


def close_position(
    db: Session, pos: dict, today: date, exit_price: float, reason: str,
    completed: list[dict], extra_meta: dict | None = None,
) -> float:
    """Close a position at exit_price (already slipped); % fee deducted. Returns proceeds."""
    qty = pos["qty"]
    gross = qty * exit_price
    fee = fee_on(gross)
    proceeds = gross - fee
    realized = proceeds - pos["cost"]
    hold_days = get_trading_days(db, pos["stock_id"], pos["entry_date"], today)

    pp = db.scalar(select(PortfolioPosition).where(
        PortfolioPosition.stock_id == UUID(pos["stock_id"]),
        PortfolioPosition.is_current.is_(True),
        PortfolioPosition.portfolio_id == PORTFOLIO_ID,
        PortfolioPosition.position_status == "OPEN"))
    if pp:
        pp.exit_price = exit_price
        pp.exit_date = today
        pp.realized_pnl = realized
        pp.unrealized_pnl = 0.0
        pp.market_value = gross
        pp.is_current = False
        pp.position_status = "CLOSED"
        pp.exit_reason = reason[:64]

    db.add(PaperTrade(
        stock_id=UUID(pos["stock_id"]), side=TradeSide.SELL.value,
        quantity=qty, fill_price=exit_price, fill_quantity=qty,
        status=TradeStatus.FILLED.value,
        idempotency_key=f"v3x-{pos['stock_id'][:8]}-{today}-{reason[:12]}",
        requested_at=datetime(today.year, today.month, today.day, 15, 30, tzinfo=UTC),
        filled_at=datetime(today.year, today.month, today.day, 15, 30, tzinfo=UTC),
        metadata_={"symbol": pos["symbol"], "strategy": pos["strategy"],
                   "exit_reason": reason, "fee": round(fee, 2),
                   "hold_days": hold_days, **(extra_meta or {})},
    ))
    record_cash(db, "TRADE_SELL", proceeds, today,
                f"{reason} {pos['symbol']} {qty:.2f}@{exit_price:.2f} fee={fee:.0f}")
    completed.append({
        "symbol": pos["symbol"], "strategy": pos["strategy"],
        "entry_date": pos["entry_date"], "exit_date": today,
        "entry_price": pos["entry_price"], "exit_price": exit_price,
        "qty": qty, "pnl": realized, "pnl_pct": realized / pos["cost"] * 100,
        "hold_days": hold_days, "exit_reason": reason,
        "conviction_band": pos["conviction_band"], "fee": fee,
    })
    return proceeds


def run_replay() -> None:
    global _cash_balance
    settings = get_settings()
    if not settings.regime_dynamic_stops_enabled or settings.time_stop_enabled:
        print("FATAL: ADR-035 flags not active. Need REGIME_DYNAMIC_STOPS_ENABLED=true "
              "and TIME_STOP_ENABLED=false in the environment/.env")
        sys.exit(1)

    engine = create_engine(DATABASE_URL)
    with Session(engine) as db:
        print("\n=== PI-PM PAPER TRADE REPLAY v3 — ADR-035 BEST OUTCOME ===")
        print(f"    Capital : ₹{INITIAL_CAPITAL:,.0f} | {MAX_SLOTS} slots | "
              f"₹{MAX_TRADE_CAPITAL:,.0f}/slot")
        print(f"    Costs   : fee {FEE_BPS}bps/side + slippage {SLIPPAGE_BPS}bps/side")
        print("    Stops   : regime-dynamic (resolver) | realistic fills | no time stop")
        print(f"    Period  : {START_DATE} → {END_DATE}\n")

        clean_portfolio(db)
        _cash_balance = 0.0
        setup_config(db)
        record_cash(db, "INITIAL_CAPITAL", INITIAL_CAPITAL, date.fromisoformat(START_DATE),
                    f"Initial capital ₹{INITIAL_CAPITAL:,.0f}")
        db.commit()

        print("  Loading signals...")
        buy_signals = load_all_buy_signals(db)
        all_ranks = load_all_ranks(db)
        trading_days = [r[0] for r in db.execute(text(
            "SELECT DISTINCT date FROM market_data WHERE date >= :s AND date <= :e ORDER BY date"),
            {"s": START_DATE, "e": END_DATE}).fetchall()]
        print(f"  {len(trading_days)} trading days | "
              f"{sum(len(v) for v in buy_signals.values())} BUY signals\n")

        regime_repo = RegimeAnalyticsRepository(db)

        cash = INITIAL_CAPITAL
        open_positions: list[dict] = []
        completed: list[dict] = []
        total_fees = 0.0
        stop_count = 0
        day_count = 0
        peak_nav = INITIAL_CAPITAL
        max_dd = 0.0

        for today in trading_days:
            day_count += 1

            # ── 1. Regime-dynamic stop exits (realistic slipped-close fills) ──
            advisory_pct, _ = resolve_stop_pcts(regime_repo, as_of=today, settings=settings)
            exited: set[str] = set()
            for pos in list(open_positions):
                close = get_eod_close(db, pos["stock_id"], today)
                if close is None:
                    continue
                unreal = (close - pos["entry_price"]) / pos["entry_price"] * 100
                if unreal <= advisory_pct:
                    px = slip(close, "SELL")
                    proceeds = close_position(
                        db, pos, today, px, "EXIT_STOP_LOSS", completed,
                        {"stop_pct": advisory_pct, "regime_resolved": True})
                    cash += proceeds
                    total_fees += fee_on(pos["qty"] * px)
                    exited.add(pos["stock_id"])
                    stop_count += 1
            open_positions = [p for p in open_positions if p["stock_id"] not in exited]
            db.flush()

            # ── 2. Rank-drop exits (validated basis: MIN rank across strategies) ──
            # The T2 monitor is intentionally NOT used here: its EXIT_REGIME
            # trigger fires daily in defensive postures and its rank lookup reads
            # a single strategy's latest run — both churned NAV to ~zero in
            # earlier replay runs (recorded as ADR-035 findings).
            today_ranks = all_ranks.get(today, {})
            swing_exited: set[str] = set()
            for pos in list(open_positions):
                r = today_ranks.get(pos["stock_id"])
                if r is None or r <= RANK_DROP_THRESH:
                    continue
                close = get_eod_close(db, pos["stock_id"], today)
                if close is None:
                    continue
                px = slip(close, "SELL")
                proceeds = close_position(db, pos, today, px, "EXIT_RANK_DROP",
                                          completed, {"rank": r})
                cash += proceeds
                total_fees += fee_on(pos["qty"] * px)
                swing_exited.add(pos["stock_id"])
            open_positions = [p for p in open_positions if p["stock_id"] not in swing_exited]
            db.flush()

            # ── 3. Entries (conviction-ordered, dedup, slots) ─────────────────
            if today in buy_signals:
                open_ids = {p["stock_id"] for p in open_positions}
                slots_free = MAX_SLOTS - len(open_positions)
                for sig in buy_signals[today]:
                    if slots_free <= 0:
                        break
                    if sig["stock_id"] in open_ids:
                        continue
                    close = get_eod_close(db, sig["stock_id"], today)
                    if close is None:
                        continue
                    entry_px = slip(close, "BUY")
                    mult = CONVICTION_MULT.get(sig["conviction_band"], 0.75)
                    alloc = min(MAX_TRADE_CAPITAL * mult, cash * 0.98)
                    if alloc < entry_px:
                        continue
                    qty = alloc / entry_px
                    gross = qty * entry_px
                    fee = fee_on(gross)
                    cost = gross + fee
                    if cost > cash:
                        qty = (cash * 0.98) / entry_px
                        gross = qty * entry_px
                        fee = fee_on(gross)
                        cost = gross + fee
                    if qty <= 0:
                        continue
                    cash -= cost
                    total_fees += fee
                    stop_px = round(entry_px * (1 + advisory_pct / 100), 4)
                    db.add(PortfolioPosition(
                        id=uuid4(), portfolio_id=PORTFOLIO_ID,
                        stock_id=UUID(sig["stock_id"]),
                        recommendation_result_id=UUID(sig["rec_result_id"]),
                        quantity=qty, avg_cost=entry_px, entry_price=entry_px,
                        entry_date=today, market_value=gross, unrealized_pnl=0.0,
                        conviction_band=sig["conviction_band"],
                        strategy_name=sig["strategy"], sector=sig["sector"],
                        stop_loss_price=stop_px,
                        as_of=datetime(today.year, today.month, today.day, 15, tzinfo=UTC),
                        is_current=True, position_status="OPEN",
                    ))
                    db.add(PaperTrade(
                        stock_id=UUID(sig["stock_id"]), side=TradeSide.BUY.value,
                        quantity=qty, fill_price=entry_px, fill_quantity=qty,
                        status=TradeStatus.FILLED.value,
                        idempotency_key=f"v3e-{sig['stock_id'][:8]}-{today}",
                        requested_at=datetime(today.year, today.month, today.day, 15, tzinfo=UTC),
                        filled_at=datetime(today.year, today.month, today.day, 15, tzinfo=UTC),
                        metadata_={"symbol": sig["symbol"], "strategy": sig["strategy"],
                                   "conviction_band": sig["conviction_band"],
                                   "fee": round(fee, 2), "stop_loss_price": stop_px},
                    ))
                    record_cash(db, "TRADE_BUY", -cost, today,
                                f"BUY {sig['symbol']} {qty:.2f}@{entry_px:.2f} "
                                f"[{sig['conviction_band']}] fee={fee:.0f}")
                    open_positions.append({
                        "stock_id": sig["stock_id"], "symbol": sig["symbol"],
                        "strategy": sig["strategy"], "entry_date": today,
                        "entry_price": entry_px, "qty": qty, "cost": cost,
                        "conviction_band": sig["conviction_band"],
                    })
                    open_ids.add(sig["stock_id"])
                    slots_free -= 1
                db.flush()

            # ── 4. Mark-to-market: positions + DAILY NAV row ──────────────────
            mtm = cash
            invested_cost = 0.0
            for pos in open_positions:
                close = get_eod_close(db, pos["stock_id"], today)
                mv = pos["qty"] * close if close else pos["cost"]
                mtm += mv
                invested_cost += pos["cost"]
                pp = db.scalar(select(PortfolioPosition).where(
                    PortfolioPosition.stock_id == UUID(pos["stock_id"]),
                    PortfolioPosition.is_current.is_(True),
                    PortfolioPosition.position_status == "OPEN"))
                if pp and close:
                    pp.market_value = mv
                    pp.unrealized_pnl = mv - pos["qty"] * pos["entry_price"]
                    pp.stop_loss_price = round(pos["entry_price"] * (1 + advisory_pct / 100), 4)
            for pos in open_positions:  # weight vs today's NAV (ADR weight basis)
                pp = db.scalar(select(PortfolioPosition).where(
                    PortfolioPosition.stock_id == UUID(pos["stock_id"]),
                    PortfolioPosition.is_current.is_(True),
                    PortfolioPosition.position_status == "OPEN"))
                if pp and pp.market_value and mtm > 0:
                    pp.weight_pct = round(float(pp.market_value) / mtm * 100, 4)

            peak_nav = max(peak_nav, mtm)
            max_dd = max(max_dd, (peak_nav - mtm) / peak_nav * 100)
            rpnl = sum(t["pnl"] for t in completed)
            db.execute(text("""
                INSERT INTO portfolio_nav_history
                    (id, as_of_date, total_equity, cash_balance, market_value,
                     unrealized_pnl, realized_pnl_cumulative, open_positions,
                     cash_pct, regime_label, created_at, updated_at)
                VALUES (:id, :aod, :nav, :cash, :mv, :upnl, :rpnl, :npos, :cpct,
                        :reg, NOW(), NOW())
                ON CONFLICT DO NOTHING
            """), {
                "id": str(uuid4()), "aod": today, "nav": round(mtm, 2),
                "cash": round(cash, 2), "mv": round(mtm - cash, 2),
                "upnl": round((mtm - cash) - invested_cost, 2),
                "rpnl": round(rpnl, 2), "npos": len(open_positions),
                "cpct": round(cash / mtm if mtm > 0 else 0, 4),
                "reg": None,
            })
            if day_count % 50 == 0:
                db.commit()
            if day_count % 250 == 0:
                print(f"  [{today}] {len(open_positions)} open | NAV ₹{mtm:,.0f} | "
                      f"cash ₹{cash:,.0f} | stops={stop_count} | DD {max_dd:.1f}%")

        db.commit()

        # ── Final report ───────────────────────────────────────────────────────
        final_nav = mtm
        wins = [t for t in completed if t["pnl"] > 0]
        losses = [t for t in completed if t["pnl"] <= 0]
        total_pnl = final_nav - INITIAL_CAPITAL
        years = (trading_days[-1] - date.fromisoformat(START_DATE)).days / 365.25
        cagr = ((final_nav / INITIAL_CAPITAL) ** (1 / years) - 1) * 100 if years > 0 else 0
        gl = abs(sum(t["pnl"] for t in losses))
        pf = sum(t["pnl"] for t in wins) / gl if gl > 0 else 999.0

        W = 70
        print("\n" + "=" * W)
        print("  REPLAY v3 COMPLETE — ADR-035 BEST OUTCOME (system tables updated)")
        print("=" * W)
        print(f"  Final NAV       : ₹{final_nav:>14,.0f}")
        print(f"  Total P&L       : ₹{total_pnl:>+14,.0f}  ({total_pnl/INITIAL_CAPITAL*100:+.2f}%)")
        print(f"  CAGR            : {cagr:>+13.2f}%  ({years:.1f} yrs)")
        print(f"  Max Drawdown    : {max_dd:>13.2f}%")
        print(f"  Closed trades   : {len(completed)} ({len(wins)}W/{len(losses)}L, "
              f"win {len(wins)/len(completed)*100 if completed else 0:.1f}%)  PF {pf:.2f}x")
        print(f"  Stop-loss exits : {stop_count}")
        print(f"  Total fees paid : ₹{total_fees:>14,.0f}")
        print(f"  Open positions  : {len(open_positions)} (left OPEN in DB)")
        reasons: dict[str, int] = defaultdict(int)
        for t in completed:
            reasons[t["exit_reason"].split(',')[0]] += 1
        print("  Exit reasons    :", dict(sorted(reasons.items(), key=lambda x: -x[1])))
        print()


if __name__ == "__main__":
    run_replay()
