"""SQLAlchemy declarative base for all ORM models."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base.

    All ORM model classes should inherit from this so Alembic can discover
    them via ``Base.metadata``.
    """

    pass
