import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_default_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production")


def test_production_rejects_short_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production", jwt_secret="short")


def test_production_accepts_strong_secret() -> None:
    settings = Settings(app_env="production", jwt_secret="x" * 40)

    assert settings.jwt_secret == "x" * 40


def test_production_rejects_cors_origins() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production", jwt_secret="x" * 40, cors_origins=["https://a.ru"])


def test_invalid_timezone_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(company_timezone="Mars/Olympus")


def test_defaults_match_spec() -> None:
    settings = Settings()

    assert settings.access_token_ttl_minutes == 15
    assert settings.refresh_token_ttl_days == 14
    assert settings.company_timezone == "Europe/Moscow"
