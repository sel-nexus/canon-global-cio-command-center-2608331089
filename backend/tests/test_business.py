"""Exercise business impact against a disposable PostgreSQL database."""
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.business import BusinessQuarter
from app.services.business import business_data


@pytest.fixture()
def context(isolated_context):
    """Use the per-test isolated PostgreSQL schema."""
    return isolated_context


def login(client):
    """Register and authenticate a test user."""
    assert client.post('/api/v1/auth/register', json={'username': 'alice', 'email': 'alice@example.com', 'password': 'password123'}).status_code == 201
    response = client.post('/api/v1/auth/login', json={'username': 'alice', 'password': 'password123'})
    assert response.status_code == 200
    return {'Authorization': 'Bearer ' + response.json()['access_token']}


def test_auth_empty_and_revocation(context):
    """Reject unauthenticated and revoked sessions and return an honest empty result."""
    client, factory = context
    path = '/api/v1/business/impact'
    assert client.get(path).status_code == 401
    assert client.get(path, headers={'Authorization': 'Bearer forged'}).status_code == 401
    headers = login(client)
    response = client.get(path, headers=headers)
    assert response.status_code == 200
    assert response.json() == {'quarters': [], 'total': 0}
    with factory() as db:
        assert business_data(db, 20).quarters == []
    assert client.post('/api/v1/auth/logout', headers=headers).status_code == 204
    assert client.get(path, headers=headers).status_code == 401


def test_values_order_nulls_updates_and_limit(context):
    """Return committed values and preserve missing measures without calculation."""
    client, factory = context
    headers = login(client)
    with factory() as db:
        db.add_all([
            BusinessQuarter(year=2025, quarter=2, investment_m=Decimal('10.50'), revenue_attribution_m=Decimal('19.25'), cost_avoidance_m=Decimal('3.00'), operational_cost_savings_m=Decimal('2.00'), transformation_roi_pct=Decimal('-5.25')),
            BusinessQuarter(year=2024, quarter=4, investment_m=Decimal('0.00')),
            BusinessQuarter(year=2025, quarter=1),
        ])
        db.commit()
    path = '/api/v1/business/impact'
    response = client.get(path, headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert result['total'] == 3
    assert [(row['year'], row['quarter']) for row in result['quarters']] == [(2024, 4), (2025, 1), (2025, 2)]
    assert result['quarters'][0]['investment_m'] == '0.00'
    assert result['quarters'][1]['transformation_roi_pct'] is None
    latest = result['quarters'][2]
    assert (latest['investment_m'], latest['revenue_attribution_m'], latest['cost_avoidance_m'], latest['operational_cost_savings_m'], latest['transformation_roi_pct']) == ('10.50', '19.25', '3.00', '2.00', '-5.25')
    assert latest['updated_at']
    limited_response = client.get(path, params={'limit': 1}, headers=headers)
    assert limited_response.status_code == 200
    limited = limited_response.json()
    assert limited['total'] == 3 and limited['quarters'] == [latest]
    assert client.get(path, params={'limit': 0}, headers=headers).status_code == 422
    assert client.get(path, params={'limit': 101}, headers=headers).status_code == 422
    with factory() as db:
        row = db.get(BusinessQuarter, 1)
        row.transformation_roi_pct = None
        db.commit()
    updated = client.get(path, params={'limit': 1}, headers=headers)
    assert updated.status_code == 200
    assert updated.json()['quarters'][0]['transformation_roi_pct'] is None


def test_quarter_constraints(context):
    """Enforce valid calendar keys and reject duplicate observations."""
    _, factory = context
    with factory() as db:
        db.add(BusinessQuarter(year=2025, quarter=1))
        db.commit()
        for bad in [BusinessQuarter(year=2025, quarter=1), BusinessQuarter(year=2025, quarter=0), BusinessQuarter(year=2025, quarter=5), BusinessQuarter(year=0, quarter=1)]:
            db.add(bad)
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()
