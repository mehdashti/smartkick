# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field # برای امکانات بیشتر مثل alias یا validation (اختیاری)
import logging # استفاده از لاگر به جای print

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # --- API Football Settings ---
    API_FOOTBALL_KEY: str
    API_FOOTBALL_HOST: str = "v3.football.api-sports.io"

    # --- Database Settings ---
    DATABASE_URL: str = Field(..., validation_alias='DATABASE_URL') 
    DEFAULT_DB_BATCH_SIZE: int = 500
    SQL_ECHO: bool = False # در پروداکشن False باشد بهتر است

    # ----- Security Settings -----
    JWT_SECRET_KEY: str = Field(..., validation_alias='JWT_SECRET_KEY') # اطمینان از خواندن از env
    JWT_ALGORITHM: str = Field(default="HS256", validation_alias='JWT_ALGORITHM')
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, validation_alias='ACCESS_TOKEN_EXPIRE_MINUTES')
    # -----------------------------

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )


try:
    settings = Settings()
    logger.info(f"Settings loaded successfully. DB URL set: {'Yes' if settings.DATABASE_URL else 'No'}. JWT Algo: {settings.JWT_ALGORITHM}")
except Exception as e:
    logger.exception("CRITICAL ERROR: Failed to load settings from environment or .env file!")
    raise SystemExit(f"Failed to load settings: {e}") from e
