"""Portfolio Service — capital management, regime slots, position allocation.

All sizing is deterministic (PRD §5). No LLM involvement.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import DEFAULT_BENCHMARK_SYMBOL
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.regime_analytics_repository import RegimeAnalyticsRepository
from app.models.portfolio_analytics import PortfolioNavHistory
from app.models.portfolio_position import PortfolioConfig, PortfolioPosition
from app.models.stock import Stock

# ── Conviction band allocation weights (PRD §5) ───────────────────────────────
_CONVICTION_WEIGHTS: dict[str, float] = {
    "EXCEPTIONAL": 1.15,
    "HIGH": 1.00,
    "MEDIUM": 0.75,
    "LOW": 0.00,
    "BLOCKED": 0.00,
}

_DEFAULT_REGIME_SLOTS: dict[str, dict] = {
    "risk_on": {"max_positions": 8, "max_buy_per_day": 2},
    "neutral": {"max_positions": 6, "max_buy_per_day": 1},
    "defensive": {"max_positions": 4, "max_buy_per_day": 0},
    "crisis": {"max_positions": 2, "max_buy_per_day": 0},
}


@dataclass
class PortfolioSummary:
    total_equity: float
    deployable_capital: float
    cash_available: float
    cash_pct: float
    market_value: float
    unrealized_pnl: float
    active_positions: int
    regime_posture: str
    max_positions: int
    slots_available: int
    max_buy_per_day: int


@dataclass
class PositionAllocation:
    slot_budget: float  # deployable / max_slots
    position_notional: float  # slot_budget × conviction_weight
    quantity_estimate: float  # position_notional / last_price
    conviction_weight: float
    within_single_name_cap: bool
    within_sector_cap: bool


@dataclass
class RegimeLimits:
    regime_posture: str
    max_positions: int
    max_buy_per_day: int
    active_positions: int
    slots_available: int
    buys_today: int
    can_add_position: bool
    block_reason: str | None


class PortfolioService:
    def __init__(
        self,
        db: Session,
        *,
        portfolio_id: UUID | None = None,
        market_data_repo: MarketDataRepository | None = None,
        regime_repo: RegimeAnalyticsRepository | None = None,
    ) -> None:
        self.db = db
        self.portfolio_id = portfolio_id
        self.market_data_repo = market_data_repo or MarketDataRepository(db)
        self.regime_repo = regime_repo or RegimeAnalyticsRepository(db)

    # ── Config ────────────────────────────────────────────────────────────────

    def get_config(self) -> PortfolioConfig:
        stmt = select(PortfolioConfig).where(PortfolioConfig.is_active.is_(True))
        if self.portfolio_id is not None:
            stmt = stmt.where(PortfolioConfig.portfolio_id == self.portfolio_id)
        cfg = self.db.scalar(stmt.order_by(PortfolioConfig.created_at.desc()).limit(1))
        if cfg is None:
            raise ValueError("No active portfolio config. Call POST /portfolio/config first.")
        return cfg

    def upsert_config(
        self,
        total_equity: float,
        *,
        deploy_pct: float = 0.85,
        cash_floor_pct: float = 0.15,
        reserve_pct: float = 0.02,
        regime_slots: dict | None = None,
        notes: str | None = None,
    ) -> PortfolioConfig:
        # Deactivate existing
        stmt = select(PortfolioConfig).where(PortfolioConfig.is_active.is_(True))
        if self.portfolio_id is not None:
            stmt = stmt.where(PortfolioConfig.portfolio_id == self.portfolio_id)
        existing = self.db.scalars(stmt).all()
        for cfg in existing:
            cfg.is_active = False

        new_cfg = PortfolioConfig(
            portfolio_id=self.portfolio_id,
            is_active=True,
            total_equity=total_equity,
            deploy_pct=deploy_pct,
            cash_floor_pct=cash_floor_pct,
            reserve_pct=reserve_pct,
            regime_slots=regime_slots or _DEFAULT_REGIME_SLOTS,
            notes=notes,
        )
        self.db.add(new_cfg)
        self.db.flush()
        return new_cfg

    # ── Summary ───────────────────────────────────────────────────────────────

    def get_summary(self, as_of_date: date | None = None) -> PortfolioSummary:
        cfg = self.get_config()
        positions = self._current_positions()
        regime_posture = self._resolve_regime_posture(as_of_date)
        slots = self._regime_slots(cfg, regime_posture)

        nav_row = self._latest_nav(as_of_date)
        if nav_row is not None:
            total_equity = float(nav_row.total_equity)
            market_value = float(nav_row.market_value or 0)
            unrealized_pnl = float(nav_row.unrealized_pnl or 0)
            cash_available = float(nav_row.cash_balance or 0)
            cash_pct = float(nav_row.cash_pct or 0)
        else:
            market_value = sum(
                float(p.market_value or p.quantity * (p.avg_cost or 0)) for p in positions
            )
            unrealized_pnl = sum(float(p.unrealized_pnl or 0) for p in positions)
            total_equity = float(cfg.total_equity)
            cash_available = max(0.0, total_equity - market_value)
            cash_pct = cash_available / total_equity if total_equity else 0

        deployable = total_equity * float(cfg.deploy_pct)

        active_count = len(positions)
        max_positions = slots["max_positions"]
        slots_available = max(0, max_positions - active_count)

        return PortfolioSummary(
            total_equity=total_equity,
            deployable_capital=deployable,
            cash_available=cash_available,
            cash_pct=round(cash_pct, 4),
            market_value=market_value,
            unrealized_pnl=unrealized_pnl,
            active_positions=active_count,
            regime_posture=regime_posture,
            max_positions=max_positions,
            slots_available=slots_available,
            max_buy_per_day=slots["max_buy_per_day"],
        )

    def _latest_nav(self, as_of_date: date | None = None) -> PortfolioNavHistory | None:
        as_of = as_of_date or date.today()
        return self.db.scalar(
            select(PortfolioNavHistory)
            .where(PortfolioNavHistory.as_of_date <= as_of)
            .order_by(PortfolioNavHistory.as_of_date.desc())
            .limit(1)
        )

    def nav_basis(self, as_of_date: date | None = None) -> float:
        """Denominator for position weights — the SAME NAV the summary reports.

        Uses the latest ``portfolio_nav_history`` row's ``total_equity`` (cash +
        marked-to-market positions), falling back to the config seed equity only
        when no NAV snapshot exists yet. Dividing by the seed (often a ₹1L/₹10L
        placeholder, see context/GOTCHAS.md) is what produced the >100% phantom
        weights and false concentration breaches.
        """
        nav_row = self._latest_nav(as_of_date)
        if nav_row is not None:
            nav = float(nav_row.total_equity or 0)
            if nav > 0:
                return nav
        return float(self.get_config().total_equity)

    # ── Positions ─────────────────────────────────────────────────────────────

    def get_positions(self, include_closed: bool = False) -> list[PortfolioPosition]:
        if not include_closed:
            return self._current_positions()
        stmt = (
            select(PortfolioPosition)
            .order_by(PortfolioPosition.exit_date.desc().nulls_first(), PortfolioPosition.entry_date.desc())
        )
        if self.portfolio_id is not None:
            stmt = stmt.where(PortfolioPosition.portfolio_id == self.portfolio_id)
        return list(self.db.scalars(stmt).all())

    def get_limits(self, as_of_date: date | None = None) -> RegimeLimits:
        cfg = self.get_config()
        positions = self._current_positions()
        regime_posture = self._resolve_regime_posture(as_of_date)
        slots = self._regime_slots(cfg, regime_posture)

        active_count = len(positions)
        max_pos = slots["max_positions"]
        max_buy = slots["max_buy_per_day"]
        slots_avail = max(0, max_pos - active_count)

        # Count BUYs today (paper trades filled today)
        from sqlalchemy import func

        from app.core.constants import TradeStatus
        from app.models.paper_trade import PaperTrade

        eval_date = as_of_date or date.today()
        day_start = datetime(eval_date.year, eval_date.month, eval_date.day, tzinfo=UTC)
        day_end = datetime(eval_date.year, eval_date.month, eval_date.day, 23, 59, 59, tzinfo=UTC)
        buys_today = (
            self.db.scalar(
                select(func.count(PaperTrade.id)).where(
                    PaperTrade.side == "BUY",
                    PaperTrade.status == TradeStatus.FILLED.value,
                    PaperTrade.filled_at >= day_start,
                    PaperTrade.filled_at <= day_end,
                )
            )
            or 0
        )
        buys_today = int(buys_today) if buys_today else 0

        can_add = slots_avail > 0 and buys_today < max_buy
        block_reason = None
        if max_buy == 0:
            block_reason = f"REGIME_BLOCK: {regime_posture} posture — no new BUYs"
        elif slots_avail == 0:
            block_reason = f"PORTFOLIO_FULL: {active_count}/{max_pos} slots used"
        elif buys_today >= max_buy:
            block_reason = f"DAILY_BUY_LIMIT: {buys_today}/{max_buy} BUYs used today"

        return RegimeLimits(
            regime_posture=regime_posture,
            max_positions=max_pos,
            max_buy_per_day=max_buy,
            active_positions=active_count,
            slots_available=slots_avail,
            buys_today=int(buys_today),
            can_add_position=can_add,
            block_reason=block_reason,
        )

    def compute_allocation(
        self,
        conviction_band: str,
        last_price: float,
        symbol: str | None = None,
        sector: str | None = None,
    ) -> PositionAllocation:
        cfg = self.get_config()
        summary = self.get_summary()

        slot_budget = summary.deployable_capital / max(summary.max_positions, 1)

        # Position sizing version (v1 default; v2 risk-adjusted, feature-flagged)
        from app.portfolio.position_sizing import SizingInputs, size_position

        sizing_version = getattr(cfg, "position_sizing_version", "v1") or "v1"
        target_value = slot_budget * _CONVICTION_WEIGHTS.get(conviction_band, 0.0)
        sizing = size_position(
            SizingInputs(
                conviction_band=conviction_band,
                slot_budget=slot_budget,
                last_price=last_price,
                regime_posture=summary.regime_posture,
                target_position_value=target_value,
            ),
            version=sizing_version,
        )
        weight = sizing.conviction_weight
        position_notional = sizing.position_notional
        quantity = sizing.quantity

        # Single-name cap check
        single_name_max = float(cfg.total_equity) * float(cfg.single_name_cap_pct)
        within_single = position_notional <= single_name_max

        # Sector cap check (simplified — sum existing sector exposure)
        sector_exposure = 0.0
        if sector:
            for pos in self._current_positions():
                if pos.sector == sector:
                    sector_exposure += float(pos.market_value or 0)
        sector_max = float(cfg.total_equity) * float(cfg.sector_cap_pct)
        within_sector = (sector_exposure + position_notional) <= sector_max

        return PositionAllocation(
            slot_budget=round(slot_budget, 2),
            position_notional=round(position_notional, 2),
            quantity_estimate=round(quantity, 4),
            conviction_weight=weight,
            within_single_name_cap=within_single,
            within_sector_cap=within_sector,
        )

    # ── Position lifecycle ────────────────────────────────────────────────────

    def open_position(
        self,
        *,
        stock_id: UUID,
        quantity: float,
        fill_price: float,
        entry_date: date,
        recommendation_result_id: UUID | None = None,
        conviction_band: str | None = None,
        strategy_name: str | None = None,
        sector: str | None = None,
    ) -> PortfolioPosition:
        """Open a new position. Mark any existing current position for this stock as closed."""
        existing = self.db.scalar(
            select(PortfolioPosition).where(
                PortfolioPosition.stock_id == stock_id,
                PortfolioPosition.is_current.is_(True),
            )
        )
        if existing:
            existing.is_current = False
            self.db.flush()

        market_value = quantity * fill_price
        pos = PortfolioPosition(
            portfolio_id=self.portfolio_id,
            stock_id=stock_id,
            recommendation_result_id=recommendation_result_id,
            quantity=quantity,
            avg_cost=fill_price,
            entry_price=fill_price,
            entry_date=entry_date,
            market_value=market_value,
            unrealized_pnl=0.0,
            weight_pct=None,  # updated by recompute
            conviction_band=conviction_band,
            strategy_name=strategy_name,
            sector=sector,
            as_of=datetime.now(UTC),
            is_current=True,
            position_status="OPEN",
        )
        self.db.add(pos)
        self.db.flush()
        self._recompute_weights()
        return pos

    def close_position(
        self,
        stock_id: UUID,
        *,
        exit_price: float,
        exit_date: date,
    ) -> PortfolioPosition:
        pos = self.db.scalar(
            select(PortfolioPosition).where(
                PortfolioPosition.stock_id == stock_id,
                PortfolioPosition.is_current.is_(True),
            )
        )
        if pos is None:
            raise ValueError(f"No current open position for stock {stock_id}")

        realized_pnl = (exit_price - float(pos.avg_cost)) * float(pos.quantity)
        pos.exit_price = exit_price
        pos.exit_date = exit_date
        pos.realized_pnl = realized_pnl
        pos.unrealized_pnl = 0.0
        pos.market_value = float(pos.quantity) * exit_price
        pos.is_current = False
        pos.position_status = "CLOSED"
        self.db.flush()
        return pos

    def mark_to_market(self, as_of_date: date | None = None) -> int:
        """Update market_value and unrealized_pnl for all open positions."""
        positions = self._current_positions()

        # ADR-035: stop_loss_price is dynamic under regime stops — refresh it from
        # today's regime-resolved advisory %. No-op while the flag is off.
        from app.core.config import get_settings
        from app.portfolio.regime_stops import resolve_stop_pcts

        settings = get_settings()
        advisory_pct: float | None = None
        if settings.regime_dynamic_stops_enabled:
            advisory_pct, _ = resolve_stop_pcts(
                self.regime_repo, as_of=as_of_date, settings=settings
            )

        updated = 0
        for pos in positions:
            stock = self.db.get(Stock, pos.stock_id)
            if stock is None:
                continue
            latest = self.market_data_repo.get_latest_market_data(pos.stock_id)
            if latest is None:
                continue
            last_price = float(latest.close)
            pos.market_value = float(pos.quantity) * last_price
            pos.unrealized_pnl = (last_price - float(pos.avg_cost)) * float(pos.quantity)
            if advisory_pct is not None and pos.avg_cost:
                pos.stop_loss_price = round(float(pos.avg_cost) * (1 + advisory_pct / 100), 4)
            pos.as_of = datetime.now(UTC)
            updated += 1
        if updated:
            self._recompute_weights()
            self.db.flush()
        return updated

    def recompute(self) -> dict:
        """Admin rebuild — mark-to-market + weight recompute."""
        updated = self.mark_to_market()
        return {"positions_updated": updated}

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _current_positions(self) -> list[PortfolioPosition]:
        stmt = select(PortfolioPosition).where(
            PortfolioPosition.is_current.is_(True),
            PortfolioPosition.position_status == "OPEN",
        )
        if self.portfolio_id is not None:
            stmt = stmt.where(PortfolioPosition.portfolio_id == self.portfolio_id)
        return list(self.db.scalars(stmt).all())

    def _resolve_regime_posture(self, as_of_date: date | None = None) -> str:
        try:
            regime = self.regime_repo.get_current(
                benchmark_symbol=DEFAULT_BENCHMARK_SYMBOL,
                as_of_date=as_of_date,
            )
            if regime is None:
                return "neutral"
            label = (regime.regime_label or "").upper()
            if "BEAR" in label or "HIGH_VOL" in label:
                return "defensive"
            if "BULL" in label and "LOW_VOL" in label:
                return "risk_on"
            return "neutral"
        except Exception:
            return "neutral"

    def _regime_slots(self, cfg: PortfolioConfig, posture: str) -> dict:
        slots = cfg.regime_slots or {}
        return slots.get(
            posture, _DEFAULT_REGIME_SLOTS.get(posture, {"max_positions": 6, "max_buy_per_day": 1})
        )

    def _recompute_weights(self) -> None:
        basis = self.nav_basis()
        if basis <= 0:
            return
        positions = self._current_positions()
        for pos in positions:
            mv = float(pos.market_value or 0)
            pos.weight_pct = round(mv / basis * 100, 4)
