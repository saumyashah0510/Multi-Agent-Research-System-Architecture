import React, { useState, useEffect } from "react";
import { Sparkles, CircleCheck, ChevronDown, ChevronUp, RotateCcw } from "lucide-react";
import { cn } from "../../lib/utils";
import { PipelineStage } from "./types";
import { StageTimelineNode } from "./StageTimelineNode";
import { StageCard } from "./StageCard";
import { useMockPipeline } from "./useMockPipeline";

export interface ResearchProgressProps {
  /** Optional custom stages for real agent integration */
  stages?: PipelineStage[];
  /** Flag indicating whether the pipeline is currently executing */
  isRunning?: boolean;
  /** Flag indicating whether all pipeline stages have completed */
  isCompleted?: boolean;
  /** Active research query */
  query?: string;
  /** Flag indicating whether this is mock demonstration mode */
  isMock?: boolean;
  /** Auto start simulation */
  autoStart?: boolean;
  /** Callback fired when pipeline completes */
  onComplete?: () => void;
  /** Callback for Find More Papers button in the merged card */
  onFindMore?: () => void;
  /** Loading flag when finding more papers */
  isFindingMore?: boolean;
}

export const ResearchProgress: React.FC<ResearchProgressProps> = ({
  stages: customStages,
  isRunning: customIsRunning,
  isCompleted: customIsCompleted,
  query,
  isMock: customIsMock,
  autoStart = true,
  onComplete,
  onFindMore,
  isFindingMore = false,
}) => {
  const mock = useMockPipeline({ autoStart, query, onComplete });

  const stages = customStages ?? mock.stages;
  const isRunning = customIsRunning ?? mock.isRunning;
  const isCompleted = customIsCompleted ?? mock.isCompleted;
  const isMock = customIsMock ?? mock.isMock;

  const [isCollapsed, setIsCollapsed] = useState(false);

  useEffect(() => {
    setIsCollapsed(Boolean(isCompleted));
  }, [isCompleted]);

  const renderStagesList = () => (
    <div className="flex flex-col">
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
  );

  // UNIFIED MERGED CARD VIEW (shown when pipeline is completed)
  if (isCompleted) {
    return (
      <section
        aria-label="Research Progress and Paper Status"
        className="w-full bg-white rounded-2xl border border-neutral-200/80 shadow-xs overflow-hidden transition-all duration-200 animate-in fade-in"
      >
        {/* Top Header Row: Status, Title, Matching Completed Pill, and View Details Toggle */}
        <div className="px-4 sm:px-6 py-3.5 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <CircleCheck className="w-6 h-6 sm:w-6.5 sm:h-6.5 text-[var(--color-success)] stroke-[2.2] shrink-0" />

            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-serif text-[17px] font-medium tracking-compact text-neutral-900">
                  Research Progress
                </h3>
                <span className="text-[11px] font-semibold bg-[var(--color-success-light)] text-[var(--color-success-dark)] border border-[var(--color-success)]/30 px-2.5 py-0.5 rounded-full">
                  Completed
                </span>
              </div>
              <p className="font-sans text-xs text-neutral-500 mt-0.5">
                3 stages finished · 24 papers screened · 10 relevant papers retained
              </p>
            </div>
          </div>

          {/* Action Buttons: Find More Papers & Toggle details */}
          <div className="flex items-center gap-2">
            {onFindMore && (
              <button
                type="button"
                onClick={onFindMore}
                disabled={isFindingMore}
                title="Search academic sources for more candidate papers"
                className={cn(
                  "text-xs font-semibold px-3.5 py-1.5 rounded-full shadow-xs transition-all tracking-compact flex items-center gap-1.5 cursor-pointer",
                  isFindingMore
                    ? "bg-neutral-200 text-neutral-400 cursor-wait"
                    : "bg-neutral-900 hover:bg-black text-white hover:scale-[1.02] active:scale-95"
                )}
              >
                {isFindingMore ? (
                  <>
                    <svg className="animate-spin h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                    </svg>
                    <span>Searching...</span>
                  </>
                ) : (
                  <>
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Find More Papers</span>
                  </>
                )}
              </button>
            )}

            <button
              type="button"
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium text-neutral-800 bg-neutral-100 hover:bg-neutral-200 active:scale-95 transition-all cursor-pointer border border-neutral-200/80 shadow-2xs"
              aria-expanded={!isCollapsed}
              aria-label={isCollapsed ? "View details of research pipeline" : "Hide details of research pipeline"}
            >
              <span>{isCollapsed ? "View details" : "Hide details"}</span>
              {isCollapsed ? (
                <ChevronDown className="w-3.5 h-3.5 text-neutral-600" />
              ) : (
                <ChevronUp className="w-3.5 h-3.5 text-neutral-600" />
              )}
            </button>
          </div>
        </div>

        {/* Expandable Details Body */}
        {!isCollapsed && (
          <div className="px-4 sm:px-6 pb-5 pt-2 border-t border-neutral-100 animate-in fade-in duration-200">
            <div className="mt-3">
              {renderStagesList()}
            </div>
          </div>
        )}
      </section>
    );
  }

  // ACTIVE PROCESSING / LOADING STATE
  return (
    <section
      aria-label="Research Pipeline Progress"
      className="w-full bg-white rounded-3xl border border-neutral-200/90 shadow-[0_4px_24px_rgba(0,0,0,0.03)] p-5 sm:p-7 md:p-8 transition-all"
    >
      {/* Header Row: Title, Subtitle, and Mock Indicator */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 pb-5 border-b border-neutral-100">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="font-serif text-xl sm:text-2xl font-normal tracking-compact text-neutral-900 leading-[1.1]">
              Research Progress
            </h2>
            {isRunning && (
              <span className="inline-flex items-center gap-1 text-[11px] font-medium text-blue-700 bg-blue-50 border border-blue-200/60 px-2 py-0.5 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse" />
                Processing
              </span>
            )}
          </div>
          <p className="font-sans text-xs sm:text-[13px] text-neutral-500 mt-1">
            Your literature review is being processed step by step
          </p>
        </div>

        {isMock && (
          <span
            className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-neutral-100 text-neutral-600 border border-neutral-200/80 shadow-2xs select-none self-start sm:self-auto"
            title="Demonstration mode: Pipeline steps are simulated locally"
          >
            <Sparkles className="w-3 h-3 text-neutral-400" aria-hidden="true" />
            Simulated progress
          </span>
        )}
      </div>

      {/* 3 Stages Stack */}
      <div className="mt-6">
        {renderStagesList()}
      </div>
    </section>
  );
};

export default ResearchProgress;
