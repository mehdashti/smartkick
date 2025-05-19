from celery import shared_task
from app.services.metadata_service import MetadataService
from app.core.database import async_session 

import asyncio
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, name="app.tasks.country_tasks.update_country_task")
def update_country_task(self):
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    logger.info(f"Task started: update_country_task")
    try:
        result = loop.run_until_complete(_update_country())
        return result
    except Exception as e:
        logger.exception(f"Error in task execution: {str(e)}")
        return {"success": False, "error": str(e)}

async def _update_country(): 

    session = await async_session()
    async with session as db:
        try:
            metadata_service = MetadataService()
            updated_count = await metadata_service.update_country(db)
            await db.commit()
            return {"updated_count": updated_count}
        except Exception as e:
            await db.rollback()
            logger.exception(f"Error in _update_country: {e}")
            raise
        finally:
            await session.close()