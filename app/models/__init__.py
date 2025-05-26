# app/models/__init__.py

# ایمپورت Base اگر در فایل جداگانه ای است یا تعریف آن همینجاست
from app.core.database import Base # یا from .base import Base

# ایمپورت تمام مدل های تعریف شده شما
from .timezone import Timezone
from .country import Country
from .league import League   
from .token import Token
from .user import User
from .venue import Venue
from .player import Player
from .player_season_stats import PlayerSeasonStats
from .team import Team 
from .match import Match
from .match_lineup import MatchLineup
from .match_event import MatchEvent
from .match_team_statistic import MatchTeamStatistic
from .player_fixture_stats import PlayerFixtureStats

    # <--- مثال: سایر مدل ها
#from .player import Player   # <--- مثال: سایر مدل ها
# ... و غیره برای تمام مدل های دیگر

# می توانید __all__ را هم تعریف کنید (اختیاری)
# __all__ = ["Base", "Timezone", "Country", "League", "Team", "Player"]