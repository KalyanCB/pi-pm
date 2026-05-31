"""Sprint 7: platform traceability, observability, and experiment framework."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260530_0007"
down_revision: str | None = "20260530_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ingestion_batch_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("period", sa.String(length=8), nullable=False),
        sa.Column("ingestion_mode", sa.String(length=16), nullable=False),
        sa.Column("symbol_count_requested", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("symbol_count_succeeded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("symbol_count_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_inserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("execution_duration_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ingestion_batch_runs_started_at",
        "ingestion_batch_runs",
        ["started_at"],
        unique=False,
    )

    op.add_column(
        "market_data_ingestion_runs",
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "market_data_ingestion_runs",
        sa.Column("ingestion_mode", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "market_data_ingestion_runs",
        sa.Column("first_date_loaded", sa.Date(), nullable=True),
    )
    op.add_column(
        "market_data_ingestion_runs",
        sa.Column("last_date_loaded", sa.Date(), nullable=True),
    )
    op.create_foreign_key(
        "fk_market_data_ingestion_runs_batch_id",
        "market_data_ingestion_runs",
        "ingestion_batch_runs",
        ["batch_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_market_data_ingestion_runs_batch_id",
        "market_data_ingestion_runs",
        ["batch_id"],
        unique=False,
    )

    op.add_column("ranking_runs", sa.Column("regime_label", sa.String(length=32), nullable=True))
    op.add_column("ranking_runs", sa.Column("weight_config_hash", sa.String(length=64), nullable=True))
    op.add_column("ranking_runs", sa.Column("ranked_stock_count", sa.Integer(), nullable=True))
    op.add_column("ranking_runs", sa.Column("excluded_stock_count", sa.Integer(), nullable=True))
    op.add_column("ranking_runs", sa.Column("execution_duration_ms", sa.Integer(), nullable=True))

    op.create_table(
        "ranking_factor_contributions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ranking_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stock_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("factor_name", sa.String(length=64), nullable=False),
        sa.Column("raw_factor_value", sa.Numeric(18, 8), nullable=True),
        sa.Column("normalized_factor_value", sa.Numeric(18, 8), nullable=True),
        sa.Column("weighted_factor_value", sa.Numeric(18, 8), nullable=True),
        sa.ForeignKeyConstraint(["ranking_run_id"], ["ranking_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ranking_run_id",
            "stock_id",
            "factor_name",
            name="uq_ranking_factor_contributions_run_stock_factor",
        ),
    )
    op.create_index(
        "ix_ranking_factor_contributions_run",
        "ranking_factor_contributions",
        ["ranking_run_id"],
        unique=False,
    )

    op.create_table(
        "validation_horizon_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("validation_report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ranking_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_name", sa.String(length=64), nullable=False),
        sa.Column("strategy_version", sa.String(length=32), nullable=False),
        sa.Column("regime_label", sa.String(length=32), nullable=True),
        sa.Column("horizon", sa.Integer(), nullable=False),
        sa.Column("ic_pearson", sa.Numeric(18, 8), nullable=True),
        sa.Column("rank_ic_spearman", sa.Numeric(18, 8), nullable=True),
        sa.Column("hit_rate", sa.Numeric(18, 8), nullable=True),
        sa.Column("directional_hit_rate", sa.Numeric(18, 8), nullable=True),
        sa.Column("spread", sa.Numeric(18, 8), nullable=True),
        sa.Column("top_decile_return", sa.Numeric(18, 8), nullable=True),
        sa.Column("bottom_decile_return", sa.Numeric(18, 8), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["validation_report_id"], ["ranking_validation_reports.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["ranking_run_id"], ["ranking_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "validation_report_id",
            "horizon",
            name="uq_validation_horizon_metrics_report_horizon",
        ),
    )

    op.create_table(
        "validation_decile_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("validation_report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("horizon", sa.Integer(), nullable=False),
        sa.Column("decile", sa.Integer(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_return", sa.Numeric(18, 8), nullable=True),
        sa.Column("median_return", sa.Numeric(18, 8), nullable=True),
        sa.Column("win_rate", sa.Numeric(18, 8), nullable=True),
        sa.ForeignKeyConstraint(
            ["validation_report_id"], ["ranking_validation_reports.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "validation_report_id",
            "horizon",
            "decile",
            name="uq_validation_decile_metrics_report_horizon_decile",
        ),
    )

    op.create_table(
        "run_lineage_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("child_entity_type", sa.String(length=32), nullable=False),
        sa.Column("child_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_entity_type", sa.String(length=32), nullable=False),
        sa.Column("parent_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_type", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "child_entity_type",
            "child_entity_id",
            "parent_entity_type",
            "parent_entity_id",
            "relationship_type",
            name="uq_run_lineage_records_link",
        ),
    )
    op.create_index(
        "ix_run_lineage_records_child",
        "run_lineage_records",
        ["child_entity_type", "child_entity_id"],
        unique=False,
    )

    op.create_table(
        "experiment_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("experiment_name", sa.String(length=128), nullable=False),
        sa.Column("strategy_name", sa.String(length=64), nullable=False),
        sa.Column("strategy_version", sa.String(length=32), nullable=False),
        sa.Column("parameter_set", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_experiment_runs_strategy_started",
        "experiment_runs",
        ["strategy_name", "strategy_version", "started_at"],
        unique=False,
    )

    op.create_table(
        "regime_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("benchmark_symbol", sa.String(length=32), nullable=False),
        sa.Column("trend_regime", sa.String(length=16), nullable=False),
        sa.Column("vol_regime", sa.String(length=16), nullable=False),
        sa.Column("regime_label", sa.String(length=32), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "as_of_date",
            "benchmark_symbol",
            name="uq_regime_history_date_benchmark",
        ),
    )

    op.create_table(
        "strategy_regime_performance",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_name", sa.String(length=64), nullable=False),
        sa.Column("strategy_version", sa.String(length=32), nullable=False),
        sa.Column("regime_label", sa.String(length=32), nullable=False),
        sa.Column("horizon", sa.Integer(), nullable=False),
        sa.Column("avg_ic", sa.Numeric(18, 8), nullable=True),
        sa.Column("avg_spread", sa.Numeric(18, 8), nullable=True),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "strategy_name",
            "strategy_version",
            "regime_label",
            "horizon",
            name="uq_strategy_regime_performance_key",
        ),
    )


def downgrade() -> None:
    op.drop_table("strategy_regime_performance")
    op.drop_table("regime_history")
    op.drop_index("ix_experiment_runs_strategy_started", table_name="experiment_runs")
    op.drop_table("experiment_runs")
    op.drop_index("ix_run_lineage_records_child", table_name="run_lineage_records")
    op.drop_table("run_lineage_records")
    op.drop_table("validation_decile_metrics")
    op.drop_table("validation_horizon_metrics")
    op.drop_index("ix_ranking_factor_contributions_run", table_name="ranking_factor_contributions")
    op.drop_table("ranking_factor_contributions")
    op.drop_column("ranking_runs", "execution_duration_ms")
    op.drop_column("ranking_runs", "excluded_stock_count")
    op.drop_column("ranking_runs", "ranked_stock_count")
    op.drop_column("ranking_runs", "weight_config_hash")
    op.drop_column("ranking_runs", "regime_label")
    op.drop_index("ix_market_data_ingestion_runs_batch_id", table_name="market_data_ingestion_runs")
    op.drop_constraint(
        "fk_market_data_ingestion_runs_batch_id",
        "market_data_ingestion_runs",
        type_="foreignkey",
    )
    op.drop_column("market_data_ingestion_runs", "last_date_loaded")
    op.drop_column("market_data_ingestion_runs", "first_date_loaded")
    op.drop_column("market_data_ingestion_runs", "ingestion_mode")
    op.drop_column("market_data_ingestion_runs", "batch_id")
    op.drop_index("ix_ingestion_batch_runs_started_at", table_name="ingestion_batch_runs")
    op.drop_table("ingestion_batch_runs")
