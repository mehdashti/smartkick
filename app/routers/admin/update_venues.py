from fastapi import APIRouter, Depends, HTTPException, status, Path
from pydantic import BaseModel
import logging
from app.routers.dependencies import require_admin_user, get_async_db_session, AdminUser
from app.schemas.tasks import TaskQueueResponse
from app.tasks.venue_tasks import update_venues_by_country_task, update_venue_by_id_task

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/venues",
    tags=["Admin - Venues"],
    dependencies=[Depends(require_admin_user)]
)

@router.post(
    "/update-by-id/{venue_id}",
    response_model=TaskQueueResponse, 
    summary="Queue Background Task to Update Venue by ID", 
    status_code=status.HTTP_202_ACCEPTED,
)
async def queue_venue_update_by_id(
    *,
    admin_user: AdminUser,
    venue_id: int = Path(..., title="External ID of the Venue", ge=1),
) -> TaskQueueResponse:
    """
    Queues a background task to update a specific venue by its external ID.
    """
    logger.info(f"Admin request from '{admin_user.username}': Queue venue update task for ID={venue_id}.")
    try:
        task_result = update_venue_by_id_task.apply_async(args=[venue_id])
        logger.info(f"Celery task queued with ID: {task_result.id} for venue ID={venue_id}.")
        
        return TaskQueueResponse(
            status="success",
            message=f"Venue update task for ID={venue_id} has been queued successfully.",
            task_id=task_result.id,
        )
    except Exception as e:
        logger.exception(f"Failed to queue Celery task for venue update (ID={venue_id}). Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue background task for venue ID={venue_id}: {e}",
        )

@router.post(
    "/update-by-country/{country_name}",
    response_model=TaskQueueResponse, 
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue Background Task to Update Venues by Country",
    description="Queues a background task to update venues for a given country. Requires Admin privileges.",
)
async def queue_venues_update_by_country(
    *,
    admin_user: AdminUser,
    country_name: str = Path(..., title="Country Name", description="The name of the country (e.g., 'Japan')"),
) -> TaskQueueResponse: 
    """
    Queues a background task to update venues for a specific country.
    """
    logger.info(f"Admin request from '{admin_user.username}': Queue venues update task for country '{country_name}'.")
    try:
        task_result = update_venues_by_country_task.apply_async(args=[country_name])
        logger.info(f"Celery task queued with ID: {task_result.id} for country '{country_name}'.")
        # بازگرداندن نمونه‌ای از مدل پاسخ
        return TaskQueueResponse(
            status="success",
            message=f"Venues update task for country '{country_name}' has been queued successfully.",
            task_id=task_result.id,
        )
    except Exception as e:
        logger.exception(f"Failed to queue Celery task for venues update for country '{country_name}'. Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue background task for country '{country_name}': {e}",
        )