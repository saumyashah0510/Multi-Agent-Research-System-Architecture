// @vitest-environment jsdom
import { cleanup, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useDownstreamWebSocket } from "../src/hooks/useDownstreamWebSocket";

class SocketStub {
  close = vi.fn();
}
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("downstream REST status synchronization", () => {
  it.each(["failed", "FAILED", "error", "Error"])("stops processing for %s with no socket", (initialStatus) => {
    const { result } = renderHook(() => useDownstreamWebSocket(null, { initialStatus }));
    expect(result.current.status).toBe("FAILED");
    expect(result.current.isRunning).toBe(false);
    expect(result.current.isCompleted).toBe(false);
  });

  it.each(["failed", "ERROR"])("preserves %s while connecting a real review", (initialStatus) => {
    vi.stubGlobal("WebSocket", SocketStub);
    const { result } = renderHook(() => useDownstreamWebSocket("r1", { initialStatus }));
    expect(result.current.status).toBe("FAILED");
    expect(result.current.isRunning).toBe(false);
  });

  it("handles a REST failure that arrives after mount", () => {
    const { result, rerender } = renderHook(({ initialStatus }) =>
      useDownstreamWebSocket(null, { initialStatus }), { initialProps: { initialStatus: "report_synthesis" } });
    expect(result.current.isRunning).toBe(true);
    rerender({ initialStatus: "failed" });
    expect(result.current.status).toBe("FAILED");
    expect(result.current.isRunning).toBe(false);
  });

  it("keeps a completed pipeline completed when stale failure status arrives", () => {
    const { result } = renderHook(() => useDownstreamWebSocket(null, { initialCompleted: true, initialStatus: "failed" }));
    expect(result.current.status).toBe("COMPLETED");
    expect(result.current.isCompleted).toBe(true);
    expect(result.current.stages.every((s) => s.status === "completed")).toBe(true);
  });

  it.each([
    ["pdf_extraction", 0], ["vector_embedding", 1], ["gap_analysis", 2],
    ["citation_verification", 3], ["report_synthesis", 4],
  ])("resumes at %s without resetting earlier stages", (initialStatus, index) => {
    vi.stubGlobal("WebSocket", SocketStub);
    const { result } = renderHook(() => useDownstreamWebSocket("r1", { initialStatus }));
    expect(result.current.stages.map((s) => s.status)).toEqual(
      Array.from({ length: 5 }, (_, i) => i < index ? "completed" : i === index ? "running" : "pending"),
    );
    expect(result.current.isRunning).toBe(true);
    result.current.stages.slice(0, index).forEach((s) => expect(s.result).toBeTruthy());
  });
});
