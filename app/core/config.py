# core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # این متغیرها رو از فایل .env یا متغیرهای محیطی سیستم می‌خونه
    API_FOOTBALL_KEY: str
    API_FOOTBALL_HOST: str = "v3.football.api-sports.io" # مقدار پیش‌فرض

    # تنظیمات Pydantic برای خواندن از فایل .env
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

# یک نمونه از تنظیمات ساخته می‌شه که در کل برنامه قابل استفاده است
settings = Settings()

# برای تست می‌تونی چاپش کنی (بعداً حذف کن)
print(f"Loaded settings: API Key starts with {settings.API_FOOTBALL_KEY[:5]}..., Host: {settings.API_FOOTBALL_HOST}")
