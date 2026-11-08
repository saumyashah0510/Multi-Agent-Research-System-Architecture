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
import { Sparkles, CircleCheck, AlertCircle, ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "../../lib/utils";
import { PipelineStage, DOWNSTREAM_PIPELINE_STAGES } from "./types";
import { StageTimelineNode } from "./StageTimelineNode";
import { StageCard } from "./StageCard";
import { useDownstreamWebSocket } from "../../hooks/useDownstreamWebSocket";

export interface DownstreamProgressProps {
  stages?: PipelineStage[];
  isRunning?: boolean;
  isCompleted?: boolean;
  onComplete?: () => void;
  className?: string;
  reviewId?: string;
  isMock?: boolean;
}

export const DownstreamProgress: React.FC<DownstreamProgressProps> = ({
  stages: customStages,
  isRunning: customIsRunning,
  isCompleted: customIsCompleted = false,
  onComplete,
  className = "",
  reviewId,
  isMock = false,
}) => {
  const ws = useDownstreamWebSocket(reviewId, {
    onComplete,
    isMock,
    initialCompleted: customIsCompleted,
  });

  const stages = customStages ?? ws.stages ?? DOWNSTREAM_PIPELINE_STAGES;
  const isRunning = customIsRunning ?? ws.isRunning;
  const isCompleted = customIsCompleted || ws.isCompleted;
  const isFailed = !isCompleted && (ws.status === "FAILED" || Boolean(ws.error));

  const [isCollapsed, setIsCollapsed] = useState(isCompleted);

  useEffect(() => {
    if (isCompleted) {
      setIsCollapsed(true);
    }
  }, [isCompleted]);

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
          <div className="w-8 h-8 rounded-full bg-[var(--color-accent)]/20 flex items-center justify-center text-[var(--color-accent-dark)] shrink-0">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="font-serif text-lg sm:text-xl font-bold text-neutral-900 tracking-compact">
                Synthesis & Deep Analysis
              </h2>
              <span
                className={cn(
                  "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold",
                  isCompleted
                    ? "bg-[var(--color-success-light)] text-[var(--color-success-dark)] border border-[var(--color-success)]/30"
                    : isFailed
                    ? "bg-red-50 text-red-700 border border-red-200"
                    : isRunning
                    ? "bg-blue-50 text-blue-700 border border-blue-200"
                    : "bg-neutral-100 text-neutral-600 border border-neutral-200"
                )}
              >
                {isCompleted ? (
                  <>
                    <CircleCheck className="w-3 h-3 text-[var(--color-success)]" />
                    <span>Completed</span>
                  </>
                ) : isFailed ? (
                  <>
                    <AlertCircle className="w-3 h-3 text-red-600" />
                    <span>Failed</span>
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
              {isCompleted
                ? "All 5 downstream agents finished · Synthesis report & methodology matrix ready"
                : isFailed
                ? ws.error || "Downstream analysis encountered an issue"
                : "Extracting full-text PDFs, building vector indices, analyzing gaps, and synthesizing report"}
            </p>
          </div>
        </div>

        {/* Collapse Toggle */}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-1.5 text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors cursor-pointer shrink-0"
          aria-expanded={!isCollapsed}
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
