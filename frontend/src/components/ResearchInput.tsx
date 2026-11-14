import React, { useState, useEffect } from "react";
import { ArrowUp, Loader2 } from "lucide-react";
import { cn } from "../lib/utils";

export interface ResearchSearchParams {
  query: string;
  max_papers?: number;
  citation_format?: string;
  review_id?: string;
}

export interface ResearchInputProps {
  onSearch?: (params: ResearchSearchParams) => void;
  isLoading?: boolean;
  initialQuery?: string;
  initialNumPapers?: string;
  isSearchingActive?: boolean;
}

export default function ResearchInput({
  onSearch,
  isLoading = false,
  initialQuery = "",
  isSearchingActive = false,
}: ResearchInputProps) {
  const [query, setQuery] = useState(initialQuery);

  useEffect(() => {
    if (initialQuery) {
      setQuery(initialQuery);
    }
  }, [initialQuery]);

  const isSubmitting = isLoading;

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const finalQuery = query.trim();
    if (isSubmitting || !finalQuery) return;

    // Delegate review task creation exclusively to parent handler (prevents duplicate runs)
    onSearch?.({
      query: finalQuery,
      max_papers: 10,
      citation_format: "APA",
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // When search has already started and research progress is underway,
  // display the query as a clean white message bubble at ~75% width aligned to the right.
  if (isSearchingActive && query.trim()) {
    return (
      <div className="w-full flex justify-end">
        <div className="w-full sm:w-[75%] max-w-[75%] bg-white border border-neutral-200/90 text-neutral-900 rounded-2xl rounded-tr-xs px-5 py-3.5 shadow-xs transition-all">
          <p className="font-sans text-sm sm:text-[15px] leading-relaxed text-neutral-900 whitespace-pre-wrap break-words">
            {query}
          </p>
        </div>
      </div>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="w-full bg-white rounded-[22px] border border-neutral-200/90 shadow-[0_12px_40px_rgba(0,0,0,0.08)] px-5 sm:px-6 py-3.5 sm:py-4 transition-all hover:shadow-[0_16px_48px_rgba(0,0,0,0.11)] flex items-center justify-between gap-4"
    >
      {/* Research Input Textarea (Accommodates ~2 visible lines without auto-scaling) */}
      <textarea
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="What do you want to research?"
        aria-label="What do you want to research?"
        rows={2}
        className="flex-1 bg-transparent border-0 outline-none resize-none h-[48px] sm:h-[52px] text-base sm:text-[17px] text-neutral-900 placeholder:text-neutral-500 font-sans tracking-tight focus:ring-0 focus:outline-none leading-snug sm:leading-relaxed overflow-y-auto block p-0"
      />

      {/* Black Squircle Submit Button with White Arrow Up */}
      <button
        type="submit"
        disabled={isSubmitting || !query.trim()}
        aria-label="Start Research"
        style={{ borderRadius: "var(--radius-sm)" }}
        className={cn(
          "w-10 h-10 bg-black text-white flex items-center justify-center transition-all shadow-sm shrink-0 cursor-pointer self-center",
          "hover:bg-neutral-800 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
        )}
      >
        {isSubmitting ? (
          <Loader2 className="w-5 h-5 text-white animate-spin" />
        ) : (
          <ArrowUp className="w-5 h-5 text-white" strokeWidth={2.25} />
        )}
      </button>
    </form>
  );
}
