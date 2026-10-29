import { useState } from "react";
import { useNavigate } from "react-router-dom";
import ResearchInput, { type ResearchSearchParams } from "../components/ResearchInput";
import PaperGrid from "../components/dashboard/paper-grid";
import { type PaperSummary } from "../components/PaperSummaryCard";
import { submitHumanDecision } from "../lib/api";
import ResearchProgress from "../components/pipeline/ResearchProgress";

// Single example summary card per user specification
const defaultPapers: PaperSummary[] = [
  {
    id: "paper-1",
    title: "Generative AI in Higher Education: A Systematic Review of Learning Outcomes",
    authors: "Chen, K. et al.",
    year: 2025,
    venue: "Journal of Educational Technology",
    url: "https://arxiv.org/abs/2303.08774",
    abstract:
      "A systematic evaluation of generative AI adoption across 142 university courses demonstrates notable gains in conceptual synthesis and computational problem solving, alongside critical pedagogical considerations regarding cognitive offloading and assessment validity.",
    tags: [],
    relevanceScore: 98,
    isSelected: true,
  },
];

export default function Dashboard() {
  const navigate = useNavigate();
  const [activeQuery, setActiveQuery] = useState<string>(
    "How does generative AI affect student learning and academic performance?"
  );
  const [hasSearched, setHasSearched] = useState(false);
  const [isPipelineDone, setIsPipelineDone] = useState(false);
  const [pipelineSession, setPipelineSession] = useState(0);
  const [papers] = useState<PaperSummary[]>(defaultPapers);

  // Review session state
  const [reviewId, setReviewId] = useState<string | null>(null);

  // TODO (Assignee - FE-05): Connect useReviewWebSocket(reviewId) to stream live events
  // const ws = useReviewWebSocket(reviewId);
  // Pass ws.stages, ws.status, and update papers state when ws.screenedPapers updates

  // Single source of truth for selected paper IDs
  const [selectedPaperIds, setSelectedPaperIds] = useState<string[]>(
    defaultPapers.filter((p) => p.isSelected).map((p) => p.id)
  );

  // Approval submission state
  const [isProceeding, setIsProceeding] = useState(false);
  const [isFindingMore, setIsFindingMore] = useState(false);
  const [approvalError, setApprovalError] = useState<string | null>(null);
  const [approvalSuccess, setApprovalSuccess] = useState<string | null>(null);

  const handleSearch = (params: ResearchSearchParams) => {
    setActiveQuery(params.query);
    setHasSearched(true);
    setIsPipelineDone(false);
    setPipelineSession((prev) => prev + 1);
    setApprovalError(null);
    setApprovalSuccess(null);

    // Track review_id from research search params if returned by backend API
    if (params.review_id) {
      setReviewId(params.review_id);
    } else {
      setReviewId(null);
    }
  };

  const togglePaperSelection = (id: string) => {
    setSelectedPaperIds((prev) =>
      prev.includes(id) ? prev.filter((pId) => pId !== id) : [...prev, id]
    );
  };

  const handleProceed = async () => {
    if (selectedPaperIds.length === 0) {
      setApprovalError("Please select at least one paper before proceeding.");
      return;
    }

    setIsProceeding(true);
    setApprovalError(null);
    setApprovalSuccess(null);

    try {
      if (reviewId) {
        await submitHumanDecision(reviewId, selectedPaperIds, "continue");
        // TODO (Assignee - FE-06): Redirect user to /review/:reviewId for downstream stages
        navigate(`/review/${reviewId}`);
      } else {
        setApprovalSuccess(
          `Selection approved successfully! (${selectedPaperIds.length} paper${
            selectedPaperIds.length > 1 ? "s" : ""
          } submitted for synthesis matrix)`
        );
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to submit paper approvals";
      setApprovalError(message);
    } finally {
      setIsProceeding(false);
    }
  };

  // Unified Find More Papers action
  const handleFindMore = async () => {
    setIsFindingMore(true);
    setApprovalError(null);
    setApprovalSuccess(null);

    try {
      if (reviewId) {
        await submitHumanDecision(reviewId, [], "find_more");
      }
      // Re-trigger pipeline discovery to find additional literature
      setPipelineSession((prev) => prev + 1);
      setIsPipelineDone(false);
      setApprovalSuccess("Searching academic repositories for additional papers...");
    } catch (err) {
      // In mock/frontend mode, smoothly re-run pipeline discovery
      setPipelineSession((prev) => prev + 1);
      setIsPipelineDone(false);
    } finally {
      setIsFindingMore(false);
    }
  };

  return (
    <div
      id="dashboard-page"
      className="w-full max-w-4xl mx-auto flex flex-col items-center px-3 sm:px-6 min-h-[calc(100vh-3.75rem)] pb-16"
    >
      {!hasSearched ? (
        /* Initial Screen: covers 100vh with Research Input positioned ~75% vh down and footer starting after 100vh */
        <div className="w-full flex-1 flex flex-col justify-between pt-[14vh] sm:pt-[16vh] pb-[10vh] sm:pb-[12vh]">
          {/* Welcome Headline */}
          <div className="text-center max-w-3xl mx-auto px-4 flex flex-col items-center">
            <h1 className="font-serif text-3xl sm:text-5xl md:text-6xl font-normal text-neutral-900 tracking-tight leading-none">
              Welcome,
            </h1>
            <p className="font-serif text-2xl sm:text-3xl md:text-4xl font-normal text-neutral-800 tracking-tight leading-none mt-2">
              What are you curious about?
            </p>
          </div>

          {/* Main Research Search Card positioned ~75% vh down */}
          <div className="w-full">
            <ResearchInput
              initialQuery={activeQuery}
              initialNumPapers="6"
              onSearch={handleSearch}
              isLoading={false}
            />
          </div>
        </div>
      ) : (
        /* Workflow State: Compact header followed by Pipeline and Paper Approval Grid */
        <div className="w-full flex flex-col items-center pt-6 sm:pt-8">
          {/* Welcome Headline */}
          <div className="text-center pb-5 sm:pb-6 max-w-3xl px-4 flex flex-col items-center">
            <h1 className="font-serif text-2xl sm:text-4xl font-normal text-neutral-900 tracking-tight leading-none">
              Welcome,
            </h1>
            <p className="font-serif text-xl sm:text-2xl font-normal text-neutral-800 tracking-tight leading-none mt-1.5">
              What are you curious about?
            </p>
          </div>

          {/* Main Research Search Card */}
          <div className="w-full mb-5">
            <ResearchInput
              initialQuery={activeQuery}
              initialNumPapers="6"
              onSearch={handleSearch}
              isLoading={false}
            />
          </div>

          {/* Research Progress Pipeline (only triggered upon search click) */}
          <div className="w-full mb-5">
            <ResearchProgress
              key={`pipeline-session-${pipelineSession}-${activeQuery}`}
              query={activeQuery}
              autoStart={true}
              onComplete={() => setIsPipelineDone(true)}
              onFindMore={handleFindMore}
              isFindingMore={isFindingMore}
            />
          </div>

          {/* Completed Search Results (Paper Approval Grid on the SAME page) */}
          {isPipelineDone && (
            <div className="w-full space-y-4 animate-in fade-in duration-300">
              <PaperGrid
                papers={papers}
                selectedPaperIds={selectedPaperIds}
                onToggleSelect={togglePaperSelection}
                onProceed={handleProceed}
                isProceeding={isProceeding}
                errorMessage={approvalError}
                successMessage={approvalSuccess}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
