from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="REPLAYTUTOR_",
        extra="ignore",
        case_sensitive=False,
    )

    host: str = "127.0.0.1"
    port: int = Field(default=8788, ge=1, le=65535)
    data_dir: Path = Path("./data")
    log_level: str = "INFO"
    cors_origins: str = "http://127.0.0.1:5173"
    codex_timeout_seconds: int = Field(default=180, ge=10, le=600)
    binance_config_path: Path = Path("~/.config/replaytutor/binance-readonly.json")

    @field_validator("host")
    @classmethod
    def local_host_only(cls, value: str) -> str:
        if value != "127.0.0.1":
            raise ValueError("REPLAYTUTOR_HOST must remain 127.0.0.1 in M0")
        return value

    @field_validator("log_level")
    @classmethod
    def valid_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
            raise ValueError("unsupported log level")
        return normalized

    @property
    def resolved_data_dir(self) -> Path:
        return self.data_dir.expanduser().resolve()

    @property
    def database_path(self) -> Path:
        return self.resolved_data_dir / "app.db"

    @property
    def resolved_binance_config_path(self) -> Path:
        return self.binance_config_path.expanduser().resolve()

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
