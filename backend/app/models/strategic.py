"""Persist dated strategic observations and financial comparisons."""
import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StrategicMetric(Base):
    """Represent one source-provided metric observation."""

    __tablename__ = "strategic_metrics"
    __table_args__ = (
        CheckConstraint("category IN ('business', 'risk', 'innovation', 'operations')", name="ck_strategic_category"),
        CheckConstraint("trend IS NULL OR trend IN ('up', 'down', 'neutral')", name="ck_strategic_trend"),
        UniqueConstraint("category", "metric_name", "recorded_date", name="uq_strategic_observation"),
        Index("ix_strategic_metric_date", "recorded_date"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20))
    trend: Mapped[str | None] = mapped_column(String(20))
    change_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    insight: Mapped[str | None] = mapped_column(Text)
    recorded_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)


class StrategicBudget(Base):
    """Store comparable budget and actual values for a specific month."""

    __tablename__ = "strategic_budgets"
    __table_args__ = (
        CheckConstraint("EXTRACT(DAY FROM month) = 1", name="ck_strategic_budget_month"),
        UniqueConstraint("name", "month", name="uq_strategic_budget_month"),
        Index("ix_strategic_budget_month", "month"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    month: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20))
    budget: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    actual: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
