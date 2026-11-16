/**
 * ReviewDetail Page Component (/review/:reviewId)
 *
 * Assignee Task (Issues FE-06 / FE-07 / FE-08):
 * - Extract reviewId from route params (useParams)
 * - Fetch initial review status via GET /api/v1/reviews/{reviewId}
 * - Stream remaining stages 5 to 9 via WebSocket connection to /api/v1/ws/reviews/{reviewId}
 * - Display review topic header and session status
 * - Mount downstream pipeline progress tracker (Stages 5 to 9)
 * - Integrate accessible tab switcher (Synthesis Report | Knowledge Graph) when isCompleted is true
 * - Pass synthesized review to SynthesisReportViewer and methodology_matrix to MethodologyMatrix
 */

import React, { useState, useEffect, useCallback } from "react";
import { useParams, useSearchParams, Link } from "react-router-dom";
import {
  FileText,
  Download,
  Check,
  Loader2,
  RefreshCw,
  AlertCircle,
  Network,
  ArrowLeft,
} from "lucide-react";
import { cn } from "../lib/utils";
import DownstreamProgress from "../components/pipeline/DownstreamProgress";
import RetryBanner from "../components/pipeline/RetryBanner";
import SynthesisReportViewer, {
  formatReportAsMarkdown,
} from "../components/dashboard/SynthesisReportViewer";
import CitationKnowledgeGraph from "../components/graph/CitationKnowledgeGraph";
import { getReviewStatus, getReviewPdfDownloadUrl, retryReviewPipeline } from "../lib/api";
import { SynthesizedReview } from "../types";

const ReviewDetailInner: React.FC = () => {
  const { reviewId } = useParams<{ reviewId: string }>();
  const [searchParams] = useSearchParams();
  const tabParam = (searchParams.get("tab") || "").toLowerCase();

  const [isCompleted, setIsCompleted] = useState(false);
  const [isFailed, setIsFailed] = useState(false);
  const [failedMessage, setFailedMessage] = useState<string | null>(null);
  const [failedStage, setFailedStage] = useState<string | null>(null);
  const [retryEpoch, setRetryEpoch] = useState(0);
  const isGraphView = tabParam === "graph";
  const [copiedMarkdown, setCopiedMarkdown] = useState(false);
  const [reviewTopic, setReviewTopic] = useState<string | null>(null);
  const [reviewStatus, setReviewStatus] = useState<string | null>(null);
  const [synthesizedReport, setSynthesizedReport] = useState<SynthesizedReview | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [isRetrying, setIsRetrying] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Load review status and synthesized report via GET /api/v1/reviews/{reviewId}
  const loadReviewData = useCallback(async () => {
    if (!reviewId) return null;
    try {
      const data = await getReviewStatus(reviewId);
      if (data?.query || data?.user_query) {
        setReviewTopic(data.query || data.user_query);
      }
      if (data?.status) {
        setReviewStatus(data.status);
      }
      const normStatus = String(data?.status || "").toLowerCase();
      if (normStatus === "completed" || normStatus === "synthesis_completed") {
        setIsCompleted(true);
        setIsFailed(false);
        setFailedMessage(null);
        setFailedStage(null);
        if (data?.synthesized_review) {
          setSynthesizedReport(data.synthesized_review);
          setFetchError(null);
        }
      } else if (normStatus === "failed") {
        setIsFailed(true);
        setFailedMessage(
          data?.error_message ||
          "Pipeline was interrupted. Click 'Retry from Failed Step' to resume from your latest checkpoint."
        );
        const stage = data?.failed_stage || data?.current_step || data?.stage;
        if (stage) {
          setFailedStage(stage);
        }
      } else {
        setIsFailed(false);
      }
      return data;
    } catch (err) {
      console.warn("Could not retrieve review status:", err);
      return null;
    }
  }, [reviewId]);

  useEffect(() => {
    if (!reviewId) return;

    // Reset review state on reviewId change to avoid displaying stale data
    setReviewTopic(null);
    setReviewStatus(null);
    setSynthesizedReport(null);
    setIsCompleted(false);
    setIsFailed(false);
    setFailedMessage(null);
    setFailedStage(null);
    setRetryCount(0);
    setRetryEpoch(0);
    setFetchError(null);

    let isMounted = true;
    loadReviewData().then((data) => {
      if (!isMounted || !data) return;
    });

    return () => {
      isMounted = false;
    };
  }, [reviewId, loadReviewData]);

  const handlePipelineComplete = useCallback(() => {
    setIsCompleted(true);
    setRetryCount(0);
    setFetchError(null);
    loadReviewData();
  }, [loadReviewData]);

  const handlePipelineFailed = useCallback((stageName?: string, errorMsg?: string) => {
    setIsFailed(true);
    if (stageName) setFailedStage(stageName);
    if (errorMsg) setFailedMessage(errorMsg);
  }, []);

  const handleRetryPipeline = async () => {
    if (!reviewId) return;
    await retryReviewPipeline(reviewId);
    setIsFailed(false);
    setReviewStatus("processing");
    setRetryEpoch((prev) => prev + 1);
    await loadReviewData();
  };

  // Auto-retry polling if pipeline completed but synthesized_review is not yet available
  useEffect(() => {
    if (!isCompleted || synthesizedReport || retryCount >= 5) return;

    const timer = setTimeout(async () => {
      setRetryCount((prev) => prev + 1);
      const res = await loadReviewData();
      if (!res?.synthesized_review && retryCount + 1 >= 5) {
        setFetchError("Synthesis report is taking longer than expected to persist.");
      }
    }, 3000);

    return () => clearTimeout(timer);
  }, [isCompleted, synthesizedReport, retryCount, loadReviewData]);

  const handleManualRetry = async () => {
    setIsRetrying(true);
    setFetchError(null);
    try {
      const res = await loadReviewData();
      if (!res?.synthesized_review) {
        setFetchError("Report not available yet. Please try again in a few moments.");
      }
    } finally {
      setIsRetrying(false);
    }
  };

  const activeReport: SynthesizedReview | null = synthesizedReport;

  const handleExportMarkdown = () => {
    if (!activeReport) return;
    const markdown = formatReportAsMarkdown(activeReport);
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const slug = (activeReport.title || reviewId || "literature-review")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "")
      .slice(0, 60);
    link.href = url;
    link.download = `${slug || "literature-review"}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(markdown).catch(() => { });
    }
    setCopiedMarkdown(true);
    window.setTimeout(() => setCopiedMarkdown(false), 2000);
  };

  return (
    <div
      style={{ maxWidth: "var(--container-max-width)" }}
      className="w-full max-w-[var(--container-max-width)] mx-auto px-4 sm:px-6 py-8 space-y-6"
    >
      {/* Back to Past Reviews Link */}
      <div>
        <Link
          to="/dashboard?tab=report"
          style={{
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--surface-card)",
            borderColor: "var(--border-default)",
            color: "var(--text-primary)",
          }}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold border hover:bg-[var(--surface-muted)] transition-colors shadow-2xs cursor-pointer select-none"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to past reviews</span>
        </Link>
      </div>

      {/* Session Header Bar */}
      <div className="border-b border-neutral-200/80 pb-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl sm:text-3xl font-serif font-bold text-neutral-900 leading-tight">
            {activeReport?.title || reviewTopic || "Literature Review Session"}
          </h1>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {isCompleted && (
            <>
              <a
                href={getReviewPdfDownloadUrl(reviewId || "")}
                target="_blank"
                rel="noopener noreferrer"
                style={{ borderRadius: "var(--radius-sm)" }}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-neutral-900 text-white text-xs font-semibold hover:bg-neutral-800 transition-colors shadow-xs"
                title="Download PDF Synthesis Report"
              >
                <Download className="w-3.5 h-3.5" />
                <span>PDF</span>
              </a>

              {activeReport && (
                <button
                  type="button"
                  onClick={handleExportMarkdown}
                  style={{ borderRadius: "var(--radius-sm)" }}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-white border border-neutral-200 text-neutral-800 text-xs font-semibold hover:bg-neutral-50 transition-colors cursor-pointer shadow-xs"
                  title="Download Markdown report and copy to clipboard"
                >
                  {copiedMarkdown ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-[var(--color-success)]" />
                      <span>Exported</span>
                    </>
                  ) : (
                    <>
                      <FileText className="w-3.5 h-3.5" />
                      <span>Markdown</span>
                    </>
                  )}
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {/* Mid-Pipeline Retry Banner (Issue FE-13) */}
      {isFailed && (
        <RetryBanner
          reviewId={reviewId || ""}
          failedStage={failedStage || undefined}
          errorMessage={failedMessage || undefined}
          onRetry={handleRetryPipeline}
          className="mb-6"
        />
      )}

      {/* Downstream Checkpoints Tracker (Stages 5 to 9) */}
      <DownstreamProgress
        key={`${reviewId}-${retryEpoch}`}
        reviewId={reviewId}
        isCompleted={isCompleted}
        initialStatus={reviewStatus || undefined}
        onComplete={handlePipelineComplete}
        onFailed={handlePipelineFailed}
      />

      {/* Synthesis Report or Citation Graph View */}
      {isCompleted && (
        <div className="space-y-5 animate-in fade-in duration-300">
          {/* Tab Switcher */}
          <div className="flex items-center gap-2 border-b border-[var(--border-subtle)] pb-3">
            <Link
              to={`/review/${reviewId}`}
              style={{
                borderRadius: "var(--radius-sm)",
                backgroundColor: !isGraphView ? "var(--tint-sky)" : "var(--surface-card)",
                borderColor: !isGraphView ? "var(--sky-dark)" : "var(--border-default)",
                color: !isGraphView ? "var(--sky-dark)" : "var(--text-secondary)",
              }}
              className={cn(
                "inline-flex items-center gap-1.5 px-3 py-1.5 text-xs sm:text-sm font-semibold border transition-colors select-none",
                !isGraphView
                  ? "shadow-2xs"
                  : "hover:bg-[var(--tint-sky)]/40 hover:text-[var(--sky-dark)]"
              )}
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Synthesis Report</span>
            </Link>
            <Link
              to={`/review/${reviewId}?tab=graph`}
              style={{
                borderRadius: "var(--radius-sm)",
                backgroundColor: isGraphView ? "var(--tint-sky)" : "var(--surface-card)",
                borderColor: isGraphView ? "var(--sky-dark)" : "var(--border-default)",
                color: isGraphView ? "var(--sky-dark)" : "var(--text-secondary)",
              }}
              className={cn(
                "inline-flex items-center gap-1.5 px-3 py-1.5 text-xs sm:text-sm font-semibold border transition-colors select-none",
                isGraphView
                  ? "shadow-2xs"
                  : "hover:bg-[var(--tint-sky)]/40 hover:text-[var(--sky-dark)]"
              )}
            >
              <Network className="w-3.5 h-3.5" />
              <span>Knowledge Graph</span>
            </Link>
          </div>

          {isGraphView ? (
            <CitationKnowledgeGraph reviewId={reviewId || ""} />
          ) : activeReport ? (
            <SynthesisReportViewer report={activeReport} />
          ) : (
            <div className="w-full bg-white rounded-2xl border border-neutral-200/90 shadow-xs p-8 text-center space-y-4">
              <div className="w-10 h-10 mx-auto rounded-full bg-[var(--tint-lavender)] flex items-center justify-center text-[var(--lavender-dark)]">
                {fetchError && retryCount >= 5 ? (
                  <AlertCircle className="w-5 h-5 text-[var(--status-warning)]" />
                ) : (
                  <Loader2 className="w-5 h-5 animate-spin" />
                )}
              </div>
              <div>
                <h3 className="font-serif text-lg font-bold text-neutral-900">
                  {fetchError && retryCount >= 5
                    ? "Report Generation in Progress"
                    : "Finalizing Literature Synthesis..."}
                </h3>
                <p className="text-xs text-neutral-500 max-w-md mx-auto mt-1">
                  {fetchError ||
                    "Downstream agents completed analysis. The structured synthesis report and comparative matrix are currently being assembled."}
                </p>
              </div>
              <div>
                <button
                  type="button"
                  onClick={handleManualRetry}
                  disabled={isRetrying}
                  style={{ borderRadius: "var(--radius-sm)" }}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-[var(--tint-lavender)] hover:bg-[var(--tint-lavender)]/80 text-[var(--lavender-dark)] text-xs font-semibold transition-colors cursor-pointer disabled:opacity-50"
                >
                  <RefreshCw className={cn("w-3.5 h-3.5", isRetrying && "animate-spin")} />
                  <span>{isRetrying ? "Checking..." : "Refresh Report"}</span>
                </button>
              </div>
            </div>
          )}
        </div>
      )}

    </div>
  );
};

export const ReviewDetail: React.FC = () => {
  const { reviewId } = useParams<{ reviewId: string }>();
  return <ReviewDetailInner key={reviewId} />;
};

export default ReviewDetail;
