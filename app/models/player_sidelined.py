# app/models/player_sidelined.py
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


class PlayerSidelined(Base):
    __tablename__ = 'player_sidelined'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    player_sidelined: Mapped["Player"] = relationship(back_populates="sidelined", lazy="noload")

    __table_args__ = (
        UniqueConstraint('player_id', 'start_date', name='uq_player_date'),
        Index('ix_injury_query', 'player_id')
    )

    def __repr__(self) -> str:
        return f"<Player(external_id={self.player_id})>"

