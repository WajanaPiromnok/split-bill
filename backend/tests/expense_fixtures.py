"""Isolated PostgreSQL fixtures for tests that commit expense transactions."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from alembic import command
from splitbill.app import create_app
from splitbill.seed import seed_database

BACKEND_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def expense_database_url():
    raw_url = os.environ.get("TEST_DATABASE_URL")
    if not raw_url:
        raise pytest.UsageError("Set TEST_DATABASE_URL to a PostgreSQL 16 test database")
    admin = create_engine(raw_url)
    schema = f"splitbill_test_{uuid4().hex}"
    with admin.begin() as connection:
        version = int(connection.exec_driver_sql("SHOW server_version_num").scalar_one())
        if not 160000 <= version < 170000:
            raise pytest.UsageError("Expense integration tests require PostgreSQL 16")
        connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
    scoped_url = make_url(raw_url).update_query_dict({"options": f"-csearch_path={schema}"})
    try:
        yield scoped_url.render_as_string(hide_password=False)
    finally:
        with admin.begin() as connection:
            connection.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
        admin.dispose()


@pytest.fixture
def expense_engine(expense_database_url):
    engine = create_engine(expense_database_url)
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    with Session(engine) as session, session.begin():
        seed_database(session)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def expense_client(expense_database_url, expense_engine):
    with TestClient(create_app(expense_database_url), raise_server_exceptions=False) as client:
        yield client
