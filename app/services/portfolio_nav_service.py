"""NAV Snapshot Service — writes daily portfolio_nav_history rows + cash ledger helper.

NAV history is the time series that powers performance analytics.
Cash ledger is the append-only money movement log for reconciliation.
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import DEFAULT_BENCHMARK_SYMBOL
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.regime_analytics_repository import RegimeAnalyticsRepository
from app.models.portfolio_analytics import CashLedger, PortfolioNavHistory
from app.models.portfolio_position import PortfolioConfig, PortfolioPosition


class PortfolioNavService:
    def __init__(
        self,
        db: Session,
        *,
        market_data_repo: MarketDataRepository | None = None,
        regime_repo: RegimeAnalyticsRepository | None = None,
    ) -> None:
        self.db = db
        self.market_data_repo = market_data_repo or MarketDataRepository(db)
        self.regime_repo = regime_repo or RegimeAnalyticsRepository(db)

    # ── Cash ledger ───────────────────────────────────────────────────────────

    def record_cash_entry(
        self,
        *,
        entry_type: str,
        amount: float,
        as_of_date: date,
        reference_id: UUID | None = None,
        reference_type: str | None = None,
        description: str | None = None,
    ) -> CashLedger:
        """Append a cash movement. amount: +in / -out."""
        prev_balance = float(
            self.db.scalar(select(func.sum(CashLedger.amount))) or 0.0
        )
        new_balance = prev_balance + amount
        entry = CashLedger(
            entry_type=entry_type,
            amount=amount,
            balance_after=new_balance,
            reference_id=reference_id,
            reference_type=reference_type,
            description=description,
            as_of_date=as_of_date,
        )
        self.db.add(entry)
        self.db.flush()
        return entry

    def ensure_initial_capital(self, as_of_date: date) -> None:
        """Seed the cash ledger with initial capital if empty."""
        existing = self.db.scalar(select(func.count(CashLedger.id)))
        if existing and existing > 0:
            return
        cfg = self._config()
        if cfg is None:
            return
        self.record_cash_entry(
            entry_type="INITIAL_CAPITAL",
            amount=float(cfg.total_equity),
            as_of_date=as_of_date,
            description="Initial portfolio capital",
        )

    def cash_balance(self) -> float:
        return float(self.db.scalar(select(func.sum(CashLedger.amount))) or 0.0)

    # ── NAV snapshot ──────────────────────────────────────────────────────────

    def snapshot(self, as_of_date: date | None = None) -> PortfolioNavHistory:
        """Write (or update) the NAV snapshot for as_of_date."""
        as_of = as_of_date or date.today()
        cfg = self._config()
        total_equity = float(cfg.total_equity) if cfg else 0.0

        positions = self._open_positions()
        market_value = sum(float(p.market_value or 0) for p in positions)
        unrealized = sum(float(p.unrealized_pnl or 0) for p in positions)

        realized_cum = float(self.db.scalar(
            select(func.sum(PortfolioPosition.realized_pnl)).where(
                PortfolioPosition.position_status == "CLOSED",
                PortfolioPosition.exit_date <= as_of,
            )
        ) or 0.0)

        # Cash from ledger; fall back to equity - mv when ledger empty
        cash = self.cash_balance()
        if cash == 0.0 and total_equity > 0:
            cash = max(0.0, total_equity - market_value)

        nav = cash + market_value
        cash_pct = (cash / nav) if nav > 0 else 0.0

        regime_label = self._regime_label(as_of)

        # Previous NAV for day return
        prev = self.db.scalar(
            select(PortfolioNavHistory)
            .where(PortfolioNavHistory.as_of_date < as_of)
            .order_by(PortfolioNavHistory.as_of_date.desc())
            .limit(1)
        )
        day_return = None
        if prev and float(prev.total_equity) > 0:
            day_return = (nav - float(prev.total_equity)) / float(prev.total_equity) * 100

        benchmark_return = self._benchmark_day_return(as_of)
        alpha = (day_return - benchmark_return) if (day_return is not None and benchmark_return is not None) else None

        existing = self.db.scalar(
            select(PortfolioNavHistory).where(PortfolioNavHistory.as_of_date == as_of)
        )
        row = existing or PortfolioNavHistory(as_of_date=as_of)
        row.total_equity = nav
        row.cash_balance = cash
        row.market_value = market_value
        row.unrealized_pnl = unrealized
        row.realized_pnl_cumulative = realized_cum
        row.open_positions = len(positions)
        row.cash_pct = round(cash_pct, 4)
        row.day_return_pct = round(day_return, 4) if day_return is not None else None
        row.benchmark_return_pct = round(benchmark_return, 4) if benchmark_return is not None else None
        row.alpha_pct = round(alpha, 4) if alpha is not None else None
        row.regime_label = regime_label
        if existing is None:
            self.db.add(row)
        self.db.flush()
        return row

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _config(self) -> PortfolioConfig | None:
        return self.db.scalar(
            select(PortfolioConfig)
            .where(PortfolioConfig.is_active.is_(True))
            .order_by(PortfolioConfig.created_at.desc())
            .limit(1)
        )

    def _open_positions(self) -> list[PortfolioPosition]:
        return list(self.db.scalars(
            select(PortfolioPosition).where(
                PortfolioPosition.is_current.is_(True),
                PortfolioPosition.position_status == "OPEN",
            )
        ).all())

    def _regime_label(self, as_of: date) -> str | None:
        try:
            regime = self.regime_repo.get_current(
                benchmark_symbol=DEFAULT_BENCHMARK_SYMBOL, as_of_date=as_of
            )
            return regime.regime_label if regime else None
        except Exception:
            return None

    def _benchmark_day_return(self, as_of: date) -> float | None:
        try:
            from app.models.stock import Stock
            stock = self.db.scalar(select(Stock).where(Stock.symbol == DEFAULT_BENCHMARK_SYMBOL))
            if stock is None:
                return None
            bars = self.market_data_repo.get_by_stock_and_date_range(
                stock.id, end_date=as_of, limit=2
            )
            if len(bars) < 2:
                return None
            # bars are desc by date
            today_close = float(bars[0].close)
            prev_close = float(bars[1].close)
            if prev_close <= 0:
                return None
            return (today_close - prev_close) / prev_close * 100
        except Exception:
            return None
