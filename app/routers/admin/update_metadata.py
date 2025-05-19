# app/routers/admin/update_metadata.py

from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from app.services.metadata_service import MetadataService
from app.schemas.tasks import TaskQueueResponse
from app.routers.dependencies import require_admin_user, get_async_db_session, AdminUser
from app.schemas.country import CountryOut
from app.tasks.country_tasks import update_country_task
from app.tasks.timezone_tasks import update_timezone_task

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/metadata",
    tags=["Admin - Metadata"],
    dependencies=[Depends(require_admin_user)]
)

@router.post(
    "/update-timezones",
    response_model=TaskQueueResponse, 
    status_code=status.HTTP_202_ACCEPTED,
    summary="Update Timezones from API",
    description="Fetches the latest list of timezones from the external API and updates the local database. Requires Admin privileges.",
)
async def update_timezones(
    *,
    admin_user: AdminUser,
) -> TaskQueueResponse: 

    logger.info(f"Admin request from '{admin_user.username}': Queue timezones update task.")
    try:
        task_result = update_timezone_task.apply_async()
        logger.info(f"Celery task queued with ID: {task_result.id}.")
        
        return TaskQueueResponse(
            status="success",
            message=f"Timezones update task has been queued successfully.",
            task_id=task_result.id,
        )
        
    except Exception as e:
        logger.exception(f"Failed to queue Celery task for timezones update. Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue background task: {e}",
        )

@router.post(
    "/update-countries",
    response_model=TaskQueueResponse, 
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue Background Task to Update Countries from API",
    description="Fetches the latest list of countries from the external API and updates the local database. Requires Admin privileges.",
)
async def update_countries(
    *,
    admin_user: AdminUser,
) -> TaskQueueResponse: 

    logger.info(f"Admin request from '{admin_user.username}': Queue countries update task.")
    try:
        task_result = update_country_task.apply_async()
        logger.info(f"Celery task queued with ID: {task_result.id}.")
        return TaskQueueResponse(
            status="success",
            message=f"Countries update task has been queued successfully.",
            task_id=task_result.id,
        )
    except Exception as e:
        logger.exception(f"Failed to queue Celery task for countries update. Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue background task: {e}",
        )