from celery import shared_task
from app.services.fixture_service import FixtureService
from app.core.database import async_session
import logging
import asyncio
from app.repositories.league_repository import LeagueRepository

logger = logging.getLogger(__name__)

@shared_task(bind=True, name="app.tasks.team_tasks.update_fixtures_by_league_season_task")
def update_fixtures_by_league_season_task(self, league_id: int, season: int):
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    logger.info(f"Task started: update_fixtures_by_league_season_task with league_id={league_id}, season={season}")
    try:
        result = loop.run_until_complete(_update_fixtures_by_league_season(league_id, season))
        logger.info(f"Task completed successfully: {result}")
        return {
            "status": "success",
            "message": f"Fixtures update task for league {league_id}, season {season} completed successfully.",
            "task_id": self.request.id,  
        }
    except Exception as e:
        logger.exception(f"Error in Celery task: {e}")
        return {
            "status": "error",
            "message": f"Failed to update fixtures for league {league_id}, season {season}: {e}",
            "task_id": self.request.id, 
        }

async def _update_fixtures_by_league_season(league_id: int, season: int):
    session = await async_session() 
    async with session as db:
        try:
            fixture_service = FixtureService()
            updated_count = await fixture_service.update_fixtures_by_league_season(db=db, league_id=league_id, season=season)
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


@shared_task(bind=True, name="app.tasks.team_tasks.update_fixtures_current_leagues_task")
def update_fixtures_current_leagues_task(self):
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    logger.info(f"Task started: update_fixtures_current_leagues_task")
    try:
        result = loop.run_until_complete(_update_fixtures_current_leagues())
        logger.info(f"Task completed successfully: {result}")
        return {
            "status": "success",
            "message": f"Fixtures update task for current leagues completed successfully.",
            "task_id": self.request.id,  
        }
    except Exception as e:
        logger.exception(f"Error in Celery task: {e}")
        return {
            "status": "error",
            "message": f"Failed to update fixtures for current leagues: {e}",
            "task_id": self.request.id, 
        }

async def _update_fixtures_current_leagues():
    session = await async_session()
    async with session as db:
        leagues_list = await LeagueRepository(db).get_current_leagues()

        all_results = [] 

        for league in leagues_list: 
            league_id = league.league_id
            season = league.season
            logger.info(f"Processing league_id={league_id}, season={season} in _update_fixtures_current_leagues") # لاگ برای پیگیری
            try:
                fixture_service = FixtureService()
 
                updated_count_for_league = await fixture_service.update_fixtures_by_league_season(db=db, league_id=league_id, season=season)
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


@shared_task(bind=True, name="app.tasks.team_tasks.update_fixture_lineups_task")
def update_fixture_lineups_task(self, match_id: int):
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    logger.info(f"Task started: update_fixture_lineups_task with match_id={match_id}")
    try:
        result = loop.run_until_complete(_update_fixture_lineups(match_id))
        logger.info(f"Task completed successfully: {result}")
        return {
            "status": "success",
            "message": f"Fixture lienups update task for league {match_id} completed successfully.",
            "task_id": self.request.id,  
        }
    except Exception as e:
        logger.exception(f"Error in Celery task: {e}")
        return {
            "status": "error",
            "message": f"Failed to update fixture lineups {match_id}: {e}",
            "task_id": self.request.id, 
        }

async def _update_fixture_lineups(match_id: int):
    session = await async_session() 
    async with session as db:
        try:
            fixture_service = FixtureService()
            updated_count = await fixture_service.update_fixture_lineups(db=db, match_id=match_id)
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
