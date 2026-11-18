"""Expose authenticated regional radar and performance data."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.routers.auth import current_session
from app.schemas.regional import RegionalResponse
from app.services.regional import regional_data

router = APIRouter(prefix="/api/v1/metrics", tags=["regional"], dependencies=[Depends(current_session)])


@router.get("/regional-radar", response_model=RegionalResponse)
def regional_radar(db: Annotated[Session, Depends(get_db)]) -> RegionalResponse:
    """Return the raw regional values used for the radar comparison."""
    return regional_data(db)


@router.get("/regional-performance", response_model=RegionalResponse)
def regional_performance(db: Annotated[Session, Depends(get_db)]) -> RegionalResponse:
    """Return the regional status and evidence for investigation."""
    return regional_data(db)
