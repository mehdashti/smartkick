# tests/routers/test_players_router.py
from fastapi.testclient import TestClient
# از مدل ها یا تایپ های لازم برای بررسی پاسخ استفاده کنید (اختیاری ولی خوب)
# from app.models.player import PlayerTeamInfo # مثال

# --- تست اندپوینت /players/{player_id}/teams ---

def test_get_player_teams_success(test_client: TestClient):
    """تست دریافت موفقیت آمیز تیم های یک بازیکن موجود."""
    player_id = 874 # ID کریستیانو رونالدو (فرض می کنیم در API موجود است)
    response = test_client.get(f"/players/{player_id}/teams")

    assert response.status_code == 200
    response_data = response.json()

    # --- شروع اصلاح بررسی ها ---
    # بر اساس لاگ خطا، تابع fetch_player_teams اولین عنصر لیست response را برگرداند
    # که یک دیکشنری شامل کلیدهای 'team' و 'seasons' بود.
    assert isinstance(response_data, dict) # بررسی نوع کلی پاسخ

    # بررسی وجود کلیدهای اصلی در پاسخ
    assert "team" in response_data
    assert "seasons" in response_data

    # بررسی جزئیات داخل کلید 'team'
    assert isinstance(response_data["team"], dict)
    assert "id" in response_data["team"]
    assert "name" in response_data["team"]
    assert "logo" in response_data["team"]
    # مثال: بررسی مقدار خاص (اختیاری)
    # assert response_data["team"]["id"] == 2939
    # assert response_data["team"]["name"] == "Al-Nassr"

    # بررسی جزئیات داخل کلید 'seasons'
    assert isinstance(response_data["seasons"], list)
    # مثال: بررسی اینکه لیست فصل ها خالی نیست (اگر همیشه باید باشد)
    # assert len(response_data["seasons"]) > 0
    # مثال: بررسی نوع اعضای لیست فصل ها (اگر ساختار دقیقش را می دانید)
    # assert isinstance(response_data["seasons"][0], int) # اگر فقط سال است
    # assert isinstance(response_data["seasons"][0], dict) # اگر دیکشنری با جزئیات است
    # --- پایان اصلاح بررسی ها ---


def test_get_player_teams_not_found(test_client: TestClient):
    """تست دریافت تیم های بازیکنی که وجود ندارد (انتظار 404)."""
    player_id = 999999999 # یک ID نامعتبر
    response = test_client.get(f"/players/{player_id}/teams")

    # انتظار داریم سرویس/روتر خطای LookupError کلاینت را به 404 تبدیل کند
    assert response.status_code == 404
    response_data = response.json()
    assert "detail" in response_data
    # می توانید پیام خطا را دقیق تر بررسی کنید
    assert "not found" in response_data["detail"].lower()

def test_get_player_teams_invalid_id(test_client: TestClient):
    """تست با ID نامعتبر (رشته به جای عدد - انتظار 422)."""
    player_id = "invalid-player-id"
    response = test_client.get(f"/players/{player_id}/teams")

    # FastAPI باید به طور خودکار ورودی نامعتبر را رد کند
    assert response.status_code == 422
    # می توانید ساختار خطای 422 را هم بررسی کنید


# TODO: تست برای زمانی که API خارجی خطا برمی گرداند (نیاز به Mocking دارد)
# def test_get_player_teams_api_error(test_client: TestClient, mocker):
#    pass