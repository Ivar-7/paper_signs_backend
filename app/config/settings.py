"""Runtime configuration                    loaded from .env via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "paper_signs_backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Broker
    broker: str = "paper"
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_base_url: str = "https://paper-api.alpaca.markets"

    # Instruments
    symbols: str = "SPY,QQQ,IWM,EFA,EEM,TLT,GLD,DBC,VNQ,UUP"

    # Scheduler
    schedule_cron: str = "30 22 * * 1-5"

    # Database
    database_url: str = "sqlite:///./trendbot.db"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Data
    data_period: str = "15y"

    # Logging
    log_level: str = "INFO"

    @property
    def symbol_list(self) -> List[str]:
        return [s.strip().upper() for s in self.symbols.split(",") if s.strip()]

    @field_validator("database_url", mode="before")
    @classmethod
    def fix_database_url(cls, v: str) -> str:
        if isinstance(v, str) and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    @field_validator("broker")
    @classmethod
    def validate_broker(cls, v: str) -> str:
        if v not in ("paper", "alpaca"):
            raise ValueError("BROKER must be 'paper' or 'alpaca'")
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton Settings instance (cached)."""
    return Settings()