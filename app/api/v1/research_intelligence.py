from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_research_intelligence_service
from app.schemas.research_intelligence import ResearchIntelligenceGenerateRequest
from app.services.research_intelligence_service import ResearchIntelligenceService

router = APIRouter()


@router.post("/generate")
def generate_executive_pack(
    payload: ResearchIntelligenceGenerateRequest,
    service: ResearchIntelligenceService = Depends(get_research_intelligence_service),
) -> dict:
    return service.generate_executive_pack(
        universe_code=payload.universe_code,
        start_date=payload.start_date,
        end_date=payload.end_date,
        holdout_start_date=payload.holdout_start_date,
        persist=payload.persist,
    )


@router.get("/reports/executive-summary")
def executive_summary(
    universe_code: str = Query(...),
    service: ResearchIntelligenceService = Depends(get_research_intelligence_service),
) -> dict | None:
    return service.get_report("executive_committee_summary", universe_code=universe_code)


@router.get("/reports/coverage")
def coverage_report(
    universe_code: str = Query(...),
    service: ResearchIntelligenceService = Depends(get_research_intelligence_service),
) -> dict | None:
    return service.get_report("coverage_statistics", universe_code=universe_code)


@router.get("/reports/ic-by-strategy")
def ic_by_strategy(
    universe_code: str = Query(...),
    service: ResearchIntelligenceService = Depends(get_research_intelligence_service),
) -> dict | None:
    return service.get_report("ic_by_strategy", universe_code=universe_code)


@router.get("/reports/top-20")
def top_20(
    universe_code: str = Query(...),
    service: ResearchIntelligenceService = Depends(get_research_intelligence_service),
) -> dict | None:
    return service.get_report("current_top_20_candidates", universe_code=universe_code)
