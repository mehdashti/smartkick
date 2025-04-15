# app/schemas/timezone.py

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

class TimezoneBase(BaseModel):
    """Base schema for Timezone"""
    name: str = Field(..., max_length=100, description="Unique name of the timezone (e.g., Europe/Istanbul)")

class TimezoneCreate(TimezoneBase):
    """Schema for creating a new timezone"""
    pass

class TimezoneUpdate(BaseModel):
    """Schema for updating an existing timezone"""
    name: Optional[str] = Field(None, max_length=100, description="New name of the timezone")

class TimezoneOut(TimezoneBase):
    """Schema for returning timezone data"""
    id: int = Field(..., description="Primary ID of the timezone")
    created_at: datetime = Field(..., description="Timestamp when the record was created")
    updated_at: datetime = Field(..., description="Timestamp when the record was last updated")

    model_config = ConfigDict(from_attributes=True)
