# app/schemas/match_lineup.py
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime
from pydantic.alias_generators import to_camel

if TYPE_CHECKING:
    from app.schemas.team import TeamOut
    from app.schemas.match import MatchOut

class APIModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        extra="ignore"
    )

class CoachSchema(APIModel):
    id: Optional[int] = None
    name: Optional[str] = None
    photo: Optional[HttpUrl | str] = None

class TeamColorsPlayerSchema(APIModel):
    primary: Optional[str] = None
    number: Optional[str] = None
    border: Optional[str] = None

class TeamColorsSchema(APIModel):
    player: Optional[TeamColorsPlayerSchema] = None
    goalkeeper: Optional[TeamColorsPlayerSchema] = None

class PlayerDetailSchema(APIModel):
    id: int
    name: str
    number: Optional[int] = Field(None, ge=1, le=99)
    pos: Optional[str] = Field(None, min_length=1, max_length=5)
    grid: Optional[str] = Field(None, pattern=r"^\d+:\d+$")

class PlayerEntrySchema(APIModel):
    player: PlayerDetailSchema

class TeamInfoForLineupSchema(APIModel):
    id: int
    name: str
    logo: Optional[HttpUrl | str] = None
    colors: Optional[TeamColorsSchema] = None

class SingleTeamLineupDataFromAPI(APIModel):
    team: TeamInfoForLineupSchema
    formation: Optional[str] = Field(None, max_length=20)
    startXI: List[PlayerEntrySchema] = Field(default_factory=list)
    substitutes: List[PlayerEntrySchema] = Field(default_factory=list)
    coach: Optional[CoachSchema] = None

class MatchLineupCreateInternal(APIModel):
    match_id: int
    team_id: int
    team_name: str
    formation: Optional[str] = None
    startXI: Optional[List[Dict[str, Any]]] = None
    substitutes: Optional[List[Dict[str, Any]]] = None
    coach_id: Optional[int] = None
    coach_name: Optional[str] = None
    coach_photo: Optional[str] = None
    team_colors: Optional[Dict[str, Any]] = None

class MatchLineupUpdate(APIModel):
    formation: Optional[str] = None
    startXI: Optional[List[Dict[str, Any]]] = None
    substitutes: Optional[List[Dict[str, Any]]] = None
    coach_id: Optional[int] = None
    coach_name: Optional[str] = None
    coach_photo: Optional[str] = None
    team_colors: Optional[Dict[str, Any]] = None

class MatchLineupOut(APIModel):
    lineup_id: int = Field(..., alias="id")
    match_id: int
    team_id: int
    team_name: str
    formation: Optional[str] = None
    startXI: Optional[List[Dict[str, Any]]] = None
    substitutes: Optional[List[Dict[str, Any]]] = None
    coach_id: Optional[int] = None
    coach_name: Optional[str] = None
    coach_photo: Optional[str] = None
    team_colors: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    # match: Optional["MatchOut"] = None
    # team: Optional["TeamOut"] = None

class MatchLineupApiResponse(APIModel):
    get: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    errors: List[Any] = Field(default_factory=list)
    results: Optional[int] = None
    paging: Optional[Dict[str, int]] = None
    response: List[SingleTeamLineupDataFromAPI]

# if TYPE_CHECKING:
#     MatchLineupOut.model_rebuild()