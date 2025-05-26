# app/models/timezone.py
from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, DateTime, func
from app.core.database import Base
from typing import Optional

class Timezone(Base):
    __tablename__ = "timezones"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True
    )
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="IANA timezone name (e.g., 'America/New_York')"
    )
    offset: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="UTC offset in minutes"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Timezone(id={self.id}, name='{self.name}', offset={self.offset})>"