/**
 * ReviewDetail Page Component (/review/:reviewId)
 *
 * Assignee Task (Issues FE-06 / FE-07):
 * - Extract reviewId from route params (useParams)
 * - Display review topic header and session status
 * - Mount downstream pipeline progress tracker (Stages 5 to 9)
 * - Render synthesis report, methodology matrix, and RAG chat once completed
 */

import React, { useState } from "react";
import { useParams } from "react-router-dom";
import { FileText, Layers, MessageSquare, Download, History } from "lucide-react";
import DownstreamProgress from "../components/pipeline/DownstreamProgress";
import SynthesisReportViewer from "../components/dashboard/SynthesisReportViewer";
import MethodologyMatrix from "../components/dashboard/MethodologyMatrix";
import ReviewChat from "../components/chat/ReviewChat";
import PastReviewsDrawer from "../components/dashboard/PastReviewsDrawer";
import { getReviewPdfDownloadUrl } from "../lib/api";
import { SynthesizedReview } from "../types";

export const ReviewDetail: React.FC = () => {
  const { reviewId } = useParams<{ reviewId: string }>();
  const [isCompleted, setIsCompleted] = useState(false);
  const [activeTab, setActiveTab] = useState<"report" | "matrix" | "chat">("report");
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // TODO (Assignee - FE-08):
  // 1. Fetch synthesized review data from GET /api/v1/reviews/{reviewId}
  // 2. Pass review.synthesized_review to SynthesisReportViewer
  // 3. Pass review.synthesized_review.methodology_matrix to MethodologyMatrix

  const sampleReport: SynthesizedReview = {
    title: "Comparative Literature Synthesis",
    executive_summary: "Comprehensive automated literature review synthesized across screened candidate literature.",
    thematic_clusters: [],
    methodology_matrix: [],
    research_gaps: [],
    references: [],
  };

  return (
    <div className="w-full max-w-5xl mx-auto px-4 py-8 space-y-6">
      <div className="border-b border-neutral-200 pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-serif font-bold text-neutral-900">
            Literature Review Session
          </h1>
          <p className="text-sm text-neutral-500 mt-1">Review ID: {reviewId}</p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsDrawerOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-neutral-200 text-xs font-semibold text-neutral-700 hover:bg-neutral-50 transition-colors"
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

          {/* Tab Navigation (unlocked once completed) */}
          {isCompleted && (
            <div className="flex items-center gap-1 bg-neutral-100 p-1 rounded-xl">
              <button
                onClick={() => setActiveTab("report")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  activeTab === "report" ? "bg-white text-neutral-900 shadow-xs" : "text-neutral-600 hover:text-neutral-900"
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Report</span>
              </button>
              <button
                onClick={() => setActiveTab("matrix")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  activeTab === "matrix" ? "bg-white text-neutral-900 shadow-xs" : "text-neutral-600 hover:text-neutral-900"
                }`}
              >
                <Layers className="w-3.5 h-3.5" />
                <span>Matrix</span>
              </button>
              <button
                onClick={() => setActiveTab("chat")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  activeTab === "chat" ? "bg-white text-neutral-900 shadow-xs" : "text-neutral-600 hover:text-neutral-900"
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
        isCompleted={isCompleted}
        onComplete={() => setIsCompleted(true)}
      />

      {/* Synthesis Report & Methodology Matrix Views */}
      {isCompleted && (
        <div className="animate-in fade-in duration-300">
          {activeTab === "report" && (
            <SynthesisReportViewer report={sampleReport} />
          )}

          {activeTab === "matrix" && (
            <MethodologyMatrix matrix={sampleReport.methodology_matrix} />
          )}

          {activeTab === "chat" && (
            <ReviewChat reviewId={reviewId || "default"} />
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

export default ReviewDetail;
