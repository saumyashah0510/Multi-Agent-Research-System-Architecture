/**
 * RetryBanner Component
 *
 * Assignee Task (Issue FE-13):
 * - Render an actionable recovery banner when review pipeline status is 'failed'.
 * - Reassure researchers that earlier checkpointed papers/PDFs are safely preserved in Neon DB.
 * - Call onRetry() to invoke POST /api/v1/reviews/{id}/retry and resume execution.
 */

import { useState } from "react";
import { AlertCircle, RefreshCw, ChevronDown, ChevronUp, X } from "lucide-react";

export interface RetryBannerProps {
  reviewId: string | number;
  failedStage?: string;
  errorMessage?: string;
  onRetry: () => Promise<void>;
  className?: string;
}

function formatStageName(stage?: string): string {
  if (!stage) return "Report Synthesis";
  const cleaned = stage.replace(/[_-]+/g, " ").trim();
  return cleaned
    .split(/\s+/)
    .map((w) => {
      const lower = w.toLowerCase();
      if (lower === "pdf") return "PDF";
      if (lower === "llm") return "LLM";
      return w.charAt(0).toUpperCase() + lower.slice(1);
    })
    .join(" ");
}

export default function RetryBanner({
  reviewId,
  failedStage = "Report Synthesis",
  errorMessage,
  onRetry,
  className = "",
}: RetryBannerProps) {
  const [isRetrying, setIsRetrying] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [retryError, setRetryError] = useState<string | null>(null);

  const displayStage = formatStageName(failedStage);

  const handleRetryClick = async () => {
    if (isRetrying) return;
    setIsRetrying(true);
    setRetryError(null);
    try {
      await onRetry();
    } catch (err: unknown) {
      let message = "Failed to resume pipeline. Please try again.";
      if (err instanceof Error) {
        if (
          err.message.includes("Failed to fetch") ||
          err.message.includes("NetworkError") ||
          err.message.toLowerCase().includes("network")
        ) {
          message = "Network error: Unable to reach the server. Please check your connection and try again.";
        } else {
          message = err.message;
        }
      } else if (typeof err === "string") {
        message = err;
      } else if (
        err &&
        typeof err === "object" &&
        "message" in err &&
        typeof (err as { message: unknown }).message === "string"
      ) {
        message = (err as { message: string }).message;
      }
      setRetryError(message);
    } finally {
      setIsRetrying(false);
    }
  };

  return (
    <div
      data-review-id={reviewId}
      role="alert"
      aria-live="polite"
      className={`rounded-2xl border border-rose-200 bg-rose-50/70 p-5 backdrop-blur-xs text-neutral-900 shadow-xs ${className}`}
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        {/* Left: Status & Reassurance */}
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-xl bg-rose-100 text-[var(--status-error)] shrink-0 mt-0.5">
            <AlertCircle className="w-5 h-5" />
          </div>
          <div>
            <h4 className="font-semibold text-sm sm:text-base text-rose-950">
              Pipeline Execution Paused at {displayStage}
            </h4>
            <p className="text-xs sm:text-sm text-rose-800/80 mt-0.5">
              Don't worry — your discovered papers, approvals, and extracted texts are safely
              preserved in the database checkpointer.
            </p>
          </div>
        </div>

        {/* Right: Action Button */}
        <div className="flex items-center gap-2 shrink-0">
          {errorMessage && (
            <button
              type="button"
              onClick={() => setShowDetails(!showDetails)}
              className="text-xs text-rose-700 hover:text-rose-900 underline flex items-center gap-1 cursor-pointer"
            >
              {showDetails ? "Hide Error" : "View Error"}
              {showDetails ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
          )}

          <button
            type="button"
            onClick={handleRetryClick}
            disabled={isRetrying}
            aria-busy={isRetrying}
            style={{ borderRadius: "var(--radius-sm)" }}
            className="flex items-center gap-2 px-4 py-2 bg-[var(--status-error-dark)] hover:bg-[var(--status-error-text)] text-white font-medium text-xs sm:text-sm shadow-xs transition hover:shadow cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RefreshCw className={`w-4 h-4 ${isRetrying ? "animate-spin" : ""}`} />
            {isRetrying ? "Resuming from Checkpoint..." : "Retry from Failed Step"}
          </button>
        </div>
      </div>

      {/* Expandable Technical Trace / Error */}
      {showDetails && errorMessage && (
        <div className="mt-4 pt-3 border-t border-rose-200/60 text-xs font-mono text-rose-900 bg-rose-100/50 p-3 rounded-lg overflow-x-auto whitespace-pre-wrap break-words">
          {errorMessage}
        </div>
      )}

      {retryError && (
        <div
          role="alert"
          className="mt-3 text-xs text-red-700 bg-white/90 p-3 rounded-lg border border-red-200 flex items-start justify-between gap-2 shadow-2xs"
        >
          <div className="flex items-start gap-2 flex-1">
            <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
            <span className="flex-1 font-medium">{retryError}</span>
          </div>
          <button
            type="button"
            onClick={() => setRetryError(null)}
            className="text-red-400 hover:text-red-700 p-0.5 rounded cursor-pointer transition-colors"
            aria-label="Dismiss error"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}
