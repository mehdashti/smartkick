# app/routers/admin/update_players.py
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from app.routers.dependencies import require_admin_user, AdminUser
from app.tasks.player_tasks import update_player_by_id_task, update_players_profiles_task  
from app.schemas.tasks import TaskQueueResponse
from app.services.player_service import PlayerService
from app.core.database import async_session
from app.api_clients.api_football import fetch_player_profiles_from_api
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/players",
    tags=["Admin - Players"],
    dependencies=[Depends(require_admin_user)]
)

@router.post(
    "/update-by-id/{player_id}",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TaskQueueResponse,
    summary="Queue Background Task to Update a Player by ID",
)
async def queue_player_update_by_id(
    *,
    admin_user: AdminUser,
    player_id: int = Path(..., title="Player ID", ge=1),
) -> TaskQueueResponse:
    """Queues a background task to update a specific player by its ID."""
    logger.info(f"Admin request from '{admin_user.username}': Queue player update task for ID={player_id}.")
    try:
        task_result = update_player_by_id_task.apply_async(args=[player_id])
        logger.info(f"Celery task queued with ID: {task_result.id} for player ID={player_id}.")
        return TaskQueueResponse(
            message=f"Player update task for ID={player_id} has been queued successfully.",
            task_id=task_result.id,
        )
    except Exception as e:
        logger.exception(f"Failed to queue Celery task for player update (ID={player_id}). Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue background task for player ID={player_id}: {e}",
        )


@router.post(
    "/profiles",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TaskQueueResponse,
    summary="Queue Background Task to Update all Player Profiles",
)
async def queue_players_update_profiles(
    *,
    admin_user: AdminUser,
) -> TaskQueueResponse:
    logger.info(f"Admin request from '{admin_user.username}': Queue players profiles update task.")
    try:
        task_result = update_players_profiles_task.apply_async()
        logger.info(f"Celery task queued with ID: {task_result.id} for players profiles.")
        return TaskQueueResponse(
            message=f"Players profiles update task has been queued successfully.",
            task_id=task_result.id,
        )
    except Exception as e:
        logger.exception(f"Failed to queue Celery task for players profiles. Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue background task for players profiles: {e}",
        )
