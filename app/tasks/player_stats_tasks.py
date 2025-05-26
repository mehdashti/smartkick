# app/tasks/player_stats_tasks.py
from celery import shared_task
from app.services.player_stats_service import PlayerStatsService
from app.core.database import async_session
from celery import shared_task
import asyncio
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, name="app.tasks.player_tasks.update_player_stats_for_league_season_task")
def update_player_stats_for_league_season_task(self, league_id: int, season: int, max_pages: int = None):
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    logger.info(f"Task started: update_player_stats_for_league_season_task with league_id={league_id}, season={season}, max_pages={max_pages}")
    try:
        result = loop.run_until_complete(_update_player_stats_for_league_season(league_id, season, max_pages))
        logger.info(f"Task completed successfully: {result}")
        return {
            "status": "success",
            "message": f"Player stats update task for league {league_id}, season {season} completed successfully.",
            "details": result,  
            "task_id": self.request.id,
        }
    except Exception as e:
        logger.exception(f"Error in Celery task: {e}")
        return {
            "status": "error",
            "message": f"Failed to update player stats for league {league_id}, season {season}: {str(e)}",
            "task_id": self.request.id,
        }


async def _update_player_stats_for_league_season(league_id: int, season: int, max_pages: int = None):
    session = await async_session()
    async with session as db:
        try:
            player_stats_service = PlayerStatsService()
            players_updated, stats_updated = await player_stats_service.update_player_stats_for_league_season(
                db=db, league_id=league_id, season=season, max_pages=max_pages
            )
            await db.commit()

            return {
                "players_updated": players_updated,
                "stats_updated": stats_updated,
            }
        except Exception as e:
            await db.rollback()
            logger.exception(f"Error during async task execution: {e}")
            raise
        finally:
            await db.close()


@shared_task(bind=True, name="app.tasks.player_tasks.update_player_stats_for_season_task")
def update_player_stats_for_season_task(self, season: int, max_pages: int = None):
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    logger.info(f"Task started: update_player_stats_for_season_task with season={season}, max_pages={max_pages}")
    try:
        result = loop.run_until_complete(_update_player_stats_for_season(season, max_pages))
        logger.info(f"Task completed successfully: {result}")
        return {
            "status": "success",
            "message": f"Player stats update task for season {season} completed successfully.",
            "details": result,  
            "task_id": self.request.id,
        }
    except Exception as e:
        logger.exception(f"Error in Celery task: {e}")
        return {
            "status": "error",
            "message": f"Failed to update player stats for season {season}: {str(e)}",
            "task_id": self.request.id,
        }


async def _update_player_stats_for_season(season: int, max_pages: int = None):
    session = await async_session()
    async with session as db:
        try:
            player_stats_service = PlayerStatsService()
            players_updated, stats_updated = await player_stats_service.update_player_stats_for_season(
                db=db, season=season, max_pages=max_pages
            )
            await db.commit()

            return {
                "players_updated": players_updated,
                "stats_updated": stats_updated,
            }
        except Exception as e:
            await db.rollback()
            logger.exception(f"Error during async task execution: {e}")
            raise
        finally:
            await db.close()


@shared_task(bind=True, name="app.tasks.player_tasks.update_player_stats_for_league_task")
def update_player_stats_for_league_task(self, league_id: int, max_pages: int = None):
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    logger.info(f"Task started: update_player_stats_for_season_task with league_id={league_id}, max_pages={max_pages}")
    try:
        result = loop.run_until_complete(_update_player_stats_for_league(league_id, max_pages))
        logger.info(f"Task completed successfully: {result}")
        return {
            "status": "success",
            "message": f"Player stats update task for league {league_id} completed successfully.",
            "details": result,  
            "task_id": self.request.id,
        }
    except Exception as e:
        logger.exception(f"Error in Celery task: {e}")
        return {
            "status": "error",
            "message": f"Failed to update player stats for league {league_id}: {str(e)}",
            "task_id": self.request.id,
        }


async def _update_player_stats_for_league(league_id: int, max_pages: int = None):
    session = await async_session()
    async with session as db:
        try:
            player_stats_service = PlayerStatsService()
            players_updated, stats_updated = await player_stats_service.update_player_stats_for_league(
                db=db, league_id=league_id, max_pages=max_pages
            )
            await db.commit()

            return {
                "players_updated": players_updated,
                "stats_updated": stats_updated,
            }
        except Exception as e:
            await db.rollback()
            logger.exception(f"Error during async task execution: {e}")
            raise
        finally:
            await db.close()


@shared_task(bind=True, name="app.tasks.update_fixture_player_stats_by_id_task")
def update_fixture_player_stats_by_id_task(self, match_id: int):
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    logger.info(f"Task started: update_fixture_player_stats_by_id_task with match_id={match_id}")
    try:
        result = loop.run_until_complete(_update_fixture_player_stats_by_id(match_id))
        logger.info(f"Task completed successfully: {result}")
        return {
            "status": "success",
            "message": f"Player stats update task for match_id {match_id} completed successfully.",
            "details": result,  
            "task_id": self.request.id,
        }
    except Exception as e:
        logger.exception(f"Error in Celery task: {e}")
        return {
            "status": "error",
            "message": f"Failed to update player stats for match_id {match_id}: {str(e)}",
            "task_id": self.request.id,
        }


async def _update_fixture_player_stats_by_id(match_id: int):
    session = await async_session()
    async with session as db:
        try:
            player_stats_service = PlayerStatsService()
            players_updated, stats_updated = await player_stats_service.update_fixture_player_stats_by_id(
                db=db, match_id=match_id
            )
            await db.commit()

            return {
                "players_updated": players_updated,
                "stats_updated": stats_updated,
            }
        except Exception as e:
            await db.rollback()
            logger.exception(f"Error during async task execution: {e}")
            raise
        finally:
            await db.close()
