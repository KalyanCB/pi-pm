from uuid import uuid4

from app.args.graph.workflow import ArgsResearchWorkflow
from app.args.llm.registry import CommitteeLlmRegistry
from app.args.plugins.registry import CommitteeRegistry
from app.core.config import Settings
from app.workspace_args.models import InvestmentReviewPacket


def _sample_packet() -> InvestmentReviewPacket:
    payload = {
        "packet_version": "1.0.0",
        "symbol": "AAA.NS",
        "ranking": {"rank": 1, "composite_score": 0.9},
        "technical_factors": {"momentum": {"normalized": 0.8}},
        "validation": {
            "status": "completed",
            "horizon_metrics": [{"horizon": 5, "sample_size": 50}],
        },
        "quant_evidence": {"factor_ic": [{"factor_name": "momentum"}]},
        "regime": {"regime_label": "BULL_LOW_VOL"},
    }
    rid = uuid4()
    return InvestmentReviewPacket(
        symbol="AAA.NS",
        stock_id=uuid4(),
        ranking_run_id=rid,
        ranking_result_id=uuid4(),
        payload=payload,
        packet_hash="deadbeef",
    )


def test_workflow_produces_reviews_and_cro():
    llm_registry = CommitteeLlmRegistry.from_settings(Settings(args_llm_provider="mock"))
    workflow = ArgsResearchWorkflow(CommitteeRegistry(), llm_registry)
    reviews, cro, tokens = workflow.run_committees_and_cro([_sample_packet()], ["TARC", "QRC"])
    assert len(reviews) == 2
    assert len(cro) == 1
    assert tokens > 0
    assert "aggregation" in cro[0]
