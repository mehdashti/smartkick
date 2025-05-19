# app/routers/admin/update_teams.py
from fastapi import APIRouter, Depends, HTTPException, status, Path
from pydantic import BaseModel
import logging
from typing import List
import httpx

# وابستگی‌ها و سرویس‌ها
from app.routers.dependencies import require_admin_user, get_async_db_session, AdminUser
from app.services.team_service import TeamService
from app.schemas.team import TeamOut
from app.tasks.team_tasks import update_teams_by_league_season_task, update_team_by_id_task, update_teams_by_country_task
from app.schemas.tasks import TaskQueueResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/teams",
    tags=["Admin - Teams"],
    dependencies=[Depends(require_admin_user)]
)

@router.post(
    "/update-by-country/{country_name}",
    response_model=TaskQueueResponse, 
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue Background Task to Update Teams by Country",
)
async def queue_teams_update_by_country(
    *,
    admin_user: AdminUser,
    country_name: str = Path(..., title="Country Name", description="The name of the country (e.g., 'Japan')"),
) -> TaskQueueResponse:
    """Queues a background task to update teams for a specific country."""
    logger.info(f"Admin request from '{admin_user.username}': Queue teams update task for country '{country_name}'.")
    try:
        task_result = update_teams_by_country_task.apply_async(args=[country_name])
        logger.info(f"Celery task queued with ID: {task_result.id} for country '{country_name}'.")
        return TaskQueueResponse(
            status="success",
            message=f"Teams update task for country '{country_name}' has been queued successfully.",
            task_id=task_result.id,
        )
        
    except Exception as e:
        logger.exception(f"Failed to queue Celery task for teams update for country '{country_name}'. Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue background task for country '{country_name}': {e}",
        )

@router.post(
    "/update-by-league-season/{league_id}/{season}",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TaskQueueResponse, 
    summary="Queue Background Task to Update Teams & Venues by League/Season",
    description=(
        "Queues a background task to update teams and venues for a given league and season. "
        "Requires Admin privileges."
    )
)
async def queue_team_venue_update_by_league_season(
    *,
    admin_user: AdminUser,
    league_id: int = Path(..., title="External ID of the League", ge=1),
    season: int = Path(..., title="Season Year (e.g., 2023)", ge=1990)
) -> TaskQueueResponse:
    """
    Queues a background task to update teams and venues for a given league and season.
    """
    logger.info(f"Admin request from '{admin_user.username}': Queue team/venue update task for L={league_id}/S={season}.")

    try:
        # ارسال تسک به صورت آسنکرون
        task_result = update_teams_by_league_season_task.apply_async(args=[league_id, season])
        logger.info(f"Celery task queued with ID: {task_result.id} for L={league_id}/S={season}")
        return TaskQueueResponse(
            status="success",
            message=f"Team/Venue update task for league {league_id}, season {season} has been queued successfully.",
            task_id=task_result.id,
        )

    except Exception as e:
        logger.exception(f"Failed to queue Celery task for team/venue update (L={league_id}/S={season}). Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue background task for L={league_id}/S={season}: {e}"
        )

@router.post(
    "/update-by-id/{team_id}",
    response_model=TaskQueueResponse, 
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue Background Task to Update a Team by ID",
)
async def queue_team_update_by_id(
    *,
    admin_user: AdminUser,
    team_id: int = Path(..., title="Team ID", ge=1),
) -> TaskQueueResponse:
    """Queues a background task to update a specific team by its ID."""
    logger.info(f"Admin request from '{admin_user.username}': Queue team update task for ID={team_id}.")
    try:
        task_result = update_team_by_id_task.apply_async(args=[team_id])
        logger.info(f"Celery task queued with ID: {task_result.id} for team ID={team_id}.")
        return TaskQueueResponse(
            status="success",
            message=f"Team update task for ID={team_id} has been queued successfully.",
            task_id=task_result.id,
        )
        
    except Exception as e:
        logger.exception(f"Failed to queue Celery task for team update (ID={team_id}). Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue background task for team ID={team_id}: {e}",
        )

