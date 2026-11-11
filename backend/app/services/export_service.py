"""PDF report compilation service and S3 export helpers using ReportLab.

Assignee Task (Issue BE-11):
- Compile publication-grade academic literature review PDFs from synthesized_review data
- Structure PDF: Title & Metadata, Executive Summary, Thematic Clusters, Methodology Matrix, Research Gaps, References
- Upload generated PDF to AWS S3 (s3://{AWS_S3_BUCKET}/exports/literature_review_{review_id}.pdf)
- Generate presigned download URLs with Content-Disposition attachment headers
"""

import asyncio
from datetime import datetime, timezone
import html
import io
import logging
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


def _escape(text: Any) -> str:
    """Safely escape text for ReportLab XML/HTML paragraphs."""
    if text is None:
        return ""
    return html.escape(str(text))


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and render running headers and 'Page X of Y' footers."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: List[Dict[str, Any]] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int) -> None:
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Running Header (pages 2 and onward)
        if self._pageNumber > 1:
            self.drawString(
                36, 756, "Scholaris Multi-Agent Research System | Literature Review Synthesis"
            )
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(36, 750, 576, 750)

        # Running Footer (all pages)
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(36, 45, 576, 45)
        self.drawString(
            36, 32, "Confidential Academic Synthesis Report • Verified via Scholaris Pipeline"
        )
        self.drawRightString(576, 32, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def compile_literature_review_pdf(
    synthesized_review: Dict[str, Any],
    review_id: int,
    user_query: str = "",
    created_at: Optional[datetime] = None,
    corpus_paper_count: Optional[int] = None,
) -> bytes:
    """Compile structured synthesized_review JSON into a publication-grade PDF document.

    Args:
        synthesized_review: Dict containing title, executive_summary, thematic_clusters,
                            methodology_matrix, research_gaps, conclusion, references.
        review_id: ID of the literature review session.
        user_query: Research prompt / topic provided by the user.
        created_at: Review creation timestamp.
        corpus_paper_count: Number of papers evaluated in the review.

    Returns:
        Compiled PDF binary bytes starting with b"%PDF-".
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=48,
        bottomMargin=54,
    )

    printable_width = 540  # 612 - 36 - 36

    styles = getSampleStyleSheet()

    # Custom typography styles
    kicker_style = ParagraphStyle(
        "ScholarisKicker",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#4338CA"),
        textTransform="uppercase",
        spaceAfter=4,
    )

    title_style = ParagraphStyle(
        "ScholarisTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0F172A"),
        alignment=0,
        spaceAfter=10,
    )

    h1_style = ParagraphStyle(
        "ScholarisH1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "ScholarisH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#1E293B"),
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "ScholarisBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13.5,
        textColor=colors.HexColor("#334155"),
        spaceAfter=6,
    )

    meta_label = ParagraphStyle(
        "ScholarisMetaLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#64748B"),
    )

    meta_val = ParagraphStyle(
        "ScholarisMetaVal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0F172A"),
    )

    table_header_style = ParagraphStyle(
        "ScholarisTableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10.5,
        textColor=colors.white,
    )

    table_cell_style = ParagraphStyle(
        "ScholarisTableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10.5,
        textColor=colors.HexColor("#1E293B"),
    )

    table_cell_bold = ParagraphStyle(
        "ScholarisTableCellBold",
        parent=table_cell_style,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#0F172A"),
    )

    quote_style = ParagraphStyle(
        "ScholarisQuote",
        parent=styles["Italic"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#475569"),
    )

    story: List[Any] = []

    # 1. Header & Title (Page 1)
    story.append(Paragraph("SCHOLARIS MULTI-AGENT RESEARCH SYSTEM • SYNTHESIS REPORT", kicker_style))
    title_text = synthesized_review.get("title") or "Academic Literature Review Synthesis"
    story.append(Paragraph(_escape(title_text), title_style))

    # 2. Metadata Grid
    review_date = (
        created_at.strftime("%B %d, %Y")
        if created_at
        else datetime.now(timezone.utc).strftime("%B %d, %Y")
    )
    paper_count = (
        corpus_paper_count
        if corpus_paper_count is not None
        else len(synthesized_review.get("references") or [])
    )
    query_str = user_query or "Automated Literature Review Session"

    meta_data = [
        [
            Paragraph("<b>SESSION ID:</b>", meta_label),
            Paragraph(f"Review #{review_id}", meta_val),
            Paragraph("<b>DATE GENERATED:</b>", meta_label),
            Paragraph(_escape(review_date), meta_val),
        ],
        [
            Paragraph("<b>RESEARCH TOPIC:</b>", meta_label),
            Paragraph(_escape(query_str), meta_val),
            Paragraph("<b>CORPUS PAPERS:</b>", meta_label),
            Paragraph(f"{paper_count} Papers Evaluated", meta_val),
        ],
    ]

    meta_table = Table(
        meta_data,
        colWidths=[80, 200, 95, 165],
        hAlign="LEFT",
    )
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#F1F5F9")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # 3. Executive Summary (Page 1 Callout)
    story.append(Paragraph("Executive Summary", h1_style))
    exec_summary = (
        synthesized_review.get("executive_summary")
        or "Comprehensive academic literature review synthesized across screened candidate literature."
    )
    summary_paragraph = Paragraph(_escape(exec_summary), body_style)

    summary_table = Table([[summary_paragraph]], colWidths=[printable_width], hAlign="LEFT")
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("LINEBEFORE", (0, 0), (0, -1), 3.0, colors.HexColor("#4338CA")),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    story.append(summary_table)

    # 4. Page Break for Thematic Chapters
    story.append(PageBreak())

    # Section 1: Thematic Clusters
    thematic_clusters: List[Dict[str, Any]] = synthesized_review.get("thematic_clusters") or []
    if thematic_clusters:
        story.append(Paragraph("1. Thematic Synthesis & Core Findings", h1_style))
        story.append(Spacer(1, 4))

        for idx, cluster in enumerate(thematic_clusters, 1):
            theme_title = cluster.get("theme") or f"Theme {idx}"
            summary_text = cluster.get("summary") or ""
            citations: List[str] = cluster.get("citations") or []

            cluster_content = [
                Paragraph(f"1.{idx} {_escape(theme_title)}", h2_style),
                Paragraph(_escape(summary_text), body_style),
            ]

            if citations:
                cite_str = ", ".join(_escape(c) for c in citations)
                cite_p = Paragraph(f"<b>Key Citations:</b> {cite_str}", quote_style)
                cluster_content.append(Spacer(1, 2))
                cluster_content.append(cite_p)

            cluster_content.append(Spacer(1, 8))
            story.append(KeepTogether(cluster_content))

    # Section 2: Methodology Comparison Matrix
    methodology_matrix: List[Dict[str, Any]] = synthesized_review.get("methodology_matrix") or []
    if methodology_matrix:
        story.append(Spacer(1, 10))
        story.append(Paragraph("2. Comparative Methodology Matrix", h1_style))
        story.append(
            Paragraph(
                "Structured cross-paper analysis comparing research paradigms, empirical models, benchmark strengths, and known constraints.",
                body_style,
            )
        )
        story.append(Spacer(1, 4))

        matrix_rows: List[List[Any]] = [
            [
                Paragraph("Methodology", table_header_style),
                Paragraph("Papers Applied", table_header_style),
                Paragraph("Advantages / Strengths", table_header_style),
                Paragraph("Known Limitations", table_header_style),
            ]
        ]

        col_w = [110, 130, 150, 150]  # Total 540 pt

        for item in methodology_matrix:
            method_name = item.get("method_name") or "Method"
            papers = item.get("papers_used") or []
            strengths = item.get("strengths") or []
            limitations = item.get("limitations") or []

            papers_formatted = "<br/>".join(f"• {_escape(p)}" for p in papers) or "—"
            strengths_formatted = "<br/>".join(f"• {_escape(s)}" for s in strengths) or "—"
            limits_formatted = "<br/>".join(f"• {_escape(l)}" for l in limitations) or "—"

            matrix_rows.append(
                [
                    Paragraph(_escape(method_name), table_cell_bold),
                    Paragraph(papers_formatted, table_cell_style),
                    Paragraph(strengths_formatted, table_cell_style),
                    Paragraph(limits_formatted, table_cell_style),
                ]
            )

        matrix_table = Table(matrix_rows, colWidths=col_w, repeatRows=1, hAlign="LEFT")
        matrix_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ]
            )
        )
        story.append(matrix_table)

    # Section 3: Research Gaps & Strategic Roadmap
    research_gaps: List[str] = synthesized_review.get("research_gaps") or []
    if research_gaps:
        story.append(Spacer(1, 14))
        story.append(Paragraph("3. Research Gaps & Strategic Roadmap", h1_style))
        story.append(
            Paragraph(
                "Critical unaddressed challenges, conflicting benchmark findings, and theoretical voids identified across the literature corpus:",
                body_style,
            )
        )
        story.append(Spacer(1, 4))

        for idx, gap in enumerate(research_gaps, 1):
            gap_num_cell = Paragraph(f"<b>Gap {idx}</b>", table_cell_bold)
            gap_text_cell = Paragraph(_escape(gap), body_style)

            gap_table = Table(
                [[gap_num_cell, gap_text_cell]],
                colWidths=[55, printable_width - 55],
                hAlign="LEFT",
            )
            gap_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFBEB")),
                        ("LINEBEFORE", (0, 0), (0, -1), 2.5, colors.HexColor("#D97706")),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#FDE68A")),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            story.append(gap_table)
            story.append(Spacer(1, 4))

    # Section 4: Conclusion (if provided)
    conclusion: Optional[str] = synthesized_review.get("conclusion")
    if conclusion:
        story.append(Spacer(1, 12))
        story.append(Paragraph("4. Conclusion & Theoretical Implications", h1_style))
        story.append(Paragraph(_escape(conclusion), body_style))

    # Section 5: References & Bibliography
    references: List[Dict[str, Any]] = synthesized_review.get("references") or []
    if references:
        story.append(Spacer(1, 14))
        story.append(Paragraph("5. Grounded References & Verified Bibliography", h1_style))
        story.append(Spacer(1, 4))

        for idx, ref in enumerate(references, 1):
            ref_title = ref.get("title") or f"Reference {idx}"
            authors_list = ref.get("authors") or []
            authors_str = (
                ", ".join(authors_list) if isinstance(authors_list, list) else str(authors_list)
            )
            year = ref.get("year")
            year_str = f" ({year})" if year else ""
            url = ref.get("url") or ""
            passage = ref.get("matched_passage")

            ref_entry = [
                Paragraph(f"<b>[{idx}] {_escape(ref_title)}</b>{_escape(year_str)}", body_style),
            ]
            if authors_str:
                ref_entry.append(
                    Paragraph(f"<b>Authors:</b> {_escape(authors_str)}", table_cell_style)
                )
            if url:
                ref_entry.append(
                    Paragraph(f"<b>URL:</b> <font color='#4338CA'>{_escape(url)}</font>", table_cell_style)
                )
            if passage:
                ref_entry.append(
                    Paragraph(f"<b>Verbatim Passage:</b> &ldquo;{_escape(passage)}&rdquo;", quote_style)
                )

            ref_entry.append(Spacer(1, 6))
            story.append(KeepTogether(ref_entry))

    # Build PDF with two-pass NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes


def _get_s3_client() -> Any:
    """Instantiate standard Boto3 S3 client configured with settings."""
    s3_config = Config(
        connect_timeout=3,
        read_timeout=5,
        retries={"max_attempts": 2},
    )
    client_kwargs: Dict[str, Any] = {
        "region_name": settings.AWS_REGION,
        "config": s3_config,
    }
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        client_kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        client_kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
    if settings.AWS_SESSION_TOKEN:
        client_kwargs["aws_session_token"] = settings.AWS_SESSION_TOKEN

    return boto3.client("s3", **client_kwargs)


def upload_report_pdf_to_s3_sync(pdf_bytes: bytes, review_id: int) -> str:
    """Synchronous helper to upload compiled report PDF bytes to AWS S3."""
    s3_key = f"exports/literature_review_{review_id}.pdf"
    client = _get_s3_client()
    client.put_object(
        Bucket=settings.AWS_S3_BUCKET,
        Key=s3_key,
        Body=pdf_bytes,
        ContentType="application/pdf",
    )
    return s3_key


async def upload_report_pdf_to_s3(pdf_bytes: bytes, review_id: int) -> str:
    """Upload compiled review PDF to s3://{AWS_S3_BUCKET}/exports/literature_review_{review_id}.pdf.

    Args:
        pdf_bytes: Raw PDF document bytes.
        review_id: Literature review primary key.

    Returns:
        The S3 key where the document was stored.
    """
    return await asyncio.to_thread(upload_report_pdf_to_s3_sync, pdf_bytes, review_id)


def check_report_pdf_exists_in_s3_sync(s3_key: str) -> bool:
    """Synchronous check if an object exists in the S3 bucket using head_object."""
    client = _get_s3_client()
    try:
        client.head_object(Bucket=settings.AWS_S3_BUCKET, Key=s3_key)
        return True
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code in ("404", "NoSuchKey", "NotFound"):
            return False
        logger.warning("S3 head_object error checking '%s': %s", s3_key, exc)
        return False
    except Exception as exc:
        logger.warning("Unexpected error checking S3 key '%s': %s", s3_key, exc)
        return False


async def check_report_pdf_exists_in_s3(s3_key: str) -> bool:
    """Async check if a compiled PDF already exists in S3."""
    return await asyncio.to_thread(check_report_pdf_exists_in_s3_sync, s3_key)


def generate_presigned_download_url(
    s3_key: str, expiration: int = 3600, filename: Optional[str] = None
) -> str:
    """Generate a presigned S3 GET URL with Content-Disposition attachment header for direct browser download.

    Args:
        s3_key: S3 object key.
        expiration: Presigned URL validity in seconds (default: 3600s / 1 hour).
        filename: Optional custom attachment filename.

    Returns:
        Secure HTTPS presigned download URL.
    """
    client = _get_s3_client()
    dl_filename = filename or s3_key.split("/")[-1]
    params = {
        "Bucket": settings.AWS_S3_BUCKET,
        "Key": s3_key,
        "ResponseContentDisposition": f'attachment; filename="{dl_filename}"',
        "ResponseContentType": "application/pdf",
    }
    return client.generate_presigned_url(
        "get_object",
        Params=params,
        ExpiresIn=expiration,
    )

