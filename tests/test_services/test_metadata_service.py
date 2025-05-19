# tests/unit/test_metadata_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch # یا از mocker فیکسچر pytest-mock
import httpx

from app.services.metadata_service import MetadataService
from app.schemas.timezone import TimezoneOut
from app.models.timezone import Timezone # برای ساخت داده‌های mock
from datetime import datetime

@pytest.fixture
def metadata_service():
    return MetadataService()

# --- تست get_timezones_from_db ---
@pytest.mark.asyncio
async def test_get_timezones_from_db_success(metadata_service: MetadataService, mocker):
    """Tests successfully getting timezones and converting to schemas."""
    mock_db_session = AsyncMock()
    mock_repo_instance = AsyncMock()
    now = datetime.utcnow()
    mock_db_objects = [
        Timezone(id=1, name="A", created_at=now, updated_at=now),
        Timezone(id=2, name="B", created_at=now, updated_at=now),
    ]
    mock_repo_instance.get_all_timezones.return_value = mock_db_objects

    # Mock کردن ساخت ریپازیتوری
    mocker.patch('app.services.metadata_service.TimezoneRepository', return_value=mock_repo_instance)

    result = await metadata_service.get_timezones_from_db(mock_db_session)

    assert len(result) == 2
    assert isinstance(result[0], TimezoneOut)
    assert result[0].name == "A"
    assert result[1].id == 2
    mock_repo_instance.get_all_timezones.assert_awaited_once()

@pytest.mark.asyncio
async def test_get_timezones_from_db_repo_error(metadata_service: MetadataService, mocker):
    """Tests handling of exceptions from the repository."""
    mock_db_session = AsyncMock()
    mock_repo_instance = AsyncMock()
    mock_repo_instance.get_all_timezones.side_effect = Exception("DB connection lost")

    mocker.patch('app.services.metadata_service.TimezoneRepository', return_value=mock_repo_instance)

    with pytest.raises(Exception, match="Database error occurred"):
        await metadata_service.get_timezones_from_db(mock_db_session)

# --- تست update_timezones_from_api ---
@pytest.mark.asyncio
async def test_update_timezones_from_api_success(metadata_service: MetadataService, mocker):
    """Tests successful update process."""
    mock_db_session = AsyncMock()
    mock_repo_instance = AsyncMock()
    mock_repo_instance.replace_all_timezones.return_value = 3 # تعداد درج شده

    mock_api_client = AsyncMock()
    api_data = ["Europe/London", "Asia/Tokyo", "UTC"]
    # Mock کردن تابع fetch_timezones_from_api در ماژول api_clients.api_football
    mocker.patch('app.services.metadata_service.api_football.fetch_timezones_from_api', return_value=api_data)
    mocker.patch('app.services.metadata_service.TimezoneRepository', return_value=mock_repo_instance)

    result_count = await metadata_service.update_timezones_from_api(mock_db_session)

    assert result_count == 3
    # بررسی اینکه تابع API و ریپازیتوری با مقادیر درست فراخوانی شده‌اند
    mocker.patch('app.services.metadata_service.api_football.fetch_timezones_from_api').assert_awaited_once()
    mock_repo_instance.replace_all_timezones.assert_awaited_once_with(api_data)

@pytest.mark.asyncio
async def test_update_timezones_from_api_empty_list(metadata_service: MetadataService, mocker):
    """Tests handling empty list from API."""
    mock_db_session = AsyncMock()
    mock_repo_instance = AsyncMock()

    mocker.patch('app.services.metadata_service.api_football.fetch_timezones_from_api', return_value=[])
    mocker.patch('app.services.metadata_service.TimezoneRepository', return_value=mock_repo_instance)

    result_count = await metadata_service.update_timezones_from_api(mock_db_session)

    assert result_count == 0
    # ریپازیتوری نباید فراخوانی شود
    mock_repo_instance.replace_all_timezones.assert_not_awaited()

@pytest.mark.asyncio
async def test_update_timezones_from_api_api_error(metadata_service: MetadataService, mocker):
    """Tests handling API client errors."""
    mock_db_session = AsyncMock()
    mock_repo_instance = AsyncMock()

    # شبیه‌سازی خطای شبکه از API client
    mocker.patch('app.services.metadata_service.api_football.fetch_timezones_from_api', side_effect=httpx.RequestError("Network error"))
    mocker.patch('app.services.metadata_service.TimezoneRepository', return_value=mock_repo_instance)

    with pytest.raises(httpx.RequestError):
        await metadata_service.update_timezones_from_api(mock_db_session)

    mock_repo_instance.replace_all_timezones.assert_not_awaited()

@pytest.mark.asyncio
async def test_update_timezones_from_api_repo_error(metadata_service: MetadataService, mocker):
    """Tests handling repository errors during update."""
    mock_db_session = AsyncMock()
    mock_repo_instance = AsyncMock()
    mock_repo_instance.replace_all_timezones.side_effect = Exception("DB write failed")

    api_data = ["Data/From/API"]
    mocker.patch('app.services.metadata_service.api_football.fetch_timezones_from_api', return_value=api_data)
    mocker.patch('app.services.metadata_service.TimezoneRepository', return_value=mock_repo_instance)

    with pytest.raises(Exception, match="DB write failed"):
        await metadata_service.update_timezones_from_api(mock_db_session)

    mock_repo_instance.replace_all_timezones.assert_awaited_once_with(api_data)
