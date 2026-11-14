"""Unit tests for ReviewStatus enum and ReviewLog ORM model."""

from app.models import LiteratureReview, ReviewLog, ReviewStatus
from sqlalchemy import inspect


def test_review_status_enum_values():
    """Verify all 12 literature review lifecycle statuses."""

    expected_statuses = [
        "pending",
        "query_expansion",
        "paper_discovery",
        "screening",
        "awaiting_user_input",
        "pdf_extraction",
        "vector_embedding",
        "gap_analysis",
        "citation_verification",
        "report_synthesis",
        "completed",
        "failed",
    ]

    actual_statuses = [status.value for status in ReviewStatus]

    assert actual_statuses == expected_statuses
    assert len(ReviewStatus) == 12


def test_review_log_instantiation():
    """Verify ReviewLog model fields and their values."""

    log = ReviewLog(
        review_id=1,
        agent_name="PaperDiscoveryAgent",
        message="Successfully discovered research papers",
        status=ReviewStatus.PAPER_DISCOVERY.value,
        payload={"papers_found": 10},
    )

    assert log.review_id == 1
    assert log.agent_name == "PaperDiscoveryAgent"
    assert log.message == "Successfully discovered research papers"
    assert log.status == "paper_discovery"
    assert log.payload == {"papers_found": 10}


def test_review_logs_relationship():
    """Verify relationship between LiteratureReview and ReviewLog."""

    review_relationship = inspect(LiteratureReview).relationships["review_logs"]
    log_relationship = inspect(ReviewLog).relationships["review"]

    assert review_relationship.back_populates == "review"
    assert log_relationship.back_populates == "review_logs"
    assert review_relationship.uselist is True
