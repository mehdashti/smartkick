# app/models/match_lineup.py
from sqlalchemy import Integer, String, Boolean, ForeignKey, DateTime, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.team import Team
    from app.models.match import Match 

class MatchLineup(Base):
    __tablename__ = "match_lineups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.match_id"), nullable=False, index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.team_id"), nullable=False, index=True)
    team_name: Mapped[str] = mapped_column(String(100))
    formation: Mapped[Optional[str]] = mapped_column(String(20))
    startXI: Mapped[Optional[dict]] = mapped_column(JSONB)
    substitutes: Mapped[Optional[dict]] = mapped_column(JSONB)
    coach_id: Mapped[Optional[int]] = mapped_column(Integer)
    coach_name: Mapped[Optional[str]] = mapped_column(String(100))
    coach_photo: Mapped[Optional[str]] = mapped_column(String(200))
    team_colors: Mapped[Optional[dict]] = mapped_column(JSONB)


    match: Mapped["Match"] = relationship(back_populates="lineups", lazy="noload")
    team: Mapped["Team"] = relationship(back_populates="lineups", lazy="noload")

    def __repr__(self):
        return f"<MatchLineup(id={self.id}, team={self.team_name})>"