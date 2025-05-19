from fastapi import APIRouter, HTTPException, Path, status
from celery.result import AsyncResult
from app.core.celery_app import celery_app

router = APIRouter(
    prefix="/admin/tasks",
    tags=["Admin - Task Status"],
)

@router.get(
    "/{task_id}",
    summary="Get Task Status",
    description="Fetches the status and result of a Celery task by its ID.",
    response_description="Task status and result.",
)
async def get_task_status(
    task_id: str = Path(..., title="Task ID", description="The ID of the Celery task to fetch status for."),
) -> dict:
    """
    Fetches the status and result of a Celery task by its ID.
    """
    task_result = AsyncResult(task_id, app=celery_app)

    if not task_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found.",
        )

    return {
        "task_id": task_id,
        "status": task_result.status,
        "result": task_result.result,
    }
