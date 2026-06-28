from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://tennis:tennis@localhost:5432/tennis_bot"
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "text"

    STATUS_CHECK_INTERVAL_SECONDS: int = 300
    DISCOVERY_INTERVAL_SECONDS: int = 43200
    DISCOVERY_ENABLED: bool = True

    LIVE_SCORE_INTERVAL_SECONDS: int = 10
    LIVE_ODDS_INTERVAL_SECONDS: int = 2
    LIVE_PREFETCH_MINUTES: int = 5

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


settings = Settings()
