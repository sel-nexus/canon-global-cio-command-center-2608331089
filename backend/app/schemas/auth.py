"""Define and validate the public identity API contract."""
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class Registration(BaseModel):
    """Accept validated registration details."""
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        """Normalize email for consistent duplicate detection."""
        value = str(value).lower()
        if len(value) > 100:
            raise ValueError("Email must be at most 100 characters")
        return value

    @field_validator("password")
    @classmethod
    def limit_password_bytes(cls, value: str) -> str:
        """Reject passwords that bcrypt cannot represent without truncation."""
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes")
        return value


class LoginRequest(BaseModel):
    """Accept credentials for an existing account."""
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=72)


class UserProfile(BaseModel):
    """Expose only public account fields and currently defined permissions."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: EmailStr
    role: str
    permissions: list[str] = Field(default_factory=list)


class LoginResponse(BaseModel):
    """Return the bearer token and verified account profile."""
    access_token: str
    token_type: str = "bearer"
    user: UserProfile
