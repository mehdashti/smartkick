# app/repositories/league_repository.py
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select # Import select

from app.models.league import League # مدل League
# ممکن است به مدل Country هم نیاز باشد اگر بخواهیم مستقیما با آن کار کنیم، ولی فعلا لازم نیست
import logging

logger = logging.getLogger(__name__)

class LeagueRepository:
    def __init__(self, db_session: AsyncSession):
        self.db: AsyncSession = db_session

    async def bulk_upsert_leagues(self, leagues_data: List[Dict[str, Any]]) -> int:
        """
        لیگ‌ها و فصل‌های آن‌ها را به صورت دسته‌ای درج یا آپدیت (Upsert) می‌کند.
        از یک قید UNIQUE بر روی (external_id, season) استفاده می‌کند.

        Args:
            leagues_data: لیستی از دیکشنری‌ها، هر کدام شامل فیلدهای مدل League
                          (به جز league_id, created_at, updated_at).
                          باید شامل 'external_id' و 'season' باشد.

        Returns:
            تعداد رکوردهایی که درج یا آپدیت شدند (تقریبی).
        """
        if not leagues_data:
            logger.warning("Received empty list for league upsert.")
            return 0

        logger.info(f"Attempting to bulk upsert {len(leagues_data)} league/season entries.")

        # ساخت دستور INSERT ... ON CONFLICT DO UPDATE
        # مقادیر ورودی باید دیکشنری هایی با کلیدهای مطابق نام ستون های مدل باشند
        insert_stmt = insert(League).values(leagues_data)

        # تعریف ستون هایی که در صورت تداخل آپدیت می شوند
        # همه چیز به جز کلیدهای اصلی (external_id, season) و country_id (که نباید تغییر کند)
        update_dict = {
            "name": insert_stmt.excluded.name,
            "is_current": insert_stmt.excluded.is_current,
            "type": insert_stmt.excluded.type,
            "start_date": insert_stmt.excluded.start_date,
            "end_date": insert_stmt.excluded.end_date,
            "logo_url": insert_stmt.excluded.logo_url,
            "has_standings": insert_stmt.excluded.has_standings,
            "has_players": insert_stmt.excluded.has_players,
            "has_top_scorers": insert_stmt.excluded.has_top_scorers,
            "has_top_assists": insert_stmt.excluded.has_top_assists,
            "has_top_cards": insert_stmt.excluded.has_top_cards,
            "has_injuries": insert_stmt.excluded.has_injuries,
            "has_predictions": insert_stmt.excluded.has_predictions,
            "has_odds": insert_stmt.excluded.has_odds,
            "has_events": insert_stmt.excluded.has_events,
            "has_lineups": insert_stmt.excluded.has_lineups,
            "has_fixture_stats": insert_stmt.excluded.has_fixture_stats,
            "has_player_stats": insert_stmt.excluded.has_player_stats,
            # updated_at به طور خودکار توسط onupdate=func.now() به‌روز می‌شود
        }

        # ---> مهم: اطمینان حاصل کنید که یک قید UNIQUE در دیتابیس روی ستون های (external_id, season) وجود دارد <---
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=['external_id', 'season'], # کلیدهای ترکیبی برای تشخیص تداخل
            set_=update_dict # دیکشنری مقادیر برای آپدیت
        )

        # اجرای دستور Upsert
        try:
            result = await self.db.execute(upsert_stmt)


            # rowcount ممکن است دقیق نباشد، اما نشان دهنده اجراست
            processed_count = result.rowcount if result.rowcount is not None else len(leagues_data)
            logger.info(f"Bulk upsert for leagues/seasons finished. Processed approximately {processed_count} rows.")
            return processed_count

        except Exception as e:
            # لاگ کردن خطای احتمالی در زمان اجرای کوئری upsert
            logger.exception(f"Error during league bulk upsert execution: {e}")
            raise e # خطا را دوباره raise کن

    # می توانید توابع دیگری برای خواندن لیگ ها اضافه کنید (مثلا get_league_by_id, get_all_leagues)
    # که از مدل ها و اسکیماهای Out استفاده خواهند کرد
    # async def get_league_by_external_id_and_season(self, external_id: int, season: int) -> Optional[League]:
    #     ...