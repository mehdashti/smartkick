# app/models/venue.py
from sqlalchemy import Column, Integer, String, Float, UniqueConstraint, Index, DateTime, func
from sqlalchemy.orm import relationship, declared_attr
from app.core.database import Base

class Venue(Base):
    __tablename__ = "venues"

    venue_id = Column(Integer, primary_key=True, index=True)
    external_id = Column(Integer, unique=True, nullable=False, index=True, comment="Venue ID from API-Football")
    name = Column(String(150), nullable=True, index=True, comment="Venue name")
    address = Column(String(255), nullable=True, comment="Venue address")
    city = Column(String(100), nullable=True, index=True, comment="City where the venue is located")
    # ظرفیت می‌تواند بزرگ باشد، اما Integer معمولاً کافی است
    capacity = Column(Integer, nullable=True, comment="Venue capacity")
    surface = Column(String(50), nullable=True, comment="Playing surface (e.g., grass, artificial)")
    image_url = Column(String(255), nullable=True, comment="URL of the venue image")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # --- رابطه یک-به-چند با تیم‌ها ---
    # یک ورزشگاه می‌تواند میزبان چند تیم باشد (هرچند در API فعلی اینطور نیست)
    @declared_attr
    def teams(cls):
        # back_populates باید با نام رابطه در مدل Team مطابقت داشته باشد
        return relationship("Team", back_populates="venue", lazy="selectin")

    # --- محدودیت‌ها ---
    # UniqueConstraint در تعریف ستون external_id اعمال شد

    def __repr__(self):
        return f"<Venue(venue_id={self.venue_id}, name='{self.name}', external_id={self.external_id})>"