"""Hash passwords and sign short-lived session tokens."""
from datetime import datetime, timedelta, timezone
import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Hash an accepted password with bcrypt cost twelve."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    """Check a password without accepting bcrypt's 72-byte truncation."""
    if len(password.encode("utf-8")) > 72:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except (ValueError, UnicodeError):
        return False


def create_token(user_id: int, session_id: str, expires_at: datetime) -> str:
    """Sign a token tied to a persisted session and expiration."""
    return jwt.encode({"sub": str(user_id), "jti": session_id, "exp": expires_at}, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict | None:
    """Return validated claims or fail closed on malformed and expired tokens."""
    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"], options={"require_exp": True, "require_sub": True, "require_jti": True})
        if not isinstance(claims.get("sub"), str) or not isinstance(claims.get("jti"), str):
            return None
        return claims
    except JWTError:
        return None


def expiry() -> datetime:
    """Compute the configured session expiration in UTC."""
    return datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
