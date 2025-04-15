# app/models/countries.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship, declared_attr
from sqlalchemy.sql import func
from app.core.database import Base


class Country(Base):
    __tablename__ = 'countries'
    
    country_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    code = Column(String(10), nullable=False, unique=True)
    flag_url = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # رابطه با استفاده از async_attrs
    @declared_attr
    def leagues(cls):
        return relationship("League", back_populates="country", lazy="selectin")