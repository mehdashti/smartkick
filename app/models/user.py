# app/models/user.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, Index, JSON
from sqlalchemy.orm import relationship # اگر نیاز به روابط دارید
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False, comment="Unique username for login")
    email = Column(String(255), unique=True, index=True, nullable=False, comment="Unique email address")
    hashed_password = Column(String(255), nullable=False, comment="Hashed password")
    full_name = Column(String(150), nullable=True, comment="User's full name")
    avatar_url = Column(String(255), nullable=True, comment="URL to user's profile picture")
    role = Column(String(50), default="user", nullable=False, index=True, comment="User role (e.g., 'user', 'admin', 'moderator')")
    is_active = Column(Boolean, default=True, nullable=False, index=True, comment="Designates whether this user account is active")
    is_verified = Column(Boolean, default=False, nullable=False, comment="Designates whether the user has verified their email")
    preferences = Column(JSON, nullable=True, comment="User-specific settings or preferences (e.g., favorite teams)")
    last_login_at = Column(DateTime(timezone=True), nullable=True, comment="Timestamp of the last successful login")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # --- ایندکس‌های اضافی (اختیاری ولی مفید) ---
    # Index('ix_users_email', 'email', unique=True) # در تعریف ستون هم unique=True گذاشتیم
    # Index('ix_users_username', 'username', unique=True)

    # --- روابط (اگر نیاز دارید) ---
    # مثلاً اگر کاربر بتواند تیم های مورد علاقه داشته باشد
    # favorite_teams = relationship("Team", secondary="user_favorite_teams", back_populates="favorited_by_users")

    def __repr__(self):
        return f"<User(user_id={self.user_id}, username='{self.username}', role='{self.role}')>"