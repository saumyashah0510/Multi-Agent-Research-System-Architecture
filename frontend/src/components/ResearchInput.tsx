import React, { useState } from "react";
import { cn } from "../lib/utils";

export interface ResearchInputProps {
  onSearch?: (params: {
    query: string;
    numPapers: number;
    source: string;
    dateRange: string;
  }) => void;
  isLoading?: boolean;
}

export default function ResearchInput({
  onSearch,
  isLoading = false,
}: ResearchInputProps) {
  const [query, setQuery] = useState("");
  const [numPapers, setNumPapers] = useState("10");
  const [source, setSource] = useState("All");
  const [dateRange, setDateRange] = useState("Publication Date");
  const [showDateMenu, setShowDateMenu] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isLoading) return;
    if (onSearch) {
      onSearch({
        query: query.trim(),
        numPapers: parseInt(numPapers, 10) || 10,
        source,
        dateRange,
      });
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="w-full max-w-3xl mx-auto bg-white rounded-2xl sm:rounded-3xl border border-neutral-200/90 shadow-[0_8px_30px_rgb(0,0,0,0.06)] p-3.5 sm:p-5 transition-all hover:shadow-[0_12px_40px_rgb(0,0,0,0.09)]"
    >
      {/* Top Research Input Field */}
      <div className="w-full">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="What do you want to research?"
          rows={2}
          className="w-full resize-none border-0 outline-none text-base sm:text-lg text-neutral-900 placeholder:text-neutral-400 bg-transparent p-1 sm:p-2 focus:ring-0 tracking-compact"
        />
      </div>

      {/* Bottom Controls Bar from Figma Mockup */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 pt-3 border-t border-neutral-100">
        <div className="flex flex-wrap items-center gap-2 text-xs sm:text-sm">
          {/* Paperclip / Attachment Button */}
          <button
            type="button"
            title="Attach paper or PDF"
            className="p-1.5 sm:p-2 rounded-lg text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 transition-colors"
          >
            <svg
              className="w-4 h-4 sm:w-4.5 sm:h-4.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth="2"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
              />
            </svg>
          </button>

          {/* Publication Date Chip */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowDateMenu(!showDateMenu)}
              className={cn(
                "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium tracking-compact transition-colors border",
                dateRange !== "Publication Date"
                  ? "bg-[#DFFFAA] text-black border-black/10"
                  : "bg-neutral-100/90 hover:bg-neutral-200/80 text-neutral-700 border-neutral-200/60"
              )}
            >
              <svg
                className="w-3.5 h-3.5 text-neutral-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                strokeWidth="2"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </svg>
              <span>{dateRange}</span>
            </button>

            {showDateMenu && (
              <div className="absolute top-full left-0 mt-1.5 w-44 bg-white rounded-xl shadow-lg border border-neutral-200/80 py-1.5 z-20 text-xs">
                {["Publication Date (Any)", "Past 1 Year", "Past 3 Years", "Past 5 Years", "2020 - 2026"].map(
                  (range) => (
                    <button
                      key={range}
                      type="button"
                      onClick={() => {
                        setDateRange(range.replace(" (Any)", ""));
                        setShowDateMenu(false);
                      }}
                      className="w-full text-left px-3 py-1.5 hover:bg-neutral-100 text-neutral-700 font-medium"
                    >
                      {range}
                    </button>
                  )
                )}
              </div>
            )}
          </div>

          {/* Number of Papers Chip */}
          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-neutral-100/90 text-neutral-700 border border-neutral-200/60">
            <span>Number of Papers</span>
            <select
              value={numPapers}
              onChange={(e) => setNumPapers(e.target.value)}
              className="bg-transparent text-neutral-900 font-semibold outline-none cursor-pointer pr-1"
            >
              <option value="5">5</option>
              <option value="10">10</option>
              <option value="20">20</option>
              <option value="50">50</option>
            </select>
          </div>

          {/* Sources Chip */}
          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-neutral-100/90 text-neutral-700 border border-neutral-200/60">
            <span>Sources</span>
            <select
              value={source}
              onChange={(e) => setSource(e.target.value)}
              className="bg-transparent text-neutral-900 font-semibold outline-none cursor-pointer pr-1"
            >
              <option value="All">All</option>
              <option value="arXiv">arXiv</option>
              <option value="Semantic Scholar">Semantic Scholar</option>
              <option value="PubMed">PubMed</option>
            </select>
          </div>
        </div>

        {/* Circular Upward Arrow Submit Button */}
        <button
          type="submit"
          disabled={!query.trim() || isLoading}
          aria-label="Start Research"
          className={cn(
            "w-9 h-9 sm:w-10 sm:h-10 rounded-full flex items-center justify-center text-white transition-all shadow-md shrink-0",
            query.trim() && !isLoading
              ? "bg-[#4F6BF7] hover:bg-[#3D59E3] hover:scale-105 active:scale-95 cursor-pointer shadow-[#4F6BF7]/30"
              : "bg-neutral-300 opacity-60 cursor-not-allowed"
          )}
        >
          {isLoading ? (
            <svg
              className="animate-spin h-4 w-4 text-white"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
              />
            </svg>
          ) : (
            <svg
              className="w-4 h-4 sm:w-5 sm:h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth="2.5"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M5 10l7-7m0 0l7 7m-7-7v18"
              />
            </svg>
          )}
        </button>
      </div>
    </form>
  );
}
