"""Read persisted operational observations and active incident counts."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.operations import Incident, OperationsHistory
from app.schemas.operations import HistoryRecord, IncidentRecord, IncidentResponse, OperationsSummary


def incidents_data(db: Session, limit: int, offset: int) -> IncidentResponse:
    """Return a deterministic newest-first incident page."""
    rows = db.scalars(select(Incident).order_by(Incident.created_at.desc(), Incident.id.desc()).limit(limit).offset(offset)).all()
    total = db.scalar(select(func.count()).select_from(Incident)) or 0
    return IncidentResponse(incidents=[IncidentRecord.model_validate(row) for row in rows], total=total)


def summary_data(db: Session, limit: int) -> OperationsSummary:
    """Return counts over all stored incidents and recent supplied history."""
    total_incidents = db.scalar(select(func.count()).select_from(Incident)) or 0
    counts = None
    if total_incidents:
        counts = dict.fromkeys(('P1', 'P2', 'P3'), 0)
        grouped = db.execute(select(Incident.severity, func.count()).where(Incident.status.in_(['Open', 'Investigating']), Incident.severity.in_(['P1', 'P2', 'P3'])).group_by(Incident.severity)).all()
        counts.update(dict(grouped))
    rows = db.scalars(select(OperationsHistory).order_by(OperationsHistory.recorded_date.desc()).limit(limit)).all()
    history = [HistoryRecord.model_validate(row) for row in reversed(rows)]
    total = db.scalar(select(func.count()).select_from(OperationsHistory)) or 0
    return OperationsSummary(active_counts=counts, latest=history[-1] if history else None, history=history, history_total=total)
