"""Literature review task session ORM model placeholder.

Assignee Task (Issue BE-03):
- Define columns: id (Integer/UUID primary key), user_query (String), status (String), created_at (DateTime).
"""

from app.db.base import Base


# TODO (Assignee - Database Engineer): Define LiteratureReview model columns
class LiteratureReview(Base):
    """Literature Review session model placeholder."""

    __tablename__ = "literature_reviews"
