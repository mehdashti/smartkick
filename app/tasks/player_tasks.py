# app/tasks/player_tasks.py
from celery import shared_task
from app.services.player_service import PlayerService
from app.core.database import async_session
from celery import shared_task
import asyncio
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, name="app.tasks.player_tasks.update_player_by_id_task")
def update_player_by_id_task(self, player_id: int):
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    logger.info(f"Task started: update_player_by_id_task with player_id={player_id}")
    try:
        result = loop.run_until_complete(_update_player_by_id(player_id))
        logger.info(f"Task completed successfully for player ID={player_id}.")
        return {
            "status": "success",
            "message": f"Player update task for ID={player_id} completed successfully.",
            "details": result,  
            "task_id": self.request.id,
        }
    except Exception as e:
        logger.exception(f"Error in Celery task logic for player ID={player_id}: {e}")
        return {
            "status": "error",
            "message": f"Failed to update player for ID={player_id}: {str(e)}",
            "task_id": self.request.id,
        }

async def _update_player_by_id(player_id: int):
    session = await async_session()
    async with session as db:
        try:
            player_service = PlayerService()
            updated_player = await player_service.update_player_by_id(db, player_id)
            await session.commit()
            return {"player_updated": updated_player}
        except Exception as e:
            await session.rollback()
            logger.exception(f"Error in _update_player_by_id for player ID={player_id}: {e}")
            raise
        finally:
            await session.close()


@shared_task(bind=True, name="app.tasks.player_tasks.update_players_profiles_task")
def update_players_profiles_task(self):
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    logger.info(f"Task started: update_players_profiles_task")
    try:
        result = loop.run_until_complete(_update_players_profiles())
        logger.info(f"Task completed successfully for players.")
        return result
    except Exception as e:
        logger.exception(f"Error in task execution: {str(e)}")
        return {"success": False, "error": str(e)}

async def _update_players_profiles():
    session = await async_session()
    async with session as db:
        try:
            player_service = PlayerService()
            updated_player = await player_service.update_players_from_api(db)
            await session.commit()
            return {"player_updated": updated_player}
        except Exception as e:
            await session.rollback()
            logger.exception(f"Error in _update_players_profiles: {e}")
            raise
        finally:
            await session.close()
