"""Describe the authenticated strategic dashboard response."""
import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class Metric(BaseModel):
    """Expose a stored observation without internal identifiers."""
    model_config = ConfigDict(from_attributes=True)
    category: str
    metric_name: str
    metric_value: Decimal
    unit: str | None
    trend: str | None
    change_pct: Decimal | None
    insight: str | None
    recorded_date: datetime.date


class Budget(BaseModel):
    """Expose one monthly budget and actual comparison."""
    model_config = ConfigDict(from_attributes=True)
    name: str
    month: datetime.date
    unit: str | None
    budget: Decimal
    actual: Decimal


class StrategicDashboard(BaseModel):
    """Return current observations and dated data in the reporting window."""
    window_start: datetime.date
    window_end: datetime.date
    metrics: list[Metric]
    trends: list[Metric]
    budgets: list[Budget]
    insights: list[Metric]
