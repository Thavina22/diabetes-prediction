from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Diabetes Risk Intelligence API"
    VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str

    # Clerk
    CLERK_PUBLISHABLE_KEY: str
    CLERK_SECRET_KEY: str
    CLERK_ISSUER: str = "https://clerk.example.com"

    # Upstash Redis
    UPSTASH_REDIS_REST_URL: str | None = None
    UPSTASH_REDIS_REST_TOKEN: str | None = None

    # ML Model
    MODEL_PATH: str = "models/diabetes_rf.joblib"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    return Settings()