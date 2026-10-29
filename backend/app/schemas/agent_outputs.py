"""Pydantic schemas for structured LLM agent outputs."""

from typing import List

from pydantic import BaseModel, Field


class QueryExpansionOutput(BaseModel):
    """Structured output schema for Agent 01 Query Expansion."""

    target_domains: List[str] = Field(
        default_factory=list, description="Academic domain classifications (e.g. cs.AI, q-bio)"
    )
    search_queries: List[str] = Field(
        default_factory=list, description="3-5 deconstructed sub-queries for arXiv and Scholar"
    )


class PaperScreeningItem(BaseModel):
    """Single paper screening evaluation."""

    paper_id_or_title: str
    relevance_score: float = Field(
        ..., ge=0.0, le=1.0, description="Relevance score from 0.0 to 1.0"
    )
    reason: str = Field(..., description="Justification for inclusion or exclusion")
    accepted: bool = Field(..., description="True if relevance_score >= 0.6")


class ScreeningOutput(BaseModel):
    """Structured output schema for Agent 03 Screening."""

    decisions: List[PaperScreeningItem] = Field(default_factory=list)


class MethodologyItem(BaseModel):
    """Single methodology comparison entry across analyzed papers."""

    method_name: str = Field(..., description="Methodology, algorithm, or architecture category")
    papers_used: List[str] = Field(
        default_factory=list, description="Titles or IDs of papers using this method"
    )
    strengths: List[str] = Field(
        default_factory=list, description="Observed advantages or benchmark strengths"
    )
    limitations: List[str] = Field(
        default_factory=list, description="Known bottlenecks, overhead, or constraints"
    )


class GapAnalysisOutput(BaseModel):
    """Structured output schema for Agent 07 Gap Analysis."""

    methodology_matrix: List[MethodologyItem] = Field(
        default_factory=list, description="Comparative methodology breakdown across analyzed papers"
    )
    research_gaps: List[str] = Field(
        default_factory=list, description="3-5 identified unaddressed challenges or research voids"
    )


class VerifiedCitationItem(BaseModel):
    """Single citation verification result checking for hallucination."""

    claim: str = Field(..., description="Specific factual claim or assertion made in the review")
    paper_id_or_title: str = Field(..., description="Cited paper identifier or paper title")
    matched_passage: str = Field(
        default="", description="Exact or near-match text snippet from paper chunk"
    )
    is_supported: bool = Field(
        ..., description="True if supported by the paper text; False if hallucinated"
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence score of verification"
    )


class CitationVerificationOutput(BaseModel):
    """Structured output schema for Agent 08 Citation Verification."""

    verified_citations: List[VerifiedCitationItem] = Field(default_factory=list)
    has_hallucinations: bool = Field(
        default=False, description="True if any unverified claims exist"
    )
    verification_summary: str = Field(
        default="", description="High-level evaluation of factual accuracy"
    )


class ThematicClusterItem(BaseModel):
    """Single thematic discussion section synthesizing multiple papers."""

    theme: str = Field(
        ..., description="Theme or topic title (e.g. 'Efficiency & Quantization Techniques')"
    )
    summary: str = Field(
        ..., description="In-depth analytical synthesis of papers under this theme"
    )
    citations: List[str] = Field(
        default_factory=list, description="Paper titles or citation keys referenced"
    )


class SynthesizedReviewOutput(BaseModel):
    """Structured output schema for Agent 09 Synthesis Report."""

    title: str = Field(..., description="Formal academic title of the literature review")
    executive_summary: str = Field(..., description="Comprehensive high-level summary of findings")
    thematic_clusters: List[ThematicClusterItem] = Field(default_factory=list)
    methodology_matrix: List[MethodologyItem] = Field(default_factory=list)
    research_gaps: List[str] = Field(default_factory=list)
    conclusion: str = Field(
        default="", description="Concluding synthesis remarks and future directions"
    )
    references: List[dict] = Field(
        default_factory=list, description="Curated reference bibliography"
    )
