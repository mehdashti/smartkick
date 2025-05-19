from celery import shared_task
from app.services.venue_service import VenueService
from app.core.database import async_session 
import asyncio
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="app.tasks.venue_tasks.update_venue_by_id_task")
def update_venue_by_id_task(self, venue_id: int):
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    logger.info(f"Task started: update_venue_by_id_task with venue_id={venue_id}")
    try:
        result_data = loop.run_until_complete(_update_venue_by_id(venue_id))
        logger.info(f"Task logic completed successfully for venue ID={venue_id}.")
        return {
             "status": "success", 
             "message": f"Venue update task for ID={venue_id} completed successfully.",
             "details": result_data, 
             "task_id": self.request.id
        }
    except Exception as e:
        logger.exception(f"Error in Celery task logic for venue ID={venue_id}: {e}")
        return {
            "status": "error",
            "message": f"Failed to update venue for ID={venue_id}: {str(e)}",
            "task_id": self.request.id
        }



@shared_task(bind=True, name="app.tasks.venue_tasks.update_venues_by_country_task")
def update_venues_by_country_task(self, country_name: str):
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    logger.info(f"Task started: update_venues_by_country_task with country_name={country_name}")
    try:
        result_data = loop.run_until_complete(_update_venues_by_country(country_name))
        logger.info(f"Task logic completed successfully for country '{country_name}'.")
        return {
            "status": "success",
            "message": f"Venues update task for country '{country_name}' completed successfully.",
            "details": result_data,
            "task_id": self.request.id,
        }
    except Exception as e:
        logger.exception(f"Error in Celery task logic for country '{country_name}': {e}")
        return {
            "status": "error",
            "message": f"Failed to update venues for country '{country_name}': {str(e)}",
            "task_id": self.request.id,
        }




async def _update_venue_by_id(venue_id: int):

    session = await async_session()
    async with session as db:
        try:
            venue_service = VenueService()
            updated_count = await venue_service.update_venue_by_id(db, venue_id)
            await db.commit()
            logger.info(f"Transaction committed successfully for '{venue_id}'.")
            return {"venues_updated": updated_count}
        except Exception as e:
            await db.rollback()
            logger.error(f"Error in _update_venue_by_id for {venue_id}: {e}")
            raise 
        finally:
            await session.close()


async def _update_venues_by_country(country_name: str):

    session = await async_session()  
    async with session as db:
        try:
            venue_service = VenueService()
            updated_count = await venue_service.update_venues_by_country(db, country_name)
            await db.commit()  
            logger.info(f"Transaction committed successfully for country '{country_name}'.")
            return {"venues_updated": updated_count}
        except Exception as e:
            await db.rollback()  
            logger.exception(f"Transaction rolled back for country '{country_name}'. Error: {e}")
            raise
        finally:
            await session.close()