"""Persist supplier assessments and source-reported quarterly financial history."""
import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PartnerPerformance(Base):
    """Store a current vendor assessment without deriving its measures."""
    __tablename__ = 'partner_performance'
    __table_args__ = (
        UniqueConstraint('vendor_name', name='uq_partner_vendor'),
        CheckConstraint('length(trim(vendor_name)) > 0', name='ck_partner_name'),
        CheckConstraint('sla_compliance_pct BETWEEN 0 AND 100', name='ck_partner_sla'),
        CheckConstraint('annual_spend >= 0', name='ck_partner_spend'),
        CheckConstraint('length(trim(contract_status)) > 0 AND length(trim(review_quarter)) > 0', name='ck_partner_review'),
        CheckConstraint('length(trim(currency)) > 0', name='ck_partner_currency'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_name: Mapped[str] = mapped_column(String(100), nullable=False)
    sla_compliance_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    roi_multiple: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    delivery_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    annual_spend: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(20), nullable=False)
    contract_status: Mapped[str] = mapped_column(String(50), nullable=False)
    review_quarter: Mapped[str] = mapped_column(String(10), nullable=False)
    innovation_output: Mapped[str | None] = mapped_column(String(500))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class PartnerQuarter(Base):
    """Store independent reported spend, verified savings and ROI for a quarter."""
    __tablename__ = 'partner_quarters'
    __table_args__ = (
        UniqueConstraint('partner_id', 'year', 'quarter', name='uq_partner_quarter'),
        CheckConstraint('year BETWEEN 1 AND 9999 AND quarter BETWEEN 1 AND 4', name='ck_partner_quarter_period'),
        CheckConstraint('spend IS NULL OR spend >= 0', name='ck_partner_quarter_spend'),
        CheckConstraint('length(trim(currency)) > 0', name='ck_partner_quarter_currency'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    partner_id: Mapped[int] = mapped_column(ForeignKey('partner_performance.id', ondelete='CASCADE'), nullable=False, index=True)
    year: Mapped[int] = mapped_column(nullable=False)
    quarter: Mapped[int] = mapped_column(nullable=False)
    spend: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    verified_savings: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    roi_multiple: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    currency: Mapped[str] = mapped_column(String(20), nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
