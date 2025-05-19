# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # --- API Football Settings ---
    API_FOOTBALL_KEY: str
    API_FOOTBALL_HOST: str = "v3.football.api-sports.io"
    API_FOOTBALL_BASE_URL: str = "https://v3.football.api-sports.io"
    API_FOOTBALL_MAX_REQUESTS_PER_MINUTE: int = 300
    API_FOOTBALL_RATE_LIMIT_PERIOD_SECONDS: int = 60
    CURRENT_SEASON: int = 2023

    # --- Database Settings ---
    DATABASE_URL: str = Field(..., validation_alias='DATABASE_URL')
    DEFAULT_DB_BATCH_SIZE: int = 500
    SQL_ECHO: bool = False

    # --- Security Settings ---
    JWT_SECRET_KEY: str = Field(..., validation_alias='JWT_SECRET_KEY')
    JWT_ALGORITHM: str = Field(default="HS256", validation_alias='JWT_ALGORITHM')
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, validation_alias='ACCESS_TOKEN_EXPIRE_MINUTES')

    # --- Celery Settings ---
    CELERY_BROKER_URL: str = Field(..., validation_alias='CELERY_BROKER_URL')
    CELERY_RESULT_BACKEND: str = Field(..., validation_alias='CELERY_RESULT_BACKEND')
    CELERY_TASK_ACKS_LATE: bool = True
    CELERY_TASK_REJECT_ON_WORKER_LOST: bool = False
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP: bool = True

    # --- General Settings ---
    TIMEZONE: str = Field(default="UTC", validation_alias='TIMEZONE')

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

try:
    settings = Settings()
    logger.info(
        f"Settings loaded successfully. "
        f"DB URL set: {'Yes' if settings.DATABASE_URL else 'No'}. "
        f"JWT Algo: {settings.JWT_ALGORITHM}. "
        f"Timezone: {settings.TIMEZONE}. "
        f"Celery Broker Set: {'Yes' if settings.CELERY_BROKER_URL else 'No'}. "
        f"Celery Backend Set: {'Yes' if settings.CELERY_RESULT_BACKEND else 'No'}."
    )
except Exception as e:
    logger.exception("CRITICAL ERROR: Failed to load settings from environment or .env file!")
    raise SystemExit(f"Failed to load settings: {e}") from e
