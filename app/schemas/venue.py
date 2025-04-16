# app/schemas/venue.py
from pydantic import BaseModel, Field, ConfigDict, HttpUrl
from typing import Optional
from datetime import datetime

# --- Base Schema ---
class VenueBase(BaseModel):
    """Base schema for venue data."""
    name: str = Field(..., max_length=150, description="Venue name")
    address: Optional[str] = Field(None, max_length=255, description="Venue address")
    city: Optional[str] = Field(None, max_length=100, description="City where the venue is located")
    capacity: Optional[int] = Field(None, gt=0, description="Venue capacity")
    surface: Optional[str] = Field(None, max_length=50, description="Playing surface")
    # استفاده از HttpUrl برای اعتبار سنجی بهتر URL
    image_url: Optional(HttpUrl | str) = Field(None, description="URL of the venue image") # HttpUrl برای اعتبارسنجی، اما str هم قبول کند

# --- Schema for Creation (from API data) ---
class VenueCreate(VenueBase):
    """Schema used when creating a venue, requires external_id."""
    external_id: int = Field(..., description="Venue ID from the external API (API-Football)")

# --- Schema for Update ---
class VenueUpdate(VenueBase):
    """Schema for updating an existing venue. All fields are optional."""
    # name معمولاً نباید None شود ولی برای انعطاف‌پذیری Optional می‌گذاریم
    name: Optional[str] = Field(None, max_length=150)
    # external_id نباید آپدیت شود

# --- Schema for Output ---
class VenueOut(VenueBase):
    """Schema for representing venue data in API responses."""
    venue_id: int = Field(..., description="Internal unique ID for the venue")
    external_id: int = Field(..., description="Venue ID from the external API")
    created_at: datetime = Field(..., description="Timestamp when the venue was created")
    updated_at: datetime = Field(..., description="Timestamp when the venue was last updated")

    # Pydantic V2: ConfigDict replaces Config class
    model_config = ConfigDict(from_attributes=True) # Enable ORM mode