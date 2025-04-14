# app/models/countries.py
from sqlalchemy import Column, Integer, String
from app.core.database import Base 

class Country(Base):
    __tablename__ = "countries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), index=True, nullable=False)
    code = Column(String(10), unique=True, nullable=True, index=True)
    flag = Column(String(255), nullable=True)
