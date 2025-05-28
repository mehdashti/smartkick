# app/routers/admin/update_coaches.py
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from app.routers.dependencies import require_admin_user, AdminUser
from app.tasks.coach_tasks import update_coach_by_id_task
from app.schemas.tasks import TaskQueueResponse
from app.core.database import async_session
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/coaches",
    tags=["Admin - Coaches"],
    dependencies=[Depends(require_admin_user)]
)

@router.post(
    "/update-by-id/{coach_id}",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TaskQueueResponse,
    summary="Queue Background Task to Update a Coach by ID",
)
async def queue_coach_update_by_id(
    *,
    admin_user: AdminUser,
    coach_id: int = Path(..., title="coach ID", ge=1),
) -> TaskQueueResponse:
    """Queues a background task to update a specific coach by its ID."""
    logger.info(f"Admin request from '{admin_user.username}': Queue coach update task for ID={coach_id}.")
    try:
        task_result = update_coach_by_id_task.apply_async(args=[coach_id])
        logger.info(f"Celery task queued with ID: {task_result.id} for coach ID={coach_id}.")
        return TaskQueueResponse(
            message=f"coach update task for ID={coach_id} has been queued successfully.",
            task_id=task_result.id,
        )
    except Exception as e:
        logger.exception(f"Failed to queue Celery task for coach update (ID={coach_id}). Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue background task for coach ID={coach_id}: {e}",
        )


