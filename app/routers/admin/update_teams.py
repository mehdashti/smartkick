# app/routers/admin/update_teams.py
from fastapi import Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
import logging

# ---> استفاده از روتر پایه یا تعریف مجدد با امنیت <---
from fastapi import APIRouter
# from ..dependencies import get_admin_user
router = APIRouter(
    prefix="/admin", tags=["Admin - Teams"],
    # dependencies=[Depends(get_admin_user)]
)

from app.core.database import get_async_db_session
from app.services.team_service import TeamService

logger = logging.getLogger(__name__)

@router.post(
    "/teams/{team_id}/update",
    status_code=status.HTTP_200_OK,
    summary="Update team info from external API",
)
async def trigger_team_update(
    team_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_async_db_session)
):
    # ... (منطق قبلی اندپوینت آپدیت تیم بدون تغییر) ...
    logger.info(f"Admin endpoint triggered: POST /admin/teams/{team_id}/update")
    service = TeamService()
    try:
        updated_team_data = await service.update_team_info_from_api(team_id, db)
        if updated_team_data is None:
             raise HTTPException(status_code=404, detail=f"Team with ID {team_id} not found in external API or invalid data.")
        return {"message": f"Team {team_id} update process finished.", "team_data": updated_team_data}
    except Exception as e:
        logger.exception(f"Error during admin-triggered team update for ID {team_id}.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update team {team_id}: {e}")

# می توانید اندپوینتی برای آپدیت همه تیم ها یا تیم های یک لیگ هم اضافه کنید