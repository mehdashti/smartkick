# app/schemas/coach.py
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import date, datetime
from pydantic.alias_generators import to_camel

if TYPE_CHECKING:
    from app.schemas.coach_careers import CoachCareersOut

# --- Base Config ---
class APIModel(BaseModel):
    """Base model with common config for all schemas"""
    model_config = ConfigDict(
        from_attributes=True,  
        populate_by_name=True, 
        alias_generator=to_camel  
    )

# --- Base Schema ---
class CoachBase(APIModel):
    """Base schema for coach data (core data fields)."""
    name: str = Field(..., min_length=1, max_length=150)
    firstname: Optional[str] = Field(None, max_length=100)
    lastname: Optional[str] = Field(None, max_length=100)
    photo_url: Optional[HttpUrl | str] = Field(None)

# --- API Input Schema ---
class CoachBirthData(APIModel):
    date: Optional[str] = None  
    place: Optional[str] = None
    country: Optional[str] = None

class TeamData(APIModel):
    id: Optional[int] = None
    name: Optional[str] = None
    logo: Optional[HttpUrl | str] = None

class CoachCareers(APIModel):
    team: TeamData
    start: Optional[str] = None
    end: Optional[str] = None

class CoachApiResponseItem(APIModel):
    id: int = Field(..., description="Coach ID from external API")
    name: str
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    age: Optional[int] = None
    birth: Optional[CoachBirthData] = None
    nationality: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    photo: Optional[HttpUrl | str] = None
    team: Optional[TeamData] = None
    career: Optional[List[CoachCareers]] = None

class CoachApiResponse(APIModel):
    get: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    errors: List[Any] = Field(default_factory=list)
    results: Optional[int] = None
    paging: Optional[Dict[str, int]] = None
    response: List[CoachApiResponseItem]

# --- Internal Create/Update Schema ---
class CoachCreateInternal(CoachBase):
    """Schema used internally for creating/updating coaches."""
    id: int = Field(..., description="Coach ID from the external API")
    name: str = Field(..., min_length=1, max_length=150)
    firstname: Optional[str] = Field(None, max_length=100)
    lastname: Optional[str] = Field(None, max_length=100)
    age: Optional[int] = Field(None, ge=0, description="Player's age")
    birth_date: Optional[date] = Field(None, description="Player's date of birth")
    birth_place: Optional[str] = Field(None, max_length=100)
    birth_country: Optional[str] = Field(None, max_length=100)
    nationality: Optional[str] = Field(None, max_length=100)
    height: Optional[str] = Field(None, max_length=20)
    weight: Optional[str] = Field(None, max_length=20)
    photo_url: Optional[HttpUrl | str] = Field(None, description="URL to the coach's photo")
    team_id: Optional[int] = Field(None, description="Team ID if the coach is associated with a team")
    career: Optional[List[Dict[str, Any]]] = Field(
        None, description="Career history of the coach, including teams and dates"
    )


# --- Update Schema ---
class CoachUpdate(APIModel):
    """Schema for partially updating an existing coach."""
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
    photo_url: Optional[HttpUrl | str] = None
    team_id: Optional[int] = Field(None, description="Team ID if the coach is associated with a team")
    career: Optional[List[Dict[str, Any]]] = Field(
        None, description="Career history of the coach, including teams and dates"
    )

# --- Output Schema ---
class CoachOut(CoachBase):
    """Schema for representing a coach in API responses."""
    id: int = Field(..., description="coach ID (Primary Key)")
    name: str
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    age: Optional[int] = None
    birth_date: Optional[date] = None
    birth_place: Optional[str] = None
    birth_country: Optional[str] = None
    nationality: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    photo_url: Optional[HttpUrl | str] = None
    team_id: Optional[int] = None
    career: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    updated_at: datetime








