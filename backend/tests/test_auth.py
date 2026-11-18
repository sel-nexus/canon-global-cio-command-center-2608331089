"""Exercise identity endpoints against a dedicated PostgreSQL database."""
import os
from datetime import datetime, timedelta, timezone

import bcrypt
import pytest
from jose import jwt
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.models.user import AuthSession, User

TEST_URL = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://canon:canon-dev-only@localhost:5432/canon_cio_test")


@pytest.fixture()
def client(isolated_context):
    """Use the per-test isolated PostgreSQL schema."""
    return isolated_context


def test_registration_persistence_and_duplicate_constraints(client):
    """Store a bcrypt hash and reject duplicate usernames and normalized emails."""
    http, factory = client
    payload = {"username": "alice", "email": "Alice@example.com", "password": "password123"}
    response = http.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    assert response.json()["role"] == "executive"
    assert "password_hash" not in response.json()
    with factory() as db:
        user = db.scalar(select(User).where(User.username == "alice"))
        assert user.email == "alice@example.com"
        assert user.password_hash.startswith("$2b$12$")
        assert bcrypt.checkpw(b"password123", user.password_hash.encode())
    assert http.post("/api/v1/auth/register", json={**payload, "email": "other@example.com"}).status_code == 409
    assert http.post("/api/v1/auth/register", json={**payload, "username": "other"}).status_code == 409


@pytest.mark.parametrize("payload", [
    {"username": "ab", "email": "a@example.com", "password": "password123"},
    {"username": "alice", "email": "bad", "password": "password123"},
    {"username": "alice", "email": "a@example.com", "password": "short"},
    {"username": "alice", "email": "a@example.com", "password": "é" * 40},
    {"username": "alice", "email": "a@example.com"},
])
def test_registration_validation(client, payload):
    """Reject invalid input and bcrypt byte overflow as validation errors."""
    assert client[0].post("/api/v1/auth/register", json=payload).status_code == 422


@pytest.mark.parametrize("missing_field", ["username", "email", "password"])
def test_registration_missing_required_field_does_not_create_user(client, missing_field):
    """Reject each missing registration field without writing an account."""
    http, factory = client
    payload = {"username": "alice", "email": "alice@example.com", "password": "password123"}
    del payload[missing_field]
    response = http.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    assert any(error["loc"] == ["body", missing_field] and error["type"] == "missing" for error in response.json()["detail"])
    with factory() as db:
        assert db.scalars(select(User)).all() == []


@pytest.mark.parametrize("field", ["username", "email", "password"])
@pytest.mark.parametrize("value", [None, 123, True, [], {}], ids=["null", "number", "boolean", "array", "object"])
def test_registration_null_or_wrong_type_preserves_users(client, field, value):
    """Reject invalid fields and leave existing accounts and sessions unchanged."""
    http, factory = client
    registered = http.post("/api/v1/auth/register", json={
        "username": "alice", "email": "alice@example.com", "password": "password123",
    })
    assert registered.status_code == 201
    with factory() as db:
        before = db.execute(select(User.id, User.username, User.email, User.password_hash, User.role, User.is_active, User.created_at, User.updated_at)).all()
        sessions_before = db.execute(select(AuthSession.id, AuthSession.user_id, AuthSession.expires_at, AuthSession.revoked_at, AuthSession.created_at)).all()
    payload = {"username": "bob", "email": "bob@example.com", "password": "password123", field: value}
    response = http.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    assert any(error["loc"] == ["body", field] for error in response.json()["detail"])
    with factory() as db:
        assert db.execute(select(User.id, User.username, User.email, User.password_hash, User.role, User.is_active, User.created_at, User.updated_at)).all() == before
        assert db.execute(select(AuthSession.id, AuthSession.user_id, AuthSession.expires_at, AuthSession.revoked_at, AuthSession.created_at)).all() == sessions_before


@pytest.mark.parametrize("field,value", [
    ("username", None), ("password", None),
    ("username", 123), ("password", 123),
    ("username", True), ("password", False),
    ("username", {"name": "alice"}), ("password", ["password123"]),
    ("username", ""), ("password", ""),
    ("username", "x" * 51), ("password", "x" * 73),
])
def test_login_invalid_fields_rejected_without_session(client, field, value):
    """Reject null, wrong-type, empty and oversized login credentials."""
    http, factory = client
    payload = {"username": "alice", "password": "password123", field: value}
    response = http.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 422
    assert any(error["loc"] == ["body", field] for error in response.json()["detail"])
    assert "access_token" not in response.json()
    with factory() as db:
        assert db.scalars(select(AuthSession)).all() == []


@pytest.mark.parametrize("missing_field", ["username", "password"])
def test_login_missing_required_field_does_not_create_session(client, missing_field):
    """Require both login fields rather than issuing a session."""
    http, factory = client
    payload = {"username": "alice", "password": "password123"}
    del payload[missing_field]
    response = http.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 422
    assert any(error["loc"] == ["body", missing_field] and error["type"] == "missing" for error in response.json()["detail"])
    assert "access_token" not in response.json()
    with factory() as db:
        assert db.scalars(select(AuthSession)).all() == []


@pytest.mark.parametrize("field,value", [
    ("username", "u" * 51),
    ("email", "a" * 64 + "@" + "b" * 35 + ".com"),
    ("password", "p" * 73),
])
def test_registration_oversized_field_does_not_create_user(client, field, value):
    """Enforce registration limits before persisting oversized values."""
    http, factory = client
    payload = {"username": "alice", "email": "alice@example.com", "password": "password123", field: value}
    response = http.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    assert any(error["loc"] == ["body", field] for error in response.json()["detail"])
    with factory() as db:
        assert db.scalars(select(User)).all() == []


@pytest.mark.parametrize("credentials", [
    {"username": "' OR '1'='1' --", "password": "password123"},
    {"username": "alice", "password": "' OR '1'='1' --"},
    {"username": "alice'; DROP TABLE users; --", "password": "password123"},
])
def test_login_sql_injection_cannot_authenticate_or_change_data(client, credentials):
    """Treat SQL metacharacters as credentials, never as executable SQL."""
    http, factory = client
    registered = http.post("/api/v1/auth/register", json={"username": "alice", "email": "alice@example.com", "password": "password123"})
    assert registered.status_code == 201
    response = http.post("/api/v1/auth/login", json=credentials)
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password"}
    assert "access_token" not in response.json()
    with factory() as db:
        users = db.scalars(select(User)).all()
        assert [(user.username, user.email) for user in users] == [("alice", "alice@example.com")]
        assert db.scalars(select(AuthSession)).all() == []
    legitimate = http.post("/api/v1/auth/login", json={"username": "alice", "password": "password123"})
    assert legitimate.status_code == 200
    assert legitimate.json()["user"]["username"] == "alice"


@pytest.mark.parametrize("field,value", [
    ("username", "<script>alert(1)</script>"),
    ("email", "<script>alert(1)</script>@example.com"),
])
def test_registration_xss_payload_rejected_and_not_persisted(client, field, value):
    """Reject markup in public profile fields and preserve existing data."""
    http, factory = client
    registered = http.post("/api/v1/auth/register", json={"username": "alice", "email": "alice@example.com", "password": "password123"})
    assert registered.status_code == 201
    payload = {"username": "bob", "email": "bob@example.com", "password": "password123", field: value}
    response = http.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    assert any(error["loc"] == ["body", field] for error in response.json()["detail"])
    with factory() as db:
        users = db.scalars(select(User)).all()
        assert [(user.username, user.email) for user in users] == [("alice", "alice@example.com")]


def test_login_me_logout_and_independent_sessions(client):
    """Revoke only the presented token and enforce authentication on both routes."""
    http, factory = client
    assert http.post("/api/v1/auth/register", json={"username": "alice", "email": "alice@example.com", "password": "password123"}).status_code == 201
    assert http.post("/api/v1/auth/login", json={"username": "alice", "password": "wrong"}).status_code == 401
    assert http.post("/api/v1/auth/login", json={"username": "unknown", "password": "password123"}).status_code == 401
    first = http.post("/api/v1/auth/login", json={"username": "alice", "password": "password123"})
    second = http.post("/api/v1/auth/login", json={"username": "alice", "password": "password123"})
    assert first.status_code == second.status_code == 200
    assert first.json()["user"]["permissions"] == []
    headers = {"Authorization": "Bearer " + first.json()["access_token"]}
    me = http.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["username"] == "alice"
    assert http.get("/api/v1/auth/me").status_code == 401
    assert http.post("/api/v1/auth/logout").status_code == 401
    assert http.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert http.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert http.post("/api/v1/auth/logout", headers=headers).status_code == 401
    assert http.get("/api/v1/auth/me", headers={"Authorization": "Bearer " + second.json()["access_token"]}).status_code == 200
    with factory() as db:
        assert sum(s.revoked_at is not None for s in db.scalars(select(AuthSession)).all()) == 1


def test_expired_tampered_and_inactive_tokens(client):
    """Reject expired and forged tokens and immediately honor inactive accounts."""
    http, factory = client
    assert http.post("/api/v1/auth/register", json={"username": "alice", "email": "alice@example.com", "password": "password123"}).status_code == 201
    response = http.post("/api/v1/auth/login", json={"username": "alice", "password": "password123"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    claims = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    claims["exp"] = datetime.now(timezone.utc) - timedelta(seconds=1)
    expired = jwt.encode(claims, settings.jwt_secret, algorithm="HS256")
    for bad in [expired, token + "x", "garbage"]:
        assert http.get("/api/v1/auth/me", headers={"Authorization": "Bearer " + bad}).status_code == 401
    with factory() as db:
        db.scalar(select(User)).is_active = False
        db.commit()
    assert http.get("/api/v1/auth/me", headers={"Authorization": "Bearer " + token}).status_code == 401
    assert http.post("/api/v1/auth/login", json={"username": "alice", "password": "password123"}).status_code == 401


def test_password_helpers():
    """Check bcrypt cost and reject invalid or oversized credentials."""
    hashed = hash_password("password123")
    assert hashed.startswith("$2b$12$")
    assert verify_password("password123", hashed)
    assert not verify_password("wrong", hashed)
    assert not verify_password("é" * 40, hashed)
    assert not verify_password("password123", "invalid")
