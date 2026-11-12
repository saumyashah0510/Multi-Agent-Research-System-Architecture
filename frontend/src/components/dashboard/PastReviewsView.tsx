import { useState, useEffect, useMemo } from "react";
import { Search, Loader2, ArrowRight, Download } from "lucide-react";
import { fetchPastReviews, getReviewPdfDownloadUrl } from "../../lib/api";
import { ReviewHistoryItem } from "../../types";
import { cn } from "../../lib/utils";

export type TargetSection = "papers" | "report" | "chat";

export interface PastReviewsViewProps {
  targetSection: TargetSection;
  onSelectReview: (review: ReviewHistoryItem) => void;
  onStartNewResearch: () => void;
}

function normalizeStatus(rawStatus: string | undefined): ReviewHistoryItem["status"] {
  const s = String(rawStatus || "").toLowerCase();
  if (s === "completed" || s === "synthesis_completed") return "completed";
  if (s === "awaiting_approval" || s === "awaiting_user_input") return "awaiting_approval";
  if (s === "failed" || s === "error") return "failed";
  return "pending";
}

function formatCreatedDate(isoDate?: string): string {
  if (!isoDate) return "Recently";
  const d = new Date(isoDate);
  if (Number.isNaN(d.getTime())) return "Recently";
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function PastReviewsView({
  targetSection,
  onSelectReview,
  onStartNewResearch,
}: PastReviewsViewProps) {
  const [reviews, setReviews] = useState<ReviewHistoryItem[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);

    fetchPastReviews(20)
      .then((data) => {
        if (!isMounted) return;
        const list = Array.isArray(data)
          ? data.map((item: any) => ({
              ...item,
              id: String(item.id),
              query: item.query || item.user_query || "Untitled Literature Review",
              status: normalizeStatus(item.status),
            }))
          : [];
        setReviews(list);
      })
      .catch(() => {
        if (!isMounted) return;
        setReviews([]);
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const filteredReviews = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return reviews;
    return reviews.filter((r) => (r.query || "").toLowerCase().includes(q));
  }, [reviews, searchQuery]);

  const sectionActionLabel =
    targetSection === "chat"
      ? "Open Chat"
      : targetSection === "papers"
      ? "View Papers"
      : "Open Report";

  const renderStatusBadge = (status: ReviewHistoryItem["status"]) => {
    switch (status) {
      case "completed":
        return (
          <span
            style={{ borderRadius: "var(--radius-sm)" }}
            className="inline-flex items-center gap-1.5 px-2.5 py-0.5 text-xs font-semibold bg-[var(--tint-mint)] text-[var(--color-success-dark)] border border-[var(--color-success-border)] shrink-0"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-success)] shrink-0" />
            <span>Completed</span>
          </span>
        );
      case "awaiting_approval":
        return (
          <span
            style={{ borderRadius: "var(--radius-sm)" }}
            className="inline-flex items-center gap-1.5 px-2.5 py-0.5 text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200/90 shrink-0"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0" />
            <span>Awaiting Approval</span>
          </span>
        );
      case "failed":
        return (
          <span
            style={{ borderRadius: "var(--radius-sm)" }}
            className="inline-flex items-center gap-1.5 px-2.5 py-0.5 text-xs font-semibold bg-red-50 text-red-700 border border-red-200 shrink-0"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-red-500 shrink-0" />
            <span>Failed</span>
          </span>
        );
      default:
        return (
          <span
            style={{ borderRadius: "var(--radius-sm)" }}
            className="inline-flex items-center gap-1.5 px-2.5 py-0.5 text-xs font-semibold bg-[var(--tint-sky)] text-[var(--color-sky-dark)] border border-[var(--color-pill-sky)] shrink-0"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-sky-dark)] animate-pulse shrink-0" />
            <span>Processing</span>
          </span>
        );
    }
  };

  return (
    <div className="w-full pt-8 sm:pt-12 pb-16 space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div>
        <h1 className="font-serif text-2xl sm:text-3xl font-bold text-neutral-900 tracking-compact">
          Past reviews &amp; papers
        </h1>
        <p className="font-sans text-xs sm:text-sm text-neutral-600 mt-1.5">
          Open a previous literature review or continue where you left off. Start a new search anytime from Research.
        </p>
      </div>

      {/* Search Bar */}
      <div className="relative">
        <Search className="w-4 h-4 text-neutral-400 absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search past reviews or paper titles..."
          aria-label="Search past reviews or paper titles"
          className="w-full bg-white border border-neutral-200/90 rounded-xl pl-10 pr-4 py-3 text-sm text-neutral-900 placeholder:text-neutral-400 shadow-xs focus:outline-none focus:ring-2 focus:ring-neutral-900/15 focus:border-neutral-300 transition-all"
        />
      </div>

      {/* Section Title */}
      <div className="space-y-3">
        <h2 className="font-sans text-sm font-semibold text-neutral-900">
          Recent reviews
        </h2>

        {isLoading ? (
          <div className="w-full bg-white rounded-2xl border border-neutral-200/80 p-10 flex items-center justify-center gap-2.5 text-sm text-neutral-500 shadow-xs">
            <Loader2 className="w-4 h-4 animate-spin text-[var(--color-sky-dark)]" />
            <span>Loading past reviews...</span>
          </div>
        ) : filteredReviews.length === 0 ? (
          <div className="w-full bg-white rounded-2xl border border-dashed border-neutral-200 p-10 text-center space-y-3">
            <p className="text-sm font-medium text-neutral-700">
              {searchQuery.trim()
                ? "No past reviews match your search."
                : "No previous literature reviews found yet."}
            </p>
            <p className="text-xs text-neutral-500">
              Start a new research query to discover papers, review summaries, and generate reports.
            </p>
            <button
              type="button"
              onClick={onStartNewResearch}
              style={{ borderRadius: "var(--radius-sm)" }}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold bg-neutral-900 hover:bg-black text-white transition-colors cursor-pointer mt-1"
            >
              <span>Start New Research</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredReviews.map((review) => (
              <div
                key={review.id}
                role="button"
                tabIndex={0}
                onClick={() => onSelectReview(review)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    if (e.target === e.currentTarget) {
                      e.preventDefault();
                      onSelectReview(review);
                    }
                  }
                }}
                className={cn(
                  "bg-white rounded-2xl border border-neutral-200/80 p-5 shadow-xs hover:border-neutral-300 hover:shadow-sm transition-all flex flex-col justify-between gap-4 text-left cursor-pointer"
                )}
              >
                <div className="space-y-1.5">
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="font-sans text-sm font-semibold text-neutral-900 line-clamp-1 leading-snug flex-1 min-w-0">
                      {review.query}
                    </h3>
                    {renderStatusBadge(review.status)}
                  </div>

                  <p className="font-sans text-xs text-neutral-500">
                    Created {formatCreatedDate(review.created_at)}
                    {typeof review.paper_count === "number" && ` · ${review.paper_count} papers`}
                  </p>
                </div>

                {/* Actions */}
                <div className="flex flex-wrap items-center gap-2">
                  {review.status === "completed" && (
                    <a
                      href={getReviewPdfDownloadUrl(review.id)}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      style={{ borderRadius: "var(--radius-sm)" }}
                      className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold bg-neutral-900 hover:bg-black text-white transition-colors"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Download PDF</span>
                    </a>
                  )}

                  {review.status === "awaiting_approval" ? (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectReview(review);
                      }}
                      style={{ borderRadius: "var(--radius-sm)" }}
                      className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold bg-white hover:bg-neutral-50 text-neutral-800 border border-neutral-200/90 transition-colors cursor-pointer"
                    >
                      <span>Continue Review</span>
                    </button>
                  ) : review.status !== "failed" ? (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectReview(review);
                      }}
                      style={{ borderRadius: "var(--radius-sm)" }}
                      className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold bg-white hover:bg-neutral-50 text-neutral-800 border border-neutral-200/90 transition-colors cursor-pointer"
                    >
                      <span>{sectionActionLabel}</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
