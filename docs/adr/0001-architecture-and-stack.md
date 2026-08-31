# ADR-0001: Architecture and stack

- Status: Accepted
- Date: 2026-08-31

## Context

A personal Fantasy Premier League suggestion engine, deployed on a single VPS,
that ingests FPL + FBref data and pushes a weekly transfer recommendation. The
dataset is tiny (hundreds of players, hundreds of fixtures, kilobyte-scale daily
snapshots), so the engineering priority is correctness, reproducibility, and
automation — not scale. The primary user is one person (the author).

## Decision

1. **Single-user, no auth.** The FPL entry id lives in config; there is no user
   table or authentication layer. The Dagster UI is protected only by Caddy
   basic-auth.
2. **PostgreSQL warehouse; dbt for transformation; Python for EL and modelling.**
   Ingestion lands raw data; dbt builds staging → intermediate → marts; Python
   analytics reads only from marts.
3. **Dagster for orchestration from v1.** Asset-based, integrated with dbt via
   `dagster-dbt` so the whole pipeline is one lineage graph with scheduling,
   sensors, retries, and a run-history UI.
4. **Discord push (incoming webhook) as the primary delivery.** Implemented as a
   Dagster op downstream of the recommendation asset, fired by a pre-deadline
   schedule, and written against a small swappable `Notifier` interface so the
   channel can change without touching the pipeline.
5. **Docker Compose on one VPS**, Caddy for TLS + basic-auth, GitHub Actions for
   CI/CD, trunk-based git with PR-gated CI and SemVer release tags.

## Alternatives considered and rejected

- **SQLite** — fine for the original laptop script, but not for a persistent,
  scheduled, multi-process service. Rejected in favour of Postgres.
- **Airflow / Kafka / Spark / Kubernetes** — all oversized for kilobyte-scale
  batch data; they would add operational burden with no benefit.
- **Cron-only orchestration** — simplest, but the author explicitly wants
  observability, retries, and lineage from the start, which Dagster provides.
- **Multi-user / auth** — out of scope; would add a user model, session
  handling, and a real secret surface for no current benefit.
- **Telegram (delivery)** — equally free and frictionless, and a perfectly good
  alternative. Discord edged it only because an incoming webhook needs no bot
  token or chat-id lookup — a plain HTTP POST. The `Notifier` interface keeps a
  later switch cheap.
- **WhatsApp (delivery)** — rejected. Business-initiated messages outside a
  24-hour window require pre-approved message templates and per-message billing,
  which fights a fully-automated, scheduled, free-form push. Unofficial libraries
  that bypass this violate WhatsApp's terms and risk number bans.

## Consequences

- The secret surface is minimal and there is no auth code to maintain.
- Dagster adds a couple of long-running services (webserver, daemon) and a
  learning surface, repaid by unified lineage, scheduling, and a UI.
- Postgres is shared between the warehouse and Dagster's run storage (separate
  databases on the same instance) to keep the deployment to one datastore.
- Revisiting multi-user or a web dashboard later means adding an API/auth layer;
  the raw → marts → analytics separation keeps that additive rather than a
  rewrite.
- The delivery channel sits behind a `Notifier` interface, so moving from Discord
  to Telegram — or sending to both — is a one-file change, not a cross-cutting
  one.
