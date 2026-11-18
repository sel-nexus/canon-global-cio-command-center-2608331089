"""Exercise assistant authentication, context and provider boundaries on PostgreSQL."""
import json
import os
from datetime import date

import httpx
from httpx import Client as HTTPClient
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.strategic import StrategicMetric
from app.models.partnerships import PartnerPerformance, PartnerQuarter


@pytest.fixture()
def context(monkeypatch):
    """Migrate and isolate a disposable test database."""
    url = make_url(os.environ['TEST_DATABASE_URL'])
    if not url.drivername.startswith('postgresql') or not url.database or 'test' not in url.database.lower() or url == settings.application_url:
        raise RuntimeError('TEST_DATABASE_URL must name a separate PostgreSQL test database')
    config = Config('alembic.ini')
    config.attributes['database_url'] = url
    command.upgrade(config, 'head')
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text('TRUNCATE strategic_metrics, business_quarters, partner_quarters, partner_performance, auth_sessions, users RESTART IDENTITY CASCADE'))
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override():
        """Yield a test database session."""
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override
    monkeypatch.setattr(settings, 'ai_enabled', False)
    with TestClient(app) as client:
        yield client, factory
    app.dependency_overrides.clear()
    engine.dispose()


def login(client):
    """Create a real session through the identity API."""
    assert client.post('/api/v1/auth/register', json={'username': 'alice', 'email': 'alice@example.com', 'password': 'password123'}).status_code == 201
    token = client.post('/api/v1/auth/login', json={'username': 'alice', 'password': 'password123'}).json()['access_token']
    return {'Authorization': f'Bearer {token}'}


def enable(monkeypatch, handler):
    """Enable a test provider and intercept only its HTTP transport."""
    monkeypatch.setattr(settings, 'ai_enabled', True)
    monkeypatch.setattr(settings, 'ai_endpoint', 'https://provider.example/v1/chat/completions')
    monkeypatch.setattr(settings, 'ai_model', 'test-model')
    monkeypatch.setattr(settings, 'ai_api_key', 'provider-key')
    monkeypatch.setattr('app.services.ai.httpx.Client', lambda **kwargs: HTTPClient(transport=httpx.MockTransport(handler), **kwargs))


def response(content):
    """Wrap structured provider text in the expected chat completion shape."""
    return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps(content)}}]})


def test_auth_validation_unconfigured_and_revocation(context):
    """Fail closed for unauthenticated, invalid, unavailable and revoked requests."""
    client, _ = context
    path = '/api/v1/ai/chat'
    body = {'query': 'Review', 'context_tab': 'strategic'}
    assert client.get('/api/v1/ai/recommendations').status_code == 401
    assert client.post(path, json=body).status_code == 401
    headers = login(client)
    recommendations = client.get('/api/v1/ai/recommendations?context_tab=operations', headers=headers)
    assert recommendations.status_code == 200 and recommendations.json()[0]['context_tab'] == 'operations'
    assert client.get('/api/v1/ai/recommendations?context_tab=bad', headers=headers).status_code == 422
    assert client.post(path, headers=headers, json=body).status_code == 503
    for bad in [{'query': ' ', 'context_tab': 'strategic'}, {'query': 'x' * 1001, 'context_tab': 'strategic'}, {'query': 'x', 'context_tab': 'bad'}, {'query': 'x'}, {**body, 'extra': 1}]:
        assert client.post(path, headers=headers, json=bad).status_code == 422
    assert client.post('/api/v1/auth/logout', headers=headers).status_code == 204
    assert client.post(path, headers=headers, json=body).status_code == 401


def test_persisted_context_is_bounded_and_private(context, monkeypatch):
    """Use stored selected-tab values while excluding identity and free text."""
    client, factory = context
    headers = login(client)
    with factory() as db:
        db.add_all([StrategicMetric(category='business', metric_name=f'private-name-{i}', metric_value=i, recorded_date=date(2025, 1, i + 1), insight='private insight') for i in range(12)])
        db.commit()
    captured = []

    def handler(request):
        captured.append(json.loads(request.content))
        assert request.headers['authorization'] == 'Bearer provider-key'
        return response({'narrative': 'Review the data.', 'actions': ['Investigate'], 'confidence': None})

    enable(monkeypatch, handler)
    result = client.post('/api/v1/ai/chat', headers=headers, json={'query': 'Review', 'context_tab': 'strategic'})
    assert result.status_code == 200
    assert result.json()['actions'] == ['Investigate'] and result.json()['confidence'] is None
    assert 'did not supply' in result.json()['limitations'][-1]
    sent = json.loads(captured[0]['messages'][1]['content'])
    assert len(sent['records']) == 10 and sent['records'][0]['metric_value'] == '11.00'
    assert 'private' not in json.dumps(sent) and 'alice' not in json.dumps(sent) and 'password' not in json.dumps(sent)
    assert 'provider-key' not in json.dumps(captured[0])


def test_partner_history_and_empty_data(context, monkeypatch):
    """Send only limited anonymous partner and quarterly numeric evidence."""
    client, factory = context
    headers = login(client)
    with factory() as db:
        row = PartnerPerformance(vendor_name='Secret vendor', sla_compliance_pct=98, roi_multiple=2, delivery_score=90, annual_spend=100, currency='USD', contract_status='Secret', review_quarter='2025 Q1')
        db.add(row)
        db.flush()
        db.add_all([PartnerQuarter(partner_id=row.id, year=2024, quarter=q, spend=q, currency='USD') for q in range(1, 5)])
        db.commit()
    captured = []
    def handler(request):
        captured.append(json.loads(json.loads(request.content)['messages'][1]['content']))
        return response({'narrative': 'Evidence is limited.', 'actions': [], 'confidence': 'provider estimate'})
    enable(monkeypatch, handler)
    result = client.post('/api/v1/ai/chat', headers=headers, json={'query': 'Review', 'context_tab': 'partnerships'})
    assert result.status_code == 200 and result.json()['confidence'] == 'provider estimate'
    assert len(captured[0]['records'][0]['history']) == 4 and 'Secret' not in json.dumps(captured[0])
    empty = client.post('/api/v1/ai/chat', headers=headers, json={'query': 'Review', 'context_tab': 'business'})
    assert empty.status_code == 200 and any('No persisted' in item for item in empty.json()['limitations'])


def test_provider_failures_and_credential_guard(context, monkeypatch):
    """Reject credentials, insecure configuration and malformed or failed provider responses."""
    client, _ = context
    headers = login(client)
    body = {'query': 'Review', 'context_tab': 'strategic'}
    enable(monkeypatch, lambda request: httpx.Response(500, text='sensitive upstream error'))
    assert client.post('/api/v1/ai/chat', headers=headers, json={**body, 'query': 'password=secret'}).status_code == 422
    failure = client.post('/api/v1/ai/chat', headers=headers, json=body)
    assert failure.status_code == 502 and 'sensitive' not in failure.text
    monkeypatch.setattr(settings, 'ai_endpoint', 'http://provider.example')
    assert client.post('/api/v1/ai/chat', headers=headers, json=body).status_code == 503
    monkeypatch.setattr(settings, 'ai_endpoint', 'https://provider.example')
    enable(monkeypatch, lambda request: response({'narrative': 'x', 'actions': 'not a list'}))
    assert client.post('/api/v1/ai/chat', headers=headers, json=body).status_code == 502
