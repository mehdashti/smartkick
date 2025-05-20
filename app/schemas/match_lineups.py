# app/schemas/match_lineup.py
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime
from pydantic.alias_generators import to_camel


if TYPE_CHECKING:
    from app.schemas.team import TeamOut # اگر TeamOut در جای دیگری تعریف شده
    from app.schemas.match import MatchOut # اگر MatchOut در جای دیگری تعریف شده

class APIModel(BaseModel):
    """Base model with common config for all schemas"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        extra="ignore"
    )

# --- Nested Schemas ---
class CoachSchema(APIModel):
    id: int = Field(..., description="Coach ID from external API")
    name: str = Field(..., description="Coach full name")
    photo: Optional[HttpUrl | str] = Field(None, description="Coach photo URL")

# TeamColorsSchema بدون تغییر باقی می‌ماند، چون ساختار داخلی colors را به درستی تعریف می‌کند
class TeamColorsSchema(APIModel):
    player: Dict[str, str] = Field(..., example={"primary": "5badff", "number": "ffffff"})
    goalkeeper: Dict[str, str] = Field(..., example={"primary": "99ff99", "number": "000000"})

class PlayerSchema(APIModel):
    id: int = Field(..., description="Player ID from external API")
    name: str = Field(..., description="Player full name")
    number: Optional[int] = Field(None, ge=1, le=99)
    pos: Optional[str] = Field(None, min_length=1, max_length=5, example="GK")
    grid: Optional[str] = Field(None, pattern=r"^\d+:\d+$", example="2:4")

# --- اسکیمای جدید برای اطلاعات تیم در ترکیب از API ---
class TeamAPIDataForLineup(APIModel):
    id: int
    name: str
    logo: Optional[HttpUrl | str] = None
    colors: Optional[TeamColorsSchema] = None # <<<< فیلد colors اینجا و Optional تعریف شده است

# --- API Input Schemas (اصلاح شده) ---
class MatchLineupAPIData(APIModel):
    team: TeamAPIDataForLineup = Field(..., description="Team info from API") # <<<< استفاده از اسکیمای جدید
    formation: Optional[str] = Field(None, max_length=20, example="4-3-3")
    startXI: List[Dict[str, PlayerSchema]] = Field(
        default_factory=list,
        example=[{"player": {"id": 617, "name": "Ederson", "pos": "G"}}]
    )
    substitutes: List[Dict[str, PlayerSchema]] = Field(default_factory=list)
    coach: Optional[CoachSchema] = None # <<<< Optional کردن coach چون ممکن است API همیشه آن را نفرستد
    # فیلد colors از این سطح حذف شد

# --- Internal Create/Update Schemas ---
class MatchLineupCreateInternal(APIModel):
    match_id: int = Field(..., description="Related match ID")
    team_id: int = Field(..., description="Team ID from external API")
    team_name: str = Field(..., max_length=100)
    formation: Optional[str] = Field(None)
    startXI: Optional[List[Dict[str, Any]]] = Field( # <<<< تغییر به List برای سازگاری بیشتر با JSONB
        None,
        examples=[[{"player": {"id": 617, "grid": "1:1"}}]],
        description="JSONB field for starting XI"
    )
    substitutes: Optional[List[Dict[str, Any]]] = Field(None, description="JSONB field for substitutes") # <<<< تغییر به List
    coach_id: Optional[int] = Field(None)
    coach_name: Optional[str] = Field(None, max_length=100)
    coach_photo: Optional[str] = Field(None, max_length=200)
    team_colors: Optional[Dict[str, Any]] = Field(None, description="JSONB field for team colors")

# --- Update Schema ---
class MatchLineupUpdate(APIModel):
    formation: Optional[str] = Field(None)
    startXI: Optional[List[Dict[str, Any]]] = Field(None) # <<<< تغییر به List
    substitutes: Optional[List[Dict[str, Any]]] = Field(None) # <<<< تغییر به List
    coach_id: Optional[int] = Field(None)
    coach_name: Optional[str] = Field(None)
    coach_photo: Optional[str] = Field(None)
    team_colors: Optional[Dict[str, Any]] = Field(None)

# --- Output Schema ---
class MatchLineupOut(APIModel):
    lineup_id: int = Field(..., alias="id", description="Internal lineup ID") # << از alias استفاده کنید اگر نام فیلد در مدل دیتابیس id است
    match_id: int
    team_id: int
    team_name: str
    formation: Optional[str] = None
    startXI: Optional[List[Dict[str, Any]]] = Field(None) # <<<< تغییر به List
    substitutes: Optional[List[Dict[str, Any]]] = Field(None) # <<<< تغییر به List
    coach_id: Optional[int] = None
    coach_name: Optional[str] = None
    coach_photo: Optional[str] = None
    team_colors: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    # Relationships (این بخش بستگی به تعریف MatchOut و TeamOut دارد)
    # match: Optional["MatchOut"] = None
    # team: Optional["TeamOut"] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "lineupId": 1, # با توجه به alias_generator=to_camel
                "matchId": 592872,
                "teamId": 50,
                "teamName": "Manchester City",
                "formation": "4-3-3",
                "startXI": [{"player": {"id": 617, "name": "Ederson"}}],
                "coachName": "Guardiola",
                "createdAt": "2023-08-15T15:00:00Z", # معمولاً با Z برای UTC
                "updatedAt": "2023-08-15T15:00:00Z"
            }
        }
    )

# --- API Response Schema ---
class MatchLineupApiResponse(APIModel):
    get: str = Field(..., example="fixtures/lineups")
    parameters: Dict[str, Any] = Field(..., example={"fixture": 592872})
    errors: List[Any] = Field(default_factory=list)
    results: int = Field(...)
    paging: Dict[str, int] = Field(...)
    response: List[MatchLineupAPIData] # << لیستی از آبجکت‌های ترکیب تیم‌ها

# اگر MatchOut و TeamOut در این فایل تعریف نشده‌اند، این خط ممکن است لازم نباشد یا باید تنظیم شود
# MatchLineupOut.model_rebuild()