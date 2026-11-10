// API Client Helper for Scholaris Multi-Agent Research System
import { ChatHistoryMessage, ChatResponse } from "../types";

const API_BASE_URL =
  (import.meta.env && import.meta.env.VITE_API_URL) ||
  "http://localhost:8000/api/v1";

export async function fetchHealthStatus() {
  const res = await fetch(`${API_BASE_URL}/health`);
  if (!res.ok) {
    throw new Error(`Health check failed with status ${res.status}`);
  }
  return res.json();
}

export async function createReviewTask(query: string, maxPapers: number = 10) {
  const res = await fetch(`${API_BASE_URL}/reviews/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, max_papers: maxPapers }),
  });
  if (!res.ok) {
    throw new Error(`Failed to initiate review task: ${res.statusText}`);
  }
  return res.json();
}

export async function getReviewStatus(reviewId: string) {
  const res = await fetch(`${API_BASE_URL}/reviews/${reviewId}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch review status: ${res.statusText}`);
  }
  return res.json();
}

export async function submitHumanDecision(
  reviewId: string,
  approvedPaperIds: string[],
  decision: "continue" | "find_more"
) {
  const res = await fetch(`${API_BASE_URL}/reviews/${reviewId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_decision: decision,
      approved_paper_ids: approvedPaperIds,
    }),
  });
  if (!res.ok) {
    let errorDetail = res.statusText;
    try {
      const errorJson = await res.json();
      if (errorJson && errorJson.detail) {
        errorDetail =
          typeof errorJson.detail === "string"
            ? errorJson.detail
            : JSON.stringify(errorJson.detail);
      }
    } catch {
      // ignore
    }
    throw new Error(`Failed to submit human approval: ${errorDetail}`);
  }
  return res.json();
}

/**
 * Submits a question and conversation history to the literature review RAG chat endpoint.
 *
 * Targets POST /api/v1/reviews/{reviewId}/chat with a JSON payload containing the user's
 * current question and sanitized previous conversation history turns. Supports request
 * cancellation via an optional AbortSignal and gracefully parses FastAPI detail error responses.
 *
 * @param reviewId - Unique identifier of the literature review task.
 * @param question - The user's current query or question about the review literature.
 * @param history - Array of previous valid conversation turns formatted as [{ role, content }].
 * @param signal - Optional AbortSignal used to cancel the in-flight HTTP request.
 * @returns Promise resolving to the grounded ChatResponse containing the generated answer and retrieved citations.
 * @throws {Error} When the HTTP response is non-2xx, extracting FastAPI detail or HTTP status text.
 */
export async function sendReviewChatMessage(
  reviewId: string,
  question: string,
  history: ChatHistoryMessage[] = [],
  signal?: AbortSignal
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE_URL}/reviews/${encodeURIComponent(reviewId)}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, history }),
    signal,
  });
  if (!res.ok) {
    let errorDetail = res.statusText || `HTTP ${res.status}`;
    try {
      const errorJson = await res.json();
      if (errorJson && typeof errorJson.detail === "string") {
        errorDetail = errorJson.detail;
      }
    } catch {
      // Body may not be valid JSON or empty; fallback to status text
    }
    throw new Error(`Failed to send chat message: ${errorDetail}`);
  }
  return res.json();
}

export async function fetchPastReviews(limit: number = 20) {
  const res = await fetch(`${API_BASE_URL}/reviews/?limit=${limit}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch past reviews: ${res.statusText}`);
  }
  return res.json();
}

export function getReviewPdfDownloadUrl(reviewId: string): string {
  return `${API_BASE_URL}/reviews/${reviewId}/export`;
}
