# tests/routers/test_teams_router.py
from fastapi.testclient import TestClient
# از مدل ها یا تایپ های لازم برای بررسی پاسخ استفاده کنید (اختیاری ولی خوب)
# from app.models.team import TeamInfo # مثال

# --- تست اندپوینت /teams/{team_id} ---

def test_get_team_info_success(test_client: TestClient):
    """تست دریافت موفقیت آمیز اطلاعات یک تیم موجود."""
    team_id = 33 # ID منچستر یونایتد (فرض می کنیم در API موجود است)
    response = test_client.get(f"/teams/{team_id}")

    assert response.status_code == 200
    response_data = response.json()

    # بر اساس کد API Client شما که response_list[0] را برمی گرداند:
    assert isinstance(response_data, dict)
    # بررسی های دقیق تر روی ساختار:
    assert "team" in response_data
    assert "venue" in response_data # یا فیلدهای دیگر مورد انتظار
    assert response_data["team"]["id"] == team_id
    assert response_data["team"]["name"] == "Manchester United" # یا نام صحیح تیم

def test_get_team_info_not_found(test_client: TestClient):
    """تست دریافت اطلاعات تیمی که وجود ندارد (انتظار 404)."""
    team_id = 999999999 # یک ID نامعتبر
    response = test_client.get(f"/teams/{team_id}")

    # انتظار داریم سرویس/روتر خطای LookupError کلاینت را به 404 تبدیل کند
    assert response.status_code == 404
    response_data = response.json()
    assert "detail" in response_data
    assert "not found" in response_data["detail"].lower()

def test_get_team_info_invalid_id(test_client: TestClient):
    """تست با ID نامعتبر (رشته به جای عدد - انتظار 422)."""
    team_id = "invalid-team-id"
    response = test_client.get(f"/teams/{team_id}")

    # FastAPI باید به طور خودکار ورودی نامعتبر را رد کند
    assert response.status_code == 422

# TODO: تست برای زمانی که API خارجی خطا برمی گرداند (نیاز به Mocking دارد)
# def test_get_team_info_api_error(test_client: TestClient, mocker):
#    pass