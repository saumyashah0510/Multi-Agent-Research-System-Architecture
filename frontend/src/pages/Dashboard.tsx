import { useState, useEffect } from "react";
import ResearchInput, { type ResearchSearchParams } from "../components/ResearchInput";
import PaperSummaryCard, { type PaperSummary } from "../components/PaperSummaryCard";
import { cn } from "../lib/utils";

// Single example summary card per user specification
const defaultPapers: PaperSummary[] = [
  {
    id: "paper-1",
    title: "Generative AI in Higher Education: A Systematic Review of Learning Outcomes",
    authors: "Chen, K. et al.",
    year: 2025,
    venue: "Journal of Educational Technology",
    abstract:
      "A systematic evaluation of generative AI adoption across 142 university courses demonstrates notable gains in conceptual synthesis and computational problem solving, alongside critical pedagogical considerations regarding cognitive offloading and assessment validity.",
    tags: ["Highly cited", "Open access", "Peer reviewed"],
    relevanceScore: 98,
    isSelected: true,
  },
];

const searchingSteps = [
  "Searching arXiv, PubMed Central, and OpenAlex academic databases...",
  "Found candidate preprint. Running semantic deduplication...",
  "Scoring methodology relevance and screening abstract...",
  "Synthesizing paper summary and extracted citation metadata...",
];

export default function Dashboard() {
  const [activeQuery, setActiveQuery] = useState<string>(
    "How does generative AI affect student learning and academic performance?"
  );
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(true);
  const [searchStepIndex, setSearchStepIndex] = useState(0);
  const [papers, setPapers] = useState<PaperSummary[]>(defaultPapers);

  // Rotate reassuring loading status lines while searching
  useEffect(() => {
    if (!isSearching) return;
    const interval = setInterval(() => {
      setSearchStepIndex((prev) => (prev + 1) % searchingSteps.length);
    }, 900);
    return () => clearInterval(interval);
  }, [isSearching]);

  const handleSearch = ({ query }: ResearchSearchParams) => {
    setActiveQuery(query);
    setIsSearching(true);
    setSearchStepIndex(0);

    // Simulate search latency to allow researcher to see satisfying discovery progression
    setTimeout(() => {
      setIsSearching(false);
      setHasSearched(true);
      setPapers(defaultPapers);
    }, 2400);
  };

  const togglePaperSelection = (id: string) => {
    setPapers((prev) =>
      prev.map((paper) =>
        paper.id === id ? { ...paper, isSelected: !paper.isSelected } : paper
      )
    );
  };

  const selectedCount = papers.filter((p) => p.isSelected).length;

  return (
    <div
      id="dashboard-page"
      className="w-full max-w-4xl mx-auto flex flex-col items-center px-3 sm:px-6 pb-16"
    >
      {/* Welcome Headline: Generous whitespace above */}
      <div className="text-center pt-16 sm:pt-24 md:pt-[18vh] pb-8 sm:pb-10 max-w-3xl px-4 flex flex-col items-center">
        <h1 className="font-serif text-3xl sm:text-5xl md:text-6xl font-normal text-neutral-900 tracking-tight leading-none">
          Welcome,
        </h1>
        <p className="font-serif text-2xl sm:text-3xl md:text-4xl font-normal text-neutral-800 tracking-tight leading-none">
          What are you curious about?
        </p>
      </div>

      {/* Main Research Search Card: Consistent expanded width */}
      <div className="w-full mb-5">
        <ResearchInput onSearch={handleSearch} isLoading={isSearching} />
      </div>

      {/* SEARCHING STATE: Satisfying animated search status card */}
      {isSearching && (
        <div className="w-full bg-white rounded-2xl border border-neutral-200/80 shadow-xs p-8 sm:p-10 text-center space-y-6 animate-in fade-in duration-300">
          <div className="relative w-16 h-16 mx-auto flex items-center justify-center">
            <div className="absolute inset-0 rounded-full border-4 border-[var(--color-pill-sky)] opacity-30 animate-ping" />
            <div className="w-12 h-12 rounded-full border-3 border-[var(--color-primary-blue)] border-t-transparent animate-spin" />
          </div>

          <div className="space-y-2 max-w-md mx-auto">
            <h3 className="font-serif text-xl font-bold text-neutral-900">
              Scouring Literature Repositories
            </h3>
            <p className="text-sm font-medium text-[var(--color-success)] transition-all duration-300 min-h-[40px] flex items-center justify-center">
              ✦ {searchingSteps[searchStepIndex]}
            </p>
            <p className="text-xs text-neutral-400">
              Query: &ldquo;{activeQuery}&rdquo;
            </p>
          </div>

          {/* Skeleton Placeholder */}
          <div className="pt-2 max-w-2xl mx-auto opacity-40">
            <div className="h-24 bg-neutral-100 rounded-xl animate-pulse" />
          </div>
        </div>
      )}

      {/* COMPLETED SEARCH RESULTS */}
      {!isSearching && hasSearched && (
        <div className="w-full space-y-5 animate-in fade-in duration-300">
          {/* Status & Action Bar: Exact same width */}
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

            {/* Search again button - consistent rounded-full pill button */}
            <button
              type="button"
              onClick={() => {
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}
              className="bg-[var(--color-danger)] hover:bg-[var(--color-danger-hover)] text-white text-xs sm:text-sm font-semibold px-4 py-1.5 rounded-full shadow-xs transition-colors cursor-pointer tracking-compact"
            >
              Search again
            </button>
          </div>


          <div className="w-full bg-white rounded-2xl border border-neutral-200/80 shadow-xs p-5 sm:p-7 space-y-6">
            {/* Header: Title + Selected Counter */}
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

            {/* Reusable Paper Summary Cards List */}
            <div className="space-y-4">
              {papers.map((paper) => (
                <PaperSummaryCard
                  key={paper.id}
                  paper={paper}
                  onToggleSelect={togglePaperSelection}
                />
              ))}
            </div>

            {/* Action Footer for Selected Papers */}
            <div className="pt-4 border-t border-neutral-100 flex flex-col sm:flex-row items-center justify-between gap-4">
              <span className="text-xs text-neutral-500">
                {selectedCount} paper ready for automated literature synthesis & citation analysis.
              </span>

              <button
                type="button"
                disabled={selectedCount === 0}
                className={cn(
                  "px-6 py-2.5 rounded-lg text-sm font-semibold tracking-compact transition-all shadow-sm cursor-pointer",
                  selectedCount > 0
                    ? "bg-neutral-900 hover:bg-black text-white hover:shadow-md"
                    : "bg-neutral-200 text-neutral-400 cursor-not-allowed"
                )}
              >
                Proceed with Selected Paper ({selectedCount}) →
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
