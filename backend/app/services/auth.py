"""Implement account creation and database-backed token lifecycle."""
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_token, decode_token, expiry, hash_password, verify_password
from app.models.user import AuthSession, User
from app.schemas.auth import Registration


def register(db: Session, data: Registration) -> User:
    """Persist a new account and map database uniqueness races to conflict."""
    user = User(username=data.username, email=str(data.email), password_hash=hash_password(data.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username or email already registered") from exc
    db.refresh(user)
    return user


def login(db: Session, username: str, password: str) -> tuple[str, User]:
    """Verify credentials and create a new independent persistent session."""
    user = db.scalar(select(User).where(User.username == username))
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password", headers={"WWW-Authenticate": "Bearer"})
    session = AuthSession(id=str(uuid4()), user_id=user.id, expires_at=expiry())
    db.add(session)
    db.commit()
    return create_token(user.id, session.id, session.expires_at), user


def authenticate(db: Session, token: str) -> tuple[User, AuthSession]:
    """Reject invalid, expired, revoked, missing, or inactive sessions."""
    claims = decode_token(token)
    if claims and claims["sub"].isdigit():
        result = db.execute(select(User, AuthSession).join(AuthSession, AuthSession.user_id == User.id).where(
            User.id == int(claims["sub"]), User.is_active.is_(True), AuthSession.id == claims["jti"],
            AuthSession.revoked_at.is_(None), AuthSession.expires_at > datetime.now(timezone.utc),
        )).first()
        if result:
            return result[0], result[1]
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session", headers={"WWW-Authenticate": "Bearer"})


def logout(db: Session, session: AuthSession) -> None:
    """Revoke the presented session without affecting other logins."""
    session.revoked_at = datetime.now(timezone.utc)
    db.commit()
