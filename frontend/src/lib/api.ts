// API Client Helper for Scholaris Multi-Agent Research System
import { AuthResponse, ChatHistoryMessage, ChatResponse, CitationGraphResponse, UserProfile } from "../types";

export function getApiBaseUrl(): string {
  const envApiUrl = import.meta.env?.VITE_API_URL;
  if (envApiUrl && typeof envApiUrl === "string" && envApiUrl.trim()) {
    return envApiUrl.trim().replace(/\/+$/, "");
  }

  if (typeof window !== "undefined" && window.location) {
    const { hostname, port, protocol } = window.location;
    // When running Vite dev server locally on port 5173 / 5174
    if (port === "5173" || port === "5174") {
      return "http://localhost:8000/api/v1";
    }
    // In production, use same-origin relative URL proxied by Nginx
    return `${protocol}//${hostname}${port ? `:${port}` : ""}/api/v1`;
  }

  return "http://localhost:8000/api/v1";
}

export async function fetchHealthStatus() {
  const res = await fetch(`${getApiBaseUrl()}/health`);
  if (!res.ok) {
    throw new Error(`Health check failed with status ${res.status}`);
  }
  return res.json();
}

export async function createReviewTask(query: string, maxPapers: number = 10) {
  const res = await fetch(`${getApiBaseUrl()}/reviews/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ query, max_papers: maxPapers }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to initiate review task: ${res.statusText}`);
  }
  return res.json();
}

export async function getReviewStatus(reviewId: string) {
  const res = await fetch(`${getApiBaseUrl()}/reviews/${reviewId}`, {
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
  });
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
  const res = await fetch(`${getApiBaseUrl()}/reviews/${reviewId}/approve`, {
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
  const res = await fetch(`${getApiBaseUrl()}/reviews/${encodeURIComponent(reviewId)}/chat`, {
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
  const res = await fetch(`${getApiBaseUrl()}/reviews/?limit=${limit}`, {
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch past reviews: ${res.statusText}`);
  }
  return res.json();
}

export function getReviewPdfDownloadUrl(reviewId: string): string {
  return `${getApiBaseUrl()}/reviews/${reviewId}/export`;
}


// Auth API Helpers (Issue FE-11)
export function getAuthToken(): string | null {
  return localStorage.getItem("scholaris_token");
}

export function setAuthToken(token: string): void {
  localStorage.setItem("scholaris_token", token);
}

export function clearAuthToken(): void {
  localStorage.removeItem("scholaris_token");
}

export function getAuthHeaders(): HeadersInit {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function loginUser(email: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${getApiBaseUrl()}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Login failed with status ${res.status}`);
  }
  return res.json();
}

export async function registerUser(email: string, password: string, name?: string): Promise<AuthResponse> {
  const res = await fetch(`${getApiBaseUrl()}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, name }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Registration failed with status ${res.status}`);
  }
  return res.json();
}

export async function fetchCurrentUser(): Promise<UserProfile> {
  const res = await fetch(`${getApiBaseUrl()}/auth/me`, {
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch current user: ${res.statusText}`);
  }
  return res.json();
}


// OAuth API Helpers (Issue FE-12)
export async function authWithGoogle(
  credential?: string,
  code?: string,
  redirectUri?: string
): Promise<AuthResponse> {
  const res = await fetch(`${getApiBaseUrl()}/auth/google`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ credential, code, redirect_uri: redirectUri }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Google authentication failed: ${res.statusText}`);
  }
  return res.json();
}

export async function authWithGitHub(code: string): Promise<AuthResponse> {
  const res = await fetch(`${getApiBaseUrl()}/auth/github`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `GitHub authentication failed: ${res.statusText}`);
  }
  return res.json();
}


// Pipeline Retry API (Issue FE-13)
export async function retryReviewPipeline(reviewId: string | number): Promise<any> {
  // TODO (Assignee - FE-13): POST /reviews/{reviewId}/retry
  const res = await fetch(`${getApiBaseUrl()}/reviews/${reviewId}/retry`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Retry failed with status ${res.status}`);
  }
  return res.json();
}


// Citation Knowledge Graph API (Issue FE-14)
export async function fetchReviewGraph(
  reviewId: string | number
): Promise<CitationGraphResponse> {
  // TODO (Assignee - FE-14): GET /reviews/{reviewId}/graph
  const res = await fetch(`${getApiBaseUrl()}/reviews/${reviewId}/graph`, {
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch citation knowledge graph: ${res.statusText}`);
  }
  return res.json();
}
