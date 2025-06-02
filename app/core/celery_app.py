# app/core/celery_app.py
from gevent import monkey
monkey.patch_all()
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
    result_expires=3600,
    task_acks_late=True,
    task_reject_on_worker_lost=False, # این تنظیم یعنی اگر worker از دست برود (مثلا kill شود) تسک reject نمی‌شود و بعدا دوباره تلاش می‌شود.
    broker_connection_retry_on_startup=True,

    # --- تنظیمات مهم Heartbeat ---
    broker_heartbeat=30,  # ارسال heartbeat به بروکر هر 30 ثانیه
    # broker_heartbeat_checkrate=2.0, # (اختیاری) ضریبی برای بررسی heartbeat های از دست رفته. پیش‌فرض معمولا کافی است.

    # --- تنظیم مربوط به هشدار لاگ‌ها (اختیاری اما توصیه شده برای آینده) ---
    # اگر می‌خواهید تسک‌های طولانی در صورت قطع اتصال کنسل شوند تا سریع‌تر redeliver شوند:
    worker_cancel_long_running_tasks_on_connection_loss=True,

    beat_schedule={} # غیرفعال کردن موقت Beat برای تست
)

# ثبت تسک‌ها
celery_app.autodiscover_tasks(["app.tasks"])

if __name__ == "__main__":
    celery_app.start()