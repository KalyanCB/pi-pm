from __future__ import annotations

from typing import Any, TypedDict


class ArgsGraphState(TypedDict, total=False):
    run_id: str
    run_config: dict[str, Any]
    ranking_run_id: str
    packets: list[dict[str, Any]]
    committee_codes: list[str]
    reviews: list[dict[str, Any]]
    cro_outputs: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    phase: str
    token_usage_total: int
