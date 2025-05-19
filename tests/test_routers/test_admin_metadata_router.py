# tests/integration/test_admin_metadata_router.py
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import httpx

# --- فیکسچر برای TestClient ---
# (نیاز به فایل اصلی app یا ساخت app تستی دارید)
# from app.main import app # فرض کنید app اصلی شما اینجاست
# client = TestClient(app)

# --- فرض کنید یک app تستی ساخته‌اید ---
@pytest.fixture
def test_app(mocker):
    # Mock کردن وابستگی دیتابیس و سرویس در سطح app (اگر لازم باشد)
    # این بخش پیچیده‌تر است و به ساختار app شما بستگی دارد
    # ساده‌ترین راه: Mock کردن مستقیم سرویس در هر تست
    from fastapi import FastAPI
    from app.routers.admin.update_metadata import router as metadata_router
    app = FastAPI()
    app.include_router(metadata_router)
    # اینجا می‌توانید وابستگی‌های امنیتی را هم override کنید اگر فعال بودند
    return app

@pytest.fixture
def client(test_app):
    return TestClient(test_app)

# --- تست‌ها ---
def test_trigger_timezone_update_success(client: TestClient, mocker):
    """Tests successful timezone update via API endpoint."""
    # Mock کردن متد سرویس
    mock_service_method = mocker.patch(
        'app.routers.admin.update_metadata.MetadataService.update_timezones_from_api',
        return_value=5 # تعداد آپدیت شده
    )
    # Mock کردن وابستگی دیتابیس (اگر لازم است، گاهی TestClient خودش مدیریت می‌کند)
    # mocker.patch('app.routers.admin.update_metadata.get_async_db_session', return_value=AsyncMock())

    response = client.post("/admin/metadata/update-timezones")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "Timezone update process finished successfully.", "count": 5}
    mock_service_method.assert_awaited_once()

def test_trigger_timezone_update_api_error(client: TestClient, mocker):
    """Tests API endpoint handling external API errors."""
    mock_service_method = mocker.patch(
        'app.routers.admin.update_metadata.MetadataService.update_timezones_from_api',
        side_effect=httpx.TimeoutException("Request timed out")
    )

    response = client.post("/admin/metadata/update-timezones")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "Could not connect to the external API" in response.json()["detail"]
    assert "TimeoutException" in response.json()["detail"]
    mock_service_method.assert_awaited_once()

def test_trigger_timezone_update_internal_error(client: TestClient, mocker):
    """Tests API endpoint handling unexpected internal errors."""
    mock_service_method = mocker.patch(
        'app.routers.admin.update_metadata.MetadataService.update_timezones_from_api',
        side_effect=Exception("Something went wrong")
    )

    response = client.post("/admin/metadata/update-timezones")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "An unexpected internal error occurred" in response.json()["detail"]
    assert "Exception" in response.json()["detail"]
    mock_service_method.assert_awaited_once()

# --- تست‌های مربوط به احراز هویت ادمین ---
# اگر وابستگی require_admin_user فعال بود، باید تست‌های بیشتری بنویسید:
# 1. تستی که بدون توکن معتبر ادمین 401 یا 403 برمی‌گرداند.
# 2. تستی که با توکن معتبر ادمین 200 برمی‌گرداند (نیاز به override وابستگی امنیتی دارد).
