// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import RetryBanner from "../src/components/pipeline/RetryBanner";

afterEach(cleanup);
const retryButton = () => screen.getByRole("button", { name: "Retry from Failed Step" });

describe("RetryBanner", () => {
  it.each([
    [undefined, "Report Synthesis"], ["", "Report Synthesis"],
    ["CITATION_VERIFICATION", "Citation Verification"],
    ["  pdf--EXTRACTION  ", "PDF Extraction"], ["llm_report-synthesis", "LLM Report Synthesis"],
  ])("formats stage %s for the researcher", (failedStage, title) => {
    render(<RetryBanner reviewId="r1" failedStage={failedStage} onRetry={vi.fn()} />);
    expect(screen.getByRole("heading").textContent).toBe(`Pipeline Execution Paused at ${title}`);
    expect(screen.getByRole("alert").getAttribute("aria-live")).toBe("polite");
  });

  it("reveals and hides the raw error only on request", () => {
    const trace = "Checkpoint failed\n<unsafe>";
    render(<RetryBanner reviewId="r1" errorMessage={trace} onRetry={vi.fn()} />);
    expect(screen.queryByText(/Checkpoint failed/)).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "View Error" }));
    expect(screen.getByText(/Checkpoint failed/).textContent).toBe(trace);
    fireEvent.click(screen.getByRole("button", { name: "Hide Error" }));
    expect(screen.queryByText(/Checkpoint failed/)).toBeNull();
  });

  it("omits technical disclosure when there is no trace", () => {
    render(<RetryBanner reviewId={1} onRetry={vi.fn()} />);
    expect(screen.queryByRole("button", { name: "View Error" })).toBeNull();
  });

  it("disables repeat clicks and exposes busy state until retry settles", async () => {
    let resolve!: () => void;
    const onRetry = vi.fn(() => new Promise<void>((done) => { resolve = done; }));
    render(<RetryBanner reviewId="r1" onRetry={onRetry} />);
    fireEvent.click(retryButton());
    const busy = screen.getByRole("button", { name: "Resuming from Checkpoint..." }) as HTMLButtonElement;
    expect(busy.disabled).toBe(true);
    expect(busy.getAttribute("aria-busy")).toBe("true");
    fireEvent.click(busy);
    expect(onRetry).toHaveBeenCalledTimes(1);
    await act(async () => resolve());
    expect((retryButton() as HTMLButtonElement).disabled).toBe(false);
    expect(retryButton().getAttribute("aria-busy")).toBe("false");
  });

  it.each([
    [new Error("Failed to fetch"), "Network error:"],
    [new Error("NetworkError"), "Network error:"],
    [new Error("NETWORK disconnected"), "Network error:"],
    [new Error("Checkpoint expired"), "Checkpoint expired"],
    ["Retry denied", "Retry denied"], [{ message: "Session expired" }, "Session expired"],
    [null, "Failed to resume pipeline. Please try again."],
    [{ message: 42 }, "Failed to resume pipeline. Please try again."],
  ])("handles unknown rejection %# without crashing", async (error, message) => {
    render(<RetryBanner reviewId="r1" onRetry={vi.fn().mockRejectedValue(error)} />);
    fireEvent.click(retryButton());
    expect(await screen.findByText(message as string, { exact: false })).toBeTruthy();
    expect((retryButton() as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "Dismiss error" }));
    expect(screen.queryByText(message as string, { exact: false })).toBeNull();
    expect(screen.getByRole("heading")).toBeTruthy();
  });

  it("clears a previous error as soon as another retry begins", async () => {
    const onRetry = vi.fn().mockRejectedValueOnce(new Error("Checkpoint locked"))
      .mockResolvedValueOnce(undefined);
    render(<RetryBanner reviewId="r1" onRetry={onRetry} />);
    fireEvent.click(retryButton());
    await screen.findByText("Checkpoint locked");
    await act(async () => fireEvent.click(retryButton()));
    expect(screen.queryByText("Checkpoint locked")).toBeNull();
    expect(onRetry).toHaveBeenCalledTimes(2);
  });
});
