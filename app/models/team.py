# app/models/team.py
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Boolean, ForeignKey, DateTime, func
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.country import Country
    from app.models.venue import Venue
    from app.models.player_season_stats import PlayerSeasonStats  
    from app.models.match import Match
    from app.models.match_lineup import MatchLineup

class Team(Base):
    __tablename__ = "teams"

    team_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="Team name")
    code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, comment="Team code")
    founded: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="Foundation year")
    is_national: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="Logo URL")
    country: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    

    # Foreign Keys
    venue_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey('venues.venue_id'),
        nullable=True,
        index=True
    )

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
        back_populates="teams",
        lazy="noload",
        foreign_keys=[venue_id]
    )
    player_season_stats: Mapped[List["PlayerSeasonStats"]] = relationship(
        back_populates="team",
        lazy="noload",
        cascade="all, delete-orphan",
        foreign_keys="[PlayerSeasonStats.team_id]"
    )
    home_matches: Mapped[List["Match"]] = relationship(
        back_populates="home_team",
        lazy="noload",
        foreign_keys="[Match.home_team_id]"
    )
    away_matches: Mapped[List["Match"]] = relationship(
        back_populates="away_team",
        lazy="noload",
        foreign_keys="[Match.away_team_id]"
    )
    lineups: Mapped[List["MatchLineup"]] = relationship(
        back_populates="team", 
        lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Team(team_id={self.team_id}, name='{self.name}', country='{self.country}')>"