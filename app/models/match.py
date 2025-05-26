# app/models/match.py
from __future__ import annotations
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING, Dict, Any
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Boolean, ForeignKey, DateTime, func, JSON
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.team import Team
    from app.models.venue import Venue
    from app.models.league import League
    from app.models.match_lineup import MatchLineup
    from app.models.match_event import MatchEvent
    from app.models.player_fixture_stats import PlayerFixtureStats

class Match(Base):
    __tablename__ = "matches"

    match_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    referee: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timestamp: Mapped[int] = mapped_column(Integer, nullable=False)
    periods_first: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    periods_second: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status_long: Mapped[str] = mapped_column(String(50), nullable=False)
    status_short: Mapped[str] = mapped_column(String(10), nullable=False)
    status_elapsed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status_extra: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    goals_home: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    goals_away: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score_halftime_home: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score_halftime_away: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score_fulltime_home: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score_fulltime_away: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score_extratime_home: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score_extratime_away: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score_penalty_home: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score_penalty_away: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    winner_home: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    winner_away: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    round: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Foreign Keys
    venue_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey('venues.venue_id'),
        nullable=True,
        index=True
    )
    league_id: Mapped[int] = mapped_column(Integer, nullable=False)
    season: Mapped[int] = mapped_column(Integer, nullable=False)

    home_team_id: Mapped[int] = mapped_column(
        ForeignKey('teams.team_id'),
        nullable=False,
        index=True
    )
    away_team_id: Mapped[int] = mapped_column(
        ForeignKey('teams.team_id'),
        nullable=False,
        index=True
    )

    # JSONB Columns
    events_json: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSONB, nullable=True, default=list)
    lineups_json: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSONB, nullable=True, default=list)
    team_stats_json: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSONB, nullable=True, default=list) 
    player_stats_json: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSONB, nullable=True, default=list)

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

    # Relationships
    venue: Mapped[Optional["Venue"]] = relationship(
        back_populates="matches",
        lazy="noload"
    )
#    league: Mapped["League"] = relationship(
#        back_populates="matches",
#        lazy="noload"
#    )
    home_team: Mapped["Team"] = relationship(
        foreign_keys=[home_team_id],
        lazy="noload"
    )
    away_team: Mapped["Team"] = relationship(
        foreign_keys=[away_team_id],
        lazy="noload"
    )
    lineups: Mapped[List["MatchLineup"]] = relationship(
        back_populates="match", 
        lazy="noload"
    )
    events: Mapped[List["MatchEvent"]] = relationship(
        back_populates="match",
        lazy="noload",
        cascade="all, delete-orphan" # Optional: if a Match is deleted, delete its events
    )
    player_stats: Mapped[List[PlayerFixtureStats]] = relationship(
        back_populates="match", 
        cascade="all, delete-orphan",
        lazy="noload" 
    )    

    def __repr__(self) -> str:
        return f"<Match(match_id={self.match_id}, home={self.home_team_id}, away={self.away_team_id}, date='{self.date}')>"