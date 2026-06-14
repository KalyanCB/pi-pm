"""Per-intent context retriever.

Each function queries the DB for exactly the records relevant to that intent.
Returns structured dicts — never raw SQL results in the LLM prompt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.copilot.intent import CopilotIntent, ExtractedEntities
from app.copilot.lineage import source_ref
from app.models.args import CommitteeReview, CroReview, InvestmentReviewPacket
from app.models.daily_batch import DailyBatchRun
from app.models.exit_research import ExitResearchPolicyMetric, ExitResearchRun
from app.models.factor_analytics import FactorPerformanceMetric
from app.models.market_data import MarketData
from app.models.platform_traceability import StrategyRegimePerformance
from app.models.portfolio_analytics import ExitRecommendation, PortfolioNavHistory
from app.models.portfolio_position import PortfolioConfig, PortfolioPosition
from app.models.ranking_result import RankingResult
from app.models.ranking_run import RankingRun
from app.models.ranking_validation_report import RankingValidationReport
from app.models.recommendation import RecommendationOutcome, RecommendationResult, RecommendationRun
from app.models.regime_policy import RegimePolicyConfig
from app.models.stock import Stock
from app.models.stock_setup_research import StockSetupResearch, StockSetupResearchMetric

_BUY_ACTIONS = frozenset({"BUY", "WATCH"})
_REJECT_ACTIONS = frozenset({"REJECT", "WATCH"})
_RISK_REASON_CODES = frozenset(
    {
        "EXIT_RISK",
        "REGIME_BLOCK",
        "VALIDATION_WEAK",
        "VALIDATION_PENDING",
        "PORTFOLIO_FULL",
        "INSUFFICIENT_LIQUIDITY",
    }
)


@dataclass
class RetrievalContext:
    intent: CopilotIntent
    sources: list[dict[str, Any]] = field(default_factory=list)
    source_refs: list[dict[str, str]] = field(default_factory=list)


def retrieve(
    db: Session,
    intent: CopilotIntent,
    entities: ExtractedEntities,
) -> RetrievalContext:
    ctx = RetrievalContext(intent=intent)

    dispatch: dict[CopilotIntent, Any] = {
        CopilotIntent.WHY_RECOMMENDED: _retrieve_why_recommended,
        CopilotIntent.WHY_NOT_RECOMMENDED: _retrieve_why_not_recommended,
        CopilotIntent.EXPLAIN_EXIT: _retrieve_exit,
        CopilotIntent.EXPLAIN_CONVICTION: _retrieve_conviction,
        CopilotIntent.EXPLAIN_COMMITTEE: _retrieve_committee,
        CopilotIntent.EXPLAIN_PORTFOLIO: _retrieve_portfolio,
        CopilotIntent.EXPLAIN_RISK: _retrieve_risk,
        CopilotIntent.EXPLAIN_PERFORMANCE: _retrieve_performance,
        CopilotIntent.EXPLAIN_RANK: _retrieve_rank,
        CopilotIntent.EXPLAIN_VALIDATION: _retrieve_validation,
        CopilotIntent.OPS_STATUS: _retrieve_ops,
        CopilotIntent.EXPLAIN_STOCK: _retrieve_stock,
        CopilotIntent.EXPLAIN_MARKET_DATA: _retrieve_market_data,
        CopilotIntent.EXPLAIN_FACTOR_IC: _retrieve_factor_ic,
        CopilotIntent.EXPLAIN_RCEE: _retrieve_rcee,
        CopilotIntent.EXPLAIN_REGIME: _retrieve_regime,
        CopilotIntent.EXPLAIN_POSITIONS: _retrieve_positions,
        CopilotIntent.EXPLAIN_EXIT_STRATEGY: _retrieve_exit_strategy,
    }
    handler = dispatch.get(intent)
    if handler:
        handler(db, entities, ctx)

    return ctx


# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_stock(db: Session, symbol: str | None) -> Stock | None:
    if not symbol:
        return None
    clean = symbol.upper().replace(".NS", "")
    return db.scalar(select(Stock).where(Stock.symbol.in_([symbol.upper(), f"{clean}.NS", clean])))


def _symbol_map(db: Session, stock_ids: list) -> dict[str, str]:
    """Resolve stock_id -> ticker symbol for a set of positions."""
    ids = [sid for sid in stock_ids if sid is not None]
    if not ids:
        return {}
    rows = db.execute(select(Stock.id, Stock.symbol).where(Stock.id.in_(ids))).all()
    return {str(sid): sym for sid, sym in rows}


def _latest_ranking_run(
    db: Session,
    strategy: str | None,
    as_of_date: date | None,
) -> RankingRun | None:
    q = select(RankingRun).where(RankingRun.status == "completed")
    if strategy:
        q = q.where(RankingRun.strategy_name == strategy)
    if as_of_date:
        q = q.where(RankingRun.as_of_date == as_of_date)
    return db.scalar(q.order_by(desc(RankingRun.as_of_date), desc(RankingRun.created_at)).limit(1))


def _latest_recommendation_run(
    db: Session,
    strategy: str | None,
    as_of_date: date | None,
) -> RecommendationRun | None:
    q = select(RecommendationRun).where(RecommendationRun.status == "completed")
    if strategy:
        q = q.where(RecommendationRun.strategy_name == strategy)
    if as_of_date:
        q = q.where(RecommendationRun.as_of_date == as_of_date)
    return db.scalar(
        q.order_by(desc(RecommendationRun.as_of_date), desc(RecommendationRun.created_at)).limit(1)
    )


def _append_recommendation(
    ctx: RetrievalContext,
    rec_run: RecommendationRun,
    result: RecommendationResult,
    stock: Stock | None,
) -> None:
    ctx.source_refs.append(
        source_ref(
            "recommendation_results",
            str(result.id),
            recommendation_run_id=str(rec_run.id),
            recommendation_id=str(result.id),
            portfolio_position_id=str(result.portfolio_position_id)
            if result.portfolio_position_id
            else None,
        )
    )
    ctx.sources.append(
        {
            "recommendation_id": str(result.id),
            "recommendation_run_id": str(rec_run.id),
            "stock_id": str(result.stock_id),
            "symbol": stock.symbol if stock else None,
            "rank": result.rank,
            "composite_score": float(result.composite_score) if result.composite_score else None,
            "action": result.action,
            "lifecycle_state": result.lifecycle_state,
            "conviction_score": result.conviction_score,
            "conviction_band": result.conviction_band,
            "conviction_components": result.conviction_components,
            "reason_codes": result.reason_codes,
            # ADR-034: deterministic trade levels (BUY = actionable, WATCH = indicative)
            "reference_close": float(result.reference_close)
            if result.reference_close is not None
            else None,
            "atr_pct": float(result.atr_pct) if result.atr_pct is not None else None,
            "entry_low": float(result.entry_low) if result.entry_low is not None else None,
            "entry_high": float(result.entry_high) if result.entry_high is not None else None,
            "stop_advisory": float(result.stop_advisory)
            if result.stop_advisory is not None
            else None,
            "stop_critical": float(result.stop_critical)
            if result.stop_critical is not None
            else None,
            "levels_basis": result.levels_basis,
            "portfolio_position_id": str(result.portfolio_position_id)
            if result.portfolio_position_id
            else None,
            "as_of_date": rec_run.as_of_date.isoformat(),
            "strategy_name": rec_run.strategy_name,
        }
    )


# ── Per-intent retrievers ─────────────────────────────────────────────────────


def _retrieve_why_recommended(
    db: Session,
    entities: ExtractedEntities,
    ctx: RetrievalContext,
) -> None:
    stock = _get_stock(db, entities.symbol)
    rec_run = _latest_recommendation_run(db, entities.strategy_name, entities.as_of_date)
    if not rec_run:
        ctx.sources.append({"note": "No completed recommendation runs found."})
        return

    ctx.source_refs.append(
        source_ref("recommendation_runs", str(rec_run.id), recommendation_run_id=str(rec_run.id))
    )

    if stock:
        # Specific stock — return whatever action it received (may be REJECT)
        q = select(RecommendationResult).where(
            RecommendationResult.recommendation_run_id == rec_run.id,
            RecommendationResult.stock_id == stock.id,
        )
    else:
        # No stock — top BUY/WATCH across ALL strategies for the same date
        same_date_runs = db.scalars(
            select(RecommendationRun).where(
                RecommendationRun.status == "completed",
                RecommendationRun.as_of_date == rec_run.as_of_date,
            )
        ).all()
        run_ids = [r.id for r in same_date_runs]
        q = (
            select(RecommendationResult)
            .where(
                RecommendationResult.recommendation_run_id.in_(run_ids),
                RecommendationResult.action.in_(tuple(_BUY_ACTIONS)),
            )
            .order_by(desc(RecommendationResult.conviction_score))
            .limit(10)
        )

    results = db.scalars(q).all()
    if not results:
        ctx.sources.append(
            {
                "recommendation_run_id": str(rec_run.id),
                "note": "No recommendations found for the query scope.",
            }
        )
        return

    if stock:
        for r in results:
            _append_recommendation(ctx, rec_run, r, stock)
    else:
        # Bulk-resolve symbols so the LLM can name the stocks
        sym_map = _symbol_map(db, [r.stock_id for r in results])
        for r in results:
            _append_recommendation(ctx, rec_run, r, None)
            # Patch symbol into the last appended source
            ctx.sources[-1]["symbol"] = sym_map.get(str(r.stock_id))


def _retrieve_why_not_recommended(
    db: Session,
    entities: ExtractedEntities,
    ctx: RetrievalContext,
) -> None:
    stock = _get_stock(db, entities.symbol)
    rec_run = _latest_recommendation_run(db, entities.strategy_name, entities.as_of_date)
    if not rec_run:
        ctx.sources.append({"note": "No completed recommendation runs found."})
        return

    ctx.source_refs.append(
        source_ref("recommendation_runs", str(rec_run.id), recommendation_run_id=str(rec_run.id))
    )

    q = select(RecommendationResult).where(
        RecommendationResult.recommendation_run_id == rec_run.id,
    )
    if stock:
        q = q.where(RecommendationResult.stock_id == stock.id)
    else:
        q = q.where(RecommendationResult.action.in_(tuple(_REJECT_ACTIONS))).limit(10)

    results = db.scalars(q).all()
    if not results:
        ctx.sources.append(
            {
                "recommendation_run_id": str(rec_run.id),
                "note": "No recommendation results found for the query scope.",
            }
        )
        return

    for r in results:
        if (
            stock
            or r.action in _REJECT_ACTIONS
            or any(
                code in r.reason_codes
                for code in (
                    "RANK_OUTSIDE_POOL",
                    "CONVICTION_LOW",
                    "REGIME_BLOCK",
                    "PORTFOLIO_FULL",
                )
            )
        ):
            _append_recommendation(ctx, rec_run, r, stock)


def _retrieve_rank(db: Session, entities: ExtractedEntities, ctx: RetrievalContext) -> None:
    stock = _get_stock(db, entities.symbol)
    run = _latest_ranking_run(db, entities.strategy_name, entities.as_of_date)
    if not run:
        ctx.sources.append({"note": "No completed ranking runs found."})
        return

    ctx.source_refs.append(source_ref("ranking_runs", str(run.id)))
    run_data: dict[str, Any] = {
        "ranking_run_id": str(run.id),
        "strategy_name": run.strategy_name,
        "as_of_date": run.as_of_date.isoformat(),
        "universe_code": run.universe_code,
        "regime_label": run.regime_label,
    }

    if stock:
        result = db.scalar(
            select(RankingResult).where(
                RankingResult.ranking_run_id == run.id,
                RankingResult.stock_id == stock.id,
            )
        )
        if result:
            ctx.source_refs.append(source_ref("ranking_results", str(result.id)))
            run_data["symbol"] = stock.symbol
            run_data["rank"] = result.rank
            run_data["composite_score"] = float(result.score)
            run_data["score_components"] = result.score_components or {}
        else:
            top = db.scalars(
                select(RankingResult)
                .where(RankingResult.ranking_run_id == run.id)
                .order_by(RankingResult.rank)
                .limit(5)
            ).all()
            run_data["top_5"] = [
                {"rank": r.rank, "stock_id": str(r.stock_id), "score": float(r.score)} for r in top
            ]
            run_data["note"] = f"{stock.symbol} was not ranked in this run."
    else:
        top = db.scalars(
            select(RankingResult)
            .where(RankingResult.ranking_run_id == run.id)
            .order_by(RankingResult.rank)
            .limit(10)
        ).all()
        run_data["top_10"] = [
            {"rank": r.rank, "stock_id": str(r.stock_id), "score": float(r.score)} for r in top
        ]

    ctx.sources.append(run_data)


def _retrieve_conviction(db: Session, entities: ExtractedEntities, ctx: RetrievalContext) -> None:
    stock = _get_stock(db, entities.symbol)
    rec_run = _latest_recommendation_run(db, entities.strategy_name, entities.as_of_date)
    if not rec_run:
        ctx.sources.append({"note": "No completed recommendation runs found."})
        return

    ctx.source_refs.append(
        source_ref("recommendation_runs", str(rec_run.id), recommendation_run_id=str(rec_run.id))
    )

    q = select(RecommendationResult).where(RecommendationResult.recommendation_run_id == rec_run.id)
    if stock:
        q = q.where(RecommendationResult.stock_id == stock.id)
    else:
        q = q.order_by(desc(RecommendationResult.conviction_score)).limit(5)

    for r in db.scalars(q).all():
        _append_recommendation(ctx, rec_run, r, stock)


def _retrieve_validation(db: Session, entities: ExtractedEntities, ctx: RetrievalContext) -> None:
    run = _latest_ranking_run(db, entities.strategy_name, entities.as_of_date)
    if not run:
        ctx.sources.append({"note": "No ranking runs found."})
        return

    report = db.scalar(
        select(RankingValidationReport).where(RankingValidationReport.ranking_run_id == run.id)
    )
    if not report:
        ctx.sources.append(
            {
                "ranking_run_id": str(run.id),
                "as_of_date": run.as_of_date.isoformat(),
                "note": "No validation report attached to this ranking run.",
            }
        )
        return

    ctx.source_refs.append(source_ref("ranking_validation_reports", str(report.id)))
    ctx.sources.append(
        {
            "validation_report_id": str(report.id),
            "ranking_run_id": str(run.id),
            "strategy_name": run.strategy_name,
            "as_of_date": run.as_of_date.isoformat(),
            "status": report.status,
            "regime_label": report.regime_label,
            "horizon_metrics": report.horizon_metrics or {},
            "sample_summary": report.sample_summary or {},
        }
    )


def _append_position_exit(
    ctx: RetrievalContext, pos: PortfolioPosition, stock: Stock | None
) -> None:
    """Record an actual position exit (the real SELL): prices, P&L, exit reason."""
    ctx.source_refs.append(
        source_ref("portfolio_positions", str(pos.id), portfolio_position_id=str(pos.id))
    )
    entry = float(pos.entry_price) if pos.entry_price is not None else None
    exit_p = float(pos.exit_price) if pos.exit_price is not None else None
    return_pct = (
        round((exit_p - entry) / entry * 100, 2) if entry and exit_p and entry != 0 else None
    )
    ctx.sources.append(
        {
            "record_type": "position_exit",
            "portfolio_position_id": str(pos.id),
            "symbol": stock.symbol if stock else None,
            "position_status": pos.position_status,
            "entry_date": pos.entry_date.isoformat() if pos.entry_date else None,
            "exit_date": pos.exit_date.isoformat() if pos.exit_date else None,
            "entry_price": entry,
            "exit_price": exit_p,
            "return_pct": return_pct,
            "realized_pnl": float(pos.realized_pnl) if pos.realized_pnl is not None else None,
            "exit_reason": pos.exit_reason,
            "quantity": float(pos.quantity) if pos.quantity is not None else None,
            "conviction_band": pos.conviction_band,
            "strategy_name": pos.strategy_name,
        }
    )


def _retrieve_exit(db: Session, entities: ExtractedEntities, ctx: RetrievalContext) -> None:
    """Trade history for a symbol: recommendations (BUY/WATCH/EXIT) + actual exits.

    Covers an optional [from_date, to_date] window so questions like
    "explain the BUY and SELL recommendations for X between 1-Jun and 10-Jun"
    are answerable from real data — not just engine EXIT_APPROVED rows.
    """
    stock = _get_stock(db, entities.symbol)
    appended = False

    if stock:
        # 1) Recommendation history for the symbol over the date range.
        rq = (
            select(RecommendationResult, RecommendationRun)
            .join(
                RecommendationRun,
                RecommendationResult.recommendation_run_id == RecommendationRun.id,
            )
            .where(RecommendationResult.stock_id == stock.id)
        )
        if entities.from_date:
            rq = rq.where(RecommendationRun.as_of_date >= entities.from_date)
        if entities.to_date:
            rq = rq.where(RecommendationRun.as_of_date <= entities.to_date)
        rq = rq.order_by(RecommendationRun.as_of_date, RecommendationRun.strategy_name).limit(80)
        for result, rec_run in db.execute(rq).all():
            _append_recommendation(ctx, rec_run, result, stock)
            appended = True

        # 2) Actual position exits (real SELLs: STOP_LOSS, FORCE_CLOSE, etc.).
        pq = select(PortfolioPosition).where(
            PortfolioPosition.stock_id == stock.id,
            PortfolioPosition.exit_date.is_not(None),
        )
        if entities.from_date:
            pq = pq.where(PortfolioPosition.exit_date >= entities.from_date)
        if entities.to_date:
            pq = pq.where(PortfolioPosition.exit_date <= entities.to_date)
        pq = pq.order_by(PortfolioPosition.entry_date).limit(40)
        for pos in db.scalars(pq).all():
            _append_position_exit(ctx, pos, stock)
            appended = True

    # 3) Fallback — latest EXIT_APPROVED signals (original behaviour).
    if not appended:
        q = (
            select(RecommendationResult)
            .where(RecommendationResult.action == "EXIT_APPROVED")
            .order_by(desc(RecommendationResult.updated_at))
            .limit(10)
        )
        if stock:
            q = q.where(RecommendationResult.stock_id == stock.id)
        results = db.scalars(q).all()
        if not results:
            ctx.sources.append(
                {"note": "No exit/sell or recommendation history found for this symbol/range."}
            )
            return
        for r in results:
            rec_run = db.get(RecommendationRun, r.recommendation_run_id)
            if rec_run:
                _append_recommendation(ctx, rec_run, r, stock)


def _retrieve_committee(db: Session, entities: ExtractedEntities, ctx: RetrievalContext) -> None:
    stock = _get_stock(db, entities.symbol)

    if stock:
        # Specific stock — fetch its single latest packet (full detail)
        packets = db.scalars(
            select(InvestmentReviewPacket)
            .where(InvestmentReviewPacket.stock_id == stock.id)
            .order_by(desc(InvestmentReviewPacket.built_at))
            .limit(1)
        ).all()
    else:
        # No stock specified — show most recent 5 packets across different stocks
        packets = db.scalars(
            select(InvestmentReviewPacket)
            .order_by(desc(InvestmentReviewPacket.built_at))
            .limit(5)
        ).all()

    if not packets:
        ctx.sources.append({"note": "No ARGS committee packet found in the corpus."})
        return

    # If "high concern" was the query intent but no flagged rows exist, say so
    # and fall through to show the available committee data for context.
    high_concern_total = db.scalar(
        select(CommitteeReview).where(CommitteeReview.high_concern.is_(True)).limit(1)
    )
    if high_concern_total is None:
        ctx.sources.append({
            "note": "No high-concern committee flags found in the corpus. "
                    "All recent committee reviews are shown below for context."
        })

    for packet in packets:
        ctx.source_refs.append(source_ref("investment_review_packets", str(packet.id)))

        reviews = db.scalars(
            select(CommitteeReview)
            .where(CommitteeReview.packet_id == packet.id)
            .order_by(CommitteeReview.committee_code)
        ).all()

        for r in reviews:
            ctx.source_refs.append(
                source_ref(
                    "committee_reviews",
                    str(r.id),
                    committee_review_id=str(r.id),
                    recommendation_run_id=None,
                )
            )
            ctx.sources.append(
                {
                    "committee_review_id": str(r.id),
                    "committee": r.committee_code,
                    "status": r.status,
                    "findings": r.findings,
                    "strengths": r.strengths or [],
                    "risks": r.risks or [],
                    "advisory_action": r.advisory_action,
                    "high_concern": r.high_concern,
                    "high_concern_reason": r.high_concern_reason,
                    "packet_id": str(packet.id),
                    "symbol": packet.symbol,
                }
            )

        cro = db.scalar(select(CroReview).where(CroReview.packet_id == packet.id))
        if cro:
            ctx.source_refs.append(source_ref("cro_reviews", str(cro.id)))
            ctx.sources.append(
                {
                    "cro_review_id": str(cro.id),
                    "rationale": cro.rationale,
                    "investment_committee_summary": cro.investment_committee_summary,
                    "cro_advisory_action": cro.cro_advisory_action,
                    "packet_id": str(packet.id),
                    "symbol": packet.symbol,
                }
            )


def _retrieve_portfolio(db: Session, entities: ExtractedEntities, ctx: RetrievalContext) -> None:
    stock = _get_stock(db, entities.symbol)

    config = db.scalar(select(PortfolioConfig).where(PortfolioConfig.is_active.is_(True)).limit(1))
    if config:
        ctx.source_refs.append(source_ref("portfolio_configs", str(config.id)))
        ctx.sources.append(
            {
                "portfolio_config_id": str(config.id),
                "total_equity": float(config.total_equity),
                "deploy_pct": float(config.deploy_pct),
                "cash_floor_pct": float(config.cash_floor_pct),
                "regime_slots": config.regime_slots,
                "single_name_cap_pct": float(config.single_name_cap_pct),
                "sector_cap_pct": float(config.sector_cap_pct),
            }
        )

    nav = db.scalar(
        select(PortfolioNavHistory).order_by(desc(PortfolioNavHistory.as_of_date)).limit(1)
    )
    if nav:
        ctx.source_refs.append(source_ref("portfolio_nav_history", str(nav.id)))
        ctx.sources.append(
            {
                "nav_id": str(nav.id),
                "as_of_date": nav.as_of_date.isoformat(),
                "total_equity": float(nav.total_equity),
                "cash_balance": float(nav.cash_balance),
                "market_value": float(nav.market_value),
                "open_positions": nav.open_positions,
                "cash_pct": float(nav.cash_pct),
                "day_return_pct": float(nav.day_return_pct) if nav.day_return_pct else None,
                "alpha_pct": float(nav.alpha_pct) if nav.alpha_pct else None,
                "regime_label": nav.regime_label,
            }
        )

    pos_q = select(PortfolioPosition).order_by(desc(PortfolioPosition.as_of))
    if stock:
        pos_q = pos_q.where(PortfolioPosition.stock_id == stock.id)
    else:
        pos_q = pos_q.limit(10)

    positions = db.scalars(pos_q).all()
    pos_symbols = _symbol_map(db, [pos.stock_id for pos in positions])
    for pos in positions:
        ctx.source_refs.append(
            source_ref(
                "portfolio_positions",
                str(pos.id),
                portfolio_position_id=str(pos.id),
                recommendation_id=str(pos.recommendation_result_id)
                if pos.recommendation_result_id
                else None,
            )
        )
        ctx.sources.append(
            {
                "portfolio_position_id": str(pos.id),
                "stock_id": str(pos.stock_id),
                "symbol": pos_symbols.get(str(pos.stock_id)),
                "quantity": float(pos.quantity),
                "avg_cost": float(pos.avg_cost),
                "market_value": float(pos.market_value) if pos.market_value else None,
                "unrealized_pnl": float(pos.unrealized_pnl) if pos.unrealized_pnl else None,
                "weight_pct": float(pos.weight_pct) if pos.weight_pct else None,
                "conviction_band": pos.conviction_band,
                "strategy_name": pos.strategy_name,
                "recommendation_id": str(pos.recommendation_result_id)
                if pos.recommendation_result_id
                else None,
            }
        )

    if not ctx.sources:
        ctx.sources.append({"note": "No portfolio data found."})


def _retrieve_risk(db: Session, entities: ExtractedEntities, ctx: RetrievalContext) -> None:
    stock = _get_stock(db, entities.symbol)
    rec_run = _latest_recommendation_run(db, entities.strategy_name, entities.as_of_date)

    if rec_run:
        ctx.source_refs.append(
            source_ref(
                "recommendation_runs", str(rec_run.id), recommendation_run_id=str(rec_run.id)
            )
        )
        q = select(RecommendationResult).where(
            RecommendationResult.recommendation_run_id == rec_run.id
        )
        if stock:
            q = q.where(RecommendationResult.stock_id == stock.id)
        for r in db.scalars(q.limit(5)).all():
            if stock or any(code in _RISK_REASON_CODES for code in r.reason_codes):
                row = {
                    "recommendation_id": str(r.id),
                    "reason_codes": r.reason_codes,
                    "action": r.action,
                    "conviction_band": r.conviction_band,
                }
                ctx.source_refs.append(
                    source_ref(
                        "recommendation_results",
                        str(r.id),
                        recommendation_run_id=str(rec_run.id),
                        recommendation_id=str(r.id),
                    )
                )
                ctx.sources.append(row)

    if stock:
        packet = db.scalar(
            select(InvestmentReviewPacket)
            .where(InvestmentReviewPacket.stock_id == stock.id)
            .order_by(desc(InvestmentReviewPacket.built_at))
            .limit(1)
        )
        if packet:
            high_concern = db.scalars(
                select(CommitteeReview).where(
                    CommitteeReview.packet_id == packet.id,
                    CommitteeReview.high_concern.is_(True),
                )
            ).all()
            for r in high_concern:
                ctx.source_refs.append(
                    source_ref("committee_reviews", str(r.id), committee_review_id=str(r.id))
                )
                ctx.sources.append(
                    {
                        "committee_review_id": str(r.id),
                        "committee": r.committee_code,
                        "high_concern": True,
                        "high_concern_reason": r.high_concern_reason,
                        "risks": r.risks or [],
                    }
                )

        exit_recs = db.scalars(
            select(ExitRecommendation)
            .where(ExitRecommendation.stock_id == stock.id, ExitRecommendation.status == "PENDING")
            .order_by(desc(ExitRecommendation.as_of_date))
            .limit(3)
        ).all()
        for er in exit_recs:
            ctx.source_refs.append(
                source_ref(
                    "portfolio_exit_recommendations",
                    str(er.id),
                    portfolio_position_id=str(er.portfolio_position_id),
                )
            )
            ctx.sources.append(
                {
                    "exit_recommendation_id": str(er.id),
                    "portfolio_position_id": str(er.portfolio_position_id),
                    "triggers": er.triggers,
                    "urgency": er.urgency,
                    "unrealized_pnl_pct": float(er.unrealized_pnl_pct)
                    if er.unrealized_pnl_pct
                    else None,
                }
            )

    if not ctx.sources:
        ctx.sources.append({"note": "No risk signals found in corpus."})


def _retrieve_performance(db: Session, entities: ExtractedEntities, ctx: RetrievalContext) -> None:
    import re as _re
    from datetime import timedelta
    from calendar import monthrange

    stock = _get_stock(db, entities.symbol)
    period = entities.period_label  # e.g. "1Y", "6M", "2024", "Q1-2025", "2025-03", "YTD"

    # ── Closed positions (portfolio_positions WHERE status=CLOSED) ────────────
    # recommendation_outcomes table is currently empty; use portfolio_positions.
    pos_q = (
        select(PortfolioPosition)
        .where(PortfolioPosition.position_status == "CLOSED")
        .order_by(desc(PortfolioPosition.realized_pnl))
        .limit(20)
    )
    pos_q_asc = (
        select(PortfolioPosition)
        .where(PortfolioPosition.position_status == "CLOSED")
        .order_by(PortfolioPosition.realized_pnl)
        .limit(5)
    )
    if stock:
        pos_q = pos_q.where(PortfolioPosition.stock_id == stock.id)
        pos_q_asc = pos_q_asc.where(PortfolioPosition.stock_id == stock.id)

    closed_positions = db.scalars(pos_q).all()
    # Bottom performers (worst realized_pnl) — deduplicated against top list
    bottom_ids = {p.id for p in closed_positions}
    worst_positions = [p for p in db.scalars(pos_q_asc).all() if p.id not in bottom_ids]
    if closed_positions:
        wins = [p for p in closed_positions if p.realized_pnl and float(p.realized_pnl) > 0]
        losses = [p for p in closed_positions if p.realized_pnl and float(p.realized_pnl) < 0]
        total_pnl = sum(float(p.realized_pnl) for p in closed_positions if p.realized_pnl)
        ctx.sources.append({
            "note": f"Closed positions summary: {len(closed_positions)} total, "
                    f"{len(wins)} wins, {len(losses)} losses. "
                    f"Total realized PnL: {round(total_pnl, 2)}.",
            "win_rate_pct": round(len(wins) / len(closed_positions) * 100, 1) if closed_positions else None,
        })
        # Bulk-fetch recommendation actions for these positions
        rec_ids = [p.recommendation_result_id for p in closed_positions if p.recommendation_result_id]
        _rec_action_map: dict = {}
        if rec_ids:
            from sqlalchemy import and_
            recs = db.scalars(
                select(RecommendationResult).where(RecommendationResult.id.in_(rec_ids))
            ).all()
            _rec_action_map = {r.id: r.action for r in recs}

        for p in closed_positions[:15]:
            ctx.source_refs.append(source_ref("portfolio_positions", str(p.id)))
            action = _rec_action_map.get(p.recommendation_result_id) if p.recommendation_result_id else None
            ctx.sources.append({
                "record_type": "closed_position",
                "portfolio_position_id": str(p.id),
                "symbol": p.stock.symbol if p.stock else None,
                "recommendation_action": action,
                "entry_date": p.entry_date.isoformat() if p.entry_date else None,
                "exit_date": p.exit_date.isoformat() if p.exit_date else None,
                "entry_price": float(p.avg_cost) if p.avg_cost else None,
                "exit_price": float(p.exit_price) if p.exit_price else None,
                "realized_pnl": float(p.realized_pnl) if p.realized_pnl else None,
                "exit_reason": p.exit_reason,
                "quantity": p.quantity,
            })

        # Append worst performers separately so LLM can answer "worst ever" queries
        if worst_positions:
            ctx.sources.append({"note": "Bottom performers (lowest realized_pnl):"})
            for p in worst_positions:
                action = _rec_action_map.get(p.recommendation_result_id) if p.recommendation_result_id else None
                ctx.sources.append({
                    "record_type": "worst_closed_position",
                    "portfolio_position_id": str(p.id),
                    "symbol": p.stock.symbol if p.stock else None,
                    "recommendation_action": action,
                    "realized_pnl": float(p.realized_pnl) if p.realized_pnl else None,
                    "exit_date": p.exit_date.isoformat() if p.exit_date else None,
                    "exit_reason": p.exit_reason,
                })

    # ── NAV history — targeted to requested period ────────────────────────────
    latest_nav = db.scalar(
        select(PortfolioNavHistory).order_by(desc(PortfolioNavHistory.as_of_date)).limit(1)
    )
    if not latest_nav:
        if not closed_positions:
            ctx.sources.append({"note": "No performance data available yet."})
        return

    ctx.source_refs.append(source_ref("portfolio_nav_history", str(latest_nav.id)))
    today = latest_nav.as_of_date

    def _nav_summary(label: str, start_date: date, end_date: date) -> None:
        rows = db.scalars(
            select(PortfolioNavHistory)
            .where(
                PortfolioNavHistory.as_of_date >= start_date,
                PortfolioNavHistory.as_of_date <= end_date,
            )
            .order_by(PortfolioNavHistory.as_of_date)
        ).all()
        if not rows:
            ctx.sources.append({"note": f"No NAV data found for period {label}."})
            return
        s, e = rows[0], rows[-1]
        returns = [float(r.day_return_pct) for r in rows if r.day_return_pct]
        cumulative = (
            (float(e.total_equity) - float(s.total_equity)) / float(s.total_equity) * 100
            if s.total_equity and e.total_equity
            else None
        )
        ctx.sources.append({
            "period": label,
            "start_date": s.as_of_date.isoformat(),
            "end_date": e.as_of_date.isoformat(),
            "start_equity": float(s.total_equity) if s.total_equity else None,
            "end_equity": float(e.total_equity) if e.total_equity else None,
            "cumulative_return_pct": round(cumulative, 4) if cumulative is not None else None,
            "avg_daily_return_pct": round(sum(returns) / len(returns), 4) if returns else None,
            "best_day_return_pct": round(max(returns), 4) if returns else None,
            "worst_day_return_pct": round(min(returns), 4) if returns else None,
            "up_days": sum(1 for r in returns if r > 0),
            "down_days": sum(1 for r in returns if r < 0),
            "trading_days_in_period": len(rows),
            "source_table": "portfolio_nav_history",
        })

    if period and period.isdigit() and len(period) == 4:
        # Calendar year: "2024"
        yr = int(period)
        _nav_summary(period, date(yr, 1, 1), date(yr, 12, 31))

    elif period and _re.match(r"^Q([1-4])-(\d{4})$", period):
        # Quarter: "Q1-2025"
        m = _re.match(r"^Q([1-4])-(\d{4})$", period)
        q_num, yr = int(m.group(1)), int(m.group(2))
        q_start_month = (q_num - 1) * 3 + 1
        q_end_month = q_start_month + 2
        _, last_day = monthrange(yr, q_end_month)
        _nav_summary(period, date(yr, q_start_month, 1), date(yr, q_end_month, last_day))

    elif period and _re.match(r"^\d{4}-\d{2}$", period):
        # Month: "2025-03"
        yr, mo = int(period[:4]), int(period[5:])
        _, last_day = monthrange(yr, mo)
        _nav_summary(period, date(yr, mo, 1), date(yr, mo, last_day))

    elif period == "YTD":
        _nav_summary("YTD", date(today.year, 1, 1), today)

    elif period:
        # Rolling window: "1Y", "6M", "3M", "1M"
        unit_days = {"Y": 365, "M": 30, "W": 7}
        try:
            num = int(period[:-1])
            unit = period[-1]
            cutoff = today - timedelta(days=num * unit_days.get(unit, 30))
            _nav_summary(f"last {period}", cutoff, today)
        except (ValueError, IndexError):
            _nav_summary("1Y", today - timedelta(days=365), today)

    else:
        # No period specified — show 1Y + all-time
        _nav_summary("1Y", today - timedelta(days=365), today)
        earliest = db.scalar(
            select(PortfolioNavHistory.as_of_date)
            .order_by(PortfolioNavHistory.as_of_date)
            .limit(1)
        )
        if earliest:
            _nav_summary("all_time", earliest, today)

    if not ctx.sources:
        ctx.sources.append({"note": "No performance or outcome data found."})


def _retrieve_ops(db: Session, entities: ExtractedEntities, ctx: RetrievalContext) -> None:
    runs = db.scalars(select(DailyBatchRun).order_by(desc(DailyBatchRun.started_at)).limit(3)).all()

    for run in runs:
        ctx.source_refs.append(source_ref("daily_batch_runs", str(run.id)))
        ctx.sources.append(
            {
                "run_id": str(run.id),
                "status": run.status,
                "universe_code": run.universe_code,
                "started_at": run.started_at.isoformat(),
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "phase_results": run.phase_results or {},
            }
        )


def _retrieve_stock(db: Session, entities: ExtractedEntities, ctx: RetrievalContext) -> None:
    stock = _get_stock(db, entities.symbol)
    if not stock:
        ctx.sources.append({"note": "Specify a stock symbol to explain its profile/setup."})
        return

    ctx.source_refs.append(source_ref("stocks", str(stock.id)))
    ctx.sources.append(
        {
            "stock_id": str(stock.id),
            "symbol": stock.symbol,
            "name": stock.name,
            "exchange": stock.exchange,
            "sector": stock.sector,
            "industry": stock.industry,
            "is_active": stock.is_active,
        }
    )

    setup = db.scalar(
        select(StockSetupResearch)
        .where(StockSetupResearch.stock_id == stock.id)
        .order_by(desc(StockSetupResearch.as_of_date), desc(StockSetupResearch.started_at))
        .limit(1)
    )
    if not setup:
        ctx.sources.append({"note": f"No setup-evidence research found for {stock.symbol}."})
        return

    ctx.source_refs.append(source_ref("stock_setup_research", str(setup.id)))
    ctx.sources.append(
        {
            "stock_setup_research_id": str(setup.id),
            "symbol": setup.symbol,
            "as_of_date": setup.as_of_date.isoformat(),
            "status": setup.status,
            "setup_evidence_score": float(setup.setup_evidence_score)
            if setup.setup_evidence_score is not None
            else None,
            "match_count": setup.match_count,
            "qualifying_matches": setup.qualifying_matches,
            "total_matches": setup.total_matches,
        }
    )

    metrics = db.scalars(
        select(StockSetupResearchMetric)
        .where(StockSetupResearchMetric.stock_setup_research_id == setup.id)
        .limit(5)
    ).all()
    for m in metrics:
        ctx.source_refs.append(source_ref("stock_setup_research_metrics", str(m.id)))
        ctx.sources.append(
            {
                "setup_metric_id": str(m.id),
                "regime_label": m.regime_label,
                "occurrence_count": m.occurrence_count,
                "win_rate_20d": float(m.win_rate_20d) if m.win_rate_20d is not None else None,
                "avg_return_20d": float(m.avg_return_20d) if m.avg_return_20d is not None else None,
            }
        )


def _retrieve_market_data(
    db: Session, entities: ExtractedEntities, ctx: RetrievalContext
) -> None:
    stock = _get_stock(db, entities.symbol)
    if not stock:
        ctx.sources.append({"note": "Specify a stock symbol to retrieve market data."})
        return

    rows = db.scalars(
        select(MarketData)
        .where(MarketData.stock_id == stock.id)
        .order_by(desc(MarketData.date))
        .limit(5)
    ).all()
    if not rows:
        ctx.sources.append({"note": f"No market data found for {stock.symbol}."})
        return

    for r in rows:
        ctx.source_refs.append(source_ref("market_data", str(r.id)))
        ctx.sources.append(
            {
                "market_data_id": str(r.id),
                "symbol": stock.symbol,
                "date": r.date.isoformat(),
                "open": float(r.open) if r.open is not None else None,
                "high": float(r.high) if r.high is not None else None,
                "low": float(r.low) if r.low is not None else None,
                "close": float(r.close),
                "volume": r.volume,
                "adj_close": float(r.adj_close) if r.adj_close is not None else None,
                "source": r.source,
            }
        )


def _retrieve_factor_ic(
    db: Session, entities: ExtractedEntities, ctx: RetrievalContext
) -> None:
    q = select(FactorPerformanceMetric)
    if entities.strategy_name:
        q = q.where(FactorPerformanceMetric.strategy_name == entities.strategy_name)
    rows = db.scalars(
        q.order_by(
            desc(FactorPerformanceMetric.as_of_date_end),
            desc(FactorPerformanceMetric.ic_spearman),
        ).limit(10)
    ).all()
    if not rows:
        ctx.sources.append({"note": "No factor-IC metrics found."})
        return

    for m in rows:
        ctx.source_refs.append(source_ref("factor_performance_metrics", str(m.id)))
        ctx.sources.append(
            {
                "factor_metric_id": str(m.id),
                "factor_name": m.factor_name,
                "strategy_name": m.strategy_name,
                "regime_label": m.regime_label,
                "horizon": m.horizon,
                "dataset_split": m.dataset_split,
                "ic_spearman": float(m.ic_spearman) if m.ic_spearman is not None else None,
                "ic_pearson": float(m.ic_pearson) if m.ic_pearson is not None else None,
                "hit_rate": float(m.hit_rate) if m.hit_rate is not None else None,
                "stability_label": m.stability_label,
                "coverage_label": m.coverage_label,
                "confidence": m.confidence,
                "is_statistically_significant": m.is_statistically_significant,
                "sample_size": m.sample_size,
            }
        )


def _retrieve_rcee(db: Session, entities: ExtractedEntities, ctx: RetrievalContext) -> None:
    q = select(StrategyRegimePerformance)
    if entities.strategy_name:
        q = q.where(StrategyRegimePerformance.strategy_name == entities.strategy_name)
    rows = db.scalars(
        q.order_by(
            desc(StrategyRegimePerformance.last_updated),
            StrategyRegimePerformance.regime_label,
            StrategyRegimePerformance.horizon,
        ).limit(12)
    ).all()
    if not rows:
        ctx.sources.append(
            {"note": "No strategy-regime (RCEE) edge metrics found in the corpus."}
        )
        return

    for r in rows:
        ctx.source_refs.append(source_ref("strategy_regime_performance", str(r.id)))
        ctx.sources.append(
            {
                "strategy_regime_performance_id": str(r.id),
                "strategy_name": r.strategy_name,
                "regime_label": r.regime_label,
                "horizon": r.horizon,
                "avg_ic": float(r.avg_ic) if r.avg_ic is not None else None,
                "ic_lower_95": float(r.ic_lower_95) if r.ic_lower_95 is not None else None,
                "hit_rate": float(r.hit_rate) if r.hit_rate is not None else None,
                "expectancy": float(r.expectancy) if r.expectancy is not None else None,
                "expectancy_after_costs": float(r.expectancy_after_costs)
                if r.expectancy_after_costs is not None
                else None,
                "sample_count": r.sample_count,
                "computed_from": r.computed_from,
            }
        )


def _retrieve_regime(db: Session, entities: ExtractedEntities, ctx: RetrievalContext) -> None:
    # Distinct (date, regime) sessions, newest first — to find current regime + onset.
    rows = db.execute(
        select(RankingRun.as_of_date, RankingRun.regime_label)
        .where(RankingRun.regime_label.is_not(None), RankingRun.status == "completed")
        .order_by(desc(RankingRun.as_of_date))
    ).all()
    # Collapse to one regime per date (a date can have multiple strategy runs).
    seen: dict = {}
    ordered_dates: list = []
    for as_of, label in rows:
        if as_of not in seen:
            seen[as_of] = label
            ordered_dates.append(as_of)

    if not ordered_dates:
        ctx.sources.append({"note": "No regime history found in ranking runs."})
    else:
        current_date = ordered_dates[0]
        current_regime = seen[current_date]
        onset = current_date
        sessions = 0
        for d in ordered_dates:
            if seen[d] == current_regime:
                onset = d
                sessions += 1
            else:
                break
        ctx.source_refs.append(
            source_ref("ranking_runs", f"regime:{current_regime}")
        )
        ctx.sources.append(
            {
                "current_regime": current_regime,
                "as_of_date": current_date.isoformat(),
                "in_effect_since": onset.isoformat(),
                "sessions_in_regime": sessions,
            }
        )

    # Active regime policy (allowed regimes / default action / sizing).
    pol_q = select(RegimePolicyConfig).where(RegimePolicyConfig.status == "active")
    if entities.strategy_name:
        pol_q = pol_q.where(RegimePolicyConfig.strategy_name == entities.strategy_name)
    policy = db.scalar(pol_q.order_by(desc(RegimePolicyConfig.policy_version)).limit(1))
    if policy:
        ctx.source_refs.append(source_ref("regime_policy_configs", str(policy.id)))
        ctx.sources.append(
            {
                "regime_policy_config_id": str(policy.id),
                "policy_name": policy.policy_name,
                "strategy_name": policy.strategy_name,
                "allowed_regimes": policy.allowed_regimes,
                "default_action": policy.default_action,
                "size_multipliers": policy.size_multipliers,
            }
        )


def _retrieve_positions(
    db: Session, entities: ExtractedEntities, ctx: RetrievalContext
) -> None:
    stock = _get_stock(db, entities.symbol)
    q = select(PortfolioPosition).order_by(desc(PortfolioPosition.as_of))
    if stock:
        q = q.where(PortfolioPosition.stock_id == stock.id)
    else:
        q = q.limit(15)

    positions = db.scalars(q).all()
    if not positions:
        ctx.sources.append({"note": "No portfolio positions found."})
        return

    symbols = _symbol_map(db, [pos.stock_id for pos in positions])
    for pos in positions:
        ctx.source_refs.append(
            source_ref(
                "portfolio_positions",
                str(pos.id),
                portfolio_position_id=str(pos.id),
                recommendation_id=str(pos.recommendation_result_id)
                if pos.recommendation_result_id
                else None,
            )
        )
        ctx.sources.append(
            {
                "portfolio_position_id": str(pos.id),
                "stock_id": str(pos.stock_id),
                "symbol": symbols.get(str(pos.stock_id)),
                "position_status": pos.position_status,
                "quantity": float(pos.quantity),
                "avg_cost": float(pos.avg_cost),
                "market_value": float(pos.market_value) if pos.market_value else None,
                "unrealized_pnl": float(pos.unrealized_pnl) if pos.unrealized_pnl else None,
                "weight_pct": float(pos.weight_pct) if pos.weight_pct else None,
                "conviction_band": pos.conviction_band,
                "strategy_name": pos.strategy_name,
            }
        )


def _retrieve_exit_strategy(
    db: Session, entities: ExtractedEntities, ctx: RetrievalContext
) -> None:
    run = db.scalar(
        select(ExitResearchRun)
        .where(ExitResearchRun.status == "completed")
        .order_by(desc(ExitResearchRun.completed_at))
        .limit(1)
    )
    if run:
        ctx.source_refs.append(source_ref("exit_research_runs", str(run.id)))
        ctx.sources.append(
            {
                "exit_research_run_id": str(run.id),
                "strategy_name": run.strategy_name,
                "universe_code": run.universe_code,
                "as_of_date_start": run.as_of_date_start.isoformat(),
                "as_of_date_end": run.as_of_date_end.isoformat(),
                "signals_processed": run.signals_processed,
            }
        )

    q = select(ExitResearchPolicyMetric)
    if run:
        q = q.where(ExitResearchPolicyMetric.research_run_id == run.id)
    if entities.strategy_name:
        q = q.where(ExitResearchPolicyMetric.strategy_name == entities.strategy_name)
    metrics = db.scalars(
        q.order_by(desc(ExitResearchPolicyMetric.hit_rate)).limit(10)
    ).all()
    for m in metrics:
        ctx.source_refs.append(source_ref("exit_research_policy_metrics", str(m.id)))
        ctx.sources.append(
            {
                "exit_policy_metric_id": str(m.id),
                "policy_family": m.policy_family,
                "policy_variant": m.policy_variant,
                "regime_label": m.regime_label,
                "horizon": m.horizon,
                "dataset_split": m.dataset_split,
                "hit_rate": float(m.hit_rate) if m.hit_rate is not None else None,
                "mean_return": float(m.mean_return) if m.mean_return is not None else None,
                "avg_holding_days": float(m.avg_holding_days)
                if m.avg_holding_days is not None
                else None,
                "conclusion_status": m.conclusion_status,
            }
        )

    if not ctx.sources:
        ctx.sources.append({"note": "No exit-strategy research found in the corpus."})
