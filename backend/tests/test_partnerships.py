"""Exercise supplier data and authentication against disposable PostgreSQL."""
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models.partnerships import PartnerPerformance, PartnerQuarter


@pytest.fixture()
def context(isolated_context):
    """Use the per-test isolated PostgreSQL schema."""
    return isolated_context


def login(client):
    """Create an authenticated identity through the real API."""
    assert client.post('/api/v1/auth/register', json={'username': 'alice', 'email': 'alice@example.com', 'password': 'password123'}).status_code == 201
    response = client.post('/api/v1/auth/login', json={'username': 'alice', 'password': 'password123'})
    assert response.status_code == 200
    return {'Authorization': 'Bearer ' + response.json()['access_token']}


def partner(name='Supplier A'):
    """Create a complete source-supplied supplier assessment."""
    return PartnerPerformance(vendor_name=name, sla_compliance_pct=Decimal('98.25'), roi_multiple=Decimal('1.25'), delivery_score=Decimal('88.50'), annual_spend=Decimal('1234.50'), currency='USD', contract_status='Review', review_quarter='2025 Q2', innovation_output='Two pilots')


def test_auth_empty_and_session_revocation(context):
    """Reject missing, forged and revoked sessions and report empty data."""
    client, _ = context
    path = '/api/v1/partnerships'
    assert client.get(path).status_code == 401
    assert client.get(path, headers={'Authorization': 'Bearer forged'}).status_code == 401
    headers = login(client)
    response = client.get(path, headers=headers)
    assert response.status_code == 200
    assert response.json() == {'partners': [], 'total': 0}
    assert client.post('/api/v1/auth/logout', headers=headers).status_code == 204
    assert client.get(path, headers=headers).status_code == 401


def test_persisted_assessments_history_and_bounds(context):
    """Return persisted, ordered history with nulls and independently reported values."""
    client, factory = context
    headers = login(client)
    with factory() as db:
        first = partner()
        second = partner('Supplier B')
        db.add_all([first, second])
        db.flush()
        db.add_all([
            PartnerQuarter(partner_id=first.id, year=2024, quarter=4, spend=10, verified_savings=9, roi_multiple=2, currency='USD'),
            PartnerQuarter(partner_id=first.id, year=2025, quarter=1, spend=0, verified_savings=None, roi_multiple=Decimal('-0.25'), currency='EUR'),
            PartnerQuarter(partner_id=first.id, year=2025, quarter=2, spend=15, verified_savings=50, roi_multiple=None, currency='USD'),
        ])
        db.commit()
    response = client.get('/api/v1/partnerships?limit=1&history_limit=2', headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert result['total'] == 2
    row = result['partners'][0]
    assert (row['vendor_name'], row['sla_compliance_pct'], row['innovation_output'], row['delivery_score'], row['annual_spend']) == ('Supplier A', '98.25', 'Two pilots', '88.50', '1234.50')
    assert row['history_total'] == 3
    assert [(r['year'], r['quarter']) for r in row['history']] == [(2025, 1), (2025, 2)]
    assert row['history'][0]['spend'] == '0.00' and row['history'][0]['verified_savings'] is None
    assert row['history'][0]['currency'] == 'EUR' and row['history'][0]['roi_multiple'] == '-0.25'
    assert row['history'][1]['verified_savings'] == '50.00' and row['history'][1]['roi_multiple'] is None
    response = client.get('/api/v1/partnerships?limit=1&offset=1', headers=headers)
    assert response.status_code == 200
    assert response.json()['partners'][0]['history'] == []
    for query in ['limit=0', 'limit=101', 'offset=-1', 'history_limit=0', 'history_limit=101']:
        assert client.get('/api/v1/partnerships?' + query, headers=headers).status_code == 422
    with factory() as db:
        db.get(PartnerPerformance, row['id']).contract_status = 'Renewed'
        db.commit()
    response = client.get('/api/v1/partnerships', headers=headers)
    assert response.status_code == 200
    assert response.json()['partners'][0]['contract_status'] == 'Renewed'


def test_constraints_and_cascade(context):
    """Enforce periods, uniqueness, foreign keys and deletion of history."""
    _, factory = context
    with factory() as db:
        record = partner()
        db.add(record)
        db.flush()
        partner_id = record.id
        db.add(PartnerQuarter(partner_id=partner_id, year=2025, quarter=1, currency='USD'))
        db.commit()
        invalid = [partner(), PartnerQuarter(partner_id=partner_id, year=2025, quarter=1, currency='USD'), PartnerQuarter(partner_id=partner_id, year=2025, quarter=5, currency='USD'), PartnerQuarter(partner_id=partner_id, year=2025, quarter=2, currency='USD', spend=-1), PartnerQuarter(partner_id=99999, year=2025, quarter=1, currency='USD'), PartnerQuarter(partner_id=partner_id, year=2025, quarter=2, currency=' ')]
        invalid_partner = partner('Invalid SLA')
        invalid_partner.sla_compliance_pct = 101
        invalid.append(invalid_partner)
        for row in invalid:
            db.add(row)
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()
        db.delete(db.get(PartnerPerformance, partner_id))
        db.commit()
        assert db.execute(text('SELECT count(*) FROM partner_quarters')).scalar_one() == 0


@pytest.mark.parametrize('table,column', [('partner_performance', 'vendor_name'), ('partner_quarters', 'currency')])
def test_not_null_violation_rolls_back_partner_transaction(context, table, column):
    """PostgreSQL rejects nulls and rolls back earlier writes in the transaction."""
    _, factory = context
    with factory() as db:
        existing = partner('Committed supplier')
        db.add(existing)
        db.commit()
        partner_id = existing.id

        db.add(partner('Pending supplier'))
        db.flush()
        if table == 'partner_performance':
            invalid = partner(None)
        else:
            invalid = PartnerQuarter(partner_id=partner_id, year=2025, quarter=1, currency=None)
        db.add(invalid)
        with pytest.raises(IntegrityError) as error:
            db.flush()
        assert error.value.orig.sqlstate == '23502'
        assert error.value.orig.diag.column_name == column
        db.rollback()

        names = db.execute(text('SELECT vendor_name FROM partner_performance ORDER BY vendor_name')).scalars().all()
        assert names == ['Committed supplier']
        assert db.execute(text('SELECT count(*) FROM partner_quarters')).scalar_one() == 0
