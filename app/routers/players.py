# routers/players.py
from fastapi import APIRouter, HTTPException, Path, Query
from app.api_clients.api_football import fetch_player_teams

router = APIRouter(
    prefix="/players",
    tags=["Players"]
)

@router.get("/{player_id}")
async def get_player_info(player_id: int):

    try:
        player_data = await fetch_player_teams(player_id=player_id)
        return player_data

    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

