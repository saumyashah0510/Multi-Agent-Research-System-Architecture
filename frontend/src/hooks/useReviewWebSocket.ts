/**
 * Custom React Hook: useReviewWebSocket
 *
 * Assignee Task (Issue FE-05):
 * - Establish WebSocket connection to /api/v1/ws/reviews/{reviewId}
 * - Parse incoming live Redis Pub/Sub events from backend LangGraph pipeline
 * - Update PipelineStage states for first 3 checkpoints (Query Expansion, Discovery, Screening)
 * - Populate candidate screened papers when status reaches AWAITING_USER_INPUT
 * - Handle reconnects and network drops with exponential backoff
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { PipelineStage, StageStatus, INITIAL_DEMO_STAGES } from "../components/pipeline/types";
import { PaperSummary } from "../components/PaperSummaryCard";
import { ReviewStatus, WebSocketStageUpdateEvent } from "../types";

export interface ReviewWebSocketState {
  stages: PipelineStage[];
  screenedPapers: PaperSummary[];
  status: ReviewStatus;
  isConnected: boolean;
  isPausedForInput: boolean;
  error: string | null;
}

const MAX_RECONNECT_ATTEMPTS = 5;
const INITIAL_RECONNECT_DELAY_MS = 1000;
const MAX_RECONNECT_DELAY_MS = 16000;

/**
 * Builds standard WebSocket URL for connecting to literature review progress stream.
 */
export function getWebSocketUrl(reviewId: string): string {
  const envWsUrl = import.meta.env?.VITE_WS_URL;
  if (envWsUrl && typeof envWsUrl === "string") {
    const trimmed = envWsUrl.trim().replace(/\/+$/, "");
    if (trimmed.includes("{reviewId}")) {
      return trimmed.replace("{reviewId}", encodeURIComponent(reviewId));
    }
    if (trimmed.endsWith("/reviews")) {
      return `${trimmed}/${encodeURIComponent(reviewId)}`;
    }
    if (trimmed.endsWith("/ws")) {
      return `${trimmed}/reviews/${encodeURIComponent(reviewId)}`;
    }
    return `${trimmed}/reviews/${encodeURIComponent(reviewId)}`;
  }

  const envApiUrl = import.meta.env?.VITE_API_URL;
  if (envApiUrl && typeof envApiUrl === "string") {
    const trimmed = envApiUrl.trim().replace(/\/+$/, "");
    const wsBase = trimmed
      .replace(/^http:\/\//i, "ws://")
      .replace(/^https:\/\//i, "wss://");
    return `${wsBase}/ws/reviews/${encodeURIComponent(reviewId)}`;
  }

  return `ws://localhost:8000/api/v1/ws/reviews/${encodeURIComponent(reviewId)}`;
}

/**
 * Normalizes raw paper dicts from LangGraph screening node into UI PaperSummary items.
 */
export function normalizePaper(raw: any, index: number): PaperSummary {
  const rawId = raw.id ?? raw.paper_id ?? raw.arxiv_id ?? raw.doi ?? `paper-${index + 1}`;

  let authors = "Unknown Authors";
  if (typeof raw.authors === "string" && raw.authors.trim()) {
    authors = raw.authors.trim();
  } else if (Array.isArray(raw.authors) && raw.authors.length > 0) {
    if (raw.authors.length > 2) {
      authors = `${raw.authors[0]}, et al.`;
    } else {
      authors = raw.authors.join(", ");
    }
  }

  let year: number | string = new Date().getFullYear();
  if (raw.year !== undefined && raw.year !== null) {
    year = raw.year;
  } else if (raw.published_year !== undefined && raw.published_year !== null) {
    year = raw.published_year;
  } else if (raw.publication_date) {
    const match = String(raw.publication_date).match(/\b\d{4}\b/);
    if (match) year = match[0];
  }

  const venue = raw.venue || raw.source || raw.journal || "Academic Repository";
  const abstract = raw.abstract || raw.summary || "No abstract available.";

  let relevanceScore = 95;
  const scoreVal = raw.relevance_score ?? raw.relevanceScore ?? raw.score;
  if (typeof scoreVal === "number") {
    relevanceScore = scoreVal <= 1 ? Math.round(scoreVal * 100) : Math.round(scoreVal);
  }

  let url = raw.url || raw.pdf_url;
  if (!url) {
    if (raw.arxiv_id) {
      url = `https://arxiv.org/abs/${raw.arxiv_id}`;
    } else if (raw.doi) {
      url = `https://doi.org/${raw.doi}`;
    }
  }

  const tags = Array.isArray(raw.tags) ? raw.tags : [];

  return {
    id: String(rawId),
    title: raw.title || `Research Paper ${index + 1}`,
    authors,
    year,
    venue,
    abstract,
    tags,
    relevanceScore,
    isSelected: raw.isSelected !== undefined ? Boolean(raw.isSelected) : true,
    url,
  };
}

/**
 * Resolves corresponding stage index (0 = Query Expansion, 1 = Discovery, 2 = Screening)
 */
function getStageIndex(stageName: string): number | null {
  const norm = stageName.toUpperCase().replace(/[\s-]/g, "_");
  if (norm.includes("QUERY_EXPANSION") || norm === "AGENT_01" || norm.includes("EXPANSION")) {
    return 0;
  }
  if (
    norm.includes("PAPER_DISCOVERY") ||
    norm.includes("ACADEMIC_SEARCH") ||
    norm.includes("DISCOVERY") ||
    norm === "AGENT_02"
  ) {
    return 1;
  }
  if (
    norm.includes("SCREENING") ||
    norm.includes("RELEVANCE_SCREENING") ||
    norm === "AGENT_03"
  ) {
    return 2;
  }
  return null;
}

export function useReviewWebSocket(reviewId: string | null): ReviewWebSocketState {
  const [stages, setStages] = useState<PipelineStage[]>(() =>
    INITIAL_DEMO_STAGES.map((s) => ({ ...s }))
  );
  const [screenedPapers, setScreenedPapers] = useState<PaperSummary[]>([]);
  const [status, setStatus] = useState<ReviewStatus>("PENDING");
  const [isConnected, setIsConnected] = useState(false);
  const [isPausedForInput, setIsPausedForInput] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isManualCloseRef = useRef(false);
  const isPausedForInputRef = useRef(false);
  const isCompletedRef = useRef(false);

  // Keep refs in sync with state
  useEffect(() => {
    isPausedForInputRef.current = isPausedForInput;
  }, [isPausedForInput]);

  useEffect(() => {
    isCompletedRef.current = status === "COMPLETED";
  }, [status]);

  const connect = useCallback(() => {
    if (!reviewId) return;

    if (isPausedForInputRef.current || isCompletedRef.current) {
      return;
    }

    try {
      const wsUrl = getWebSocketUrl(reviewId);
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event: MessageEvent) => {
        try {
          const payload: WebSocketStageUpdateEvent =
            typeof event.data === "string" ? JSON.parse(event.data) : event.data;

          if (!payload) return;

          const rawStage = String(
            payload.stage || payload.step || payload.current_step || ""
          ).trim();
          const normStage = rawStage.toUpperCase().replace(/[\s-]/g, "_");
          const normStatus = String(payload.status || "running").toLowerCase();
          const message = payload.message || null;
          const data = payload.data || {};

          // Check if this is the Human-in-the-Loop Interrupt checkpoint
          if (
            normStage === "AWAITING_USER_INPUT" ||
            normStage === "AWAITING_APPROVAL" ||
            normStage === "HUMAN_IN_LOOP" ||
            payload.event === "awaiting_user_input"
          ) {
            setIsPausedForInput(true);
            isPausedForInputRef.current = true;
            setStatus("AWAITING_USER_INPUT");

            // Extract candidate screened papers
            const candidateList =
              data.screened_papers ||
              payload.screened_papers ||
              data.papers ||
              payload.papers ||
              [];

            let normalized: PaperSummary[] = [];
            if (Array.isArray(candidateList) && candidateList.length > 0) {
              normalized = candidateList.map((paper: any, idx: number) =>
                normalizePaper(paper, idx)
              );
              setScreenedPapers(normalized);
            }

            // Mark all three demo pipeline stages completed
            setStages((prevStages) =>
              prevStages.map((stg, idx) => ({
                ...stg,
                status: "completed",
                message: null,
                result:
                  idx === 2 && normalized.length > 0
                    ? `${data.total_screened || normalized.length} papers screened · ${normalized.length} relevant papers retained`
                    : stg.result,
              }))
            );
            return;
          }

          // Check if review has completed entirely
          if (normStage === "COMPLETED" || (normStatus === "completed" && normStage === "")) {
            setStatus("COMPLETED");
            isCompletedRef.current = true;
            setStages((prevStages) =>
              prevStages.map((stg) => ({
                ...stg,
                status: "completed",
                message: null,
              }))
            );
            return;
          }

          // Check if review or stage has failed
          if (normStage === "FAILED" || normStatus === "failed" || normStatus === "error") {
            setStatus("FAILED");
            setError(message || "Pipeline execution encountered an error");
            const targetIdx = getStageIndex(rawStage);
            if (targetIdx !== null) {
              setStages((prevStages) =>
                prevStages.map((stg, idx) =>
                  idx === targetIdx
                    ? { ...stg, status: "failed", error: message || "Stage failed" }
                    : stg
                )
              );
            }
            return;
          }

          // Process Checkpoint Stages 01–03
          const targetIndex = getStageIndex(rawStage);
          if (targetIndex !== null) {
            // Update review lifecycle status
            if (targetIndex === 0) setStatus("QUERY_EXPANSION");
            else if (targetIndex === 1) setStatus("PAPER_DISCOVERY");
            else if (targetIndex === 2) setStatus("SCREENING");

            // Check if screened papers came alongside screening completion
            if (
              targetIndex === 2 &&
              Array.isArray(data.screened_papers) &&
              data.screened_papers.length > 0
            ) {
              const normalized = data.screened_papers.map((p: any, idx: number) =>
                normalizePaper(p, idx)
              );
              setScreenedPapers(normalized);
            }

            setStages((prevStages) =>
              prevStages.map((stg, idx) => {
                // Preceding stages are completed
                if (idx < targetIndex) {
                  return {
                    ...stg,
                    status: "completed",
                    message: null,
                  };
                }

                // Active matching stage
                if (idx === targetIndex) {
                  const isRunning =
                    normStatus === "running" ||
                    normStatus === "in_progress" ||
                    normStatus === "started";
                  const isCompleted =
                    normStatus === "completed" ||
                    normStatus === "done" ||
                    normStatus === "success";
                  const isFailed =
                    normStatus === "failed" || normStatus === "error";

                  let nextStatus: StageStatus = stg.status;
                  if (isRunning) nextStatus = "running";
                  else if (isCompleted) nextStatus = "completed";
                  else if (isFailed) nextStatus = "failed";

                  let updatedMessage = stg.message;
                  let updatedResult = stg.result;
                  let updatedProgress = stg.progress;
                  let updatedError = stg.error;

                  if (isRunning) {
                    updatedMessage = message || stg.supportingStatus;
                    // Format stage-specific metrics if provided in event data
                    if (targetIndex === 0 && Array.isArray(data.sub_queries) && data.sub_queries.length > 0) {
                      updatedMessage = `Generating ${data.sub_queries.length} academic sub-queries...`;
                    } else if (targetIndex === 1) {
                      if (data.counts && typeof data.counts === "object") {
                        const countsDesc = Object.entries(data.counts)
                          .map(([src, count]) => `${src}: ${count}`)
                          .join(", ");
                        updatedMessage = `Discovered papers (${countsDesc})...`;
                      } else if (data.total_count || data.count) {
                        updatedMessage = `Discovered ${data.total_count || data.count} candidate papers...`;
                      }
                    } else if (targetIndex === 2) {
                      if (data.screened_count !== undefined && data.total !== undefined) {
                        updatedMessage = `Scoring papers: ${data.screened_count} of ${data.total}...`;
                        updatedProgress = Math.round((data.screened_count / data.total) * 100);
                      }
                    }
                  } else if (isCompleted) {
                    updatedMessage = null;
                    if (message) {
                      updatedResult = message;
                    } else if (targetIndex === 0 && Array.isArray(data.sub_queries)) {
                      updatedResult = `${data.sub_queries.length} search queries generated`;
                    } else if (targetIndex === 1 && (data.total_count !== undefined || data.count !== undefined)) {
                      updatedResult = `${data.total_count ?? data.count} candidate papers discovered`;
                    } else if (targetIndex === 2 && Array.isArray(data.screened_papers)) {
                      updatedResult = `${data.total_screened || data.screened_papers.length} papers screened · ${data.screened_papers.length} relevant papers retained`;
                    }
                  } else if (isFailed) {
                    updatedError = message || "Stage execution failed";
                  }

                  if (typeof data.progress === "number") {
                    updatedProgress = data.progress;
                  }

                  return {
                    ...stg,
                    status: nextStatus,
                    message: updatedMessage,
                    result: updatedResult,
                    progress: updatedProgress,
                    error: updatedError,
                  };
                }

                // Subsequent stages remain in current state
                return stg;
              })
            );
          }
        } catch (err) {
          console.warn("Failed to parse WebSocket event payload:", err);
        }
      };

      ws.onerror = () => {
        setError("WebSocket connection encountered an error");
      };

      ws.onclose = () => {
        setIsConnected(false);

        // Do not auto-reconnect if intentionally closed, paused for HITL, or already completed
        if (
          isManualCloseRef.current ||
          isPausedForInputRef.current ||
          isCompletedRef.current
        ) {
          return;
        }

        // Automatic reconnect with exponential backoff
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          const delay = Math.min(
            INITIAL_RECONNECT_DELAY_MS * Math.pow(2, reconnectAttemptsRef.current),
            MAX_RECONNECT_DELAY_MS
          );
          reconnectAttemptsRef.current += 1;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else {
          setError("WebSocket connection lost. Max reconnection attempts reached.");
        }
      };
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to open WebSocket");
    }
  }, [reviewId]);

  useEffect(() => {
    if (!reviewId) return;

    // Reset lifecycle state on new reviewId
    isManualCloseRef.current = false;
    isPausedForInputRef.current = false;
    isCompletedRef.current = false;
    reconnectAttemptsRef.current = 0;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    setStages(INITIAL_DEMO_STAGES.map((s) => ({ ...s })));
    setScreenedPapers([]);
    setStatus("PENDING");
    setIsConnected(false);
    setIsPausedForInput(false);
    setError(null);

    connect();

    return () => {
      isManualCloseRef.current = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  }, [reviewId, connect]);

  return {
    stages,
    screenedPapers,
    status,
    isConnected,
    isPausedForInput,
    error,
  };
}

export default useReviewWebSocket;
