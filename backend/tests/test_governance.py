"""Exercise authenticated governance against a disposable PostgreSQL database."""
import datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.governance import InnovationPortfolio, InnovationQuarter, RiskObservation


@pytest.fixture()
def context(isolated_context):
    """Use the per-test isolated PostgreSQL schema."""
    return isolated_context


def login(client):
    """Register and authenticate through the identity API."""
    assert client.post('/api/v1/auth/register', json={'username': 'alice', 'email': 'alice@example.com', 'password': 'password123'}).status_code == 201
    response = client.post('/api/v1/auth/login', json={'username': 'alice', 'password': 'password123'})
    assert response.status_code == 200
    return {'Authorization': 'Bearer ' + response.json()['access_token']}


def test_auth_empty_and_revocation(context):
    """Reject invalid and revoked sessions and preserve truly empty states."""
    client, _ = context
    paths = ['/api/v1/governance/risk-overview', '/api/v1/governance/innovation']
    for path in paths:
        assert client.get(path).status_code == 401
        assert client.get(path, headers={'Authorization': 'Bearer forged'}).status_code == 401
    headers = login(client)
    risk = client.get(paths[0], headers=headers)
    assert risk.status_code == 200
    assert risk.json() == {'latest': None}
    innovation = client.get(paths[1], headers=headers)
    assert innovation.status_code == 200
    assert innovation.json() == {'latest': None, 'portfolio': []}
    assert client.post('/api/v1/auth/logout', headers=headers).status_code == 204
    for path in paths:
        assert client.get(path, headers=headers).status_code == 401


def test_latest_persisted_values_and_missing_fields(context):
    """Read latest separate reporting periods without inferring missing measures."""
    client, factory = context
    headers = login(client)
    with factory() as db:
        db.add_all([
            RiskObservation(recorded_date=datetime.date(2024, 1, 1), compliance_pct=Decimal('90.00'), nist_maturity='Tier 3', privacy_audit_status='Complete'),
            RiskObservation(recorded_date=datetime.date(2025, 1, 1), compliance_pct=Decimal('0.00'), nist_maturity='Tier 4'),
            InnovationQuarter(year=2024, quarter=4, deployed_models=8, innovation_index=Decimal('55.00')),
            InnovationQuarter(year=2025, quarter=1, deployed_models=0, patent_disclosures=3, innovation_index=Decimal('64.25')),
            InnovationPortfolio(year=2024, quarter=4, category='Automation', amount=Decimal('99'), unit='USD M'),
            *[InnovationPortfolio(year=2025, quarter=2, category=category, amount=Decimal('12.50'), unit='USD M') for category in ['GenAI', 'Cloud Migration', 'Edge Computing', 'Automation']],
        ])
        db.commit()
    risk = client.get('/api/v1/governance/risk-overview', headers=headers)
    assert risk.status_code == 200
    assert risk.json()['latest']['recorded_date'] == '2025-01-01'
    assert risk.json()['latest']['compliance_pct'] == '0.00'
    assert risk.json()['latest']['nist_maturity'] == 'Tier 4'
    assert risk.json()['latest']['privacy_audit_status'] is None
    response = client.get('/api/v1/governance/innovation', headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert result['latest']['quarter'] == 1 and result['latest']['deployed_models'] == 0
    assert result['latest']['patent_disclosures'] == 3 and result['latest']['innovation_index'] == '64.25'
    assert {row['category'] for row in result['portfolio']} == {'GenAI', 'Cloud Migration', 'Edge Computing', 'Automation'}
    assert all(row['amount'] == '12.50' and row['unit'] == 'USD M' and row['quarter'] == 2 for row in result['portfolio'])
    with factory() as db:
        row = db.get(RiskObservation, 2)
        row.privacy_audit_status = 'Review in progress'
        db.commit()
    risk = client.get('/api/v1/governance/risk-overview', headers=headers)
    assert risk.status_code == 200
    assert risk.json()['latest']['privacy_audit_status'] == 'Review in progress'


def test_database_constraints(context):
    """Reject invalid periods, scores, counts, categories and duplicate records."""
    _, factory = context
    with factory() as db:
        db.add_all([RiskObservation(recorded_date=datetime.date(2025, 1, 1)), InnovationQuarter(year=2025, quarter=1), InnovationPortfolio(year=2025, quarter=1, category='GenAI', amount=Decimal('0'), unit='USD M')])
        db.commit()
        bad = [
            RiskObservation(recorded_date=datetime.date(2025, 1, 1)),
            RiskObservation(recorded_date=datetime.date(2025, 1, 2), compliance_pct=Decimal('100.01')),
            RiskObservation(recorded_date=datetime.date(2025, 1, 2), nist_maturity=' '),
            InnovationQuarter(year=2025, quarter=1),
            InnovationQuarter(year=2025, quarter=5),
            InnovationQuarter(year=2025, quarter=2, deployed_models=-1),
            InnovationQuarter(year=2025, quarter=2, patent_disclosures=-1),
            InnovationPortfolio(year=2025, quarter=1, category='GenAI', amount=Decimal('1'), unit='USD M'),
            InnovationPortfolio(year=2025, quarter=1, category='Other', amount=Decimal('1'), unit='USD M'),
            InnovationPortfolio(year=2025, quarter=2, category='GenAI', amount=Decimal('-1'), unit='USD M'),
            InnovationPortfolio(year=2025, quarter=2, category='GenAI', amount=Decimal('1'), unit=' '),
        ]
        for row in bad:
            db.add(row)
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()
