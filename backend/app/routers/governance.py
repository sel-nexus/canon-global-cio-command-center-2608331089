"""Expose authenticated source-reported risk and innovation data."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.routers.auth import current_session
from app.schemas.governance import InnovationOverview, RiskOverview
from app.services.governance import innovation_overview, risk_overview

router = APIRouter(prefix='/api/v1/governance', tags=['governance'], dependencies=[Depends(current_session)])


@router.get('/risk-overview', response_model=RiskOverview)
def risk(db: Annotated[Session, Depends(get_db)]) -> RiskOverview:
    """Return the most recent source-reported risk assessment."""
    return risk_overview(db)


@router.get('/innovation', response_model=InnovationOverview)
def innovation(db: Annotated[Session, Depends(get_db)]) -> InnovationOverview:
    """Return the latest available portfolio and innovation outcomes."""
    return innovation_overview(db)
