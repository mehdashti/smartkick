# app/core/celery_app.py
from celery import Celery
from .config import settings

celery_app = Celery(
    "smartkick_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.TIMEZONE,
    enable_utc=True,
    task_track_started=True,
    result_expires=3600,  # مدت زمان نگهداری نتایج (به ثانیه)
    task_acks_late=True,  # تأیید تسک‌ها پس از اتمام
    task_reject_on_worker_lost=False,  # جلوگیری از بازپردازش تسک‌های ناتمام
    broker_connection_retry_on_startup=True,  # تلاش مجدد برای اتصال به بروکر
    # غیرفعال کردن موقت Beat برای تست
    beat_schedule={}
)

# ثبت تسک‌ها
celery_app.autodiscover_tasks(["app.tasks"])

if __name__ == "__main__":
    celery_app.start()
