import ipaddress
from functools import lru_cache
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_JWT_SECRET = "local-development-secret-do-not-use-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["local", "test", "staging", "production"] = "local"
    database_url: str = "postgresql+asyncpg://app:app@localhost:5432/it_platform"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = LOCAL_JWT_SECRET
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 14
    cookie_secure: bool = True
    trusted_proxies: list[str] = Field(default_factory=lambda: ["127.0.0.1/32", "::1/128"])
    cors_origins: list[str] = Field(default_factory=list)
    company_timezone: str = "Europe/Moscow"

    @field_validator("trusted_proxies")
    @classmethod
    def _validate_trusted_proxies(cls, value: list[str]) -> list[str]:
        for entry in value:
            try:
                ipaddress.ip_network(entry, strict=False)
            except ValueError as exc:
                raise ValueError(
                    f"TRUSTED_PROXIES: некорректный IP-адрес или сеть {entry!r}"
                ) from exc
        return value

    @model_validator(mode="after")
    def _validate(self) -> "Settings":
        try:
            ZoneInfo(self.company_timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Неизвестный часовой пояс: {self.company_timezone}") from exc
        if self.app_env in ("staging", "production"):
            if self.jwt_secret == LOCAL_JWT_SECRET or len(self.jwt_secret) < 32:
                raise ValueError("JWT_SECRET должен быть случайной строкой длиной от 32 символов")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE=false допустим только в local и test")
            if self.cors_origins:
                raise ValueError("CORS_ORIGINS должен быть пустым: фронтенд и API на одном домене")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
