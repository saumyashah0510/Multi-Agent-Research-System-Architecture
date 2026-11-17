// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import ReviewDetail from "../src/pages/ReviewDetail";
import { getReviewStatus, retryReviewPipeline } from "../src/lib/api";
import type { DownstreamProgressProps } from "../src/components/pipeline/DownstreamProgress";

vi.mock("../src/lib/api", () => ({ getReviewStatus: vi.fn(), retryReviewPipeline: vi.fn(), getReviewPdfDownloadUrl: vi.fn() }));
vi.mock("../src/components/dashboard/SynthesisReportViewer", () => ({ default: () => null, formatReportAsMarkdown: vi.fn() }));
vi.mock("../src/components/graph/CitationKnowledgeGraph", () => ({ default: () => null }));
vi.mock("../src/components/pipeline/DownstreamProgress", async () => {
  const { useEffect } = await import("react");
  return { default: (props: DownstreamProgressProps) => {
    useEffect(() => { tracker.mounts(); }, []);
    return <><output data-testid="initial-status">{props.initialStatus}</output>
      <button onClick={() => props.onFailed?.("PDF Extraction", "Live failure")}>Fail stream</button>
      <button onClick={props.onComplete}>Complete stream</button></>;
  } };
});
const tracker = vi.hoisted(() => ({ mounts: vi.fn() }));
const failed = { status: "failed", failed_stage: "citation_verification", error_message: "Checkpoint failure" };
const flush = async () => { await act(async () => {}); };
function mount() {
  return render(<MemoryRouter initialEntries={["/review/r1"]}><Routes>
    <Route path="/review/:reviewId" element={<ReviewDetail />} />
  </Routes></MemoryRouter>);
}
beforeEach(() => {
  vi.useFakeTimers();
  vi.mocked(getReviewStatus).mockResolvedValue(failed);
  vi.mocked(retryReviewPipeline).mockResolvedValue({ status: "processing" });
});
afterEach(() => { cleanup(); vi.useRealTimers(); vi.resetAllMocks(); });

describe("ReviewDetail recovery", () => {
  it("shows the failed stage from REST and remounts progress after an accepted retry", async () => {
    mount(); await flush();
    expect(screen.getByRole("heading", { name: /Paused at Citation Verification/ })).toBeTruthy();
    const mountsBefore = tracker.mounts.mock.calls.length;
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Retry from Failed Step" })));
    expect(retryReviewPipeline).toHaveBeenCalledExactlyOnceWith("r1");
    expect(screen.queryByRole("button", { name: "Retry from Failed Step" })).toBeNull();
    expect(screen.getByTestId("initial-status").textContent).toBe("citation_verification");
    expect(tracker.mounts).toHaveBeenCalledTimes(mountsBefore + 1);
  });

  it("suppresses stale failed GETs during resume but restores failure after the safety timeout", async () => {
    mount(); await flush();
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Retry from Failed Step" })));
    await act(async () => vi.advanceTimersByTimeAsync(1000));
    expect(screen.queryByRole("button", { name: "Retry from Failed Step" })).toBeNull();
    await act(async () => vi.advanceTimersByTimeAsync(5000));
    expect(screen.getByRole("button", { name: "Retry from Failed Step" })).toBeTruthy();
    expect(getReviewStatus).toHaveBeenCalledTimes(3);
  });

  it("retains the failure UI and permits another attempt when POST fails", async () => {
    vi.mocked(retryReviewPipeline).mockRejectedValueOnce(new Error("Checkpoint locked"));
    mount(); await flush();
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Retry from Failed Step" })));
    expect(screen.getByText("Checkpoint locked")).toBeTruthy();
    await act(async () => vi.advanceTimersByTimeAsync(6000));
    expect(getReviewStatus).toHaveBeenCalledTimes(1);
    expect((screen.getByRole("button", { name: "Retry from Failed Step" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it.each(["current_step", "stage"])("uses %s when failed_stage is absent", async (key) => {
    vi.mocked(getReviewStatus).mockResolvedValue({ status: "failed", [key]: "pdf_extraction" });
    mount(); await flush();
    expect(screen.getByRole("heading", { name: /Paused at PDF Extraction/ })).toBeTruthy();
  });

  it("accepts a fresh stream failure during the resume grace period", async () => {
    mount(); await flush();
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Retry from Failed Step" })));
    fireEvent.click(screen.getByRole("button", { name: "Fail stream" }));
    expect(screen.getByRole("heading", { name: /Paused at PDF Extraction/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Retry from Failed Step" })).toBeTruthy();
  });

  it("ignores an in-flight REST result superseded by a live pipeline failure", async () => {
    let resolve!: (value: unknown) => void;
    vi.mocked(getReviewStatus).mockReturnValueOnce(new Promise((done) => { resolve = done; }));
    mount();
    fireEvent.click(screen.getByRole("button", { name: "Fail stream" }));
    await act(async () => resolve({ status: "report_synthesis", query: "Stale topic" }));
    expect(screen.getByRole("heading", { name: /Paused at PDF Extraction/ })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "View Error" }));
    expect(screen.getByText("Live failure")).toBeTruthy();
    expect(screen.queryByText("Stale topic")).toBeNull();
  });

  it("cancels the resume safeguard after live completion", async () => {
    mount(); await flush();
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Retry from Failed Step" })));
    vi.mocked(getReviewStatus).mockResolvedValue({ status: "completed", synthesized_review: { title: "Done" } });
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Complete stream" })));
    await act(async () => vi.advanceTimersByTimeAsync(6000));
    // Initial GET, completion GET, and the already scheduled one-second refresh.
    expect(getReviewStatus).toHaveBeenCalledTimes(3);
    expect(screen.queryByRole("button", { name: "Retry from Failed Step" })).toBeNull();
  });
});
