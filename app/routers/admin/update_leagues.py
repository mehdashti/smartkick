# app/routers/admin/update_leagues.py
from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from app.services.league_service import LeagueService
from app.schemas.tasks import TaskQueueResponse
from app.routers.dependencies import require_admin_user, get_async_db_session, AdminUser
from app.schemas.league import LeagueOut
from app.tasks.league_tasks import update_league_task

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/leagues",
    tags=["Admin - Leagues"],
    dependencies=[Depends(require_admin_user)]
)

@router.post(
    "/update-leagues",
    response_model=TaskQueueResponse, 
    status_code=status.HTTP_202_ACCEPTED,
    summary="Update Leagues and Seasons",
    description="Fetches the latest list of leagues and their seasons from API-Football and upserts them into the local database. Requires Admin privileges.",
)
async def update_leagues(
    *,
    admin_user: AdminUser,
) -> TaskQueueResponse: 

    logger.info(f"Admin request from '{admin_user.username}': Update leagues and seasons.")

    try:
        task_result = update_league_task.apply_async()
        logger.info(f"Celery task queued with ID: {task_result.id}.")

        return TaskQueueResponse(
            status="success",
            message=f"Leagues and seasons update task has been queued successfully.",
            task_id=task_result.id,
        )

    except Exception as e:
        logger.exception(f"Failed to queue Celery task for leagues update. Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue background task: {e}",
        )