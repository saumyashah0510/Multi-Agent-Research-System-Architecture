/**
 * DownstreamProgress Component (Agents 05 to 09)
 *
 * Assignee Task (Issue FE-07):
 * - Render downstream pipeline stages on /review/:reviewId
 *   (PDF Extraction, Vector Embedding, Gap Analysis, Citation Verification, Report Synthesis)
 * - Display sequential progress indicators and status animations
 * - Auto-collapse upon completion and trigger onComplete callback
 */

import React, { useState, useEffect } from "react";
import { Sparkles, CircleCheck, ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "../../lib/utils";
import { PipelineStage, DOWNSTREAM_PIPELINE_STAGES } from "./types";
import { StageTimelineNode } from "./StageTimelineNode";
import { StageCard } from "./StageCard";

export interface DownstreamProgressProps {
  stages?: PipelineStage[];
  isRunning?: boolean;
  isCompleted?: boolean;
  onComplete?: () => void;
  className?: string;
}

export const DownstreamProgress: React.FC<DownstreamProgressProps> = ({
  stages = DOWNSTREAM_PIPELINE_STAGES,
  isRunning = true,
  isCompleted = false,
  onComplete,
  className = "",
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  useEffect(() => {
    if (isCompleted) {
      setIsCollapsed(true);
      if (onComplete) onComplete();
    }
  }, [isCompleted, onComplete]);

  // TODO (Assignee - FE-07):
  // 1. Listen for WebSocket messages from /api/v1/ws/reviews/{reviewId}
  // 2. Transition stages: PDF_EXTRACTION -> VECTOR_EMBEDDING -> GAP_ANALYSIS -> CITATION_VERIFICATION -> REPORT_SYNTHESIS
  // 3. Mark each stage "completed" and update the final result message
  // 4. When REPORT_SYNTHESIS completes, set isCompleted to true

  return (
    <div
      className={cn(
        "w-full bg-white rounded-2xl border border-neutral-200/90 shadow-xs p-5 sm:p-6 transition-all duration-300",
        className
      )}
    >
      {/* Header Bar */}
      <div className="flex items-center justify-between pb-4 border-b border-neutral-100">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-[var(--color-accent)]/20 flex items-center justify-center text-[var(--color-accent-dark)]">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-serif text-lg sm:text-xl font-bold text-neutral-900 tracking-compact">
                Synthesis & Deep Analysis
              </h2>
              <span
                className={cn(
                  "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold",
                  isCompleted
                    ? "bg-[var(--color-success-light)] text-[var(--color-success-dark)]"
                    : "bg-blue-50 text-blue-700"
                )}
              >
                {isCompleted ? (
                  <>
                    <CircleCheck className="w-3 h-3" />
                    <span>Completed</span>
                  </>
                ) : isRunning ? (
                  <>
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse" />
                    <span>Processing</span>
                  </>
                ) : (
                  <span>Queued</span>
                )}
              </span>
            </div>
            <p className="text-xs text-neutral-500 mt-0.5">
              Extracting full-text PDFs, building vector indices, analyzing gaps, and synthesizing report
            </p>
          </div>
        </div>

        {/* Collapse Toggle */}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-1.5 text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
          aria-label={isCollapsed ? "Expand pipeline" : "Collapse pipeline"}
        >
          {isCollapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
        </button>
      </div>

      {/* Stages List */}
      {!isCollapsed && (
        <div className="mt-5 flex flex-col">
          {stages.map((stage, index) => (
            <div
              key={stage.id}
              className="relative flex items-start gap-3 sm:gap-4 pb-3.5 last:pb-0 z-10"
            >
              <div className="shrink-0 pt-3 flex items-center justify-center">
                <StageTimelineNode status={stage.status} />
              </div>
              <div className="flex-1 min-w-0">
                <StageCard stage={stage} index={index} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default DownstreamProgress;
