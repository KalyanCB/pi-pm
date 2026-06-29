"""Paper-trading pilot orchestration for daily batch.

Orchestrates portfolio ops only — does not modify ranking, validation,
recommendation generation, conviction, or committee logic.
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import RecommendationAction
from app.models.portfolio_analytics import ExitRecommendation, PortfolioNavHistory
from app.models.portfolio_position import PortfolioPosition
from app.models.recommendation import RecommendationResult, RecommendationRun
from app.recommendation.rank_bucket_expectancy import RankBucketExpectancyProvider
from app.recommendation.trade_prioritizer import TradeCandidate, prioritize
from app.portfolio.exit_monitor.service import ExitMonitorService
from app.portfolio.reconciliation.service import ReconciliationService
from app.execution.services.execution_service import ExecutionService
from app.models.recommendation import RecommendationApproval
from app.services.paper_trade_service import PaperTradeService
from app.services.portfolio_nav_service import PortfolioNavService
from app.services.portfolio_service import PortfolioService
from app.services.recommendation_service import RecommendationService

DEFAULT_PORTFOLIO_ID = UUID("00000000-0000-4000-8000-000000000010")


class PaperPilotOps:
    def __init__(
        self,
        db: Session,
        *,
        portfolio_service: PortfolioService | None = None,
        nav_service: PortfolioNavService | None = None,
        reconciliation_service: ReconciliationService | None = None,
        exit_monitor: ExitMonitorService | None = None,
        paper_trade_service: PaperTradeService | None = None,
        recommendation_service: RecommendationService | None = None,
        execution_service: ExecutionService | None = None,
    ) -> None:
        self.db = db
        self.portfolio_service = portfolio_service or PortfolioService(
            db, portfolio_id=DEFAULT_PORTFOLIO_ID
        )
        self.nav_service = nav_service or PortfolioNavService(db)
        self.reconciliation_service = reconciliation_service or ReconciliationService(db)
        self.exit_monitor = exit_monitor or ExitMonitorService(db)
        self.paper_trade_service = paper_trade_service or PaperTradeService(
            db, portfolio_service=self.portfolio_service
        )
        self.recommendation_service = recommendation_service or RecommendationService(db)
        self.execution_service = execution_service or ExecutionService(
            db, portfolio_id=DEFAULT_PORTFOLIO_ID
        )
        self._pilot_actor_id = UUID("00000000-0000-4000-8000-000000000001")

    def run(
        self,
        as_of_date: date,
        *,
        recompute: bool = True,
        exit_monitor: bool = True,
        paper_trading: bool = True,
        nav_snapshot: bool = True,
        reconcile: bool = True,
        pilot_auto_approve: bool = False,
        pilot_auto_execute: bool = False,
    ) -> dict:
        results: dict = {}

        if recompute:
            results["recompute"] = self.portfolio_service.recompute(as_of_date)

        # When auto-executing, the exit monitor runs INSIDE _execute_pilot_trades in two
        # phases (signal pre-buy, price post-buy). Only run the single all-trigger pass
        # here for the non-execute (UI / PENDING-review) path to avoid double-evaluation.
        if exit_monitor and not (paper_trading and pilot_auto_execute):
            exit_recs = self.exit_monitor.run(as_of_date)
            results["exit_monitor"] = {
                "candidates": len(exit_recs),
                "ids": [str(r.id) for r in exit_recs],
            }

        if paper_trading and pilot_auto_execute:
            results["paper_trading"] = self._execute_pilot_trades(
                as_of_date,
                pilot_auto_approve=pilot_auto_approve,
            )

        if nav_snapshot:
            nav = self.nav_service.snapshot(as_of_date)
            results["nav_snapshot"] = {
                "nav_id": str(nav.id),
                "total_equity": float(nav.total_equity),
                "cash_pct": float(nav.cash_pct),
                "open_positions": nav.open_positions,
            }

        if reconcile:
            try:
                report = self.reconciliation_service.run(as_of_date)
                results["reconcile"] = {
                    "report_id": str(report.id),
                    "status": report.status,
                    "discrepancy_pct": float(report.discrepancy_pct),
                }
            except Exception as exc:
                self.db.rollback()
                results["reconcile"] = {"status": "ERROR", "error": str(exc)}

        return results

    # ── ADR-037 v18 P-22: defensive gold rotation (flag-gated) ───────────────

    def _gold_rotation(self, as_of_date: date, regime_label: str) -> dict | None:
        """In BEAR regimes deploy the defensive sleeve to GOLDBEES instead of cash;
        sell it when the regime is no longer bear. Gold is a non-universe instrument
        (strategy_name='gold_rotation') so it never interacts with the equity ranking.
        """
        from app.core.config import get_settings
        from sqlalchemy import text as _text
        s = get_settings()
        if not s.gold_rotation_enabled:
            return None
        gold = self.db.execute(_text("SELECT id FROM stocks WHERE symbol=:sym"),
                               {"sym": s.gold_symbol}).fetchone()
        if not gold:
            return {"status": "no_gold_data"}
        gold_id = gold[0]
        px = self.db.execute(_text(
            "SELECT close FROM market_data WHERE stock_id=:s AND date<=:d ORDER BY date DESC LIMIT 1"
        ), {"s": gold_id, "d": as_of_date}).scalar()
        if not px:
            return {"status": "no_gold_price"}
        px = float(px)

        held = self.db.scalar(select(PortfolioPosition).where(
            PortfolioPosition.stock_id == gold_id,
            PortfolioPosition.is_current.is_(True),
            PortfolioPosition.position_status == "OPEN",
        ))
        is_bear = regime_label.upper().startswith("BEAR")
        cash = self.nav_service.cash_balance()

        # fast_deploy: demand-driven dynamic-band sleeve (rides winners, yields to
        # buys, 25-50% band, buy-cooldown to curb gold churn).
        if s.fast_deploy_enabled:
            return self._gold_rotation_dynamic(as_of_date, gold_id, px, held, cash, regime_label, s)

        def _sell(reason: str) -> dict:
            fill = round(px * 0.9995, 4)
            qty = float(held.quantity)
            self.portfolio_service.close_position(
                gold_id, exit_price=fill, exit_date=as_of_date, exit_reason=reason)
            self.nav_service.record_cash_entry(
                entry_type="TRADE_SELL", amount=qty * fill, as_of_date=as_of_date,
                reference_type="gold_rotation", description=f"{reason} {qty} @ {fill}")
            return {"action": reason, "qty": qty, "price": fill}

        # NON-BEAR: ride if winning, cut only if losing (underwater vs avg cost).
        if not is_bear:
            if held is None:
                return {"action": "none", "is_bear": False}
            if px < float(held.entry_price):          # underwater → cut the loser
                return _sell("GOLD_LOSS_EXIT")
            return {"action": "GOLD_HOLD_RIDE",       # in profit → let it ride into bull
                    "unreal_pct": round((px / float(held.entry_price) - 1) * 100, 1)}

        # BEAR: slots take ABSOLUTE priority. Reserve cash for any open stock slots
        # (slots_available × single-name cap × equity); gold may only use the surplus.
        cfg = self.portfolio_service.get_config()
        total_equity = float(cfg.total_equity) if cfg else 0.0
        cap = float(cfg.single_name_cap_pct) if cfg and cfg.single_name_cap_pct else 0.18
        limits = self.portfolio_service.get_limits(as_of_date)
        reserve = limits.slots_available * cap * total_equity

        # Open stock slots need cash that's parked in gold → yield: sell gold to fund them.
        if held is not None and cash < reserve:
            return _sell("GOLD_YIELD_SLOTS")

        # Gold budget. With the mega diversifier on, size gold to the RESIDUAL slots
        # (total − equity cap) × single-name cap × equity — 1 in defensive, 3 in crisis.
        # Else legacy surplus share.
        if held is None:
            if s.mega_diversifier_enabled:
                _cap = float(cfg.single_name_cap_pct) if cfg and cfg.single_name_cap_pct else 0.18
                _posture = self.portfolio_service._resolve_regime_posture(as_of_date)
                _eqcap = (s.mega_diversifier_crisis_max_buy if _posture == "crisis"
                          else s.mega_diversifier_bear_max_buy)
                _gslots = max(0, s.mega_diversifier_total_slots - _eqcap)  # residual slots
                budget = min(_gslots * _cap * total_equity, cash)
            else:
                budget = max(0.0, cash - reserve) * s.gold_alloc_pct
            qty = int(budget / px)
            if qty <= 0:
                return {"action": "hold", "cash": round(cash), "reserve": round(reserve)}
            fill = round(px * 1.0005, 4)  # 5bps slippage
            self.portfolio_service.open_position(
                stock_id=gold_id, quantity=qty, fill_price=fill,
                entry_date=as_of_date, strategy_name="gold_rotation", sector="ETF",
            )
            self.nav_service.record_cash_entry(
                entry_type="TRADE_BUY", amount=-(qty * fill), as_of_date=as_of_date,
                reference_type="gold_rotation", description=f"GOLD BUY {qty} @ {fill}")
            return {"action": "GOLD_BUY", "qty": qty, "price": fill}

        return {"action": "GOLD_HOLD_BEAR", "cash": round(cash), "reserve": round(reserve)}

    def _gold_rotation_dynamic(
        self, as_of_date, gold_id, px, held, cash, regime_label, s
    ) -> dict:
        """fast_deploy gold sleeve: demand-driven dynamic band (% of total portfolio).
        Stock slots have absolute priority. Gold rides winners (no auto-sell on a
        regime flip), yields cash to stock BUYS (bull: fully; bear: down to the 25%
        floor), soaks idle cash up to the 50% ceiling, cuts losers, and a buy-cooldown
        stops the buy-yield-rebuy thrash.
        """
        from sqlalchemy import text as _text

        cfg = self.portfolio_service.get_config()
        total_equity = float(cfg.total_equity) if cfg else 0.0
        is_bear = regime_label.upper().startswith("BEAR")
        gold_val = float(held.quantity) * px if held else 0.0
        # Cash the stock slots still want = regime DEPLOY CEILING (fast_deploy-aware)
        # minus what stocks already hold. NOT slots_available × single-name-cap — that
        # over-reserved (e.g. BEAR_HIGH_VOL: 4 slots × 18% = 72% phantom-reserved for
        # stocks that won't be bought at a 0% ceiling, starving gold of idle cash).
        summary = self.portfolio_service.get_summary(as_of_date)
        stock_value = max(0.0, float(summary.market_value) - gold_val)
        slot_reserve = max(0.0, float(summary.deployable_capital) - stock_value)
        floor = s.gold_min_pct * total_equity
        ceil = s.gold_max_pct * total_equity
        # Mega diversifier: reserve ONLY equity's own slot sleeve (max_buy × cap) so gold
        # gets the residual; gold fills up to (total − equity) slots and yields fully (no
        # floor). This makes the bear structure exact even under fast_deploy.
        if s.mega_diversifier_enabled and is_bear:
            _cap = float(cfg.single_name_cap_pct) if cfg and cfg.single_name_cap_pct else 0.18
            _posture = self.portfolio_service._resolve_regime_posture(as_of_date)
            _eqcap = (s.mega_diversifier_crisis_max_buy if _posture == "crisis"
                      else s.mega_diversifier_bear_max_buy)
            slot_reserve = max(0.0, _eqcap * _cap * total_equity - stock_value)
            floor = 0.0  # gold always yields to buys
            ceil = max(0.0, (s.mega_diversifier_total_slots - _eqcap) * _cap * total_equity)

        def _sell(qty: float, reason: str) -> dict:
            qty = min(qty, float(held.quantity))
            fill = round(px * 0.9995, 4)
            if qty >= float(held.quantity) - 1e-9:
                self.portfolio_service.close_position(
                    gold_id, exit_price=fill, exit_date=as_of_date, exit_reason=reason)
            else:
                held.quantity = float(held.quantity) - qty   # partial yield
                self.db.flush()
            self.nav_service.record_cash_entry(
                entry_type="TRADE_SELL", amount=qty * fill, as_of_date=as_of_date,
                reference_type="gold_rotation", description=f"{reason} {qty:.0f} @ {fill}")
            return {"action": reason, "qty": qty, "price": fill}

        # cut losers (bull only — in bear the band holds through MTM dips)
        if held is not None and not is_bear and px < float(held.entry_price):
            return _sell(float(held.quantity), "GOLD_LOSS_EXIT")

        # YIELD to stock buys: slots need cash → release gold. Bull: all; bear: to floor
        # UNLESS gold_yield_to_buys_enabled, which makes gold yield fully (no bear floor).
        if held is not None and cash < slot_reserve:
            need = slot_reserve - cash
            yield_fully = (not is_bear) or s.gold_yield_to_buys_enabled or s.mega_diversifier_enabled
            sellable = gold_val if yield_fully else max(0.0, gold_val - floor)
            qty = int(min(need, sellable) / px)
            if qty > 0:
                return _sell(qty, "GOLD_YIELD_SLOTS")

        if not is_bear:
            if held is None:
                return {"action": "none", "is_bear": False}
            return {"action": "GOLD_HOLD_RIDE",
                    "unreal_pct": round((px / float(held.entry_price) - 1) * 100, 1)}

        # BEAR: size gold to the band from idle cash, once, cooldown-gated.
        if held is not None:
            return {"action": "GOLD_HOLD_BEAR", "gold_val": round(gold_val)}
        idle = max(0.0, cash - slot_reserve)
        if idle < floor:                       # not enough idle to meet the 25% floor
            return {"action": "hold", "idle": round(idle)}
        last = self.db.execute(_text(
            "SELECT max(as_of_date) FROM portfolio_cash_ledger WHERE reference_type='gold_rotation'"
        )).scalar()
        if last is not None and (as_of_date - last).days < s.gold_buy_cooldown_days:
            return {"action": "GOLD_COOLDOWN", "last": str(last)}
        budget = min(ceil, idle)               # soak idle cash up to the 50% ceiling
        qty = int(budget / px)
        if qty <= 0:
            return {"action": "hold"}
        fill = round(px * 1.0005, 4)
        self.portfolio_service.open_position(
            stock_id=gold_id, quantity=qty, fill_price=fill,
            entry_date=as_of_date, strategy_name="gold_rotation", sector="ETF")
        self.nav_service.record_cash_entry(
            entry_type="TRADE_BUY", amount=-(qty * fill), as_of_date=as_of_date,
            reference_type="gold_rotation", description=f"GOLD BUY {qty} @ {fill}")
        return {"action": "GOLD_BUY", "qty": qty, "price": fill, "budget": round(budget)}

    def _raise_cash_from_gold(self, need: float, as_of_date: date, regime_label: str) -> float:
        """Sell GOLD to fund a stock buy when cash is short. Returns cash raised.

        Funding waterfall (per-trade): bull → gold is fully sellable; bear → only the
        amount ABOVE the 25% gold floor (gold_min_pct*equity) may be sold, keeping the
        bear hedge intact. No-op if gold is disabled / not held / already at the floor.
        """
        from app.core.config import get_settings
        from sqlalchemy import text as _text
        s = get_settings()
        if need <= 0 or not s.gold_rotation_enabled:
            return 0.0
        gold = self.db.execute(_text("SELECT id FROM stocks WHERE symbol=:sym"),
                               {"sym": s.gold_symbol}).fetchone()
        if not gold:
            return 0.0
        gold_id = gold[0]
        held = self.db.scalar(select(PortfolioPosition).where(
            PortfolioPosition.stock_id == gold_id,
            PortfolioPosition.is_current.is_(True),
            PortfolioPosition.position_status == "OPEN"))
        if held is None:
            return 0.0
        px = self.db.execute(_text(
            "SELECT close FROM market_data WHERE stock_id=:s AND date<=:d ORDER BY date DESC LIMIT 1"),
            {"s": gold_id, "d": as_of_date}).scalar()
        if not px:
            return 0.0
        fill = round(float(px) * 0.9995, 4)        # 5bps sell slippage (matches sleeve)
        is_bear = regime_label.upper().startswith("BEAR")
        cfg = self.portfolio_service.get_config()
        equity = float(cfg.total_equity) if cfg else 0.0
        # gold_yield_to_buys: sell gold fully to fund a buy — no bear floor retained.
        floor = (s.gold_min_pct * equity) if (
            is_bear and not s.gold_yield_to_buys_enabled and not s.mega_diversifier_enabled
        ) else 0.0
        gold_val = float(held.quantity) * fill
        sellable_val = max(0.0, gold_val - floor)
        if sellable_val <= 0:
            return 0.0
        # Sell just enough to cover `need` (+1 unit for rounding), capped at the floor.
        qty = min(int(need / fill) + 1, int(sellable_val / fill))
        if qty <= 0:
            return 0.0
        proceeds = qty * fill
        if qty >= float(held.quantity) - 1e-9:
            self.portfolio_service.close_position(
                gold_id, exit_price=fill, exit_date=as_of_date, exit_reason="GOLD_YIELD_BUY")
        else:
            held.quantity = float(held.quantity) - qty
            self.db.flush()
        self.nav_service.record_cash_entry(
            entry_type="TRADE_SELL", amount=proceeds, as_of_date=as_of_date,
            reference_type="gold_rotation", description=f"GOLD_YIELD_BUY {qty} @ {fill}")
        return proceeds

    # ── Buy trace (price-tag limit-fill audit) ────────────────────────────────
    def _ensure_buy_trace_table(self) -> None:
        from sqlalchemy import text as _t
        self.db.execute(_t("""
            CREATE TABLE IF NOT EXISTS buy_trace (
              id bigserial PRIMARY KEY,
              as_of_date date, fill_date date, stock_id uuid, symbol text,
              recommendation_id uuid,
              strategy text, conviction text,
              reference_close numeric, entry_low numeric, entry_high numeric,
              d1_open numeric, d1_high numeric, d1_low numeric, d1_close numeric,
              decision text, reason text, fill_price numeric,
              created_at timestamptz DEFAULT now())"""))
        # backfill the column on pre-existing tables (retry queue keys off it)
        self.db.execute(_t(
            "ALTER TABLE buy_trace ADD COLUMN IF NOT EXISTS recommendation_id uuid"))

    def _log_buy_trace(self, as_of_date, rec, el, eh, d1, decision, reason, fill_price) -> None:
        """One row per BUY candidate evaluated — executed or skipped, with the band,
        D+1 OHLC, decision and reason. Best-effort; never breaks the trade loop."""
        from sqlalchemy import text as _t
        try:
            self.db.execute(_t("""
                INSERT INTO buy_trace (as_of_date, fill_date, stock_id, symbol, recommendation_id,
                  strategy, conviction, reference_close, entry_low, entry_high,
                  d1_open, d1_high, d1_low, d1_close, decision, reason, fill_price)
                VALUES (:aod, :fd, :sid, (SELECT symbol FROM stocks WHERE id=:sid), :rid, :strat,
                  :conv, :rc, :el, :eh, :o, :h, :l, :c, :dec, :rsn, :fp)"""), {
                "aod": as_of_date, "fd": (d1.date if d1 else None), "sid": rec.stock_id,
                "rid": getattr(rec, "id", None),
                "strat": getattr(rec, "strategy_name", None), "conv": rec.conviction_band,
                "rc": float(rec.reference_close) if rec.reference_close is not None else None,
                "el": el, "eh": eh,
                "o": float(d1.open) if d1 and d1.open is not None else None,
                "h": float(d1.high) if d1 and d1.high is not None else None,
                "l": float(d1.low) if d1 and d1.low is not None else None,
                "c": float(d1.close) if d1 and d1.close is not None else None,
                "dec": decision, "rsn": reason, "fp": fill_price})
        except Exception:
            pass

    def _entry_band_decision(self, d1, el, eh):
        """Momentum-confirmed band entry — mirrors the LIVE monitor: fire ONLY if D+1's
        price actually trades INTO the band [entry_low, entry_high]; fill at the band
        level (high by default, mid optional). Gap-up (price stays above) AND gap-down
        (price stays below) both → NOT fired. No day-low / open capture.
        Returns (decision, fill_price, reason)."""
        if d1 is None or d1.high is None or d1.low is None:
            return ("SKIPPED", None, "NO_D1_DATA")
        lo, hi = float(d1.low), float(d1.high)
        from app.core.config import get_settings
        level = (get_settings().entry_band_fill_level or "mid").lower()
        target = eh if level == "high" else (el + eh) / 2.0   # default: MID of band
        if lo <= target <= hi:            # price traded THROUGH the fill level → take it
            return ("FILLED", round(target, 4), "BAND_" + level.upper())
        # fill level not touched → not fired today; classify for the retry queue
        if lo > eh:
            return ("SKIPPED", None, "PRICE_TAG_MISSED_GAPUP")
        if hi < el:
            return ("SKIPPED", None, "PRICE_TAG_MISSED_GAPDOWN")
        return ("SKIPPED", None, "BAND_MID_NOT_TOUCHED")

    _RETRY_REASONS = ("PRICE_TAG_MISSED_GAPUP", "PRICE_TAG_MISSED_GAPDOWN",
                      "BAND_MID_NOT_TOUCHED")

    def _collect_missed_recs(self, as_of_date, active_strategy, open_stock_ids,
                             fresh_stock_ids, lookback_days):
        """Missed-fill retry queue: BUY recs from the last ``lookback_days`` trading days
        (of the CURRENTLY-active strategy only → 'falls on current regime') that missed
        their band and were never since filled. Re-checked against today's bar by the
        same band gate in the buy loop; returned ranked by ORIGINAL rank then
        composite_score so they backfill open slots best-first."""
        if not lookback_days or lookback_days <= 0:
            return []
        from sqlalchemy import text as _t
        rows = self.db.execute(_t("""
            WITH days AS (
                SELECT DISTINCT as_of_date FROM buy_trace
                WHERE as_of_date < :d AND strategy = :strat
                ORDER BY as_of_date DESC LIMIT :n
            ),
            missed AS (
                SELECT DISTINCT ON (bt.stock_id)
                       bt.recommendation_id, bt.stock_id, bt.as_of_date
                FROM buy_trace bt
                WHERE bt.as_of_date IN (SELECT as_of_date FROM days)
                  AND bt.strategy = :strat
                  AND bt.decision = 'SKIPPED'
                  AND bt.reason = ANY(:reasons)
                  AND bt.recommendation_id IS NOT NULL
                ORDER BY bt.stock_id, bt.as_of_date DESC
            )
            SELECT m.recommendation_id FROM missed m
            WHERE NOT EXISTS (
                SELECT 1 FROM buy_trace f
                WHERE f.stock_id = m.stock_id AND f.decision = 'FILLED'
                  AND f.as_of_date >= m.as_of_date)
        """), {"d": as_of_date, "strat": active_strategy,
               "n": int(lookback_days), "reasons": list(self._RETRY_REASONS)}).fetchall()
        ids = [r[0] for r in rows if r[0] is not None]
        if not ids:
            return []
        recs = self.db.scalars(select(RecommendationResult).where(
            RecommendationResult.id.in_(ids),
            RecommendationResult.action == RecommendationAction.BUY.value,
        )).all()
        recs = [r for r in recs
                if r.stock_id not in open_stock_ids
                and r.stock_id not in fresh_stock_ids
                and not r.portfolio_position_id]
        recs.sort(key=lambda r: (
            r.rank if r.rank is not None else 1_000_000,
            -(float(r.composite_score) if r.composite_score is not None else 0.0)))
        for r in recs:
            setattr(r, "_is_retry", True)
        return recs

    # ── P-21 Trade Decision Layer ────────────────────────────────────────────

    def _get_expectancy_provider(self, as_of_date: date) -> RankBucketExpectancyProvider:
        """Cached rank-bucketed expectancy. Rebuilt quarterly (expectancy is slow-
        moving and the build is a heavy historical aggregation — avoid per-day cost)."""
        built_for = getattr(self, "_expectancy_built_for", None)
        if built_for is None or (as_of_date - built_for).days >= 63:
            self._expectancy_provider = RankBucketExpectancyProvider.build(
                self.db, as_of_date=as_of_date
            )
            self._expectancy_built_for = as_of_date
        return self._expectancy_provider

    def _market_context(self, as_of_date: date) -> tuple[float | None, float | None]:
        """(P-14 breadth, P-13 synthetic-universe 20-day mean return) in one query
        over the traded universe. Both are absolute market signals the NIFTY-50
        regime cannot see. Returns (None, None) at cold start (<50 stocks)."""
        from sqlalchemy import text as _text
        row = self.db.execute(_text("""
            WITH recent AS (
                SELECT stock_id, close,
                       ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY date DESC) AS rn
                FROM market_data WHERE source = 'kite' AND date <= :d
            ),
            per_stock AS (
                SELECT stock_id,
                       MAX(close) FILTER (WHERE rn = 1)  AS last_close,
                       AVG(close) FILTER (WHERE rn <= 50) AS sma50,
                       MAX(close) FILTER (WHERE rn = 20) AS close_20d,
                       COUNT(*) AS bars
                FROM recent WHERE rn <= 50 GROUP BY stock_id
            )
            SELECT
                COUNT(*) FILTER (WHERE bars >= 50) AS n,
                AVG(CASE WHEN last_close > sma50 THEN 1.0 ELSE 0.0 END)
                    FILTER (WHERE bars >= 50) AS breadth,
                AVG((last_close - close_20d) / close_20d)
                    FILTER (WHERE bars >= 50 AND close_20d > 0) AS universe_ret20
            FROM per_stock
        """), {"d": as_of_date}).fetchone()
        if row is None or row.n is None or row.n < 50:
            return None, None
        breadth = float(row.breadth) if row.breadth is not None else None
        uret = float(row.universe_ret20) if row.universe_ret20 is not None else None
        return breadth, uret

    def _prioritize_entries(
        self,
        fresh_recs: list,
        active_strategy: str,
        regime_label: str,
        as_of_date: date,
    ) -> list:
        """Order BUY candidates by expected value (P-21), with per-stock trend
        eligibility. Returns RecommendationResult objects in execution order.
        Falls back to conviction ordering when expectancy is thin (cold start)."""
        if not fresh_recs:
            return []

        # Lifecycle dual-sleeve gather (Tiers 1-3): replace the single active-strategy
        # recs with regime-aware candidates from BOTH sleeves — LEADERS (breakout_v2, any
        # regime) + BOUNCES (reversion_v3, non-bull) — each routed by the unified
        # stock-trend gate. Recs for all sleeves already exist (all-5-sync ranking).
        from app.core.config import get_settings as _get_settings_lc
        _ls = _get_settings_lc()
        if _ls.lifecycle_entry_enabled:
            fresh_recs = self._lifecycle_gather(as_of_date, _ls)
            if not fresh_recs:
                return []

        # Batch trend/volume context for all candidate stocks in one query.
        # close_20d (rn=20) supports the P-13 synthetic relative-strength check.
        from sqlalchemy import text as _text
        sids = [r.stock_id for r in fresh_recs]
        ctx_rows = self.db.execute(_text("""
            WITH recent AS (
                SELECT stock_id, close, volume,
                       ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY date DESC) AS rn
                FROM market_data
                WHERE stock_id = ANY(:sids) AND source = 'kite' AND date <= :d
            )
            SELECT stock_id,
                   MAX(close)  FILTER (WHERE rn = 1)  AS last_price,
                   AVG(close)  FILTER (WHERE rn <= 50) AS sma50,
                   AVG(close)  FILTER (WHERE rn <= 200) AS sma200,
                   AVG(close)  FILTER (WHERE rn BETWEEN 21 AND 220) AS sma200_prev,
                   MAX(close)  FILTER (WHERE rn = 20) AS close_20d,
                   MAX(volume) FILTER (WHERE rn = 1)  AS vol_today,
                   AVG(volume) FILTER (WHERE rn <= 90) AS vol_avg90,
                   AVG(close * volume) FILTER (WHERE rn <= 90) AS adv_value
            FROM recent WHERE rn <= 220 GROUP BY stock_id
        """), {"sids": sids, "d": as_of_date}).fetchall()
        ctx = {r.stock_id: r for r in ctx_rows}

        # (Lifecycle candidates were already gathered above, before the ctx query.)

        # P-14 breadth + P-13 synthetic universe benchmark (equal-weight 20-day mean
        # return) — one universe-wide query, the absolute market/segment context the
        # NIFTY-50 regime cannot see (the 2024-H1 failure mode).
        breadth_pct, universe_ret20 = self._market_context(as_of_date)

        provider = self._get_expectancy_provider(as_of_date)

        # Trend-following strategies require uptrend + volume + positive RS.
        # Mean-reversion strategies (reversal_v1, low_vol_v1) intentionally buy
        # oversold/quiet names *below* their 50-SMA and underperforming peers — those
        # gates must NOT apply to them, or they would veto every legitimate entry.
        _trend_following = active_strategy in ("breakout_v1", "momentum_v1")

        candidates: list[TradeCandidate] = []
        rec_by_id = {}
        for rec in fresh_recs:
            row = ctx.get(rec.stock_id)
            rec_by_id[rec.id] = rec
            # P-13 synthetic RS: stock 20-day return minus universe 20-day return.
            rs = None
            if (_trend_following and row and row.last_price is not None
                    and row.close_20d is not None and float(row.close_20d) > 0
                    and universe_ret20 is not None):
                stock_ret20 = (float(row.last_price) - float(row.close_20d)) / float(row.close_20d)
                rs = stock_ret20 - universe_ret20
            candidates.append(TradeCandidate(
                stock_id=rec.stock_id,
                symbol=str(rec.stock_id),
                strategy_name=active_strategy,
                rank=int(rec.rank) if rec.rank is not None else 999,
                conviction_score=float(rec.conviction_score or 0.0),
                market_regime=regime_label,
                recommendation_id=rec.id,
                last_price=float(row.last_price) if row and row.last_price is not None else None,
                sma50=float(row.sma50) if row and row.sma50 is not None else None,
                segment_state="UNKNOWN",  # true segment-index state needs P-13 index ingest
                volume_today=(float(row.vol_today)
                              if _trend_following and row and row.vol_today is not None else None),
                volume_avg90=(float(row.vol_avg90)
                              if _trend_following and row and row.vol_avg90 is not None else None),
                rs_vs_universe=rs,
                adv_value=(float(row.adv_value)
                           if row and row.adv_value is not None else None),
            ))

        # Breadth gate applies market-wide only to trend-following entries (mean-
        # reversion is designed to buy weak tape); pass None for reversal/low_vol.
        _breadth = breadth_pct if _trend_following else None
        ordered = prioritize(
            candidates, provider,
            breadth_pct=_breadth,
            require_uptrend=_trend_following,
        )
        # Map prioritized queue back to RecommendationResult objects, preserving order.
        return [rec_by_id[pc.candidate.recommendation_id] for pc in ordered]

    def _lifecycle_gather(self, as_of_date, settings):
        """Dual-sleeve lifecycle entry (Tiers 1-3). Pull the top-N BUY recs from BOTH
        sleeves — breakout_v2 (LEADERS, any regime) and, in a non-bull market,
        reversion_v3 (BOUNCES) — and keep the ones that clear the unified stock-trend
        gate. Recs for all sleeves already exist (all-5-sync ranking)."""
        from sqlalchemy import text as _text
        from app.lifecycle.entry import should_enter
        m3 = self.db.execute(_text(
            "SELECT market_regime_3way FROM regime_history "
            "WHERE as_of_date = :d AND benchmark_symbol = '^NSEI'"
        ), {"d": as_of_date}).scalar()
        if not m3:
            return []
        # leaders always; bounces only when the market is NOT bull (Tier 1: chop too).
        sleeves = ["breakout_v2"] if m3 == "BULL" else ["breakout_v2", "reversion_v3"]
        top_rank = settings.lifecycle_entry_top_rank or 5
        rows = self.db.execute(_text("""
            SELECT res.id AS rid, res.stock_id AS sid, res.rank AS rank, rr.strategy_name AS strat,
                   (SELECT max(rank) FROM ranking_results WHERE ranking_run_id = rr.ranking_run_id) AS pool
            FROM recommendation_results res
            JOIN recommendation_runs rr ON rr.id = res.recommendation_run_id
            WHERE rr.as_of_date = :d AND rr.strategy_name = ANY(:sl) AND res.action = 'BUY'
                  AND res.rank IS NOT NULL AND res.rank <= :tr
            ORDER BY res.rank
        """), {"d": as_of_date, "sl": sleeves, "tr": top_rank}).fetchall()
        kept_ids = []
        for r in rows:
            if should_enter(
                strategy=r.strat,
                market_regime_3way=m3,
                stock_trend_3way=self._stock_trend3_bars(r.sid, as_of_date),
                rank=int(r.rank),
                pool_size=int(r.pool) if r.pool else None,
                entry_top_pct=settings.lifecycle_entry_top_pct,
                top_rank=top_rank,
            ):
                kept_ids.append(r.rid)
        if not kept_ids:
            return []
        from app.models.recommendation import RecommendationResult
        return list(self.db.scalars(
            select(RecommendationResult).where(RecommendationResult.id.in_(kept_ids))
        ).all())

    def _stock_trend3_bars(self, stock_id, as_of) -> str | None:
        """Per-stock 3-way trend from a bars query (used before the ctx is built)."""
        from sqlalchemy import text as _text
        from app.ranking.math_utils import PriceBar
        from app.validation.regimes import classify_stock_trend
        rows = self.db.execute(_text(
            "SELECT date, close FROM market_data WHERE stock_id = :s AND date <= :d "
            "AND source = 'kite' ORDER BY date DESC LIMIT 260"
        ), {"s": stock_id, "d": as_of}).fetchall()
        if len(rows) < 220:
            return None
        bars = [PriceBar(date=r[0], close=float(r[1]), volume=None) for r in reversed(rows)]
        return classify_stock_trend(bars, as_of)

    def _stock_trend3(self, row) -> str | None:
        """Per-stock 3-way trend (BULL/BEAR/SIDEWAYS) from the entry context row
        (close / 50-SMA / 200-SMA + slope) — same logic as the market 3-way."""
        if row is None or getattr(row, "sma200", None) is None or row.last_price is None:
            return None
        from app.validation.constants import (
            REGIME_SLOPE_FLAT_PCT,
            TREND_REGIME_BEAR,
            TREND_REGIME_BULL,
            TREND_REGIME_SIDEWAYS,
        )
        last = float(row.last_price)
        sma200 = float(row.sma200)
        sma50 = float(row.sma50) if row.sma50 is not None else None
        sp = float(row.sma200_prev) if getattr(row, "sma200_prev", None) is not None else None
        slope = ((sma200 - sp) / sp) if sp else 0.0
        if last > sma200 and sma50 is not None and sma50 > sma200 and slope > REGIME_SLOPE_FLAT_PCT:
            return TREND_REGIME_BULL
        if last < sma200 and sma50 is not None and sma50 < sma200 and slope < -REGIME_SLOPE_FLAT_PCT:
            return TREND_REGIME_BEAR
        return TREND_REGIME_SIDEWAYS

    def _drain_pending_monitor_exits(self, as_of_date, exits: list, skipped: list) -> None:
        """Execute all currently-PENDING exit-monitor recommendations for the day and
        confirm them. Called once per phase (signal pre-buy, price post-buy) so each
        phase only drains the recs its own exit_monitor.run() just produced."""
        monitor_exits = self.db.scalars(
            select(ExitRecommendation).where(
                ExitRecommendation.as_of_date == as_of_date,
                ExitRecommendation.status == "PENDING",
            )
        ).all()
        for exit_rec in monitor_exits:
            pos = self.db.get(PortfolioPosition, exit_rec.portfolio_position_id)
            if pos is None or pos.position_status != "OPEN" or not pos.is_current:
                continue
            try:
                trade = self.paper_trade_service.execute_position_exit(
                    stock_id=exit_rec.stock_id,
                    as_of_date=as_of_date,
                    exit_triggers=list(exit_rec.triggers or []),
                    portfolio_exit_recommendation_id=exit_rec.id,
                    idempotency_key=f"pilot-exit-monitor:{exit_rec.id}",
                )
                self.exit_monitor.confirm(exit_rec.id)
                exits.append(str(trade.id))
            except Exception as exc:
                skipped.append({
                    "exit_recommendation_id": str(exit_rec.id),
                    "action": "exit_monitor", "error": str(exc),
                })

    def _execute_pilot_trades(
        self,
        as_of_date: date,
        *,
        pilot_auto_approve: bool,
    ) -> dict:
        entries: list[str] = []
        exits: list[str] = []
        skipped: list[dict] = []

        limits = self.portfolio_service.get_limits(as_of_date)

        # ── PHASE 1 — SIGNAL exits (daily-job pass, before buys) ──────────────────
        # rank-drop / alpha / regime / time / liquidity, decided on the prior close.
        # Frees slots for the buy round. (Intraday stop/trailing run in PHASE 3.)
        self.exit_monitor.run(as_of_date, trigger_group="signal")
        self._drain_pending_monitor_exits(as_of_date, exits, skipped)

        # EXIT_APPROVED recommendation rows (engine path, when present)
        exit_candidates = self.db.scalars(
            select(RecommendationResult).where(
                RecommendationResult.action == RecommendationAction.EXIT_APPROVED.value,
            )
        ).all()
        for rec in exit_candidates:
            pos = self.db.scalar(
                select(PortfolioPosition).where(
                    PortfolioPosition.stock_id == rec.stock_id,
                    PortfolioPosition.is_current.is_(True),
                    PortfolioPosition.position_status == "OPEN",
                )
            )
            if pos is None:
                continue
            try:
                approval_id = self._latest_approval_id(rec.id)
                if approval_id is None:
                    self.recommendation_service.approve(
                        rec.id,
                        approval_type="EXIT",
                        decision="APPROVED",
                        actor_id="paper_pilot",
                        note="Auto-approved exit for paper pilot",
                        idempotency_key=f"pilot-approve-exit:{rec.id}",
                    )
                    approval_id = self._latest_approval_id(rec.id)
                order = self.execution_service.submit_from_recommendation(
                    recommendation_id=rec.id,
                    approval_id=approval_id,
                    requested_by=self._pilot_actor_id,
                    as_of_date=as_of_date,
                    idempotency_key=f"pilot-exit:{rec.id}",
                )
                exits.append(str(order.id))
            except Exception as exc:
                skipped.append({"recommendation_id": str(rec.id), "action": "exit", "error": str(exc)})

        # Entries — BUY recommendations
        # Regime-gated strategy selection: only trade the strategy whose design
        # regime matches the current market regime. The other two still rank for
        # Factor IC evidence but do not generate live trades.
        # regime_label (4-way) gives finer routing than trend_regime (3-way).
        # BEAR_LOW_VOL: reversal has RCEE edge (ic_lo95=+0.010, hr=58.5%).
        # BEAR_HIGH_VOL: reversal is lethal (ic_lo95=-0.114); use low_vol instead.
        # BULL_HIGH_VOL: breakout underperforms in high-vol; momentum is safer.
        # MUST stay in sync with scripts/replay_fast.py _REGIME_STRATEGY. Suite-aware:
        # STRATEGY_SUITE=v2 routes trades to the forward-IC-validated v2/v3 sleeves
        # (currently breakout_v2 across regimes for the honest single-edge backtest;
        # extend to reversion_v3/momentum_v3 when wiring the multi-sleeve system).
        import os as _os
        _REGIME_STRATEGY_V1 = {
            "BULL_LOW_VOL":    "breakout_v1",
            "BULL_HIGH_VOL":   "momentum_v1",
            "BEAR_LOW_VOL":    "reversal_v1",
            "BEAR_HIGH_VOL":   "low_vol_v1",
            "NEUTRAL_LOW_VOL": "momentum_v1",
            "NEUTRAL_HIGH_VOL":"momentum_v1",
        }
        _REGIME_STRATEGY_V2 = {k: "breakout_v2" for k in _REGIME_STRATEGY_V1}
        # lifecycle: breakout_v2 in bull/neutral, reversion_v3 in bear (the 3-way entry
        # gate sits out actual SIDEWAYS). Must match scripts/replay_fast _REGIME_STRATEGY_LIFECYCLE.
        _REGIME_STRATEGY_LIFECYCLE = {
            "BULL_LOW_VOL": "breakout_v2", "BULL_HIGH_VOL": "breakout_v2",
            "BEAR_LOW_VOL": "reversion_v3", "BEAR_HIGH_VOL": "reversion_v3",
            "NEUTRAL_LOW_VOL": "breakout_v2", "NEUTRAL_HIGH_VOL": "breakout_v2",
        }
        _suite = _os.getenv("STRATEGY_SUITE", "v1").lower()
        _REGIME_STRATEGY: dict[str, str] = (
            _REGIME_STRATEGY_LIFECYCLE if _suite == "lifecycle"
            else _REGIME_STRATEGY_V2 if _suite == "v2"
            else _REGIME_STRATEGY_V1
        )
        from app.db.repositories.regime_analytics_repository import RegimeAnalyticsRepository
        from app.core.constants import DEFAULT_BENCHMARK_SYMBOL
        _regime_repo = RegimeAnalyticsRepository(self.db)
        _regime_row = _regime_repo.get_current(
            benchmark_symbol=DEFAULT_BENCHMARK_SYMBOL,
            as_of_date=as_of_date,
        )
        _regime_label = (_regime_row.regime_label if _regime_row else None) or "NEUTRAL_LOW_VOL"
        _active_strategy = _REGIME_STRATEGY.get(_regime_label, "momentum_v1")

        # P-22 (v18, flag-gated): rotate the defensive sleeve to gold in BEAR regimes.
        _gold = self._gold_rotation(as_of_date, _regime_label)
        if _gold and _gold.get("action", "").startswith("GOLD_"):
            entries.append(f"gold:{_gold['action']}")

        rec_runs = self.db.scalars(
            select(RecommendationRun).where(
                RecommendationRun.as_of_date == as_of_date,
                RecommendationRun.status == "completed",
                RecommendationRun.strategy_name == _active_strategy,
            )
        ).all()

        # Collect all buy candidates upfront
        all_buy_results: list = []
        for run in rec_runs:
            rows = self.db.scalars(
                select(RecommendationResult).where(
                    RecommendationResult.recommendation_run_id == run.id,
                    RecommendationResult.action == RecommendationAction.BUY.value,
                )
            ).all()
            all_buy_results.extend(rows)

        # Batch: fetch all open position stock_ids in one query
        _open_stock_ids: set = set(self.db.scalars(
            select(PortfolioPosition.stock_id).where(
                PortfolioPosition.is_current.is_(True),
                PortfolioPosition.position_status == "OPEN",
            )
        ).all())

        # ── P-21 Trade Decision Layer: order by expected value, not conviction ────
        # Eligibility (absolute per-stock trend) + prioritization (rank-bucketed
        # expectancy, horizon-matched). Cold-start / thin buckets fall back to
        # conviction so behaviour degrades gracefully. The ordered queue is the
        # same artifact a HITL reviewer would approve top-down.
        _fresh = [r for r in all_buy_results
                  if not r.portfolio_position_id and r.stock_id not in _open_stock_ids]
        _ordered_recs = self._prioritize_entries(
            _fresh, _active_strategy, _regime_label, as_of_date
        )
        # Missed-fill retry: pull band-misses from the last N trading days of the SAME
        # (now-active) strategy and let them COMPETE HEAD-TO-HEAD with today's fresh
        # picks — the merged pool is ranked by original rank then composite_score, so a
        # strong 3-day-old rank can bump a weak fresh one. The buy loop's band gate
        # re-checks each against today's bar and its slot/funding caps still apply.
        from app.core.config import get_settings as _gs0
        _retry_days = _gs0().entry_band_retry_days
        if _retry_days and _retry_days > 0:
            self._ensure_buy_trace_table()  # retry query reads buy_trace.recommendation_id
            _fresh_sids = {r.stock_id for r in _ordered_recs}
            _missed = self._collect_missed_recs(
                as_of_date, _active_strategy, _open_stock_ids, _fresh_sids, _retry_days)
            if _missed:
                _ordered_recs = sorted(
                    list(_ordered_recs) + _missed,
                    key=lambda r: (r.rank if r.rank is not None else 1_000_000,
                                   -(float(r.composite_score) if r.composite_score is not None else 0.0)))

        buys_today = 0
        from app.core.config import get_settings as _get_settings
        _settings = _get_settings()
        self._ensure_buy_trace_table()
        # Seed the ₹10L starting capital BEFORE any cash check. The funding waterfall
        # (cash floor + gold-yield) reads cash_balance() to size/gate each buy; without
        # this, day-1 cash reads 0 (initial capital was only seeded lazily inside the
        # entry path that the funding gate blocks) → every buy is skipped → zero trades.
        self.nav_service.ensure_initial_capital(as_of_date)
        # Live slot cap (fixes over-allocation): count open NON-gold positions now and
        # cap at max_positions, incremented per entry below. `limits.can_add_position`
        # was a stale day-start snapshot — when eligibility was loose (e.g. shorter RCEE
        # warm-up) it let many candidates through, opening far more than max_positions.
        # Gold is excluded — it is not a stock slot.
        _open_slots = self.db.scalar(
            select(func.count(PortfolioPosition.id)).where(
                PortfolioPosition.is_current.is_(True),
                PortfolioPosition.position_status == "OPEN",
                PortfolioPosition.strategy_name != "gold_rotation",
            )
        ) or 0
        for rec in _ordered_recs:
                if rec.portfolio_position_id:
                    continue
                if rec.stock_id in _open_stock_ids:
                    continue

                if pilot_auto_approve and rec.lifecycle_state != "APPROVED":
                    try:
                        self.recommendation_service.approve(
                            rec.id,
                            approval_type="PILOT_AUTO",
                            decision="APPROVED",
                            actor_id="paper_pilot",
                            note="Auto-approved for 90-day paper pilot",
                            idempotency_key=f"pilot-approve:{rec.id}",
                        )
                    except Exception as exc:
                        skipped.append({
                            "recommendation_id": str(rec.id),
                            "action": "approve",
                            "error": str(exc),
                        })
                        continue

                if rec.lifecycle_state not in ("APPROVED", "ACTIVE"):
                    skipped.append({
                        "recommendation_id": str(rec.id),
                        "action": "entry",
                        "reason": f"lifecycle={rec.lifecycle_state}",
                    })
                    continue

                if _open_slots >= limits.max_positions or buys_today >= limits.max_buy_per_day:
                    skipped.append({
                        "recommendation_id": str(rec.id),
                        "action": "entry",
                        "reason": limits.block_reason
                        or f"slot_limit: {_open_slots}/{limits.max_positions} open, "
                        f"{buys_today}/{limits.max_buy_per_day} buys today",
                    })
                    continue

                # P-05: volume confirmation — skip entry if today's volume < 70% of 90d avg.
                # Runs per-stock after slot check so it only fires on actual buy candidates.
                # reversal_v1 and low_vol_v1 intentionally buy quiet names — exempt.
                if _active_strategy in ("breakout_v1", "momentum_v1"):
                    from sqlalchemy import text as _text
                    _vol_row = self.db.execute(_text("""
                        WITH recent AS (
                            SELECT volume FROM market_data
                            WHERE stock_id = :sid AND source = 'kite'
                              AND date <= :d
                            ORDER BY date DESC LIMIT 90
                        ),
                        today_vol AS (
                            SELECT volume FROM market_data
                            WHERE stock_id = :sid AND source = 'kite' AND date = :d
                        )
                        SELECT
                            (SELECT volume FROM today_vol) as today_volume,
                            AVG(volume) as avg_90d
                        FROM recent
                    """), {"sid": rec.stock_id, "d": as_of_date}).fetchone()
                    if _vol_row and _vol_row[0] is not None and _vol_row[1] is not None:
                        if float(_vol_row[0]) < float(_vol_row[1]) * 0.70:
                            skipped.append({
                                "recommendation_id": str(rec.id),
                                "action": "entry",
                                "reason": f"LOW_VOLUME_ENTRY: {float(_vol_row[0]):.0f} < 70% of {float(_vol_row[1]):.0f}",
                            })
                            continue

                from sqlalchemy import text as _ctext
                # ── Entry-band LIMIT gate (price-tag) + buy trace ─────────────────
                # Treat the BUY as a limit order on the rec's band [entry_low, entry_high]
                # (= reference_close ± 0.5×ATR). Fill only if D+1 trades in/below the band;
                # gap-up (all O/H/L/C above the band) → SKIP. Every candidate is traced.
                _d1 = self.db.execute(_ctext(
                    "SELECT date, open, high, low, close FROM market_data "
                    "WHERE stock_id=:s AND date>:d AND source='kite' ORDER BY date LIMIT 1"),
                    {"s": rec.stock_id, "d": as_of_date}).fetchone()
                _el = float(rec.entry_low) if rec.entry_low is not None else None
                _eh = float(rec.entry_high) if rec.entry_high is not None else None
                _band_fill = None
                _rsn = None
                if _settings.entry_band_fills_enabled and _el is not None and _eh is not None:
                    _dec, _band_fill, _rsn = self._entry_band_decision(_d1, _el, _eh)
                    if _dec == "SKIPPED":
                        self._log_buy_trace(as_of_date, rec, _el, _eh, _d1, "SKIPPED", _rsn, None)
                        skipped.append({"recommendation_id": str(rec.id), "action": "entry", "reason": _rsn})
                        continue

                # ── Funding waterfall (cash floor + gold yields to buys) ──────────
                # Size to the concentration target, verify it can be PAID FOR: cash first,
                # then sell gold to its 25% bear floor. If still short → SKIP (no margin).
                _latest = self.db.execute(_ctext(
                    "SELECT close FROM market_data WHERE stock_id=:s AND date<=:d "
                    "ORDER BY date DESC LIMIT 1"), {"s": rec.stock_id, "d": as_of_date}).scalar()
                if _latest:
                    _alloc = self.portfolio_service.compute_allocation(
                        conviction_band=rec.conviction_band or "MEDIUM",
                        last_price=float(_latest), as_of_date=as_of_date)
                    _need = float(_alloc.position_notional) * 1.005  # + fee/slippage buffer
                    _cash = self.nav_service.cash_balance()
                    if _cash < _need:
                        _cash += self._raise_cash_from_gold(_need - _cash, as_of_date, _regime_label)
                    if _cash < _need:
                        self._log_buy_trace(as_of_date, rec, _el, _eh, _d1, "SKIPPED", "INSUFFICIENT_CASH", None)
                        skipped.append({
                            "recommendation_id": str(rec.id), "action": "entry",
                            "reason": f"INSUFFICIENT_CASH: need {_need:.0f} > cash {_cash:.0f} (gold at floor)"})
                        continue

                try:
                    approval_id = self._latest_approval_id(rec.id)
                    # D-1 rec → fill on D: date the entry on the gated next-session bar
                    # (_d1) so the position reflects when it actually filled, not the rec day.
                    _entry_as_of = as_of_date
                    if _settings.entry_execute_next_session and _d1 is not None:
                        _entry_as_of = _d1[0]
                    order = self.execution_service.submit_from_recommendation(
                        recommendation_id=rec.id,
                        approval_id=approval_id,
                        requested_by=self._pilot_actor_id,
                        as_of_date=_entry_as_of,
                        idempotency_key=f"pilot-entry:{rec.id}",
                    )
                    entries.append(str(order.id))
                    buys_today += 1
                    _open_slots += 1  # live slot cap — count this new position
                    _fill_rsn = (_rsn if _band_fill is not None else "EXECUTED")
                    if getattr(rec, "_is_retry", False):
                        _fill_rsn += "/RETRY"
                    self._log_buy_trace(as_of_date, rec, _el, _eh, _d1, "FILLED", _fill_rsn, _band_fill)
                except Exception as exc:
                    self._log_buy_trace(as_of_date, rec, _el, _eh, _d1, "SKIPPED", f"EXEC_ERROR: {str(exc)[:60]}", None)
                    skipped.append({
                        "recommendation_id": str(rec.id),
                        "action": "entry",
                        "error": str(exc),
                    })

        # ── PHASE 3 — INTRADAY exits (after buys, on D-day OHLC) ──────────────────
        # stop-loss / trailing fire against the trade-day high/low, on ALL still-open
        # trades — including names just bought this round (a same-day stop-out). This
        # is what the live exit monitor does intraday; here it runs post-buy.
        self.exit_monitor.run(as_of_date, trigger_group="price")
        self._drain_pending_monitor_exits(as_of_date, exits, skipped)

        return {
            "entries": entries,
            "exits": exits,
            "skipped": skipped,
            "entries_count": len(entries),
            "exits_count": len(exits),
            "regime_label": _regime_label,
            "active_strategy": _active_strategy,
        }

    def _latest_approval_id(self, recommendation_id: UUID) -> UUID | None:
        approval = self.db.scalar(
            select(RecommendationApproval)
            .where(
                RecommendationApproval.recommendation_result_id == recommendation_id,
                RecommendationApproval.decision == "APPROVED",
            )
            .order_by(RecommendationApproval.decided_at.desc())
        )
        return approval.id if approval else None

    def health_snapshot(self, as_of_date: date | None = None) -> dict:
        """Portfolio health for pilot dashboard — read-only."""
        as_of = as_of_date or date.today()
        limits = self.portfolio_service.get_limits(as_of)
        summary = self.portfolio_service.get_summary()
        nav = self.db.scalar(
            select(PortfolioNavHistory)
            .where(PortfolioNavHistory.as_of_date <= as_of)
            .order_by(PortfolioNavHistory.as_of_date.desc())
            .limit(1)
        )
        recon = self.reconciliation_service.get_latest()
        pending_exits = int(
            self.db.scalar(
                select(func.count(ExitRecommendation.id)).where(
                    ExitRecommendation.status == "PENDING"
                )
            )
            or 0
        )
        return {
            "as_of_date": as_of.isoformat(),
            "summary": summary,
            "limits": {
                "can_add_position": limits.can_add_position,
                "slots_available": limits.slots_available,
                "block_reason": limits.block_reason,
            },
            "nav": {
                "total_equity": float(nav.total_equity) if nav else None,
                "day_return_pct": float(nav.day_return_pct) if nav and nav.day_return_pct else None,
                "alpha_pct": float(nav.alpha_pct) if nav and nav.alpha_pct else None,
            },
            "reconciliation_status": recon.status if recon else None,
            "pending_exit_recommendations": pending_exits,
        }
