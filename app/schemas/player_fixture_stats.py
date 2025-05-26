# app/schemas/player_fixture_stats.py

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime
from pydantic.alias_generators import to_camel

if TYPE_CHECKING:
    from app.schemas.player import PlayerOut
    from app.schemas.team import TeamOut
    from app.schemas.match import MatchOut 
    pass

class APIModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        extra="ignore"
    )

class StatsTeamInfoForFixtureAPI(APIModel):
    id: int
    name: str
    logo: Optional[HttpUrl | str] = None
    update: Optional[datetime | str] = None

class PlayerSimpleInfoForFixtureAPI(APIModel):
    id: int
    name: str
    photo: Optional[HttpUrl | str] = None

class GamesStatsForFixtureAPI(APIModel):
    minutes: Optional[int] = None
    number: Optional[int] = None
    position: Optional[str] = None
    rating: Optional[float | str] = None
    captain: Optional[bool] = False
    substitute: Optional[bool] = None

    @field_validator('rating', mode='before')
    def validate_rating(cls, v):
        if v is None: return None
        if isinstance(v, str):
            try:
                return float(v)
            except (ValueError, TypeError):
                return None
        return v

class ShotsStatsAPI(APIModel):
    total: Optional[int] = None
    on: Optional[int] = None

class GoalsStatsAPI(APIModel):
    total: Optional[int] = None
    conceded: Optional[int] = None
    assists: Optional[int] = None
    saves: Optional[int] = None

class PassesStatsAPI(APIModel):
    total: Optional[int] = None
    key: Optional[int] = None
    accuracy: Optional[int | str] = None

    @field_validator('accuracy', mode='before')
    def validate_accuracy(cls, v):
        if v is None: return None
        if isinstance(v, str):
            try:
                return int(v.replace('%', ''))
            except (ValueError, TypeError):
                return None
        return v

class TacklesStatsAPI(APIModel):
    total: Optional[int] = None
    blocks: Optional[int] = None
    interceptions: Optional[int] = None

class DuelsStatsAPI(APIModel):
    total: Optional[int] = None
    won: Optional[int] = None

class DribblesStatsAPI(APIModel):
    attempts: Optional[int] = None
    success: Optional[int] = None
    past: Optional[int] = None

class FoulsStatsAPI(APIModel):
    drawn: Optional[int] = None
    committed: Optional[int] = None

class CardsStatsAPI(APIModel):
    yellow: Optional[int] = None
    red: Optional[int] = None
    # yellowred در این خروجی وجود ندارد

class PenaltyStatsAPI(APIModel):
    won: Optional[int] = None
    commited: Optional[int] = None # بر اساس JSON شما
    scored: Optional[int] = None
    missed: Optional[int] = None
    saved: Optional[int] = None

class PlayerStatisticsForFixtureAPI(APIModel):
    games: GamesStatsForFixtureAPI
    offsides: Optional[int] = None
    shots: ShotsStatsAPI
    goals: GoalsStatsAPI
    passes: PassesStatsAPI
    tackles: TacklesStatsAPI
    duels: DuelsStatsAPI
    dribbles: DribblesStatsAPI
    fouls: FoulsStatsAPI
    cards: CardsStatsAPI
    penalty: PenaltyStatsAPI

class PlayerDetailInFixtureAPI(APIModel):
    player: PlayerSimpleInfoForFixtureAPI
    statistics: List[PlayerStatisticsForFixtureAPI]

class TeamPlayersStatsInFixtureAPI(APIModel):
    team: StatsTeamInfoForFixtureAPI
    players: List[PlayerDetailInFixtureAPI]

class FixturePlayersStatsApiResponse(APIModel):
    get: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    errors: List[Any] = Field(default_factory=list)
    results: Optional[int] = None
    paging: Optional[Dict[str, int]] = None
    response: List[TeamPlayersStatsInFixtureAPI]

# --- اسکیماهای داخلی برای ذخیره آمار بازیکن در یک بازی خاص ---
class PlayerFixtureStatsBase(APIModel):
    player_id: int
    match_id: int # یا match_id بسته به نامگذاری شما
    team_id: int

class PlayerFixtureStatsCreateInternal(PlayerFixtureStatsBase):
    minutes_played: Optional[int] = None
    player_number: Optional[int] = None
    position: Optional[str] = None
    rating: Optional[float] = None
    captain: Optional[bool] = None
    substitute: Optional[bool] = None
    offsides: Optional[int] = None
    shots_total: Optional[int] = None
    shots_on: Optional[int] = None
    goals_total: Optional[int] = None
    goals_conceded: Optional[int] = None
    goals_assists: Optional[int] = None
    goals_saves: Optional[int] = None
    passes_total: Optional[int] = None
    passes_key: Optional[int] = None
    passes_accuracy_percentage: Optional[int] = None
    tackles_total: Optional[int] = None
    tackles_blocks: Optional[int] = None
    tackles_interceptions: Optional[int] = None
    duels_total: Optional[int] = None
    duels_won: Optional[int] = None
    dribbles_attempts: Optional[int] = None
    dribbles_success: Optional[int] = None
    dribbles_past: Optional[int] = None
    fouls_drawn: Optional[int] = None
    fouls_committed: Optional[int] = None
    cards_yellow: Optional[int] = None
    cards_red: Optional[int] = None
    penalty_won: Optional[int] = None
    penalty_committed: Optional[int] = None
    penalty_scored: Optional[int] = None
    penalty_missed: Optional[int] = None
    penalty_saved: Optional[int] = None

class PlayerFixtureStatsUpdate(PlayerFixtureStatsCreateInternal):
    pass

class PlayerFixtureStatsOut(PlayerFixtureStatsCreateInternal):
    stat_id: int = Field(..., alias="id")
    created_at: datetime
    updated_at: datetime
    # player: Optional["PlayerOut"] = None
    # team: Optional["TeamOut"] = None
    # match: Optional["MatchOut"] = None # یا FixtureOut

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "statId": 1,
                "playerId": 35931,
                "matchId": 169080,
                "teamId": 2284,
                "minutesPlayed": 90,
                "rating": 6.3,
                "goalsConceded": 1,
                "createdAt": "2023-01-01T00:00:00Z",
                "updatedAt": "2023-01-01T00:00:00Z"
            }
        }
    )