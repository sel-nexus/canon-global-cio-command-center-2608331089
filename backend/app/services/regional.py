"""Read regional performance without calculating missing indicators."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.regional import RegionalPerformance
from app.schemas.regional import RegionalRecord, RegionalResponse


def regional_data(db: Session) -> RegionalResponse:
    """Return each persisted region in deterministic alphabetical order."""
    rows = db.scalars(select(RegionalPerformance).order_by(RegionalPerformance.region)).all()
    return RegionalResponse(regions=[RegionalRecord.model_validate(row) for row in rows])
