from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="WB_RND_",
        extra="ignore",
    )

    app_name: str = Field(default="wellnessbox-rnd")
    app_env: str = Field(default="local")
    api_prefix: str = Field(default="/v1")
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)
    log_level: str = Field(default="INFO")


@lru_cache
def get_settings() -> Settings:
    return Settings()

