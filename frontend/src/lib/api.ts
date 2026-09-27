// API Client Helper for Scholaris Multi-Agent Research System
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
      approved_paper_ids: approvedPaperIds,
      decision: decision,
    }),
  });
  if (!res.ok) {
    throw new Error(`Failed to submit human approval: ${res.statusText}`);
  }
  return res.json();
}
