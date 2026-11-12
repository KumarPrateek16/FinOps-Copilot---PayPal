from functools import lru_cache
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


import os
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENV_FILE = os.path.join(_BACKEND_DIR, ".env")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]
    SECRET_KEY: str = "insecure-dev-secret-key-replace-in-production-32b"
    ENCRYPTION_KEY: str = "insecure-dev-encryption-key-replace-in-production"

    # PostgreSQL Database
    POSTGRES_USER: str = "finops_user"
    POSTGRES_PASSWORD: str = "finops_password"
    POSTGRES_DB: str = "finops_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = "postgresql+asyncpg://finops_user:finops_password@localhost:5432/finops_db"

    # Redis & Celery
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # PayPal Sandbox API
    PAYPAL_ENVIRONMENT: str = "sandbox"
    PAYPAL_API_BASE_URL: str = "https://api-m.sandbox.paypal.com"
    PAYPAL_CLIENT_ID: str = Field(default="", description="PayPal Sandbox Client ID")
    PAYPAL_CLIENT_SECRET: str = Field(default="", description="PayPal Sandbox Client Secret")
    PAYPAL_WEBHOOK_ID: str = Field(default="", description="Registered PayPal Webhook ID")

    # Google Gemini API
    GEMINI_API_KEY: str = Field(default="", description="Google Gemini API Key")
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Human-in-the-Loop (HITL) Thresholds
    HITL_AUTO_SUBMIT_AMOUNT_THRESHOLD: float = 50.00
    HITL_MIN_CONFIDENCE_SCORE: float = 0.85

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()

