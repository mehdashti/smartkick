# app/models/team.py
from sqlalchemy import Column, Integer, String, Boolean, JSON # انواع داده لازم
from app.core.database import Base # وارد کردن Base مشترک

class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True) # ID تیم از API-Football
    name = Column(String, index=True, nullable=False)
    code = Column(String, nullable=True, index=True) # کد سه حرفی (e.g., MUN)
    country = Column(String, nullable=True)
    founded = Column(Integer, nullable=True)
    national = Column(Boolean, default=False)
    logo = Column(String, nullable=True) # URL لوگو

    # می توانید فیلدهای venue و ... را هم اضافه کنید
    # venue_info = Column(JSON, nullable=True) # برای ذخیره اطلاعات ورزشگاه به صورت JSON