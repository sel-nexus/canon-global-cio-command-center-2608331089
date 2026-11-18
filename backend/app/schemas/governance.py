"""Describe source-reported risk and innovation responses."""
import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class RiskRecord(BaseModel):
    """Expose a dated risk assessment."""
    model_config = ConfigDict(from_attributes=True)
    recorded_date: datetime.date
    compliance_pct: Decimal | None
    nist_maturity: str | None
    privacy_audit_status: str | None
    updated_at: datetime.datetime


class RiskOverview(BaseModel):
    """Return the latest source assessment or no assessment."""
    latest: RiskRecord | None


class InnovationRecord(BaseModel):
    """Expose outcomes from a single reporting quarter."""
    model_config = ConfigDict(from_attributes=True)
    year: int
    quarter: int
    deployed_models: int | None
    patent_disclosures: int | None
    innovation_index: Decimal | None
    updated_at: datetime.datetime


class PortfolioRecord(BaseModel):
    """Expose a portfolio amount with its source unit and reporting period."""
    model_config = ConfigDict(from_attributes=True)
    year: int
    quarter: int
    category: str
    amount: Decimal
    unit: str
    updated_at: datetime.datetime


class InnovationOverview(BaseModel):
    """Return the latest outcomes and the latest portfolio period independently."""
    latest: InnovationRecord | None
    portfolio: list[PortfolioRecord]
