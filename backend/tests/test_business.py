"""Exercise business impact against a disposable PostgreSQL database."""
import os
from decimal import Decimal

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.business import BusinessQuarter
from app.services.business import business_data


@pytest.fixture()
def context():
    """Migrate and reset the explicitly selected test database."""
    url = make_url(os.environ['TEST_DATABASE_URL'])
    if not url.drivername.startswith('postgresql') or not url.database or 'test' not in url.database.lower() or url == settings.application_url:
        raise RuntimeError('TEST_DATABASE_URL must name a separate PostgreSQL test database')
    config = Config('alembic.ini')
    config.attributes['database_url'] = url
    command.upgrade(config, 'head')
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text('TRUNCATE business_quarters, auth_sessions, users RESTART IDENTITY CASCADE'))
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override():
        """Provide a test database session."""
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override
    with TestClient(app) as client:
        yield client, factory
    app.dependency_overrides.clear()
    engine.dispose()


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
    assert client.get(path, headers=headers).json() == {'quarters': [], 'total': 0}
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
    limited = client.get(path, params={'limit': 1}, headers=headers).json()
    assert limited['total'] == 3 and limited['quarters'] == [latest]
    assert client.get(path, params={'limit': 0}, headers=headers).status_code == 422
    assert client.get(path, params={'limit': 101}, headers=headers).status_code == 422
    with factory() as db:
        row = db.get(BusinessQuarter, 1)
        row.transformation_roi_pct = None
        db.commit()
    assert client.get(path, params={'limit': 1}, headers=headers).json()['quarters'][0]['transformation_roi_pct'] is None


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
