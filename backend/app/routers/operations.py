"""Expose authenticated incident and operations observations."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.routers.auth import current_session
from app.schemas.operations import IncidentResponse, OperationsSummary
from app.services.operations import incidents_data, summary_data

router = APIRouter(prefix='/api/v1/operations', tags=['operations'], dependencies=[Depends(current_session)])


@router.get('/incidents', response_model=IncidentResponse)
def incidents(db: Annotated[Session, Depends(get_db)], limit: Annotated[int, Query(ge=1, le=100)] = 20, offset: Annotated[int, Query(ge=0)] = 0) -> IncidentResponse:
    """Return a bounded page of stored incidents."""
    return incidents_data(db, limit, offset)


@router.get('/summary', response_model=OperationsSummary)
def summary(db: Annotated[Session, Depends(get_db)], limit: Annotated[int, Query(ge=1, le=100)] = 30) -> OperationsSummary:
    """Return active severity counts and source-provided history."""
    return summary_data(db, limit)
