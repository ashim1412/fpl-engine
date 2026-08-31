import json
import os
from pathlib import Path

import psycopg
import pytest

from fpl_engine.migrate import apply_migrations

FIXTURES_DIR = Path(__file__).parent / "fixtures"

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get("DATABASE_URL", "postgresql://fpl:fpl@localhost:5432/fpl_engine"),
)

RAW_TABLES = (
    "raw.entry_picks",
    "raw.snapshots",
    "raw.fixtures",
    "raw.players",
    "raw.gameweeks",
    "raw.positions",
    "raw.teams",
)


@pytest.fixture(scope="session", autouse=True)
def _migrated_db():
    apply_migrations(TEST_DATABASE_URL)


@pytest.fixture
def db_conn():
    conn = psycopg.connect(TEST_DATABASE_URL)
    with conn.cursor() as cur:
        cur.execute(f"TRUNCATE {', '.join(RAW_TABLES)} RESTART IDENTITY CASCADE")
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def load_fixture():
    def _load(name: str) -> dict:
        return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))

    return _load
