from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_regime_policy_service
from app.schemas.regime_policy import (
    RegimePolicyBacktestRunRequest,
    RegimePolicyConfigCreate,
    RegimePolicyEvaluateRequest,
    RegimePolicyPresetLoadRequest,
    RegimePolicyPresetLoadResponse,
)
from app.services.regime_policy_service import RegimePolicyService

router = APIRouter()


def _config_to_read(config) -> dict:
    return {
        "id": str(config.id),
        "policy_name": config.policy_name,
        "policy_type": config.policy_type,
        "strategy_name": config.strategy_name,
        "strategy_version": config.strategy_version,
        "policy_version": config.policy_version,
        "allowed_regimes": list(config.allowed_regimes or []),
        "size_multipliers": dict(config.size_multipliers or {}),
        "min_decile": config.min_decile,
        "max_decile": config.max_decile,
        "default_action": config.default_action,
        "status": config.status,
        "effective_from": config.effective_from.isoformat() if config.effective_from else None,
        "notes": config.notes,
        "created_at": config.created_at.isoformat(),
        "activated_at": config.activated_at.isoformat() if config.activated_at else None,
    }


@router.get("/configs")
def list_configs(
    strategy_name: str | None = None,
    strategy_version: str | None = None,
    policy_type: str | None = None,
    status: str | None = None,
    service: RegimePolicyService = Depends(get_regime_policy_service),
) -> list[dict]:
    configs = service.list_configs(
        strategy_name=strategy_name,
        strategy_version=strategy_version,
        policy_type=policy_type,
        status=status,
    )
    return [_config_to_read(c) for c in configs]


@router.post("/configs")
def create_config(
    payload: RegimePolicyConfigCreate,
    service: RegimePolicyService = Depends(get_regime_policy_service),
) -> dict:
    config = service.create_config(
        policy_name=payload.policy_name,
        policy_type=payload.policy_type,
        strategy_name=payload.strategy_name,
        strategy_version=payload.strategy_version,
        allowed_regimes=payload.allowed_regimes,
        size_multipliers=payload.size_multipliers,
        min_decile=payload.min_decile,
        max_decile=payload.max_decile,
        default_action=payload.default_action,
        notes=payload.notes,
    )
    return _config_to_read(config)


@router.post("/configs/presets/load")
def load_presets(
    payload: RegimePolicyPresetLoadRequest | None = None,
    service: RegimePolicyService = Depends(get_regime_policy_service),
) -> RegimePolicyPresetLoadResponse:
    dry_run = payload.dry_run if payload else False
    configs = service.load_presets(dry_run=dry_run)
    return RegimePolicyPresetLoadResponse(
        loaded_count=len(configs),
        config_ids=[str(c.id) for c in configs],
        dry_run=dry_run,
    )


@router.post("/configs/{config_id}/activate")
def activate_config(
    config_id: UUID,
    service: RegimePolicyService = Depends(get_regime_policy_service),
) -> dict:
    try:
        config = service.activate_config(config_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _config_to_read(config)


@router.get("/decisions")
def list_decisions(
    ranking_run_id: UUID | None = None,
    as_of_date: date | None = None,
    regime_label: str | None = None,
    action: str | None = None,
    experiment_run_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    service: RegimePolicyService = Depends(get_regime_policy_service),
) -> list[dict]:
    return service.list_decisions(
        ranking_run_id=ranking_run_id,
        as_of_date=as_of_date,
        regime_label=regime_label,
        action=action,
        experiment_run_id=experiment_run_id,
        limit=limit,
    )


@router.post("/evaluate")
def evaluate_policy(
    payload: RegimePolicyEvaluateRequest,
    service: RegimePolicyService = Depends(get_regime_policy_service),
) -> dict:
    try:
        return service.evaluate(
            ranking_run_id=payload.ranking_run_id,
            policy_config_id=payload.policy_config_id,
            persist=payload.persist,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/backtest/run")
def run_backtest(
    payload: RegimePolicyBacktestRunRequest,
    service: RegimePolicyService = Depends(get_regime_policy_service),
) -> dict:
    try:
        return service.run_backtest_comparison(
            strategy_name=payload.strategy_name,
            strategy_version=payload.strategy_version,
            universe_code=payload.universe_code,
            horizon=payload.horizon,
            start_date=payload.start_date,
            end_date=payload.end_date,
            holdout_start_date=payload.holdout_start_date,
            policy_config_ids=payload.policy_config_ids,
            baseline_policy_config_id=payload.baseline_policy_config_id,
            experiment_name=payload.experiment_name,
            persist_decisions=payload.persist_decisions,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/backtest/runs")
def list_backtest_runs(
    experiment_run_id: UUID | None = None,
    policy_config_id: UUID | None = None,
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    service: RegimePolicyService = Depends(get_regime_policy_service),
) -> list[dict]:
    return service.list_backtest_runs(
        experiment_run_id=experiment_run_id,
        policy_config_id=policy_config_id,
        status=status,
        limit=limit,
    )
