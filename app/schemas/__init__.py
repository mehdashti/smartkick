# app/schemas/__init__.py

# 1. Import all schema models that might be involved in forward references
# or are referenced by other models.
# The order of imports here doesn't strictly matter for definitions,
# but it's good practice to group them logically if possible.

from .country import (
    CountryBase, CountryAPIInputData, CountryCreateInternal,
    CountryUpdate, CountryOut, CountryListResponse
)
from .league import (
    LeagueBase, LeagueAPIInputData, LeagueCreateInternal,
    LeagueUpdate, LeagueOut, LeagueProfileApiResponseItem,
    LeagueProfileApiResponse, LeagueWithSeasonsApiResponseItem,
    LeagueWithSeasonsApiResponse
)
from .venue import (
    VenueBase, VenueAPIInputData, VenueCreateInternal,
    VenueUpdate, VenueOut, VenueListResponse
)
from .team import (
    TeamBase, TeamAPIInputData, TeamCreateInternal,
    TeamUpdate, TeamOut, TeamSummaryOut, TeamListResponse
)
from .player_season_stats import (
    StatsTeamAPI, StatsLeagueAPI, StatsGamesAPI, StatsSubstitutesAPI,
    StatsShotsAPI, StatsGoalsAPI, StatsPassesAPI, StatsTacklesAPI,
    StatsDuelsAPI, StatsDribblesAPI, StatsFoulsAPI, StatsCardsAPI,
    StatsPenaltyAPI, PlayerStatisticItemAPI, PlayerSeasonStatsBase,
    PlayerSeasonStatsCreateInternal, PlayerSeasonStatsUpdate,
    PlayerSeasonStatsOut, PlayerStatsApiResponseItem, PlayerStatsApiResponse
)
from .player import (
    PlayerBase, PlayerAPIInputData, PlayerCreateInternal,
    PlayerUpdate, PlayerOut, PlayerProfileApiResponseItem,
    PlayerProfileApiResponse, PlayerWithStatsApiResponseItem,
    PlayerWithStatsApiResponse
)
from .match import (
    MatchStatusShort, PeriodsSchema, VenueSchema, StatusSchema,
    TeamMatchInfoSchema, ScoreSchema, ScoreBreakdownSchema,
    FixtureAPIData, LeagueAPIData, TeamsAPIData, GoalsAPIData,
    MatchAPIInputData, MatchCreateInternal, MatchUpdate,
    MatchOut, MatchApiResponseItem, MatchApiResponse
)
from .timezone import (
    TimezoneBase, TimezoneAPIInputData, TimezoneCreateInternal,
    TimezoneUpdate, TimezoneOut, TimezoneListResponse
)
from .token import (
    TokenType, Token, TokenPayload, TokenData,
    RefreshTokenRequest, TokenRevocationRequest, TokenValidationResponse
)
from .user import (
    UserBase, UserCreate, UserUpdate, UserUpdateAdmin,
    UserPublic, UserInDB
)
from .tasks import (
    TaskQueueResponse
)


# 2. Call model_rebuild() for all models that use forward references
# or are part of a circular dependency.
# Pydantic V2 is generally good at detecting when a rebuild is needed,
# but explicit calls ensure forward references are resolved.

# It's often sufficient to call rebuild on models that directly use string forward refs.
# Models that are *referenced* by string (e.g., "CountryOut") also need to be defined
# before the referencing model is rebuilt.

# Schemas with forward references:
# - CountryOut (references "LeagueOut")
# - LeagueOut (references "CountryOut", "PlayerSeasonStatsOut")
# - MatchOut (references "VenueOut", "LeagueOut", "TeamOut")
# - PlayerOut (references "PlayerSeasonStatsOut")
# - PlayerSeasonStatsOut (references "PlayerOut", "TeamOut", "LeagueOut")
# - TeamOut (references "CountryOut", "VenueOut", "LeagueOut")
# - VenueOut (references "CountryOut", "TeamOut")

# It's safest to rebuild all involved models after all are imported.
# The order of rebuild calls here *can* matter if one model_rebuild()
# depends on another already being complete.
# Generally, rebuild models that are referenced before models that reference them,
# OR rebuild them all and Pydantic will handle the resolution order internally.
# For simplicity and robustness with Pydantic V2, rebuilding them all usually works.

model_rebuild_candidates = [
    CountryOut,
    LeagueOut,
    VenueOut,
    TeamOut,
    PlayerSeasonStatsOut,
    PlayerOut,
    MatchOut,
    # Add any other models if they use forward references or are part of such chains
    # For example, if PlayerListResponse contains PlayerOut, etc.
    CountryListResponse,
    LeagueProfileApiResponse,
    LeagueWithSeasonsApiResponse,
    VenueListResponse,
    TeamListResponse,
    PlayerProfileApiResponse,
    PlayerWithStatsApiResponse,
    PlayerStatsApiResponse,
    MatchApiResponse,
    TimezoneListResponse,
]

for model in model_rebuild_candidates:
    # Pydantic V2's model_rebuild is idempotent and handles dependencies well.
    # No need to check __pydantic_model_rebuild_required__ in most cases.
    model.model_rebuild()

# Schemas without apparent forward references (like User, Token, Timezone, Task)
# generally do not need explicit model_rebuild() unless they become part of
# a new circular dependency or use forward refs internally.

print("Schemas initialized and models rebuilt.") # Optional: for debugging