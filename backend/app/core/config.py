"""Load runtime configuration from the environment."""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url


class Settings(BaseSettings):
    """Describe deployment-specific database and authentication settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://canon:canon-dev-only@localhost:5432/postgres"
    db_name: str = "canon_cio"
    jwt_secret: str = "dev-secret-change-in-production-at-least-32-characters"
    access_token_minutes: int = Field(default=60, gt=0)
    cors_origins: str = "http://localhost:5173"

    @property
    def application_url(self) -> URL:
        """Compose the target database URL without logging credentials."""
        return make_url(self.database_url).set(database=self.db_name)


settings = Settings()
