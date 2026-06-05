from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.repositories.factor_performance_metric_repository import (
    FactorPerformanceMetricRepository,
)
from app.db.repositories.factor_performance_run_repository import FactorPerformanceRunRepository
from app.db.repositories.full_universe_validation_repository import (
    FullUniverseValidationRepository,
)
from app.db.repositories.ingestion_batch_repository import IngestionBatchRepository
from app.db.repositories.ingestion_run_repository import IngestionRunRepository
from app.db.repositories.experiment_run_repository import ExperimentRunRepository
from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.ranking_factor_contribution_repository import (
    RankingFactorContributionRepository,
)
from app.db.repositories.ranking_performance_repository import RankingPerformanceRepository
from app.db.repositories.ranking_result_repository import RankingResultRepository
from app.db.repositories.ranking_run_repository import RankingRunRepository
from app.db.repositories.ranking_validation_repository import RankingValidationRepository
from app.db.repositories.regime_analytics_repository import RegimeAnalyticsRepository
from app.db.repositories.regime_backtest_run_repository import RegimeBacktestRunRepository
from app.db.repositories.regime_policy_config_repository import RegimePolicyConfigRepository
from app.db.repositories.regime_policy_decision_repository import RegimePolicyDecisionRepository
from app.db.repositories.run_lineage_repository import RunLineageRepository
from app.db.repositories.stock_repository import StockRepository
from app.db.repositories.stock_setup_research_repository import StockSetupResearchRepository
from app.db.repositories.universe_repository import UniverseRepository
from app.db.repositories.validation_metrics_repository import ValidationMetricsRepository
from app.db.session import get_db as _get_db
from app.market_data.cache import MarketDataCache
from app.providers.yahoo.client import YahooFinanceProvider
from app.ranking.loader import MarketDataLoader
from app.ranking.registry import RankingStrategyRegistry
from app.services.backtest_service import BacktestService
from app.services.experiment_service import ExperimentService
from app.db.repositories.daily_batch_artifact_repository import DailyBatchArtifactRepository
from app.db.repositories.daily_batch_run_repository import DailyBatchRunRepository
from app.db.repositories.exit_research_metric_repository import ExitResearchMetricRepository
from app.db.repositories.exit_research_run_repository import ExitResearchRunRepository
from app.db.repositories.research_intelligence_repository import (
    ResearchIntelligenceReportRepository,
    ResearchIntelligenceRunRepository,
)
from app.services.daily_batch_service import DailyBatchService
from app.services.exit_research_service import ExitResearchService
from app.services.factor_predictive_power_service import FactorPredictivePowerService
from app.services.research_intelligence_service import ResearchIntelligenceService
from app.services.full_universe_validation_service import FullUniverseValidationService
from app.services.market_data_service import MarketDataService
from app.services.observability_service import ObservabilityService
from app.services.ranking_service import RankingService
from app.services.regime_analytics_service import RegimeAnalyticsService
from app.services.regime_policy_service import RegimePolicyPresetService, RegimePolicyService
from app.services.signal_validation_service import SignalValidationService
from app.services.stock_service import StockService
from app.db.repositories.recommendation_repository import RecommendationRepository
from app.services.recommendation_service import RecommendationService
from app.services.traceability_service import TraceabilityService
from app.db.repositories.research_run_repository import ResearchRunRepository
from app.db.repositories.investment_review_packet_repository import (
    InvestmentReviewPacketRepository,
)
from app.db.repositories.committee_review_repository import CommitteeReviewRepository
from app.db.repositories.cro_review_repository import CroReviewRepository
from app.db.repositories.governance_research_report_repository import (
    GovernanceResearchReportRepository,
)
from app.db.repositories.args_prompt_version_repository import ArgsPromptVersionRepository
from app.args.llm.registry import CommitteeLlmRegistry
from app.db.repositories.llm_execution_record_repository import LlmExecutionRecordRepository
from app.services.args_research_run_service import ArgsResearchRunService
from app.services.args_explainability_service import ArgsExplainabilityService
from app.services.stock_setup_research_service import StockSetupResearchService
from app.services.universe_filter_service import UniverseFilterService


def get_settings_dep() -> Settings:
    return get_settings()


def get_db() -> Generator[Session, None, None]:
    yield from _get_db()


def get_stock_repository(db: Session = Depends(get_db)) -> StockRepository:
    return StockRepository(db)


def get_market_data_repository(db: Session = Depends(get_db)) -> MarketDataRepository:
    return MarketDataRepository(db)


def get_ingestion_run_repository(db: Session = Depends(get_db)) -> IngestionRunRepository:
    return IngestionRunRepository(db)


def get_ingestion_batch_repository(db: Session = Depends(get_db)) -> IngestionBatchRepository:
    return IngestionBatchRepository(db)


def get_run_lineage_repository(db: Session = Depends(get_db)) -> RunLineageRepository:
    return RunLineageRepository(db)


def get_ranking_factor_contribution_repository(
    db: Session = Depends(get_db),
) -> RankingFactorContributionRepository:
    return RankingFactorContributionRepository(db)


def get_validation_metrics_repository(
    db: Session = Depends(get_db),
) -> ValidationMetricsRepository:
    return ValidationMetricsRepository(db)


def get_experiment_run_repository(db: Session = Depends(get_db)) -> ExperimentRunRepository:
    return ExperimentRunRepository(db)


def get_regime_analytics_repository(db: Session = Depends(get_db)) -> RegimeAnalyticsRepository:
    return RegimeAnalyticsRepository(db)


def get_universe_repository(db: Session = Depends(get_db)) -> UniverseRepository:
    return UniverseRepository(db)


def get_yahoo_provider(settings: Settings = Depends(get_settings_dep)) -> YahooFinanceProvider:
    return YahooFinanceProvider(timeout_seconds=settings.yahoo_request_timeout_seconds)


def get_stock_service(stock_repo: StockRepository = Depends(get_stock_repository)) -> StockService:
    return StockService(stock_repo)


def get_market_data_service(
    db: Session = Depends(get_db),
    stock_repo: StockRepository = Depends(get_stock_repository),
    market_data_repo: MarketDataRepository = Depends(get_market_data_repository),
    ingestion_run_repo: IngestionRunRepository = Depends(get_ingestion_run_repository),
    ingestion_batch_repo: IngestionBatchRepository = Depends(get_ingestion_batch_repository),
    lineage_repo: RunLineageRepository = Depends(get_run_lineage_repository),
    provider: YahooFinanceProvider = Depends(get_yahoo_provider),
) -> MarketDataService:
    return MarketDataService(
        db,
        stock_repo,
        market_data_repo,
        ingestion_run_repo,
        ingestion_batch_repo,
        lineage_repo,
        provider,
    )


def get_universe_filter_service(
    universe_repo: UniverseRepository = Depends(get_universe_repository),
    market_data_repo: MarketDataRepository = Depends(get_market_data_repository),
) -> UniverseFilterService:
    return UniverseFilterService(universe_repo, market_data_repo)


def get_ranking_strategy_registry() -> RankingStrategyRegistry:
    return RankingStrategyRegistry()


def get_ranking_run_repository(db: Session = Depends(get_db)) -> RankingRunRepository:
    return RankingRunRepository(db)


def get_ranking_result_repository(db: Session = Depends(get_db)) -> RankingResultRepository:
    return RankingResultRepository(db)


def get_ranking_performance_repository(
    db: Session = Depends(get_db),
) -> RankingPerformanceRepository:
    return RankingPerformanceRepository(db)


def get_traceability_service(
    db: Session = Depends(get_db),
    factor_contribution_repo: RankingFactorContributionRepository = Depends(
        get_ranking_factor_contribution_repository
    ),
    validation_metrics_repo: ValidationMetricsRepository = Depends(get_validation_metrics_repository),
    lineage_repo: RunLineageRepository = Depends(get_run_lineage_repository),
    ingestion_run_repo: IngestionRunRepository = Depends(get_ingestion_run_repository),
) -> TraceabilityService:
    return TraceabilityService(
        db,
        factor_contribution_repo,
        validation_metrics_repo,
        lineage_repo,
        ingestion_run_repo,
    )


def get_ranking_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    universe_filter_service: UniverseFilterService = Depends(get_universe_filter_service),
    ranking_run_repo: RankingRunRepository = Depends(get_ranking_run_repository),
    ranking_result_repo: RankingResultRepository = Depends(get_ranking_result_repository),
    ranking_performance_repo: RankingPerformanceRepository = Depends(
        get_ranking_performance_repository
    ),
    stock_repo: StockRepository = Depends(get_stock_repository),
    universe_repo: UniverseRepository = Depends(get_universe_repository),
    strategy_registry: RankingStrategyRegistry = Depends(get_ranking_strategy_registry),
    traceability_service: TraceabilityService = Depends(get_traceability_service),
) -> RankingService:
    return RankingService(
        db,
        settings,
        universe_filter_service,
        ranking_run_repo,
        ranking_result_repo,
        ranking_performance_repo,
        stock_repo,
        universe_repo,
        strategy_registry,
        traceability_service,
    )


def get_ranking_validation_repository(
    db: Session = Depends(get_db),
) -> RankingValidationRepository:
    return RankingValidationRepository(db)


def get_signal_validation_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    ranking_run_repo: RankingRunRepository = Depends(get_ranking_run_repository),
    ranking_result_repo: RankingResultRepository = Depends(get_ranking_result_repository),
    ranking_performance_repo: RankingPerformanceRepository = Depends(
        get_ranking_performance_repository
    ),
    validation_repo: RankingValidationRepository = Depends(get_ranking_validation_repository),
    stock_repo: StockRepository = Depends(get_stock_repository),
    market_data_repo: MarketDataRepository = Depends(get_market_data_repository),
    traceability_service: TraceabilityService = Depends(get_traceability_service),
) -> SignalValidationService:
    return SignalValidationService(
        db,
        settings,
        ranking_run_repo,
        ranking_result_repo,
        ranking_performance_repo,
        validation_repo,
        stock_repo,
        market_data_repo,
        traceability_service,
    )


def get_observability_service(
    db: Session = Depends(get_db),
    ingestion_batch_repo: IngestionBatchRepository = Depends(get_ingestion_batch_repository),
    ranking_run_repo: RankingRunRepository = Depends(get_ranking_run_repository),
    experiment_run_repo: ExperimentRunRepository = Depends(get_experiment_run_repository),
    lineage_repo: RunLineageRepository = Depends(get_run_lineage_repository),
) -> ObservabilityService:
    return ObservabilityService(
        db,
        ingestion_batch_repo,
        ranking_run_repo,
        experiment_run_repo,
        lineage_repo,
    )


def get_experiment_service(
    db: Session = Depends(get_db),
    experiment_run_repo: ExperimentRunRepository = Depends(get_experiment_run_repository),
) -> ExperimentService:
    return ExperimentService(db, experiment_run_repo)


def get_regime_policy_config_repository(
    db: Session = Depends(get_db),
) -> RegimePolicyConfigRepository:
    return RegimePolicyConfigRepository(db)


def get_regime_policy_decision_repository(
    db: Session = Depends(get_db),
) -> RegimePolicyDecisionRepository:
    return RegimePolicyDecisionRepository(db)


def get_regime_backtest_run_repository(
    db: Session = Depends(get_db),
) -> RegimeBacktestRunRepository:
    return RegimeBacktestRunRepository(db)


def get_regime_policy_service(
    db: Session = Depends(get_db),
    config_repo: RegimePolicyConfigRepository = Depends(get_regime_policy_config_repository),
    decision_repo: RegimePolicyDecisionRepository = Depends(get_regime_policy_decision_repository),
    backtest_repo: RegimeBacktestRunRepository = Depends(get_regime_backtest_run_repository),
    validation_repo: RankingValidationRepository = Depends(get_ranking_validation_repository),
    validation_metrics_repo: ValidationMetricsRepository = Depends(get_validation_metrics_repository),
    ranking_run_repo: RankingRunRepository = Depends(get_ranking_run_repository),
    lineage_repo: RunLineageRepository = Depends(get_run_lineage_repository),
    experiment_service: ExperimentService = Depends(get_experiment_service),
) -> RegimePolicyService:
    preset_service = RegimePolicyPresetService(config_repo)
    return RegimePolicyService(
        db,
        config_repo,
        decision_repo,
        backtest_repo,
        validation_repo,
        validation_metrics_repo,
        ranking_run_repo,
        lineage_repo,
        experiment_service,
        preset_service,
    )


def get_factor_performance_metric_repository(
    db: Session = Depends(get_db),
) -> FactorPerformanceMetricRepository:
    return FactorPerformanceMetricRepository(db)


def get_factor_performance_run_repository(
    db: Session = Depends(get_db),
) -> FactorPerformanceRunRepository:
    return FactorPerformanceRunRepository(db)


def get_factor_predictive_power_service(
    db: Session = Depends(get_db),
    metric_repo: FactorPerformanceMetricRepository = Depends(get_factor_performance_metric_repository),
    run_repo: FactorPerformanceRunRepository = Depends(get_factor_performance_run_repository),
    validation_repo: RankingValidationRepository = Depends(get_ranking_validation_repository),
    ranking_run_repo: RankingRunRepository = Depends(get_ranking_run_repository),
) -> FactorPredictivePowerService:
    return FactorPredictivePowerService(
        db,
        metric_repo,
        run_repo,
        validation_repo,
        ranking_run_repo,
    )


def get_exit_research_run_repository(
    db: Session = Depends(get_db),
) -> ExitResearchRunRepository:
    return ExitResearchRunRepository(db)


def get_exit_research_metric_repository(
    db: Session = Depends(get_db),
) -> ExitResearchMetricRepository:
    return ExitResearchMetricRepository(db)


def get_exit_research_service(
    db: Session = Depends(get_db),
    run_repo: ExitResearchRunRepository = Depends(get_exit_research_run_repository),
    metric_repo: ExitResearchMetricRepository = Depends(get_exit_research_metric_repository),
) -> ExitResearchService:
    return ExitResearchService(db, run_repo, metric_repo)


def get_research_intelligence_run_repository(
    db: Session = Depends(get_db),
) -> ResearchIntelligenceRunRepository:
    return ResearchIntelligenceRunRepository(db)


def get_research_intelligence_report_repository(
    db: Session = Depends(get_db),
) -> ResearchIntelligenceReportRepository:
    return ResearchIntelligenceReportRepository(db)


def get_research_intelligence_service(
    db: Session = Depends(get_db),
    run_repo: ResearchIntelligenceRunRepository = Depends(get_research_intelligence_run_repository),
    report_repo: ResearchIntelligenceReportRepository = Depends(
        get_research_intelligence_report_repository
    ),
    validation_service: SignalValidationService = Depends(get_signal_validation_service),
    factor_metric_repo: FactorPerformanceMetricRepository = Depends(
        get_factor_performance_metric_repository
    ),
) -> ResearchIntelligenceService:
    return ResearchIntelligenceService(
        db, run_repo, report_repo, validation_service, factor_metric_repo
    )


def get_regime_analytics_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    regime_repo: RegimeAnalyticsRepository = Depends(get_regime_analytics_repository),
    stock_repo: StockRepository = Depends(get_stock_repository),
    market_data_repo: MarketDataRepository = Depends(get_market_data_repository),
) -> RegimeAnalyticsService:
    return RegimeAnalyticsService(db, settings, regime_repo, stock_repo, market_data_repo)


def get_backtest_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    ranking_service: RankingService = Depends(get_ranking_service),
    universe_repo: UniverseRepository = Depends(get_universe_repository),
    stock_repo: StockRepository = Depends(get_stock_repository),
    market_data_repo: MarketDataRepository = Depends(get_market_data_repository),
) -> BacktestService:
    return BacktestService(
        db,
        settings,
        ranking_service,
        universe_repo,
        stock_repo,
        market_data_repo,
    )


def get_full_universe_validation_repository(
    db: Session = Depends(get_db),
) -> FullUniverseValidationRepository:
    return FullUniverseValidationRepository(db)


def get_daily_batch_run_repository(db: Session = Depends(get_db)) -> DailyBatchRunRepository:
    return DailyBatchRunRepository(db)


def get_daily_batch_artifact_repository(
    db: Session = Depends(get_db),
) -> DailyBatchArtifactRepository:
    return DailyBatchArtifactRepository(db)


def get_stock_setup_research_repository(
    db: Session = Depends(get_db),
) -> StockSetupResearchRepository:
    return StockSetupResearchRepository(db)


def get_stock_setup_research_service(
    db: Session = Depends(get_db),
    research_repo: StockSetupResearchRepository = Depends(get_stock_setup_research_repository),
    stock_repo: StockRepository = Depends(get_stock_repository),
    lineage_repo: RunLineageRepository = Depends(get_run_lineage_repository),
) -> StockSetupResearchService:
    cache = MarketDataCache(MarketDataRepository(db))
    loader = MarketDataLoader(cache)
    return StockSetupResearchService(
        db,
        research_repo=research_repo,
        stock_repo=stock_repo,
        lineage_repo=lineage_repo,
        market_data_loader=loader,
    )


def get_daily_batch_service(
    db: Session = Depends(get_db),
    market_data_service: MarketDataService = Depends(get_market_data_service),
    backtest_service: BacktestService = Depends(get_backtest_service),
    validation_service: SignalValidationService = Depends(get_signal_validation_service),
    factor_service: FactorPredictivePowerService = Depends(get_factor_predictive_power_service),
    exit_service: ExitResearchService = Depends(get_exit_research_service),
    regime_service: RegimeAnalyticsService = Depends(get_regime_analytics_service),
    research_intelligence_service: ResearchIntelligenceService = Depends(
        get_research_intelligence_service
    ),
    ranking_run_repo: RankingRunRepository = Depends(get_ranking_run_repository),
    run_repo: DailyBatchRunRepository = Depends(get_daily_batch_run_repository),
    artifact_repo: DailyBatchArtifactRepository = Depends(get_daily_batch_artifact_repository),
) -> DailyBatchService:
    return DailyBatchService(
        db,
        market_data_service=market_data_service,
        backtest_service=backtest_service,
        validation_service=validation_service,
        factor_service=factor_service,
        exit_service=exit_service,
        regime_service=regime_service,
        research_intelligence_service=research_intelligence_service,
        ranking_run_repo=ranking_run_repo,
        run_repo=run_repo,
        artifact_repo=artifact_repo,
    )


def get_full_universe_validation_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    campaign_repo: FullUniverseValidationRepository = Depends(
        get_full_universe_validation_repository
    ),
    ranking_run_repo: RankingRunRepository = Depends(get_ranking_run_repository),
    backtest_service: BacktestService = Depends(get_backtest_service),
    signal_validation_service: SignalValidationService = Depends(get_signal_validation_service),
) -> FullUniverseValidationService:
    return FullUniverseValidationService(
        db,
        settings,
        campaign_repo,
        ranking_run_repo,
        backtest_service,
        signal_validation_service,
    )


def get_research_run_repository(db: Session = Depends(get_db)) -> ResearchRunRepository:
    return ResearchRunRepository(db)


def get_investment_review_packet_repository(
    db: Session = Depends(get_db),
) -> InvestmentReviewPacketRepository:
    return InvestmentReviewPacketRepository(db)


def get_committee_review_repository(db: Session = Depends(get_db)) -> CommitteeReviewRepository:
    return CommitteeReviewRepository(db)


def get_cro_review_repository(db: Session = Depends(get_db)) -> CroReviewRepository:
    return CroReviewRepository(db)


def get_governance_research_report_repository(
    db: Session = Depends(get_db),
) -> GovernanceResearchReportRepository:
    return GovernanceResearchReportRepository(db)


def get_args_prompt_version_repository(db: Session = Depends(get_db)) -> ArgsPromptVersionRepository:
    return ArgsPromptVersionRepository(db)


def get_llm_execution_record_repository(
    db: Session = Depends(get_db),
) -> LlmExecutionRecordRepository:
    return LlmExecutionRecordRepository(db)


def get_committee_llm_registry(
    settings: Settings = Depends(get_settings_dep),
) -> CommitteeLlmRegistry:
    return CommitteeLlmRegistry.from_settings(settings)


def get_args_research_run_service(
    db: Session = Depends(get_db),
    research_run_repo: ResearchRunRepository = Depends(get_research_run_repository),
    packet_repo: InvestmentReviewPacketRepository = Depends(
        get_investment_review_packet_repository
    ),
    committee_review_repo: CommitteeReviewRepository = Depends(get_committee_review_repository),
    cro_review_repo: CroReviewRepository = Depends(get_cro_review_repository),
    governance_report_repo: GovernanceResearchReportRepository = Depends(
        get_governance_research_report_repository
    ),
    lineage_repo: RunLineageRepository = Depends(get_run_lineage_repository),
    prompt_repo: ArgsPromptVersionRepository = Depends(get_args_prompt_version_repository),
    llm_record_repo: LlmExecutionRecordRepository = Depends(get_llm_execution_record_repository),
    ranking_run_repo: RankingRunRepository = Depends(get_ranking_run_repository),
    ranking_result_repo: RankingResultRepository = Depends(get_ranking_result_repository),
    validation_repo: RankingValidationRepository = Depends(get_ranking_validation_repository),
    stock_repo: StockRepository = Depends(get_stock_repository),
    stock_setup_service: StockSetupResearchService = Depends(get_stock_setup_research_service),
    llm_registry: CommitteeLlmRegistry = Depends(get_committee_llm_registry),
) -> ArgsResearchRunService:
    return ArgsResearchRunService(
        db,
        research_run_repo=research_run_repo,
        packet_repo=packet_repo,
        committee_review_repo=committee_review_repo,
        cro_review_repo=cro_review_repo,
        governance_report_repo=governance_report_repo,
        lineage_repo=lineage_repo,
        prompt_repo=prompt_repo,
        llm_record_repo=llm_record_repo,
        ranking_run_repo=ranking_run_repo,
        ranking_result_repo=ranking_result_repo,
        validation_repo=validation_repo,
        stock_repo=stock_repo,
        stock_setup_service=stock_setup_service,
        llm_registry=llm_registry,
    )


def get_recommendation_repository(db: Session = Depends(get_db)) -> RecommendationRepository:
    return RecommendationRepository(db)


def get_recommendation_service(
    db: Session = Depends(get_db),
) -> RecommendationService:
    return RecommendationService(db)


def get_args_explainability_service(
    research_run_repo: ResearchRunRepository = Depends(get_research_run_repository),
    packet_repo: InvestmentReviewPacketRepository = Depends(
        get_investment_review_packet_repository
    ),
    committee_review_repo: CommitteeReviewRepository = Depends(get_committee_review_repository),
    cro_review_repo: CroReviewRepository = Depends(get_cro_review_repository),
    governance_report_repo: GovernanceResearchReportRepository = Depends(
        get_governance_research_report_repository
    ),
    lineage_repo: RunLineageRepository = Depends(get_run_lineage_repository),
) -> ArgsExplainabilityService:
    return ArgsExplainabilityService(
        research_run_repo,
        packet_repo,
        committee_review_repo,
        cro_review_repo,
        governance_report_repo,
        lineage_repo,
    )
