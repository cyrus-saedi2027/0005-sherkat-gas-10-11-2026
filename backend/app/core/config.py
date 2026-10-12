"""Runtime configuration (env prefix ``GAZYAR_``).

Business numbers (threshold, points, co-pay …) are NOT here — they are
database settings editable from the admin panel (see settings_registry).
This file only holds deployment/infrastructure configuration.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GAZYAR_", env_file=".env", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"
    database_url: str = f"sqlite:///{BACKEND_DIR / 'var' / 'gazyar.db'}"
    sql_echo: bool = False

    # Secrets. Dev defaults are deliberately obvious so a prod boot with them fails (see check_prod()).
    secret_key: str = "dev-insecure-secret-change-me-0123456789abcdef"
    # Comma-separated Fernet keys, newest first (MultiFernet → key rotation without re-encrypting at once).
    fernet_keys: str = "UoldSfLhBdeLgRa6aUb_InGZLrH0LVQ7UlrMVvjgPEg="
    blind_index_key: str = "dev-insecure-blind-index-key-change-me"
    otp_pepper: str = "dev-insecure-otp-pepper"

    access_token_minutes: int = 15
    refresh_token_days: int = 30
    signup_token_minutes: int = 15
    file_url_ttl_seconds: int = 600

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://localhost:5174"])
    cookie_secure: bool = False

    upload_dir: Path = BACKEND_DIR / "var" / "uploads"
    max_json_body_bytes: int = 1_000_000
    # Hard ceiling for multipart bodies; the per-purpose limit is the `uploads.max_mb` setting.
    max_upload_body_bytes: int = 25_000_000

    sms_provider: Literal["console", "kavenegar"] = "console"
    sms_api_key: str = ""
    sms_sender: str = ""

    ratelimit_backend: Literal["memory", "redis"] = "memory"
    redis_url: str = "redis://localhost:6379/0"

    run_scheduler: bool = False
    # Dev/test only: echo OTP codes in API responses so E2E tests and local demos can proceed.
    expose_dev_otp: bool = True

    public_base_url: str = "http://localhost:8000"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"

    def check_prod(self) -> None:
        """Refuse to boot production with development secrets or dev conveniences."""
        if not self.is_prod:
            return
        bad = [
            name
            for name, val in (
                ("GAZYAR_SECRET_KEY", self.secret_key),
                ("GAZYAR_BLIND_INDEX_KEY", self.blind_index_key),
                ("GAZYAR_OTP_PEPPER", self.otp_pepper),
            )
            if "dev-insecure" in val or len(val) < 32
        ]
        if "UoldSfLhBdeLgRa6aUb_InGZLrH0LVQ7UlrMVvjgPEg=" in self.fernet_keys:
            bad.append("GAZYAR_FERNET_KEYS")
        if self.expose_dev_otp:
            bad.append("GAZYAR_EXPOSE_DEV_OTP must be false")
        if self.sms_provider == "console":
            bad.append("GAZYAR_SMS_PROVIDER must be a real provider")
        if bad:
            raise RuntimeError("Unsafe production configuration: " + ", ".join(bad))


@lru_cache
def get_settings() -> Settings:
    return Settings()
