"""Exercise authenticated operations against a disposable PostgreSQL database."""
import datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.operations import Incident, OperationsHistory


@pytest.fixture()
def context(isolated_context):
    """Use the per-test isolated PostgreSQL schema."""
    return isolated_context


def login(client):
    """Create and authenticate a user through the real identity API."""
    assert client.post('/api/v1/auth/register', json={'username': 'alice', 'email': 'alice@example.com', 'password': 'password123'}).status_code == 201
    response = client.post('/api/v1/auth/login', json={'username': 'alice', 'password': 'password123'})
    assert response.status_code == 200
    return {'Authorization': 'Bearer ' + response.json()['access_token']}


def test_auth_empty_and_revocation(context):
    """Reject invalid sessions and distinguish absent data from zero."""
    client, _ = context
    paths = ['/api/v1/operations/incidents', '/api/v1/operations/summary']
    for path in paths:
        assert client.get(path).status_code == 401
        assert client.get(path, headers={'Authorization': 'Bearer forged'}).status_code == 401
    headers = login(client)
    incidents = client.get(paths[0], headers=headers)
    summary = client.get(paths[1], headers=headers)
    assert incidents.status_code == summary.status_code == 200
    assert incidents.json() == {'incidents': [], 'total': 0}
    assert summary.json() == {'active_counts': None, 'latest': None, 'history': [], 'history_total': 0}
    assert client.post('/api/v1/auth/logout', headers=headers).status_code == 204
    for path in paths:
        assert client.get(path, headers=headers).status_code == 401


def test_stored_data_counts_history_and_pagination(context):
    """Expose committed values without deriving source metrics or filling gaps."""
    client, factory = context
    headers = login(client)
    created = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)
    with factory() as db:
        db.add_all([
            Incident(incident_number='I1', severity='P1', title='Network', status='Open', created_at=created),
            Incident(incident_number='I2', severity='P2', title='Storage', status='Investigating', created_at=created),
            Incident(incident_number='I3', severity='P1', title='Fixed', status='Resolved', created_at=created, resolved_at=created, mttr_minutes=5),
            Incident(incident_number='I4', severity='P4', title='Other', status='Open', created_at=created),
            OperationsHistory(recorded_date=datetime.date(2025, 1, 1), mttr_minutes=Decimal('12.50'), sla_compliance_pct=Decimal('99.50'), uptime_pct=Decimal('99.99'), incident_volume=4, resolution_count=2, p1_volume=1, p2_volume=2),
            OperationsHistory(recorded_date=datetime.date(2025, 1, 2), incident_volume=0, p1_volume=0),
        ])
        db.commit()
    response = client.get('/api/v1/operations/summary', headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert result['active_counts'] == {'P1': 1, 'P2': 1, 'P3': 0}
    assert result['history_total'] == 2
    assert [r['recorded_date'] for r in result['history']] == ['2025-01-01', '2025-01-02']
    assert result['history'][0]['mttr_minutes'] == '12.50'
    assert result['history'][0]['sla_compliance_pct'] == '99.50'
    assert result['history'][0]['uptime_pct'] == '99.99'
    assert result['history'][0]['resolution_count'] == 2
    assert result['latest']['mttr_minutes'] is None and result['latest']['incident_volume'] == 0
    limited = client.get('/api/v1/operations/summary?limit=1', headers=headers)
    assert limited.status_code == 200
    assert limited.json()['history'] == [result['latest']]
    page_response = client.get('/api/v1/operations/incidents?limit=2&offset=1', headers=headers)
    assert page_response.status_code == 200
    page = page_response.json()
    assert page['total'] == 4 and [i['incident_number'] for i in page['incidents']] == ['I3', 'I2']
    for path in ['/api/v1/operations/incidents?limit=0', '/api/v1/operations/incidents?offset=-1', '/api/v1/operations/summary?limit=101']:
        assert client.get(path, headers=headers).status_code == 422
    with factory() as db:
        db.get(Incident, 1).status = 'Investigating'
        db.commit()
    updated = client.get('/api/v1/operations/incidents', headers=headers)
    assert updated.status_code == 200
    assert updated.json()['incidents'][-1]['status'] == 'Investigating'


def test_database_constraints(context):
    """Reject duplicate, invalid, inconsistent, and out-of-range observations."""
    _, factory = context
    with factory() as db:
        db.add(Incident(incident_number='I1', severity='P1', title='Valid', status='Open'))
        db.add(OperationsHistory(recorded_date=datetime.date(2025, 1, 1)))
        db.commit()
        bad = [
            Incident(incident_number='I1', severity='P1', title='Duplicate', status='Open'),
            Incident(incident_number='I2', severity='P5', title='Invalid', status='Open'),
            Incident(incident_number='I2', severity='P1', title=' ', status='Open'),
            Incident(incident_number='I2', severity='P1', title='Invalid', status='Resolved'),
            Incident(incident_number='I2', severity='P1', title='Invalid', status='Open', mttr_minutes=-1),
            OperationsHistory(recorded_date=datetime.date(2025, 1, 1)),
            OperationsHistory(recorded_date=datetime.date(2025, 1, 2), sla_compliance_pct=Decimal('100.01')),
            OperationsHistory(recorded_date=datetime.date(2025, 1, 2), uptime_pct=Decimal('-0.01')),
            OperationsHistory(recorded_date=datetime.date(2025, 1, 2), resolution_count=-1),
        ]
        for row in bad:
            db.add(row)
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()
