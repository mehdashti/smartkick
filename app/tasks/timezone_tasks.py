# app/tasks/timezone_tasks.py

from celery import shared_task
from app.services.metadata_service import MetadataService
import asyncio
from celery.utils.log import get_task_logger
from app.core.database import async_session

logger = get_task_logger(__name__)

@shared_task(name="app.tasks.timezone_tasks.update_timezone_task")
def update_timezone_task() -> dict:
    # استفاده از حلقه‌ی رویداد پیش‌فرض
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    logger.info("Using existing event loop")
    try:
        result = loop.run_until_complete(_update_timezone())
        return result
    except Exception as e:
        logger.exception(f"Error in task execution: {str(e)}")
        return {"success": False, "error": str(e)}

async def _update_timezone() -> dict:
    session = await async_session()
    async with session as db:
        try:
            logger.info("Celery Task started: update_timezone_task")
            metadata_service = MetadataService()
            metadata_count = await metadata_service.update_timezone(db)
            await db.commit()
            logger.info(f"Logic finished successfully. Updated count: {metadata_count}")
            return {
                "success": True,
                "updated_count": metadata_count,
                "items_processed": metadata_count
            }
        except Exception as e:
            await db.rollback()
            logger.exception(f"Error within task execution: {e}")
            raise
        finally:
            await session.close()

