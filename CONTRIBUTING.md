# Contributing

Solo project, professional habits. The point of the workflow below is not
ceremony — it is that every change is CI-validated and `main` is always
deployable to the VPS.

## Dev setup

```
uv sync                 # install deps from the lockfile
pre-commit install      # wire up ruff + sqlfluff on commit
cp .env.example .env     # fill in local values
docker compose up -d     # Postgres + Dagster locally
```

## Branching — trunk-based

- `main` is protected and always releasable. No direct pushes.
- Work happens on short-lived branches off `main`, merged within days:
  - `feat/…` new capability
  - `fix/…` bug fix
  - `data/…` ingestion / dbt model / data-quality change
  - `chore/…` tooling, deps, infra
  - `docs/…` documentation only
- Rebase on `main` before opening the PR; squash-merge into `main`.

## Commits — Conventional Commits

`type(scope): summary`, e.g. `feat(ingestion): add fixtures loader`.
Types: `feat`, `fix`, `data`, `chore`, `docs`, `test`, `refactor`, `ci`.
This keeps history machine-readable and lets the changelog auto-generate.

## Pull requests

Every change goes through a PR into `main` — even solo — because the PR is the
CI gate. CI must pass before merge:

1. `ruff` (lint + format check) and `sqlfluff` (SQL lint)
2. `pytest` (unit + integration against an ephemeral Postgres)
3. `dbt build` into a PR-scoped schema (`dbt_pr<number>`)
4. `dagster definitions validate`

## Releases

Cut a SemVer tag on `main` (`vX.Y.Z`); the tag push triggers the deploy
workflow (build image → pull on VPS → migrate → `dbt run` → health-check).
`CHANGELOG.md` is generated from the conventional commits since the last tag.

## dbt conventions

- Names: `stg_<source>__<entity>`, `int_<subject>`, `mart_<subject>`.
- Every model has a `schema.yml` entry with a description and at least one test.
- PR runs build into `dbt_pr<number>`; production builds into `marts`. Model
  changes are always validated in an isolated schema before touching prod data.

## Code style

- Python: `ruff` for lint + format, full type hints, `structlog` for logging.
- Tests are required for the scoring model, the optimizer constraints, and the
  -4 hit / roll decision logic — these are the parts that must never silently
  regress into recommending a points-losing move.
