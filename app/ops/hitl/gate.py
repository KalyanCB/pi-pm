"""Human-In-The-Loop (HITL) Gate — feature-flagged approval control.

When HITL_ENABLED=True  (default / production):
  BUY recommendations require explicit human approval before execution.
  Recommendations sit in CANDIDATE state until approved via API.

When HITL_ENABLED=False (paper trading mode):
  BUYs are auto-approved immediately after committee review completes.
  pilot_auto_approve=True is passed to PaperPilotOps.
  All governance constraints remain: RCEE, conviction, committee are
  advisory but HITL approval step is skipped.

Non-negotiables (unchanged regardless of HITL flag):
  - LLMs never modify recommendation actions
  - Committee remains advisory only
  - Conviction scoring is deterministic
  - Full audit trail maintained (auto-approvals are logged with actor=HITL_AUTO)
  - All lineage preserved

Usage:
    gate = HITLGate.from_settings()
    if gate.auto_approve:
        # execute without waiting for human input
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_AUTO_ACTOR_ID = "hitl_auto"
_AUTO_APPROVAL_TYPE = "HITL_AUTO"
_AUTO_NOTE = "Auto-approved: HITL_ENABLED=false (paper trading mode)"


@dataclass(frozen=True)
class HITLGate:
    """Immutable HITL configuration derived from settings."""

    hitl_enabled: bool
    paper_trading_enabled: bool

    @classmethod
    def from_settings(cls) -> "HITLGate":
        s = get_settings()
        return cls(
            hitl_enabled=s.hitl_enabled,
            paper_trading_enabled=s.paper_trading_enabled,
        )

    @property
    def auto_approve(self) -> bool:
        """True when human approval step is bypassed."""
        return not self.hitl_enabled

    @property
    def should_execute_paper_trades(self) -> bool:
        """True when autonomous paper trade execution is active."""
        return self.paper_trading_enabled and not self.hitl_enabled

    def log_status(self) -> None:
        if self.auto_approve:
            logger.info(
                "HITL gate: DISABLED — BUYs will be auto-approved after committee "
                "(paper_trading_enabled=%s)",
                self.paper_trading_enabled,
            )
        else:
            logger.info(
                "HITL gate: ENABLED — BUYs require human approval "
                "(paper_trading_enabled=%s)",
                self.paper_trading_enabled,
            )

    def auto_approve_buys(
        self,
        db: Session,
        as_of_date: date,
        *,
        max_slots: int = 5,
    ) -> dict:
        """Auto-approve CANDIDATE BUYs when HITL_ENABLED=false.

        Called after committee review. Records approval with actor=hitl_auto
        for full auditability. Only approves BUYs in CANDIDATE lifecycle state.

        Returns dict with approved/skipped counts.
        """
        if not self.auto_approve:
            return {"skipped": "hitl_enabled=true — manual approval required"}

        from sqlalchemy import select
        from app.models.recommendation import (
            RecommendationApproval,
            RecommendationResult,
            RecommendationRun,
        )
        from app.core.constants import RecommendationAction

        # Load CANDIDATE BUYs for today that haven't been approved yet
        candidates = db.scalars(
            select(RecommendationResult)
            .join(RecommendationRun, RecommendationResult.recommendation_run_id == RecommendationRun.id)
            .where(
                RecommendationResult.action == RecommendationAction.BUY.value,
                RecommendationResult.lifecycle_state == "CANDIDATE",
                RecommendationRun.as_of_date == as_of_date,
            )
            .order_by(RecommendationResult.conviction_score.desc())
        ).all()

        approved: list[str] = []
        skipped: list[str] = []

        for rec in candidates[:max_slots]:
            # Idempotency: skip if already approved
            existing = db.scalar(
                select(RecommendationApproval).where(
                    RecommendationApproval.recommendation_result_id == rec.id,
                    RecommendationApproval.decision == "APPROVED",
                )
            )
            if existing:
                skipped.append(str(rec.id))
                continue

            # Create auto-approval record
            approval = RecommendationApproval(
                recommendation_result_id=rec.id,
                approval_type=_AUTO_APPROVAL_TYPE,
                decision="APPROVED",
                actor_id=_AUTO_ACTOR_ID,
                note=_AUTO_NOTE,
                decided_at=datetime(as_of_date.year, as_of_date.month, as_of_date.day, 12, 0, tzinfo=UTC),
                idempotency_key=f"hitl-auto:{rec.id}:{as_of_date.isoformat()}",
            )
            db.add(approval)
            rec.lifecycle_state = "APPROVED"
            approved.append(str(rec.id))
            logger.debug(
                "HITL auto-approved BUY: result_id=%s conviction=%s band=%s",
                rec.id, rec.conviction_score, rec.conviction_band,
            )

        db.flush()
        logger.info(
            "HITL auto-approval complete: approved=%d skipped=%d date=%s",
            len(approved), len(skipped), as_of_date,
        )
        return {
            "approved": approved,
            "skipped_already_approved": skipped,
            "approved_count": len(approved),
        }
