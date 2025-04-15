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
    DATABASE_URL: str = Field(..., validation_alias='DATABASE_URL') # <--- اضافه شد
    # `validation_alias` اطمینان می دهد که دقیقا دنبال DATABASE_URL در .env می گردد
    # `...` یعنی این فیلد اجباری است و مقدار پیش فرض ندارد
    DEFAULT_DB_BATCH_SIZE: int = 500
    SQL_ECHO: bool = True # برای لاگ کردن SQL ها (اختیاری)
    # --- Celery Settings (Example) ---
    # CELERY_BROKER_URL: str = Field(..., validation_alias='CELERY_BROKER_URL')
    # CELERY_RESULT_BACKEND: str = Field(..., validation_alias='CELERY_RESULT_BACKEND') # اگر نیاز دارید
    

    # --- Pydantic Settings Configuration ---
    # خواندن از فایل .env و متغیرهای محیطی
    model_config = SettingsConfigDict(
        env_file='.env',         # نام فایل .env
        env_file_encoding='utf-8', # انکودینگ فایل
        extra='ignore'           # نادیده گرفتن متغیرهای اضافی در محیط
    )

# --- ایجاد نمونه تنظیمات ---
# این بلوک try-except مهم است تا اگر متغیرهای لازم پیدا نشدند، خطای واضحی بدهد
try:
    settings = Settings()
    # لاگ کردن تنظیمات بارگذاری شده (به جز اطلاعات حساس)
    logger.info(f"Settings loaded successfully. DB URL set: {'Yes' if settings.DATABASE_URL else 'No'}")
    # logger.debug(f"Loaded settings: API Key starts with {settings.API_FOOTBALL_KEY[:5]}..., Host: {settings.API_FOOTBALL_HOST}, DB URL: {settings.DATABASE_URL}") # DB URL را در debug لاگ کنید نه info
except Exception as e:
    logger.exception("CRITICAL ERROR: Failed to load settings from environment or .env file!")
    # در صورت عدم بارگذاری تنظیمات، برنامه نباید ادامه دهد
    raise SystemExit(f"Failed to load settings: {e}") from e