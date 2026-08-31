from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven configuration. See ARCHITECTURE.md#config--secrets."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str | None = None
    fpl_entry_id: int | None = None
    discord_webhook_url: str | None = None
    fbref_cache_dir: str | None = None


def get_settings() -> Settings:
    return Settings()
