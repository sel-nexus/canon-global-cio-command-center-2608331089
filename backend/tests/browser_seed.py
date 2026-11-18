"""Seed synthetic browser-only observations into an explicitly named disposable database."""
import os
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.business import BusinessQuarter
from app.models.governance import InnovationPortfolio, InnovationQuarter, RiskObservation
from app.models.operations import Incident, OperationsHistory
from app.models.partnerships import PartnerPerformance, PartnerQuarter
from app.models.regional import RegionalPerformance
from app.models.strategic import StrategicMetric


def main() -> None:
    """Add one labeled fixture per dashboard to a fresh isolated browser database."""
    url = os.environ['BROWSER_TEST_DATABASE_URL']
    if not url.endswith('/cio_browser_test'):
        raise ValueError('Only the dedicated cio_browser_test database may be seeded')
    engine = create_engine(url)
    today = date.today()
    with Session(engine) as db:
        partner = PartnerPerformance(vendor_name='TEST Supplier', sla_compliance_pct=Decimal('98.25'), roi_multiple=Decimal('1.25'), delivery_score=Decimal('88.50'), annual_spend=Decimal('1234.50'), currency='USD', contract_status='Review', review_quarter='2025 Q2', innovation_output='TEST pilots')
        db.add(partner)
        db.flush()
        db.add_all([
            StrategicMetric(category='business', metric_name='TEST impact', metric_value=Decimal('25.50'), unit='index', trend='up', insight='Synthetic browser test observation', recorded_date=today),
            RegionalPerformance(region='TEST EMEA', health_score=Decimal('68.25'), availability_pct=Decimal('99.70'), security_score=Decimal('73.10'), transformation_index=Decimal('54.50'), status='Warning'),
            BusinessQuarter(year=2025, quarter=2, investment_m=Decimal('10.50'), revenue_attribution_m=Decimal('19.25'), cost_avoidance_m=Decimal('3.00'), operational_cost_savings_m=Decimal('2.00'), transformation_roi_pct=Decimal('5.25')),
            RiskObservation(recorded_date=today, compliance_pct=Decimal('92.75'), nist_maturity='TEST', privacy_audit_status='TEST'),
            InnovationQuarter(year=2025, quarter=1, deployed_models=2, patent_disclosures=3, innovation_index=Decimal('64.25')),
            InnovationPortfolio(year=2025, quarter=1, category='GenAI', amount=Decimal('10.00'), unit='TEST'),
            OperationsHistory(recorded_date=today, mttr_minutes=Decimal('12.50'), sla_compliance_pct=Decimal('99.50'), uptime_pct=Decimal('99.99'), incident_volume=4, resolution_count=2, p1_volume=1, p2_volume=0),
            Incident(incident_number='E2E-XSS', severity='P1', status='Open', title='<img src=x onerror="window.__e2eStoredXss=1">'),
            PartnerQuarter(partner_id=partner.id, year=2025, quarter=1, spend=10, verified_savings=9, roi_multiple=2, currency='USD'),
        ])
        db.commit()
    engine.dispose()


if __name__ == '__main__':
    main()
