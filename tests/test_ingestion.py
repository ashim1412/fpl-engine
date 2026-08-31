import httpx
import respx

from fpl_engine.ingestion.common.db import new_batch_id
from fpl_engine.ingestion.fpl import loaders
from fpl_engine.ingestion.fpl.client import BASE_URL, FplClient
from fpl_engine.ingestion.fpl.models import BootstrapPayload, EntryPicksPayload, Fixture


def test_bootstrap_payload_parses(load_fixture):
    payload = BootstrapPayload.model_validate(load_fixture("bootstrap.json"))
    assert len(payload.elements) == 6
    assert payload.elements[0].selected_by_percent > 0
    assert any(event.is_current for event in payload.events)


def test_fixtures_payload_parses(load_fixture):
    fixtures = [Fixture.model_validate(item) for item in load_fixture("fixtures.json")]
    assert len(fixtures) == 3
    assert fixtures[0].stats is not None


def test_entry_picks_payload_parses(load_fixture):
    payload = EntryPicksPayload.model_validate(load_fixture("picks.json"))
    assert len(payload.picks) == 4
    assert payload.entry_history["event"] == 1


@respx.mock
def test_client_retries_on_transient_error_then_succeeds(load_fixture):
    route = respx.get(f"{BASE_URL}/bootstrap-static/")
    route.side_effect = [
        httpx.Response(500),
        httpx.Response(200, json=load_fixture("bootstrap.json")),
    ]

    with FplClient() as client:
        payload = client.get_bootstrap()

    assert route.call_count == 2
    assert len(payload.elements) == 6


def _snapshot_counts(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM raw.players")
        players = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM raw.teams")
        teams = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM raw.snapshots")
        snapshots = cur.fetchone()[0]
        cur.execute("SELECT count(DISTINCT batch_id) FROM raw.snapshots")
        batches = cur.fetchone()[0]
    return players, teams, snapshots, batches


def test_load_bootstrap_is_idempotent(db_conn, load_fixture):
    payload = BootstrapPayload.model_validate(load_fixture("bootstrap.json"))

    loaders.load_bootstrap(db_conn, payload, new_batch_id())
    db_conn.commit()
    players_1, teams_1, snapshots_1, batches_1 = _snapshot_counts(db_conn)

    loaders.load_bootstrap(db_conn, payload, new_batch_id())
    db_conn.commit()
    players_2, teams_2, snapshots_2, batches_2 = _snapshot_counts(db_conn)

    assert players_2 == players_1 == len(payload.elements)
    assert teams_2 == teams_1
    assert snapshots_2 == snapshots_1 + len(payload.elements)
    assert batches_2 == batches_1 + 1


def test_load_fixtures_is_idempotent(db_conn, load_fixture):
    payload = BootstrapPayload.model_validate(load_fixture("bootstrap.json"))
    loaders.load_bootstrap(db_conn, payload, new_batch_id())

    fixtures = [Fixture.model_validate(item) for item in load_fixture("fixtures.json")]
    loaders.load_fixtures(db_conn, fixtures, new_batch_id())
    db_conn.commit()

    with db_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM raw.fixtures")
        count_1 = cur.fetchone()[0]

    loaders.load_fixtures(db_conn, fixtures, new_batch_id())
    db_conn.commit()

    with db_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM raw.fixtures")
        count_2 = cur.fetchone()[0]

    assert count_1 == count_2 == len(fixtures)


def test_load_entry_picks_is_idempotent(db_conn, load_fixture):
    payload = BootstrapPayload.model_validate(load_fixture("bootstrap.json"))
    loaders.load_bootstrap(db_conn, payload, new_batch_id())
    db_conn.commit()

    picks_payload = EntryPicksPayload.model_validate(load_fixture("picks.json"))
    loaders.load_entry_picks(
        db_conn, entry_id=1, event_id=1, payload=picks_payload, batch_id=new_batch_id()
    )
    db_conn.commit()

    with db_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM raw.entry_picks")
        count_1 = cur.fetchone()[0]

    loaders.load_entry_picks(
        db_conn, entry_id=1, event_id=1, payload=picks_payload, batch_id=new_batch_id()
    )
    db_conn.commit()

    with db_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM raw.entry_picks")
        count_2 = cur.fetchone()[0]

    assert count_1 == count_2 == len(picks_payload.picks)
