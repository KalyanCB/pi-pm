from __future__ import annotations

import logging
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import (
    LineageEntityType,
    LineageRelationshipType,
)
from app.db.repositories.run_lineage_repository import RunLineageRepository
from app.db.repositories.stock_repository import StockRepository
from app.db.repositories.stock_setup_research_repository import StockSetupResearchRepository
from app.models.platform_traceability import RegimeHistory
from app.models.ranking_result import RankingResult
from app.models.ranking_run import RankingRun
from app.models.stock import Stock
from app.ranking.loader import MarketDataLoader
from app.stock_setup_evidence.constants import (
    DEFAULT_HISTORY_TRADING_DAYS,
    DEFAULT_MAX_STORED_SETUPS,
    DEFAULT_MIN_SIMILARITY,
    DEFAULT_NEAREST_SETUPS,
    DEFAULT_SETUP_SAMPLE_STEP,
    REGIME_LABELS_V2,
    SEE_ENGINE_VERSION,
    STOCK_SETUP_STATUS_COMPLETED,
    STOCK_SETUP_STATUS_FAILED,
    STOCK_SETUP_STATUS_INSUFFICIENT_DATA,
)
from app.stock_setup_evidence.hashing import compute_research_hash
from app.stock_setup_evidence.outcomes import (
    aggregate_outcomes,
    build_setup_outcomes,
    metrics_to_dict,
)
from app.stock_setup_evidence.profile import (
    build_stock_internal_normalized_profiles,
    extract_reference_profile,
    list_candidate_setup_dates,
)
from app.stock_setup_evidence.scoring import compute_setup_evidence_score
from app.stock_setup_evidence.similarity import select_qualifying_setups
from app.stock_setup_evidence.strategy_profiles import resolve_see_strategy
from app.universe.models import StockSnapshot

logger = logging.getLogger(__name__)


class StockSetupResearchService:
    def __init__(
        self,
        db: Session,
        *,
        research_repo: StockSetupResearchRepository,
        stock_repo: StockRepository,
        lineage_repo: RunLineageRepository,
        market_data_loader: MarketDataLoader,
    ) -> None:
        self.db = db
        self.research_repo = research_repo
        self.stock_repo = stock_repo
        self.lineage_repo = lineage_repo
        self.loader = market_data_loader

    def run_for_ranking_run(
        self,
        ranking_run_id: UUID,
        *,
        limit: int | None = None,
        nearest_n: int = DEFAULT_NEAREST_SETUPS,
        min_similarity: float = DEFAULT_MIN_SIMILARITY,
    ) -> dict:
        run = self.db.get(RankingRun, ranking_run_id)
        if run is None:
            raise ValueError(f"Ranking run not found: {ranking_run_id}")

        results = list(
            self.db.scalars(
                select(RankingResult)
                .where(RankingResult.ranking_run_id == ranking_run_id)
                .order_by(RankingResult.rank)
            ).all()
        )
        if limit is not None:
            results = results[:limit]

        completed = 0
        failed = 0
        for result in results:
            stock = self.stock_repo.get_by_id(result.stock_id)
            if stock is None:
                failed += 1
                continue
            try:
                self.run_for_candidate(
                    run,
                    result,
                    stock,
                    nearest_n=nearest_n,
                    min_similarity=min_similarity,
                )
                completed += 1
            except Exception as exc:
                logger.exception("SEE failed for %s on run %s", stock.symbol, ranking_run_id)
                self._persist_failure(run, result, stock, str(exc), nearest_n, min_similarity)
                failed += 1

        self.db.commit()
        return {
            "ranking_run_id": str(ranking_run_id),
            "engine_version": SEE_ENGINE_VERSION,
            "candidates": len(results),
            "completed": completed,
            "failed": failed,
        }

    def run_for_candidate(
        self,
        ranking_run: RankingRun,
        result: RankingResult,
        stock: Stock,
        *,
        nearest_n: int = DEFAULT_NEAREST_SETUPS,
        min_similarity: float = DEFAULT_MIN_SIMILARITY,
        history_trading_days: int = DEFAULT_HISTORY_TRADING_DAYS,
        sample_step: int = DEFAULT_SETUP_SAMPLE_STEP,
        max_stored_setups: int = DEFAULT_MAX_STORED_SETUPS,
    ) -> dict:
        strategy_config = resolve_see_strategy(ranking_run.strategy_name)
        reference = extract_reference_profile(
            result.score_components,
            factor_names=strategy_config.factor_names,
        )
        min_factors = min(3, len(strategy_config.factor_names))
        if len(reference) < min_factors:
            return self._persist_insufficient(
                ranking_run,
                result,
                stock,
                reference,
                strategy_config.strategy_name,
                nearest_n,
                min_similarity,
                reason="reference_profile_too_sparse",
            )

        source = "yahoo"
        stock_series = self.loader.load_series(stock.id, ranking_run.as_of_date, source=source)
        benchmark_id = self._resolve_benchmark_stock_id(ranking_run.benchmark_symbol)
        bench_series = (
            self.loader.load_series(benchmark_id, ranking_run.as_of_date, source=source)
            if benchmark_id
            else []
        )

        snapshot = StockSnapshot(
            stock_id=stock.id,
            symbol=stock.symbol,
            name=stock.name,
            exchange=stock.exchange,
            sector=stock.sector,
            is_active=stock.is_active,
            data_status=stock.data_status,
        )
        candidate_dates = list_candidate_setup_dates(
            stock_series,
            ranking_run.as_of_date,
            max_trading_days=history_trading_days,
            sample_step=sample_step,
        )
        historical = build_stock_internal_normalized_profiles(
            snapshot,
            stock_series,
            bench_series or None,
            candidate_dates,
            strategy_config=strategy_config,
            min_factors=min_factors,
        )
        matches, total_scored = select_qualifying_setups(
            reference,
            historical,
            factor_names=strategy_config.factor_names,
            min_similarity=min_similarity,
        )
        if nearest_n > 0:
            stored_matches = matches[:nearest_n]
        else:
            stored_matches = matches

        regime_by_date = self._load_regime_by_date(
            ranking_run.benchmark_symbol, [m[0] for m in matches]
        )
        outcomes = build_setup_outcomes(stock_series, matches, regime_by_date)

        metrics_by_regime: dict = {}
        metrics_payload: list[dict] = []
        for label in REGIME_LABELS_V2:
            agg = aggregate_outcomes(outcomes, label)
            metrics_by_regime[label] = agg
            metrics_payload.append(metrics_to_dict(agg))

        evidence_score = compute_setup_evidence_score(
            metrics_by_regime,
            qualifying_matches=len(matches),
        )

        similar_setups = [
            {
                "setup_date": o.setup_date.isoformat(),
                "similarity_score": round(o.similarity_score, 4),
                "regime_label": o.regime_label,
                "return_5d": o.return_5d,
                "return_20d": o.return_20d,
                "max_drawdown_20d": o.max_drawdown_20d,
                "max_runup_20d": o.max_runup_20d,
            }
            for o in outcomes[:max_stored_setups]
        ]

        parameter_set = {
            "engine_version": SEE_ENGINE_VERSION,
            "strategy_name": strategy_config.strategy_name,
            "nearest_n": nearest_n,
            "min_similarity": min_similarity,
            "history_trading_days": history_trading_days,
            "sample_step": sample_step,
            "retrieval_mode": "threshold",
            "max_stored_setups": max_stored_setups,
        }
        hash_input = {
            "engine_version": SEE_ENGINE_VERSION,
            "strategy_name": strategy_config.strategy_name,
            "reference_profile": reference,
            "parameter_set": parameter_set,
            "total_matches": total_scored,
            "qualifying_matches": len(matches),
        }
        research_hash = compute_research_hash(hash_input)

        row = self.research_repo.replace_for_run_stock(
            ranking_run_id=ranking_run.id,
            ranking_result_id=result.id,
            stock_id=stock.id,
            symbol=stock.symbol,
            as_of_date=ranking_run.as_of_date,
            strategy_name=strategy_config.strategy_name,
            engine_version=SEE_ENGINE_VERSION,
            status=STOCK_SETUP_STATUS_COMPLETED,
            reference_profile=reference,
            similar_setups=similar_setups,
            nearest_n=nearest_n,
            min_similarity=min_similarity,
            match_count=len(matches),
            total_matches=total_scored,
            qualifying_matches=len(matches),
            setup_evidence_score=evidence_score,
            parameter_set=parameter_set,
            research_hash=research_hash,
            metrics=metrics_payload,
        )
        self.lineage_repo.link(
            child_entity_type=LineageEntityType.STOCK_SETUP_RESEARCH.value,
            child_entity_id=row.id,
            parent_entity_type=LineageEntityType.RANKING_RESULT.value,
            parent_entity_id=result.id,
            relationship_type=LineageRelationshipType.RANK_RESULT_STOCK_SETUP.value,
        )
        return self.to_payload(row)

    def get_packet_evidence(self, *, ranking_run_id: UUID, stock_id: UUID) -> dict:
        row = self.research_repo.get_for_run_stock(ranking_run_id=ranking_run_id, stock_id=stock_id)
        if row is None:
            run = self.db.get(RankingRun, ranking_run_id)
            result = self.db.scalar(
                select(RankingResult).where(
                    RankingResult.ranking_run_id == ranking_run_id,
                    RankingResult.stock_id == stock_id,
                )
            )
            stock = self.stock_repo.get_by_id(stock_id)
            if run is not None and result is not None and stock is not None:
                payload = self.run_for_candidate(run, result, stock)
                self.db.flush()
                return payload
        if row is None:
            return {"status": "missing"}
        return self.to_payload(row)

    def to_payload(self, row) -> dict:
        metrics = sorted(row.metrics, key=lambda m: m.regime_label)

        def _metric_dict(m) -> dict:
            return {
                "regime_label": m.regime_label,
                "sample_size": m.occurrence_count,
                "similar_setups": m.occurrence_count,
                "win_rate_5d": float(m.win_rate_5d) if m.win_rate_5d is not None else None,
                "win_rate_20d": float(m.win_rate_20d) if m.win_rate_20d is not None else None,
                "average_return_5d": float(m.avg_return_5d)
                if m.avg_return_5d is not None
                else None,
                "average_return_20d": float(m.avg_return_20d)
                if m.avg_return_20d is not None
                else None,
                "avg_return_5d": float(m.avg_return_5d) if m.avg_return_5d is not None else None,
                "avg_return_20d": float(m.avg_return_20d) if m.avg_return_20d is not None else None,
                "median_return_20d": (
                    float(m.median_return_20d) if m.median_return_20d is not None else None
                ),
                "standard_deviation_20d": (
                    float(m.standard_deviation_20d)
                    if m.standard_deviation_20d is not None
                    else None
                ),
                "max_return_20d": float(m.max_return_20d) if m.max_return_20d is not None else None,
                "min_return_20d": float(m.min_return_20d) if m.min_return_20d is not None else None,
                "confidence_interval_95_lower_20d": (
                    float(m.confidence_interval_95_lower_20d)
                    if m.confidence_interval_95_lower_20d is not None
                    else None
                ),
                "confidence_interval_95_upper_20d": (
                    float(m.confidence_interval_95_upper_20d)
                    if m.confidence_interval_95_upper_20d is not None
                    else None
                ),
                "avg_max_drawdown": (
                    float(m.avg_max_drawdown) if m.avg_max_drawdown is not None else None
                ),
                "avg_max_runup": float(m.avg_max_runup) if m.avg_max_runup is not None else None,
                "avg_similarity_score": (
                    float(m.avg_similarity_score) if m.avg_similarity_score is not None else None
                ),
            }

        return {
            "status": row.status,
            "engine_version": row.engine_version,
            "research_id": str(row.id),
            "symbol": row.symbol,
            "strategy_name": row.strategy_name,
            "as_of_date": row.as_of_date.isoformat(),
            "reference_profile": row.reference_profile,
            "match_count": row.match_count,
            "total_matches": row.total_matches,
            "qualifying_matches": row.qualifying_matches,
            "setup_evidence_score": (
                float(row.setup_evidence_score) if row.setup_evidence_score is not None else None
            ),
            "nearest_n": row.nearest_n,
            "min_similarity": float(row.min_similarity),
            "research_hash": row.research_hash,
            "regime_statistics": [_metric_dict(m) for m in metrics],
            "top_similar_setups": (row.similar_setups or [])[:10],
        }

    def _load_regime_by_date(self, benchmark_symbol: str, dates: list[date]) -> dict[date, str]:
        if not dates:
            return {}
        rows = self.db.scalars(
            select(RegimeHistory).where(
                RegimeHistory.benchmark_symbol == benchmark_symbol,
                RegimeHistory.as_of_date.in_(dates),
            )
        ).all()
        return {row.as_of_date: row.regime_label for row in rows}

    def _resolve_benchmark_stock_id(self, benchmark_symbol: str) -> UUID | None:
        stock = self.stock_repo.get_by_symbol(benchmark_symbol)
        return stock.id if stock else None

    def _persist_insufficient(
        self,
        ranking_run: RankingRun,
        result: RankingResult,
        stock: Stock,
        reference: dict,
        strategy_name: str,
        nearest_n: int,
        min_similarity: float,
        *,
        reason: str,
    ) -> dict:
        row = self.research_repo.replace_for_run_stock(
            ranking_run_id=ranking_run.id,
            ranking_result_id=result.id,
            stock_id=stock.id,
            symbol=stock.symbol,
            as_of_date=ranking_run.as_of_date,
            strategy_name=strategy_name,
            engine_version=SEE_ENGINE_VERSION,
            status=STOCK_SETUP_STATUS_INSUFFICIENT_DATA,
            reference_profile=reference,
            similar_setups=[],
            nearest_n=nearest_n,
            min_similarity=min_similarity,
            match_count=0,
            total_matches=0,
            qualifying_matches=0,
            setup_evidence_score=0.0,
            parameter_set={"reason": reason, "engine_version": SEE_ENGINE_VERSION},
            research_hash=None,
            metrics=[metrics_to_dict(aggregate_outcomes([], label)) for label in REGIME_LABELS_V2],
            error_message=reason,
        )
        return self.to_payload(row)

    def _persist_failure(
        self,
        run: RankingRun,
        result: RankingResult,
        stock: Stock,
        message: str,
        nearest_n: int,
        min_similarity: float,
    ) -> None:
        self.research_repo.replace_for_run_stock(
            ranking_run_id=run.id,
            ranking_result_id=result.id,
            stock_id=stock.id,
            symbol=stock.symbol,
            as_of_date=run.as_of_date,
            strategy_name=run.strategy_name,
            engine_version=SEE_ENGINE_VERSION,
            status=STOCK_SETUP_STATUS_FAILED,
            reference_profile={},
            similar_setups=[],
            nearest_n=nearest_n,
            min_similarity=min_similarity,
            match_count=0,
            total_matches=0,
            qualifying_matches=0,
            setup_evidence_score=0.0,
            parameter_set={},
            research_hash=None,
            metrics=[],
            error_message=message,
        )
