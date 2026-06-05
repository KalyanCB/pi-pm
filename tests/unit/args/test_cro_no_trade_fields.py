from app.args.agents.cro_agent import aggregate_committee_reviews
from app.args.llm.port import MockLlmPort
from app.workspace_args.committee_contracts import CommitteeReviewOutput


def test_cro_output_has_no_trade_recommendation_keys():
    reviews = [
        CommitteeReviewOutput(
            committee_code="TARC",
            committee_version="1.0.0",
            findings="ok",
            strengths=[],
            risks=[],
            supporting_evidence=[],
            confidence=0.8,
            research_label="supportive",
        )
    ]
    cro_result = aggregate_committee_reviews("AAA.NS", reviews, MockLlmPort())
    cro = cro_result.output
    blob = {**cro.__dict__, **cro.aggregation_snapshot, **cro.structured}
    forbidden = {
        "recommendation_label",
        "position_size_pct",
        "stop_loss_pct",
        "label",
        "BUY",
        "SELL",
        "HOLD",
    }
    text = str(blob).upper()
    for key in ("POSITION_SIZE", "STOP_LOSS", "STRONG_BUY"):
        assert key not in text
