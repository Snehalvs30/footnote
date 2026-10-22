"""Application settings, read from environment variables (or a .env file).

Like Spring's application.yaml + @ConfigurationProperties: each field below can be
overridden by an environment variable with the FOOTNOTE_ prefix, e.g.
FOOTNOTE_DATABASE_URL=postgresql+psycopg://...
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="FOOTNOTE_")

    # "postgresql+psycopg" = PostgreSQL, using the psycopg (version 3) driver.
    database_url: str = "postgresql+psycopg://footnote:footnote@localhost:5433/footnote"

    # Uploads larger than this are rejected with 413.
    max_upload_mb: int = 10

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


# One shared instance, imported wherever settings are needed.
settings = Settings()