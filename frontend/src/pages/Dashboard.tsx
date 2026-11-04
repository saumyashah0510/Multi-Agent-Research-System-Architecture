import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import ResearchInput, { type ResearchSearchParams } from "../components/ResearchInput";
import PaperGrid from "../components/dashboard/paper-grid";
import { type PaperSummary } from "../components/PaperSummaryCard";
import { createReviewTask, submitHumanDecision } from "../lib/api";
import ResearchProgress from "../components/pipeline/ResearchProgress";
import useReviewWebSocket from "../hooks/useReviewWebSocket";

// Candidate screened papers from Agent 03 with scores and rationales
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
    rationale:
      "Direct empirical alignment with generative AI pedagogy, robust sample size (142 courses), and high relevance score.",
    tags: [],
    relevanceScore: 98,
    isSelected: true,
  },
  {
    id: "paper-2",
    title: "Multi-Agent Systems for Automated Academic Literature Reviews",
    authors: "Vanderbilt, R. & Patel, S.",
    year: 2025,
    venue: "ACM Computing Surveys",
    url: "https://arxiv.org/abs/2401.03412",
    abstract:
      "This survey categorizes multi-agent LLM architectures applied to autonomous academic literature retrieval, relevance filtering, and cross-document synthesis, identifying open challenges in citation verification.",
    rationale:
      "Comprehensive architectural review directly covering multi-agent retrieval and screening methodologies.",
    tags: [],
    relevanceScore: 94,
    isSelected: true,
  },
  {
    id: "paper-3",
    title: "Hallucination Mitigation in Large Language Models via Graph-Based Verification",
    authors: "Morales, D. et al.",
    year: 2024,
    venue: "NeurIPS 2024",
    url: "https://arxiv.org/abs/2402.05190",
    abstract:
      "We introduce an attribution graph verification framework that anchors LLM generation against ground-truth academic corpora, cutting non-factual citation claims by over 78%.",
    rationale:
      "Provides verified reference checking techniques relevant to downstream citation verification checkpoints.",
    tags: [],
    relevanceScore: 91,
    isSelected: false,
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
  const [papers, setPapers] = useState<PaperSummary[]>(defaultPapers);

  // Review session state
  const [reviewId, setReviewId] = useState<string | null>(null);

  // Connect useReviewWebSocket(reviewId) to stream live events
  const ws = useReviewWebSocket(reviewId);

  // Single source of truth for selected paper IDs
  const [selectedPaperIds, setSelectedPaperIds] = useState<string[]>(
    defaultPapers.filter((p) => p.isSelected).map((p) => p.id)
  );

  // Synchronize screened papers from WebSocket when available
  useEffect(() => {
    if (ws.screenedPapers && ws.screenedPapers.length > 0) {
      setPapers(ws.screenedPapers);
      setSelectedPaperIds(
        ws.screenedPapers.filter((p) => p.isSelected !== false).map((p) => p.id)
      );
    }
  }, [ws.screenedPapers]);

  // Synchronize pipeline completion / pause state
  useEffect(() => {
    if (ws.isPausedForInput || ws.status === "COMPLETED") {
      setIsPipelineDone(true);
    }
  }, [ws.isPausedForInput, ws.status]);

  // Approval submission state
  const [isProceeding, setIsProceeding] = useState(false);
  const [isFindingMore, setIsFindingMore] = useState(false);
  const [approvalError, setApprovalError] = useState<string | null>(null);
  const [approvalSuccess, setApprovalSuccess] = useState<string | null>(null);

  const handleSearch = async (params: ResearchSearchParams) => {
    setActiveQuery(params.query);
    setHasSearched(true);
    setIsPipelineDone(false);
    setPipelineSession((prev) => prev + 1);
    setApprovalError(null);
    setApprovalSuccess(null);

    // Call backend API createReviewTask to obtain the real review_id
    try {
      const res = await createReviewTask(params.query, params.max_papers || 10);
      if (res && res.review_id) {
        setReviewId(res.review_id);
      } else if (params.review_id) {
        setReviewId(params.review_id);
      } else {
        setReviewId(`review-${Date.now().toString(36)}`);
      }
    } catch (err) {
      console.warn("Could not initiate backend review task, fallback to params/offline:", err);
      if (params.review_id) {
        setReviewId(params.review_id);
      } else {
        setReviewId(`review-${Date.now().toString(36)}`);
      }
    }
  };

  const togglePaperSelection = (id: string) => {
    setApprovalError(null);
    setSelectedPaperIds((prev) =>
      prev.includes(id) ? prev.filter((pId) => pId !== id) : [...prev, id]
    );
  };

  const handleProceed = async () => {
    // Require at least 1 paper selected; if none selected, show an inline warning alert
    if (selectedPaperIds.length === 0) {
      setApprovalError("Please select at least one paper before proceeding.");
      return;
    }

    setIsProceeding(true);
    setApprovalError(null);
    setApprovalSuccess(null);

    const activeReviewId = reviewId || "demo-review";
    try {
      // Dispatch submitHumanDecision(reviewId, selectedPaperIds, "continue")
      await submitHumanDecision(activeReviewId, selectedPaperIds, "continue");

      // On HTTP 200 response from approval endpoint, clear local error states and redirect
      setApprovalError(null);
      navigate(`/review/${activeReviewId}`);
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

    const activeReviewId = reviewId || "demo-review";
    try {
      await submitHumanDecision(activeReviewId, [], "find_more");
      // Re-trigger pipeline discovery to find additional literature
      setPipelineSession((prev) => prev + 1);
      setIsPipelineDone(false);
      setApprovalSuccess("Searching academic repositories for additional papers...");
    } catch (err) {
      // In mock/frontend mode, smoothly re-run pipeline discovery without redirecting
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
              stages={reviewId ? ws.stages : undefined}
              isRunning={reviewId ? (ws.isConnected && ws.status !== "COMPLETED") : undefined}
              isCompleted={reviewId ? (ws.isPausedForInput || ws.status === "COMPLETED") : isPipelineDone}
              isMock={Boolean(!reviewId)}
              autoStart={!reviewId}
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
                onFindMore={handleFindMore}
                isProceeding={isProceeding}
                isFindingMore={isFindingMore}
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
