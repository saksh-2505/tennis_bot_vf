from config import Settings


def test_settings_defaults() -> None:
    s = Settings()
    assert s.DATABASE_URL == "postgresql+psycopg2://tennis:tennis@localhost:5432/tennis_bot"
    assert s.LOG_LEVEL == "INFO"
    assert s.LOG_FORMAT == "text"
