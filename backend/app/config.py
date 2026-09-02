from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_repo_root() -> Path:
    backend_root = Path(__file__).resolve().parents[1]
    if (backend_root / "data" / "snapshots").exists():
        return backend_root
    parent = backend_root.parent
    if (parent / "data" / "snapshots").exists() or (parent / "docker-compose.yml").exists():
        return parent
    return parent


REPO_ROOT = _resolve_repo_root()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(REPO_ROOT / ".env"), str(Path.cwd() / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Policy Tracker"
    app_env: Literal["development", "production", "test"] = "development"
    data_mode: Literal["snapshot", "live"] = "snapshot"
    snapshot_id: str = "2026-08-31"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    database_url: str = "sqlite:///./data/runtime/app.db"
    admin_token: str = ""

    llm_provider: str = "doubao"
    llm_api_key: str = ""
    llm_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    llm_model: str = "ep-xxxxxxxx"
    llm_timeout_seconds: int = 60
    llm_max_retries: int = 2

    crawl_enabled: bool = False
    crawl_interval_seconds: float = 3.0
    crawl_user_agent: str = "Mozilla/5.0 (compatible; AIPolicyTracker/1.0)"

    scheduler_enabled: bool = False
    daily_crawl_cron: str = "0 2 * * *"
    daily_digest_cron: str = "0 8 * * *"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True

    data_dir: Path = Field(default=REPO_ROOT / "data")

    @field_validator("data_dir", mode="before")
    @classmethod
    def _as_path(cls, value: Path | str) -> Path:
        return Path(value)

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def snapshot_dir(self) -> Path:
        return self.data_dir / "snapshots" / self.snapshot_id

    @property
    def runtime_dir(self) -> Path:
        return self.data_dir / "runtime"

    @property
    def sqlite_path(self) -> Path:
        url = self.database_url
        if url.startswith("sqlite:///"):
            raw = url.replace("sqlite:///", "", 1)
            path = Path(raw)
            if not path.is_absolute():
                return (REPO_ROOT / path).resolve()
            return path
        return self.runtime_dir / "app.db"

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key) and not self.llm_api_key.startswith("ep-xxxx")

    @property
    def is_dev(self) -> bool:
        return self.app_env in {"development", "test"}

    @property
    def write_guard_relaxed(self) -> bool:
        return self.is_dev and not self.admin_token


@lru_cache
def get_settings() -> Settings:
    return Settings()
