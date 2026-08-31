"""Pydantic contracts for the FPL API payloads we land into `raw`.

Only the fields ingestion actually lands are modelled here — this is the
parse boundary, not a full mirror of the API. A breaking upstream change to
one of these fields should fail loudly rather than silently landing bad data.
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class Team(BaseModel):
    id: int
    name: str
    short_name: str
    strength: int | None = None
    strength_overall_home: int | None = None
    strength_overall_away: int | None = None
    strength_attack_home: int | None = None
    strength_attack_away: int | None = None
    strength_defence_home: int | None = None
    strength_defence_away: int | None = None


class Position(BaseModel):
    id: int
    singular_name: str
    singular_name_short: str
    plural_name: str
    plural_name_short: str
    squad_min_play: int | None = None
    squad_max_play: int | None = None


class Gameweek(BaseModel):
    id: int
    name: str
    deadline_time: datetime
    finished: bool
    is_previous: bool
    is_current: bool
    is_next: bool
    average_entry_score: int | None = None
    highest_score: int | None = None


class Player(BaseModel):
    id: int
    code: int
    team: int
    element_type: int
    first_name: str
    second_name: str
    web_name: str
    status: str
    now_cost: int
    selected_by_percent: Decimal
    form: Decimal | None = None


class BootstrapPayload(BaseModel):
    teams: list[Team]
    element_types: list[Position]
    events: list[Gameweek]
    elements: list[Player]


class Fixture(BaseModel):
    id: int
    event: int | None = None
    team_h: int
    team_a: int
    team_h_score: int | None = None
    team_a_score: int | None = None
    team_h_difficulty: int | None = None
    team_a_difficulty: int | None = None
    kickoff_time: datetime | None = None
    finished: bool
    stats: list[dict] | None = None


class Pick(BaseModel):
    element: int
    element_type: int
    position: int
    multiplier: int
    is_captain: bool
    is_vice_captain: bool


class EntryPicksPayload(BaseModel):
    active_chip: str | None = None
    entry_history: dict
    picks: list[Pick]
