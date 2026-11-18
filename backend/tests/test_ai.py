"""Exercise assistant authentication, context and provider boundaries on PostgreSQL."""
import json
from datetime import date, datetime, timezone

import httpx
from httpx import Client as HTTPClient
import pytest

from app.core.config import Settings, settings
from app.models.strategic import StrategicMetric
from app.models.partnerships import PartnerPerformance, PartnerQuarter
from app.models.business import BusinessQuarter
from app.models.governance import InnovationQuarter, RiskObservation
from app.models.operations import OperationsHistory
from app.models.regional import RegionalPerformance


@pytest.fixture()
def context(isolated_context, monkeypatch):
    """Disable the provider for each isolated test by default."""
    monkeypatch.setattr(settings, 'ai_enabled', False)
    monkeypatch.setattr(settings, 'ai_mock_enabled', False)
    return isolated_context


def login(client):
    """Create a real session through the identity API."""
    assert client.post('/api/v1/auth/register', json={'username': 'alice', 'email': 'alice@example.com', 'password': 'password123'}).status_code == 201
    response = client.post('/api/v1/auth/login', json={'username': 'alice', 'password': 'password123'})
    assert response.status_code == 200
    token = response.json()['access_token']
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


def test_mock_flag_requires_opt_in(monkeypatch):
    """Default to provider behavior unless the environment explicitly enables mock mode."""
    monkeypatch.delenv('AI_MOCK_ENABLED', raising=False)
    assert Settings(_env_file=None).ai_mock_enabled is False
    monkeypatch.setenv('AI_MOCK_ENABLED', 'true')
    assert Settings(_env_file=None).ai_mock_enabled is True
    monkeypatch.setenv('AI_MOCK_ENABLED', 'false')
    assert Settings(_env_file=None).ai_mock_enabled is False


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
    assert result.json()['source'] == 'provider'
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


@pytest.mark.parametrize('action', ['', '   ', 'x' * 501], ids=['empty', 'whitespace', 'overlong'])
def test_provider_rejects_invalid_action(context, monkeypatch, action):
    """Reject blank or oversized actions in otherwise valid provider output."""
    client, _ = context
    headers = login(client)
    enable(monkeypatch, lambda request: response({'narrative': 'Analysis', 'actions': [action], 'confidence': None}))
    result = client.post('/api/v1/ai/chat', headers=headers, json={'query': 'Review', 'context_tab': 'strategic'})
    assert result.status_code == 502
    assert result.json() == {'detail': 'AI provider response unavailable or invalid.'}


def test_provider_transport_timeout_returns_502(context, monkeypatch):
    """Convert a provider transport timeout into a sanitized gateway error."""
    client, _ = context
    headers = login(client)

    def timeout(request):
        raise httpx.ReadTimeout('sensitive provider timeout', request=request)

    enable(monkeypatch, timeout)
    result = client.post('/api/v1/ai/chat', headers=headers, json={'query': 'Review', 'context_tab': 'strategic'})
    assert result.status_code == 502
    assert result.json() == {'detail': 'AI provider response unavailable or invalid.'}
    assert 'sensitive' not in result.text


@pytest.mark.parametrize('body', [
    {}, {'context_tab': 'strategic'}, {'query': None, 'context_tab': 'strategic'},
    {'query': 123, 'context_tab': 'strategic'}, {'query': [], 'context_tab': 'strategic'},
    {'query': '', 'context_tab': 'strategic'}, {'query': 'Review', 'context_tab': None},
    {'query': 'Review', 'context_tab': 123}, {'query': 'Review', 'context_tab': []},
])
def test_chat_rejects_missing_and_wrong_type_fields(context, body):
    """Validate the public request contract before invoking the provider."""
    client, _ = context
    result = client.post('/api/v1/ai/chat', headers=login(client), json=body)
    assert result.status_code == 422


def test_provider_rejects_oversized_response_and_malformed_endpoint(context, monkeypatch):
    """Fail closed for a response over the byte limit and an invalid URL."""
    client, _ = context
    headers = login(client)
    body = {'query': 'Review', 'context_tab': 'strategic'}
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, content=b'x' * 65537)

    enable(monkeypatch, handler)
    result = client.post('/api/v1/ai/chat', headers=headers, json=body)
    assert result.status_code == 502
    assert result.json()['detail'] == 'AI provider response unavailable or invalid.'
    assert len(calls) == 1
    monkeypatch.setattr(settings, 'ai_endpoint', 'https://[invalid')
    result = client.post('/api/v1/ai/chat', headers=headers, json=body)
    assert result.status_code == 503
    assert result.json()['detail'] == 'AI provider is not configured or approved.'
    assert len(calls) == 1


def test_each_tab_sends_only_its_persisted_evidence(context, monkeypatch):
    """Check every tab's selected records and protect omitted private fields."""
    client, factory = context
    headers = login(client)
    with factory() as db:
        db.add_all([
            StrategicMetric(category='business', metric_name='private metric', metric_value=11, recorded_date=date(2025, 1, 1)),
            RegionalPerformance(region='private region', health_score=22, availability_pct=99, security_score=88, transformation_index=77, status='Good'),
            BusinessQuarter(year=2025, quarter=1, investment_m=33),
            OperationsHistory(recorded_date=date(2025, 2, 1), incident_volume=44),
            RiskObservation(recorded_date=date(2025, 3, 1), compliance_pct=55, privacy_audit_status='private audit'),
            InnovationQuarter(year=2025, quarter=2, deployed_models=66),
            PartnerPerformance(vendor_name='private vendor', sla_compliance_pct=77, roi_multiple=2, delivery_score=90, annual_spend=100, currency='USD', contract_status='private contract', review_quarter='2025 Q1'),
        ])
        db.commit()
    captured = []

    def handler(request):
        captured.append(json.loads(json.loads(request.content)['messages'][1]['content']))
        return response({'narrative': 'Analysis', 'actions': [], 'confidence': None})

    enable(monkeypatch, handler)
    expected = {
        'strategic': ('metric_value', '11.00'),
        'executive-summary': ('health_score', '22.00'),
        'business': ('investment_m', '33.00'),
        'operations': ('incident_volume', '44'),
        'governance': ('compliance_pct', '55.00'),
        'innovation': ('deployed_models', '66'),
        'partnerships': ('sla_compliance_pct', '77.00'),
    }
    for tab, (field, value) in expected.items():
        recommendation = client.get('/api/v1/ai/recommendations', headers=headers, params={'context_tab': tab})
        assert recommendation.status_code == 200
        assert recommendation.json()[0]['context_tab'] == tab
        result = client.post('/api/v1/ai/chat', headers=headers, json={'query': 'Review', 'context_tab': tab})
        assert result.status_code == 200
        sent = captured[-1]
        assert sent['context_tab'] == tab and sent['question'] == 'Review'
        assert len(sent['records']) == 1 and sent['records'][0][field] == value
        assert 'private' not in json.dumps(sent).lower()


def test_mock_is_deterministic_and_preserves_persisted_dashboard(context, monkeypatch):
    """Return labeled examples without provider calls or changes to stored data."""
    client, factory = context
    monkeypatch.setattr(settings, 'ai_mock_enabled', True)
    monkeypatch.setattr(settings, 'ai_enabled', True)
    monkeypatch.setattr(settings, 'ai_endpoint', 'https://[invalid')
    def no_provider(**kwargs):
        pytest.fail('Mock mode must not create a provider client')
    monkeypatch.setattr('app.services.ai.httpx.Client', no_provider)
    body = {'query': 'Review', 'context_tab': 'strategic'}
    assert client.post('/api/v1/ai/chat', json=body).status_code == 401
    headers = login(client)
    today = datetime.now(timezone.utc).date()
    with factory() as db:
        db.add(StrategicMetric(category='business', metric_name='Stored observation', metric_value=42, recorded_date=today))
        db.commit()
    dashboard = client.get('/api/v1/dashboard/strategic-metrics', headers=headers)
    assert dashboard.status_code == 200 and dashboard.json()['metrics'][0]['metric_value'] == '42.00'
    first = client.post('/api/v1/ai/chat', headers=headers, json=body)
    second = client.post('/api/v1/ai/chat', headers=headers, json={'query': 'Another question', 'context_tab': 'business'})
    assert first.status_code == second.status_code == 200
    result = first.json()
    assert result == second.json() and result['source'] == 'mock'
    assert 'MOCK / synthetic' in result['narrative']
    assert all('MOCK / synthetic' in action for action in result['actions'])
    assert 'MOCK / synthetic' in result['confidence']
    assert any('does not use dashboard data' in item for item in result['limitations'])
    assert '42.00' not in first.text
    dashboard_after = client.get('/api/v1/dashboard/strategic-metrics', headers=headers)
    assert dashboard_after.status_code == 200
    assert dashboard_after.json() == dashboard.json()
    assert client.post('/api/v1/ai/chat', headers=headers, json={**body, 'query': 'password=secret'}).status_code == 422
    assert client.post('/api/v1/ai/chat', headers=headers, json={**body, 'context_tab': 'invalid'}).status_code == 422
    assert client.post('/api/v1/auth/logout', headers=headers).status_code == 204
    assert client.post('/api/v1/ai/chat', headers=headers, json=body).status_code == 401
