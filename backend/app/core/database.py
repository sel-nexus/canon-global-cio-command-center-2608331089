"""Provide pooled database sessions without connecting at import time."""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """Collect mapped application tables."""


engine = create_engine(settings.application_url, pool_size=5, max_overflow=15, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Yield a session and always return its connection to the pool."""
    with SessionLocal() as session:
        yield session
