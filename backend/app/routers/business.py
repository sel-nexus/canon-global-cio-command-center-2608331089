"""Expose authenticated source-supplied business impact observations."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.routers.auth import current_session
from app.schemas.business import BusinessResponse
from app.services.business import business_data

router = APIRouter(prefix="/api/v1/business", tags=["business"], dependencies=[Depends(current_session)])


@router.get("/impact", response_model=BusinessResponse, summary="Get quarterly business impact")
def impact(db: Annotated[Session, Depends(get_db)], limit: Annotated[int, Query(ge=1, le=100)] = 20) -> BusinessResponse:
    """Return recent source observations, preserving unavailable values."""
    return business_data(db, limit)
