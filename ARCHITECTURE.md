# FPL Engine — Architecture

A personal Fantasy Premier League suggestion engine: ingests FPL + FBref data,
projects player points, and pushes a weekly transfer recommendation (with the
-4 hit already accounted for) before each gameweek deadline.

## Scope & decisions (locked)

| Decision | Choice | Consequence |
|---|---|---|
| Users | Single-user, no auth | No users table, no auth layer; entry id in config |
| Primary delivery | Discord push (webhook) | Notifier is a Dagster op behind a swappable interface |
| Orchestration | Dagster (from v1) | dbt models become Dagster assets; one lineage graph |
| Hosting | One VPS, Docker Compose | Small-data problem — no distributed tooling |

## Principles

- **EL is separate from T.** Ingestion lands *raw*, source-shaped data. dbt
  transforms. Python models read only from marts. No layer reaches backwards.
- **Idempotent, reproducible, observable.** Re-running a load never duplicates;
  every artifact is rebuildable from raw; every run is visible in Dagster.
- **`main` is always deployable.** Trunk-based flow, PR-gated CI.
- **Right-sized.** Postgres + dbt + Dagster + Discord + Caddy on one box.
  Explicitly *not* using Kubernetes, Kafka, Spark, or Airflow — this is
  kilobytes of data, so the discipline is correctness, not scale.

## Data flow

```
Sources            Ingestion         Warehouse        Transform         Analytics            Serving
FPL API  ─┐                          Postgres         dbt               projections          Discord push
          ├──► Python EL ──────────► raw schema ────► staging  ───────► + PuLP optimizer ───► (Dagster op,
FBref  ───┘     (httpx,              (source-shaped)  intermediate      + backtest/tuning     pre-deadline)
                soccerdata)                           marts             (reads marts)
```

Dagster orchestrates the entire chain as software-defined assets. dbt models are
registered as Dagster assets via `dagster-dbt`, so raw → staging → marts →
projections → recommendation → notify is a single dependency graph.

## Services (VPS `docker-compose.prod.yml`)

- `postgres` — the warehouse (schemas: `raw`, `staging`, `intermediate`,
  `marts`, `analytics`) and Dagster's run/event storage (separate database).
- `dagster-webserver` — the observability UI, behind Caddy basic-auth.
- `dagster-daemon` — runs schedules and sensors.
- `dagster-code` — the user-code container holding our Dagster definitions.
- `caddy` — automatic TLS + basic-auth in front of the Dagster UI.
- *(later)* `api` (FastAPI), `metabase` (BI on marts) — deferred; not in v1.

## Warehouse schemas

- `raw.*` — landed source data, one table per source object, with lineage
  columns (`source`, `loaded_at`, `batch_id`). The append-only `raw.snapshots`
  table accumulates price/ownership/form over time — this is the one dataset we
  cannot re-fetch, so it is the thing backups exist to protect.
- `staging.stg_<source>__<entity>` — cleaned, typed, renamed views.
- `intermediate.int_*` — joins and reshaping (FPL↔FBref via a mapping seed,
  rolling form windows off snapshot history, per-team forward fixture runs).
- `marts.mart_*` — the stable interface Python reads: `mart_player_gameweek`
  (one row per player per upcoming GW with every feature), `mart_fixtures`,
  `mart_team_form`.
- `analytics.*` — model outputs and backtest results.

## Dagster assets, schedules & sensors

- Ingestion assets: `raw_fpl_bootstrap`, `raw_fpl_fixtures`,
  `raw_fpl_entry_picks`, `raw_fbref_*`.
- dbt assets: staging → intermediate → marts (auto-generated from the dbt graph).
- Analytics assets: `player_projections` (← marts),
  `transfer_recommendation` (← projections + entry picks).
- `daily_ingest_job` — schedule at ~06:00 to refresh FPL data.
- `pre_deadline_job` — schedule/sensor keyed on the next deadline from
  `mart_fixtures`; runs the full chain and pushes the Discord tip. Also polls
  hourly inside the 24h pre-deadline window to catch price moves.
- `notify_discord` — op downstream of `transfer_recommendation`, written against
  a small `Notifier` interface (`send(tip)`) with a `DiscordNotifier`
  implementation, so the delivery channel is a one-file detail rather than
  something wired through the pipeline.

## Config & secrets (single-user)

`pydantic-settings` reads everything from the environment:
`DATABASE_URL`, `FPL_ENTRY_ID`, `DISCORD_WEBHOOK_URL`, `FBREF_CACHE_DIR`.
Real values live in a git-ignored `.env` on the VPS;
`.env.example` is committed. No auth system means the secret surface is tiny.

## Observability

Structured JSON logging (`structlog`); the Dagster UI is the primary window into
run history, retries, and asset freshness; dbt tests are the data-quality
tripwire; a dead-man's-switch heartbeat catches a silently-failed nightly load;
pipeline failures are routed to the same Discord channel as the tips.

## Rate-limit etiquette

FBref is capped well under its 10-requests-per-minute limit, cached to disk, and
run on a slower cadence than the FPL pull. The FPL API is generous but gets a
descriptive user-agent and backoff; hourly polling happens only in the
pre-deadline window.

## Non-goals (v1)

Auth / multi-user, web dashboard, live in-play data, a mobile app, and any model
more complex than the tuned linear scoring blend. These are revisitable later —
the architecture leaves room — but none are v1.
