# app/schemas/player_season_stats.py
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime
from pydantic.alias_generators import to_camel

if TYPE_CHECKING:
    from app.schemas.player import PlayerOut
    from app.schemas.team import TeamOut
    from app.schemas.league import LeagueOut

class APIModel(BaseModel):
    """Base model with common config for all schemas"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        extra="ignore"
    )

# --- API Data Schemas ---
class StatsTeamAPI(APIModel):
    """Team data from external API"""
    id: int = Field(..., description="External team ID")
    name: str = Field(..., description="Team name")
    logo: Optional[str] = Field(None, description="Team logo URL")

class StatsLeagueAPI(APIModel):
    """League data from external API"""
    id: int = Field(..., description="External league ID")
    name: str = Field(..., description="League name")
    country: Optional[str] = Field(None, description="Country name")
    logo: Optional[str] = Field(None, description="League logo URL")
    flag: Optional[str] = Field(None, description="Country flag URL")
    season: int = Field(..., description="Season year")

class StatsGamesAPI(APIModel):
    """Games statistics from API"""
    appearences: Optional[int] = Field(None, description="Number of appearances")
    lineups: Optional[int] = Field(None, description="Number of starts in lineup")
    minutes: Optional[int] = Field(None, description="Minutes played")
    number: Optional[int] = Field(None, description="Jersey number")
    position: Optional[str] = Field(None, description="Player position")
    rating: Optional[float] = Field(None, description="Average rating")
    captain: Optional[bool] = Field(False, description="Is team captain")

    @field_validator('rating', mode='before')
    def validate_rating(cls, v):
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                return None
        return v

class StatsSubstitutesAPI(APIModel):
    """Substitute statistics from API"""
    in_: Optional[int] = Field(None, alias="in", description="Substituted in")
    out: Optional[int] = Field(None, description="Substituted out")
    bench: Optional[int] = Field(None, description="On bench")

class StatsShotsAPI(APIModel):
    """Shooting statistics from API"""
    total: Optional[int] = Field(None, description="Total shots")
    on: Optional[int] = Field(None, description="Shots on target")

class StatsGoalsAPI(APIModel):
    """Goal statistics from API"""
    total: Optional[int] = Field(None, description="Goals scored")
    conceded: Optional[int] = Field(None, description="Goals conceded (for GKs)")
    assists: Optional[int] = Field(None, description="Assists provided")
    saves: Optional[int] = Field(None, description="Saves made (for GKs)")

class StatsPassesAPI(APIModel):
    """Passing statistics from API"""
    total: Optional[int] = Field(None, description="Total passes")
    key: Optional[int] = Field(None, description="Key passes")
    accuracy: Optional[int] = Field(None, description="Pass accuracy percentage")

    @field_validator('accuracy', mode='before')
    def validate_accuracy(cls, v):
        if isinstance(v, str):
            try:
                return int(v.replace('%', ''))
            except ValueError:
                return None
        return v

class StatsTacklesAPI(APIModel):
    """Tackling statistics from API"""
    total: Optional[int] = Field(None, description="Total tackles")
    blocks: Optional[int] = Field(None, description="Blocks made")
    interceptions: Optional[int] = Field(None, description="Interceptions made")

class StatsDuelsAPI(APIModel):
    """Duel statistics from API"""
    total: Optional[int] = Field(None, description="Total duels")
    won: Optional[int] = Field(None, description="Duels won")

class StatsDribblesAPI(APIModel):
    """Dribbling statistics from API"""
    attempts: Optional[int] = Field(None, description="Dribble attempts")
    success: Optional[int] = Field(None, description="Successful dribbles")
    past: Optional[int] = Field(None, description="Players dribbled past")

class StatsFoulsAPI(APIModel):
    """Foul statistics from API"""
    drawn: Optional[int] = Field(None, description="Fouls drawn")
    committed: Optional[int] = Field(None, description="Fouls committed")

class StatsCardsAPI(APIModel):
    """Card statistics from API"""
    yellow: Optional[int] = Field(None, description="Yellow cards")
    yellowred: Optional[int] = Field(None, description="Yellow-red cards")
    red: Optional[int] = Field(None, description="Red cards")

class StatsPenaltyAPI(APIModel):
    """Penalty statistics from API"""
    won: Optional[int] = Field(None, description="Penalties won")
    commited: Optional[int] = Field(None, description="Penalties committed")
    scored: Optional[int] = Field(None, description="Penalties scored")
    missed: Optional[int] = Field(None, description="Penalties missed")
    saved: Optional[int] = Field(None, description="Penalties saved")

class PlayerStatisticItemAPI(APIModel):
    """Complete player statistics item from API"""
    team: StatsTeamAPI
    league: StatsLeagueAPI
    games: StatsGamesAPI
    substitutes: StatsSubstitutesAPI
    shots: StatsShotsAPI
    goals: StatsGoalsAPI
    passes: StatsPassesAPI
    tackles: StatsTacklesAPI
    duels: StatsDuelsAPI
    dribbles: StatsDribblesAPI
    fouls: StatsFoulsAPI
    cards: StatsCardsAPI
    penalty: StatsPenaltyAPI

# --- Internal Schemas ---
class PlayerSeasonStatsBase(APIModel):
    """Base schema for player season statistics"""
    player_id: int = Field(..., description="Internal player ID")
    team_id: int = Field(..., description="Internal team ID")
    league_id: int = Field(..., description="Internal league ID")
    season: int = Field(..., description="Season year")

class PlayerSeasonStatsCreateInternal(PlayerSeasonStatsBase):
    """Schema for creating player season stats from API data"""
    appearences: Optional[int] = Field(None, description="Number of appearances")
    lineups: Optional[int] = Field(None, description="Number of starts in lineup")
    minutes: Optional[int] = Field(None, description="Minutes played")
    player_number: Optional[int] = Field(None, description="Jersey number")
    position: Optional[str] = Field(None, description="Player position")
    rating: Optional[float] = Field(None, description="Average rating")
    captain: Optional[bool] = Field(None, description="Is team captain")
    
    sub_in: Optional[int] = Field(None, description="Substituted in")
    sub_out: Optional[int] = Field(None, description="Substituted out")
    sub_bench: Optional[int] = Field(None, description="On bench")
    
    shots_total: Optional[int] = Field(None, description="Total shots")
    shots_on: Optional[int] = Field(None, description="Shots on target")
    
    goals_total: Optional[int] = Field(None, description="Goals scored")
    goals_conceded: Optional[int] = Field(None, description="Goals conceded")
    goals_assists: Optional[int] = Field(None, description="Assists provided")
    goals_saves: Optional[int] = Field(None, description="Saves made")
    
    passes_total: Optional[int] = Field(None, description="Total passes")
    passes_key: Optional[int] = Field(None, description="Key passes")
    passes_accuracy: Optional[int] = Field(None, description="Pass accuracy %")
    
    tackles_total: Optional[int] = Field(None, description="Total tackles")
    tackles_blocks: Optional[int] = Field(None, description="Blocks made")
    tackles_interceptions: Optional[int] = Field(None, description="Interceptions")
    
    duels_total: Optional[int] = Field(None, description="Total duels")
    duels_won: Optional[int] = Field(None, description="Duels won")
    
    dribbles_attempts: Optional[int] = Field(None, description="Dribble attempts")
    dribbles_success: Optional[int] = Field(None, description="Successful dribbles")
    dribbles_past: Optional[int] = Field(None, description="Players dribbled past")
    
    fouls_drawn: Optional[int] = Field(None, description="Fouls drawn")
    fouls_committed: Optional[int] = Field(None, description="Fouls committed")
    
    cards_yellow: Optional[int] = Field(None, description="Yellow cards")
    cards_yellowred: Optional[int] = Field(None, description="Yellow-red cards")
    cards_red: Optional[int] = Field(None, description="Red cards")
    
    penalty_won: Optional[int] = Field(None, description="Penalties won")
    penalty_committed: Optional[int] = Field(None, description="Penalties committed")
    penalty_scored: Optional[int] = Field(None, description="Penalties scored")
    penalty_missed: Optional[int] = Field(None, description="Penalties missed")
    penalty_saved: Optional[int] = Field(None, description="Penalties saved")

class PlayerSeasonStatsUpdate(APIModel):
    """Schema for updating player season stats"""
    # Include all the same fields as Create but all optional
    # (Same fields as CreateInternal but all Optional[...])

class PlayerSeasonStatsOut(PlayerSeasonStatsCreateInternal):
    """Output schema for player season statistics"""
    stat_id: int = Field(..., description="Internal stats ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    # Optional relationships
    player: Optional["PlayerOut"] = Field(None, description="Player details")
    team: Optional["TeamOut"] = Field(None, description="Team details")
    league: Optional["LeagueOut"] = Field(None, description="League details")

# --- API Response Schemas ---
class PlayerStatsApiResponseItem(APIModel):
    """Single item in API stats response"""
    player: Dict[str, Any] = Field(..., description="Player data")
    statistics: List[PlayerStatisticItemAPI] = Field(..., description="Stats data")

class PlayerStatsApiResponse(APIModel):
    """Complete API stats response"""
    response: List[PlayerStatsApiResponseItem] = Field(..., description="Stats items")
    paging: Optional[Dict[str, int]] = Field(None, description="Pagination info")

# Handle forward references
#PlayerSeasonStatsOut.model_rebuild()