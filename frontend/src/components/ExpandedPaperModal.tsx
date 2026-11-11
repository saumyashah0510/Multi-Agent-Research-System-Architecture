import { useEffect } from "react";
import { createPortal } from "react-dom";
import { FileText, Check, X, ExternalLink } from "lucide-react";
import { cn } from "../lib/utils";
import { type PaperSummary } from "./PaperSummaryCard";

export interface ExpandedPaperModalProps {
  paper: PaperSummary | null;
  isOpen: boolean;
  onClose: () => void;
  onToggleSelect?: (id: string) => void;
}

export default function ExpandedPaperModal({
  paper,
  isOpen,
  onClose,
  onToggleSelect,
}: ExpandedPaperModalProps) {
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = originalOverflow;
    };
  }, [isOpen, onClose]);

  if (!isOpen || !paper) return null;

  const isSelected = Boolean(paper.isSelected);
  const paperUrl =
    paper.url ||
    `https://scholar.google.com/scholar?q=${encodeURIComponent(paper.title)}`;

  const relevanceScore =
    typeof paper.relevanceScore === "number"
      ? paper.relevanceScore <= 1
        ? Math.round(paper.relevanceScore * 100)
        : Math.round(paper.relevanceScore)
      : null;

  const summaryContent =
    paper.screeningRationale ||
    paper.rationale ||
    paper.abstract ||
    "No summary available for this paper.";

  // Split multi-paragraph content cleanly
  const paragraphs = summaryContent
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean);

  const modalContent = (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="paper-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/40 backdrop-blur-xs animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className={cn(
          "bg-white rounded-3xl p-6 sm:p-8 max-w-3xl lg:max-w-4xl w-full max-h-[90vh] overflow-y-auto shadow-2xl border border-neutral-200/90 space-y-5 animate-in zoom-in-95 duration-200"
        )}
      >
        {/* Header Tags & Close Button */}
        <div className="flex items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            {/* Paper details badge */}
            <span
              style={{ borderRadius: "var(--radius-sm)" }}
              className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium bg-[var(--color-surface)] text-[var(--color-text-secondary)] border border-neutral-200/80"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Paper details</span>
            </span>

            {/* Selected paper badge */}
            {isSelected ? (
              <button
                type="button"
                onClick={() => onToggleSelect?.(paper.id)}
                title="Click to toggle selection"
                style={{ borderRadius: "var(--radius-sm)" }}
                className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-semibold bg-[var(--tint-mint)] text-[var(--color-success-dark)] border border-[var(--color-success-border)] cursor-pointer hover:opacity-90 transition-opacity"
              >
                <Check className="w-3.5 h-3.5 stroke-[2.5]" />
                <span>Selected paper</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={() => onToggleSelect?.(paper.id)}
                style={{ borderRadius: "var(--radius-sm)" }}
                className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium bg-neutral-100 hover:bg-neutral-200 text-neutral-700 transition-colors cursor-pointer"
              >
                <span>Select for review</span>
              </button>
            )}

            {/* Relevance Score Badge displayed once near Selected paper */}
            {relevanceScore !== null && (
              <span
                style={{ borderRadius: "var(--radius-sm)" }}
                className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-semibold bg-[var(--tint-mint)] text-[var(--color-success-dark)] border border-[var(--color-success-border)]"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-success)] shrink-0" />
                <span>{relevanceScore}% Relevance</span>
              </span>
            )}
          </div>

          {/* Close Button */}
          <button
            type="button"
            onClick={onClose}
            aria-label="Close details"
            style={{ borderRadius: "var(--radius-sm)" }}
            className="p-1.5 text-neutral-400 hover:text-neutral-900 hover:bg-neutral-100 border border-neutral-200 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Paper Title & Authors Heading */}
        <div>
          <h2
            id="paper-modal-title"
            className="font-serif text-xl sm:text-2xl font-bold text-[var(--color-text-primary)] leading-tight tracking-compact"
          >
            {paper.title}
          </h2>
          <p className="text-xs text-[var(--color-text-secondary)] mt-2 pb-4 border-b border-neutral-100 font-sans">
            {paper.authors} · {paper.year} · {paper.venue}
          </p>
        </div>

        {/* Content Layout: 2 Columns with Increased Width for Expanded Summary */}
        <div className="grid grid-cols-1 md:grid-cols-[1fr_210px] gap-6 sm:gap-8 items-start pt-1">
          {/* Left Column: Expanded Summary */}
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <h3 className="font-serif text-base sm:text-lg font-bold text-[var(--color-text-primary)] tracking-compact">
                Expanded summary
              </h3>
              <a
                href={paperUrl}
                target="_blank"
                rel="noopener noreferrer"
                style={{ borderRadius: "var(--radius-sm)" }}
                className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium bg-[var(--tint-sky)] text-[var(--color-pill-sky-text)] hover:bg-[var(--color-pill-sky)] transition-colors border border-[var(--color-pill-sky)] shrink-0"
              >
                <span>Open paper</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>

            {/* Inner Summary Box: Only Clean Generated Summary */}
            <div className="bg-[var(--color-surface)] rounded-2xl p-5 sm:p-6 border border-neutral-200/80 text-left">
              <div className="text-[13px] sm:text-[13.5px] text-neutral-700 leading-relaxed font-normal space-y-3 font-sans">
                {paragraphs.length > 0 ? (
                  paragraphs.map((para, idx) => (
                    <p key={idx}>{para}</p>
                  ))
                ) : (
                  <p>{summaryContent}</p>
                )}
              </div>
            </div>
          </div>

          {/* Right Column: At a glance */}
          <div className="space-y-4">
            <h3 className="font-serif text-sm sm:text-base font-bold text-[var(--color-text-primary)] tracking-compact">
              At a glance
            </h3>

            <div className="space-y-3.5 text-left">
              <div>
                <span className="text-[10px] sm:text-[10.5px] font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider block">
                  Authors
                </span>
                <span className="text-xs sm:text-[13px] font-medium text-neutral-800 leading-snug block mt-0.5">
                  {paper.authors || "Not specified"}
                </span>
              </div>

              <div>
                <span className="text-[10px] sm:text-[10.5px] font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider block">
                  Published
                </span>
                <span className="text-xs sm:text-[13px] font-medium text-neutral-800 leading-snug block mt-0.5">
                  {paper.year || "Unknown"}
                </span>
              </div>

              <div>
                <span className="text-[10px] sm:text-[10.5px] font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider block">
                  Journal
                </span>
                <span className="text-xs sm:text-[13px] font-medium text-neutral-800 leading-snug block mt-0.5">
                  {paper.venue || "Academic Publication"}
                </span>
              </div>
            </div>

            {/* Read in context callout */}
            <div className="bg-[var(--color-surface)] rounded-xl p-3 sm:p-3.5 border border-neutral-200/80 mt-5 text-left">
              <span className="text-xs font-bold text-[var(--color-text-primary)] block">
                Read in context
              </span>
              <p className="text-[11px] text-[var(--color-text-secondary)] leading-tight mt-1">
                Check the original paper before using it as evidence in your review.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  return typeof document !== "undefined"
    ? createPortal(modalContent, document.body)
    : modalContent;
}
