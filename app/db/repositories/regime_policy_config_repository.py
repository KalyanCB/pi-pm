from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import PolicyConfigStatus
from app.models.regime_policy import RegimePolicyConfig


class RegimePolicyConfigRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        policy_name: str,
        policy_type: str,
        strategy_name: str,
        strategy_version: str,
        policy_version: int,
        allowed_regimes: list[str],
        size_multipliers: dict[str, float],
        min_decile: int | None,
        max_decile: int | None,
        default_action: str,
        notes: str | None = None,
    ) -> RegimePolicyConfig:
        config = RegimePolicyConfig(
            policy_name=policy_name,
            policy_type=policy_type,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            policy_version=policy_version,
            allowed_regimes=allowed_regimes,
            size_multipliers=size_multipliers,
            min_decile=min_decile,
            max_decile=max_decile,
            default_action=default_action,
            status=PolicyConfigStatus.DRAFT.value,
            notes=notes,
            created_at=datetime.now(UTC),
        )
        self.db.add(config)
        self.db.flush()
        return config

    def get_by_id(self, config_id: UUID) -> RegimePolicyConfig | None:
        return self.db.scalar(
            select(RegimePolicyConfig).where(RegimePolicyConfig.id == config_id)
        )

    def get_next_version(self, policy_name: str) -> int:
        current = self.db.scalar(
            select(RegimePolicyConfig.policy_version)
            .where(RegimePolicyConfig.policy_name == policy_name)
            .order_by(RegimePolicyConfig.policy_version.desc())
            .limit(1)
        )
        return (current or 0) + 1

    def list_configs(
        self,
        *,
        strategy_name: str | None = None,
        strategy_version: str | None = None,
        policy_type: str | None = None,
        status: str | None = None,
    ) -> list[RegimePolicyConfig]:
        stmt = select(RegimePolicyConfig).order_by(RegimePolicyConfig.created_at.desc())
        if strategy_name:
            stmt = stmt.where(RegimePolicyConfig.strategy_name == strategy_name)
        if strategy_version:
            stmt = stmt.where(RegimePolicyConfig.strategy_version == strategy_version)
        if policy_type:
            stmt = stmt.where(RegimePolicyConfig.policy_type == policy_type)
        if status:
            stmt = stmt.where(RegimePolicyConfig.status == status)
        return list(self.db.scalars(stmt).all())

    def find_by_name_and_version(
        self,
        policy_name: str,
        policy_version: int,
    ) -> RegimePolicyConfig | None:
        return self.db.scalar(
            select(RegimePolicyConfig).where(
                RegimePolicyConfig.policy_name == policy_name,
                RegimePolicyConfig.policy_version == policy_version,
            )
        )

    def archive_active_for_type(
        self,
        strategy_name: str,
        strategy_version: str,
        policy_type: str,
    ) -> None:
        active = self.db.scalars(
            select(RegimePolicyConfig).where(
                RegimePolicyConfig.strategy_name == strategy_name,
                RegimePolicyConfig.strategy_version == strategy_version,
                RegimePolicyConfig.policy_type == policy_type,
                RegimePolicyConfig.status == PolicyConfigStatus.ACTIVE.value,
            )
        ).all()
        for config in active:
            config.status = PolicyConfigStatus.ARCHIVED.value
        self.db.flush()

    def activate(self, config: RegimePolicyConfig) -> RegimePolicyConfig:
        self.archive_active_for_type(
            config.strategy_name,
            config.strategy_version,
            config.policy_type,
        )
        config.status = PolicyConfigStatus.ACTIVE.value
        config.activated_at = datetime.now(UTC)
        self.db.flush()
        return config
