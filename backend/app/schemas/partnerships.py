"""Describe source-reported supplier assessments and history."""
import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PartnerQuarterRecord(BaseModel):
    """Expose one reporting period without calculating missing fields."""
    model_config = ConfigDict(from_attributes=True)
    year: int
    quarter: int
    spend: Decimal | None
    verified_savings: Decimal | None
    roi_multiple: Decimal | None
    currency: str
    updated_at: datetime.datetime


class PartnerRecord(BaseModel):
    """Expose a current assessment and its recent financial history."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    vendor_name: str
    sla_compliance_pct: Decimal
    roi_multiple: Decimal
    delivery_score: Decimal
    annual_spend: Decimal
    currency: str
    contract_status: str
    review_quarter: str
    innovation_output: str | None
    updated_at: datetime.datetime
    history: list[PartnerQuarterRecord]
    history_total: int


class PartnershipsResponse(BaseModel):
    """Return a page of partners and their bounded histories."""
    partners: list[PartnerRecord]
    total: int
