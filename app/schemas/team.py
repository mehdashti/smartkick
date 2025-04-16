# app/schemas/team.py
from pydantic import BaseModel, Field, ConfigDict, HttpUrl
from typing import Optional
from datetime import datetime

# --- وارد کردن اسکیماهای وابسته ---
# فرض می‌کنیم این فایل‌ها از قبل وجود دارند و CountryOut و VenueOut را تعریف می‌کنند
from .country import CountryOut
from .venue import VenueOut

# --- Base Schema ---
class TeamBase(BaseModel):
    """Base schema for team data."""
    name: str = Field(..., max_length=100, description="Team name")
    code: Optional[str] = Field(None, max_length=10, description="Team code (e.g., 3-letter code)")
    founded: Optional[int] = Field(None, gt=1800, lt=2100, description="Year the team was founded")
    is_national: bool = Field(..., description="True if it's a national team")
    logo_url: Optional(HttpUrl | str) = Field(None, description="URL of the team logo")

# --- Schema for Creation (from API data) ---
class TeamCreate(TeamBase):
    """Schema used when creating a team."""
    external_id: int = Field(..., description="Team ID from the external API (API-Football)")
    country_id: int = Field(..., description="Internal ID of the associated country")
    # venue_id هنگام ایجاد از API ممکن است هنوز وجود نداشته باشد یا نیاز به ایجاد داشته باشد،
    # پس در سرویس مقداردهی می‌شود و اینجا نمی‌گذاریم یا Optional است
    venue_external_id: Optional[int] = Field(None, description="External ID of the venue (used by service to find/create venue)")

# --- Schema for Update ---
class TeamUpdate(BaseModel):
    """Schema for updating an existing team. All fields are optional."""
    name: Optional[str] = Field(None, max_length=100)
    code: Optional[str] = Field(None, max_length=10)
    founded: Optional[int] = Field(None, gt=1800, lt=2100)
    is_national: Optional[bool] = None
    logo_url: Optional(HttpUrl | str) = None
    # آپدیت country_id یا venue_id معمولاً از طریق سرویس‌های خاص انجام می‌شود
    venue_id: Optional[int] = Field(None, description="Update the internal venue ID association")


# --- Schema for Output ---
class TeamOut(TeamBase):
    """Schema for representing team data in API responses."""
    team_id: int = Field(..., description="Internal unique ID for the team")
    external_id: int = Field(..., description="Team ID from the external API")
    created_at: datetime = Field(..., description="Timestamp when the team was created")
    updated_at: datetime = Field(..., description="Timestamp when the team was last updated")

    # --- نمایش داده‌های مرتبط ---
    # از اسکیمای Out مربوطه استفاده می‌کنیم
    country: Optional[CountryOut] = Field(None, description="Associated country data")
    venue: Optional[VenueOut] = Field(None, description="Associated venue data")

    # Pydantic V2: ConfigDict replaces Config class
    model_config = ConfigDict(from_attributes=True) # Enable ORM mode

# (اختیاری) اسکیمای خلاصه برای لیست‌ها
class TeamSummaryOut(BaseModel):
    team_id: int
    external_id: int
    name: str
    logo_url: Optional(HttpUrl | str) = None
    country_name: Optional[str] = Field(None, validation_alias="country.name") # گرفتن نام کشور از رابطه

    model_config = ConfigDict(from_attributes=True)