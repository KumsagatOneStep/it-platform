import pytest
from pydantic import ValidationError

from app.core.config import Settings
from tests.db_utils import BACKEND_DIR


def test_production_rejects_default_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production")


def test_production_rejects_short_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production", jwt_secret="short")


def test_production_accepts_strong_secret() -> None:
    settings = Settings(app_env="production", jwt_secret="x" * 40, cookie_secure=True)

    assert settings.jwt_secret == "x" * 40


def test_production_rejects_cors_origins() -> None:
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            jwt_secret="x" * 40,
            cookie_secure=True,
            cors_origins=["https://a.ru"],
        )


def test_invalid_timezone_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(company_timezone="Mars/Olympus")


def test_defaults_match_spec() -> None:
    settings = Settings()

    assert settings.access_token_ttl_minutes == 15
    assert settings.refresh_token_ttl_days == 14
    assert settings.company_timezone == "Europe/Moscow"


@pytest.mark.parametrize("app_env", ["staging", "production"])
def test_non_local_env_rejects_insecure_cookie(app_env: str) -> None:
    with pytest.raises(ValidationError, match="COOKIE_SECURE"):
        Settings(app_env=app_env, jwt_secret="x" * 40, cookie_secure=False)


def test_local_env_allows_insecure_cookie() -> None:
    assert Settings(app_env="local", cookie_secure=False).cookie_secure is False


@pytest.mark.parametrize("entry", ["not-an-ip", "10.0.0.0/33", ""])
def test_malformed_trusted_proxy_rejected_at_load(entry: str) -> None:
    with pytest.raises(ValidationError, match="TRUSTED_PROXIES"):
        Settings(trusted_proxies=["127.0.0.1/32", entry])


def test_trusted_proxies_accept_networks_and_addresses() -> None:
    settings = Settings(trusted_proxies=["172.16.0.0/12", "10.0.0.5", "::1/128"])

    assert settings.trusted_proxies == ["172.16.0.0/12", "10.0.0.5", "::1/128"]


def test_trusted_proxies_from_env_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXIES", '["172.16.0.0/12"]')

    assert Settings().trusted_proxies == ["172.16.0.0/12"]


def test_dockerfile_defaults_to_production() -> None:
    dockerfile = (BACKEND_DIR / "Dockerfile").read_text(encoding="utf-8")

    assert "APP_ENV=production" in dockerfile
