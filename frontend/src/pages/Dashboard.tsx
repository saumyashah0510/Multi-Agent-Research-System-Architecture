import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import ResearchInput, { type ResearchSearchParams } from "../components/ResearchInput";
import PaperGrid from "../components/dashboard/paper-grid";
import { type PaperSummary } from "../components/PaperSummaryCard";
import { createReviewTask, submitHumanDecision, getReviewStatus } from "../lib/api";
import ResearchProgress from "../components/pipeline/ResearchProgress";
import useReviewWebSocket, { normalizePaper } from "../hooks/useReviewWebSocket";

export default function Dashboard() {
  const navigate = useNavigate();
  const [activeQuery, setActiveQuery] = useState<string>(
    "How does generative AI affect student learning and academic performance?"
  );
  const [hasSearched, setHasSearched] = useState(false);
  const [isPipelineDone, setIsPipelineDone] = useState(false);
  const [pipelineSession, setPipelineSession] = useState(0);

  // Screened candidate papers list (initialized empty to prevent stale demo data)
  const [papers, setPapers] = useState<PaperSummary[]>([]);

  // Review session state (must be established by backend; no temporary fallback IDs)
  const [reviewId, setReviewId] = useState<string | null>(null);

  // Connect useReviewWebSocket(reviewId) to stream live events
  const ws = useReviewWebSocket(reviewId);

  // Single source of truth for selected paper IDs
  const [selectedPaperIds, setSelectedPaperIds] = useState<string[]>([]);

  // Restore session from query parameters or localStorage on mount
  useEffect(() => {
    if (typeof window !== "undefined") {
      const urlParams = new URLSearchParams(window.location.search);
      const urlReviewId = urlParams.get("review_id");
      const storedReviewId = localStorage.getItem("scholaris_active_review_id");
      const candidateId = urlReviewId || storedReviewId;
      if (candidateId && !reviewId) {
        setReviewId(candidateId);
        setHasSearched(true);
      }
    }
  }, []);

  // Fetch persisted review status and candidate papers from REST API as fallback/cache
  useEffect(() => {
    if (reviewId) {
      if (typeof window !== "undefined") {
        localStorage.setItem("scholaris_active_review_id", reviewId);
      }
      getReviewStatus(reviewId)
        .then((res) => {
          if (res) {
            if (res.user_query) {
              setActiveQuery(res.user_query);
            }
            if (Array.isArray(res.screened_papers) && res.screened_papers.length > 0) {
              const normalized = res.screened_papers.map((p: any, idx: number) =>
                normalizePaper(p, idx)
              );
              setPapers((prev) => (prev.length === 0 ? normalized : prev));
              setSelectedPaperIds((prev) =>
                prev.length === 0
                  ? normalized.filter((p: any) => p.isSelected !== false).map((p: any) => p.id)
                  : prev
              );
            }
            const statusUpper = String(res.status || "").toUpperCase();
            if (
              statusUpper === "AWAITING_USER_INPUT" ||
              statusUpper === "COMPLETED" ||
              statusUpper === "PDF_EXTRACTION"
            ) {
              setIsPipelineDone(true);
            }
          }
        })
        .catch((err) => {
          console.debug("Could not restore past review status from REST API:", err);
        });
    }
  }, [reviewId]);

  // Synchronize actual screened papers from WebSocket when available for active review session
  useEffect(() => {
    if (reviewId && ws.screenedPapers && ws.screenedPapers.length > 0) {
      setPapers(ws.screenedPapers);
      setSelectedPaperIds(
        ws.screenedPapers.filter((p) => p.isSelected !== false).map((p) => p.id)
      );
    }
  }, [reviewId, ws.screenedPapers]);

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

    // Reset candidates and selection when starting a new search
    setPapers([]);
    setSelectedPaperIds([]);
    setApprovalError(null);
    setApprovalSuccess(null);

    // Call backend API createReviewTask to obtain the real review_id
    try {
      const res = await createReviewTask(params.query, params.max_papers || 10);
      if (res && res.review_id) {
        setReviewId(res.review_id);
        if (typeof window !== "undefined") {
          localStorage.setItem("scholaris_active_review_id", res.review_id);
        }
      } else if (params.review_id) {
        setReviewId(params.review_id);
        if (typeof window !== "undefined") {
          localStorage.setItem("scholaris_active_review_id", params.review_id);
        }
      } else {
        setReviewId(null);
        setApprovalError("Failed to initialize review session. Please try searching again.");
      }
    } catch (err) {
      console.warn("Could not initiate backend review task:", err);
      if (params.review_id) {
        setReviewId(params.review_id);
      } else {
        // Keep review ID null when creation fails and show an error
        setReviewId(null);
        const message = err instanceof Error ? err.message : "Failed to initiate backend review task";
        setApprovalError(`Could not establish review session: ${message}. Approval is prevented until a session exists.`);
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
    // Prevent approval until a valid review session exists
    if (!reviewId) {
      setApprovalError("No confirmed review session found. Please start a valid research search first.");
      return;
    }

    // Require at least 1 paper selected; if none selected, show an inline warning alert
    if (selectedPaperIds.length === 0) {
      setApprovalError("Please select at least one paper before proceeding.");
      return;
    }

    setIsProceeding(true);
    setApprovalError(null);
    setApprovalSuccess(null);

    try {
      // Dispatch submitHumanDecision(reviewId, selectedPaperIds, "continue")
      await submitHumanDecision(reviewId, selectedPaperIds, "continue");

      // On HTTP 200 response from approval endpoint, clear local error states and redirect
      setApprovalError(null);
      navigate(`/review/${reviewId}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to submit paper approvals";
      setApprovalError(message);
    } finally {
      setIsProceeding(false);
    }
  };

  // Unified Find More Papers action
  const handleFindMore = async () => {
    // Prevent find more until a valid review session exists
    if (!reviewId) {
      setApprovalError("Cannot search for additional papers without a confirmed review session.");
      return;
    }

    setIsFindingMore(true);
    setApprovalError(null);
    setApprovalSuccess(null);

    try {
      await submitHumanDecision(reviewId, [], "find_more");

      // Reset pipeline and candidates only after a successful submission
      setPipelineSession((prev) => prev + 1);
      setIsPipelineDone(false);
      setPapers([]);
      setSelectedPaperIds([]);
      setApprovalSuccess("Searching academic repositories for additional papers...");
    } catch (err) {
      // Display the error and do NOT reset the pipeline display on failure
      const message = err instanceof Error ? err.message : "Failed to request additional papers";
      setApprovalError(`Failed to request more papers: ${message}`);
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
              autoStart={false}
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
