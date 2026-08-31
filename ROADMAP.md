# FPL Engine — Roadmap

Phases are ordered so that data reliability comes first and model sophistication
last: never tune a model on top of a flaky pipeline. Each phase has a hard
"done-when" gate before the next begins.

## Phase 0 — Scaffold

Goal: an empty but *deployable* skeleton with quality gates wired up.

- `repo`: init, `pyproject.toml` + `uv.lock`, `src/fpl_engine/` package layout.
- `tooling`: `pre-commit` with `ruff` (lint+format) and `sqlfluff`.
- `config`: `pydantic-settings`, `.env.example`, `structlog` setup.
- `infra`: `docker-compose.yml` (Postgres + Dagster webserver/daemon/code).
- `ci`: GitHub Actions skeleton (lint + a trivial passing test).
- `docs`: this file, `ARCHITECTURE.md`, `CONTRIBUTING.md`, ADR-0001.

Done when: `docker compose up` yields Postgres + an empty Dagster UI, and CI is
green on `main`.

## Phase 1 — Ingestion (data engineer)

Goal: FPL data lands in `raw` reliably, on schedule, on the VPS.

- FPL API client (`httpx`) with retry/backoff and a descriptive UA.
- Loaders → `raw`: bootstrap (players/teams/positions/gameweeks), fixtures,
  and `entry/{id}/picks` for your squad. Append `raw.snapshots`.
- Versioned migrations for the raw schema; lineage columns on every table.
- Dagster `raw_*` assets + `daily_ingest_job`; hourly polling in the
  pre-deadline window.

Done when: raw tables refresh daily on the VPS, `snapshots` accumulate, and a
re-run produces zero duplicates.

## Phase 2 — Transform (analytics engineer)

Goal: clean, tested marts as the Python interface.

- dbt project (`dbt-postgres`); `stg_*` views per source.
- `int_*`: FPL↔FBref join via a `player_map` seed, rolling form off snapshots,
  per-team forward fixture runs with difficulty.
- `mart_player_gameweek`, `mart_fixtures`, `mart_team_form`.
- dbt tests (`not_null`, `unique`, `relationships`, plus custom business rules)
  and generated docs. Register dbt as Dagster assets via `dagster-dbt`.

Done when: `dbt build` passes with all tests, and marts materialize inside the
Dagster lineage graph.

## Phase 3 — Analytics (data analyst)

Goal: a data-tuned recommendation, not a hand-guessed one.

- Port scoring to read `mart_player_gameweek`.
- PuLP transfer optimizer: best free move, the -4 hit rule, and the roll logic.
- Backtest harness: replay historical gameweeks, score under a weight set,
  compare projected vs actual.
- Tune `W_FORM / W_XGI / W_PPG`; define KPIs — projection MAE per GW,
  suggestion hit-rate, and hit ROI (did -4 moves clear +4?).

Done when: `transfer_recommendation` outputs for your squad, and the backtest
reports error metrics from which the weights were chosen.

## Phase 4 — Serving (Telegram first)

Goal: the tip arrives automatically before every deadline.

- Telegram bot; `notify_telegram` op downstream of the recommendation.
- `pre_deadline_job` schedule/sensor keyed on the next deadline.
- Message format: squad projected points, best free-transfer move, hit verdict,
  captain pick, and a deadline countdown.

Done when: you receive a formatted, correct tip before a real deadline with no
manual trigger.

## Phase 5 — Enrichment & polish

Goal: richer signal and the deferred nice-to-haves.

- FBref ingestion + `player_map` seed maintenance.
- Captaincy / triple-captain ranker on the same scores.
- Optional FastAPI read API and Metabase on marts.
- Nightly `pg_dump` backup asset shipped off-box; alerting polish.

## Backlog (unscheduled)

- Chip-timing planner (double/blank gameweek detection from the fixtures mart).
- Price-change predictor trained on the `snapshots` time series.
- Expected-hit ROI dashboard.
