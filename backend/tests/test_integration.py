"""Cross-feature HTTP journeys backed by a dedicated PostgreSQL test database.

Set TEST_DATABASE_URL to a separate PostgreSQL database whose name contains
"test". Each test creates and drops only its own uniquely named schema.
Run from the backend directory: pytest tests/test_integration.py -v.
Strategic and partnership data are source-fed and have no write API, so the
fixtures insert those records directly before exercising their read APIs.
"""
import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from httpx import Client as HTTPClient
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.partnerships import PartnerPerformance, PartnerQuarter
from app.models.strategic import StrategicMetric
from app.models.user import AuthSession, User


@pytest.fixture()
def integration_context():
    """Migrate an isolated schema without truncating any existing tables."""
    raw_url = os.environ.get('TEST_DATABASE_URL')
    if not raw_url:
        raise RuntimeError('Set TEST_DATABASE_URL to a dedicated PostgreSQL test database')
    url = make_url(raw_url)
    if (not url.drivername.startswith('postgresql') or not url.database
            or 'test' not in url.database.lower()
            or url.database == settings.application_url.database):
        raise RuntimeError('TEST_DATABASE_URL must name a separate PostgreSQL test database')
    if url.drivername == 'postgresql':
        url = url.set(drivername='postgresql+psycopg')
    schema = 'integration_' + uuid4().hex
    admin_engine = create_engine(url)
    schema_created = False
    test_engine = None
    previous_override = app.dependency_overrides.get(get_db)
    try:
        with admin_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        schema_created = True
        schema_url = url.update_query_dict({'options': f'-csearch_path={schema}'})
        backend = Path(__file__).resolve().parents[1]
        config = Config(str(backend / 'alembic.ini'))
        config.set_main_option('script_location', str(backend / 'alembic'))
        config.attributes['database_url'] = schema_url
        command.upgrade(config, 'head')
        test_engine = create_engine(schema_url)
        factory = sessionmaker(bind=test_engine, expire_on_commit=False)

        def override():
            """Provide a real PostgreSQL session for each application request."""
            with factory() as db:
                yield db

        app.dependency_overrides[get_db] = override
        with TestClient(app) as client:
            yield client, factory
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_override
        if test_engine is not None:
            test_engine.dispose()
        try:
            if schema_created:
                with admin_engine.begin() as connection:
                    connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        finally:
            admin_engine.dispose()


def configure_provider(monkeypatch, handler):
    """Intercept only the external provider HTTP transport."""
    monkeypatch.setattr(settings, 'ai_enabled', True)
    monkeypatch.setattr(settings, 'ai_endpoint', 'https://provider.example/v1/chat/completions')
    monkeypatch.setattr(settings, 'ai_model', 'integration-model')
    monkeypatch.setattr(settings, 'ai_api_key', 'integration-provider-key')
    monkeypatch.setattr(
        'app.services.ai.httpx.Client',
        lambda **kwargs: HTTPClient(transport=httpx.MockTransport(handler), **kwargs),
    )


def assert_no_orphans(db):
    """Check the two actual child-to-parent relationships after the journey."""
    assert db.scalar(select(func.count()).select_from(AuthSession).outerjoin(
        User, AuthSession.user_id == User.id
    ).where(User.id.is_(None))) == 0
    assert db.scalar(select(func.count()).select_from(PartnerQuarter).outerjoin(
        PartnerPerformance, PartnerQuarter.partner_id == PartnerPerformance.id
    ).where(PartnerPerformance.id.is_(None))) == 0


def test_auth_features_and_ai_share_persisted_context_and_revocation(integration_context, monkeypatch):
    """Read source data across three routers, then revoke only one session."""
    client, factory = integration_context
    registered = client.post('/api/v1/auth/register', json={
        'username': 'integration', 'email': 'integration@example.com', 'password': 'password123',
    })
    assert registered.status_code == 201
    user_id = registered.json()['id']
    login = client.post('/api/v1/auth/login', json={'username': 'integration', 'password': 'password123'})
    second_login = client.post('/api/v1/auth/login', json={'username': 'integration', 'password': 'password123'})
    assert login.status_code == second_login.status_code == 200
    assert login.json()['user']['id'] == user_id
    first_headers = {'Authorization': 'Bearer ' + login.json()['access_token']}
    second_headers = {'Authorization': 'Bearer ' + second_login.json()['access_token']}
    today = datetime.now(timezone.utc).date()
    with factory() as db:
        db.add(StrategicMetric(
            category='risk', metric_name='Confidential metric', metric_value=Decimal('42.50'),
            trend='down', change_pct=Decimal('-3.25'), insight='Private insight', recorded_date=today,
        ))
        partner = PartnerPerformance(
            vendor_name='Confidential supplier', sla_compliance_pct=Decimal('98.25'),
            roi_multiple=Decimal('1.25'), delivery_score=Decimal('88.50'),
            annual_spend=Decimal('1234.50'), currency='USD', contract_status='Review',
            review_quarter='2025 Q2', innovation_output='Private project',
        )
        db.add(partner)
        db.flush()
        partner_id = partner.id
        db.add(PartnerQuarter(
            partner_id=partner_id, year=2025, quarter=2, spend=Decimal('300.00'),
            verified_savings=Decimal('40.00'), roi_multiple=Decimal('1.50'), currency='USD',
        ))
        db.commit()

    strategic = client.get('/api/v1/dashboard/strategic-metrics', headers=first_headers)
    partners = client.get('/api/v1/partnerships', headers=first_headers)
    assert strategic.status_code == partners.status_code == 200
    assert strategic.json()['metrics'][0]['metric_value'] == '42.50'
    assert strategic.json()['metrics'][0]['metric_name'] == 'Confidential metric'
    partner_record = partners.json()['partners'][0]
    assert partners.json()['total'] == 1
    assert partner_record['id'] == partner_id
    assert partner_record['vendor_name'] == 'Confidential supplier'
    assert partner_record['history_total'] == 1
    assert partner_record['history'][0]['spend'] == '300.00'

    captured = []

    def provider(request):
        assert request.headers['authorization'] == 'Bearer integration-provider-key'
        captured.append(json.loads(json.loads(request.content)['messages'][1]['content']))
        return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps({
            'narrative': 'Review the source data.', 'actions': ['Investigate'], 'confidence': None,
        })}}]})

    configure_provider(monkeypatch, provider)
    for tab in ('strategic', 'partnerships'):
        result = client.post('/api/v1/ai/chat', headers=first_headers, json={
            'query': 'Review the evidence', 'context_tab': tab,
        })
        assert result.status_code == 200
        assert result.json()['narrative'] == 'Review the source data.'
        assert result.json()['actions'] == ['Investigate']
    assert [payload['context_tab'] for payload in captured] == ['strategic', 'partnerships']
    assert captured[0]['records'] == [{
        'category': 'risk', 'metric_value': '42.50', 'trend': 'down',
        'change_pct': '-3.25', 'recorded_date': today.isoformat(),
    }]
    assert captured[1]['records'] == [{
        'sla_compliance_pct': '98.25', 'roi_multiple': '1.25', 'delivery_score': '88.50',
        'annual_spend': '1234.50', 'history': [{
            'year': '2025', 'quarter': '2', 'spend': '300.00',
            'verified_savings': '40.00', 'roi_multiple': '1.50',
        }],
    }]
    for private in ('Confidential', 'Private', 'integration@example.com', 'password123', 'USD'):
        assert private not in json.dumps(captured)

    assert client.post('/api/v1/auth/logout', headers=first_headers).status_code == 204
    for path in ('/api/v1/auth/me', '/api/v1/dashboard/strategic-metrics',
                 '/api/v1/dashboard/strategic-metrics/export', '/api/v1/partnerships',
                 '/api/v1/ai/recommendations'):
        assert client.get(path, headers=first_headers).status_code == 401
    assert client.post('/api/v1/ai/chat', headers=first_headers, json={
        'query': 'Review the evidence', 'context_tab': 'strategic',
    }).status_code == 401
    assert len(captured) == 2
    assert client.get('/api/v1/partnerships', headers=second_headers).status_code == 200
    assert client.get('/api/v1/dashboard/strategic-metrics', headers=second_headers).status_code == 200
    with factory() as db:
        users = db.scalars(select(User)).all()
        sessions = db.scalars(select(AuthSession)).all()
        assert len(users) == 1 and users[0].id == user_id
        assert len(sessions) == 2 and all(session.user_id == user_id for session in sessions)
        assert sum(session.revoked_at is not None for session in sessions) == 1
        assert db.scalar(select(func.count()).select_from(StrategicMetric)) == 1
        assert db.scalar(select(func.count()).select_from(PartnerPerformance)) == 1
        quarter = db.scalar(select(PartnerQuarter))
        assert quarter.partner_id == partner_id and quarter.spend == Decimal('300.00')
        assert_no_orphans(db)


def test_provider_failure_preserves_source_data_and_live_session(integration_context, monkeypatch):
    """A failed downstream provider must not corrupt data or invalidate identity."""
    client, factory = integration_context
    assert client.post('/api/v1/auth/register', json={
        'username': 'failurecase', 'email': 'failurecase@example.com', 'password': 'password123',
    }).status_code == 201
    login = client.post('/api/v1/auth/login', json={'username': 'failurecase', 'password': 'password123'})
    assert login.status_code == 200
    headers = {'Authorization': 'Bearer ' + login.json()['access_token']}
    with factory() as db:
        db.add(StrategicMetric(category='business', metric_name='Stable', metric_value=Decimal('17.00'),
                               recorded_date=datetime.now(timezone.utc).date()))
        partner = PartnerPerformance(vendor_name='Stable supplier', sla_compliance_pct=Decimal('91.00'),
                                     roi_multiple=Decimal('2.00'), delivery_score=Decimal('85.00'),
                                     annual_spend=Decimal('900.00'), currency='USD',
                                     contract_status='Active', review_quarter='2025 Q1')
        db.add(partner)
        db.flush()
        partner_id = partner.id
        db.add(PartnerQuarter(partner_id=partner_id, year=2025, quarter=1,
                              spend=Decimal('100.00'), currency='USD'))
        db.commit()
    before_strategic = client.get('/api/v1/dashboard/strategic-metrics', headers=headers)
    before_partners = client.get('/api/v1/partnerships', headers=headers)
    assert before_strategic.status_code == before_partners.status_code == 200
    sent = []

    def failing_provider(request):
        sent.append(json.loads(json.loads(request.content)['messages'][1]['content']))
        return httpx.Response(500, text='sensitive provider failure')

    configure_provider(monkeypatch, failing_provider)
    failure = client.post('/api/v1/ai/chat', headers=headers, json={
        'query': 'Review the evidence', 'context_tab': 'partnerships',
    })
    assert failure.status_code == 502
    assert failure.json()['detail'] == 'AI provider response unavailable or invalid.'
    assert 'sensitive provider failure' not in failure.text
    assert sent[0]['records'][0]['annual_spend'] == '900.00'
    assert sent[0]['records'][0]['history'][0]['spend'] == '100.00'
    after_strategic = client.get('/api/v1/dashboard/strategic-metrics', headers=headers)
    after_partners = client.get('/api/v1/partnerships', headers=headers)
    assert after_strategic.status_code == after_partners.status_code == 200
    assert after_strategic.json() == before_strategic.json()
    assert after_partners.json() == before_partners.json()
    assert client.get('/api/v1/auth/me', headers=headers).status_code == 200
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 1
        session = db.scalar(select(AuthSession))
        assert session is not None and session.revoked_at is None
        assert db.scalar(select(StrategicMetric)).metric_value == Decimal('17.00')
        assert db.scalar(select(PartnerPerformance)).annual_spend == Decimal('900.00')
        quarter = db.scalar(select(PartnerQuarter))
        assert quarter.partner_id == partner_id and quarter.spend == Decimal('100.00')
        assert_no_orphans(db)


def test_empty_feature_data_reaches_ai_without_fabricated_evidence(integration_context, monkeypatch):
    """Empty persisted data stays empty through feature and contextual APIs."""
    client, factory = integration_context
    assert client.post('/api/v1/auth/register', json={
        'username': 'emptycase', 'email': 'emptycase@example.com', 'password': 'password123',
    }).status_code == 201
    login = client.post('/api/v1/auth/login', json={'username': 'emptycase', 'password': 'password123'})
    assert login.status_code == 200
    headers = {'Authorization': 'Bearer ' + login.json()['access_token']}
    partners = client.get('/api/v1/partnerships', headers=headers)
    assert partners.status_code == 200
    assert partners.json() == {'partners': [], 'total': 0}
    captured = []

    def provider(request):
        captured.append(json.loads(json.loads(request.content)['messages'][1]['content']))
        return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps({
            'narrative': 'No partner data available.', 'actions': [], 'confidence': None,
        })}}]})

    configure_provider(monkeypatch, provider)
    result = client.post('/api/v1/ai/chat', headers=headers, json={
        'query': 'Review the evidence', 'context_tab': 'partnerships',
    })
    assert result.status_code == 200
    assert captured[0]['records'] == []
    assert any('No persisted records' in limitation for limitation in result.json()['limitations'])
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(PartnerPerformance)) == 0
        assert db.scalar(select(func.count()).select_from(PartnerQuarter)) == 0
        assert_no_orphans(db)
