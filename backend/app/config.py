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


# One shared instance, imported wherever settings are needed.
settings = Settings()