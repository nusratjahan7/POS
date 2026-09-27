"""Application configuration.

All runtime configuration is read from environment variables (see
``.env.example``). Nothing secret is ever hard-coded; defaults exist only so the
app can boot in development and CI without a populated environment.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal
from urllib.parse import quote

from pydantic import EmailStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "staging", "production", "test"]
SameSite = Literal["lax", "strict", "none"]

_INSECURE_SECRET = "dev-only-insecure-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application -------------------------------------------------------
    PROJECT_NAME: str = "POS API"
    VERSION: str = "0.1.0"
    ENVIRONMENT: Environment = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Exact-match list of allowed browser origins. Send as a JSON array.
    BACKEND_CORS_ORIGINS: list[str] = []

    # --- Database ----------------------------------------------------------
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "pos"
    POSTGRES_PASSWORD: str = "pos"
    POSTGRES_DB: str = "pos"
    DATABASE_URL: str | None = None
    TEST_DATABASE_URL: str | None = None
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # --- Security ----------------------------------------------------------
    SECRET_KEY: str = _INSECURE_SECRET
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    ARGON2_TIME_COST: int = 3
    ARGON2_MEMORY_COST: int = 65536
    ARGON2_PARALLELISM: int = 4

    REFRESH_COOKIE_NAME: str = "pos_refresh"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: SameSite = "lax"
    COOKIE_DOMAIN: str | None = None

    # --- Rate limiting -----------------------------------------------------
    RATE_LIMIT_ENABLED: bool = True
    LOGIN_RATE_LIMIT: str = "10/minute"

    # --- Password reset ----------------------------------------------------
    # How long a reset link stays valid. Short, because it is a bearer secret.
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    # Base URL of the frontend, used to build the link that goes in the email.
    FRONTEND_APP_URL: str = "http://localhost:3000"
    PASSWORD_RESET_PATH: str = "/reset-password"

    # --- Bootstrap ---------------------------------------------------------
    FIRST_SUPERUSER_EMAIL: EmailStr = "admin@pos.example.com"
    FIRST_SUPERUSER_PASSWORD: str = "ChangeMe123!"
    FIRST_SUPERUSER_FULL_NAME: str = "Platform Administrator"

    # --- Derived -----------------------------------------------------------
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def database_url(self) -> str:
        """Async SQLAlchemy URL used by the application."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def test_database_url(self) -> str:
        if self.TEST_DATABASE_URL:
            return self.TEST_DATABASE_URL
        return self.database_url

    @property
    def access_token_ttl_seconds(self) -> int:
        return self.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    @property
    def refresh_token_ttl_seconds(self) -> int:
        return self.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

    @property
    def password_reset_ttl_seconds(self) -> int:
        return self.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES * 60

    def password_reset_url(self, token: str) -> str:
        """Absolute link embedded in the reset email, built from settings."""
        base = self.FRONTEND_APP_URL.rstrip("/")
        path = self.PASSWORD_RESET_PATH
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{base}{path}?token={quote(token, safe='')}"

    # --- Validation --------------------------------------------------------
    @model_validator(mode="after")
    def _validate_production_hardening(self) -> Settings:
        if self.is_production:
            if self.SECRET_KEY == _INSECURE_SECRET:
                raise ValueError("SECRET_KEY must be set to a strong value in production")
            if not self.COOKIE_SECURE:
                raise ValueError("COOKIE_SECURE must be true in production")
        if self.COOKIE_SAMESITE == "none" and not self.COOKIE_SECURE:
            raise ValueError("COOKIE_SAMESITE='none' requires COOKIE_SECURE=true")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor (import-safe, overridable in tests)."""
    return Settings()


settings = get_settings()
