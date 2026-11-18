"""Persist the latest source-provided regional performance records."""
import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RegionalPerformance(Base):
    """Store one current observation per named region."""
    __tablename__ = "regional_performance"
    __table_args__ = (
        UniqueConstraint("region", name="uq_regional_performance_region"),
        CheckConstraint("status IN ('Excellent', 'Good', 'Warning', 'Critical')", name="ck_regional_status"),
        CheckConstraint("availability_pct BETWEEN 0 AND 100", name="ck_regional_availability"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    region: Mapped[str] = mapped_column(String(50), nullable=False)
    health_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    availability_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    security_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    transformation_index: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
