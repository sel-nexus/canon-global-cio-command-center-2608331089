"""Exercise identity endpoints against a dedicated PostgreSQL database."""
import os
from datetime import datetime, timedelta, timezone

import bcrypt
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_password, verify_password
from app.main import app
from app.models.user import AuthSession, User

TEST_URL = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://canon:canon-dev-only@localhost:5432/canon_cio_test")


@pytest.fixture()
def client():
    """Migrate and clear only the explicitly dedicated test database."""
    url = make_url(TEST_URL)
    if not url.drivername.startswith("postgresql") or not url.database or "test" not in url.database.lower() or url == settings.application_url:
        raise RuntimeError("TEST_DATABASE_URL must name a separate PostgreSQL test database")
    config = Config("alembic.ini")
    config.attributes["database_url"] = url
    command.upgrade(config, "head")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE auth_sessions, users RESTART IDENTITY CASCADE"))
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override():
        """Supply an isolated session to each request."""
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override
    with TestClient(app) as test_client:
        yield test_client, factory
    app.dependency_overrides.clear()
    engine.dispose()


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


def test_login_me_logout_and_independent_sessions(client):
    """Revoke only the presented token and enforce authentication on both routes."""
    http, factory = client
    http.post("/api/v1/auth/register", json={"username": "alice", "email": "alice@example.com", "password": "password123"})
    assert http.post("/api/v1/auth/login", json={"username": "alice", "password": "wrong"}).status_code == 401
    assert http.post("/api/v1/auth/login", json={"username": "unknown", "password": "password123"}).status_code == 401
    first = http.post("/api/v1/auth/login", json={"username": "alice", "password": "password123"})
    second = http.post("/api/v1/auth/login", json={"username": "alice", "password": "password123"})
    assert first.status_code == second.status_code == 200
    assert first.json()["user"]["permissions"] == []
    headers = {"Authorization": "Bearer " + first.json()["access_token"]}
    assert http.get("/api/v1/auth/me", headers=headers).json()["username"] == "alice"
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
    http.post("/api/v1/auth/register", json={"username": "alice", "email": "alice@example.com", "password": "password123"})
    token = http.post("/api/v1/auth/login", json={"username": "alice", "password": "password123"}).json()["access_token"]
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
