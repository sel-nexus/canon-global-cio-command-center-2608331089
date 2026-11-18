"""Describe source-supplied quarterly financial values."""
import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class BusinessRecord(BaseModel):
    """Expose independently reported measures without inferred values."""
    model_config = ConfigDict(from_attributes=True)
    year: int
    quarter: int
    investment_m: Decimal | None
    revenue_attribution_m: Decimal | None
    cost_avoidance_m: Decimal | None
    operational_cost_savings_m: Decimal | None
    transformation_roi_pct: Decimal | None
    updated_at: datetime.datetime


class BusinessResponse(BaseModel):
    """Return the newest bounded reporting periods and total available count."""
    quarters: list[BusinessRecord]
    total: int
