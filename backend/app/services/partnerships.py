"""Read supplier assessments and bounded source-reported histories."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.partnerships import PartnerPerformance, PartnerQuarter
from app.schemas.partnerships import PartnerQuarterRecord, PartnerRecord, PartnershipsResponse


def partnerships_data(db: Session, limit: int, offset: int, history_limit: int) -> PartnershipsResponse:
    """Return a supplier page and the latest quarters in chronological order."""
    partners = db.scalars(select(PartnerPerformance).order_by(PartnerPerformance.vendor_name, PartnerPerformance.id).offset(offset).limit(limit)).all()
    total = db.scalar(select(func.count()).select_from(PartnerPerformance)) or 0
    ids = [partner.id for partner in partners]
    histories = {partner_id: [] for partner_id in ids}
    counts = {partner_id: 0 for partner_id in ids}
    if ids:
        ranked = select(PartnerQuarter.id, func.row_number().over(partition_by=PartnerQuarter.partner_id, order_by=(PartnerQuarter.year.desc(), PartnerQuarter.quarter.desc())).label('rank')).where(PartnerQuarter.partner_id.in_(ids)).subquery()
        rows = db.scalars(select(PartnerQuarter).join(ranked, PartnerQuarter.id == ranked.c.id).where(ranked.c.rank <= history_limit).order_by(PartnerQuarter.year, PartnerQuarter.quarter)).all()
        for row in rows:
            histories[row.partner_id].append(PartnerQuarterRecord.model_validate(row))
        for partner_id, count in db.execute(select(PartnerQuarter.partner_id, func.count()).where(PartnerQuarter.partner_id.in_(ids)).group_by(PartnerQuarter.partner_id)):
            counts[partner_id] = count
    return PartnershipsResponse(partners=[PartnerRecord.model_validate({**{field: getattr(partner, field) for field in PartnerRecord.model_fields if field not in {'history', 'history_total'}}, 'history': histories[partner.id], 'history_total': counts[partner.id]}) for partner in partners], total=total)
