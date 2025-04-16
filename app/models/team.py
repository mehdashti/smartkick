# app/models/team.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, func, UniqueConstraint, Index
from sqlalchemy.orm import relationship, declared_attr  
from app.core.database import Base

class Team(Base):
    __tablename__ = "teams"

    team_id = Column(Integer, primary_key=True, index=True)
    external_id = Column(Integer, unique=True, nullable=False, index=True, comment="Team ID from API-Football")
    name = Column(String(100), nullable=False, index=True, comment="Team name")
    code = Column(String(10), nullable=True, comment="Team code (e.g., 3-letter code)")
    # سال تاسیس می تواند عدد صحیح باشد
    founded = Column(Integer, nullable=True, comment="Year the team was founded")
    is_national = Column(Boolean, default=False, nullable=False, index=True, comment="True if it's a national team")
    logo_url = Column(String(255), nullable=True, comment="URL of the team logo")

    # --- کلیدهای خارجی ---
    country_id = Column(Integer, ForeignKey('countries.country_id'), nullable=False, index=True)
    venue_id = Column(Integer, ForeignKey('venues.venue_id'), nullable=True, index=True) # ورزشگاه می‌تواند Null باشد

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # --- رابطه چند-به-یک با کشور با استفاده از declared_attr ---
    @declared_attr
    def country(cls):
        # back_populates باید با نام رابطه در مدل Country مطابقت داشته باشد
        return relationship("Country", back_populates="teams", lazy="selectin")

    # --- رابطه چند-به-یک با ورزشگاه با استفاده از declared_attr ---
    @declared_attr
    def venue(cls):
        # back_populates باید با نام رابطه در مدل Venue مطابقت داشته باشد
        return relationship("Venue", back_populates="teams", lazy="selectin")

    def __repr__(self):
        return f"<Team(team_id={self.team_id}, name='{self.name}', external_id={self.external_id})>"