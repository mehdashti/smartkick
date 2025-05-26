# app/models/player_season_stats.py
from __future__ import annotations
from sqlalchemy import (Column, Integer, String, Boolean, Float, ForeignKey,
                      DateTime, UniqueConstraint, Index)
from sqlalchemy.orm import relationship 
from sqlalchemy.sql import func
from app.core.database import Base

class PlayerSeasonStats(Base):
    __tablename__ = 'player_season_stats'

    stat_id = Column(Integer, primary_key=True)

    # Foreign Keys linking to other tables
    player_id = Column(Integer, ForeignKey('players.id'), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey('teams.team_id'), nullable=False, index=True)
    league_id = Column(Integer, ForeignKey('leagues.id'), nullable=False, index=True)
    season = Column(Integer, nullable=False, index=True)

    # Games stats
    appearences = Column(Integer, nullable=True)
    lineups = Column(Integer, nullable=True)
    minutes = Column(Integer, nullable=True)
    player_number = Column(Integer, nullable=True)
    position = Column(String(50), nullable=True)
    rating = Column(Float, nullable=True)
    captain = Column(Boolean, default=False, nullable=True)

    # Substitutes stats
    sub_in = Column(Integer, nullable=True)
    sub_out = Column(Integer, nullable=True)
    sub_bench = Column(Integer, nullable=True)

    # Shots stats
    shots_total = Column(Integer, nullable=True)
    shots_on = Column(Integer, nullable=True)

    # Goals stats
    goals_total = Column(Integer, nullable=True)
    goals_conceded = Column(Integer, nullable=True)
    goals_assists = Column(Integer, nullable=True)
    goals_saves = Column(Integer, nullable=True)

    # Passes stats
    passes_total = Column(Integer, nullable=True)
    passes_key = Column(Integer, nullable=True)
    passes_accuracy = Column(Integer, nullable=True) 

    # Tackles stats
    tackles_total = Column(Integer, nullable=True)
    tackles_blocks = Column(Integer, nullable=True)
    tackles_interceptions = Column(Integer, nullable=True)

    # Duels stats
    duels_total = Column(Integer, nullable=True)
    duels_won = Column(Integer, nullable=True)

    # Dribbles stats
    dribbles_attempts = Column(Integer, nullable=True)
    dribbles_success = Column(Integer, nullable=True)
    dribbles_past = Column(Integer, nullable=True) 

    # Fouls stats
    fouls_drawn = Column(Integer, nullable=True)
    fouls_committed = Column(Integer, nullable=True)

    # Cards stats
    cards_yellow = Column(Integer, nullable=True)
    cards_yellowred = Column(Integer, nullable=True)
    cards_red = Column(Integer, nullable=True)

    # Penalty stats
    penalty_won = Column(Integer, nullable=True)
    penalty_committed = Column(Integer, nullable=True) 
    penalty_scored = Column(Integer, nullable=True)
    penalty_missed = Column(Integer, nullable=True)
    penalty_saved = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


    player = relationship(
        "Player",
        back_populates="season_stats",
        lazy="noload",
        foreign_keys=[player_id]
    )
 
    team = relationship(
        "Team",
        back_populates="player_season_stats",
        lazy="noload",
        foreign_keys=[team_id]
    )
 
    league = relationship(
        "League",
        back_populates="player_season_stats", 
        lazy="noload",
        foreign_keys=[league_id] 
    )


    # --- آپدیت Unique Constraint و Index ---
    __table_args__ = (
        UniqueConstraint('player_id', 'team_id', 'league_id', 'season', name='uq_player_team_league_season_stats'),
        Index('ix_player_season_stats_query', 'player_id', 'league_id', 'season')
    )

    def __repr__(self):
        return f"<PlayerSeasonStats(stat_id={self.stat_id}, player_ext={self.player_id}, team_ext={self.team_id}, league_ext={self.league_id}, season={self.season})>"


