"""Persist incidents and independently supplied operational observations."""
import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Incident(Base):
    """Store an incident with its source status and optional resolution details."""
    __tablename__ = "operations_incidents"
    __table_args__ = (
        CheckConstraint("length(trim(incident_number)) > 0 AND length(trim(title)) > 0", name="ck_incident_nonempty"),
        CheckConstraint("severity IN ('P1', 'P2', 'P3', 'P4')", name="ck_incident_severity"),
        CheckConstraint("status IN ('Open', 'Investigating', 'Resolved')", name="ck_incident_status"),
        CheckConstraint("mttr_minutes IS NULL OR mttr_minutes >= 0", name="ck_incident_mttr"),
        CheckConstraint("resolved_at IS NULL OR resolved_at >= created_at", name="ck_incident_resolution_time"),
        CheckConstraint("(status = 'Resolved' AND resolved_at IS NOT NULL) OR (status <> 'Resolved' AND resolved_at IS NULL)", name="ck_incident_resolution_status"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    incident_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    mttr_minutes: Mapped[int | None]
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))


class OperationsHistory(Base):
    """Store source-defined daily reporting observations without inferring KPIs."""
    __tablename__ = "operations_history"
    __table_args__ = (
        UniqueConstraint("recorded_date", name="uq_operations_history_date"),
        CheckConstraint("mttr_minutes IS NULL OR mttr_minutes >= 0", name="ck_operations_mttr"),
        CheckConstraint("sla_compliance_pct IS NULL OR sla_compliance_pct BETWEEN 0 AND 100", name="ck_operations_sla"),
        CheckConstraint("uptime_pct IS NULL OR uptime_pct BETWEEN 0 AND 100", name="ck_operations_uptime"),
        CheckConstraint("incident_volume IS NULL OR incident_volume >= 0", name="ck_operations_volume"),
        CheckConstraint("resolution_count IS NULL OR resolution_count >= 0", name="ck_operations_resolutions"),
        CheckConstraint("p1_volume IS NULL OR p1_volume >= 0", name="ck_operations_p1"),
        CheckConstraint("p2_volume IS NULL OR p2_volume >= 0", name="ck_operations_p2"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    recorded_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    mttr_minutes: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    sla_compliance_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    uptime_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    incident_volume: Mapped[int | None]
    resolution_count: Mapped[int | None]
    p1_volume: Mapped[int | None]
    p2_volume: Mapped[int | None]
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
