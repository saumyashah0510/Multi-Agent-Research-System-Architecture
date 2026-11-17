// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, useLocation } from "react-router-dom";
import PastReviewsView from "../src/components/dashboard/PastReviewsView";
import PastReviewsDrawer from "../src/components/dashboard/PastReviewsDrawer";
import { fetchPastReviews } from "../src/lib/api";
vi.mock("../src/lib/api", () => ({ fetchPastReviews: vi.fn(), getReviewPdfDownloadUrl: vi.fn() }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });
const review = { id: "r1", query: "Review topic", status: "failed", created_at: "2026-01-01" };
function Location() { return <output data-testid="location">{useLocation().pathname}</output>; }

describe("failed past reviews", () => {
  it.each([
    { failed_stage: "discovery", stage: "search", current_step: "approval" },
    { failedStage: "discovery", currentStep: "approval" },
    {},
  ])("preserves retry metadata when Resume is selected: %j", async (metadata) => {
    vi.mocked(fetchPastReviews).mockResolvedValue([{ ...review, id: 7, status: "ERROR", ...metadata }] as never);
    const onSelectReview = vi.fn();
    render(<PastReviewsView targetSection="report" onSelectReview={onSelectReview} onStartNewResearch={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Resume" }));
    expect(onSelectReview).toHaveBeenCalledTimes(1);
    expect(onSelectReview).toHaveBeenCalledWith(expect.objectContaining({
      id: "7", status: "failed", raw_status: "ERROR",
      failed_stage: "failed_stage" in metadata ? metadata.failed_stage : "failedStage" in metadata ? metadata.failedStage : undefined,
      current_step: "current_step" in metadata ? metadata.current_step : "currentStep" in metadata ? metadata.currentStep : undefined,
    }));
  });

  it("prefers snake case stage metadata when both spellings exist", async () => {
    vi.mocked(fetchPastReviews).mockResolvedValue([{ ...review, failed_stage: "screening", failedStage: "synthesis", current_step: "approval", currentStep: "report" }] as never);
    const select = vi.fn();
    render(<PastReviewsView targetSection="papers" onSelectReview={select} onStartNewResearch={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Resume" }));
    expect(select).toHaveBeenCalledWith(expect.objectContaining({ failed_stage: "screening", current_step: "approval" }));
  });

  it("closes the drawer and navigates to the failed review", async () => {
    vi.mocked(fetchPastReviews).mockResolvedValue([review] as never);
    const close = vi.fn();
    render(<MemoryRouter><PastReviewsDrawer isOpen onClose={close} /><Location /></MemoryRouter>);
    fireEvent.click(await screen.findByRole("button", { name: "Resume" }));
    expect(close).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("location").textContent).toBe("/review/r1");
    expect(screen.queryByRole("button", { name: "Open Review" })).toBeNull();
  });

  it("retains Open Review for a completed drawer entry", async () => {
    vi.mocked(fetchPastReviews).mockResolvedValue([{ ...review, status: "completed" }] as never);
    render(<MemoryRouter><PastReviewsDrawer isOpen onClose={vi.fn()} /></MemoryRouter>);
    expect(await screen.findByRole("button", { name: "Open Review" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Resume" })).toBeNull();
  });
});
