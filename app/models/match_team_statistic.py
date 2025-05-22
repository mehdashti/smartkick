# app/models/match_team_statistic.py
from datetime import datetime
from typing import Optional, Any, Dict, List, TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, ForeignKey, DateTime, func, JSON, Float # Float اضافه شد
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.match import Match
    from app.models.team import Team

class MatchTeamStatistic(Base):
    __tablename__ = "match_team_statistics"

    # کلید اصلی ترکیبی یا یک id جداگانه
    # استفاده از id جداگانه معمولاً ساده‌تر است
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # کلیدهای خارجی
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.match_id"), nullable=False, index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.team_id"), nullable=False, index=True)

    # برخی آمارهای رایج به عنوان ستون‌های اختصاصی
    # مقادیر Nullable هستند چون ممکن است API برای برخی آمارها null برگرداند
    shots_on_goal: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    shots_off_goal: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_shots: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    blocked_shots: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    shots_insidebox: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    shots_outsidebox: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fouls: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    corner_kicks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    offsides: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ball_possession: Mapped[Optional[str]] = mapped_column(String(10), nullable=True) # e.g., "32%"
    yellow_cards: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    red_cards: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    goalkeeper_saves: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_passes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    passes_accurate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    passes_percentage: Mapped[Optional[str]] = mapped_column(String(10), nullable=True) # e.g., "50%" or null

    # ستون JSON برای ذخیره کل آرایه "statistics" به صورت خام یا پردازش شده
    # این ستون انعطاف‌پذیری را برای آمارهایی که ستون اختصاصی ندارند یا برای بررسی‌های آتی فراهم می‌کند.
    raw_statistics: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSONB, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships (اختیاری، اما برای دسترسی آسان مفید است)
    match: Mapped["Match"] = relationship(
        # back_populates="team_statistics" # در صورت نیاز در Match اضافه شود
        lazy="noload"
    )
    team: Mapped["Team"] = relationship(
        # back_populates="match_statistics" # در صورت نیاز در Team اضافه شود
        lazy="noload"
    )

    # برای جلوگیری از رکوردهای تکراری برای یک تیم در یک مسابقه
    # می‌توانید یک UniqueConstraint تعریف کنید (اگر از id جداگانه به عنوان PK استفاده می‌کنید)
    from sqlalchemy import UniqueConstraint
    __table_args__ = (
        UniqueConstraint('match_id', 'team_id', name='uq_match_team_statistic'),
    )

    def __repr__(self) -> str:
        return f"<MatchTeamStatistic(match_id={self.match_id}, team_id={self.team_id})>"