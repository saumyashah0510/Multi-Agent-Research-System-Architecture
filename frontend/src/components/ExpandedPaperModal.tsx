import { useEffect, useRef, useCallback } from "react";
import { createPortal } from "react-dom";
import { FileText, Check, X } from "lucide-react";
import { FiExternalLink, FiAlertTriangle } from "react-icons/fi";
import { cn } from "../lib/utils";
import { type PaperSummary } from "./PaperSummaryCard";

export interface ExpandedPaperModalProps {
  paper: PaperSummary | null;
  isOpen: boolean;
  onClose: () => void;
  onToggleSelect?: (id: string) => void;
}

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

export default function ExpandedPaperModal({
  paper,
  isOpen,
  onClose,
  onToggleSelect,
}: ExpandedPaperModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const openerRef = useRef<HTMLElement | null>(null);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }

      if (e.key === "Tab" && dialogRef.current) {
        const focusable = Array.from(
          dialogRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
        );
        if (focusable.length === 0) return;

        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (!first || !last) return;

        if (e.shiftKey) {
          if (
            document.activeElement === first ||
            !dialogRef.current.contains(document.activeElement)
          ) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (
            document.activeElement === last ||
            !dialogRef.current.contains(document.activeElement)
          ) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    },
    [onClose]
  );

  useEffect(() => {
    if (!isOpen) return;

    // Capture the element that opened the modal for focus restore
    openerRef.current = document.activeElement as HTMLElement | null;

    document.addEventListener("keydown", handleKeyDown);
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    // Move focus into the dialog on next frame
    requestAnimationFrame(() => {
      if (dialogRef.current) {
        const firstFocusable =
          dialogRef.current.querySelector<HTMLElement>(FOCUSABLE_SELECTOR);
        if (firstFocusable) {
          firstFocusable.focus();
        } else {
          dialogRef.current.focus();
        }
      }
    });

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = originalOverflow;

      // Restore focus to the opener
      if (openerRef.current && typeof openerRef.current.focus === "function") {
        openerRef.current.focus();
      }
    };
  }, [isOpen, handleKeyDown]);

  if (!isOpen || !paper) return null;

  const isSelected = Boolean(paper.isSelected);
  const paperUrl =
    paper.url ||
    `https://scholar.google.com/scholar?q=${encodeURIComponent(paper.title)}`;

  const relevanceScore =
    typeof paper.relevanceScore === "number"
      ? Math.round(paper.relevanceScore)
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
      ref={dialogRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby="paper-modal-title"
      tabIndex={-1}
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/40 backdrop-blur-xs animate-in fade-in duration-200 outline-none"
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

        {/* Paper Title Heading */}
        <div className="pb-3 border-b border-[var(--border-subtle)]">
          <h2
            id="paper-modal-title"
            className="font-serif text-xl sm:text-2xl font-bold text-[var(--color-text-primary)] leading-tight tracking-compact"
          >
            {paper.title}
          </h2>
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
                style={{
                  backgroundColor: "var(--surface-card)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-sm)",
                  color: "var(--text-secondary)",
                }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors shrink-0 shadow-2xs hover:bg-[var(--tint-sky)] hover:text-[var(--sky-dark)] hover:border-[var(--sky-dark)] cursor-pointer"
              >
                <span>Open paper</span>
                <FiExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>

            {/* Inner Summary Box: Only Clean Generated Summary */}
            <div className="bg-[var(--color-surface)] rounded-2xl p-5 sm:p-6 border border-neutral-200/80 text-left">
              <div className="text-sm text-neutral-700 leading-relaxed font-normal space-y-3 font-sans">
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
                <span className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider block">
                  Authors
                </span>
                <span className="text-sm font-semibold text-[var(--text-primary)] leading-snug block mt-1">
                  {paper.authors || "Not specified"}
                </span>
              </div>

              <div>
                <span className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider block">
                  Published
                </span>
                <span className="text-sm font-semibold text-[var(--text-primary)] leading-snug block mt-1">
                  {paper.year || "Unknown"}
                </span>
              </div>

              <div>
                <span className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider block">
                  Journal
                </span>
                <span className="text-sm font-semibold text-[var(--text-primary)] leading-snug block mt-1">
                  {paper.venue || "Academic Publication"}
                </span>
              </div>
            </div>

            {/* Verification Warning Callout */}
            <div
              style={{
                borderRadius: "var(--radius-md)",
                backgroundColor: "var(--status-warning-light)",
                border: "1px solid color-mix(in srgb, var(--status-warning) 40%, transparent)",
              }}
              className="p-3 sm:p-3.5 mt-5 text-left"
            >
              <div className="flex items-center gap-1.5 mb-1">
                <FiAlertTriangle className="w-3.5 h-3.5 text-[var(--status-warning)] shrink-0" />
                <span className="text-sm font-bold text-[var(--text-primary)] leading-none">
                  Verify source
                </span>
              </div>
              <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                Verify the original paper before trusting or citing this summary.
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
