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

    # openFDA drug recall integration (INT-FDA-01)
    fda_api_url: str = "https://api.fda.gov/drug/enforcement.json"
    fda_api_key: str = ""                      # optional; raises the openFDA rate limit
    fda_sync_enabled: bool = True              # scheduled live sync in the worker
    fda_sync_interval_minutes: int = 360
    fda_lookback_days: int = 30
    fda_max_records: int = 500
    fda_page_size: int = 100
    fda_timeout_seconds: float = 30.0
    fda_rejection_threshold: float = 0.10      # above this share of rejected records the integration is degraded

    # Knowledge Assistant (LLM). Put the key in .env, never in code or in a commit.
    llm_provider: str = "auto"             # auto | anthropic | openai | groq | none
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    groq_api_key: str = ""
    llm_model: str = ""                    # empty = provider default
    anthropic_version: str = "2026-10-21"
    anthropic_base_url: str = "https://api.anthropic.com"   # change only for a company proxy or gateway
    openai_base_url: str = "https://api.openai.com"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    llm_max_tokens: int = 1200
    llm_timeout_seconds: float = 60.0
    llm_max_tool_rounds: int = 5
    assistant_context_passages: int = 4

    # Seed demo users and systems on startup
    seed_demo_data: bool = True

    cors_origins: str = "http://localhost:5173,http://localhost:8080"


settings = Settings()
