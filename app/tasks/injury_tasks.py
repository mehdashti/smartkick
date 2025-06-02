# app/tasks/injury_tasks.py
from celery import shared_task
from app.services.injury_service import InjuryService
from app.core.database import async_session
import logging
import asyncio
from app.repositories.league_repository import LeagueRepository
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

@shared_task(bind=True, name="app.tasks.injury_tasks.update_injuries_by_league_season_task")
def update_injuries_by_league_season_task(self, league_id: int, season: int):
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    logger.info(f"Task started: update_injuries_by_league_season_task with league_id={league_id}, season={season}")
    try:
        result = loop.run_until_complete(_update_injuries_by_league_season(league_id, season))
        logger.info(f"Task completed successfully: {result}")
        return {
            "status": "success",
            "message": f"Injuries update task for league {league_id}, season {season} completed successfully.",
            "task_id": self.request.id,  
        }
    except Exception as e:
        logger.exception(f"Error in Celery task: {e}")
        return {
            "status": "error",
            "message": f"Failed to update injuries for league {league_id}, season {season}: {e}",
            "task_id": self.request.id, 
        }

async def _update_injuries_by_league_season(league_id: int, season: int):
    session = await async_session() 
    async with session as db:
        try:
            injury_service = InjuryService()
            updated_count = await injury_service.update_injuries_by_league_season(db=db, league_id=league_id, season=season)
            await db.commit() 

            return {
                "status": "success",
                "teams_updated": updated_count,
            }
        except Exception as e:
            await db.rollback()  
            logger.exception(f"Error during async task execution: {e}")
            raise
        finally:
            await session.close()


@shared_task(bind=True, name="app.tasks.injury_tasks.update_injuries_current_leagues_task")
def update_injuries_current_leagues_task(self):
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    logger.info(f"Task started: update_injuries_current_leagues_task")
    try:
        result = loop.run_until_complete(_update_injuries_current_leagues())
        logger.info(f"Task completed successfully: {result}")
        return {
            "status": "success",
            "message": f"Injuries update task for current leagues completed successfully.",
            "task_id": self.request.id,  
        }
    except Exception as e:
        logger.exception(f"Error in Celery task: {e}")
        return {
            "status": "error",
            "message": f"Failed to update injuries for current leagues: {e}",
            "task_id": self.request.id, 
        }

async def _update_injuries_current_leagues():
    session = await async_session()
    async with session as db:
        leagues_list = await LeagueRepository(db).get_current_leagues()

        all_results = [] 

        for league in leagues_list: 
            league_id = league.league_id
            season = league.season
            logger.info(f"Processing league_id={league_id}, season={season} in _update_injuries_current_leagues") # لاگ برای پیگیری
            try:
                injury_service = InjuryService()
 
                updated_count_for_league = await injury_service.update_injuries_by_league_season(db=db, league_id=league_id, season=season)
                await db.commit() 

                all_results.append({ 
                    "league_id": league_id,
                    "season": season,
                    "status": "success",
                    "teams_updated": updated_count_for_league,
                })

            except Exception as e:
                await db.rollback()
                logger.exception(f"Error processing league_id={league_id}, season={season}: {e}")
                all_results.append({ 
                    "league_id": league_id,
                    "season": season,
                    "status": "error",
                    "error_message": str(e),
                })

        return all_results 


@shared_task(bind=True, name="app.tasks.injury_tasks.update_injuries_by_ids_task")
def update_injuries_by_ids_task(self, match_ids: List[int]):
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    logger.info(f"Task started: update_injuries_by_ids_task with match_ids={match_ids}")
    try:
        result = loop.run_until_complete(_update_injuries_by_ids(match_ids))
        logger.info(f"Task completed successfully: {result}")
        return {
            "status": "success",
            "message": f"Injuries update task for match_ids {match_ids} completed successfully.",
            "task_id": self.request.id,  
        }
    except Exception as e:
        logger.exception(f"Error in Celery task: {e}")
        return {
            "status": "error",
            "message": f"Failed to update injuries for match_ids {match_ids},: {e}",
            "task_id": self.request.id, 
        }

async def _update_injuries_by_ids(match_ids: List[int]):
    session = await async_session() 
    async with session as db:
        try:
            injury_service = InjuryService()
            updated_count = await injury_service.update_injuries_by_ids(db=db, match_ids=match_ids)
            await db.commit() 

            return {
                "status": "success",
                "teams_updated": updated_count,
            }
        except Exception as e:
            await db.rollback()  
            logger.exception(f"Error during async task execution: {e}")
            raise
        finally:
            await session.close()