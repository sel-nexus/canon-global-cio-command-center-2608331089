"""Persist source-reported risk and innovation observations."""
import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RiskObservation(Base):
    """Store one dated risk assessment without deriving its ratings."""
    __tablename__ = 'governance_risk_observations'
    __table_args__ = (
        UniqueConstraint('recorded_date', name='uq_governance_risk_date'),
        CheckConstraint('compliance_pct IS NULL OR compliance_pct BETWEEN 0 AND 100', name='ck_governance_compliance'),
        CheckConstraint("nist_maturity IS NULL OR length(trim(nist_maturity)) > 0", name='ck_governance_nist'),
        CheckConstraint("privacy_audit_status IS NULL OR length(trim(privacy_audit_status)) > 0", name='ck_governance_privacy'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    recorded_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    compliance_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    nist_maturity: Mapped[str | None] = mapped_column(String(100))
    privacy_audit_status: Mapped[str | None] = mapped_column(String(255))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class InnovationQuarter(Base):
    """Store source-defined innovation outcomes for a reporting quarter."""
    __tablename__ = 'innovation_quarters'
    __table_args__ = (
        UniqueConstraint('year', 'quarter', name='uq_innovation_quarter'),
        CheckConstraint('year BETWEEN 1 AND 9999 AND quarter BETWEEN 1 AND 4', name='ck_innovation_period'),
        CheckConstraint('deployed_models IS NULL OR deployed_models >= 0', name='ck_innovation_models'),
        CheckConstraint('patent_disclosures IS NULL OR patent_disclosures >= 0', name='ck_innovation_patents'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int]
    quarter: Mapped[int]
    deployed_models: Mapped[int | None]
    patent_disclosures: Mapped[int | None]
    innovation_index: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class InnovationPortfolio(Base):
    """Store one source-supplied portfolio amount and unit per category and quarter."""
    __tablename__ = 'innovation_portfolio'
    __table_args__ = (
        UniqueConstraint('year', 'quarter', 'category', name='uq_innovation_portfolio_period_category'),
        CheckConstraint('year BETWEEN 1 AND 9999 AND quarter BETWEEN 1 AND 4', name='ck_portfolio_period'),
        CheckConstraint("category IN ('GenAI', 'Cloud Migration', 'Edge Computing', 'Automation')", name='ck_portfolio_category'),
        CheckConstraint('amount >= 0', name='ck_portfolio_amount'),
        CheckConstraint('length(trim(unit)) > 0', name='ck_portfolio_unit'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int]
    quarter: Mapped[int]
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
