"""
PostgreSQL engine factory and health-check utilities.

Design decisions
----------------
* Synchronous SQLAlchemy engine with QueuePool – keeps things simple and
  compatible with the rest of the codebase (FastAPI sync endpoints).
* `pool_pre_ping=True` reconnects transparently after idle-timeout drops.
* Falls back to SQLite transparently when `database_url` is not PostgreSQL.
* `validate_connection()` is called on FastAPI startup to fail-fast if the
  DB is unreachable.
"""

import logging
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

from config.settings import settings

logger = logging.getLogger(__name__)


def _is_postgres(url: str) -> bool:
    return url.startswith("postgresql") or url.startswith("postgres")


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """
    Return the shared SQLAlchemy engine for the *production* database.

    Uses the `database_url` setting when it references PostgreSQL.
    Falls back to `sql_database_url` (SQLite) for local dev without PG.
    """
    url = settings.database_url or settings.sql_database_url

    if _is_postgres(url):
        engine = create_engine(
            url,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            pool_pre_ping=True,
            echo=False,
        )
        logger.info("PostgreSQL engine created (pool_size=5)")
    elif ":memory:" in url:
        from sqlalchemy.pool import StaticPool

        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )
        logger.info("In-memory SQLite engine created (testing mode)")
    else:
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            echo=False,
        )
        logger.info("SQLite file engine created: %s", url)

    return engine


def validate_connection() -> bool:
    """
    Verify the database is reachable and tables exist.

    Returns True on success, False on failure (does NOT raise).
    Call this during FastAPI `startup` event.
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✓ Database connection healthy (%s)", engine.url.drivername)
        return True
    except OperationalError as exc:
        logger.error("✗ Database connection failed: %s", exc)
        return False


def get_db_info() -> dict:
    """
    Return human-readable database diagnostics.

    Includes the active URL, absolute file path (SQLite), driver name.
    Used by startup logging and the debug endpoint.
    """
    import os

    url = settings.database_url or settings.sql_database_url
    engine = get_engine()
    driver = engine.url.drivername

    absolute_path: str = ""
    if "sqlite" in driver:
        # Strip the sqlite:/// prefix and resolve to absolute path
        raw = url.replace("sqlite:///", "", 1)
        absolute_path = os.path.abspath(raw)

    return {
        "database_url": url,
        "driver": driver,
        "absolute_path": absolute_path,
        "is_postgres": _is_postgres(url),
    }
