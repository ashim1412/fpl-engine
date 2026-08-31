"""Map parsed FPL payloads to raw rows and land them.

Extract-and-load only: no renaming beyond matching column names, no cleaning,
no joins. Reference tables upsert on their natural key; raw.snapshots is
append-only. See ARCHITECTURE.md's "EL is separate from T" principle.
"""

import psycopg
from psycopg.types.json import Jsonb

from fpl_engine.ingestion.common.db import append_rows, bulk_upsert, with_lineage
from fpl_engine.ingestion.fpl.models import BootstrapPayload, EntryPicksPayload, Fixture

SOURCE = "fpl_api"


def _current_gameweek_id(payload: BootstrapPayload) -> int | None:
    for event in payload.events:
        if event.is_current:
            return event.id
    for event in payload.events:
        if event.is_next:
            return event.id
    return None


def load_bootstrap(conn: psycopg.Connection, payload: BootstrapPayload, batch_id: str) -> None:
    teams = with_lineage(
        (
            {
                "team_id": t.id,
                "name": t.name,
                "short_name": t.short_name,
                "strength": t.strength,
                "strength_overall_home": t.strength_overall_home,
                "strength_overall_away": t.strength_overall_away,
                "strength_attack_home": t.strength_attack_home,
                "strength_attack_away": t.strength_attack_away,
                "strength_defence_home": t.strength_defence_home,
                "strength_defence_away": t.strength_defence_away,
            }
            for t in payload.teams
        ),
        SOURCE,
        batch_id,
    )
    bulk_upsert(conn, "raw.teams", teams, key_columns=["team_id"])

    positions = with_lineage(
        (
            {
                "position_id": p.id,
                "singular_name": p.singular_name,
                "singular_name_short": p.singular_name_short,
                "plural_name": p.plural_name,
                "plural_name_short": p.plural_name_short,
                "squad_min_play": p.squad_min_play,
                "squad_max_play": p.squad_max_play,
            }
            for p in payload.element_types
        ),
        SOURCE,
        batch_id,
    )
    bulk_upsert(conn, "raw.positions", positions, key_columns=["position_id"])

    gameweeks = with_lineage(
        (
            {
                "event_id": g.id,
                "name": g.name,
                "deadline_time": g.deadline_time,
                "finished": g.finished,
                "is_previous": g.is_previous,
                "is_current": g.is_current,
                "is_next": g.is_next,
                "average_entry_score": g.average_entry_score,
                "highest_score": g.highest_score,
            }
            for g in payload.events
        ),
        SOURCE,
        batch_id,
    )
    bulk_upsert(conn, "raw.gameweeks", gameweeks, key_columns=["event_id"])

    players = with_lineage(
        (
            {
                "player_id": pl.id,
                "code": pl.code,
                "team_id": pl.team,
                "element_type_id": pl.element_type,
                "first_name": pl.first_name,
                "second_name": pl.second_name,
                "web_name": pl.web_name,
                "status": pl.status,
            }
            for pl in payload.elements
        ),
        SOURCE,
        batch_id,
    )
    bulk_upsert(conn, "raw.players", players, key_columns=["player_id"])

    gw = _current_gameweek_id(payload)
    if gw is not None:
        snapshots = with_lineage(
            (
                {
                    "player_id": pl.id,
                    "gw": gw,
                    "now_cost": pl.now_cost,
                    "selected_by_percent": pl.selected_by_percent,
                    "form": pl.form,
                }
                for pl in payload.elements
            ),
            SOURCE,
            batch_id,
        )
        append_rows(conn, "raw.snapshots", snapshots)


def load_fixtures(conn: psycopg.Connection, fixtures: list[Fixture], batch_id: str) -> None:
    rows = with_lineage(
        (
            {
                "fixture_id": f.id,
                "event_id": f.event,
                "team_h": f.team_h,
                "team_a": f.team_a,
                "team_h_score": f.team_h_score,
                "team_a_score": f.team_a_score,
                "team_h_difficulty": f.team_h_difficulty,
                "team_a_difficulty": f.team_a_difficulty,
                "kickoff_time": f.kickoff_time,
                "finished": f.finished,
                "stats": Jsonb(f.stats) if f.stats is not None else None,
            }
            for f in fixtures
        ),
        SOURCE,
        batch_id,
    )
    bulk_upsert(conn, "raw.fixtures", rows, key_columns=["fixture_id"])


def load_entry_picks(
    conn: psycopg.Connection,
    entry_id: int,
    event_id: int,
    payload: EntryPicksPayload,
    batch_id: str,
) -> None:
    rows = with_lineage(
        (
            {
                "entry_id": entry_id,
                "event_id": event_id,
                "element_id": pick.element,
                "element_type_id": pick.element_type,
                "position": pick.position,
                "multiplier": pick.multiplier,
                "is_captain": pick.is_captain,
                "is_vice_captain": pick.is_vice_captain,
                "active_chip": payload.active_chip,
                "entry_history": Jsonb(payload.entry_history),
            }
            for pick in payload.picks
        ),
        SOURCE,
        batch_id,
    )
    bulk_upsert(conn, "raw.entry_picks", rows, key_columns=["entry_id", "event_id", "element_id"])
