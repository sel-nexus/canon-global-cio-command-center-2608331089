"""Verify strategic storage, exports and session boundaries on PostgreSQL."""
import csv
import datetime
import io
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
from app.models.strategic import StrategicBudget, StrategicMetric
from app.services.strategic import dashboard


@pytest.fixture()
def context():
    """Migrate and reset only a separately configured test database."""
    url = make_url(os.environ["TEST_DATABASE_URL"])
    if not url.drivername.startswith("postgresql") or not url.database or "test" not in url.database.lower() or url == settings.application_url:
        raise RuntimeError("TEST_DATABASE_URL must name a separate PostgreSQL test database")
    config = Config("alembic.ini")
    config.attributes["database_url"] = url
    command.upgrade(config, "head")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE strategic_metrics, strategic_budgets, auth_sessions, users RESTART IDENTITY CASCADE"))
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override():
        """Supply sessions backed by the isolated database."""
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override
    with TestClient(app) as client:
        yield client, factory
    app.dependency_overrides.clear()
    engine.dispose()


def login(client):
    """Create and authenticate a test account."""
    assert client.post('/api/v1/auth/register', json={'username': 'alice', 'email': 'alice@example.com', 'password': 'password123'}).status_code == 201
    response = client.post('/api/v1/auth/login', json={'username': 'alice', 'password': 'password123'})
    return {'Authorization': 'Bearer ' + response.json()['access_token']}


def test_window_latest_and_empty(context):
    """Select latest observations in a bounded calendar window without inventing values."""
    _, factory = context
    with factory() as db:
        result = dashboard(db, datetime.date(2025, 1, 15))
        assert result.window_start == datetime.date(2024, 2, 1)
        assert result.metrics == result.trends == result.budgets == result.insights == []
        db.add_all([
            StrategicMetric(category='business', metric_name='Impact', metric_value=Decimal('1.00'), recorded_date=datetime.date(2024, 1, 31)),
            StrategicMetric(category='business', metric_name='Impact', metric_value=Decimal('2.00'), recorded_date=datetime.date(2024, 2, 1), insight='Earlier'),
            StrategicMetric(category='business', metric_name='Impact', metric_value=Decimal('3.00'), recorded_date=datetime.date(2025, 1, 15), insight='Improved'),
            StrategicMetric(category='business', metric_name='Impact', metric_value=Decimal('9.00'), recorded_date=datetime.date(2025, 1, 16)),
        ])
        db.commit()
        result = dashboard(db, datetime.date(2025, 1, 15))
        assert [x.metric_value for x in result.trends] == [Decimal('2.00'), Decimal('3.00')]
        assert result.metrics[0].metric_value == Decimal('3.00')
        assert [x.insight for x in result.insights] == ['Improved']


def test_authenticated_persistence_and_exports(context):
    """Read committed observations and export matching JSON and safe CSV."""
    client, factory = context
    headers = login(client)
    today = datetime.datetime.now(datetime.timezone.utc).date()
    with factory() as db:
        db.add(StrategicMetric(category='risk', metric_name='=Risk', metric_value=Decimal('25.50'), unit='index', trend='down', change_pct=Decimal('-1.50'), insight='@review, now', recorded_date=today))
        db.add(StrategicBudget(name='Portfolio', month=today.replace(day=1), unit='USD', budget=Decimal('200.00'), actual=Decimal('175.00')))
        db.commit()
    endpoint = '/api/v1/dashboard/strategic-metrics'
    response = client.get(endpoint, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data['metrics'][0]['metric_value'] == '25.50'
    assert data['insights'][0]['insight'] == '@review, now'
    assert data['budgets'][0]['actual'] == '175.00'
    exported = client.get(endpoint + '/export?format=json', headers=headers)
    assert exported.json() == data
    assert 'attachment' in exported.headers['content-disposition']
    exported = client.get(endpoint + '/export?format=csv', headers=headers)
    rows = list(csv.DictReader(io.StringIO(exported.text)))
    assert rows[0]['name'] == "'=Risk" and rows[0]['insight'] == "'@review, now"
    assert rows[1]['budget'] == '200.00' and rows[1]['actual'] == '175.00'
    assert client.get(endpoint + '/export?format=xml', headers=headers).status_code == 422


def test_authentication_empty_and_revocation(context):
    """Require a live token for the metrics and both export formats."""
    client, _ = context
    endpoint = '/api/v1/dashboard/strategic-metrics'
    for path in (endpoint, endpoint + '/export?format=json', endpoint + '/export?format=csv'):
        assert client.get(path).status_code == 401
        assert client.get(path, headers={'Authorization': 'Bearer forged'}).status_code == 401
    headers = login(client)
    assert client.get(endpoint, headers=headers).json()['metrics'] == []
    assert client.post('/api/v1/auth/logout', headers=headers).status_code == 204
    assert client.get(endpoint, headers=headers).status_code == 401
    assert client.get(endpoint + '/export', headers=headers).status_code == 401


def test_database_constraints(context):
    """Enforce category, trend, uniqueness and monthly budget boundaries."""
    _, factory = context
    with factory() as db:
        db.add(StrategicMetric(category='invalid', metric_name='Risk', metric_value=1, recorded_date=datetime.date(2025, 1, 1)))
        with pytest.raises(IntegrityError): db.commit()
        db.rollback()
        db.add(StrategicMetric(category='risk', metric_name='Risk', metric_value=1, trend='sideways', recorded_date=datetime.date(2025, 1, 1)))
        with pytest.raises(IntegrityError): db.commit()
        db.rollback()
        db.add_all([StrategicMetric(category='risk', metric_name='Risk', metric_value=1, recorded_date=datetime.date(2025, 1, 1)), StrategicMetric(category='risk', metric_name='Risk', metric_value=2, recorded_date=datetime.date(2025, 1, 1))])
        with pytest.raises(IntegrityError): db.commit()
        db.rollback()
        db.add(StrategicBudget(name='IT', month=datetime.date(2025, 1, 2), budget=1, actual=1))
        with pytest.raises(IntegrityError): db.commit()
        db.rollback()
