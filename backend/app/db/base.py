"""Declarative base class for ORM models.

Assignee Task (Issue BE-02):
- Define Base class inheriting from DeclarativeBase.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base class for all SQLAlchemy ORM models."""

    pass
