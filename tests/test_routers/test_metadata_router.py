# tests/routers/test_metadata_router.py
# import pytest # دیگر نیازی به pytest.mark.asyncio نیست
from fastapi.testclient import TestClient # برای type hinting (اختیاری ولی خوب)

# ---> تغییر: تابع تست دیگر async نیست <---
def test_get_timezones_success(test_client: TestClient): # دریافت test_client همگام
    """
    تست موفقیت آمیز دریافت لیست timezone ها با TestClient.
    """
    # ---> تغییر: دیگر نیازی به await نیست <---
    response = test_client.get("/meta/timezones")

    # بررسی کد وضعیت موفقیت آمیز
    assert response.status_code == 200

    # بررسی اینکه پاسخ JSON است
    response_data = response.json()
    assert isinstance(response_data, list)

    # بررسی اینکه لیست خالی نیست
    assert len(response_data) > 0

    # بررسی اینکه حداقل یکی از آیتم ها رشته است
    assert isinstance(response_data[0], str)
    assert "Europe/London" in response_data # مثال

# تست خطا همچنان نیاز به Mocking دارد که در آینده انجام می دهیم
# def test_get_timezones_api_error(test_client: TestClient, mocker):
#     """تست مدیریت خطا (نیاز به Mocking)"""
#     pass