import { CircleCheck } from "lucide-react";
import { cn } from "../../lib/utils";
import PaperSummaryCard, { type PaperSummary } from "../PaperSummaryCard";

export interface PaperGridProps {
  papers: PaperSummary[];
  selectedPaperIds: string[];
  onToggleSelect: (id: string) => void;
  onProceed: () => void;
  isProceeding?: boolean;
  errorMessage?: string | null;
  successMessage?: string | null;
  className?: string;
}

export default function PaperGrid({
  papers,
  selectedPaperIds,
  onToggleSelect,
  onProceed,
  isProceeding = false,
  errorMessage = null,
  successMessage = null,
  className = "",
}: PaperGridProps) {
  const selectedCount = selectedPaperIds.length;

  return (
    <div className={cn("w-full space-y-5 animate-in fade-in duration-300", className)}>
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

        {/* Success Alert Banner: exactly matches relevance score and completed green color */}
        {successMessage && (
          <div className="p-3.5 sm:p-4 rounded-xl bg-[var(--color-success-light)] border border-[var(--color-success)]/30 text-[var(--color-success-dark)] text-xs sm:text-sm flex items-start gap-2.5 animate-in fade-in duration-200">
            <CircleCheck className="w-4 h-4 text-[var(--color-success)] shrink-0 stroke-[2.2] mt-0.5" />
            <div className="flex-1">
              <p className="font-semibold text-[var(--color-success-dark)]">Success</p>
              <p className="text-[var(--color-success-dark)]/85 text-xs mt-0.5">{successMessage}</p>
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
            disabled={selectedCount === 0 || isProceeding}
            onClick={onProceed}
            className={cn(
              "px-6 py-2.5 rounded-lg text-sm font-semibold tracking-compact transition-all shadow-sm flex items-center justify-center gap-2",
              selectedCount > 0 && !isProceeding
                ? "bg-neutral-900 hover:bg-black text-white hover:shadow-md cursor-pointer active:scale-95"
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
