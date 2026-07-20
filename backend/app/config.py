from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql://shongkhep_user:shongkhep_pass@localhost:5432/shongkhep_db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_PRE_PING: bool = True

    # ── Security ──────────────────────────────────────────────────────────────
    SECRET_KEY: str = "changeme-in-production-use-long-random-string-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # ── App ───────────────────────────────────────────────────────────────────
    APP_NAME: str = "Shongkhep AI"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 3600          # 1 hour for summary cache
    RATE_LIMIT_PER_MINUTE: int = 30

    # ── Celery ────────────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    CELERY_TASK_SOFT_TIME_LIMIT: int = 120  # seconds
    CELERY_TASK_TIME_LIMIT: int = 180

    # ── AI Model ──────────────────────────────────────────────────────────────
    MODEL_NAME: str = "google/mt5-small"
    MAX_SUMMARY_LENGTH: int = 150
    MIN_SUMMARY_LENGTH: int = 40
    MODEL_DEVICE: str = "auto"             # "auto" | "cpu" | "cuda" | "mps"
    MODEL_TORCH_DTYPE: str = "auto"        # "auto" | "float16" | "float32"

    # ── Observability ─────────────────────────────────────────────────────────
    ENABLE_METRICS: bool = True
    METRICS_PATH: str = "/metrics"

    # ── Webhooks ──────────────────────────────────────────────────────────────
    WEBHOOK_TIMEOUT_SECONDS: int = 10
    WEBHOOK_MAX_RETRIES: int = 3

    # ── Admin ─────────────────────────────────────────────────────────────────
    ADMIN_SECRET: str = "admin-secret-change-this"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
