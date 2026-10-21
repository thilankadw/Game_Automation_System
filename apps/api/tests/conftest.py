"""Test configuration and shared fixtures."""

import os
import sqlite3
import tempfile
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

API_DIR = Path(__file__).resolve().parents[1]
_TMP_DIR = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
_DB_PATH = Path(_TMP_DIR.name) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB_PATH.as_posix()}"

from app.db import engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def dispose_engine() -> Iterator[None]:
    """Dispose the database engine and remove the temporary database."""
    yield
    engine.sync_engine.dispose()
    _TMP_DIR.cleanup()


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    """Provide a test client backed by a migrated temporary database."""
    config = Config(str(API_DIR / "alembic.ini"))
    command.upgrade(config, "head")
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clear_tables(client: TestClient) -> Iterator[None]:
    """Remove ROI, game, and provider rows after each test."""
    yield
    with closing(sqlite3.connect(_DB_PATH)) as connection:
        connection.execute("DELETE FROM rois")
        connection.execute("DELETE FROM roi_sets")
        connection.execute("DELETE FROM games")
        connection.execute("DELETE FROM game_providers")
        connection.commit()
