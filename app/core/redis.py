# app/core/redis.py
import redis.asyncio as redis # <<< تغییر کلیدی: استفاده از ماژول asyncio
from app.core.config import settings

def get_redis_client():
    # از redis.asyncio.Redis یا redis.asyncio.from_url استفاده کنید
    return redis.Redis( # <<< تغییر کلیدی: این حالا یک کلاینت ناهمگام است
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        decode_responses=True # این پارامتر برای کلاینت ناهمگام هم معتبر است
    )

    # یا اگر REDIS_URL را در تنظیمات دارید:
    # return redis.from_url(
    #     settings.REDIS_URL,
    #     decode_responses=True
    # )


# یک نمونه global برای استفاده در سراسر برنامه
# این redis_client حالا یک کلاینت ناهمگام خواهد بود.
redis_client = get_redis_client()

# توابع اضافی (اختیاری) برای مدیریت اتصال در برنامه‌های بزرگتر (مثلا با FastAPI)
# async def connect_redis():
#     global redis_client
#     redis_client = get_redis_client()
#     # می‌توانید یک پینگ برای اطمینان از اتصال ارسال کنید
#     # await redis_client.ping()
#     # logger.info("Connected to Redis")

# async def close_redis():
#     if redis_client:
#         await redis_client.close()
#         # logger.info("Redis connection closed")