// @vitest-environment jsdom
// Requires Vitest and jsdom; kept outside src so production builds need no test dependencies.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getApiBaseUrl, retryReviewPipeline } from "../src/lib/api";

describe("retryReviewPipeline", () => {
  const fetchMock = vi.fn();
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
    localStorage.clear();
  });
  afterEach(() => vi.unstubAllGlobals());

  it.each([42, "review/a?b=# c"])('POSTs an encoded review ID %s and returns the response', async (id) => {
    const body = { review_id: id, status: "processing" };
    fetchMock.mockResolvedValue(new Response(JSON.stringify(body)));
    await expect(retryReviewPipeline(id)).resolves.toEqual(body);
    expect(fetchMock).toHaveBeenCalledExactlyOnceWith(
      `${getApiBaseUrl()}/reviews/${encodeURIComponent(id)}/retry`,
      expect.objectContaining({ method: "POST", headers: expect.objectContaining({ "Content-Type": "application/json" }) }),
    );
  });

  it("includes the session token when retrying an authenticated review", async () => {
    localStorage.setItem("scholaris_token", "synthetic-test-token");
    fetchMock.mockResolvedValue(new Response('{}'));
    await retryReviewPipeline("r1");
    expect(fetchMock).toHaveBeenCalledWith(expect.any(String), expect.objectContaining({
      headers: expect.objectContaining({ Authorization: "Bearer synthetic-test-token" }),
    }));
  });

  it.each([
    [JSON.stringify({ detail: "Checkpoint missing" }), "Conflict", "Checkpoint missing"],
    [JSON.stringify({ detail: [{ msg: "Invalid review" }] }), "Bad Request", '[{"msg":"Invalid review"}]'],
    [JSON.stringify({ detail: { reason: "already running" } }), "Conflict", '{"reason":"already running"}'],
    ["{}", "Service Unavailable", "Failed to resume pipeline: Service Unavailable"],
    ["null", "Bad Gateway", "Failed to resume pipeline: Bad Gateway"],
    ["not json", "Bad Gateway", "Failed to resume pipeline: Bad Gateway"],
    ["not json", "", "Failed to resume pipeline"],
    ["{}", "", "Failed to resume pipeline"],
  ])("reports API failure %s (%s)", async (body, statusText, message) => {
    fetchMock.mockResolvedValue(new Response(body, { status: 409, statusText }));
    await expect(retryReviewPipeline("r1")).rejects.toThrow(message);
  });

  it("propagates transport failures for the banner to explain", async () => {
    const error = new TypeError("Failed to fetch");
    fetchMock.mockRejectedValue(error);
    await expect(retryReviewPipeline("r1")).rejects.toBe(error);
  });
});
