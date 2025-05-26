# app/models/match_lineup.py
from __future__ import annotations
from datetime import datetime
from sqlalchemy import Integer, String, Boolean, ForeignKey, DateTime, func, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.team import Team
    from app.models.match import Match 

class MatchLineup(Base):
    __tablename__ = "match_lineups"
    __table_args__ = (UniqueConstraint('match_id', 'team_id', name='uq_match_lineup_match_team'),)

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

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
    match: Mapped["Match"] = relationship(back_populates="lineups", lazy="noload")
    team: Mapped["Team"] = relationship(back_populates="lineups", lazy="noload")

    def __repr__(self):
        return f"<MatchLineup(id={self.id}, team={self.team_name})>"