import { cn } from "../lib/utils";

export interface PaperSummary {
  id: string;
  title: string;
  authors: string;
  year: number | string;
  venue: string;
  abstract: string;
  tags: string[];
  relevanceScore?: number;
  isSelected?: boolean;
}

export interface PaperSummaryCardProps {
  paper: PaperSummary;
  onToggleSelect?: (id: string) => void;
  className?: string;
}

export default function PaperSummaryCard({
  paper,
  onToggleSelect,
  className = "",
}: PaperSummaryCardProps) {
  const isSelected = Boolean(paper.isSelected);
  const relevance = paper.relevanceScore ?? 95;

  return (
    <div
      onClick={() => onToggleSelect?.(paper.id)}
      className={cn(
        "w-full rounded-2xl p-4 sm:p-5 md:p-6 border transition-all cursor-pointer text-left bg-white",
        isSelected
          ? "border-[var(--color-success)]/50 shadow-xs ring-1 ring-[var(--color-success)]/25"
          : "border-neutral-200/90 hover:border-neutral-300 hover:shadow-xs",
        className
      )}
    >
      <div className="flex items-start gap-3 sm:gap-3.5">
        {/* Selection Indicator Checkbox */}
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onToggleSelect?.(paper.id);
          }}
          aria-label={isSelected ? "Deselect paper" : "Select paper"}
          className="mt-0.5 shrink-0 cursor-pointer focus:outline-none"
        >
          {isSelected ? (
            // Solid green circle for selected
            <div className="w-4.5 h-4.5 sm:w-5 sm:h-5 rounded-full bg-[var(--color-success)] flex items-center justify-center text-white shadow-xs">
              <svg
                className="w-2.5 h-2.5 sm:w-3 sm:h-3 stroke-[3]"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
          ) : (
            // Hollow green outline circle for unselected
            <div className="w-4.5 h-4.5 sm:w-5 sm:h-5 rounded-full border-2 border-[var(--color-success)] bg-transparent hover:bg-emerald-50 transition-colors" />
          )}
        </button>

        {/* Paper Details */}
        <div className="flex-1 space-y-1 sm:space-y-1.5 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <h3 className="font-serif text-sm sm:text-base md:text-lg font-bold text-neutral-900 tracking-compact leading-snug">
              {paper.title}
            </h3>

            {/* Relevance Percentage Placeholder Badge */}
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] sm:text-[11px] font-semibold bg-[var(--color-success-light)] text-[var(--color-success-dark)] border border-[var(--color-success)]/30 shrink-0">
              {relevance}% Relevance
            </span>
          </div>

          {/* Authors and Venue Metadata */}
          <p className="text-[11px] sm:text-xs text-neutral-500 font-sans-ui truncate sm:whitespace-normal">
            {paper.authors} · {paper.year} · {paper.venue}
          </p>

          {/* Summary / Abstract Text: Hidden on mobile, shown on tablet/desktop */}
          <p className="hidden sm:block text-xs sm:text-sm text-black leading-relaxed font-sans-ui pt-1 font-normal">
            {paper.abstract}
          </p>

          {/* Metadata Badges: essential on mobile, full on desktop */}
          <div className="flex flex-wrap items-center gap-1.5 pt-1 sm:pt-2">
            {paper.tags.map((tag, idx) => (
              <span
                key={tag}
                className={cn(
                  "px-2 sm:px-2.5 py-0.5 rounded-full text-[10px] sm:text-[11px] font-medium bg-neutral-100 text-neutral-700 border border-neutral-200/60",
                  idx > 1 && "hidden sm:inline-flex"
                )}
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
