# tests/conftest.py
import sys
import os
import pytest
# import pytest_asyncio # دیگر نیازی به این نیست چون TestClient همگام است
# from httpx import AsyncClient # دیگر نیازی به این نیست

# ---> تغییر: وارد کردن TestClient از FastAPI <---
from fastapi.testclient import TestClient

# افزودن مسیر ریشه به sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

try:
    from app.main import app as fastapi_app # وارد کردن خود برنامه FastAPI
except ModuleNotFoundError as e:
    print(f"Failed to import app.main: {e}")
    print(f"Current sys.path: {sys.path}")
    pytest.exit(f"Could not find 'app' module. Is project root ({project_root}) correct and in sys.path?", returncode=1)


# ---> تغییر: استفاده از fixture همگام با TestClient <---
@pytest.fixture(scope="session")
def test_client() -> TestClient: # تایپ هینت به TestClient تغییر کرد
    """
    یک کلاینت تست همگام برای تعامل با برنامه FastAPI در تست ها ایجاد می کند.
    """
    # TestClient برنامه FastAPI را به عنوان آرگومان می گیرد
    client = TestClient(fastapi_app)
    print("Sync Test client created")
    yield client # کلاینت را در اختیار تست قرار می دهد
    print("Sync Test client closed")
    # نیازی به async with نیست چون TestClient خودش مدیریت می کند