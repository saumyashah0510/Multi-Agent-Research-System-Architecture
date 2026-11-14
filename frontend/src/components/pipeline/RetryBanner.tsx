/**
 * RetryBanner Component
 *
 * Assignee Task (Issue FE-13):
 * - Render an actionable recovery banner when review pipeline status is 'failed'.
 * - Reassure researchers that earlier checkpointed papers/PDFs are safely preserved in Neon DB.
 * - Call onRetry() to invoke POST /api/v1/reviews/{id}/retry and resume execution.
 */

import { useState } from "react";
import { AlertCircle, RefreshCw, ChevronDown, ChevronUp } from "lucide-react";

export interface RetryBannerProps {
  reviewId: string | number;
  failedStage?: string;
  errorMessage?: string;
  onRetry: () => Promise<void>;
  className?: string;
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

  const handleRetryClick = async () => {
    // TODO (Assignee - FE-13):
    // 1. Set isRetrying(true)
    // 2. Invoke onRetry()
    // 3. Catch errors and setRetryError
    // 4. Finally set isRetrying(false)
    setIsRetrying(true);
    setRetryError(null);
    try {
      await onRetry();
    } catch (err: any) {
      setRetryError(err.message || "Failed to resume pipeline. Please try again.");
    } finally {
      setIsRetrying(false);
    }
  };

  return (
    <div
      data-review-id={reviewId}
      className={`rounded-2xl border border-rose-200 bg-rose-50/70 p-5 backdrop-blur-xs text-neutral-900 shadow-xs ${className}`}
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        {/* Left: Status & Reassurance */}
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-xl bg-rose-100 text-rose-600 shrink-0 mt-0.5">
            <AlertCircle className="w-5 h-5" />
          </div>
          <div>
            <h4 className="font-semibold text-sm sm:text-base text-rose-950">
              Pipeline Execution Paused at {failedStage}
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
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-medium text-xs sm:text-sm shadow-xs transition hover:shadow cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isRetrying ? "animate-spin" : ""}`} />
            {isRetrying ? "Resuming from Checkpoint..." : "Retry from Failed Step"}
          </button>
        </div>
      </div>

      {/* Expandable Technical Trace / Error */}
      {showDetails && errorMessage && (
        <div className="mt-4 pt-3 border-t border-rose-200/60 text-xs font-mono text-rose-900 bg-rose-100/50 p-3 rounded-lg overflow-x-auto">
          {errorMessage}
        </div>
      )}

      {retryError && (
        <div className="mt-3 text-xs text-red-600 bg-white/60 p-2 rounded-lg border border-red-200">
          {retryError}
        </div>
      )}
    </div>
  );
}
