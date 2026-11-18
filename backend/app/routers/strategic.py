"""Expose authenticated strategic metrics and exports."""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.routers.auth import current_session
from app.schemas.strategic import StrategicDashboard
from app.services import strategic

router = APIRouter(prefix="/api/v1/dashboard", tags=["strategic"], dependencies=[Depends(current_session)])


@router.get("/strategic-metrics", response_model=StrategicDashboard)
def strategic_metrics(db: Annotated[Session, Depends(get_db)]) -> StrategicDashboard:
    """Return source-backed metrics, insights, and twelve-month history."""
    return strategic.dashboard(db)


@router.get("/strategic-metrics/export")
def export_strategic(db: Annotated[Session, Depends(get_db)], format: Annotated[Literal["json", "csv"], Query()] = "json") -> Response:
    """Download the same reporting window as JSON or spreadsheet-safe CSV."""
    data = strategic.dashboard(db)
    body = data.model_dump_json() if format == "json" else strategic.csv_export(data)
    media_type = "application/json" if format == "json" else "text/csv"
    return Response(body, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="strategic-metrics.{format}"', "Cache-Control": "no-store"})
