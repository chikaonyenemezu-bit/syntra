from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://syntra:syntra@localhost:5432/syntra"

    # Auth
    jwt_secret: str = "dev-only-secret-change-me-in-production-0123456789"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    # Monitoring thresholds
    heartbeat_interval_seconds: int = 10
    heartbeat_timeout_seconds: int = 45
    latency_degraded_ms: int = 1500
    error_rate_degraded: float = 0.05

    # Seed demo users and systems on startup
    seed_demo_data: bool = True

    cors_origins: str = "http://localhost:5173,http://localhost:8080"


settings = Settings()
