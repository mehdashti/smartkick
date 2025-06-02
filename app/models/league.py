# app/models/league.py
from __future__ import annotations
from datetime import date, datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Boolean, Date, DateTime, ForeignKey, func, UniqueConstraint
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.country import Country
    from app.models.player_season_stats import PlayerSeasonStats  
    from app.models.match import Match
    from app.models.injury import Injury


class League(Base):
    __tablename__ = 'leagues'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    league_id: Mapped[int] = mapped_column(Integer, nullable=False)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    country_id: Mapped[int] = mapped_column(ForeignKey('countries.country_id'), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    logo_url: Mapped[Optional[str]] = mapped_column(String(255))
    
    # فیلدهای boolean
    has_standings: Mapped[bool] = mapped_column(Boolean, default=False)
    has_players: Mapped[bool] = mapped_column(Boolean, default=False)
    has_top_scorers: Mapped[bool] = mapped_column(Boolean, default=False)
    has_top_assists: Mapped[bool] = mapped_column(Boolean, default=False)
    has_top_cards: Mapped[bool] = mapped_column(Boolean, default=False)
    has_injuries: Mapped[bool] = mapped_column(Boolean, default=False)
    has_predictions: Mapped[bool] = mapped_column(Boolean, default=False)
    has_odds: Mapped[bool] = mapped_column(Boolean, default=False)
    has_events: Mapped[bool] = mapped_column(Boolean, default=False)
    has_lineups: Mapped[bool] = mapped_column(Boolean, default=False)
    has_fixture_stats: Mapped[bool] = mapped_column(Boolean, default=False)
    has_player_stats: Mapped[bool] = mapped_column(Boolean, default=False)

    # زمان‌های ایجاد و به‌روزرسانی
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
    country: Mapped["Country"] = relationship(
        back_populates="leagues",
        lazy="noload",
        foreign_keys=[country_id]
    )
    player_season_stats: Mapped[List["PlayerSeasonStats"]] = relationship(
        back_populates="league",
        lazy="noload",
        foreign_keys="[PlayerSeasonStats.league_id]"
    )
#    matches: Mapped[List["Match"]] = relationship(
#        back_populates="league",
#        lazy="noload",
#        cascade="all, delete-orphan"
#    )
   

    # محدودیت‌های جدول
    __table_args__ = (
        UniqueConstraint('league_id', 'season', name='uq_league_external_id_season'),
    )

    def __repr__(self) -> str:
        return f"<League(id={self.id}, name='{self.name}', season={self.season})>"