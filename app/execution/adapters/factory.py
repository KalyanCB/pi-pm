"""Execution adapter factory — selects paper or live broker (Track K)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.execution.adapters.base import ExecutionAdapter
from app.execution.adapters.paper import PaperExecutionAdapter
from app.execution.adapters.zerodha_kite import ZerodhaKiteExecutionAdapter
from app.execution.constants import ExecutionMode
from app.services.portfolio_service import PortfolioService


class ExecutionAdapterFactory:
    def __init__(
        self,
        db: Session,
        *,
        settings: Settings | None = None,
        portfolio_id: str | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.portfolio_id = portfolio_id

    def get_adapter(self, mode: ExecutionMode) -> ExecutionAdapter:
        if mode == ExecutionMode.PAPER:
            portfolio_svc = None
            if self.portfolio_id:
                portfolio_svc = PortfolioService(self.db, portfolio_id=self.portfolio_id)
            return PaperExecutionAdapter(self.db, portfolio_service=portfolio_svc)
        if mode == ExecutionMode.LIVE:
            return ZerodhaKiteExecutionAdapter(self.settings)
        raise ValueError(f"Unsupported execution mode: {mode}")
