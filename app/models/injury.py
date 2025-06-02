# app/models/injury.py
from __future__ import annotations
from datetime import date, datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Boolean, Date, DateTime, ForeignKey, func, JSON, UniqueConstraint, Index
from sqlalchemy import Index
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.player import Player
    from app.models.team import Team
    from app.models.match import Match
    from app.models.league import League


class Injury(Base):
    __tablename__ = 'injuries'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False, index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.team_id"), nullable=False, index=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.match_id"), nullable=False, index=True)
    league_id: Mapped[int] = mapped_column(Integer, nullable=True)
    season: Mapped[int] = mapped_column(Integer, nullable=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    player: Mapped["Player"] = relationship(back_populates="injuries", lazy="noload")
    team: Mapped["Team"] = relationship(back_populates="injuries", lazy="noload")
    match: Mapped["Match"] = relationship(back_populates="injuries", lazy="noload")

    __table_args__ = (
        UniqueConstraint('player_id', 'match_id', name='uq_player_match'),
        Index('ix_injury_query', 'player_id', 'match_id')
    )

    def __repr__(self) -> str:
        return f"<Player(external_id={self.player_id})>"

