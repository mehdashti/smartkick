# app/schemas/venue.py
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime
from pydantic.alias_generators import to_camel

if TYPE_CHECKING:
    from app.schemas.country import CountryOut
    from app.schemas.team import TeamOut

class APIModel(BaseModel):
    """Base model with common config for all schemas"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        extra="ignore"
    )

class VenueBase(APIModel):
    """Base schema for venue data"""
    name: str = Field(..., max_length=150, description="Official venue name")
    address: Optional[str] = Field(None, max_length=255, description="Full physical address")
    city: Optional[str] = Field(None, max_length=100, description="City location")
    capacity: Optional[int] = Field(None, gt=0, description="Seating capacity")
    surface: Optional[str] = Field(None, max_length=50, description="Playing surface type")
    image_url: Optional[HttpUrl | str] = Field(None, description="URL of venue image")

class VenueAPIInputData(APIModel):
    """Validates venue data structure from external API"""
    id: int = Field(..., description="External API venue ID")
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    capacity: Optional[int] = None
    surface: Optional[str] = None
    image: Optional[str] = Field(None, description="Image URL from API")

class VenueCreateInternal(APIModel):
    """Schema for internal venue creation"""
    venue_id: int = Field(..., description="External API venue ID")
    name: str = Field(...)
    address: Optional[str] = Field(None)
    city: Optional[str] = Field(None)
    capacity: Optional[int] = Field(None)
    surface: Optional[str] = Field(None)
    image_url: Optional[HttpUrl | str] = Field(None)
    country_id: Optional[int] = Field(None, description="Associated country ID")

    @field_validator('image_url', mode='before')
    def validate_image_url(cls, v, values):
        if v == "":
            return None
        return v

class VenueUpdate(APIModel):
    """Schema for updating venue data"""
    name: Optional[str] = Field(None, max_length=150)
    address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    capacity: Optional[int] = Field(None, gt=0)
    surface: Optional[str] = Field(None, max_length=50)
    image_url: Optional[HttpUrl | str] = None
    country_id: Optional[int] = None

class VenueOut(VenueBase):
    """Output schema for venue data"""
    venue_id: int = Field(..., description="Internal venue ID")
    country_id: Optional[int] = Field(None, description="Associated country ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    # Relationships
    country: Optional["CountryOut"] = Field(None, description="Country details")
    teams: Optional[List["TeamOut"]] = Field(None, description="Teams using this venue")

class VenueListResponse(APIModel):
    """Paginated list of venues"""
    count: int = Field(..., description="Total number of venues")
    items: List[VenueOut] = Field(..., description="List of venue records")

# Handle forward references
#VenueOut.model_rebuild()