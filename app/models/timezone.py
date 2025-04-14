# app/models/timezone.py
from sqlalchemy import Column, Integer, String
from sqlalchemy.schema import UniqueConstraint # برای اطمینان از عدم تکرار
from app.core.database import Base # وارد کردن Base مشترک

class Timezone(Base):
    __tablename__ = "timezones"

    # یک id عددی ساده به عنوان کلید اصلی
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # نام timezone که از API می آید
    # باید منحصر به فرد باشد و نمی تواند خالی باشد
    name = Column(String(100), unique=True, index=True, nullable=False)

    # تعریف قید منحصر به فرد بودن برای ستون name (اختیاری، چون unique=True هست)
    __table_args__ = (UniqueConstraint('name', name='uq_timezone_name'),)

    def __repr__(self):
        # نمایش بهتر شی در لاگ ها یا هنگام دیباگ
        return f"<Timezone(id={self.id}, name='{self.name}')>"