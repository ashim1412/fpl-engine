from datetime import UTC, datetime, timedelta

import dagster as dg

from fpl_engine.config.settings import get_settings
from fpl_engine.ingestion.common.db import get_connection, new_batch_id
from fpl_engine.ingestion.fpl import loaders
from fpl_engine.ingestion.fpl.client import FplClient


@dg.asset
def raw_fpl_bootstrap() -> dg.MaterializeResult:
    batch_id = new_batch_id()
    with FplClient() as client:
        payload = client.get_bootstrap()
    with get_connection() as conn:
        loaders.load_bootstrap(conn, payload, batch_id)
        conn.commit()
    return dg.MaterializeResult(metadata={"batch_id": batch_id, "players": len(payload.elements)})


@dg.asset
def raw_fpl_fixtures() -> dg.MaterializeResult:
    batch_id = new_batch_id()
    with FplClient() as client:
        fixtures = client.get_fixtures()
    with get_connection() as conn:
        loaders.load_fixtures(conn, fixtures, batch_id)
        conn.commit()
    return dg.MaterializeResult(metadata={"batch_id": batch_id, "fixtures": len(fixtures)})


@dg.asset(deps=[raw_fpl_bootstrap])
def raw_fpl_entry_picks() -> dg.MaterializeResult:
    """Land the configured entry's picks for the current/next gameweek.

    Depends on raw_fpl_bootstrap only for freshness of raw.gameweeks — reads
    the deadline it needs from the warehouse rather than passing data
    in-memory between assets.
    """
    settings = get_settings()
    if settings.fpl_entry_id is None:
        raise dg.Failure("FPL_ENTRY_ID is not configured; skipping entry picks ingestion")

    batch_id = new_batch_id()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT event_id FROM raw.gameweeks"
                " WHERE is_current OR is_next"
                " ORDER BY is_current DESC, event_id"
                " LIMIT 1"
            )
            row = cur.fetchone()
        if row is None:
            raise dg.Failure(
                "No current/next gameweek in raw.gameweeks; run raw_fpl_bootstrap first"
            )
        event_id = row[0]

        with FplClient() as client:
            payload = client.get_entry_picks(settings.fpl_entry_id, event_id)
        loaders.load_entry_picks(conn, settings.fpl_entry_id, event_id, payload, batch_id)
        conn.commit()

    return dg.MaterializeResult(metadata={"batch_id": batch_id, "event_id": event_id})


daily_ingest_job = dg.define_asset_job(
    "daily_ingest_job",
    selection=[raw_fpl_bootstrap, raw_fpl_fixtures, raw_fpl_entry_picks],
)

daily_ingest_schedule = dg.ScheduleDefinition(
    job=daily_ingest_job,
    cron_schedule="0 6 * * *",
)


@dg.sensor(job=daily_ingest_job, minimum_interval_seconds=3600)
def pre_deadline_sensor(context: dg.SensorEvaluationContext):
    """Fire hourly, but only inside the 24h window before the next deadline."""
    settings = get_settings()
    if not settings.database_url:
        return dg.SkipReason("DATABASE_URL is not set")

    now = datetime.now(UTC)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT deadline_time FROM raw.gameweeks"
            " WHERE deadline_time > %s"
            " ORDER BY deadline_time LIMIT 1",
            (now,),
        )
        row = cur.fetchone()

    if row is None:
        return dg.SkipReason("no upcoming deadline found in raw.gameweeks")

    deadline = row[0]
    if deadline - now > timedelta(hours=24):
        return dg.SkipReason(f"next deadline {deadline.isoformat()} is more than 24h away")

    return dg.RunRequest(run_key=f"pre-deadline-{deadline.isoformat()}")


defs = dg.Definitions(
    assets=[raw_fpl_bootstrap, raw_fpl_fixtures, raw_fpl_entry_picks],
    jobs=[daily_ingest_job],
    schedules=[daily_ingest_schedule],
    sensors=[pre_deadline_sensor],
)
