# ثبت تسک‌ها در Celery
from .player_tasks import *  # ایمپورت تمام تسک‌های مربوط به بازیکنان
from .team_tasks import *  # ثبت تسک‌های مربوط به تیم‌ها
from .venue_tasks import *  # ثبت تسک‌های مربوط به ورزشگاه‌ها
from .country_tasks import *  # ثبت تسک‌های مربوط به کشور‌ها
from .timezone_tasks import *  
from .league_tasks import *  # ثبت تسک‌های مربوط به لیگ‌ها 
from .player_stats_tasks import *  # ثبت تسک‌های مربوط به آمار بازیکنان
from .fixture_tasks import *  # ثبت تسک‌های مربوط به مسابقات