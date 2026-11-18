"""Shared PostgreSQL isolation for feature tests."""
import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import get_db
from app.main import app


@pytest.fixture()
def isolated_context(request):
    """Migrate and drop only a fresh schema belonging to this test."""
    raw_url = os.environ.get('TEST_DATABASE_URL') or getattr(request.module, 'TEST_URL', None)
    if not raw_url:
        raise RuntimeError('Set TEST_DATABASE_URL to a dedicated PostgreSQL test database')
    url = make_url(raw_url)
    if (not url.drivername.startswith('postgresql') or not url.database
            or 'test' not in url.database.lower()
            or url.database == settings.application_url.database):
        raise RuntimeError('TEST_DATABASE_URL must name a separate PostgreSQL test database')
    if url.drivername == 'postgresql':
        url = url.set(drivername='postgresql+psycopg')

    schema = 'feature_' + uuid4().hex
    admin_engine = create_engine(url)
    test_engine = None
    schema_created = False
    previous_override = app.dependency_overrides.get(get_db)
    try:
        with admin_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        schema_created = True
        schema_url = url.update_query_dict({'options': f'-csearch_path={schema}'})
        backend = Path(__file__).resolve().parents[1]
        config = Config(str(backend / 'alembic.ini'))
        config.set_main_option('script_location', str(backend / 'alembic'))
        config.attributes['database_url'] = schema_url
        command.upgrade(config, 'head')
        test_engine = create_engine(schema_url)
        factory = sessionmaker(bind=test_engine, expire_on_commit=False)

        def override():
            """Provide a session bound to this test's schema."""
            with factory() as db:
                yield db

        app.dependency_overrides[get_db] = override
        with TestClient(app) as client:
            yield client, factory
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_override
        if test_engine is not None:
            test_engine.dispose()
        try:
            if schema_created:
                with admin_engine.begin() as connection:
                    connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        finally:
            admin_engine.dispose()
