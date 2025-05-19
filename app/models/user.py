# app/models/user.py
from datetime import datetime
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Boolean, DateTime, JSON, func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique username for login"
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="User's email address"
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Bcrypt hashed password"
    )
    full_name: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
        comment="User's full name"
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="URL to user's avatar image"
    )
    role: Mapped[str] = mapped_column(
        String(50),
        default="user",
        nullable=False,
        index=True,
        comment="User role (user|moderator|admin)"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Account active status"
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Email verification status"
    )
    preferences: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="User preferences JSON"
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last login timestamp"
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
        return f"<User(user_id={self.user_id}, username='{self.username}', role='{self.role}')>"