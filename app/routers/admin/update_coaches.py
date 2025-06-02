# app/routers/admin/update_coaches.py
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from app.routers.dependencies import require_admin_user, AdminUser
from app.tasks.coach_tasks import update_coach_by_id_task, update_all_coaches_task
from app.schemas.tasks import TaskQueueResponse
from app.core.database import async_session
import logging

from app.core.redis import redis_client
import json

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


@router.post(
    "/update-all",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TaskQueueResponse,
    summary="Queue Background Task to Update all Coaches",
)
async def queue_coach_update_all(
    *,
    admin_user: AdminUser,
) -> TaskQueueResponse:
    """Queues a background task to update all coaches."""
    logger.info(f"Admin request from '{admin_user.username}'.")
    try:
        task_result = update_all_coaches_task.apply_async()
        logger.info(f"Celery task queued with ID: {task_result.id} for all coaches.")
        return TaskQueueResponse(
            message=f"coaches update task has been queued successfully.",
            task_id=task_result.id,
        )
    except Exception as e:
        logger.exception(f"Failed to queue Celery task for coaches update. Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue background task for coaches: {e}",
        )




@router.get("/update-all/status/{task_id}", response_model=dict)
async def get_update_status(
    task_id: str,
    admin_user: AdminUser,
):
    """Get status of bulk update task"""
    progress_key = f"coach_update:progress:{task_id}"
    error_key = f"coach_update:errors:{task_id}"
    
    # دریافت داده‌های پیشرفت
    progress_data = redis_client.hgetall(progress_key) or {}
    total = int(progress_data.get("total", 0))
    processed = int(progress_data.get("processed", 0))
    successful = int(progress_data.get("successful", 0))
    failed = int(progress_data.get("failed", 0))
    
    # دریافت خطاها
    error_count = redis_client.llen(error_key)
    error_messages = []
    if error_count > 0:
        raw_errors = redis_client.lrange(error_key, 0, -1)
        error_messages = [json.loads(err) for err in raw_errors]
    
    # محاسبه درصد پیشرفت
    progress_percent = (processed / total * 100) if total > 0 else 0
    
    return {
        "task_id": task_id,
        "total": total,
        "processed": processed,
        "successful": successful,
        "failed": failed,
        "progress_percent": round(progress_percent, 2),
        "error_count": error_count,
        "errors": error_messages[:100]  # فقط 100 خطای اول
    }