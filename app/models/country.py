# app/models/countries.py
from __future__ import annotations
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.team import Team
    from app.models.league import League
    from app.models.venue import Venue  

class Country(Base):
    __tablename__ = 'countries'

    country_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    code: Mapped[Optional[str]] = mapped_column(String(10), index=True)
    flag_url: Mapped[Optional[str]] = mapped_column(String(255))
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # روابط
    leagues: Mapped[List["League"]] = relationship(
        back_populates="country",
        lazy="noload",
        foreign_keys="[League.country_id]"
    )

    def __repr__(self) -> str:
        return f"<Country(country_id={self.country_id}, name='{self.name}', code='{self.code}')>"