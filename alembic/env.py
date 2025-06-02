# alembic/env.py
import sys
import os
import asyncio # <--- اضافه شد

# اضافه کردن پوشه ریشه پروژه به مسیر پایتون
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine # <--- اضافه شد

from alembic import context

from app.core.database import Base
# --- ایمپورت مدل‌ها (حتما قبل از target_metadata باشند) ---
import app.models.timezone
import app.models.country
import app.models.league
import app.models.team
import app.models.venue
import app.models.player
import app.models.player_season_stats
import app.models.match
import app.models.match_lineup
import app.models.match_event
import app.models.match_team_statistic
import app.models.player_fixture_stats
import app.models.coach
import app.models.coach_careers
import app.models.injury
import app.models.user # مدل User را هم اضافه کنیم اگر وجود دارد
# -------------------------------------------------------

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- target_metadata برای autogenerate ---
print("DEBUG: Tables registered in Base.metadata:", Base.metadata.tables.keys())
target_metadata = Base.metadata
# ----------------------------------------

# --- تابع برای خواندن URL فقط از متغیر محیطی ---
def get_url():
    """Reads database URL strictly from the environment variable."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
         raise ValueError("DATABASE_URL environment variable not set or not accessible!")

    # --- حالا URL اصلی async را برمی‌گردانیم ---
    print(f"DEBUG: Alembic using URL from env: {db_url}")
    return db_url
    # ------------------------------------------

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url() # <--- استفاده از URL اصلی (ممکن است async باشد)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# --- تابع کمکی برای اجرای پیکربندی و migration های Alembic ---
def do_run_migrations(connection):
    """Helper function to configure and run Alembic context."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True, # مثال: فعال کردن مقایسه نوع ستون‌ها
        # include_schemas=True # در صورت نیاز به کار با schema های مختلف
    )

    with context.begin_transaction():
        context.run_migrations()
# ----------------------------------------------------------

# --- تابع async برای اجرای migration ها در حالت آنلاین ---
async def run_migrations_async() -> None:
    """Create an async engine and run migrations using run_sync."""
    connectable = create_async_engine(
        get_url(), # <--- استفاده از URL اصلی async
        poolclass=pool.NullPool, # توصیه شده برای migrations
    )

    async with connectable.connect() as connection:
        # اجرای تابع همزمان do_run_migrations در بستر اتصال async
        await connection.run_sync(do_run_migrations)

    # مهم: منابع موتور را آزاد کنید
    await connectable.dispose()
# -----------------------------------------------------

def run_migrations_online() -> None:
    """Run migrations in 'online' mode using async engine."""
    try:
        # اجرای تابع async اصلی با استفاده از asyncio.run()
        asyncio.run(run_migrations_async())
    except Exception as e:
        print(f"Error during async migration: {e}")
        raise # خطا را دوباره نمایش بده تا Alembic متوجه شکست شود
# -----------------------------------------------------

if context.is_offline_mode():
    print("Running migrations in offline mode...")
    run_migrations_offline()
else:
    print("Running migrations in online mode (async)...")
    run_migrations_online()