/**
 * Custom React Hook: useDownstreamWebSocket
 *
 * Assignee Task (Issue FE-07):
 * - Establish WebSocket connection to /api/v1/ws/reviews/{reviewId}
 * - Stream incoming events for downstream agents (Agents 05 to 09):
 *   5. PDF Extraction (PDF_EXTRACTION)
 *   6. Vector Embedding (VECTOR_EMBEDDING)
 *   7. Gap Analysis (GAP_ANALYSIS)
 *   8. Citation Verification (CITATION_VERIFICATION)
 *   9. Report Synthesis (REPORT_SYNTHESIS)
 * - Dynamically update PipelineStage states and progress
 * - Auto-complete and trigger onComplete callback when REPORT_SYNTHESIS finishes
 */

import { useState, useEffect, useRef, useCallback } from "react";
import {
  PipelineStage,
  StageStatus,
  DOWNSTREAM_PIPELINE_STAGES,
} from "../components/pipeline/types";
import { ReviewStatus, WebSocketStageUpdateEvent } from "../types";
import { getWebSocketUrl } from "./useReviewWebSocket";

export interface DownstreamWebSocketOptions {
  onComplete?: () => void;
  isMock?: boolean;
  initialCompleted?: boolean;
  initialStatus?: string;
}

export interface DownstreamWebSocketState {
  stages: PipelineStage[];
  status: ReviewStatus;
  isRunning: boolean;
  isCompleted: boolean;
  isConnected: boolean;
  error: string | null;
  simulatePipeline: () => void;
}

const MAX_RECONNECT_ATTEMPTS = 5;
const INITIAL_RECONNECT_DELAY_MS = 1000;
const MAX_RECONNECT_DELAY_MS = 16000;

/**
 * Maps raw stage identifier to downstream stage index:
 * 0: PDF Extraction (Agent 05)
 * 1: Vector Embedding (Agent 06)
 * 2: Gap Analysis (Agent 07)
 * 3: Citation Verification (Agent 08)
 * 4: Report Synthesis (Agent 09)
 */
export function getDownstreamStageIndex(stageName: string): number | null {
  if (!stageName) return null;
  const norm = String(stageName).toUpperCase().replace(/[\s-]/g, "_");

  if (
    norm.includes("PDF_EXTRACTION") ||
    norm.includes("PDF_EXTRACT") ||
    norm.includes("EXTRACT_PDF") ||
    norm === "AGENT_05" ||
    norm === "AGENT_5" ||
    norm === "PDF"
  ) {
    return 0;
  }
  if (
    norm.includes("VECTOR_EMBEDDING") ||
    norm.includes("EMBEDDING") ||
    norm.includes("VECTOR") ||
    norm.includes("PGVECTOR") ||
    norm === "AGENT_06" ||
    norm === "AGENT_6"
  ) {
    return 1;
  }
  if (
    norm.includes("GAP_ANALYSIS") ||
    norm.includes("METHODOLOGY") ||
    norm.includes("GAP") ||
    norm === "AGENT_07" ||
    norm === "AGENT_7"
  ) {
    return 2;
  }
  if (
    norm.includes("CITATION_VERIFICATION") ||
    norm.includes("CITATION") ||
    norm.includes("VERIFIER") ||
    norm.includes("VERIFICATION") ||
    norm.includes("ANTI_HALLUCINATION") ||
    norm === "AGENT_08" ||
    norm === "AGENT_8"
  ) {
    return 3;
  }
  if (
    norm.includes("REPORT_SYNTHESIS") ||
    norm.includes("SYNTHESIS") ||
    norm.includes("REPORT") ||
    norm === "AGENT_09" ||
    norm === "AGENT_9"
  ) {
    return 4;
  }
  return null;
}

export function getDefaultCompletedResult(index: number): string {
  switch (index) {
    case 0:
      return "Full-text PDFs extracted and cached to AWS S3";
    case 1:
      return "384D dense semantic vector embeddings indexed";
    case 2:
      return "Methodology matrix and research gaps mapped";
    case 3:
      return "Anti-hallucination check verified all source claims";
    case 4:
      return "Comprehensive literature review report synthesized";
    default:
      return "Stage completed";
  }
}

export function getDynamicCompletedResult(index: number, data?: any): string {
  if (!data) return getDefaultCompletedResult(index);
  switch (index) {
    case 0:
      if (data.pdf_count || data.count) {
        return `${data.pdf_count || data.count} full-text PDFs cached to S3`;
      }
      return getDefaultCompletedResult(0);
    case 1:
      if (data.chunks || data.chunk_count) {
        return `${data.chunks || data.chunk_count} text chunks indexed in pgvector`;
      }
      return getDefaultCompletedResult(1);
    case 2:
      if (data.gaps_count || (Array.isArray(data.gaps) && data.gaps.length > 0)) {
        const count = data.gaps_count || data.gaps.length;
        return `Methodology matrix and ${count} research gaps mapped`;
      }
      return getDefaultCompletedResult(2);
    case 3:
      if (data.verified_claims || data.verified_count) {
        const count = data.verified_claims || data.verified_count;
        return `${count} citations corroborated against source passages`;
      }
      return getDefaultCompletedResult(3);
    case 4:
      return getDefaultCompletedResult(4);
    default:
      return getDefaultCompletedResult(index);
  }
}

export function useDownstreamWebSocket(
  reviewId: string | null | undefined,
  options: DownstreamWebSocketOptions = {}
): DownstreamWebSocketState {
  const { onComplete, isMock = false, initialCompleted = false, initialStatus } = options;

  const [stages, setStages] = useState<PipelineStage[]>(() => {
    if (initialCompleted) {
      return DOWNSTREAM_PIPELINE_STAGES.map((s, idx) => ({
        ...s,
        status: "completed" as StageStatus,
        message: null,
        result: getDefaultCompletedResult(idx),
      }));
    }
    return DOWNSTREAM_PIPELINE_STAGES.map((s) => ({ ...s }));
  });

  const [status, setStatus] = useState<ReviewStatus>(() =>
    initialCompleted ? "COMPLETED" : "PENDING"
  );
  const [isRunning, setIsRunning] = useState(!initialCompleted);
  const [isCompleted, setIsCompleted] = useState(initialCompleted);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const simulationIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isManualCloseRef = useRef(false);
  const isCompletedRef = useRef(initialCompleted);
  const onCompleteRef = useRef(onComplete);

  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    if (initialCompleted) {
      setIsCompleted(true);
      setIsRunning(false);
      setStatus("COMPLETED");
      isCompletedRef.current = true;
      setStages(
        DOWNSTREAM_PIPELINE_STAGES.map((s, idx) => ({
          ...s,
          status: "completed",
          message: null,
          result: getDefaultCompletedResult(idx),
        }))
      );
    }
  }, [initialCompleted]);

  const handleIncomingPayload = useCallback((payload: WebSocketStageUpdateEvent) => {
    if (!payload) return;

    const rawStage = String(payload.stage || payload.step || payload.current_step || "").trim();
    const normStage = rawStage.toUpperCase().replace(/[\s-]/g, "_");
    const normStatus = String(payload.status || "running").toLowerCase();
    const message = payload.message || null;
    const data = payload.data || {};

    // 1. Overall Pipeline Completion
    if (
      normStage === "COMPLETED" ||
      payload.event === "pipeline_completed" ||
      payload.event === "completed" ||
      (normStatus === "completed" && (normStage === "" || normStage === "REPORT_SYNTHESIS"))
    ) {
      setStages((prev) =>
        prev.map((s, idx) => ({
          ...s,
          status: "completed",
          message: null,
          result: s.result || getDefaultCompletedResult(idx),
        }))
      );
      setStatus("COMPLETED");
      setIsRunning(false);
      setIsCompleted(true);
      isCompletedRef.current = true;
      if (onCompleteRef.current) {
        onCompleteRef.current();
      }
      return;
    }

    // 2. Stage or Overall Failure
    if (normStage === "FAILED" || normStatus === "failed" || normStatus === "error") {
      setStatus("FAILED");
      setIsRunning(false);
      setError(message || "Pipeline execution failed");
      const targetIdx = getDownstreamStageIndex(rawStage);
      if (targetIdx !== null) {
        setStages((prev) =>
          prev.map((s, idx) =>
            idx === targetIdx
              ? { ...s, status: "failed", error: message || "Stage execution failed" }
              : s
          )
        );
      }
      return;
    }

    // 3. Downstream Stage Update (05 to 09)
    const targetIndex = getDownstreamStageIndex(rawStage);
    if (targetIndex !== null) {
      const isStageRunning =
        normStatus === "running" || normStatus === "in_progress" || normStatus === "started";
      const isStageCompleted =
        normStatus === "completed" || normStatus === "done" || normStatus === "success";
      const isStageFailed =
        normStatus === "failed" || normStatus === "error";

      const downstreamEnums: ReviewStatus[] = [
        "PDF_EXTRACTION",
        "VECTOR_EMBEDDING",
        "GAP_ANALYSIS",
        "CITATION_VERIFICATION",
        "REPORT_SYNTHESIS",
      ];
      setStatus(downstreamEnums[targetIndex] || "PENDING");
      if (isStageRunning) setIsRunning(true);

      setStages((prevStages) =>
        prevStages.map((stg, idx) => {
          // Preceding stages must be completed
          if (idx < targetIndex) {
            return {
              ...stg,
              status: "completed",
              message: null,
              result: stg.result || getDefaultCompletedResult(idx),
            };
          }

          // Active matching stage
          if (idx === targetIndex) {
            let nextStatus: StageStatus = stg.status;
            if (isStageRunning) nextStatus = "running";
            else if (isStageCompleted) nextStatus = "completed";
            else if (isStageFailed) nextStatus = "failed";

            let updatedMessage = stg.message;
            let updatedResult = stg.result;
            let updatedProgress = stg.progress;
            let updatedError = stg.error;

            if (isStageRunning) {
              updatedMessage = message || stg.supportingStatus;
              if (typeof data.progress === "number") {
                updatedProgress = data.progress;
              }
            } else if (isStageCompleted) {
              updatedMessage = null;
              updatedProgress = 100;
              updatedResult = message || getDynamicCompletedResult(idx, data);
            } else if (isStageFailed) {
              updatedError = message || "Stage execution failed";
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

          // Subsequent stages remain pending
          return stg;
        })
      );

      // Final report synthesis completed
      if (targetIndex === 4 && isStageCompleted) {
        setIsCompleted(true);
        setIsRunning(false);
        setStatus("COMPLETED");
        isCompletedRef.current = true;
        if (onCompleteRef.current) {
          onCompleteRef.current();
        }
      }
    }
  }, []);

  const simulatePipeline = useCallback(() => {
    if (simulationIntervalRef.current) {
      clearInterval(simulationIntervalRef.current);
      simulationIntervalRef.current = null;
    }

    setIsRunning(true);
    setIsCompleted(false);
    isCompletedRef.current = false;
    setStages(DOWNSTREAM_PIPELINE_STAGES.map((s) => ({ ...s })));

    const steps = [
      { stage: "PDF_EXTRACTION", status: "running", message: "Extracting methodology, results, and discussion sections..." },
      { stage: "PDF_EXTRACTION", status: "completed", message: "Full-text PDFs extracted and cached to AWS S3" },
      { stage: "VECTOR_EMBEDDING", status: "running", message: "Generating 384-dimensional dense semantic vectors..." },
      { stage: "VECTOR_EMBEDDING", status: "completed", message: "384D dense semantic vector embeddings indexed" },
      { stage: "GAP_ANALYSIS", status: "running", message: "Synthesizing cross-paper methodology matrix and 3-5 research gaps..." },
      { stage: "GAP_ANALYSIS", status: "completed", message: "Methodology matrix and research gaps synthesized" },
      { stage: "CITATION_VERIFICATION", status: "running", message: "Corroborating factual claims against source passages..." },
      { stage: "CITATION_VERIFICATION", status: "completed", message: "Anti-hallucination check verified all source claims" },
      { stage: "REPORT_SYNTHESIS", status: "running", message: "Synthesizing executive summary, thematic clusters, and bibliography..." },
      { stage: "REPORT_SYNTHESIS", status: "completed", message: "Comprehensive literature review report synthesized" },
    ];

    let stepIndex = 0;
    const interval = setInterval(() => {
      if (stepIndex >= steps.length) {
        clearInterval(interval);
        if (simulationIntervalRef.current === interval) {
          simulationIntervalRef.current = null;
        }
        handleIncomingPayload({
          event: "completed",
          stage: "COMPLETED",
          status: "completed",
        });
        return;
      }

      const current = steps[stepIndex];
      if (current) {
        handleIncomingPayload({
          event: "stage_update",
          stage: current.stage,
          status: current.status,
          message: current.message,
        });
      }
      stepIndex++;
    }, 700);

    simulationIntervalRef.current = interval;
    return () => {
      clearInterval(interval);
      if (simulationIntervalRef.current === interval) {
        simulationIntervalRef.current = null;
      }
    };
  }, [handleIncomingPayload]);

  // Window dispatch helpers for manual/automated browser testing
  useEffect(() => {
    if (typeof window !== "undefined") {
      (window as any).__dispatchDownstreamEvent = handleIncomingPayload;
      (window as any).__simulateDownstreamStages = simulatePipeline;
    }
    return () => {
      if (typeof window !== "undefined") {
        delete (window as any).__dispatchDownstreamEvent;
        delete (window as any).__simulateDownstreamStages;
      }
    };
  }, [handleIncomingPayload, simulatePipeline]);

  // Connect to real WebSocket stream if reviewId exists and not already completed/mock
  const connect = useCallback(() => {
    if (!reviewId || isMock || isCompletedRef.current) return;

    try {
      const wsUrl = getWebSocketUrl(reviewId);
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        if (socketRef.current !== ws) return;
        setIsConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event: MessageEvent) => {
        if (socketRef.current !== ws) return;
        try {
          const payload: WebSocketStageUpdateEvent =
            typeof event.data === "string" ? JSON.parse(event.data) : event.data;
          handleIncomingPayload(payload);
        } catch (err) {
          console.warn("Failed to parse downstream WebSocket message:", err);
        }
      };

      ws.onerror = () => {
        if (socketRef.current !== ws) return;
        setError("WebSocket connection encountered an error");
      };

      ws.onclose = () => {
        if (socketRef.current !== ws) return;
        setIsConnected(false);
        if (isManualCloseRef.current || isCompletedRef.current) {
          return;
        }

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
          setIsRunning(false);
          setStatus("FAILED");
          setError("Lost connection to the progress stream");
        }
      };
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to open WebSocket");
    }
  }, [reviewId, isMock, handleIncomingPayload]);

  useEffect(() => {
    if (isMock) {
      if (!initialCompleted) {
        return simulatePipeline();
      }
      return;
    }

    if (!reviewId || initialCompleted) return;

    isManualCloseRef.current = false;
    reconnectAttemptsRef.current = 0;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (simulationIntervalRef.current) {
      clearInterval(simulationIntervalRef.current);
      simulationIntervalRef.current = null;
    }

    // Set initial stage if passed (e.g. from GET /api/v1/reviews/{reviewId})
    if (initialStatus) {
      const idx = getDownstreamStageIndex(initialStatus);
      if (idx !== null) {
        setStages((prev) =>
          prev.map((s, i) => ({
            ...s,
            status: i < idx ? "completed" : i === idx ? "running" : "pending",
            message: i === idx ? s.supportingStatus : null,
            result: i < idx ? getDefaultCompletedResult(i) : null,
          }))
        );
      }
    }

    connect();

    return () => {
      isManualCloseRef.current = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (simulationIntervalRef.current) {
        clearInterval(simulationIntervalRef.current);
        simulationIntervalRef.current = null;
      }
      if (socketRef.current) {
        const s = socketRef.current;
        socketRef.current = null;
        s.onopen = null;
        s.onmessage = null;
        s.onerror = null;
        s.onclose = null;
        s.close();
      }
    };
  }, [reviewId, isMock, initialCompleted, initialStatus, connect, simulatePipeline]);

  return {
    stages,
    status,
    isRunning,
    isCompleted,
    isConnected,
    error,
    simulatePipeline,
  };
}

export default useDownstreamWebSocket;
