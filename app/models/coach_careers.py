# app/models/coach_careers.py
from __future__ import annotations
from datetime import date, datetime
from typing import Optional, List, TYPE_CHECKING, Dict, Any
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Boolean, Date, DateTime, ForeignKey, func, JSON, Index, UniqueConstraint
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.team import Team
    from app.models.coach import Coach    

class CoachCareers(Base):
    __tablename__ = 'coaches_careers'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    coach_id: Mapped[int] = mapped_column(ForeignKey("coaches.id"), nullable=False, index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.team_id"), nullable=False, index=True)
    team_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    coach: Mapped["Coach"] = relationship(back_populates="careers", lazy="noload")
    team: Mapped["Team"] = relationship(back_populates="coach_careers", lazy="noload")

    __table_args__ = (
        UniqueConstraint('coach_id', 'team_id', 'start_date', name='uq_coach_team_start_career'),
        Index('ix_coach_career_query', 'coach_id', 'team_id')
    )

    def __repr__(self) -> str:
        return f"<carrer_id={self.id}, coach_id(external_id={self.coach_id}, team_id='{self.team_id}'')>"

