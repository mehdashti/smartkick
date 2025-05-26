# app/models/match_event.py
from __future__ import annotations
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, ForeignKey, DateTime, func, Text # Added Text for comments

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.match import Match
    from app.models.team import Team
    from app.models.player import Player # Assuming a Player model exists

class MatchEvent(Base):
    __tablename__ = "match_events"

    match_event_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Time of the event
    time_elapsed: Mapped[int] = mapped_column(Integer, nullable=False)
    time_extra: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Event details
    event_type: Mapped[str] = mapped_column(String(50), nullable=False) # "type" is a keyword
    event_detail: Mapped[str] = mapped_column(String(255), nullable=False) # "detail"
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Foreign Keys
    match_id: Mapped[int] = mapped_column(
        ForeignKey('matches.match_id'),
        nullable=False,
        index=True
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey('teams.team_id'),
        nullable=False, # An event is always associated with a team
        index=True
    )
    player_id: Mapped[Optional[int]] = mapped_column( # Player performing the action
        ForeignKey('players.id'), # Assuming a 'players' table
        nullable=True, # Some events might not be tied to a specific player (e.g. half-time)
        index=True
    )
    assist_player_id: Mapped[Optional[int]] = mapped_column( # Assisting player
        ForeignKey('players.id'), # Assuming a 'players' table
        nullable=True,
        index=True
    )

    # Denormalized fields (optional, but present in your JSON for quick access)
    # If you prefer fully normalized, remove these and rely on relationships
    team_name_snapshot: Mapped[Optional[str]] = mapped_column(String(100), nullable=True) # Snapshot of team name at time of event
    player_name_snapshot: Mapped[Optional[str]] = mapped_column(String(100), nullable=True) # Snapshot of player name
    assist_player_name_snapshot: Mapped[Optional[str]] = mapped_column(String(100), nullable=True) # Snapshot of assist player name


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
    match: Mapped["Match"] = relationship(
        back_populates="events", # Will need to add 'events' relationship to Match model
        lazy="noload"
    )
    team: Mapped["Team"] = relationship(
        foreign_keys=[team_id],
        lazy="noload"
        # No back_populates specified, similar to home_team/away_team in Match model
        # Team model would need a generic 'match_events' if bidirectional navigation is needed
    )
    player: Mapped[Optional["Player"]] = relationship(
        foreign_keys=[player_id],
        lazy="noload"
        # Similar to team, Player model would need 'match_events'
    )
    assist_player: Mapped[Optional["Player"]] = relationship(
        foreign_keys=[assist_player_id],
        lazy="noload"
        # Similar to team, Player model would need 'assisted_match_events' or similar
    )

    def __repr__(self) -> str:
        return (
            f"<MatchEvent(match_event_id={self.match_event_id}, match_id={self.match_id}, "
            f"time_elapsed={self.time_elapsed}, type='{self.event_type}', team_id={self.team_id})>"
        )