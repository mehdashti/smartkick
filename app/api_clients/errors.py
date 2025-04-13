# app/api_clients/errors.py

class APIFootballError(Exception):
    """
    خطای پایه برای تمام مشکلات مربوط به ارتباط یا پردازش داده‌های API-Football.
    تمام خطاهای سفارشی دیگر در این ماژول باید از این کلاس ارث‌بری کنند.
    """
    def __init__(self, message: str = "خطایی در ارتباط با API-Football رخ داد."):
        self.message = message
        super().__init__(self.message)

class PlayerNotFoundError(APIFootballError):
    """
    خطا هنگامی که بازیکنی با مشخصات داده شده در API-Football یافت نمی‌شود.
    """
    def __init__(self, player_id: int, season: str, message: str = ""):
        if not message:
            message = f"بازیکنی با ID {player_id} در فصل {season} در API-Football یافت نشد."
        self.player_id = player_id
        self.season = season
        super().__init__(message)

class GameNotFoundError(APIFootballError):
    """
    خطا هنگامی که بازی با مشخصات داده شده در API-Football یافت نمی‌شود.
    """
    def __init__(self, game_id: int, message: str = ""):
        if not message:
            message = f"بازی با ID {game_id} در API-Football یافت نشد."
        self.game_id = game_id
        super().__init__(message)

class InvalidAPIResponseError(APIFootballError):
    """
    خطا هنگامی که ساختار پاسخ دریافت شده از API-Football معتبر یا مورد انتظار نیست.
    """
    def __init__(self, message: str = "پاسخ دریافت شده از API-Football ساختار نامعتبر یا غیرمنتظره‌ای دارد."):
        super().__init__(message)

# می‌توانید خطاهای خاص دیگری را نیز در صورت نیاز اضافه کنید، مثلاً:
# class APILimitExceededError(APIFootballError):
#     """خطا برای زمانی که محدودیت تعداد درخواست API رد شده است (e.g., 429 Too Many Requests)."""
#     pass

# class APIAuthenticationError(APIFootballError):
#     """خطا برای مشکلات احراز هویت با API (e.g., 401 Unauthorized, 403 Forbidden)."""
#     pass