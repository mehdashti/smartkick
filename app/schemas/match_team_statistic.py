# app/schemas/match_team_statistic.py

from pydantic import BaseModel, Field, HttpUrl, ConfigDict
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime
from pydantic.alias_generators import to_camel


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, alias_generator=to_camel, extra="ignore")


if TYPE_CHECKING:
    from app.schemas.team import TeamOut
    from app.schemas.match import MatchOut


class APIStatisticItem(APIModel):
    type: str
    value: Optional[Any] = None

class APITeamInfoForStats(APIModel):
    id: int
    name: str
    logo: Optional[HttpUrl | str] = None

class SingleTeamStatisticDataFromAPI(APIModel):
    team: APITeamInfoForStats
    statistics: List[APIStatisticItem]

class MatchStatisticsApiResponse(APIModel):
    get: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    errors: List[Any] = Field(default_factory=list)
    results: Optional[int] = None
    paging: Optional[Dict[str, int]] = None
    response: List[SingleTeamStatisticDataFromAPI]


class MatchTeamStatisticCreateInternal(APIModel):
    match_id: int
    team_id: int
    shots_on_goal: Optional[int] = None
    shots_off_goal: Optional[int] = None
    total_shots: Optional[int] = None
    blocked_shots: Optional[int] = None
    shots_insidebox: Optional[int] = None
    shots_outsidebox: Optional[int] = None
    fouls: Optional[int] = None
    corner_kicks: Optional[int] = None
    offsides: Optional[int] = None
    ball_possession: Optional[str] = None
    yellow_cards: Optional[int] = None
    red_cards: Optional[int] = None
    goalkeeper_saves: Optional[int] = None
    total_passes: Optional[int] = None
    passes_accurate: Optional[int] = None
    passes_percentage: Optional[str] = None
    raw_statistics: Optional[List[Dict[str, Any]]] = None


class MatchTeamStatisticUpdate(APIModel):
    shots_on_goal: Optional[int] = None
    shots_off_goal: Optional[int] = None
    total_shots: Optional[int] = None
    blocked_shots: Optional[int] = None
    shots_insidebox: Optional[int] = None
    shots_outsidebox: Optional[int] = None
    fouls: Optional[int] = None
    corner_kicks: Optional[int] = None
    offsides: Optional[int] = None
    ball_possession: Optional[str] = None
    yellow_cards: Optional[int] = None
    red_cards: Optional[int] = None
    goalkeeper_saves: Optional[int] = None
    total_passes: Optional[int] = None
    passes_accurate: Optional[int] = None
    passes_percentage: Optional[str] = None
    raw_statistics: Optional[List[Dict[str, Any]]] = None


class MatchTeamStatisticOut(APIModel):
    id: int
    shots_on_goal: Optional[int] = None
    shots_off_goal: Optional[int] = None
    total_shots: Optional[int] = None
    blocked_shots: Optional[int] = None
    shots_insidebox: Optional[int] = None
    shots_outsidebox: Optional[int] = None
    fouls: Optional[int] = None
    corner_kicks: Optional[int] = None
    offsides: Optional[int] = None
    ball_possession: Optional[str] = None
    yellow_cards: Optional[int] = None
    red_cards: Optional[int] = None
    goalkeeper_saves: Optional[int] = None
    total_passes: Optional[int] = None
    passes_accurate: Optional[int] = None
    passes_percentage: Optional[str] = None
    raw_statistics: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    updated_at: datetime
    team: Optional["TeamOut"] = None
    match: Optional["MatchOut"] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "shotsOnGoal": 3,
                "ballPossession": "32%",
                "yellowCards": 5,
                "rawStatistics": [
                    {"type": "Shots on Goal", "value": 3},
                    {"type": "Ball Possession", "value": "32%"}
                ],
                "createdAt": "2023-10-26T12:00:00Z",
                "updatedAt": "2023-10-26T12:00:00Z",
                "team": {"id": 463, "name": "Aldosivi"},
                "match": {"id": 215662, "status": "FT"}
            }
        }
    )