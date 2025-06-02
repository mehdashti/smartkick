# app/schemas/coach_careers.py
from pydantic import BaseModel, ConfigDict, Field
from datetime import date, datetime
from typing import Optional
from pydantic.alias_generators import to_camel

if TYPE_CHECKING:
    from app.schemas.coach import CoachCareers

class APIModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel
    )

class CoachCareersBase(APIModel):
    team_id: int
    team_name: str
    logo_url: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class CoachCareersCreate(CoachCareersBase):
    coach_id: int
    team_id: int
    team_name: Optional[str] = None
    logo_url: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class CoachCareersUpdate(APIModel):
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    logo_url: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class CoachCareersOut(CoachCareersBase):
    id: int
    coach_id: int
    created_at: datetime
    updated_at: datetime

class CoachCareersInDB(CoachCareersOut):
    pass