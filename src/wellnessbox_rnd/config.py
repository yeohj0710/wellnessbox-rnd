from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ALLOWED_APP_ENVS = {"local", "test", "staging", "production"}
_ALLOWED_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="WB_RND_",
        extra="ignore",
    )

    app_name: str = Field(default="wellnessbox-rnd")
    app_env: str = Field(
        default="local",
        validation_alias=AliasChoices("WB_RND_APP_ENV", "WB_RND_ENV", "APP_ENV"),
    )
    api_prefix: str = Field(default="/v1")
    host: str = Field(default="0.0.0.0")
    port: int = Field(
        default=8000,
        validation_alias=AliasChoices("WB_RND_PORT", "PORT"),
    )
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("WB_RND_LOG_LEVEL", "LOG_LEVEL"),
    )
    workers: int = Field(
        default=1,
        validation_alias=AliasChoices("WB_RND_WORKERS", "WEB_CONCURRENCY"),
    )

    @field_validator("app_name")
    @classmethod
    def validate_app_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("app_name_must_not_be_blank")
        return normalized

    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in _ALLOWED_APP_ENVS:
            allowed_values = ",".join(sorted(_ALLOWED_APP_ENVS))
            raise ValueError(f"app_env_must_be_one_of:{allowed_values}")
        return normalized

    @field_validator("api_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("api_prefix_must_start_with_slash")
        normalized = value.rstrip("/")
        return normalized or "/"

    @field_validator("host")
    @classmethod
    def validate_host(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("host_must_not_be_blank")
        return normalized

    @field_validator("port")
    @classmethod
    def validate_port(cls, value: int) -> int:
        if not 1 <= value <= 65535:
            raise ValueError("port_must_be_between_1_and_65535")
        return value

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in _ALLOWED_LOG_LEVELS:
            allowed_values = ",".join(sorted(_ALLOWED_LOG_LEVELS))
            raise ValueError(f"log_level_must_be_one_of:{allowed_values}")
        return normalized

    @field_validator("workers")
    @classmethod
    def validate_workers(cls, value: int) -> int:
        if not 1 <= value <= 4:
            raise ValueError("workers_must_be_between_1_and_4")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()

