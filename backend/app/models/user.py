"""User account ORM model placeholder.

Assignee Task (Issue BE-03):
- Define columns: id (Integer primary key), email (String unique index), hashed_password (String), created_at (DateTime).
"""

from app.db.base import Base


# TODO (Assignee - Database Engineer): Define User model columns for authentication & ownership
class User(Base):
    """User table model placeholder."""

    __tablename__ = "users"
