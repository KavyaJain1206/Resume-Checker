"""
config/settings.py
Centralized, typed application configuration. Every environment-dependent
value the app needs lives here — nothing reads os.environ directly outside
this module.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- database ------------------------------------------------------
    database_url: str
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_recycle_seconds: int = 1800
    database_echo: bool = False

    # --- admin auth ------------------------------------------------------
    admin_email: str = "admin@placement.team"
    admin_password: str = "playbook2026"
    secret_key: str = "change-me-in-prod"
    token_ttl_seconds: int = 24 * 3600

    # --- http / cors ------------------------------------------------------
    cors_origins: str = "http://localhost:5173"
    port: int = 8000

    # --- uploads ------------------------------------------------------
    max_upload_bytes: int = 5 * 1024 * 1024
    upload_dir: str = "data/resumes"

    # --- runtime ------------------------------------------------------
    environment: str = "development"
    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def upload_dir_abs(self) -> str:
        path = Path(self.upload_dir)
        if not path.is_absolute():
            path = BACKEND_ROOT / path
        return str(path)

    @property
    def sqlalchemy_database_url(self) -> str:
        """Normalize a plain postgresql:// URL to the asyncpg driver SQLAlchemy needs."""
        url = self.database_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
