"""Expose public registration and protected session endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import AuthSession, User
from app.schemas.auth import LoginRequest, LoginResponse, Registration, UserProfile
from app.services import auth

router = APIRouter(prefix="/api/v1/auth", tags=["identity"])
bearer = HTTPBearer(auto_error=False)
DB = Annotated[Session, Depends(get_db)]


def current_session(db: DB, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> tuple[User, AuthSession]:
    """Resolve the bearer token to a live session or return 401."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
    return auth.authenticate(db, credentials.credentials)


@router.post("/register", response_model=UserProfile, status_code=201, summary="Register an account")
def register(data: Registration, db: DB) -> User:
    """Create a user without revealing the password hash."""
    return auth.register(db, data)


@router.post("/login", response_model=LoginResponse, summary="Start a session")
def login(data: LoginRequest, db: DB) -> LoginResponse:
    """Authenticate credentials and return a session token."""
    token, user = auth.login(db, data.username, data.password)
    return LoginResponse(access_token=token, user=UserProfile.model_validate(user))


@router.get("/me", response_model=UserProfile, summary="Get the active profile")
def me(identity: Annotated[tuple[User, AuthSession], Depends(current_session)]) -> User:
    """Return the verified current user and role."""
    return identity[0]


@router.post("/logout", status_code=204, summary="Revoke the active session")
def logout(db: DB, identity: Annotated[tuple[User, AuthSession], Depends(current_session)]) -> Response:
    """Invalidate the presented token in the database."""
    auth.logout(db, identity[1])
    return Response(status_code=204)
