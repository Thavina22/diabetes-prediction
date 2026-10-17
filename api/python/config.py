from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Diabetes Risk Intelligence API"
    VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"

    # Database (optional in development — stateless screening is used when absent)
    DATABASE_URL: Optional[str] = None

    # Clerk (required in production)
    CLERK_PUBLISHABLE_KEY: Optional[str] = None
    CLERK_SECRET_KEY: Optional[str] = None
    CLERK_ISSUER: str = "https://clerk.example.com"
    CLERK_WEBHOOK_SECRET: Optional[str] = None

    # Vercel Cron protection
    CRON_SECRET: Optional[str] = None

    # Local development auth bypass — NEVER enable in production.
    DEV_AUTH_BYPASS: bool = False
    DEV_USER_ID: str = "dev-user"

    # Upstash Redis
    UPSTASH_REDIS_REST_URL: Optional[str] = None
    UPSTASH_REDIS_REST_TOKEN: Optional[str] = None

    # ML Model
    MODEL_PATH: str = "data/processed/best_model.joblib"

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
    ]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
