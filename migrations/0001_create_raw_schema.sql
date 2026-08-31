-- depends:

CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE raw.teams (
    team_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    short_name TEXT NOT NULL,
    strength INTEGER,
    strength_overall_home INTEGER,
    strength_overall_away INTEGER,
    strength_attack_home INTEGER,
    strength_attack_away INTEGER,
    strength_defence_home INTEGER,
    strength_defence_away INTEGER,
    source TEXT NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL,
    batch_id UUID NOT NULL
);

CREATE TABLE raw.positions (
    position_id INTEGER PRIMARY KEY,
    singular_name TEXT NOT NULL,
    singular_name_short TEXT NOT NULL,
    plural_name TEXT NOT NULL,
    plural_name_short TEXT NOT NULL,
    squad_min_play INTEGER,
    squad_max_play INTEGER,
    source TEXT NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL,
    batch_id UUID NOT NULL
);

CREATE TABLE raw.gameweeks (
    event_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    deadline_time TIMESTAMPTZ NOT NULL,
    finished BOOLEAN NOT NULL,
    is_previous BOOLEAN NOT NULL,
    is_current BOOLEAN NOT NULL,
    is_next BOOLEAN NOT NULL,
    average_entry_score INTEGER,
    highest_score INTEGER,
    source TEXT NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL,
    batch_id UUID NOT NULL
);

CREATE TABLE raw.players (
    player_id INTEGER PRIMARY KEY,
    code INTEGER NOT NULL,
    team_id INTEGER NOT NULL REFERENCES raw.teams (team_id),
    element_type_id INTEGER NOT NULL REFERENCES raw.positions (position_id),
    first_name TEXT NOT NULL,
    second_name TEXT NOT NULL,
    web_name TEXT NOT NULL,
    status TEXT NOT NULL,
    source TEXT NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL,
    batch_id UUID NOT NULL
);

CREATE TABLE raw.fixtures (
    fixture_id INTEGER PRIMARY KEY,
    event_id INTEGER REFERENCES raw.gameweeks (event_id),
    team_h INTEGER NOT NULL REFERENCES raw.teams (team_id),
    team_a INTEGER NOT NULL REFERENCES raw.teams (team_id),
    team_h_score INTEGER,
    team_a_score INTEGER,
    team_h_difficulty INTEGER,
    team_a_difficulty INTEGER,
    kickoff_time TIMESTAMPTZ,
    finished BOOLEAN NOT NULL,
    stats JSONB,
    source TEXT NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL,
    batch_id UUID NOT NULL
);

CREATE TABLE raw.entry_picks (
    entry_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL REFERENCES raw.gameweeks (event_id),
    element_id INTEGER NOT NULL,
    element_type_id INTEGER NOT NULL REFERENCES raw.positions (position_id),
    position INTEGER NOT NULL,
    multiplier INTEGER NOT NULL,
    is_captain BOOLEAN NOT NULL,
    is_vice_captain BOOLEAN NOT NULL,
    active_chip TEXT,
    entry_history JSONB,
    source TEXT NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL,
    batch_id UUID NOT NULL,
    PRIMARY KEY (entry_id, event_id, element_id)
);

-- Append-only: captures price / ownership / form over time. Never overwritten.
CREATE TABLE raw.snapshots (
    player_id INTEGER NOT NULL,
    gw INTEGER NOT NULL,
    now_cost INTEGER NOT NULL,
    selected_by_percent NUMERIC NOT NULL,
    form NUMERIC,
    source TEXT NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL,
    batch_id UUID NOT NULL
);

CREATE INDEX ix_raw_snapshots_player_gw ON raw.snapshots (player_id, gw);
