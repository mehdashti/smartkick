# app/services/metadata_service.py
from typing import List
from app.api_clients import api_football # وارد کردن ماژول کلاینت
from app.api_clients.errors import APIFootballError

class MetadataService:
    async def get_timezones(self) -> List[str]:
        """
        لیست Timezone های موجود را دریافت می‌کند.
        (در آینده می‌تواند شامل کشینگ باشد)
        """
        print("[Service] Requesting timezones...")
        try:
            timezones = await api_football.fetch_timezones_from_api()
            print(f"[Service] Received {len(timezones)} timezones.")
            # در اینجا می‌توانید منطق کشینگ اضافه کنید اگر لازم است
            # مثلا نتیجه را برای مدتی در Redis یا حافظه ذخیره کنید
            return timezones
        except APIFootballError as e:
            # خطا را برای روتر ارسال می‌کنیم تا مدیریت کند
            print(f"[Service] Error getting timezones: {e}")
            raise # Re-raise the error

# یک نمونه از سرویس یا تابع Depends برای تزریق آن
metadata_service_instance = MetadataService()

def get_metadata_service():
    return metadata_service_instance