import { useState } from "react";
import { ExternalLink, Check } from "lucide-react";
import { cn } from "../lib/utils";
import ExpandedPaperModal from "./ExpandedPaperModal";

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
  rationale?: string;
  screeningRationale?: string;
}

export interface PaperSummaryCardProps {
  paper: PaperSummary;
  onToggleSelect?: (id: string) => void;
  onOpenDetail?: (paper: PaperSummary) => void;
  className?: string;
}

export default function PaperSummaryCard({
  paper,
  onToggleSelect,
  onOpenDetail,
  className = "",
}: PaperSummaryCardProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const isSelected = Boolean(paper.isSelected);
  const paperUrl =
    paper.url ||
    `https://scholar.google.com/scholar?q=${encodeURIComponent(paper.title)}`;

  const relevanceScore =
    typeof paper.relevanceScore === "number"
      ? Math.round(paper.relevanceScore)
      : null;

  const summaryText =
    paper.screeningRationale ||
    paper.rationale ||
    paper.abstract ||
    "No summary available for this paper.";

  const maxChars = 190;
  const isTruncated = summaryText.length > maxChars;
  const previewText = isTruncated
    ? `${summaryText.slice(0, maxChars).trim()}...`
    : summaryText;

  const handleCardClick = () => {
    if (onOpenDetail) {
      onOpenDetail(paper);
    } else {
      setIsModalOpen(true);
    }
  };

  return (
    <>
      <div
        role="button"
        tabIndex={0}
        onClick={handleCardClick}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            if (e.target === e.currentTarget) {
              e.preventDefault();
              handleCardClick();
            }
          }
        }}
        className={cn(
          "w-full rounded-2xl p-4 sm:p-5 md:p-6 border transition-all cursor-pointer text-left bg-white select-none",
          isSelected
            ? "border-[var(--color-success)]/60 shadow-xs ring-1 ring-[var(--color-success)]/25"
            : "border-neutral-200/90 hover:border-neutral-300 hover:shadow-xs",
          className
        )}
      >
        {/* Top Header: Checkbox + Title + Paper ↗ Button */}
        <div className="flex items-start gap-3 sm:gap-3.5">
          {/* Accessible Checkbox */}
          <button
            type="button"
            role="checkbox"
            aria-checked={isSelected}
            aria-label={isSelected ? `Deselect ${paper.title}` : `Select ${paper.title}`}
            onClick={(e) => {
              e.stopPropagation();
              onToggleSelect?.(paper.id);
            }}
            className="mt-0.5 shrink-0 cursor-pointer focus:outline-none"
          >
            {isSelected ? (
              <div className="w-5 h-5 rounded-[6px] bg-[var(--color-success)] flex items-center justify-center text-white shadow-xs">
                <Check className="w-3.5 h-3.5 text-white stroke-[3]" />
              </div>
            ) : (
              <div className="w-5 h-5 rounded-[6px] border-2 border-neutral-300 bg-white hover:border-neutral-400 transition-colors" />
            )}
          </button>

          {/* Title and Direct Paper Link */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-3">
              <h3 className="font-serif text-sm sm:text-base md:text-lg font-bold text-[var(--color-text-primary)] tracking-compact leading-snug">
                {paper.title}
              </h3>

              {/* Right Side: Relevance Score + Dark Blue Paper Link Icon (no "Paper" text) */}
              <div className="flex items-center gap-2 shrink-0 -mt-0.5">
                {relevanceScore !== null && (
                  <span
                    style={{ borderRadius: "var(--radius-sm)" }}
                    className="inline-flex items-center gap-1.5 px-2.5 h-7 text-xs font-semibold bg-[var(--tint-mint)] text-[var(--color-success-dark)] border border-[var(--color-success-border)] select-none"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-success)] shrink-0" />
                    <span>{relevanceScore}% Relevance</span>
                  </span>
                )}

                <a
                  href={paperUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  title="Open paper in new tab"
                  aria-label={`Open direct paper link for ${paper.title}`}
                  style={{ borderRadius: "var(--radius-sm)" }}
                  className="w-7 h-7 inline-flex items-center justify-center text-[var(--color-sky-dark)] hover:text-[#005fa8] bg-white hover:bg-[var(--tint-sky)] transition-colors border border-neutral-200/90 hover:border-[var(--color-pill-sky)] shrink-0 shadow-2xs"
                >
                  <ExternalLink className="w-3.5 h-3.5 stroke-[2.25]" />
                </a>
              </div>
            </div>

            {/* Metadata row: Authors et al. · Year · Journal Name */}
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1 text-[11px] sm:text-xs text-[var(--color-text-secondary)] font-sans">
              <span>
                {paper.authors} · {paper.year} · {paper.venue}
              </span>
            </div>

            {/* Supporting Summary Box (matching design image) */}
            <div className="bg-[var(--tint-sky)] border border-[var(--color-pill-sky)] rounded-xl p-3 sm:p-4 mt-3 transition-colors hover:border-[#90cdf4]">
              <span className="text-xs font-semibold text-[var(--color-sky-dark)] block mb-1">
                Supporting summary
              </span>
                <p className="text-xs sm:text-sm text-[var(--color-pill-sky-text)] leading-relaxed font-sans">
                  <span className="italic">{previewText}</span>{" "}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleCardClick();
                    }}
                    className="not-italic font-semibold text-[var(--color-sky-dark)] hover:underline inline cursor-pointer whitespace-nowrap"
                  >
                    see more
                  </button>
                </p>
            </div>
          </div>
        </div>
      </div>

      {/* Expanded Paper Detail Modal */}
      <ExpandedPaperModal
        paper={paper}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onToggleSelect={onToggleSelect}
      />
    </>
  );
}
