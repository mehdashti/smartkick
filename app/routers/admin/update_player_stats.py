# app/routers/admin/update_player_stats.py
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
import logging
from typing import Optional
from pydantic import BaseModel
from app.schemas.tasks import TaskQueueResponse
from app.services.player_service import PlayerService
from app.routers.dependencies import require_admin_user, get_async_db_session, AdminUser
from app.tasks.player_stats_tasks import  (
    update_fixture_player_stats_by_id_task,
    update_player_stats_for_league_season_task,
    update_player_stats_for_league_task,
    update_player_stats_for_season_task,
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/players/stats",
    tags=["Admin - Player Stats"],
    dependencies=[Depends(require_admin_user)] 
)

@router.post(
    "/update-by-league-season/{league_external_id}/{season}",
    status_code=status.HTTP_202_ACCEPTED,  
    response_model=TaskQueueResponse, 
    summary="Queue Background Task to Update Player Stats by League and Season",
    description="Queues a background task to update player stats for a specific league and season.",
)
async def update_stats_by_league_season(
    *,
    admin_user: AdminUser,
    league_external_id: int = Path(..., description="External ID of the League"),
    season: int = Path(..., description="Season year (e.g., 2024)"),
    max_pages: Optional[int] = Query(None, description="Max pages per league/season", ge=1),
) -> TaskQueueResponse:
    logger.info(f"Admin request from '{admin_user.username}': Queue player stats update task for L:{league_external_id}/S:{season} (MaxPages: {max_pages or 'All'}).")
    try:
        task_result = update_player_stats_for_league_season_task.apply_async(args=[league_external_id, season, max_pages])
        logger.info(f"Celery task queued with ID: {task_result.id} for players stats.")
        return TaskQueueResponse(
            message=f"Players stats update task has been queued successfully.",
            task_id=task_result.id,
        )
    except Exception as e:
        logger.exception(f"Failed to queue Celery task for player stats update. Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue background task: {e}",
        )



@router.post(
    "/update-by-season/{season}",
    status_code=status.HTTP_202_ACCEPTED,  
    response_model=TaskQueueResponse, 
    summary="Update player stats for all leagues in a season",
    description="Fetches and updates player stats for all leagues in a specific season from the external API. Requires Admin privileges.",
    response_description="Number of player stats updated.",
)
async def update_stats_by_season(
    *,
    db=Depends(get_async_db_session),
    admin_user: AdminUser,
    season: int = Path(..., description="Season year (e.g., 2024)"),
    max_pages_per_league: Optional[int] = Query(None, alias="maxPagesPerLeague", description="Max pages per league/season processed", ge=1),
) -> TaskQueueResponse:
    
    logger.info(f"Admin request from '{admin_user.username}': Update player stats for Season:{season}.")
    try:
        task_result = update_player_stats_for_season_task.apply_async(args=[season, max_pages_per_league])
        logger.info(f"Celery task queued with ID: {task_result.id} for players stats.")
        return TaskQueueResponse(
            message=f"Players stats update task has been queued successfully.",
            task_id=task_result.id,
        )
    except Exception as e:
        logger.exception(f"Failed to queue Celery task for player stats update. Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue background task: {e}",
        )



@router.post(
    "/update-by-league/{league_external_id}",
    status_code=status.HTTP_202_ACCEPTED,  
    response_model=TaskQueueResponse, 
    summary="Update player stats for all seasons of a specific league",
    description="Fetches and updates player stats for all seasons of a specific league from the external API. Requires Admin privileges.",
    response_description="Number of player stats updated.",
)
async def update_stats_by_league(
    *,
    db=Depends(get_async_db_session),
    admin_user: AdminUser,
    league_external_id: int = Path(..., description="External ID of the League"),
    max_pages_per_league: Optional[int] = Query(None, alias="maxPagesPerLeague", description="Max pages per league/season processed", ge=1),
) -> TaskQueueResponse:
    """
    Updates player stats for all seasons of a specific league by fetching data from the external API.
    """
    logger.info(f"Admin request from '{admin_user.username}': Update player stats for League:{league_external_id}.")
    try:
        task_result = update_player_stats_for_league_task.apply_async(args=[league_external_id, max_pages_per_league])
        logger.info(f"Celery task queued with ID: {task_result.id} for players stats.")
        return TaskQueueResponse(
            message=f"Players stats update task has been queued successfully.",
            task_id=task_result.id,
        )
    except Exception as e:
        logger.exception(f"Failed to queue Celery task for player stats update. Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue background task: {e}",
        )

@router.post(
    "/update-by-match-id/{match_id}",
    status_code=status.HTTP_202_ACCEPTED,  
    response_model=TaskQueueResponse, 
    summary="Queue Background Task to Update fixture Player Stats by Match ID",
    description="Queues a background task to update fixture player stats.",
)
async def update_fixture_player_stats_by_id(
    *,
    admin_user: AdminUser,
    match_id: int = Path(..., description="Match ID"),
) -> TaskQueueResponse:
    logger.info(f"Admin request from '{admin_user.username}': Queue fixture player stats update task for match id:{match_id}).")
    try:
        task_result = update_fixture_player_stats_by_id_task.apply_async(args=[match_id])
        logger.info(f"Celery task queued with ID: {task_result.id} for fixture players stats.")
        return TaskQueueResponse(
            message=f"Players stats update task has been queued successfully.",
            task_id=task_result.id,
        )
    except Exception as e:
        logger.exception(f"Failed to queue Celery task for fixture player stats update. Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue background task: {e}",
        )