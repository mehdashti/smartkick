# app/models/league.py
from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship, declared_attr
from sqlalchemy.sql import func
from app.core.database import Base


class League(Base):
    __tablename__ = 'leagues'
    
    league_id = Column(Integer, primary_key=True)
    external_id = Column(Integer, nullable=False)
    season = Column(Integer, nullable=False)
    is_current = Column(Boolean, default=False, index=True)    
    name = Column(String(100), nullable=False, index=True)
    country_id = Column(Integer, ForeignKey('countries.country_id'), nullable=False)
    type = Column(String(20), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    logo_url = Column(String(255))
    has_standings = Column(Boolean, default=False)
    has_players = Column(Boolean, default=False)
    has_top_scorers = Column(Boolean, default=False)
    has_top_assists = Column(Boolean, default=False)
    has_top_cards = Column(Boolean, default=False)
    has_injuries = Column(Boolean, default=False)
    has_predictions = Column(Boolean, default=False)
    has_odds = Column(Boolean, default=False)
    has_events = Column(Boolean, default=False)
    has_lineups = Column(Boolean, default=False)
    has_fixture_stats = Column(Boolean, default=False)
    has_player_stats = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # روابط
    @declared_attr
    def country(cls):
        return relationship("Country", back_populates="leagues", lazy="selectin")
 
    __table_args__ = UniqueConstraint('external_id', 'season', name='uq_league_external_id_season'),
