import { useState, useEffect } from "react";
import ResearchInput, { type ResearchSearchParams } from "../components/ResearchInput";
import PaperGrid from "../components/dashboard/paper-grid";
import { type PaperSummary } from "../components/PaperSummaryCard";
import { submitHumanDecision } from "../lib/api";

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

  // Review session state
  const [reviewId, setReviewId] = useState<string | null>(null);

  // Single source of truth for selected paper IDs
  const [selectedPaperIds, setSelectedPaperIds] = useState<string[]>(
    defaultPapers.filter((p) => p.isSelected).map((p) => p.id)
  );

  // Approval submission state
  const [isProceeding, setIsProceeding] = useState(false);
  const [isFindingMore, setIsFindingMore] = useState(false);
  const [approvalError, setApprovalError] = useState<string | null>(null);
  const [approvalSuccess, setApprovalSuccess] = useState<string | null>(null);

  // Rotate reassuring loading status lines while searching
  useEffect(() => {
    if (!isSearching) return;
    const interval = setInterval(() => {
      setSearchStepIndex((prev) => (prev + 1) % searchingSteps.length);
    }, 900);
    return () => clearInterval(interval);
  }, [isSearching]);

  const handleSearch = (params: ResearchSearchParams) => {
    setActiveQuery(params.query);
    setIsSearching(true);
    setSearchStepIndex(0);
    setApprovalError(null);
    setApprovalSuccess(null);

    // Track review_id from research search params if returned by backend API
    if (params.review_id) {
      setReviewId(params.review_id);
    } else {
      setReviewId(null);
    }

    // Simulate search latency to allow researcher to see satisfying discovery progression
    setTimeout(() => {
      setIsSearching(false);
      setHasSearched(true);
      setPapers(defaultPapers);
      setSelectedPaperIds(defaultPapers.filter((p) => p.isSelected).map((p) => p.id));
    }, 2400);
  };

  const togglePaperSelection = (id: string) => {
    setSelectedPaperIds((prev) =>
      prev.includes(id) ? prev.filter((pId) => pId !== id) : [...prev, id]
    );
  };

  const handleProceed = async () => {
    if (!reviewId) {
      setApprovalError("Review session is not ready. Please initiate a search to start a review task.");
      return;
    }
    if (selectedPaperIds.length === 0) {
      setApprovalError("Please select at least one paper before proceeding.");
      return;
    }

    setIsProceeding(true);
    setApprovalError(null);
    setApprovalSuccess(null);

    try {
      await submitHumanDecision(reviewId, selectedPaperIds, "continue");
      setApprovalSuccess(
        `Selection approved successfully! (${selectedPaperIds.length} paper${
          selectedPaperIds.length > 1 ? "s" : ""
        } submitted for review ID: ${reviewId})`
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to submit paper approvals";
      setApprovalError(message);
    } finally {
      setIsProceeding(false);
    }
  };

  const handleFindMore = async () => {
    if (!reviewId) {
      setApprovalError("Review session is not ready. Please initiate a search to start a review task.");
      return;
    }

    setIsFindingMore(true);
    setApprovalError(null);
    setApprovalSuccess(null);

    try {
      await submitHumanDecision(reviewId, [], "find_more");
      setApprovalSuccess(`Request to search for more papers submitted successfully! (Review ID: ${reviewId})`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to submit request for more papers";
      setApprovalError(message);
    } finally {
      setIsFindingMore(false);
    }
  };

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

      {/* COMPLETED SEARCH RESULTS (Paper Approval Grid) */}
      {!isSearching && hasSearched && (
        <PaperGrid
          papers={papers}
          selectedPaperIds={selectedPaperIds}
          onToggleSelect={togglePaperSelection}
          onProceed={handleProceed}
          onFindMore={handleFindMore}
          reviewId={reviewId}
          isProceeding={isProceeding}
          isFindingMore={isFindingMore}
          errorMessage={approvalError}
          successMessage={approvalSuccess}
        />
      )}
    </div>
  );
}
