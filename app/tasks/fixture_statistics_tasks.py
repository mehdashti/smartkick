# app/tasks/fixture_statistics_tasks.py
from celery import shared_task
from app.services.fixture_statistics_service import FixtureStatisticsService
from app.core.database import async_session
import logging
import asyncio
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

@shared_task(bind=True, name="app.tasks.fixture_statistics_tasks.update_fixture_statistics_task")
def update_fixture_statistics_task(self, match_id: int):
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    logger.info(f"Task started: update_fixture_statistics_task with match_id={match_id}")
    try:
        result = loop.run_until_complete(_update_fixture_statistics(match_id))
        logger.info(f"Task completed successfully: {result}")
        return {
            "status": "success",
            "message": f"Fixture statistics update task for league {match_id} completed successfully.",
            "task_id": self.request.id,  
        }
    except Exception as e:
        logger.exception(f"Error in Celery task: {e}")
        return {
            "status": "error",
            "message": f"Failed to update fixture statistics {match_id}: {e}",
            "task_id": self.request.id, 
        }

async def _update_fixture_statistics(match_id: int):
    session = await async_session() 
    async with session as db:
        try:
            fixture_statistics_service = FixtureStatisticsService()
            updated_count = await fixture_statistics_service.update_fixture_statistics(db=db, match_id=match_id)
            await db.commit() 

            return {
                "status": "success",
                "statistics_updated": updated_count,
            }
        except Exception as e:
            await db.rollback()  
            logger.exception(f"Error during async task execution: {e}")
            raise
        finally:
            await session.close()


