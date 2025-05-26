# app/models/player_fixture_stats.py
from __future__ import annotations # برای type hint های رو به جلو در روابط

from typing import TYPE_CHECKING, Optional, List
from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint, Index, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.player import Player
    from app.models.match import Match
    from app.models.team import Team

class PlayerFixtureStats(Base):
    __tablename__ = 'player_fixture_stats'

    stat_id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Foreign Keys
    player_id: Mapped[int] = mapped_column(ForeignKey('players.id'), index=True)
    match_id: Mapped[int] = mapped_column(ForeignKey('matches.match_id'), index=True) 
    team_id: Mapped[int] = mapped_column(ForeignKey('teams.team_id'), index=True) 

    # Games stats
    minutes_played: Mapped[Optional[int]]
    player_number: Mapped[Optional[int]]
    position: Mapped[Optional[str]] = mapped_column(String(50))
    rating: Mapped[Optional[float]]
    captain: Mapped[Optional[bool]] = mapped_column(default=False)
    substitute: Mapped[Optional[bool]] = mapped_column(default=False)

    # Specific stats
    offsides: Mapped[Optional[int]]

    # Shots stats
    shots_total: Mapped[Optional[int]]
    shots_on: Mapped[Optional[int]]

    # Goals stats
    goals_total: Mapped[Optional[int]]
    goals_conceded: Mapped[Optional[int]]
    goals_assists: Mapped[Optional[int]]
    goals_saves: Mapped[Optional[int]]

    # Passes stats
    passes_total: Mapped[Optional[int]]
    passes_key: Mapped[Optional[int]]
    passes_accuracy_percentage: Mapped[Optional[int]]

    # Tackles stats
    tackles_total: Mapped[Optional[int]]
    tackles_blocks: Mapped[Optional[int]]
    tackles_interceptions: Mapped[Optional[int]]

    # Duels stats
    duels_total: Mapped[Optional[int]]
    duels_won: Mapped[Optional[int]]

    # Dribbles stats
    dribbles_attempts: Mapped[Optional[int]]
    dribbles_success: Mapped[Optional[int]]
    dribbles_past: Mapped[Optional[int]]

    # Fouls stats
    fouls_drawn: Mapped[Optional[int]]
    fouls_committed: Mapped[Optional[int]]

    # Cards stats
    cards_yellow: Mapped[Optional[int]]
    cards_red: Mapped[Optional[int]]

    # Penalty stats
    penalty_won: Mapped[Optional[int]]
    penalty_committed: Mapped[Optional[int]] # املای صحیح
    penalty_scored: Mapped[Optional[int]]
    penalty_missed: Mapped[Optional[int]]
    penalty_saved: Mapped[Optional[int]]

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    player: Mapped[Player] = relationship(back_populates="fixture_stats", lazy="noload")
    match: Mapped[Match] = relationship(back_populates="player_stats", lazy="noload") 
    team: Mapped[Team] = relationship(back_populates="player_fixture_stats", lazy="noload")

 
    __table_args__ = (
        UniqueConstraint('player_id', 'match_id', 'team_id', name='uq_player_fixture_team_stats'),
        Index('ix_player_fixture_stats_query', 'player_id', 'match_id')
    )

    def __repr__(self):
        return f"<PlayerFixtureStats(stat_id={self.stat_id}, player_id={self.player_id}, match_id={self.match_id}, team_id={self.team_id})>"