"""Read quarterly business impact without deriving financial measures."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.business import BusinessQuarter
from app.schemas.business import BusinessRecord, BusinessResponse


def business_data(db: Session, limit: int) -> BusinessResponse:
    """Return the newest periods in chronological order and their total count."""
    rows = db.scalars(select(BusinessQuarter).order_by(BusinessQuarter.year.desc(), BusinessQuarter.quarter.desc()).limit(limit)).all()
    total = db.scalar(select(func.count()).select_from(BusinessQuarter)) or 0
    return BusinessResponse(quarters=[BusinessRecord.model_validate(row) for row in reversed(rows)], total=total)
