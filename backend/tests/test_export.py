"""Unit and integration tests for PDF export service and endpoint.

Assignee Task (Issue #115 / Issue BE-11):
- Test PDF generation produces valid %PDF- bytes.
- Test export endpoint returns 404 for nonexistent review.
- Test export endpoint returns 400 for incomplete review.
- Test mock S3 upload and presigned URL redirect.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.db.session import get_db
from app.main import app
from app.models.review import LiteratureReview
from app.services.export_service import compile_literature_review_pdf
from fastapi.testclient import TestClient


SAMPLE_SYNTHESIZED_REVIEW = {
    "title": "A Survey on Multi-Agent Systems for Academic Research",
    "executive_summary": "This literature review examines recent advances in multi-agent AI.",
    "thematic_clusters": [
        {
            "theme": "Agent Orchestration Frameworks",
            "summary": "Research on LangGraph and similar orchestration tools.",
            "citations": ["Smith et al. (2024)", "Jones et al. (2023)"],
        },
    ],
    "methodology_matrix": [
        {
            "method_name": "Transformer-based RAG",
            "papers_used": ["Paper A", "Paper B"],
            "strengths": ["High accuracy", "Scalable"],
            "limitations": ["High compute cost"],
        },
    ],
    "research_gaps": [
        "Limited evaluation of hallucination guardrails in multi-agent pipelines.",
        "No standardized benchmark for citation verification agents.",
    ],
    "conclusion": "Multi-agent systems show significant promise for automating literature reviews.",
    "references": [
        {
            "title": "LangGraph: Stateful Multi-Agent Orchestration",
            "authors": ["A. Smith", "B. Chen"],
            "year": 2024,
            "url": "https://arxiv.org/abs/2401.00001",
            "matched_passage": "We propose a graph-based agent orchestration framework.",
        },
        {
            "title": "Citation Verification via Passage Retrieval",
            "authors": ["C. Jones"],
            "year": 2023,
            "url": "https://arxiv.org/abs/2312.99999",
        },
    ],
}


class TestPdfGeneration:
    """Tests for compile_literature_review_pdf()."""

    def test_pdf_generation_produces_valid_bytes(self):
        """Compiled PDF must start with the %PDF- magic bytes."""
        pdf_bytes = compile_literature_review_pdf(
            synthesized_review=SAMPLE_SYNTHESIZED_REVIEW,
            review_id=42,
            user_query="Multi-agent AI systems",
            created_at=datetime(2024, 6, 15, tzinfo=timezone.utc),
        )
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:5] == b"%PDF-"
        assert len(pdf_bytes) > 500  # Non-trivial document size

    def test_pdf_generation_with_minimal_data(self):
        """PDF generation should handle empty/missing optional sections gracefully."""
        minimal_review = {"title": "Minimal Review"}
        pdf_bytes = compile_literature_review_pdf(
            synthesized_review=minimal_review,
            review_id=1,
        )
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:5] == b"%PDF-"

    def test_pdf_generation_with_empty_review(self):
        """PDF generation should succeed even with a completely empty dict."""
        pdf_bytes = compile_literature_review_pdf(
            synthesized_review={},
            review_id=99,
        )
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:5] == b"%PDF-"


def _make_mock_review(
    review_id=1,
    status="completed",
    synthesized_review=None,
    user_query="Test query",
):
    """Create a mock LiteratureReview-like object."""
    review = MagicMock(spec=LiteratureReview)
    review.id = review_id
    review.status = status
    review.user_query = user_query
    review.synthesized_review = (
        synthesized_review if synthesized_review is not None else SAMPLE_SYNTHESIZED_REVIEW
    )
    review.created_at = datetime(2024, 6, 15, tzinfo=timezone.utc)
    return review


class TestExportEndpoint:
    """Tests for GET /{review_id}/export."""

    @pytest.fixture()
    def client(self):
        """Provide a TestClient with a mocked DB session."""

        async def override_get_db():
            mock_session = AsyncMock()
            mock_session.get = AsyncMock(return_value=None)
            yield mock_session

        app.dependency_overrides[get_db] = override_get_db
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client
        app.dependency_overrides.clear()

    def test_export_endpoint_404_nonexistent_review(self, client: TestClient):
        """GET /api/v1/reviews/999999/export returns 404 for missing review."""
        response = client.get("/api/v1/reviews/999999/export", follow_redirects=False)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_export_endpoint_404_non_numeric_id(self, client: TestClient):
        """GET /api/v1/reviews/abc/export returns 404 for non-numeric ID."""
        response = client.get("/api/v1/reviews/abc/export", follow_redirects=False)
        assert response.status_code == 404

    def test_export_endpoint_400_incomplete_review(self):
        """GET /api/v1/reviews/{id}/export returns 400 when review is not completed."""
        incomplete_review = _make_mock_review(
            review_id=10, status="screening", synthesized_review=None
        )

        async def override_get_db():
            mock_session = AsyncMock()
            mock_session.get = AsyncMock(return_value=incomplete_review)
            yield mock_session

        app.dependency_overrides[get_db] = override_get_db
        try:
            with TestClient(app, raise_server_exceptions=False) as test_client:
                response = test_client.get(
                    "/api/v1/reviews/10/export", follow_redirects=False
                )
            assert response.status_code == 400
            assert "not yet completed" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    @patch("app.api.v1.reviews.generate_presigned_download_url")
    @patch("app.api.v1.reviews.upload_report_pdf_to_s3", new_callable=AsyncMock)
    @patch("app.api.v1.reviews.check_report_pdf_exists_in_s3", new_callable=AsyncMock)
    @patch("app.api.v1.reviews.compile_literature_review_pdf")
    def test_mock_s3_upload_and_presigned_redirect(
        self,
        mock_compile: MagicMock,
        mock_s3_exists: AsyncMock,
        mock_s3_upload: AsyncMock,
        mock_presigned: MagicMock,
    ):
        """Full flow: compile PDF, upload to S3, redirect to presigned URL."""
        completed_review = _make_mock_review(review_id=5, status="completed")

        mock_s3_exists.return_value = False
        mock_compile.return_value = b"%PDF-1.4 fake pdf bytes"
        mock_s3_upload.return_value = "exports/literature_review_5.pdf"
        mock_presigned.return_value = "https://s3.amazonaws.com/bucket/exports/literature_review_5.pdf?signed=1"

        async def override_get_db():
            mock_session = AsyncMock()
            mock_session.get = AsyncMock(return_value=completed_review)
            yield mock_session

        app.dependency_overrides[get_db] = override_get_db
        try:
            with TestClient(app, raise_server_exceptions=False) as test_client:
                response = test_client.get(
                    "/api/v1/reviews/5/export", follow_redirects=False
                )
            assert response.status_code == 302
            assert "s3.amazonaws.com" in response.headers["location"]

            mock_compile.assert_called_once()
            mock_s3_upload.assert_awaited_once()
            mock_presigned.assert_called_once_with("exports/literature_review_5.pdf")
        finally:
            app.dependency_overrides.clear()

    @patch("app.api.v1.reviews.generate_presigned_download_url")
    @patch("app.api.v1.reviews.check_report_pdf_exists_in_s3", new_callable=AsyncMock)
    def test_s3_cache_hit_skips_compilation(
        self,
        mock_s3_exists: AsyncMock,
        mock_presigned: MagicMock,
    ):
        """When PDF already exists in S3, skip compilation and redirect directly."""
        completed_review = _make_mock_review(review_id=7, status="completed")

        mock_s3_exists.return_value = True
        mock_presigned.return_value = "https://s3.amazonaws.com/bucket/exports/literature_review_7.pdf?signed=1"

        async def override_get_db():
            mock_session = AsyncMock()
            mock_session.get = AsyncMock(return_value=completed_review)
            yield mock_session

        app.dependency_overrides[get_db] = override_get_db
        try:
            with TestClient(app, raise_server_exceptions=False) as test_client:
                with patch(
                    "app.api.v1.reviews.compile_literature_review_pdf"
                ) as mock_compile:
                    response = test_client.get(
                        "/api/v1/reviews/7/export", follow_redirects=False
                    )
                    mock_compile.assert_not_called()
            assert response.status_code == 302
        finally:
            app.dependency_overrides.clear()

