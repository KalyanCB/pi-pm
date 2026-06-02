from __future__ import annotations

from typing import Protocol

from app.args.llm.port import LlmPort
from app.workspace_args.committee_contracts import CommitteeResult
from app.workspace_args.models import InvestmentReviewPacket


class CommitteePlugin(Protocol):
    committee_code: str
    version: str

    def execute(self, packet: InvestmentReviewPacket, llm: LlmPort) -> CommitteeResult: ...
