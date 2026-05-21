"""
Shared SQLAlchemy declarative base and timestamp mixin for production models.

All models in `src/models/` inherit from `Base`.
The `TimestampMixin` automatically manages `created_at` and `updated_at`.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class TimestampMixin:
    """Adds created_at / updated_at columns to any model."""

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
    )
