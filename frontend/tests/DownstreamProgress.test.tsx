// @vitest-environment jsdom
import { cleanup, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DownstreamProgress } from "../src/components/pipeline/DownstreamProgress";
import { useDownstreamWebSocket } from "../src/hooks/useDownstreamWebSocket";
import { DOWNSTREAM_PIPELINE_STAGES } from "../src/components/pipeline/types";
vi.mock("../src/hooks/useDownstreamWebSocket", () => ({ useDownstreamWebSocket: vi.fn() }));
vi.mock("../src/components/pipeline/StageCard", () => ({ StageCard: () => null }));
vi.mock("../src/components/pipeline/StageTimelineNode", () => ({ StageTimelineNode: () => null }));
const state = (overrides = {}) => ({ stages: [], status: "PENDING" as const, isRunning: false,
  isCompleted: false, isConnected: false, error: null, simulatePipeline: vi.fn(), ...overrides });
beforeEach(() => vi.mocked(useDownstreamWebSocket).mockReturnValue(state()));
afterEach(() => { cleanup(); vi.clearAllMocks(); });

describe("DownstreamProgress failure reporting", () => {
  it.each(["Stage failed", undefined])("reports the failed stage with error fallback %s", (error) => {
    vi.mocked(useDownstreamWebSocket).mockReturnValue(state({ status: "FAILED", error: "Stream failed" }));
    const onFailed = vi.fn();
    const stages = [{ ...DOWNSTREAM_PIPELINE_STAGES[0]!, status: "failed" as const, error }];
    render(<DownstreamProgress stages={stages} onFailed={onFailed} />);
    expect(onFailed).toHaveBeenCalledExactlyOnceWith(stages[0]!.title, error || "Stream failed");
  });
  it("reports an overall failure without inventing a failed stage", () => {
    vi.mocked(useDownstreamWebSocket).mockReturnValue(state({ status: "FAILED", error: "Disconnected" }));
    const onFailed = vi.fn();
    render(<DownstreamProgress onFailed={onFailed} />);
    expect(onFailed).toHaveBeenCalledExactlyOnceWith(undefined, "Disconnected");
  });
  it("does not treat a transient connection error as a pipeline failure", () => {
    vi.mocked(useDownstreamWebSocket).mockReturnValue(state({ error: "Connecting" }));
    const onFailed = vi.fn();
    render(<DownstreamProgress onFailed={onFailed} />);
    expect(onFailed).not.toHaveBeenCalled();
  });
  it.each([true, false])("suppresses stale failures when completion comes from props=%s", (fromProps) => {
    vi.mocked(useDownstreamWebSocket).mockReturnValue(state({ status: "FAILED", isCompleted: !fromProps }));
    const onFailed = vi.fn();
    render(<DownstreamProgress isCompleted={fromProps} onFailed={onFailed} />);
    expect(onFailed).not.toHaveBeenCalled();
  });
});
