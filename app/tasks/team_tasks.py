from celery import shared_task
from app.services.team_service import TeamService
from app.core.database import async_session
import logging
import asyncio

logger = logging.getLogger(__name__)

@shared_task(bind=True, name="app.tasks.team_tasks.update_teams_by_league_season_task")
def update_teams_by_league_season_task(self, league_id: int, season: int):
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    logger.info(f"Task started: update_teams_by_league_season_task with league_id={league_id}, season={season}")
    try:
        result = loop.run_until_complete(_update_teams_by_league_season(league_id, season))
        logger.info(f"Task completed successfully: {result}")
        return {
            "status": "success",
            "message": f"Team/Venue update task for league {league_id}, season {season} completed successfully.",
            "task_id": self.request.id,  
        }
    except Exception as e:
        logger.exception(f"Error in Celery task: {e}")
        return {
            "status": "error",
            "message": f"Failed to update teams for league {league_id}, season {season}: {e}",
            "task_id": self.request.id,  # اضافه کردن task_id حتی در صورت خطا
        }

async def _update_teams_by_league_season(league_id: int, season: int):
    session = await async_session() 
    async with session as db:
        try:
            team_service = TeamService()
            updated_count = await team_service.update_teams_by_league_season(db=db, league_id=league_id, season=season)
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

@shared_task(bind=True, name="app.tasks.team_tasks.update_team_by_id_task")
def update_team_by_id_task(self, team_id: int):
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    logger.info(f"Task started: update_team_by_id_task with team_id={team_id}")
    try:
        result = loop.run_until_complete(_update_team_by_id(team_id))
        logger.info(f"Task completed successfully for team ID={team_id}.")
        return {
            "status": "success",
            "message": f"Team update task for ID={team_id} completed successfully.",
            "task_id": self.request.id,
        }
    except Exception as e:
        logger.exception(f"Error in Celery task: {e}")
        return {
            "status": "error",
            "message": f"Failed to update team for ID={team_id}: {e}",
            "task_id": self.request.id,
        }

@shared_task(bind=True, name="app.tasks.team_tasks.update_teams_by_country_task")
def update_teams_by_country_task(self, country_name: str):
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    logger.info(f"Task started: update_teams_by_country_task with country_name={country_name}")
    try:
        result = loop.run_until_complete(_update_teams_by_country(country_name))
        logger.info(f"Task completed successfully for country '{country_name}'.")
        return {
            "status": "success",
            "message": f"Teams update task for country '{country_name}' completed successfully.",
            "task_id": self.request.id,
        }
    except Exception as e:
        logger.exception(f"Error in Celery task: {e}")
        return {
            "status": "error",
            "message": f"Failed to update teams for country '{country_name}': {e}",
            "task_id": self.request.id,
        }

async def _update_team_by_id(team_id: int):
    session = await async_session()  
    async with session as db:
        try:
            team_service = TeamService()
            updated_team = await team_service.update_team_by_id(session, team_id)
            await db.commit()
            return {"team_updated": updated_team}
        except Exception as e:
            await db.rollback()
            raise
        finally:
            await session.close()

async def _update_teams_by_country(country_name: str):
    session = await async_session()  
    async with session as db:
        try:
            team_service = TeamService()
            updated_count = await team_service.update_teams_by_country(session, country_name)
            await db.commit() 
            return {"teams_updated": updated_count}
        except Exception as e:
            await db.rollback()
            raise
        finally:
            await session.close()   

