"""Exercise remaining feature-to-assistant flows against isolated PostgreSQL schemas.

Run from backend with TEST_DATABASE_URL set to a separate test database:
pytest tests/test_context_integration.py -v
"""
import json
from datetime import date, datetime, timezone
from decimal import Decimal

import httpx
import pytest

from app.models.business import BusinessQuarter
from app.models.governance import InnovationQuarter, RiskObservation
from app.models.operations import OperationsHistory
from app.models.regional import RegionalPerformance
from test_integration import configure_provider, integration_context


@pytest.mark.parametrize(
    'tab,path,model,seed,collection,api_values,evidence',
    [
        pytest.param(
            'executive-summary', '/api/v1/metrics/regional-performance', RegionalPerformance,
            {'region': 'Private region', 'health_score': Decimal('68.25'),
             'availability_pct': Decimal('99.70'), 'security_score': Decimal('73.10'),
             'transformation_index': Decimal('54.50'), 'status': 'Warning',
             'updated_at': datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)},
            'regions',
            {'region': 'Private region', 'health_score': '68.25', 'availability_pct': '99.70',
             'security_score': '73.10', 'transformation_index': '54.50', 'status': 'Warning'},
            {'health_score': '68.25', 'availability_pct': '99.70', 'security_score': '73.10',
             'transformation_index': '54.50', 'status': 'Warning',
             'updated_at': '2025-01-02 03:04:05+00:00'},
            id='regional',
        ),
        pytest.param(
            'business', '/api/v1/business/impact', BusinessQuarter,
            {'year': 2025, 'quarter': 2, 'investment_m': Decimal('10.50'),
             'revenue_attribution_m': Decimal('19.25'), 'cost_avoidance_m': Decimal('3.00'),
             'operational_cost_savings_m': None, 'transformation_roi_pct': Decimal('-5.25')},
            'quarters',
            {'year': 2025, 'quarter': 2, 'investment_m': '10.50',
             'revenue_attribution_m': '19.25', 'cost_avoidance_m': '3.00',
             'operational_cost_savings_m': None, 'transformation_roi_pct': '-5.25'},
            {'year': '2025', 'quarter': '2', 'investment_m': '10.50',
             'revenue_attribution_m': '19.25', 'cost_avoidance_m': '3.00',
             'operational_cost_savings_m': None, 'transformation_roi_pct': '-5.25'},
            id='business',
        ),
        pytest.param(
            'operations', '/api/v1/operations/summary', OperationsHistory,
            {'recorded_date': date(2025, 1, 3), 'mttr_minutes': Decimal('12.50'),
             'sla_compliance_pct': Decimal('99.50'), 'uptime_pct': Decimal('99.99'),
             'incident_volume': 4, 'resolution_count': 2, 'p1_volume': 1, 'p2_volume': 0},
            'latest',
            {'recorded_date': '2025-01-03', 'mttr_minutes': '12.50',
             'sla_compliance_pct': '99.50', 'uptime_pct': '99.99', 'incident_volume': 4,
             'resolution_count': 2, 'p1_volume': 1, 'p2_volume': 0},
            {'recorded_date': '2025-01-03', 'mttr_minutes': '12.50',
             'sla_compliance_pct': '99.50', 'uptime_pct': '99.99', 'incident_volume': '4',
             'resolution_count': '2', 'p1_volume': '1', 'p2_volume': '0'},
            id='operations',
        ),
        pytest.param(
            'governance', '/api/v1/governance/risk-overview', RiskObservation,
            {'recorded_date': date(2025, 1, 4), 'compliance_pct': Decimal('92.75'),
             'nist_maturity': 'Private maturity', 'privacy_audit_status': 'Private audit'},
            'latest',
            {'recorded_date': '2025-01-04', 'compliance_pct': '92.75',
             'nist_maturity': 'Private maturity', 'privacy_audit_status': 'Private audit'},
            {'recorded_date': '2025-01-04', 'compliance_pct': '92.75'},
            id='governance',
        ),
        pytest.param(
            'innovation', '/api/v1/governance/innovation', InnovationQuarter,
            {'year': 2025, 'quarter': 1, 'deployed_models': 0,
             'patent_disclosures': 3, 'innovation_index': Decimal('64.25')},
            'latest',
            {'year': 2025, 'quarter': 1, 'deployed_models': 0,
             'patent_disclosures': 3, 'innovation_index': '64.25'},
            {'year': '2025', 'quarter': '1', 'deployed_models': '0',
             'patent_disclosures': '3', 'innovation_index': '64.25'},
            id='innovation',
        ),
    ],
)
def test_feature_evidence_reaches_assistant_provider(
    integration_context, monkeypatch, tab, path, model, seed, collection, api_values, evidence,
):
    """Read a persisted feature observation, then verify its safe assistant evidence."""
    client, factory = integration_context
    assert client.post('/api/v1/auth/register', json={
        'username': 'contextuser', 'email': 'contextuser@example.com', 'password': 'password123',
    }).status_code == 201
    login = client.post('/api/v1/auth/login', json={
        'username': 'contextuser', 'password': 'password123',
    })
    assert login.status_code == 200
    headers = {'Authorization': 'Bearer ' + login.json()['access_token']}

    with factory() as db:
        db.add(model(**seed))
        db.commit()

    feature = client.get(path, headers=headers)
    assert feature.status_code == 200
    row = feature.json()[collection]
    if isinstance(row, list):
        assert len(row) == 1
        row = row[0]
    assert row is not None
    assert {key: row[key] for key in api_values} == api_values
    if tab == 'executive-summary':
        assert datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00')) == seed['updated_at']

    captured = []

    def provider(request):
        assert request.headers['authorization'] == 'Bearer integration-provider-key'
        captured.append(json.loads(json.loads(request.content)['messages'][1]['content']))
        return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps({
            'narrative': 'Review the evidence.', 'actions': ['Investigate'], 'confidence': None,
        })}}]})

    configure_provider(monkeypatch, provider)
    chat = client.post('/api/v1/ai/chat', headers=headers, json={
        'query': 'Review the evidence', 'context_tab': tab,
    })
    assert chat.status_code == 200
    assert chat.json()['narrative'] == 'Review the evidence.'
    assert chat.json()['actions'] == ['Investigate']
    assert captured == [{'question': 'Review the evidence', 'context_tab': tab, 'records': [evidence]}]
    assert 'Private' not in json.dumps(captured)
