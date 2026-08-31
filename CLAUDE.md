# fpl-engine

Personal FPL suggestion engine. Full context lives in:

- [ARCHITECTURE.md](ARCHITECTURE.md) — stack, data flow, warehouse schemas, Dagster assets
- [ROADMAP.md](ROADMAP.md) — phases and their done-when gates (**currently: Phase 1 complete**)
- [CONTRIBUTING.md](CONTRIBUTING.md) — branching, commit style, PR/CI requirements
- [docs/adr/0001-architecture-and-stack.md](docs/adr/0001-architecture-and-stack.md) — why this stack

## Running it

```
uv sync                  # install deps from uv.lock
pre-commit install       # wire up ruff + sqlfluff on commit
cp .env.example .env      # fill in local values
docker compose up -d      # Postgres + Dagster webserver/daemon/code
uv run fpl-migrate        # apply migrations/*.sql to the raw schema
```

Dagster UI: http://localhost:3000

## Conventions

- Python 3.12, `src/` layout, dependencies managed with `uv` (`uv.lock` is committed).
- `ruff` for lint + format, `sqlfluff` (dialect: postgres) for SQL once dbt lands.
- Conventional Commits (`feat:`, `fix:`, `data:`, `chore:`, `docs:`, `test:`, `refactor:`, `ci:`).
- Trunk-based: short-lived branches off `main`, PR-gated CI, squash-merge.
- EL is separate from T: ingestion lands raw data only; dbt transforms; Python
  analytics reads only from marts. See ARCHITECTURE.md's "Principles" section
  before adding anything that reaches backwards across that boundary.

## Current phase

Phase 1 (ingestion) is done: an `httpx`+`tenacity` FPL API client, `pydantic`
payload contracts, EL-only loaders that upsert reference tables and append
`raw.snapshots`, SQL migrations (applied via `yoyo`, no ORM), and Dagster
`raw_fpl_*` assets + `daily_ingest_job` + a pre-deadline sensor. Still no
transformation logic (no renaming/cleaning/joins) — that's Phase 2 (dbt).
Don't add dbt models, scoring, or Telegram code without checking ROADMAP.md
for which phase it belongs to.
