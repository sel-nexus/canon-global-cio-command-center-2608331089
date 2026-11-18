"""Run versioned migrations against the configured PostgreSQL database."""
from alembic import context
from sqlalchemy import create_engine

from app.core.config import settings
from app.core.database import Base
from app.models import user  # noqa: F401
from app.models import strategic  # noqa: F401
from app.models import regional  # noqa: F401
from app.models import business  # noqa: F401
from app.models import operations  # noqa: F401
from app.models import governance  # noqa: F401

config = context.config
target_metadata = Base.metadata
url = config.attributes.get("database_url", settings.application_url)


def run_migrations_offline() -> None:
    """Render SQL without opening a database connection."""
    context.configure(url=str(url), target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Apply migrations using a temporary database connection."""
    engine = create_engine(url, pool_pre_ping=True)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
