"""
Alembic migration environment.

* Reads the database URL from `settings.database_url` (falls back to
  `settings.sql_database_url`) so the same .env file used by the app
  controls migrations.
* Imports ALL model metadata so autogenerate detects every table.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ---------------------------------------------------------------------------
# Make the project root importable (alembic runs from the project directory)
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings

# ---------------------------------------------------------------------------
# Import all models so their tables appear in metadata
# ---------------------------------------------------------------------------
# Legacy sql_store models
from src.database.sql_store import Base as LegacyBase  # noqa: F401

# New production models
from src.database.base import Base as ProductionBase  # noqa: F401
import src.models  # registers ParkingType, ParkingSlot, Booking, AdminAction  # noqa: F401

# Merge metadata into a single target
# We tell Alembic about BOTH bases so it can manage all tables.
from sqlalchemy import MetaData

combined_metadata = MetaData()
for base in (LegacyBase, ProductionBase):
    for table in base.metadata.tables.values():
        table.tometadata(combined_metadata)

# ---------------------------------------------------------------------------
# Standard Alembic boilerplate
# ---------------------------------------------------------------------------
config = context.config

# Override sqlalchemy.url with value from settings
_db_url = settings.database_url or settings.sql_database_url
config.set_main_option("sqlalchemy.url", _db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = combined_metadata


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with a live DB connection (recommended)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
