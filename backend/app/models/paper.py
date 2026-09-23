"""Academic paper metadata and vector embedding ORM model placeholder.

Assignee Task (Issue BE-03):
- Define columns: id (Integer primary key), title (String), authors (String/JSON), abstract (Text), published_year (Integer), arxiv_id (String), relevance_score (Float), is_approved (Boolean), review_id (ForeignKey to literature_reviews.id).
"""

from app.db.base import Base


# TODO (Assignee - Database Engineer): Define Paper model columns (relevance_score, is_approved) & ForeignKey to literature_reviews
class Paper(Base):
    """Paper table model placeholder."""

    __tablename__ = "papers"
