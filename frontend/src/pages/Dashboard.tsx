import { useState, useEffect } from "react";
import ResearchInput, { type ResearchSearchParams } from "../components/ResearchInput";
import PaperSummaryCard, { type PaperSummary } from "../components/PaperSummaryCard";
import AgentFeed from "../components/dashboard/agent-feed";
import ReportView from "../components/dashboard/report-view";
import { cn } from "../lib/utils";
import { getReviewStatus, submitHumanDecision } from "../lib/api";
import type { PipelineStep, SynthesizedReport } from "../types";

// Example candidate paper for initial prototype UI presentation
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

/**
 * Maps raw backend review status strings to frontend PipelineStep values.
 */
export function mapBackendStatusToPipelineStep(backendStatus?: string): PipelineStep {
  if (!backendStatus) return "idle";
  switch (backendStatus.toLowerCase()) {
    case "accepted":
    case "pending":
    case "discovering":
      return "discovering";
    case "screening":
    case "screening_completed":
      return "screening";
    case "user_approval_pending":
      return "human_in_loop";
    case "approved":
    case "synthesizing":
      return "synthesizing";
    case "synthesis_completed":
    case "completed":
      return "completed";
    case "failed":
    case "error":
      return "failed";
    default:
      return "idle";
  }
}

export default function Dashboard() {
  const [hasSearched, setHasSearched] = useState(true);
  const [papers, setPapers] = useState<PaperSummary[]>(defaultPapers);

  // Review task & synthesis report state
  const [reviewId, setReviewId] = useState<string | null>(null);
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStep>("human_in_loop");
  const [report, setReport] = useState<SynthesizedReport | null>(null);
  const [isProceeding, setIsProceeding] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const isSearching =
    pipelineStatus === "discovering" || pipelineStatus === "screening";

  // Polling effect: Periodically fetch backend review status while pipeline is active
  useEffect(() => {
    if (!reviewId) return;

    const isActiveStep =
      pipelineStatus === "discovering" ||
      pipelineStatus === "screening" ||
      pipelineStatus === "synthesizing";

    if (!isActiveStep) return;

    let isMounted = true;

    const pollStatus = async () => {
      try {
        const data = await getReviewStatus(reviewId);
        if (!isMounted) return;
        if (data?.status) {
          const mappedStep = mapBackendStatusToPipelineStep(data.status);
          setPipelineStatus(mappedStep);
        }
        if (data?.synthesized_review) {
          setReport(data.synthesized_review);
        }
      } catch (err) {
        console.error("Error polling backend review status:", err);
      }
    };

    // Immediate check upon step activation
    pollStatus();

    const pollInterval = setInterval(pollStatus, 1500);

    return () => {
      isMounted = false;
      clearInterval(pollInterval);
    };
  }, [reviewId, pipelineStatus]);

  const handleSearch = (params: ResearchSearchParams) => {
    setErrorMessage(null);
    setReport(null);
    setHasSearched(true);
    setPapers(defaultPapers);

    if (params.review_id) {
      setReviewId(params.review_id);
      setPipelineStatus("discovering");
    } else {
      setReviewId(null);
      setPipelineStatus("human_in_loop");
    }
  };

  const togglePaperSelection = (id: string) => {
    setPapers((prev) =>
      prev.map((paper) =>
        paper.id === id ? { ...paper, isSelected: !paper.isSelected } : paper
      )
    );
  };

  const handleProceedWithPapers = async () => {
    if (!reviewId) {
      setErrorMessage("Review session is not ready. Please initiate a search to start a review task.");
      return;
    }

    const selectedPaperIds = papers.filter((p) => p.isSelected).map((p) => p.id);
    if (selectedPaperIds.length === 0) {
      setErrorMessage("Please select at least one paper before proceeding.");
      return;
    }

    setIsProceeding(true);
    setErrorMessage(null);

    try {
      await submitHumanDecision(reviewId, selectedPaperIds, "continue");
      setPipelineStatus("synthesizing");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to submit paper approvals";
      setErrorMessage(msg);
    } finally {
      setIsProceeding(false);
    }
  };

  const selectedCount = papers.filter((p) => p.isSelected).length;

  return (
    <div
      id="dashboard-page"
      className="w-full max-w-4xl mx-auto flex flex-col items-center px-3 sm:px-6 pb-16"
    >
      {/* Welcome Headline */}
      <div className="text-center pt-16 sm:pt-24 md:pt-[18vh] pb-8 sm:pb-10 max-w-3xl px-4 flex flex-col items-center print:hidden">
        <h1 className="font-serif text-3xl sm:text-5xl md:text-6xl font-normal text-neutral-900 tracking-tight leading-none">
          Welcome,
        </h1>
        <p className="font-serif text-2xl sm:text-3xl md:text-4xl font-normal text-neutral-800 tracking-tight leading-none">
          What are you curious about?
        </p>
      </div>

      {/* Main Research Search Card */}
      <div className="w-full mb-5 print:hidden">
        <ResearchInput onSearch={handleSearch} isLoading={isSearching} />
      </div>

      {/* Error Banner */}
      {errorMessage && (
        <div className="w-full mb-5 p-4 rounded-xl bg-red-50 border border-red-200 text-red-800 text-xs sm:text-sm flex items-start gap-2.5 animate-in fade-in duration-200 print:hidden">
          <span className="font-bold text-red-600">✕</span>
          <div className="flex-1">
            <p className="font-semibold">Error</p>
            <p className="text-red-700/90 text-xs mt-0.5">{errorMessage}</p>
          </div>
        </div>
      )}

      {/* ACTIVE PIPELINE FEED / SEARCHING / FAILED */}
      {(pipelineStatus === "discovering" ||
        pipelineStatus === "screening" ||
        pipelineStatus === "synthesizing" ||
        pipelineStatus === "failed") && (
        <div className="w-full space-y-5 animate-in fade-in duration-300 print:hidden">
          <AgentFeed status={pipelineStatus} reviewId={reviewId} />
        </div>
      )}

      {/* COMPLETED REPORT VIEW */}
      {pipelineStatus === "completed" && report && (
        <div className="w-full space-y-5 animate-in fade-in duration-300">
          <div className="w-full flex justify-end print:hidden">
            <button
              type="button"
              onClick={() => {
                setPipelineStatus("human_in_loop");
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}
              className="text-xs font-semibold px-4 py-1.5 rounded-full bg-neutral-100 hover:bg-neutral-200 text-neutral-800 transition-colors border border-neutral-200/60 cursor-pointer"
            >
              ← Back to Paper Selection
            </button>
          </div>
          <ReportView report={report} />
        </div>
      )}

      {/* SYNTHESIS IN PROGRESS OR MISSING REPORT PLACEHOLDER */}
      {pipelineStatus === "completed" && !report && (
        <div className="w-full bg-white rounded-2xl border border-neutral-200/80 p-8 text-center space-y-3 animate-in fade-in duration-300 print:hidden">
          <h3 className="font-serif text-lg font-bold text-neutral-900">
            Synthesis Complete
          </h3>
          <p className="text-xs text-neutral-500">
            Awaiting synthesized report payload from backend review status endpoint.
          </p>
        </div>
      )}

      {/* HUMAN IN LOOP PAPER APPROVAL */}
      {pipelineStatus === "human_in_loop" && hasSearched && (
        <div className="w-full space-y-5 animate-in fade-in duration-300 print:hidden">
          {/* Status Bar */}
          <div className="w-full bg-white rounded-2xl border border-neutral-200/80 shadow-xs p-3.5 sm:p-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2.5">
              <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-[var(--color-pill-sky)] text-neutral-800">
                <span>Papers found</span>
                <span className="bg-white text-neutral-900 font-bold px-2 py-0.5 rounded-full text-xs shadow-xs">
                  {papers.length}
                </span>
              </div>

              <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-[var(--color-pill-sky)] text-neutral-800">
                <span>Most relevant</span>
                <span className="bg-white text-neutral-900 font-bold px-2 py-0.5 rounded-full text-xs shadow-xs">
                  {papers.length}
                </span>
              </div>
            </div>

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

          {/* Candidate Papers Container */}
          <div className="w-full bg-white rounded-2xl border border-neutral-200/80 shadow-xs p-5 sm:p-7 space-y-6">
            <div className="flex items-center justify-between pb-2 border-b border-neutral-100">
              <h2 className="font-serif text-xl sm:text-2xl font-bold text-neutral-900 tracking-compact">
                Most relevant papers
              </h2>

              <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-[var(--color-pill-sky)] text-neutral-800">
                <span>Selected</span>
                <span className="bg-white px-2 py-0.5 rounded-full text-neutral-900 font-bold shadow-xs">
                  {selectedCount}
                </span>
                <span>of {papers.length}</span>
              </div>
            </div>

            <div className="space-y-4">
              {papers.map((paper) => (
                <PaperSummaryCard
                  key={paper.id}
                  paper={paper}
                  onToggleSelect={togglePaperSelection}
                />
              ))}
            </div>

            <div className="pt-4 border-t border-neutral-100 flex flex-col sm:flex-row items-center justify-between gap-4">
              <span className="text-xs text-neutral-500">
                {selectedCount} paper ready for automated literature synthesis &amp; citation analysis.
              </span>

              <button
                type="button"
                disabled={selectedCount === 0 || isProceeding || !reviewId}
                onClick={handleProceedWithPapers}
                className={cn(
                  "px-6 py-2.5 rounded-lg text-sm font-semibold tracking-compact transition-all shadow-sm flex items-center gap-2",
                  selectedCount > 0 && !isProceeding && Boolean(reviewId)
                    ? "bg-neutral-900 hover:bg-black text-white hover:shadow-md cursor-pointer"
                    : "bg-neutral-200 text-neutral-400 cursor-not-allowed"
                )}
              >
                {isProceeding ? (
                  <>
                    <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                    </svg>
                    <span>Submitting Approval...</span>
                  </>
                ) : (
                  <span>Proceed with Selected Paper ({selectedCount}) →</span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
