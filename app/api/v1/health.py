from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import Settings, get_settings

router = APIRouter()


@router.get("/health")
def health_check(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "service": "pi-pm",
        "environment": settings.app_env,
        "database": "connected",
    }
