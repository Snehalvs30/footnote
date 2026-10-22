"""Shared setup for integration tests: a real PostgreSQL, real migrations, the real app.

Testcontainers starts a throwaway pgvector container once per test run (it needs
Docker running) and deletes it afterwards. The app's get_session dependency is
pointed at that database, so every request in these tests hits real SQL.
"""

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.community.postgres import PostgresContainer

from app.db import get_session
from app.main import app

BACKEND = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    with PostgresContainer("pgvector/pgvector:pg17", driver="psycopg") as postgres:
        engine = create_engine(postgres.get_connection_url())
        _migrate(engine)
        yield engine
        engine.dispose()


def _migrate(engine: Engine) -> None:
    """Runs the real Alembic migrations, so tests check the schema users actually get."""
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "migrations"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


@pytest.fixture(scope="session", autouse=True)
def use_test_database(engine: Engine) -> Iterator[None]:
    TestSession = sessionmaker(bind=engine, expire_on_commit=False)

    def get_test_session() -> Iterator[Session]:
        with TestSession() as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def make_client() -> Callable[[], TestClient]:
    """Each client keeps its own cookies, like a separate browser. Use one per user.

    base_url ends in /api/, so tests can write "/documents" for "/api/documents".
    """
    return lambda: TestClient(app, base_url="http://testserver/api/")