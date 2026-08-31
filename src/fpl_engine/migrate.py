"""Apply versioned SQL migrations in migrations/ via yoyo (no ORM, no models)."""

from pathlib import Path

from yoyo import get_backend, read_migrations

from fpl_engine.config.settings import get_settings

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "migrations"


def apply_migrations(database_url: str | None = None) -> None:
    url = database_url or get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL is not set")

    backend = get_backend(url.replace("postgresql://", "postgresql+psycopg://", 1))
    migrations = read_migrations(str(MIGRATIONS_DIR))
    with backend.lock():
        backend.apply_migrations(backend.to_apply(migrations))


def main() -> None:
    apply_migrations()


if __name__ == "__main__":
    main()
