from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime
from pydantic.alias_generators import to_camel
from enum import Enum
from app.schemas.match_lineups import MatchLineupCreateInternal
from app.schemas.match_lineups import SingleTeamLineupDataFromAPI 
from app.schemas.match_event import SingleEventDataFromAPI
from app.schemas.match_event import MatchEventCreateInternal 
from app.schemas.match_team_statistic import MatchTeamStatisticCreateInternal
from app.schemas.match_team_statistic import SingleTeamStatisticDataFromAPI 
from app.schemas.player_fixture_stats import PlayerFixtureStatsCreateInternal
from app.schemas.player_fixture_stats import StatsTeamInfoForFixtureAPI
from app.schemas.player_fixture_stats import TeamPlayersStatsInFixtureAPI



if TYPE_CHECKING:
    from app.schemas.team import TeamOut
    from app.schemas.venue import VenueOut
    from app.schemas.league import LeagueOut


class APIModel(BaseModel):
    """Base model with common config for all schemas"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        extra="ignore"
    )

# --- Enums ---
class MatchStatusShort(str, Enum):
    TBD = "TBD"
    NS = "NS"
    H1 = "1H"
    HT = "HT"
    H2 = "2H"
    ET = "ET"
    BT = "BT"
    P = "P"
    SUSP = "SUSP"
    INT = "INT"
    LIVE = "LIVE"
    FT = "FT"
    AET = "AET"
    PEN = "PEN"
    PST = "PST"
    CANC = "CANC"
    ABD = "ABD"
    AWD = "AWD"
    WO = "WO"

# --- Nested Schemas ---
class PeriodsSchema(APIModel):
    first: Optional[int] = Field(None, description="Timestamp of first period start")
    second: Optional[int] = Field(None, description="Timestamp of second period start")

class VenueSchema(APIModel):
    id: Optional[int] = Field(None, description="Venue ID from external API")
    name: Optional[str] = Field(None, description="Venue name")
    city: Optional[str] = Field(None, description="City where venue is located")

class StatusSchema(APIModel):
    long: str = Field(..., description="Long status description")
    short: MatchStatusShort = Field(..., description="Short status code")
    elapsed: Optional[int] = Field(None, description="Minutes elapsed")
    extra: Optional[int] = Field(None, description="Extra time info")

class TeamMatchInfoSchema(APIModel):
    id: int = Field(..., description="Team ID from external API")
    name: str = Field(..., description="Team name")
    logo: Optional[HttpUrl | str] = Field(None, description="Team logo URL")
    winner: Optional[bool] = Field(None, description="Whether team won")

class ScoreSchema(APIModel):
    home: Optional[int] = Field(None, description="Home team score")
    away: Optional[int] = Field(None, description="Away team score")

class ScoreBreakdownSchema(APIModel):
    halftime: Optional[ScoreSchema] = Field(None)
    fulltime: Optional[ScoreSchema] = Field(None)
    extratime: Optional[ScoreSchema] = Field(None)
    penalty: Optional[ScoreSchema] = Field(None)

# --- API Input Schemas ---
class FixtureAPIData(APIModel):
    id: int = Field(..., description="Fixture ID from external API")
    referee: Optional[str] = Field(None)
    timezone: str = Field(..., description="Timezone of the match")
    date: datetime = Field(..., description="Match date and time")
    timestamp: int = Field(..., description="Unix timestamp of match")
    periods: PeriodsSchema
    venue: VenueSchema
    status: StatusSchema

class LeagueAPIData(APIModel):
    id: int = Field(..., description="League ID from external API")
    name: str = Field(..., description="League name")
    country: str = Field(..., description="Country name")
    logo: Optional[HttpUrl | str] = Field(None)
    flag: Optional[HttpUrl | str] = Field(None)
    season: int = Field(..., description="Season year")
    round: Optional[str] = Field(None, description="Round information")

class TeamsAPIData(APIModel):
    home: TeamMatchInfoSchema
    away: TeamMatchInfoSchema

class GoalsAPIData(APIModel):
    home: Optional[int] = Field(None)
    away: Optional[int] = Field(None)

class MatchAPIInputData(APIModel):
    fixture: FixtureAPIData
    league: LeagueAPIData
    teams: TeamsAPIData
    goals: GoalsAPIData
    score: ScoreBreakdownSchema
    events: Optional[List[SingleEventDataFromAPI]] = Field(default_factory=list) 
    lineups: Optional[List[SingleTeamLineupDataFromAPI]] = Field(default_factory=list) 
    statistics: Optional[List[SingleTeamStatisticDataFromAPI]] = Field(default_factory=list) 
    players: Optional[List[TeamPlayersStatsInFixtureAPI]] = Field(default_factory=list) 

# --- Internal Create/Update Schemas ---
class MatchCreateInternal(APIModel):
    match_id: int = Field(..., alias="id", description="Match ID from external API")
    referee: Optional[str] = Field(None)
    timezone: str = Field(...)
    date: datetime = Field(...)
    timestamp: int = Field(...)
    periods_first: Optional[int] = Field(None, alias="first")
    periods_second: Optional[int] = Field(None, alias="second")
    status_long: str = Field(...)
    status_short: MatchStatusShort = Field(...)
    status_elapsed: Optional[int] = Field(None)
    status_extra: Optional[int] = Field(None)
    goals_home: Optional[int] = Field(None)
    goals_away: Optional[int] = Field(None)
    score_halftime_home: Optional[int] = Field(None)
    score_halftime_away: Optional[int] = Field(None)
    score_fulltime_home: Optional[int] = Field(None)
    score_fulltime_away: Optional[int] = Field(None)
    score_extratime_home: Optional[int] = Field(None)
    score_extratime_away: Optional[int] = Field(None)
    score_penalty_home: Optional[int] = Field(None)
    score_penalty_away: Optional[int] = Field(None)
    round: Optional[str] = Field(None)
    winner_home: Optional[bool] = Field(None, description="Whether home team won")
    winner_away: Optional[bool] = Field(None, description="Whether away team won")
    season: int = Field(..., description="Season year")
    events_json: Optional[List[Dict[str, Any]]] = None
    lineups_json: Optional[List[Dict[str, Any]]] = None
    team_stats_json: Optional[List[Dict[str, Any]]] = None
    player_stats_json: Optional[List[Dict[str, Any]]] = None

    # Foreign keys
    venue_id: Optional[int] = Field(None)
    league_id: int = Field(...)
    home_team_id: int = Field(...)
    away_team_id: int = Field(...)

    @field_validator('periods_first', 'periods_second', mode='before')
    def parse_periods(cls, v, values):
        if isinstance(v, dict):
            return v.get('first') if 'first' in v else v.get('second')
        return v

# --- Update Schema ---
class MatchUpdate(APIModel):
    referee: Optional[str] = Field(None)
    status_long: Optional[str] = Field(None)
    status_short: Optional[MatchStatusShort] = Field(None)
    status_elapsed: Optional[int] = Field(None)
    status_extra: Optional[int] = Field(None)
    goals_home: Optional[int] = Field(None)
    goals_away: Optional[int] = Field(None)
    score_halftime_home: Optional[int] = Field(None)
    score_halftime_away: Optional[int] = Field(None)
    score_fulltime_home: Optional[int] = Field(None)
    score_fulltime_away: Optional[int] = Field(None)
    score_extratime_home: Optional[int] = Field(None)
    score_extratime_away: Optional[int] = Field(None)
    score_penalty_home: Optional[int] = Field(None)
    score_penalty_away: Optional[int] = Field(None)
    season: Optional[int] = Field(None, description="Season year")

# --- Output Schema ---
class MatchOut(APIModel):
    match_id: int = Field(..., description="Internal match ID")
    external_match_id: int = Field(..., alias="id", description="Match ID from external API")
    referee: Optional[str] = Field(None)
    timezone: str = Field(...)
    date: datetime = Field(...)
    timestamp: int = Field(...)
    status_long: str = Field(...)
    status_short: MatchStatusShort = Field(...)
    status_elapsed: Optional[int] = Field(None)
    status_extra: Optional[int] = Field(None)
    goals_home: Optional[int] = Field(None)
    goals_away: Optional[int] = Field(None)
    score_halftime_home: Optional[int] = Field(None)
    score_halftime_away: Optional[int] = Field(None)
    score_fulltime_home: Optional[int] = Field(None)
    score_fulltime_away: Optional[int] = Field(None)
    score_extratime_home: Optional[int] = Field(None)
    score_extratime_away: Optional[int] = Field(None)
    score_penalty_home: Optional[int] = Field(None)
    score_penalty_away: Optional[int] = Field(None)
    round: Optional[str] = Field(None)
    season: int = Field(..., description="Season year")
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)
#    events: Optional[MatchEventsJsonPayload] = None
#    lineups: Optional[MatchLineupsJsonPayload] = None
#    team_stats: Optional[MatchTeamStatsJsonPayload] = None
#    player_stats: Optional[GroupedMatchPlayerStatsJsonPayload] = None    

    events: Optional[List[Dict[str, Any]]] = Field(default_factory=list, alias="events")
    lineups: Optional[List[Dict[str, Any]]] = Field(default_factory=list, alias="lineups")
    team_stats: Optional[List[Dict[str, Any]]] = Field(default_factory=list, alias="team_stats")
    player_stats: Optional[List[Dict[str, Any]]] = Field(default_factory=list, alias="player_stats")
 
    venue: Optional["VenueOut"] = Field(None)
    home_team: "TeamOut" = Field(...)
    away_team: "TeamOut" = Field(...)
    league_info: Dict[str, Any] = Field(
        ...,
        description="Basic league info (since league is no longer a relationship)",
        alias="league"
    )

# --- API Response Schemas ---
class MatchApiResponseItem(APIModel):
    fixture: FixtureAPIData
    league: LeagueAPIData
    teams: TeamsAPIData
    goals: GoalsAPIData
    score: ScoreBreakdownSchema
    events: Optional[List[SingleEventDataFromAPI]] = Field(default_factory=list) 
    lineups: Optional[List[SingleTeamLineupDataFromAPI]] = Field(default_factory=list) 
    statistics: Optional[List[SingleTeamStatisticDataFromAPI]] = Field(default_factory=list) 
    players: Optional[List[TeamPlayersStatsInFixtureAPI]] = Field(default_factory=list) 

class MatchApiResponse(APIModel):
    get: str = Field(..., description="Endpoint name")
    parameters: Dict[str, Any] = Field(..., description="Request parameters")
    errors: List[Any] = Field(default_factory=list)
    results: int = Field(..., description="Number of results")
    paging: Dict[str, int] = Field(..., description="Pagination info")
    response: List[MatchApiResponseItem]


