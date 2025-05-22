# app/models/player.py
from datetime import date, datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Boolean, Date, DateTime, ForeignKey, func
from sqlalchemy import Index
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.player_season_stats import PlayerSeasonStats  
    from app.models.match_event import MatchEvent

class Player(Base):
    __tablename__ = 'players'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    firstname: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    lastname: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    birth_place: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    birth_country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    nationality: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    height: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    weight: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    position: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    photo_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_injured: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    season_stats: Mapped[List["PlayerSeasonStats"]] = relationship(
        back_populates="player",
        lazy="noload",
        cascade="all, delete-orphan",
        foreign_keys="[PlayerSeasonStats.player_id]"
    )
    match_events_as_actor: Mapped[List["MatchEvent"]] = relationship(
        foreign_keys="[MatchEvent.player_id]", 
        back_populates="player",
        lazy="noload"
    )
    match_events_as_assist: Mapped[List["MatchEvent"]] = relationship(
        foreign_keys="[MatchEvent.assist_player_id]",
        back_populates="assist_player",
        lazy="noload"
    )


    def __repr__(self) -> str:
        return f"<Player(external_id={self.id}, name='{self.name}')>"

