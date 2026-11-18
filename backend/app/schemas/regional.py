"""Describe source-provided regional metrics."""
import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class RegionalRecord(BaseModel):
    """Expose a region's stored scores, status and update time."""
    model_config = ConfigDict(from_attributes=True)
    region: str
    health_score: Decimal
    availability_pct: Decimal
    security_score: Decimal
    transformation_index: Decimal
    status: str
    updated_at: datetime.datetime


class RegionalResponse(BaseModel):
    """Return the stored regions, or an empty list when none exist."""
    regions: list[RegionalRecord]
