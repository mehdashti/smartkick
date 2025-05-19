# app/routers/admin/update_fixtures.py
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from app.routers.dependencies import require_admin_user, AdminUser
from app.tasks.fixture_tasks import update_fixtures_by_league_season_task, update_fixtures_current_leagues_task
from app.schemas.tasks import TaskQueueResponse
from app.core.database import async_session

import logging



logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/fixtures",
    tags=["Admin - Fixtures"],
    dependencies=[Depends(require_admin_user)]
)

@router.post(
    "/update-by-league-season/{league_id}/{season}",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TaskQueueResponse, 
    summary="Queue Background Task to Update Fixtures by League/Season",
)
async def queue_fixture_update_by_league_season(
    *,
    admin_user: AdminUser,
    league_id: int = Path(..., title="External ID of the League", ge=1),
    season: int = Path(..., title="Season Year (e.g., 2023)", ge=1990)
) -> TaskQueueResponse:
    logger.info(f"Admin request from '{admin_user.username}': Queue fixtures update task for L={league_id}/S={season}.")

    try:
        task_result = update_fixtures_by_league_season_task.apply_async(args=[league_id, season])
        logger.info(f"Celery task queued with ID: {task_result.id} for L={league_id}/S={season}")
        return TaskQueueResponse(
            status="success",
            message=f"Fixtures update task for league {league_id}, season {season} has been queued successfully.",
            task_id=task_result.id,
        )

    except Exception as e:
        logger.exception(f"Failed to queue Celery task for fixtures update (L={league_id}/S={season}). Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue background task for L={league_id}/S={season}: {e}"
        )



@router.post(
    "/update-current",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TaskQueueResponse, 
    summary="Queue Background Task to Update All Current Fixtures",
)
async def queue_fixture_update_current(
    *,
    admin_user: AdminUser,
) -> TaskQueueResponse:
    logger.info(f"Admin request from '{admin_user.username}': Queue fixtures update all current leagues.")

    try:
        task_result = update_fixtures_current_leagues_task.apply_async()
        logger.info(f"Celery task queued with ID: {task_result.id}")
        return TaskQueueResponse(
            status="success",
            message=f"Fixtures update task for current leagues has been queued successfully.",
            task_id=task_result.id,
        )

    except Exception as e:
        logger.exception(f"Failed to queue Celery task for fixtures. Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue background task: {e}"
        )





