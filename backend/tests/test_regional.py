"""Verify regional API and constraints against a disposable PostgreSQL database."""
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
from app.models.regional import RegionalPerformance
from app.services.regional import regional_data


@pytest.fixture()
def context():
    """Migrate and reset only a separate explicitly named test database."""
    url = make_url(os.environ['TEST_DATABASE_URL'])
    if not url.drivername.startswith('postgresql') or not url.database or 'test' not in url.database.lower() or url == settings.application_url:
        raise RuntimeError('TEST_DATABASE_URL must name a separate PostgreSQL test database')
    config = Config('alembic.ini')
    config.attributes['database_url'] = url
    command.upgrade(config, 'head')
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text('TRUNCATE regional_performance, auth_sessions, users RESTART IDENTITY CASCADE'))
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override():
        """Supply a session bound to the test database."""
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override
    with TestClient(app) as client:
        yield client, factory
    app.dependency_overrides.clear()
    engine.dispose()


def login(client):
    """Register and authenticate a real test account."""
    assert client.post('/api/v1/auth/register', json={'username': 'alice', 'email': 'alice@example.com', 'password': 'password123'}).status_code == 201
    response = client.post('/api/v1/auth/login', json={'username': 'alice', 'password': 'password123'})
    assert response.status_code == 200
    return {'Authorization': 'Bearer ' + response.json()['access_token']}


def record(region='EMEA', status='Warning', availability=Decimal('99.70')):
    """Build a source observation for persistence tests."""
    return RegionalPerformance(region=region, health_score=Decimal('68.25'), availability_pct=availability,
                               security_score=Decimal('73.10'), transformation_index=Decimal('54.50'), status=status)


def test_auth_empty_and_revocation(context):
    """Require live sessions for both endpoints and return empty lists honestly."""
    client, factory = context
    paths = ['/api/v1/metrics/regional-radar', '/api/v1/metrics/regional-performance']
    for path in paths:
        assert client.get(path).status_code == 401
        assert client.get(path, headers={'Authorization': 'Bearer forged'}).status_code == 401
    headers = login(client)
    for path in paths:
        assert client.get(path, headers=headers).json() == {'regions': []}
    with factory() as db:
        assert regional_data(db).regions == []
    assert client.post('/api/v1/auth/logout', headers=headers).status_code == 204
    for path in paths:
        assert client.get(path, headers=headers).status_code == 401


def test_persisted_values_and_updates(context):
    """Read committed scores, status and timestamp from both API endpoints."""
    client, factory = context
    headers = login(client)
    with factory() as db:
        db.add_all([record(), record('Americas', 'Good')])
        db.commit()
    paths = ['/api/v1/metrics/regional-radar', '/api/v1/metrics/regional-performance']
    results = [client.get(path, headers=headers) for path in paths]
    assert all(result.status_code == 200 for result in results)
    assert results[0].json() == results[1].json()
    rows = results[0].json()['regions']
    assert [row['region'] for row in rows] == ['Americas', 'EMEA']
    assert rows[1]['status'] == 'Warning'
    assert rows[1]['health_score'] == '68.25' and rows[1]['availability_pct'] == '99.70'
    assert rows[1]['security_score'] == '73.10' and rows[1]['transformation_index'] == '54.50'
    assert rows[1]['updated_at']
    with factory() as db:
        row = db.get(RegionalPerformance, 1)
        row.status = 'Critical'
        db.commit()
    assert client.get(paths[1], headers=headers).json()['regions'][1]['status'] == 'Critical'


def test_constraints(context):
    """Enforce unique regions, status vocabulary and percentage bounds."""
    _, factory = context
    with factory() as db:
        db.add(record())
        db.commit()
        for bad in [record(), record('APAC', 'Unknown'), record('APAC', 'Good', Decimal('100.01'))]:
            db.add(bad)
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()
