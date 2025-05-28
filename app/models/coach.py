# app/models/coach.py
from __future__ import annotations
from datetime import date, datetime
from typing import Optional, List, TYPE_CHECKING, Dict, Any
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Boolean, Date, DateTime, ForeignKey, func, JSON, Index
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base
from app.models.coach_careers import CoachCareers

if TYPE_CHECKING:
    from app.models.team import Team


class Coach(Base):
    __tablename__ = 'coaches'

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
    photo_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    team_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teams.team_id"), nullable=True, index=True)
    career: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSONB, nullable=True, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    team: Mapped["Team"] = relationship(back_populates="coach", lazy="noload")

    careers: Mapped[List["CoachCareers"]] = relationship(
        back_populates="coach",
        lazy="noload",
        cascade="all, delete-orphan",
        foreign_keys="[CoachCareers.coach_id]"
    )



    def __repr__(self) -> str:
        return f"<Coach(external_id={self.id}, name='{self.name}')>"

