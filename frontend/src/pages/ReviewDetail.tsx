/**
 * ReviewDetail Page Component (/review/:reviewId)
 *
 * Assignee Task (Issues FE-06 / FE-07 / FE-08):
 * - Extract reviewId from route params (useParams)
 * - Fetch initial review status via GET /api/v1/reviews/{reviewId}
 * - Stream remaining stages 5 to 9 via WebSocket connection to /api/v1/ws/reviews/{reviewId}
 * - Display review topic header and session status
 * - Mount downstream pipeline progress tracker (Stages 5 to 9)
 * - Integrate accessible tab switcher (Report | Matrix | RAG Chat) when isCompleted is true
 * - Pass synthesized review to SynthesisReportViewer and methodology_matrix to MethodologyMatrix
 */

import React, { useState, useEffect, useCallback } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import {
  FileText,
  Layers,
  MessageSquare,
  Download,
  History,
  Loader2,
  RefreshCw,
  AlertCircle,
} from "lucide-react";
import { cn } from "../lib/utils";
import DownstreamProgress from "../components/pipeline/DownstreamProgress";
import SynthesisReportViewer from "../components/dashboard/SynthesisReportViewer";
import MethodologyMatrix from "../components/dashboard/MethodologyMatrix";
import ReviewChat from "../components/chat/ReviewChat";
import PastReviewsDrawer from "../components/dashboard/PastReviewsDrawer";
import { getReviewStatus, getReviewPdfDownloadUrl } from "../lib/api";
import { SynthesizedReview } from "../types";

const SAMPLE_FALLBACK_REPORT: SynthesizedReview = {
  title: "Comparative Analysis of Multi-Agent Architectures for Autonomous Literature Review",
  executive_summary:
    "This literature review examines state-of-the-art frameworks in multi-agent orchestration, iterative retrieval-augmented generation (RAG), and anti-hallucination citation verification. Across the evaluated literature, decentralized agent workflows demonstrate a 34% reduction in factual hallucination rates compared to monolithic prompting pipelines, while vector-chunked semantic indexing combined with metadata filtering significantly improves domain-specific recall.",
  thematic_clusters: [
    {
      theme: "Decentralized Multi-Agent Orchestration",
      summary:
        "Specialized sub-agent partitioning (e.g., dedicated search, screening, and citation verifiers) yields higher precision and fault isolation than single-prompt generative models.",
      citations: ["LangGraph Multi-Agent Architecture", "AutoGPT Academic Workflows", "ChatEval Benchmark"],
    },
    {
      theme: "Anti-Hallucination & Verifiable Citation Grounding",
      summary:
        "Post-hoc citation cross-referencing against full-text source chunks reliably detects fabricated references and misattributed claims before report finalization.",
      citations: ["CitationVerifier Framework", "FactScore Audit Methodology", "RAGGuard Protocols"],
    },
    {
      theme: "Dense Vector Indexing & Hybrid Retrieval",
      summary:
        "Combining 384D dense sentence embeddings with sparse keyword scoring balances semantic topic similarity with exact academic term matching.",
      citations: ["Hybrid Search in pgvector", "Cross-Encoder Re-Ranking", "Semantic Scholar Corpus"],
    },
  ],
  methodology_matrix: [
    {
      method_name: "Iterative Multi-Agent RAG",
      papers_used: ["LangGraph Multi-Agent Architecture", "AutoGPT Academic Workflows"],
      strengths: [
        "Dynamic query expansion with sub-topic clustering",
        "Iterative refinement of search queries based on retrieved density",
        "Decoupled screening and synthesis reducing cognitive load",
      ],
      limitations: [
        "Higher cumulative API latency across multiple LLM turns",
        "Potential drift if initial query expansion is overly broad",
      ],
    },
    {
      method_name: "Post-Hoc Citation NLI Verification",
      papers_used: ["CitationVerifier Framework", "FactScore Audit Methodology"],
      strengths: [
        "Rigorous anti-hallucination gatekeeper before synthesis",
        "Maps exact claim assertions to verbatim text chunk IDs",
      ],
      limitations: [
        "Requires access to full-text PDF extracted passages",
        "Slightly increased computational overhead per claim sentence",
      ],
    },
    {
      method_name: "Dense Semantic Embedding (pgvector 384D)",
      papers_used: ["Hybrid Search in pgvector", "Semantic Scholar Corpus"],
      strengths: [
        "Fast cosine distance indexing directly within PostgreSQL",
        "Effective capture of paraphrased academic terminology",
      ],
      limitations: [
        "Fixed embedding dimension can truncate complex multi-clause sentences",
        "Cold-start index builds on large document collections",
      ],
    },
  ],
  research_gaps: [
    "Lack of standardized evaluation benchmarks measuring hallucination rates in multi-document scientific syntheses.",
    "Scalability bottlenecks when processing full-text PDFs containing complex mathematical proofs, multi-panel figures, and tabular datasets.",
    "Absence of bi-directional human-in-the-loop steering mechanisms during downstream citation verification and gap synthesis.",
    "Limited support for real-time cross-disciplinary terminology alignment across disjoint academic taxonomies.",
  ],
  conclusion:
    "Autonomous multi-agent research pipelines represent a transformative shift in scholarly discovery. By combining specialized screening agents with deterministic citation verification and interactive methodology matrices, these systems bridge the gap between vast academic literature volumes and rigorous empirical review.",
  references: [
    {
      title: "LangGraph: Cyclic Multi-Agent Architectures for Complex Reasoning Tasks",
      authors: ["Harrison Chase", "Rotem Weiss", "Erick Friis"],
      year: 2024,
      url: "https://arxiv.org/abs/2402.12345",
      matched_passage:
        "Cyclic state graphs enable multi-agent literature syntheses to self-correct through iterative verification loops.",
    },
    {
      title: "FactScore: Fine-Grained Atomic Verification for Long-Form Text Generation",
      authors: ["Sewon Min", "Kalpesh Krishna", "Xinxi Lyu"],
      year: 2023,
      url: "https://arxiv.org/abs/2305.14251",
      matched_passage:
        "Breaking long-form reviews into atomic claim propositions provides an objective metric for citation grounding.",
    },
    {
      title: "Dense Semantic Indexing and Hybrid Retrieval in Scientific Corpora",
      authors: ["Arman Cohan", "Sergey Feldman", "Iz Beltagy"],
      year: 2023,
      url: "https://doi.org/10.1145/3397271.3401075",
      matched_passage:
        "Dense vector representations effectively complement sparse inverted index matching for academic search.",
    },
  ],
};

const ReviewDetailInner: React.FC = () => {
  const { reviewId } = useParams<{ reviewId: string }>();
  const [searchParams] = useSearchParams();
  const isMockParam = searchParams.get("mock") === "true";

  const [isCompleted, setIsCompleted] = useState(false);
  const [activeTab, setActiveTab] = useState<"report" | "matrix" | "chat">("report");
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [reviewTopic, setReviewTopic] = useState<string | null>(null);
  const [synthesizedReport, setSynthesizedReport] = useState<SynthesizedReview | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [isRetrying, setIsRetrying] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Load review status and synthesized report via GET /api/v1/reviews/{reviewId}
  const loadReviewData = useCallback(async () => {
    if (!reviewId) return null;
    try {
      const data = await getReviewStatus(reviewId);
      if (data?.query || data?.user_query) {
        setReviewTopic(data.query || data.user_query);
      }
      const normStatus = String(data?.status || "").toLowerCase();
      if (normStatus === "completed" || normStatus === "synthesis_completed") {
        setIsCompleted(true);
        if (data?.synthesized_review) {
          setSynthesizedReport(data.synthesized_review);
          setFetchError(null);
        }
      }
      return data;
    } catch (err) {
      console.warn("Could not retrieve review status:", err);
      return null;
    }
  }, [reviewId]);

  useEffect(() => {
    if (!reviewId) return;

    // Reset review state on reviewId change to avoid displaying stale data
    setReviewTopic(null);
    setSynthesizedReport(null);
    setIsCompleted(false);
    setRetryCount(0);
    setFetchError(null);

    let isMounted = true;
    loadReviewData().then((data) => {
      if (!isMounted || !data) return;
    });

    return () => {
      isMounted = false;
    };
  }, [reviewId, loadReviewData]);

  const handlePipelineComplete = useCallback(() => {
    setIsCompleted(true);
    setRetryCount(0);
    setFetchError(null);
    loadReviewData();
  }, [loadReviewData]);

  // Auto-retry polling if pipeline completed but synthesized_review is not yet available
  useEffect(() => {
    if (!isCompleted || synthesizedReport || retryCount >= 5) return;

    const timer = setTimeout(async () => {
      setRetryCount((prev) => prev + 1);
      const res = await loadReviewData();
      if (!res?.synthesized_review && retryCount + 1 >= 5) {
        setFetchError("Synthesis report is taking longer than expected to persist.");
      }
    }, 3000);

    return () => clearTimeout(timer);
  }, [isCompleted, synthesizedReport, retryCount, loadReviewData]);

  const handleManualRetry = async () => {
    setIsRetrying(true);
    setFetchError(null);
    try {
      const res = await loadReviewData();
      if (!res?.synthesized_review) {
        setFetchError("Report not available yet. Please try again in a few moments.");
      }
    } finally {
      setIsRetrying(false);
    }
  };

  // Show fabricated sample data only in explicit mock/dev mode, never as real results
  const activeReport: SynthesizedReview | null =
    synthesizedReport ||
    (isMockParam || import.meta.env.DEV
      ? {
          ...SAMPLE_FALLBACK_REPORT,
          title: reviewTopic
            ? `Comparative Literature Synthesis: ${reviewTopic}`
            : SAMPLE_FALLBACK_REPORT.title,
        }
      : null);

  return (
    <div className="w-full max-w-5xl mx-auto px-4 py-8 space-y-6">
      {/* Session Header Bar */}
      <div className="border-b border-neutral-200 pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-serif font-bold text-neutral-900">
            {reviewTopic || "Literature Review Session"}
          </h1>
          <p className="text-sm text-neutral-500 mt-1">Review ID: {reviewId}</p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={() => setIsDrawerOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-neutral-200 text-xs font-semibold text-neutral-700 hover:bg-neutral-50 transition-colors cursor-pointer"
            title="View past reviews"
          >
            <History className="w-3.5 h-3.5" />
            <span>History</span>
          </button>

          {isCompleted && (
            <a
              href={getReviewPdfDownloadUrl(reviewId || "")}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-neutral-900 text-white text-xs font-semibold hover:bg-neutral-800 transition-colors shadow-xs"
              title="Download S3 PDF Synthesis Report"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export PDF</span>
            </a>
          )}

          {/* Tab Switcher (unlocked once completed) */}
          {isCompleted && (
            <div
              role="tablist"
              aria-label="Literature review output views"
              className="flex items-center gap-1 bg-neutral-100 p-1 rounded-xl"
            >
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === "report"}
                onClick={() => setActiveTab("report")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  activeTab === "report"
                    ? "bg-white text-neutral-900 shadow-xs"
                    : "text-neutral-600 hover:text-neutral-900"
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Report</span>
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === "matrix"}
                onClick={() => setActiveTab("matrix")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  activeTab === "matrix"
                    ? "bg-white text-neutral-900 shadow-xs"
                    : "text-neutral-600 hover:text-neutral-900"
                }`}
              >
                <Layers className="w-3.5 h-3.5" />
                <span>Matrix</span>
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === "chat"}
                onClick={() => setActiveTab("chat")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  activeTab === "chat"
                    ? "bg-white text-neutral-900 shadow-xs"
                    : "text-neutral-600 hover:text-neutral-900"
                }`}
              >
                <MessageSquare className="w-3.5 h-3.5" />
                <span>RAG Chat</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Downstream Checkpoints Tracker (Stages 5 to 9) */}
      <DownstreamProgress
        reviewId={reviewId}
        isCompleted={isCompleted}
        onComplete={handlePipelineComplete}
        isMock={isMockParam}
      />

      {/* Synthesis Report, Methodology Matrix, and Interactive RAG Chat Views */}
      {isCompleted && (
        <div className="animate-in fade-in duration-300">
          {activeReport ? (
            <>
              {activeTab === "report" && (
                <SynthesisReportViewer report={activeReport} />
              )}

              {activeTab === "matrix" && (
                <MethodologyMatrix matrix={activeReport.methodology_matrix} />
              )}
            </>
          ) : (
            (activeTab === "report" || activeTab === "matrix") && (
              <div className="w-full bg-white rounded-2xl border border-neutral-200/90 shadow-xs p-8 text-center space-y-4">
                <div className="w-10 h-10 mx-auto rounded-full bg-indigo-50 flex items-center justify-center text-indigo-600">
                  {fetchError && retryCount >= 5 ? (
                    <AlertCircle className="w-5 h-5 text-amber-600" />
                  ) : (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  )}
                </div>
                <div>
                  <h3 className="font-serif text-lg font-bold text-neutral-900">
                    {fetchError && retryCount >= 5
                      ? "Report Generation in Progress"
                      : "Finalizing Literature Synthesis..."}
                  </h3>
                  <p className="text-xs text-neutral-500 max-w-md mx-auto mt-1">
                    {fetchError ||
                      "Downstream agents completed analysis. The structured synthesis report and comparative matrix are currently being assembled."}
                  </p>
                </div>
                <div>
                  <button
                    type="button"
                    onClick={handleManualRetry}
                    disabled={isRetrying}
                    className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold transition-colors cursor-pointer disabled:opacity-50"
                  >
                    <RefreshCw className={cn("w-3.5 h-3.5", isRetrying && "animate-spin")} />
                    <span>{isRetrying ? "Checking..." : "Refresh Report"}</span>
                  </button>
                </div>
              </div>
            )
          )}

          {reviewId ? (
            <div className={activeTab === "chat" ? "block" : "hidden"}>
              <ReviewChat reviewId={reviewId} />
            </div>
          ) : (
            activeTab === "chat" && (
              <div className="w-full bg-white rounded-2xl border border-neutral-200/90 shadow-xs p-8 text-center text-neutral-500 text-xs sm:text-sm">
                No literature review ID provided in the route.
              </div>
            )
          )}
        </div>
      )}

      {/* Past Reviews Slide-Out Drawer */}
      <PastReviewsDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
      />
    </div>
  );
};

export const ReviewDetail: React.FC = () => {
  const { reviewId } = useParams<{ reviewId: string }>();
  return <ReviewDetailInner key={reviewId} />;
};

export default ReviewDetail;
