"""Persist source-provided quarterly business impact observations."""
import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BusinessQuarter(Base):
    """Store independent financial measures for one reporting quarter."""
    __tablename__ = "business_quarters"
    __table_args__ = (
        UniqueConstraint("year", "quarter", name="uq_business_quarter"),
        CheckConstraint("year BETWEEN 1 AND 9999", name="ck_business_year"),
        CheckConstraint("quarter BETWEEN 1 AND 4", name="ck_business_quarter"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(nullable=False)
    quarter: Mapped[int] = mapped_column(nullable=False)
    investment_m: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    revenue_attribution_m: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    cost_avoidance_m: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    operational_cost_savings_m: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    transformation_roi_pct: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
