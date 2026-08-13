from __future__ import annotations
import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration loaded from environment / .env file."""

    app_name: str = "Finance Tracker"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    database_url: str = (
        "postgresql+asyncpg://finance:finance_dev_password@localhost:5432/finance_db"
    )

    jwt_secret_key: str = "change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    bcrypt_rounds: int = 12

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()


if settings.app_env not in {"development", "test"} and settings.jwt_secret_key in {
    "",
    "change-me-to-a-long-random-string",
}:
    raise RuntimeError(
        "JWT_SECRET_KEY must be set to a strong secret in production-like environments."
    )
