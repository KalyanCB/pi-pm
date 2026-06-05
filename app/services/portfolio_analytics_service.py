"""Portfolio Analytics Service — performance, risk, attribution, benchmark.

Orchestrates the pure analytics modules with DB data. Read-only.
Gated by reconciliation: refuses to compute when latest recon is FAIL.
No LLM. Deterministic (AC-PE-13).
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import DEFAULT_BENCHMARK_SYMBOL
from app.db.repositories.market_data_repository import MarketDataRepository
from app.models.portfolio_analytics import PortfolioNavHistory
from app.models.portfolio_position import PortfolioConfig, PortfolioPosition
from app.models.recommendation import RecommendationOutcome
from app.models.stock import Stock
from app.portfolio.analytics.attribution import AttributionReport, compute_attribution
from app.portfolio.analytics.benchmark import (
    BenchmarkComparison,
    SeriesPoint,
    compute_benchmark_comparison,
)
from app.portfolio.analytics.performance import (
    NavPoint,
    PerformanceMetrics,
    compute_performance,
)
from app.portfolio.analytics.risk import RiskMetrics, compute_risk
from app.portfolio.reconciliation.service import ReconciliationService

# NIFTY 500 total-return index symbol on Yahoo is ^CRSLDX; NIFTY 50 is ^NSEI
NIFTY_500_SYMBOL = "^CRSLDX"
NIFTY_50_SYMBOL = "^NSEI"


class ReconciliationGateError(Exception):
    """Raised when analytics are requested but reconciliation is FAIL."""


class PortfolioAnalyticsService:
    def __init__(
        self,
        db: Session,
        *,
        market_data_repo: MarketDataRepository | None = None,
        reconciliation_service: ReconciliationService | None = None,
    ) -> None:
        self.db = db
        self.market_data_repo = market_data_repo or MarketDataRepository(db)
        self.reconciliation_service = reconciliation_service or ReconciliationService(db)

    # ── Gate ──────────────────────────────────────────────────────────────────

    def _check_gate(self) -> None:
        ok, reason = self.reconciliation_service.is_healthy()
        if not ok:
            raise ReconciliationGateError(reason or "Reconciliation FAIL — analytics blocked")

    # ── Performance ───────────────────────────────────────────────────────────

    def get_performance(
        self,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> PerformanceMetrics:
        self._check_gate()
        nav_points = self._load_nav_series(from_date, to_date)
        closed = self._load_closed_outcomes(from_date, to_date)
        metrics = compute_performance(nav_points, closed)

        # Augment with exposure / turnover from NAV history + open count
        open_count = self._open_position_count()
        metrics.total_open_positions = open_count
        nav_rows = self._nav_rows(from_date, to_date)
        if nav_rows:
            exposures = [float(r.market_value) / float(r.total_equity) * 100
                         for r in nav_rows if r.total_equity and float(r.total_equity) > 0]
            cash_pcts = [float(r.cash_pct) * 100 for r in nav_rows if r.cash_pct is not None]
            metrics.avg_exposure_pct = round(sum(exposures) / len(exposures), 2) if exposures else None
            metrics.avg_cash_pct = round(sum(cash_pcts) / len(cash_pcts), 2) if cash_pcts else None
        metrics.turnover_pct = self._compute_turnover(from_date, to_date)
        return metrics

    # ── Risk ──────────────────────────────────────────────────────────────────

    def get_risk(self) -> RiskMetrics:
        self._check_gate()
        cfg = self._config()
        positions = self._open_positions_as_dicts()
        total_equity = float(cfg.total_equity) if cfg else 0.0
        cash = self._current_cash(total_equity)
        current_dd = self._current_drawdown()

        return compute_risk(
            positions=positions,
            total_equity=total_equity,
            cash_balance=cash,
            max_positions=self._max_positions(cfg),
            single_name_cap_pct=float(cfg.single_name_cap_pct) * 100 if cfg else 18.0,
            sector_cap_pct=float(cfg.sector_cap_pct) * 100 if cfg else 30.0,
            cash_floor_pct=float(cfg.cash_floor_pct) * 100 if cfg else 15.0,
            current_drawdown_pct=current_dd,
        )

    # ── Attribution ───────────────────────────────────────────────────────────

    def get_attribution(
        self,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> AttributionReport:
        self._check_gate()
        rows = self._load_outcome_dicts(from_date, to_date)
        return compute_attribution(rows)

    # ── Benchmark ─────────────────────────────────────────────────────────────

    def get_benchmark(
        self,
        benchmark: str = "nifty500",
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> BenchmarkComparison:
        self._check_gate()
        symbol = NIFTY_500_SYMBOL if benchmark == "nifty500" else NIFTY_50_SYMBOL
        nav_rows = self._nav_rows(from_date, to_date)
        portfolio_series = [SeriesPoint(r.as_of_date, float(r.total_equity)) for r in nav_rows]
        benchmark_series = self._load_benchmark_series(symbol, from_date, to_date)
        return compute_benchmark_comparison(portfolio_series, benchmark_series, symbol)

    # ── NAV history ───────────────────────────────────────────────────────────

    def get_nav_history(
        self,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[PortfolioNavHistory]:
        return self._nav_rows(from_date, to_date)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _config(self) -> PortfolioConfig | None:
        return self.db.scalar(
            select(PortfolioConfig)
            .where(PortfolioConfig.is_active.is_(True))
            .order_by(PortfolioConfig.created_at.desc())
            .limit(1)
        )

    def _max_positions(self, cfg: PortfolioConfig | None) -> int:
        if cfg is None or not cfg.regime_slots:
            return 6
        # Use neutral as default ceiling reference
        return cfg.regime_slots.get("neutral", {}).get("max_positions", 6)

    def _nav_rows(self, from_date: date | None, to_date: date | None) -> list[PortfolioNavHistory]:
        q = select(PortfolioNavHistory)
        if from_date:
            q = q.where(PortfolioNavHistory.as_of_date >= from_date)
        if to_date:
            q = q.where(PortfolioNavHistory.as_of_date <= to_date)
        q = q.order_by(PortfolioNavHistory.as_of_date)
        return list(self.db.scalars(q).all())

    def _load_nav_series(self, from_date: date | None, to_date: date | None) -> list[NavPoint]:
        rows = self._nav_rows(from_date, to_date)
        return [
            NavPoint(
                date=r.as_of_date,
                nav=float(r.total_equity),
                benchmark_nav=None,
            )
            for r in rows
        ]

    def _load_closed_outcomes(self, from_date: date | None, to_date: date | None) -> list[dict]:
        return self._load_outcome_dicts(from_date, to_date, closed_only=True)

    def _load_outcome_dicts(
        self,
        from_date: date | None,
        to_date: date | None,
        closed_only: bool = False,
    ) -> list[dict]:
        q = select(RecommendationOutcome)
        if closed_only:
            q = q.where(RecommendationOutcome.outcome_status != "OPEN")
        if from_date:
            q = q.where(RecommendationOutcome.entry_date >= from_date)
        if to_date:
            q = q.where(RecommendationOutcome.entry_date <= to_date)
        outcomes = list(self.db.scalars(q).all())
        return [
            {
                "symbol": o.symbol,
                "strategy_name": o.strategy_name,
                "conviction_band": o.conviction_band,
                "regime_label": o.regime_label,
                "committee_advisory": o.committee_advisory,
                "days_held": o.days_held,
                "pnl_pct": float(o.pnl_pct) if o.pnl_pct is not None else None,
                "alpha_pct": float(o.alpha_pct) if o.alpha_pct is not None else None,
                "outcome_status": o.outcome_status,
            }
            for o in outcomes
        ]

    def _open_positions_as_dicts(self) -> list[dict]:
        positions = list(self.db.scalars(
            select(PortfolioPosition).where(
                PortfolioPosition.is_current.is_(True),
                PortfolioPosition.position_status == "OPEN",
            )
        ).all())
        out = []
        for p in positions:
            stock = self.db.get(Stock, p.stock_id)
            unrealized_pct = None
            if p.avg_cost and p.market_value and float(p.avg_cost) > 0 and p.quantity:
                cost_basis = float(p.avg_cost) * float(p.quantity)
                if cost_basis > 0:
                    unrealized_pct = (float(p.market_value) - cost_basis) / cost_basis * 100
            out.append({
                "symbol": stock.symbol if stock else None,
                "market_value": float(p.market_value) if p.market_value else 0,
                "weight_pct": float(p.weight_pct) if p.weight_pct else 0,
                "sector": p.sector or (stock.sector if stock else None),
                "unrealized_pnl_pct": unrealized_pct,
            })
        return out

    def _open_position_count(self) -> int:
        from sqlalchemy import func
        return int(self.db.scalar(
            select(func.count(PortfolioPosition.id)).where(
                PortfolioPosition.is_current.is_(True),
                PortfolioPosition.position_status == "OPEN",
            )
        ) or 0)

    def _current_cash(self, total_equity: float) -> float:
        from sqlalchemy import func
        mv = float(self.db.scalar(
            select(func.sum(PortfolioPosition.market_value)).where(
                PortfolioPosition.is_current.is_(True),
                PortfolioPosition.position_status == "OPEN",
            )
        ) or 0.0)
        return max(0.0, total_equity - mv)

    def _current_drawdown(self) -> float | None:
        rows = self._nav_rows(None, None)
        if len(rows) < 2:
            return None
        peak = max(float(r.total_equity) for r in rows)
        current = float(rows[-1].total_equity)
        if peak <= 0:
            return None
        dd = (peak - current) / peak * 100
        return round(dd, 4) if dd > 0 else 0.0

    def _compute_turnover(self, from_date: date | None, to_date: date | None) -> float | None:
        from sqlalchemy import func
        from app.models.paper_trade import PaperTrade
        q = select(func.sum(PaperTrade.fill_price * PaperTrade.fill_quantity)).where(
            PaperTrade.status == "filled"
        )
        if from_date:
            q = q.where(PaperTrade.filled_at >= from_date)
        if to_date:
            q = q.where(PaperTrade.filled_at <= to_date)
        traded_value = float(self.db.scalar(q) or 0.0)
        nav_rows = self._nav_rows(from_date, to_date)
        if not nav_rows:
            return None
        avg_nav = sum(float(r.total_equity) for r in nav_rows) / len(nav_rows)
        if avg_nav <= 0:
            return None
        return round(traded_value / avg_nav * 100, 2)

    def _load_benchmark_series(
        self,
        symbol: str,
        from_date: date | None,
        to_date: date | None,
    ) -> list[SeriesPoint]:
        stock = self.db.scalar(select(Stock).where(Stock.symbol == symbol))
        if stock is None:
            # Fallback to NIFTY 50 if NIFTY 500 index not ingested
            stock = self.db.scalar(select(Stock).where(Stock.symbol == NIFTY_50_SYMBOL))
        if stock is None:
            return []
        bars = self.market_data_repo.get_by_stock_and_date_range(
            stock.id, start_date=from_date, end_date=to_date
        )
        bars_sorted = sorted(bars, key=lambda b: b.date)
        return [SeriesPoint(b.date, float(b.close)) for b in bars_sorted]
