# app/schemas/country.py
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from pydantic.alias_generators import to_camel

if TYPE_CHECKING:
    from app.schemas.league import LeagueOut

class APIModel(BaseModel):
    """Base model with common config for all schemas"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        extra="ignore"
    )

class CountryBase(APIModel):
    """Base schema for country data"""
    name: str = Field(..., min_length=2, max_length=100, description="Country name")
    code: Optional[str] = Field(None, min_length=2, max_length=10, description="Country code (e.g. 'US')")
    flag_url: Optional[HttpUrl | str] = Field(None, description="URL of country flag image")

class CountryAPIInputData(APIModel):
    """Validates the structure of country data directly from the API"""
    name: str
    code: Optional[str] = None
    flag: Optional[str] = None  # API might use different field name

class CountryCreateInternal(CountryBase):
    """Schema used internally for creating countries"""
    country_id: int = Field(..., description="Country ID from external API")

class CountryUpdate(APIModel):
    """Schema for updating country data"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    code: Optional[str] = Field(None, min_length=2, max_length=10)
    flag_url: Optional[HttpUrl | str] = Field(None)

class CountryOut(CountryBase):
    """Output schema for country data"""
    country_id: int = Field(..., description="Internal country ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Optional relationships
    leagues: Optional[List["LeagueOut"]] = Field(None, description="List of associated leagues")

class CountryListResponse(APIModel):
    """Schema for paginated list of countries"""
    count: int = Field(..., description="Total number of countries")
    items: List[CountryOut] = Field(..., description="List of country records")

# Handle forward references
#CountryOut.model_rebuild()