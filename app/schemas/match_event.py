# app/schemas/match_event.py
# app/schemas/match_event.py

from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime
from pydantic.alias_generators import to_camel


class APIModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        extra="ignore"
    )

if TYPE_CHECKING:
    from app.schemas.team import TeamOut
    # class PlayerOut(APIModel): # Placeholder
    #     player_id: int
    #     name: str


# --- اسکیمای تو در تو برای پارس کردن یک رویداد از پاسخ API ---
class EventTimeSchema(APIModel):
    elapsed: int
    extra: Optional[int] = None

class EventTeamSchema(APIModel):
    id: int
    name: str
    logo: Optional[HttpUrl | str] = None

class EventPlayerSchema(APIModel):
    id: Optional[int] = None # ID می‌تواند null باشد (مثلاً برای پاس گل)
    name: Optional[str] = None # Name می‌تواند null باشد

# --- اسکیمای اصلی برای یک آیتم رویداد منفرد از پاسخ API ---
class SingleEventDataFromAPI(APIModel):
    """اسکیما برای یک آیتم رویداد منفرد در فیلد 'response' پاسخ API."""
    time: EventTimeSchema
    team: EventTeamSchema
    player: EventPlayerSchema
    assist: EventPlayerSchema # برای بازیکن پاس گل دهنده
    type: str
    detail: str
    comments: Optional[str] = None

# --- اسکیمای اصلی برای کل پاسخ API مربوط به رویدادهای مسابقه ---
class MatchEventApiResponse(APIModel):
    """اسکیما برای کل پاسخ API مربوط به رویدادهای مسابقه."""
    get: Optional[str] = None # می‌تواند وجود نداشته باشد اگر مستقیم فقط بخش response را می‌گیریم
    parameters: Optional[Dict[str, Any]] = None
    errors: List[Any] = Field(default_factory=list)
    results: Optional[int] = None
    paging: Optional[Dict[str, int]] = None
    response: List[SingleEventDataFromAPI] # << لیستی از رویدادها

# --- اسکیماهای داخلی برای تعامل با پایگاه داده ---

class MatchEventCreateInternal(APIModel):
    match_id: int
    time_elapsed: int
    time_extra: Optional[int] = None
    team_id: int
    team_name_snapshot: str
    # team_logo_snapshot: Optional[HttpUrl | str] = None # اگر تصمیم به ذخیره آن دارید

    player_id: Optional[int] = None
    player_name_snapshot: Optional[str] = None

    assist_player_id: Optional[int] = None
    assist_player_name_snapshot: Optional[str] = None

    event_type: str
    event_detail: str
    comments: Optional[str] = None
    # model_config از APIModel به ارث برده می‌شود، نیازی به تکرار نیست مگر برای override


class MatchEventUpdate(APIModel):
    time_elapsed: Optional[int] = None
    time_extra: Optional[int] = None
    event_type: Optional[str] = None
    event_detail: Optional[str] = None
    comments: Optional[str] = None
    team_name_snapshot: Optional[str] = None
    # team_logo_snapshot: Optional[HttpUrl | str] = None
    player_name_snapshot: Optional[str] = None
    assist_player_name_snapshot: Optional[str] = None
    # model_config از APIModel به ارث برده می‌شود


class MatchEventOut(APIModel):
    match_event_id: int = Field(..., alias="id") # اگر نام فیلد در دیتابیس id است
    match_id: int

    time_elapsed: int
    time_extra: Optional[int] = None

    event_type: str
    event_detail: str
    comments: Optional[str] = None

    team_id: int
    team_name_snapshot: str
    # team_logo_snapshot: Optional[HttpUrl | str] = None # اگر ذخیره و نمایش می‌دهید

    player_id: Optional[int] = None
    player_name_snapshot: Optional[str] = None

    assist_player_id: Optional[int] = None
    assist_player_name_snapshot: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "matchEventId": 123,
                "matchId": 215662,
                "timeElapsed": 25,
                "eventType": "Goal",
                "eventDetail": "Normal Goal",
                "teamId": 463,
                "teamNameSnapshot": "Aldosivi",
                "playerId": 6126,
                "playerNameSnapshot": "F. Andrada",
                "createdAt": "2023-10-26T10:00:00Z",
                "updatedAt": "2023-10-26T10:00:00Z"
            }
        }
    )

# اگر از TYPE_CHECKING استفاده می‌کنید و این اسکیماها به هم وابستگی دارند:
# if TYPE_CHECKING:
#     MatchEventOut.model_rebuild()