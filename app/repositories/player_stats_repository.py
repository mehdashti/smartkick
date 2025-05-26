from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.player_season_stats import PlayerSeasonStats as DBPlayerSeasonStats
from app.models.player_fixture_stats import PlayerFixtureStats as DBPlayerFixtureStats
import logging

logger = logging.getLogger(__name__)

class PlayerStatsRepository:
    def __init__(self, db_session: AsyncSession):
        self.db: AsyncSession = db_session

    async def bulk_upsert_stats(self, stats_data: List[Dict[str, Any]]) -> int:
        """
        آمار فصلی بازیکنان را به صورت دسته‌ای درج یا آپدیت (Upsert) می‌کند.
        از قید UNIQUE بر روی (player_id, team_id, league_id, season) استفاده می‌کند.
        """
        if not stats_data:
            logger.warning("Received empty list for player season stats bulk upsert.")
            return 0

        logger.info(f"Attempting to bulk upsert {len(stats_data)} player season stats entries.")

        insert_stmt = pg_insert(DBPlayerSeasonStats).values(stats_data)

        # ستون‌هایی که باید در صورت وجود به‌روزرسانی شوند
        update_columns = {
            col.name: getattr(insert_stmt.excluded, col.name)
            for col in DBPlayerSeasonStats.__table__.columns
            if col.name not in ['stat_id', 'player_id', 'team_id', 'league_id', 'season', 'created_at']
        }

        upsert_stmt = insert_stmt.on_conflict_do_update(
            constraint='uq_player_team_league_season_stats',  # نام constraint
            set_=update_columns
        )

        try:
            result = await self.db.execute(upsert_stmt)
            processed_count = result.rowcount if result.rowcount is not None else len(stats_data)
            logger.info(f"Bulk player season stats upsert finished. Processed approximately {processed_count} rows.")

            # اضافه کردن commit برای ذخیره تغییرات
            await self.db.commit()

            return processed_count
        except Exception as e:
            logger.exception(f"Error during player season stats bulk upsert execution: {e}")
            await self.db.rollback()  # در صورت خطا، rollback انجام شود
            raise



    async def bulk_upsert_player_fixture_stats(self, stats_data: Dict[str, Any]) -> int:

        if not stats_data:
            logger.warning("Received empty list for player season stats bulk upsert.")
            return 0

        logger.info(f"Attempting to bulk upsert {len(stats_data)} player season stats entries.")

        insert_stmt = pg_insert(DBPlayerFixtureStats).values(stats_data)

        # ستون‌هایی که باید در صورت وجود به‌روزرسانی شوند
        update_columns = {
            col.name: getattr(insert_stmt.excluded, col.name)
            for col in DBPlayerFixtureStats.__table__.columns
            if col.name not in ['stat_id', 'player_id', 'team_id', 'match_id', 'created_at']
        }

        upsert_stmt = insert_stmt.on_conflict_do_update(
            constraint='uq_player_fixture_team_stats',  # نام constraint
            set_=update_columns
        )

        try:
            result = await self.db.execute(upsert_stmt)
            processed_count = result.rowcount if result.rowcount is not None else len(stats_data)
            logger.info(f"Bulk player season stats upsert finished. Processed approximately {processed_count} rows.")

            # اضافه کردن commit برای ذخیره تغییرات
            await self.db.commit()

            return processed_count
        except Exception as e:
            logger.exception(f"Error during player season stats bulk upsert execution: {e}")
            await self.db.rollback()  # در صورت خطا، rollback انجام شود
            raise