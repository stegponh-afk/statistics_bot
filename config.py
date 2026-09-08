from functools import cached_property

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str
    owner_ids: str = ""

    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "statistics_bot"
    postgres_user: str = "statistics_bot"
    postgres_password: str = ""

    redis_url: str = "redis://redis:6379/0"

    # HTTP API served by aiohttp from the same process as the bot.
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    api_public_url: str = ""
    api_rate_limit_per_minute: int = 600
    api_unauth_rate_limit_per_minute: int = 60

    # getChatMember results are cached this long, so a user who just
    # subscribed may need "Проверить" (which bypasses the cache) to pass.
    forcesub_cache_ttl_seconds: int = 60
    forcesub_prompt_cooldown_seconds: int = 30

    admin_sync_ttl_seconds: int = 600
    default_timezone: str = "Europe/Moscow"

    stats_retention_days: int = 90

    log_level: str = "INFO"

    @cached_property
    def owner_ids_list(self) -> list[int]:
        return [int(x) for x in self.owner_ids.split(",") if x.strip()]

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
