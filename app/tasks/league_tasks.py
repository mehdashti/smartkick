# app/tasks/league_tasks.py

from celery import shared_task
from app.services.league_service import LeagueService
import asyncio
from celery.utils.log import get_task_logger
from app.core.database import async_session

logger = get_task_logger(__name__)

@shared_task(name="app.tasks.league_tasks.update_league_task")
def update_league_task() -> dict:
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    logger.info("Using existing event loop")
    try:
        result = loop.run_until_complete(_update_league())
        return result
    except Exception as e:
        logger.exception(f"Error in task execution: {str(e)}")
        return {"success": False, "error": str(e)}

async def _update_league() -> dict:
    session = await async_session()
    async with session as db:
        try:
            logger.info("Celery Task started: update_league_task")
            league_service = LeagueService()
            league_count = await league_service.update_league(db)
            await db.commit()
            logger.info(f"Logic finished successfully. Updated count: {league_count}")
            return {
                "success": True,
                "updated_count": league_count,
                "items_processed": league_count
            }
        except Exception as e:
            await db.rollback()
            logger.exception(f"Error within task execution: {e}")
            raise
        finally:
            await session.close()

