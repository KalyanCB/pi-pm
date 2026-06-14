"""IntradayExitMonitorService — T1 price monitor (ADR-033).

Responsibilities (price triggers only, per ADR-033 §1):
  - EXIT_STOP_LOSS    at advisory_stop_pct  → PENDING + notify owner (HITL required)
  - EXIT_STOP_LOSS    at critical_stop_pct  → auto-exec if auto_exit_on_critical_stop=true
  - EXIT_TRAILING_STOP                      → PENDING + notify owner

Non-responsibilities (stay in T2 daily swing monitor):
  - EXIT_RANK_DROP, EXIT_ALPHA_DECAY, EXIT_REGIME, EXIT_TIME, concentration, liquidity

Dedup key: (position_id, trigger_code, trading_session_date)
  One PENDING row per trigger per position per session. Severity upgrades
  update the existing row instead of creating a duplicate.

Auto-exec audit: actor_id='system', reason='AUTO_EXIT_RISK_OVERRIDE'.
  Fires only when:
    1. unrealized_pnl_pct <= critical_stop_pct
    2. auto_exit_on_critical_stop=True
    3. trigger ∈ {EXIT_STOP_LOSS, EXIT_TRAILING_STOP}
  Entries are NEVER auto-bypassed (ADR-033 §3).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.portfolio_analytics import ExitRecommendation
from app.models.portfolio_position import PortfolioPosition
from app.models.stock import Stock
from app.portfolio.exit_monitor.notification import NotificationEvent, build_notification
from app.portfolio.exit_monitor.quote_provider import LastCloseQuoteProvider, QuoteProvider
from app.portfolio.exit_monitor.triggers import check_stop_loss, check_trailing_stop

logger = logging.getLogger(__name__)

_SYSTEM_ACTOR = "system"
_URGENCY_ORDER = ["LOW", "NORMAL", "HIGH", "CRITICAL"]

# T1 only evaluates these triggers — rank/regime/time stay in T2
_T1_TRIGGER_CODES = {"EXIT_STOP_LOSS", "EXIT_TRAILING_STOP"}


@dataclass
class IntradayRunResult:
    """Summary returned by IntradayExitMonitorService.run()."""

    positions_evaluated: int
    new_recommendations: int   # freshly created PENDING rows
    severity_upgrades: int     # existing PENDING rows escalated
    auto_executed: int         # critical overrides fired
    notifications: list[NotificationEvent]


class IntradayExitMonitorService:
    """T1 price-only exit monitor.

    Inject a QuoteProvider at construction:
      - Paper mode  → LastCloseQuoteProvider(db)  (default)
      - Live S1+    → KiteQuoteProvider(...)       (future)
    """

    def __init__(
        self,
        db: Session,
        *,
        quote_provider: QuoteProvider | None = None,
        advisory_stop_pct: float | None = None,
        critical_stop_pct: float | None = None,
        trailing_stop_pct: float = 5.0,
        auto_exit_on_critical_stop: bool | None = None,
        paper_trade_service=None,  # injected; avoids circular import at module level
    ) -> None:
        self.db = db
        self._quote = quote_provider or LastCloseQuoteProvider(db)

        s = get_settings()
        # Explicit ctor overrides win; otherwise ADR-035 may resolve per-run.
        self._stops_explicit = advisory_stop_pct is not None or critical_stop_pct is not None
        self._advisory_stop = advisory_stop_pct if advisory_stop_pct is not None else s.advisory_stop_pct
        self._critical_stop = critical_stop_pct if critical_stop_pct is not None else s.critical_stop_pct
        self._trailing_stop = trailing_stop_pct
        self._auto_exit = (
            auto_exit_on_critical_stop
            if auto_exit_on_critical_stop is not None
            else s.auto_exit_on_critical_stop
        )
        self._paper_trade_service = paper_trade_service  # set lazily if needed

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self, session_date: date | None = None) -> IntradayRunResult:
        """Evaluate all OPEN positions for T1 price triggers.

        session_date: the trading session date for dedup (defaults to today).
        """
        sdate = session_date or date.today()

        # ADR-035: regime-dynamic stops — resolve once per run from the latest
        # regime label (no-op while the flag is off or ctor overrides were given).
        settings = get_settings()
        if settings.regime_dynamic_stops_enabled and not self._stops_explicit:
            from app.db.repositories.regime_analytics_repository import (
                RegimeAnalyticsRepository,
            )
            from app.portfolio.regime_stops import resolve_stop_pcts

            self._advisory_stop, self._critical_stop = resolve_stop_pcts(
                RegimeAnalyticsRepository(self.db), as_of=sdate, settings=settings
            )

        positions = self._get_open_positions()

        new_recs = 0
        upgrades = 0
        auto_executed = 0
        notifications: list[NotificationEvent] = []

        for pos in positions:
            ltp = self._quote.get_ltp(pos.stock_id)
            if ltp is None or not pos.avg_cost:
                continue

            avg_cost = float(pos.avg_cost)
            unrealized_pct = (ltp - avg_cost) / avg_cost * 100

            # Evaluate T1 triggers only
            stop_result = check_stop_loss(unrealized_pct, self._advisory_stop)
            max_gain = self._get_max_gain(pos)
            trail_result = check_trailing_stop(unrealized_pct, max_gain, self._trailing_stop)

            fired = [r for r in (stop_result, trail_result) if r.fired]
            if not fired:
                continue

            symbol = self._get_symbol(pos.stock_id)
            for trigger in fired:
                # Check for critical override FIRST — may auto-exec immediately
                is_critical = (
                    trigger.trigger_code == "EXIT_STOP_LOSS"
                    and unrealized_pct <= self._critical_stop
                    and self._auto_exit
                )

                existing = self._find_existing(pos.id, trigger.trigger_code, sdate)

                if existing is None:
                    # New recommendation — always start as PENDING/not-executed;
                    # auto-exec runs below and marks it CONFIRMED if it succeeds.
                    rec = self._create_recommendation(
                        pos=pos,
                        trigger=trigger,
                        unrealized_pct=unrealized_pct,
                        session_date=sdate,
                    )
                    new_recs += 1
                    notif = build_notification(
                        position_id=pos.id,
                        symbol=symbol,
                        trigger_code=trigger.trigger_code,
                        urgency=trigger.urgency,
                        unrealized_pnl_pct=unrealized_pct,
                        auto_executed=is_critical,
                    )
                    notifications.append(notif)
                    logger.info(
                        "T1 trigger fired",
                        extra={
                            "trigger": trigger.trigger_code,
                            "symbol": symbol,
                            "unrealized_pct": round(unrealized_pct, 2),
                            "urgency": trigger.urgency,
                            "auto_exec": is_critical,
                        },
                    )
                else:
                    # Severity upgrade path
                    old_urgency_idx = _URGENCY_ORDER.index(existing.urgency)
                    new_urgency_idx = _URGENCY_ORDER.index(trigger.urgency)
                    if new_urgency_idx > old_urgency_idx:
                        existing.urgency = trigger.urgency
                        existing.unrealized_pnl_pct = round(unrealized_pct, 4)
                        upgrades += 1
                        notif = build_notification(
                            position_id=pos.id,
                            symbol=symbol,
                            trigger_code=trigger.trigger_code,
                            urgency=trigger.urgency,
                            unrealized_pnl_pct=unrealized_pct,
                            auto_executed=False,
                        )
                        notifications.append(notif)
                        logger.info(
                            "T1 severity upgrade",
                            extra={
                                "trigger": trigger.trigger_code,
                                "symbol": symbol,
                                "old_urgency": _URGENCY_ORDER[old_urgency_idx],
                                "new_urgency": trigger.urgency,
                            },
                        )
                    rec = existing

                # Auto-exec: critical stop bypass
                if is_critical and not rec.auto_executed:
                    did_exec = self._auto_execute(pos, rec, sdate, symbol)
                    if did_exec:
                        auto_executed += 1

        self.db.flush()
        return IntradayRunResult(
            positions_evaluated=len(positions),
            new_recommendations=new_recs,
            severity_upgrades=upgrades,
            auto_executed=auto_executed,
            notifications=notifications,
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_open_positions(self) -> list[PortfolioPosition]:
        return list(
            self.db.scalars(
                select(PortfolioPosition).where(
                    PortfolioPosition.is_current.is_(True),
                    PortfolioPosition.position_status == "OPEN",
                )
            ).all()
        )

    def _find_existing(
        self, position_id: UUID, trigger_code: str, session_date: date
    ) -> ExitRecommendation | None:
        """Find a PENDING T1 recommendation for this trigger in this session.

        Dedup key: (position_id, trigger_code, as_of_date, monitor_tier=INTRADAY)
        """
        return self.db.scalar(
            select(ExitRecommendation).where(
                ExitRecommendation.portfolio_position_id == position_id,
                ExitRecommendation.as_of_date == session_date,
                ExitRecommendation.status == "PENDING",
                ExitRecommendation.monitor_tier == "INTRADAY",
                # Check if this trigger is already in the triggers list.
                # We use a JSONB contains check. Simpler: just check if any INTRADAY
                # PENDING exists and its triggers include this code.
                ExitRecommendation.triggers.contains([trigger_code]),
            )
        )

    def _create_recommendation(
        self,
        *,
        pos: PortfolioPosition,
        trigger,
        unrealized_pct: float,
        session_date: date,
    ) -> ExitRecommendation:
        """Create a PENDING INTRADAY recommendation. auto_exec is handled by caller."""
        rec = ExitRecommendation(
            portfolio_position_id=pos.id,
            stock_id=pos.stock_id,
            as_of_date=session_date,
            status="PENDING",
            triggers=[trigger.trigger_code],
            trigger_details={trigger.trigger_code: trigger.details},
            unrealized_pnl_pct=round(unrealized_pct, 4),
            urgency=trigger.urgency,
            monitor_tier="INTRADAY",
            auto_executed=False,
            actor_id=None,
        )
        self.db.add(rec)
        return rec

    def _auto_execute(
        self,
        pos: PortfolioPosition,
        rec: ExitRecommendation,
        session_date: date,
        symbol: str,
    ) -> bool:
        """Fire auto-sell via PaperTradeService (critical stop bypass).

        Audit: actor_id='system', reason='AUTO_EXIT_RISK_OVERRIDE'.
        Idempotency key: intraday-exit:{position_id}:EXIT_STOP_LOSS:{session_date}
        """
        if self._paper_trade_service is None:
            # Lazy import to avoid circular dependency
            from app.services.paper_trade_service import PaperTradeService
            self._paper_trade_service = PaperTradeService(self.db)

        idem_key = f"intraday-exit:{pos.id}:EXIT_STOP_LOSS:{session_date.isoformat()}"
        try:
            self._paper_trade_service.execute_position_exit(
                stock_id=pos.stock_id,
                as_of_date=session_date,
                exit_triggers=["EXIT_STOP_LOSS"],
                portfolio_exit_recommendation_id=rec.id,
                idempotency_key=idem_key,
            )
            rec.auto_executed = True
            rec.actor_id = _SYSTEM_ACTOR
            rec.status = "CONFIRMED"
            logger.warning(
                "AUTO_EXIT_RISK_OVERRIDE executed",
                extra={
                    "symbol": symbol,
                    "position_id": str(pos.id),
                    "recommendation_id": str(rec.id),
                    "session_date": session_date.isoformat(),
                },
            )
            return True
        except Exception as exc:
            logger.error(
                "Auto-exec failed — position remains open",
                extra={
                    "symbol": symbol,
                    "position_id": str(pos.id),
                    "error": str(exc),
                },
            )
            return False

    def _get_symbol(self, stock_id: UUID) -> str:
        stock = self.db.scalar(select(Stock).where(Stock.id == stock_id))
        return stock.symbol if stock else str(stock_id)

    def _get_max_gain(self, pos: PortfolioPosition) -> float | None:
        try:
            if pos.recommendation_result_id is None:
                return None
            from app.models.recommendation import RecommendationOutcome
            outcome = self.db.scalar(
                select(RecommendationOutcome).where(
                    RecommendationOutcome.recommendation_result_id == pos.recommendation_result_id
                )
            )
            return float(outcome.max_gain_pct) if outcome and outcome.max_gain_pct else None
        except Exception:
            return None
