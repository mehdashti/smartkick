# routers/teams.py
from fastapi import APIRouter, HTTPException, Path, Query
from app.api_clients.api_football import fetch_teams_info

router = APIRouter(
    prefix="/teams",
    tags=["Teams"]
)

@router.get("/{team_id}")
async def get_team_info(team_id: int):

    try:
        team_data = await fetch_teams_info(team_id=team_id)
        return team_data

    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

