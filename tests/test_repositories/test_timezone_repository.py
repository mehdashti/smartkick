# tests/integration/test_timezone_repository.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.timezone import Timezone
from app.repositories.timezone_repository import TimezoneRepository

# --- فیکسچر برای ایجاد session دیتابیس تستی ---
# (این بخش به نحوه راه‌اندازی دیتابیس تستی شما بستگی دارد)
# مثال ساده با استفاده از pytest-asyncio و یک engine تستی
@pytest.fixture
async def test_db_session(async_engine): # فرض کنید async_engine تعریف شده
    async with AsyncSession(async_engine) as session:
        # شروع تراکنش برای هر تست
        async with session.begin():
            yield session
        # Rollback خودکار بعد از yield (اگر از begin استفاده شود)
        # یا session.rollback() اگر begin استفاده نشود

@pytest.fixture
async def timezone_repo(test_db_session: AsyncSession):
    return TimezoneRepository(test_db_session)

# --- تست‌ها ---
@pytest.mark.asyncio
async def test_get_all_timezones_empty(timezone_repo: TimezoneRepository):
    """Tests getting timezones when the table is empty."""
    timezones = await timezone_repo.get_all_timezones()
    assert timezones == []

@pytest.mark.asyncio
async def test_get_all_timezones_with_data(timezone_repo: TimezoneRepository, test_db_session: AsyncSession):
    """Tests getting timezones when data exists."""
    # 1. Add test data directly
    tz1 = Timezone(name="Asia/Dubai")
    tz2 = Timezone(name="Europe/Paris")
    test_db_session.add_all([tz1, tz2])
    await test_db_session.flush() # Save to DB within the transaction

    # 2. Call the repository method
    timezones = await timezone_repo.get_all_timezones()

    # 3. Assert results
    assert len(timezones) == 2
    # Results should be ordered by name
    assert timezones[0].name == "Asia/Dubai"
    assert timezones[1].name == "Europe/Paris"

@pytest.mark.asyncio
async def test_replace_all_timezones_from_empty(timezone_repo: TimezoneRepository, test_db_session: AsyncSession):
    """Tests replacing timezones when the table is initially empty."""
    new_names = ["UTC", "Africa/Cairo"]
    inserted_count = await timezone_repo.replace_all_timezones(new_names)

    assert inserted_count == 2

    # Verify data in DB
    result = await test_db_session.execute(select(Timezone).order_by(Timezone.name))
    all_tz = result.scalars().all()
    assert len(all_tz) == 2
    assert all_tz[0].name == "Africa/Cairo"
    assert all_tz[1].name == "UTC"

@pytest.mark.asyncio
async def test_replace_all_timezones_with_existing(timezone_repo: TimezoneRepository, test_db_session: AsyncSession):
    """Tests replacing timezones when data already exists."""
    # 1. Add initial data
    initial_tz = Timezone(name="Old/Zone")
    test_db_session.add(initial_tz)
    await test_db_session.flush()

    # 2. Call replace method
    new_names = ["America/Los_Angeles", "Asia/Tokyo", "America/Los_Angeles"] # Duplicate
    inserted_count = await timezone_repo.replace_all_timezones(new_names)

    # Should only insert unique names
    assert inserted_count == 2

    # 3. Verify data in DB (only new ones should exist)
    result = await test_db_session.execute(select(Timezone).order_by(Timezone.name))
    all_tz = result.scalars().all()
    assert len(all_tz) == 2
    assert all_tz[0].name == "America/Los_Angeles"
    assert all_tz[1].name == "Asia/Tokyo"
    # Verify 'Old/Zone' is gone
    assert not any(tz.name == "Old/Zone" for tz in all_tz)

@pytest.mark.asyncio
async def test_replace_all_timezones_with_empty_list(timezone_repo: TimezoneRepository, test_db_session: AsyncSession):
    """Tests replacing timezones with an empty list (should delete all)."""
    # 1. Add initial data
    initial_tz = Timezone(name="To/Be/Deleted")
    test_db_session.add(initial_tz)
    await test_db_session.flush()

    # 2. Call replace method with empty list
    inserted_count = await timezone_repo.replace_all_timezones([])

    assert inserted_count == 0

    # 3. Verify data in DB (should be empty)
    result = await test_db_session.execute(select(Timezone))
    all_tz = result.scalars().all()
    assert len(all_tz) == 0
