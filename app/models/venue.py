# app/models/venue.py
from __future__ import annotations
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, DateTime, ForeignKey, func
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.country import Country
    from app.models.team import Team    
    from app.models.match import Match

class Venue(Base):
    __tablename__ = "venues"

    venue_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True, index=True, comment="Venue name")
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="Venue address")
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True, comment="City location")
    capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="Venue capacity")
    surface: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="Playing surface")
    image_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="Image URL")
    
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
    teams: Mapped[List["Team"]] = relationship(
        back_populates="venue",
        lazy="noload",
        cascade="all, delete-orphan",
        foreign_keys="[Team.venue_id]"
    )
    matches: Mapped[List["Match"]] = relationship(
        back_populates="venue",
        lazy="noload",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Venue(venue_id={self.venue_id}, name='{self.name}')>"