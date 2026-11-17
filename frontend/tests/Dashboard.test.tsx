// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, useLocation } from "react-router-dom";
import Dashboard from "../src/pages/Dashboard";
import { retryReviewPipeline } from "../src/lib/api";
import type { PastReviewsViewProps } from "../src/components/dashboard/PastReviewsView";
import type { ReviewHistoryItem } from "../src/types";

const fixtures = vi.hoisted(() => ({ reviews: [] as ReviewHistoryItem[] }));
vi.mock("../src/components/dashboard/PastReviewsView", () => ({
  default: ({ onSelectReview }: PastReviewsViewProps) => <>{fixtures.reviews.map((review) =>
    <button key={review.id} onClick={() => onSelectReview(review)}>{review.query}</button>)}</>,
}));
vi.mock("../src/lib/api", () => ({
  retryReviewPipeline: vi.fn(), getReviewStatus: vi.fn().mockResolvedValue({ status: "discovering" }),
  createReviewTask: vi.fn(), submitHumanDecision: vi.fn(),
}));
vi.mock("../src/context/AuthContext", () => ({ useAuth: () => ({ isAuthenticated: true }) }));
vi.mock("../src/hooks/useReviewWebSocket", () => ({
  default: () => ({ stages: [], screenedPapers: [], status: "PENDING", isConnected: false }),
  normalizePaper: vi.fn(),
}));
vi.mock("../src/components/ResearchInput", () => ({ default: () => null }));
vi.mock("../src/components/dashboard/paper-grid", () => ({ default: () => null }));
vi.mock("../src/components/pipeline/ResearchProgress", () => ({ default: () => null }));
vi.mock("../src/components/chat/ReviewChat", () => ({ default: () => null }));

function Location() {
  const location = useLocation();
  return <output data-testid="location">{location.pathname}{location.search}</output>;
}
function mount(reviews: ReviewHistoryItem[]) {
  fixtures.reviews = reviews;
  return render(<MemoryRouter initialEntries={["/dashboard?tab=report"]}><Dashboard /><Location /></MemoryRouter>);
}
const review = (metadata: Partial<ReviewHistoryItem> = {}): ReviewHistoryItem => ({
  id: "review/a?b", query: "Failed review", status: "failed", created_at: "2026-01-01", ...metadata,
});
const location = () => screen.getByTestId("location").textContent;
beforeEach(() => { localStorage.clear(); vi.mocked(retryReviewPipeline).mockResolvedValue({ status: "processing" }); });
afterEach(() => { cleanup(); vi.clearAllMocks(); });

describe("Dashboard failed-review routing", () => {
  it.each(["query-expansion", "DISCOVERY", "paper search", "screening", "approval", "awaiting_user_input", "interrupt"])(
    "retries %s before opening the approval session", async (failed_stage) => {
      mount([review({ failed_stage })]);
      await act(async () => fireEvent.click(screen.getByRole("button", { name: "Failed review" })));
      expect(retryReviewPipeline).toHaveBeenCalledExactlyOnceWith("review/a?b");
      expect(location()).toBe("/dashboard?tab=research&review_id=review%2Fa%3Fb");
    },
  );

  it.each(["stage", "current_step", "raw_status"] as const)("uses %s when failed_stage is absent", async (key) => {
    mount([review({ [key]: "discovery" })]);
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Failed review" })));
    expect(retryReviewPipeline).toHaveBeenCalledTimes(1);
    expect(location()).toContain("tab=research");
  });

  it.each([{}, { failed_stage: "report_synthesis" }, { failed_stage: "citation_verification", stage: "discovery" }])(
    "opens downstream/unknown failures without starting an upstream retry: %j", async (metadata) => {
      mount([review(metadata)]);
      await act(async () => fireEvent.click(screen.getByRole("button", { name: "Failed review" })));
      expect(retryReviewPipeline).not.toHaveBeenCalled();
      expect(location()).toBe("/review/review%2Fa%3Fb");
    },
  );

  it("falls back to the review page when the upstream retry fails", async () => {
    vi.mocked(retryReviewPipeline).mockRejectedValueOnce(new Error("Checkpoint unavailable"));
    mount([review({ failed_stage: "screening" })]);
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Failed review" })));
    expect(location()).toBe("/review/review%2Fa%3Fb");
  });

  it.each([false, true])("ignores a superseded retry when it rejects=%s", async (reject) => {
    let resolve!: () => void;
    let fail!: (error: Error) => void;
    vi.mocked(retryReviewPipeline).mockReturnValueOnce(new Promise((done, rejected) => {
      resolve = () => done({}); fail = rejected;
    }));
    mount([review({ failed_stage: "discovery" }), review({ id: "new", query: "New selection", failed_stage: "report_synthesis" })]);
    fireEvent.click(screen.getByRole("button", { name: "Failed review" }));
    expect(location()).toBe("/dashboard?tab=report");
    fireEvent.click(screen.getByRole("button", { name: "New selection" }));
    expect(location()).toBe("/review/new");
    await act(async () => { if (reject) fail(new Error("Late failure")); else resolve(); });
    expect(location()).toBe("/review/new");
  });

  it("opens an awaiting-approval review without retrying it", async () => {
    mount([review({ status: "awaiting_approval" })]);
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Failed review" })));
    expect(retryReviewPipeline).not.toHaveBeenCalled();
    expect(location()).toBe("/dashboard?tab=research&review_id=review%2Fa%3Fb");
  });
});
