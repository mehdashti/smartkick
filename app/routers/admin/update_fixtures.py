# app/routers/admin/update_fixtures.py
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from app.routers.dependencies import require_admin_user, AdminUser
from app.tasks.fixture_tasks import (
    update_fixtures_by_league_season_task, 
    update_fixtures_current_leagues_task, 
    update_fixtures_by_ids_task
)
from app.tasks.lineups_tasks import update_fixture_lineups_task
from app.tasks.events_tasks import update_fixture_events_task
from app.tasks.fixture_statistics_tasks import update_fixture_statistics_task

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


@router.post(
    "/update-lineups/{match_id}",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TaskQueueResponse, 
    summary="Queue Background Task to Update Fixture Lineups",
)
async def queue_fixture_update_lineups(
    *,
    admin_user: AdminUser,
    match_id: int = Path(..., title="External ID of the match", ge=1),
) -> TaskQueueResponse:
    logger.info(f"Admin request from '{admin_user.username}': Queue fixture lineups update task for Match={match_id}.")

    try:
        task_result = update_fixture_lineups_task.apply_async(args=[match_id])
        logger.info(f"Celery task queued with ID: {task_result.id} for Match={match_id}")
        return TaskQueueResponse(
            status="success",
            message=f"Fixture lineups update task for match {match_id} has been queued successfully.",
            task_id=task_result.id,
        )

    except Exception as e:
        logger.exception(f"Failed to queue Celery task for fixture lineups update (Match={match_id}). Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue background task for Match={match_id}: {e}"
        )


@router.post(
    "/update-events/{match_id}",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TaskQueueResponse, 
    summary="Queue Background Task to Update Fixture Lineups",
)
async def queue_fixture_update_events(
    *,
    admin_user: AdminUser,
    match_id: int = Path(..., title="External ID of the match", ge=1),
) -> TaskQueueResponse:
    logger.info(f"Admin request from '{admin_user.username}': Queue fixture events update task for Match={match_id}.")

    try:
        task_result = update_fixture_events_task.apply_async(args=[match_id])
        logger.info(f"Celery task queued with ID: {task_result.id} for Match={match_id}")
        return TaskQueueResponse(
            status="success",
            message=f"Fixture events update task for match {match_id} has been queued successfully.",
            task_id=task_result.id,
        )

    except Exception as e:
        logger.exception(f"Failed to queue Celery task for fixture events update (Match={match_id}). Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue background task for Match={match_id}: {e}"
        )


@router.post(
    "/update-statistics/{match_id}",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TaskQueueResponse, 
    summary="Queue Background Task to Update Fixture statistics",
)
async def queue_fixture_update_statistics(
    *,
    admin_user: AdminUser,
    match_id: int = Path(..., title="External ID of the match", ge=1),
) -> TaskQueueResponse:
    logger.info(f"Admin request from '{admin_user.username}': Queue fixture statistics update task for Match={match_id}.")

    try:
        task_result = update_fixture_statistics_task.apply_async(args=[match_id])
        logger.info(f"Celery task queued with ID: {task_result.id} for Match={match_id}")
        return TaskQueueResponse(
            status="success",
            message=f"Fixture statistics update task for match {match_id} has been queued successfully.",
            task_id=task_result.id,
        )

    except Exception as e:
        logger.exception(f"Failed to queue Celery task for fixture statistics update (Match={match_id}). Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue background task for Match={match_id}: {e}"
        )


@router.post(
    "/update-by-ids/{match_ids_str}",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TaskQueueResponse, 
    summary="Queue Background Task to Update All Current Fixtures",
)
async def queue_fixture_update_by_ids(
    *,
    match_ids_str: str = Path(..., title="Match IDs", description="Dash-separated string of match IDs (e.g., 123-456-789)"),
    admin_user: AdminUser,
) -> TaskQueueResponse:
    logger.info(f"Admin request from '{admin_user.username}': Queue fixtures update for ids={match_ids_str}.")

    try:
        match_ids_list_str = match_ids_str.split('-')
        match_ids_int_list: List[int] = []
        for id_str in match_ids_list_str:
            if not id_str.strip(): 
                continue
            try:
                match_ids_int_list.append(int(id_str.strip()))
            except ValueError:
                logger.error(f"Invalid match ID format in '{match_ids_str}'. '{id_str}' is not an integer.")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid match ID format. '{id_str}' is not a valid integer."
                )
        
        if not match_ids_int_list:
            logger.warning(f"No valid match IDs provided in string: {match_ids_str}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid match IDs provided."
            )

        logger.info(f"Converted match IDs list: {match_ids_int_list}")


        task_result = update_fixtures_by_ids_task.apply_async(args=[match_ids_int_list])
        logger.info(f"Celery task queued with ID: {task_result.id}")
        return TaskQueueResponse(
            status="success",
            message=f"Fixtures update task for ids={match_ids_str} has been queued successfully.",
            task_id=task_result.id,
        )

    except Exception as e:
        logger.exception(f"Failed to queue Celery task for fixtures. Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue background task: {e}"
        )

