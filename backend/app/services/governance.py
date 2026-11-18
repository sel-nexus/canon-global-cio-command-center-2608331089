"""Retrieve the most recent persisted governance observations."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.governance import InnovationPortfolio, InnovationQuarter, RiskObservation
from app.schemas.governance import InnovationOverview, InnovationRecord, PortfolioRecord, RiskOverview, RiskRecord


def risk_overview(db: Session) -> RiskOverview:
    """Return the newest assessment without filling missing values from older rows."""
    row = db.scalar(select(RiskObservation).order_by(RiskObservation.recorded_date.desc()).limit(1))
    return RiskOverview(latest=RiskRecord.model_validate(row) if row else None)


def innovation_overview(db: Session) -> InnovationOverview:
    """Return latest outcomes and all categories for the latest portfolio quarter."""
    latest = db.scalar(select(InnovationQuarter).order_by(InnovationQuarter.year.desc(), InnovationQuarter.quarter.desc()).limit(1))
    period = db.execute(select(InnovationPortfolio.year, InnovationPortfolio.quarter).order_by(InnovationPortfolio.year.desc(), InnovationPortfolio.quarter.desc()).limit(1)).first()
    rows = [] if period is None else db.scalars(select(InnovationPortfolio).where(InnovationPortfolio.year == period.year, InnovationPortfolio.quarter == period.quarter).order_by(InnovationPortfolio.category)).all()
    return InnovationOverview(latest=InnovationRecord.model_validate(latest) if latest else None, portfolio=[PortfolioRecord.model_validate(row) for row in rows])
