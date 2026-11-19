// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import CitationKnowledgeGraph, { CLUSTER_COLORS } from "../src/components/graph/CitationKnowledgeGraph";
import { fetchReviewGraph } from "../src/lib/api";
import type { CitationGraphResponse } from "../src/types";

vi.mock("../src/lib/api", () => ({
  fetchReviewGraph: vi.fn(),
}));

const mockGraphData: CitationGraphResponse = {
  review_id: 42,
  total_nodes: 3,
  total_links: 2,
  nodes: [
    {
      id: "paper_1",
      label: "Attention Is All You Need",
      type: "paper",
      year: 2017,
      authors: ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
      relevance_score: 0.98,
      cluster: "Transformers & Self-Attention",
      url: "https://arxiv.org/abs/1706.03762",
      citation_count: 50000,
    },
    {
      id: "paper_2",
      label: "BERT: Pre-training of Deep Bidirectional Transformers",
      type: "paper",
      year: 2018,
      authors: ["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee"],
      relevance_score: 0.95,
      cluster: "Transformers & Self-Attention",
      url: "https://arxiv.org/abs/1810.04805",
      citation_count: 45000,
    },
    {
      id: "paper_3",
      label: "Deep Residual Learning for Image Recognition",
      type: "paper",
      year: 2015,
      authors: ["Kaiming He", "Xiangyu Zhang", "Shaoqing Ren"],
      relevance_score: 0.88,
      cluster: "Convolutional Networks",
      url: "https://arxiv.org/abs/1512.03385",
      citation_count: 80000,
    },
  ],
  links: [
    {
      source: "paper_1",
      target: "paper_2",
      type: "thematic_similarity",
      weight: 0.85,
    },
    {
      source: "paper_1",
      target: "paper_2",
      type: "co_authorship",
      weight: 0.9,
    },
  ],
};

const flush = async () => {
  await act(async () => {});
};

describe("CitationKnowledgeGraph Component (FE-14)", () => {
  beforeEach(() => {
    vi.mocked(fetchReviewGraph).mockResolvedValue(mockGraphData);
  });

  afterEach(() => {
    cleanup();
    vi.resetAllMocks();
  });

  it("fetches graph topology on mount and renders header stats", async () => {
    render(<CitationKnowledgeGraph reviewId="42" />);
    await flush();

    expect(fetchReviewGraph).toHaveBeenCalledWith("42");
    expect(screen.getByText("Citation Knowledge Graph")).toBeTruthy();
    const papersBadge = screen.getByTestId("total-papers-badge");
    const connectionsBadge = screen.getByTestId("total-connections-badge");
    expect(papersBadge.textContent).toContain("3 Papers");
    expect(connectionsBadge.textContent).toContain("2 Connections");
  });

  it("renders the Paper Inspector Card with paper metadata", async () => {
    render(<CitationKnowledgeGraph reviewId="42" />);
    await flush();

    // Default selected node is paper_1, scoped directly to the inspector card
    const inspector = screen.getByTestId("paper-inspector-card");
    expect(inspector).toBeTruthy();
    expect(within(inspector).getByText("Selected Paper")).toBeTruthy();
    const heading = within(inspector).getByTestId("inspector-paper-title");
    expect(heading.textContent).toBe("Attention Is All You Need");
    expect(within(inspector).getByText(/Ashish Vaswani/)).toBeTruthy();
    expect(within(inspector).getByText("Published 2017")).toBeTruthy();
    expect(within(inspector).getByText("98% Match")).toBeTruthy();
    expect(within(inspector).getByTestId("inspector-paper-cluster").textContent).toContain(
      "Transformers & Self-Attention"
    );
    expect(within(inspector).getByText("Open Source Document")).toBeTruthy();
  });

  it("renders the floating thematic cluster legend with cluster names and categorical palette", async () => {
    render(<CitationKnowledgeGraph reviewId="42" />);
    await flush();

    expect(screen.getByText("Thematic Clusters:")).toBeTruthy();
    expect(screen.getByTitle("Transformers & Self-Attention")).toBeTruthy();
    expect(screen.getByTitle("Convolutional Networks")).toBeTruthy();
    expect(CLUSTER_COLORS).toHaveLength(6);
  });

  it("provides interactive zoom controls (Zoom In, Zoom Out, Reset)", async () => {
    render(<CitationKnowledgeGraph reviewId="42" />);
    await flush();

    const zoomInBtn = screen.getByTitle("Zoom In");
    const zoomOutBtn = screen.getByTitle("Zoom Out");
    const resetZoomBtn = screen.getByTitle("Reset Zoom");

    expect(zoomInBtn).toBeTruthy();
    expect(zoomOutBtn).toBeTruthy();
    expect(resetZoomBtn).toBeTruthy();

    await act(async () => {
      fireEvent.click(zoomInBtn);
      fireEvent.click(zoomOutBtn);
      fireEvent.click(resetZoomBtn);
    });
  });

  it("gracefully renders empty state when no approved papers are available", async () => {
    vi.mocked(fetchReviewGraph).mockResolvedValueOnce({
      review_id: 42,
      total_nodes: 0,
      total_links: 0,
      nodes: [],
      links: [],
    });

    render(<CitationKnowledgeGraph reviewId="42" />);
    await flush();

    expect(
      screen.getByText(
        "No approved papers found for this review session to construct the knowledge graph."
      )
    ).toBeTruthy();
  });

  it("closes the inspector card when the close button is clicked", async () => {
    render(<CitationKnowledgeGraph reviewId="42" />);
    await flush();

    expect(screen.getByText("Selected Paper")).toBeTruthy();
    const closeBtn = screen.getByTitle("Close Inspector");
    expect(closeBtn).toBeTruthy();

    await act(async () => {
      fireEvent.click(closeBtn);
    });

    expect(screen.queryByText("Selected Paper")).toBeNull();
  });

  it("safely handles dangling links with invalid node endpoints", async () => {
    vi.mocked(fetchReviewGraph).mockResolvedValueOnce({
      review_id: 42,
      total_nodes: 2,
      total_links: 3,
      nodes: [
        { id: "paper_1", label: "Paper 1", cluster: "Cluster A" },
        { id: "paper_2", label: "Paper 2", cluster: "Cluster B" },
      ],
      links: [
        { source: "paper_1", target: "paper_2" },
        { source: "paper_1", target: "paper_missing_999" }, // Dangling endpoint
        { source: "paper_missing_888", target: "paper_2" }, // Dangling endpoint
      ],
    });

    render(<CitationKnowledgeGraph reviewId="42" />);
    await flush();

    const papersBadge = screen.getByTestId("total-papers-badge");
    const connectionsBadge = screen.getByTestId("total-connections-badge");
    expect(papersBadge.textContent).toContain("2 Papers");
    expect(connectionsBadge.textContent).toContain("3 Connections");
  });

  it("supports node selection, deselection, and legitimate clicks without blocking window", async () => {
    const { container } = render(<CitationKnowledgeGraph reviewId="42" />);
    await flush();

    // Verify initial selection is paper_1 via inspector heading
    const initialInspector = screen.getByTestId("paper-inspector-card");
    expect(within(initialInspector).getByTestId("inspector-paper-title").textContent).toBe(
      "Attention Is All You Need"
    );

    // Deselect via background click using stable canvas testid
    const svg = screen.getByTestId("citation-graph-canvas");
    expect(svg).toBeTruthy();
    await act(async () => {
      fireEvent.click(svg);
    });
    expect(screen.queryByTestId("paper-inspector-card")).toBeNull();

    // Select paper_2 by clicking its node
    const nodeItems = container.querySelectorAll(".node-item");
    expect(nodeItems.length).toBe(3);
    if (nodeItems[1]) {
      await act(async () => {
        fireEvent.click(nodeItems[1]!);
      });
      const updatedInspector = screen.getByTestId("paper-inspector-card");
      expect(updatedInspector).toBeTruthy();
      expect(within(updatedInspector).getByTestId("inspector-paper-title").textContent).toBe(
        "BERT: Pre-training of Deep Bidirectional Transformers"
      );
    }
  });

  it("displays error message if fetchReviewGraph fails", async () => {
    vi.mocked(fetchReviewGraph).mockRejectedValueOnce(
      new Error("Database connection timed out")
    );

    render(<CitationKnowledgeGraph reviewId="42" />);
    await flush();

    expect(screen.getByText("Database connection timed out")).toBeTruthy();
  });
});
