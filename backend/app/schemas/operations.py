"""Describe incident listings and supplied operations history."""
import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class IncidentRecord(BaseModel):
    """Expose a persisted incident."""
    model_config = ConfigDict(from_attributes=True)
    incident_number: str
    severity: Literal['P1', 'P2', 'P3', 'P4']
    title: str
    status: Literal['Open', 'Investigating', 'Resolved']
    mttr_minutes: int | None
    created_at: datetime.datetime
    resolved_at: datetime.datetime | None


class IncidentResponse(BaseModel):
    """Return a bounded incident page and its total."""
    incidents: list[IncidentRecord]
    total: int


class HistoryRecord(BaseModel):
    """Expose source measures for one reporting day."""
    model_config = ConfigDict(from_attributes=True)
    recorded_date: datetime.date
    mttr_minutes: Decimal | None
    sla_compliance_pct: Decimal | None
    uptime_pct: Decimal | None
    incident_volume: int | None
    resolution_count: int | None
    p1_volume: int | None
    p2_volume: int | None
    updated_at: datetime.datetime


class OperationsSummary(BaseModel):
    """Return active counts and independently reported chronological history."""
    active_counts: dict[str, int] | None
    latest: HistoryRecord | None
    history: list[HistoryRecord]
    history_total: int
