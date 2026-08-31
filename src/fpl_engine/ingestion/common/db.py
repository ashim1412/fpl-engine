import uuid
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from typing import Any

import psycopg
from psycopg import sql

from fpl_engine.config.settings import get_settings


def get_connection(database_url: str | None = None) -> psycopg.Connection:
    """Open a connection to the warehouse. Caller owns commit/rollback/close."""
    url = database_url or get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg.connect(url)


def new_batch_id() -> str:
    """One batch_id per ingest run, shared across every row it lands."""
    return str(uuid.uuid4())


def with_lineage(
    rows: Iterable[dict[str, Any]], source: str, batch_id: str
) -> list[dict[str, Any]]:
    """Stamp each row with the lineage columns required on every raw table."""
    loaded_at = datetime.now(UTC)
    return [{**row, "source": source, "loaded_at": loaded_at, "batch_id": batch_id} for row in rows]


def bulk_upsert(
    conn: psycopg.Connection,
    table: str,
    rows: Sequence[dict[str, Any]],
    key_columns: Sequence[str],
) -> None:
    """Upsert rows into `schema.table` on `key_columns` (INSERT ... ON CONFLICT DO UPDATE)."""
    if not rows:
        return

    columns = list(rows[0].keys())
    update_columns = [c for c in columns if c not in key_columns]

    query = sql.SQL(
        "INSERT INTO {table} ({cols}) VALUES ({vals}) ON CONFLICT ({keys}) DO {action}"
    ).format(
        table=sql.Identifier(*table.split(".")),
        cols=sql.SQL(", ").join(sql.Identifier(c) for c in columns),
        vals=sql.SQL(", ").join(sql.Placeholder(c) for c in columns),
        keys=sql.SQL(", ").join(sql.Identifier(c) for c in key_columns),
        action=(
            sql.SQL("UPDATE SET {sets}").format(
                sets=sql.SQL(", ").join(
                    sql.SQL("{c} = EXCLUDED.{c}").format(c=sql.Identifier(c))
                    for c in update_columns
                )
            )
            if update_columns
            else sql.SQL("NOTHING")
        ),
    )

    with conn.cursor() as cur:
        cur.executemany(query, rows)


def append_rows(conn: psycopg.Connection, table: str, rows: Sequence[dict[str, Any]]) -> None:
    """Plain append, no conflict handling — for append-only tables like raw.snapshots."""
    if not rows:
        return

    columns = list(rows[0].keys())
    query = sql.SQL("INSERT INTO {table} ({cols}) VALUES ({vals})").format(
        table=sql.Identifier(*table.split(".")),
        cols=sql.SQL(", ").join(sql.Identifier(c) for c in columns),
        vals=sql.SQL(", ").join(sql.Placeholder(c) for c in columns),
    )

    with conn.cursor() as cur:
        cur.executemany(query, rows)
