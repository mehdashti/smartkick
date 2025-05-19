# app/schemas/player.py
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import date, datetime
from pydantic.alias_generators import to_camel

if TYPE_CHECKING:
    from app.schemas.player_season_stats import PlayerSeasonStatsOut, PlayerStatisticItemAPI

# --- Base Config ---
class APIModel(BaseModel):
    """Base model with common config for all schemas"""
    model_config = ConfigDict(
        from_attributes=True,  # جایگزین orm_mode در Pydantic v2
        populate_by_name=True,  # اجازه استفاده از aliasها
        alias_generator=to_camel  # تبدیل خودکار به camelCase برای APIها
    )

# --- Base Schema ---
class PlayerBase(APIModel):
    """Base schema for player data (core data fields)."""
    name: str = Field(..., min_length=1, max_length=150, description="Player's full name")
    firstname: Optional[str] = Field(None, max_length=100, description="Player's first name")
    lastname: Optional[str] = Field(None, max_length=100, description="Player's last name")
    position: Optional[str] = Field(None, max_length=50, description="Player's primary position")
    photo_url: Optional[HttpUrl | str] = Field(None, description="URL of the player's photo")

# --- API Input Schema ---
class PlayerAPIInputData(APIModel):
    """Validates the structure of player data directly from the API."""
    id: int = Field(..., description="Player ID from external API")
    name: str
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    age: Optional[int] = None
    birth: Optional[Dict[str, Optional[str]]] = None
    nationality: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    injured: Optional[bool] = None
    number: Optional[int] = None
    position: Optional[str] = None
    photo: Optional[HttpUrl | str] = None

# --- Internal Create/Update Schema ---
class PlayerCreateInternal(PlayerBase):
    """Schema used internally for creating/updating players."""
    id: int = Field(..., description="Player ID from the external API")
    age: Optional[int] = Field(None, ge=0, description="Player's age")
    birth_date: Optional[date] = Field(None, description="Player's date of birth")
    birth_place: Optional[str] = Field(None, max_length=100)
    birth_country: Optional[str] = Field(None, max_length=100)
    nationality: Optional[str] = Field(None, max_length=100)
    is_injured: Optional[bool] = Field(None, alias="injured")
    height: Optional[str] = Field(None, max_length=20)
    weight: Optional[str] = Field(None, max_length=20)
    number: Optional[int] = Field(None)

# --- Update Schema ---
class PlayerUpdate(APIModel):
    """Schema for partially updating an existing player."""
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    firstname: Optional[str] = Field(None, max_length=100)
    lastname: Optional[str] = Field(None, max_length=100)
    age: Optional[int] = Field(None, ge=0)
    birth_date: Optional[date] = None
    birth_place: Optional[str] = Field(None, max_length=100)
    birth_country: Optional[str] = Field(None, max_length=100)
    nationality: Optional[str] = Field(None, max_length=100)
    height: Optional[str] = Field(None, max_length=20)
    weight: Optional[str] = Field(None, max_length=20)
    number: Optional[int] = None
    is_injured: Optional[bool] = Field(None, alias="injured")
    position: Optional[str] = Field(None, max_length=50)
    photo_url: Optional[HttpUrl | str] = None

# --- Output Schema ---
class PlayerOut(PlayerBase):
    """Schema for representing a player in API responses."""
    id: int = Field(..., description="Player ID (Primary Key)")
    age: Optional[int] = None
    birth_date: Optional[date] = None
    birth_place: Optional[str] = None
    birth_country: Optional[str] = None
    nationality: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    is_injured: Optional[bool] = None
    number: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    season_stats: Optional[List["PlayerSeasonStatsOut"]] = None

# --- API Response Schemas ---
class PlayerProfileApiResponseItem(APIModel):
    player: PlayerAPIInputData

class PlayerProfileApiResponse(APIModel):
    response: List[PlayerProfileApiResponseItem]

class PlayerWithStatsApiResponseItem(APIModel):
    player: PlayerAPIInputData
    statistics: List["PlayerStatisticItemAPI"]

class PlayerWithStatsApiResponse(APIModel):
    response: List[PlayerWithStatsApiResponseItem]
    paging: Optional[Dict[str, int]] = None

# حلقه‌های ارجاعی را برطرف می‌کنیم
#PlayerOut.model_rebuild()
#پPlayerWithStatsApiResponseItem.model_rebuild()