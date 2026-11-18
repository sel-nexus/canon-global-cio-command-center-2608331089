"""Expose authenticated supplier performance and quarterly history."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.routers.auth import current_session
from app.schemas.partnerships import PartnershipsResponse
from app.services.partnerships import partnerships_data

router = APIRouter(prefix='/api/v1/partnerships', tags=['partnerships'], dependencies=[Depends(current_session)])


@router.get('', response_model=PartnershipsResponse)
def partnerships(db: Annotated[Session, Depends(get_db)], limit: Annotated[int, Query(ge=1, le=100)] = 20, offset: Annotated[int, Query(ge=0)] = 0, history_limit: Annotated[int, Query(ge=1, le=100)] = 20) -> PartnershipsResponse:
    """Return a bounded page of partner assessments and recent history."""
    return partnerships_data(db, limit, offset, history_limit)
