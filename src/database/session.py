"""
Session management for the production database.

Provides:
  * `get_session_factory()` – returns a cached sessionmaker bound to the engine
  * `SessionLocal`          – convenience alias (property-like getter)
  * `get_db()`              – FastAPI dependency (yields a session)
  * `db_session()`          – context manager for scripts / services

Sessions are created lazily so importing this module never opens a database
connection.  The engine (and psycopg2 driver) are only loaded on first use.
"""

from contextlib import contextmanager
from functools import lru_cache
from typing import Generator

from sqlalchemy.orm import Session, sessionmaker


@lru_cache(maxsize=1)
def _get_session_factory() -> sessionmaker:
    """Return a cached session factory.  Engine is initialised on first call."""
    from src.database.postgres import get_engine

    return sessionmaker(
        bind=get_engine(),
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


def SessionLocal() -> Session:  # type: ignore[override]
    """Create and return a new database Session."""
    return _get_session_factory()()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.

    Usage::

        @app.get("/items")
        def list_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = _get_session_factory()()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """
    Context manager for use outside FastAPI (scripts, services, tests).

    Usage::

        with db_session() as db:
            db.add(obj)
            db.commit()
    """
    db = _get_session_factory()()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
