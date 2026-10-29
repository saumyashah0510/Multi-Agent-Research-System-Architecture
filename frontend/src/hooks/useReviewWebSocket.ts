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

import { useState, useEffect, useRef } from "react";
import { PipelineStage, INITIAL_DEMO_STAGES } from "../components/pipeline/types";
import { PaperSummary } from "../components/PaperSummaryCard";
import { ReviewStatus } from "../types";

export interface ReviewWebSocketState {
  stages: PipelineStage[];
  screenedPapers: PaperSummary[];
  status: ReviewStatus;
  isConnected: boolean;
  isPausedForInput: boolean;
  error: string | null;
}

export function useReviewWebSocket(reviewId: string | null): ReviewWebSocketState {
  const [stages, setStages] = useState<PipelineStage[]>(INITIAL_DEMO_STAGES);
  const [screenedPapers, setScreenedPapers] = useState<PaperSummary[]>([]);
  const [status, setStatus] = useState<ReviewStatus>("PENDING");
  const [isConnected, setIsConnected] = useState(false);
  const [isPausedForInput, setIsPausedForInput] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!reviewId) return;

    // TODO (Assignee - FE-05):
    // 1. Build WebSocket URL (e.g. ws://localhost:8000/api/v1/ws/reviews/{reviewId})
    // 2. Initialize WebSocket and attach onopen, onmessage, onerror, onclose handlers
    // 3. In onmessage:
    //    - Parse event payload: { event: string, stage: ReviewStatus, message?: string, data?: any }
    //    - Map stage to corresponding PipelineStage index and update status ("running" | "completed")
    //    - If stage === "AWAITING_USER_INPUT":
    //        * Set isPausedForInput(true)
    //        * Extract data.screened_papers and call setScreenedPapers(...)
    // 4. Implement exponential backoff reconnect if socket closes unexpectedly
    // 5. Clean up socket on unmount

    // Starter reference placeholders for assignee
    void setStages;
    void setScreenedPapers;
    void setStatus;
    void setIsConnected;
    void setIsPausedForInput;
    void setError;

    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [reviewId]);

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
