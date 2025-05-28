# app/tasks/coach_tasks.py
from celery import shared_task
from app.services.coach_service import CoachService
from app.core.database import async_session
from celery import shared_task
import asyncio
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, name="app.tasks.coach_tasks.update_coach_by_id_task")
def update_coach_by_id_task(self, coach_id: int):
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    logger.info(f"Task started: update_coach_by_id_task with coach_id={coach_id}")
    try:
        result = loop.run_until_complete(_update_coach_by_id(coach_id))
        logger.info(f"Task completed successfully for coach ID={coach_id}.")
        return {
            "status": "success",
            "message": f"coach update task for ID={coach_id} completed successfully.",
            "details": result,  
            "task_id": self.request.id,
        }
    except Exception as e:
        logger.exception(f"Error in Celery task logic for coach ID={coach_id}: {e}")
        return {
            "status": "error",
            "message": f"Failed to update coach for ID={coach_id}: {str(e)}",
            "task_id": self.request.id,
        }

async def _update_coach_by_id(coach_id: int):
    session = await async_session()
    async with session as db:
        try:
            coach_service = CoachService()
            updated_coach = await coach_service.update_coach_by_id(db, coach_id)
            await session.commit()
            return {"coach_updated": updated_coach}
        except Exception as e:
            await session.rollback()
            logger.exception(f"Error in _update_coach_by_id for coach ID={coach_id}: {e}")
            raise
        finally:
            await session.close()

