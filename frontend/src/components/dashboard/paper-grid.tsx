import { cn } from "../../lib/utils";
import PaperSummaryCard, { type PaperSummary } from "../PaperSummaryCard";

export interface PaperGridProps {
  papers: PaperSummary[];
  selectedPaperIds: string[];
  onToggleSelect: (id: string) => void;
  onProceed: () => void;
  onFindMore: () => void;
  reviewId?: string | null;
  isProceeding?: boolean;
  isFindingMore?: boolean;
  errorMessage?: string | null;
  successMessage?: string | null;
  className?: string;
}

export default function PaperGrid({
  papers,
  selectedPaperIds,
  onToggleSelect,
  onProceed,
  onFindMore,
  reviewId,
  isProceeding = false,
  isFindingMore = false,
  errorMessage = null,
  successMessage = null,
  className = "",
}: PaperGridProps) {
  const selectedCount = selectedPaperIds.length;
  const isSubmitting = isProceeding || isFindingMore;
  const hasReviewId = Boolean(reviewId);

  return (
    <div className={cn("w-full space-y-5 animate-in fade-in duration-300", className)}>
      {/* Top Status & Search Control Bar */}
      <div className="w-full bg-white rounded-2xl border border-neutral-200/80 shadow-xs p-3.5 sm:p-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Papers found pill */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-[var(--color-pill-sky)] text-neutral-800">
            <span>Papers found</span>
            <span className="bg-white text-neutral-900 font-bold px-2 py-0.5 rounded-full text-xs shadow-xs">
              {papers.length}
            </span>
          </div>

          {/* Most relevant pill */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-[var(--color-pill-sky)] text-neutral-800">
            <span>Most relevant</span>
            <span className="bg-white text-neutral-900 font-bold px-2 py-0.5 rounded-full text-xs shadow-xs">
              {papers.length}
            </span>
          </div>
        </div>

        {/* Find More Papers Action Button */}
        <button
          type="button"
          onClick={onFindMore}
          disabled={!hasReviewId || isSubmitting}
          className={cn(
            "text-xs sm:text-sm font-semibold px-4 py-1.5 rounded-full shadow-xs transition-colors tracking-compact flex items-center gap-1.5",
            !hasReviewId || isSubmitting
              ? "bg-neutral-200 text-neutral-400 cursor-not-allowed"
              : "bg-[var(--color-danger)] hover:bg-[var(--color-danger-hover)] text-white cursor-pointer"
          )}
        >
          {isFindingMore ? (
            <>
              <svg className="animate-spin h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
              </svg>
              <span>Submitting...</span>
            </>
          ) : (
            <span>Find More Papers</span>
          )}
        </button>
      </div>

      {/* Main Candidate Papers Card Container */}
      <div className="w-full bg-white rounded-2xl border border-neutral-200/80 shadow-xs p-5 sm:p-7 space-y-6">
        {/* Header: Section Title + Selected Count Badge */}
        <div className="flex items-center justify-between pb-2 border-b border-neutral-100">
          <h2 className="font-serif text-xl sm:text-2xl font-bold text-neutral-900 tracking-compact">
            Most relevant papers
          </h2>

          {/* Selected Badge */}
          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-[var(--color-pill-sky)] text-neutral-800">
            <span>Selected</span>
            <span className="bg-white px-2 py-0.5 rounded-full text-neutral-900 font-bold shadow-xs">
              {selectedCount}
            </span>
            <span>of {papers.length}</span>
          </div>
        </div>

        {/* Informational Message: Review Session Missing Warning */}
        {!hasReviewId && (
          <div className="p-3.5 sm:p-4 rounded-xl bg-amber-50 border border-amber-200/80 text-amber-800 text-xs sm:text-sm flex items-start gap-2.5">
            <span className="text-amber-600 font-bold shrink-0">⚠️</span>
            <div>
              <p className="font-semibold">Review session not initialized</p>
              <p className="text-amber-700/90 text-xs mt-0.5">
                Start a research search above to establish a review session ID before approving papers.
              </p>
            </div>
          </div>
        )}

        {/* Error Alert Banner */}
        {errorMessage && (
          <div className="p-3.5 sm:p-4 rounded-xl bg-red-50 border border-red-200/80 text-red-800 text-xs sm:text-sm flex items-start gap-2.5 animate-in fade-in duration-200">
            <span className="text-red-600 font-bold shrink-0">✕</span>
            <div className="flex-1">
              <p className="font-semibold">Approval Error</p>
              <p className="text-red-700/90 text-xs mt-0.5">{errorMessage}</p>
            </div>
          </div>
        )}

        {/* Success Alert Banner */}
        {successMessage && (
          <div className="p-3.5 sm:p-4 rounded-xl bg-emerald-50 border border-emerald-200/80 text-emerald-800 text-xs sm:text-sm flex items-start gap-2.5 animate-in fade-in duration-200">
            <span className="text-emerald-600 font-bold shrink-0">✓</span>
            <div className="flex-1">
              <p className="font-semibold">Success</p>
              <p className="text-emerald-700/90 text-xs mt-0.5">{successMessage}</p>
            </div>
          </div>
        )}

        {/* Reusable Paper Summary Cards List */}
        <div className="space-y-4">
          {papers.map((paper) => {
            const isSelected = selectedPaperIds.includes(paper.id);
            return (
              <PaperSummaryCard
                key={paper.id}
                paper={{
                  ...paper,
                  isSelected,
                }}
                onToggleSelect={onToggleSelect}
              />
            );
          })}
        </div>

        {/* Action Footer for Selected Papers */}
        <div className="pt-4 border-t border-neutral-100 flex flex-col sm:flex-row items-center justify-between gap-4">
          <span className="text-xs text-neutral-500">
            {selectedCount} {selectedCount === 1 ? "paper" : "papers"} ready for automated literature synthesis &amp; citation analysis.
          </span>

          <button
            type="button"
            disabled={selectedCount === 0 || !hasReviewId || isSubmitting}
            onClick={onProceed}
            className={cn(
              "px-6 py-2.5 rounded-lg text-sm font-semibold tracking-compact transition-all shadow-sm flex items-center justify-center gap-2",
              selectedCount > 0 && hasReviewId && !isSubmitting
                ? "bg-neutral-900 hover:bg-black text-white hover:shadow-md cursor-pointer"
                : "bg-neutral-200 text-neutral-400 cursor-not-allowed"
            )}
          >
            {isProceeding ? (
              <>
                <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                </svg>
                <span>Submitting Approval...</span>
              </>
            ) : (
              <span>Proceed with Selected Papers ({selectedCount}) →</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
