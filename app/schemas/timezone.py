# app/schemas/timezone.py
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List
from pydantic.alias_generators import to_camel

class APIModel(BaseModel):
    """Base model with common config for all schemas"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        extra="ignore"
    )

class TimezoneBase(APIModel):
    """Base schema for timezone data"""
    name: str = Field(
        ...,
        max_length=100,
        description="IANA timezone name (e.g., 'Europe/Istanbul')",
        pattern=r"^[A-Za-z_]+\/[A-Za-z_]+$",
        example="America/New_York"
    )

class TimezoneAPIInputData(APIModel):
    """Validates timezone data from external API"""
    timezone: str = Field(..., description="Timezone name from API")

class TimezoneCreateInternal(APIModel):
    """Schema for internal timezone creation"""
    name: str = Field(..., max_length=100, description="IANA timezone name")
    offset: Optional[int] = Field(None, description="UTC offset in minutes")

class TimezoneUpdate(APIModel):
    """Schema for updating timezone data"""
    name: Optional[str] = Field(
        None,
        max_length=100,
        description="New IANA timezone name",
        pattern=r"^[A-Za-z_]+\/[A-Za-z_]+$"
    )
    offset: Optional[int] = Field(None, description="New UTC offset in minutes")

class TimezoneOut(TimezoneBase):
    """Output schema for timezone data"""
    id: int = Field(..., description="Internal timezone ID")
    offset: Optional[int] = Field(None, description="UTC offset in minutes")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

class TimezoneListResponse(APIModel):
    """Paginated list of timezones"""
    count: int = Field(..., description="Total number of timezones")
    items: List[TimezoneOut] = Field(..., description="List of timezone records")