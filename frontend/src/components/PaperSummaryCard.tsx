import { ExternalLink, Check } from "lucide-react";
import { cn } from "../lib/utils";

export interface PaperSummary {
  id: string;
  title: string;
  authors: string;
  year: number | string;
  venue: string;
  abstract: string;
  tags?: string[];
  relevanceScore?: number;
  isSelected?: boolean;
  url?: string;
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
  const relevance = paper.relevanceScore ?? 98;
  const paperUrl =
    paper.url ||
    `https://scholar.google.com/scholar?q=${encodeURIComponent(paper.title)}`;

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
            <div className="w-5 h-5 rounded-full bg-[var(--color-success)] flex items-center justify-center text-white shadow-xs">
              <Check className="w-3.5 h-3.5 text-white stroke-[3]" />
            </div>
          ) : (
            // Hollow outline circle for unselected
            <div className="w-5 h-5 rounded-full border-2 border-neutral-300 bg-transparent hover:border-neutral-400 hover:bg-neutral-50 transition-colors" />
          )}
        </button>

        {/* Paper Details */}
        <div className="flex-1 space-y-1 sm:space-y-1.5 min-w-0">
          {/* Top Header: Title and Right Upper Corner Direct Link Icon */}
          <div className="flex items-start justify-between gap-3">
            <h3 className="font-serif text-sm sm:text-base md:text-lg font-bold text-neutral-900 tracking-compact leading-snug">
              {paper.title}
            </h3>

            {/* Direct Link Icon cleanly placed in the top right corner */}
            <a
              href={paperUrl}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              title="Open publication website in new tab"
              aria-label={`Open direct paper link for ${paper.title}`}
              className="p-1 rounded-md text-neutral-400 hover:text-neutral-900 hover:bg-neutral-100 transition-colors shrink-0 -mt-0.5 -mr-0.5"
            >
              <ExternalLink className="w-4 h-4" />
            </a>
          </div>

          {/* Authors and Venue Metadata */}
          <p className="text-[11px] sm:text-xs text-neutral-500 font-sans-ui truncate sm:whitespace-normal">
            {paper.authors} · {paper.year} · {paper.venue}
          </p>

          {/* Summary / Abstract Text: Hidden on mobile, shown on tablet/desktop */}
          <p className="hidden sm:block text-xs sm:text-sm text-neutral-700 leading-relaxed font-sans-ui pt-1 font-normal">
            {paper.abstract}
          </p>

          {/* Bottom Row: Only Relevance Score Badge positioned at the bottom left */}
          <div className="pt-2 sm:pt-3 flex items-center justify-start">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10.5px] sm:text-[11px] font-semibold bg-[var(--color-success-light)] text-[var(--color-success-dark)] border border-[var(--color-success)]/30 shrink-0">
              {relevance}% Relevance
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
