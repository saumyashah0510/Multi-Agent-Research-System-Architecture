import { cn } from "../../lib/utils";
import type { PipelineStep } from "../../types";

export interface AgentFeedProps {
  status: PipelineStep;
  reviewId?: string | null;
  className?: string;
}

interface StepDefinition {
  key: PipelineStep;
  label: string;
  description: string;
}

const pipelineSteps: StepDefinition[] = [
  {
    key: "discovering",
    label: "Literature Discovery",
    description: "Searching ArXiv, PubMed Central, and OpenAlex databases...",
  },
  {
    key: "screening",
    label: "Semantic Screening",
    description: "Filtering relevance and scoring preprints...",
  },
  {
    key: "human_in_loop",
    label: "Human Approval",
    description: "Awaiting human approval for candidate papers...",
  },
  {
    key: "synthesizing",
    label: "Multi-Paper Synthesis",
    description: "Synthesizing report...",
  },
  {
    key: "completed",
    label: "Report Completion",
    description: "Structured academic literature review synthesized.",
  },
];

function getStepOrder(step: PipelineStep): number {
  switch (step) {
    case "discovering":
      return 0;
    case "screening":
      return 1;
    case "human_in_loop":
      return 2;
    case "synthesizing":
      return 3;
    case "completed":
      return 4;
    case "failed":
      return -1;
    default:
      return 0;
  }
}

export default function AgentFeed({
  status,
  reviewId,
  className = "",
}: AgentFeedProps) {
  const currentOrder = getStepOrder(status);
  const isFailed = status === "failed";

  return (
    <div className={cn("w-full bg-white rounded-2xl border border-neutral-200/80 shadow-xs p-6 sm:p-8 space-y-6 animate-in fade-in duration-300", className)}>
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-neutral-100">
        <div>
          <h2 className="font-serif text-xl sm:text-2xl font-bold text-neutral-900 tracking-compact">
            Agent Progress Feed
          </h2>
          <p className="text-xs text-neutral-500 mt-0.5">
            Backend Pipeline Status {reviewId ? `· Session ${reviewId}` : ""}
          </p>
        </div>

        {/* Status Badge */}
        <div
          className={cn(
            "inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold shadow-xs transition-colors",
            status === "completed" && "bg-emerald-50 text-emerald-800 border border-emerald-200",
            status === "failed" && "bg-red-50 text-red-800 border border-red-200",
            (status === "synthesizing" || status === "discovering" || status === "screening") &&
              "bg-sky-50 text-sky-800 border border-sky-200 animate-pulse",
            status === "human_in_loop" && "bg-amber-50 text-amber-800 border border-amber-200"
          )}
        >
          <span className="w-2 h-2 rounded-full bg-current" />
          <span className="capitalize">{status.replace("_", " ")}</span>
        </div>
      </div>

      {/* Timeline Steps List */}
      <div className="space-y-4">
        {pipelineSteps.map((step, idx) => {
          const stepOrder = getStepOrder(step.key);
          const isDone = !isFailed && currentOrder > stepOrder;
          const isActive = !isFailed && currentOrder === stepOrder;
          const isPending = !isFailed && currentOrder < stepOrder;
          const isStepFailed = isFailed && idx === Math.max(0, currentOrder);

          return (
            <div
              key={step.key}
              className={cn(
                "flex items-start gap-4 p-3.5 rounded-xl border transition-all",
                isActive && "bg-neutral-50/80 border-neutral-300 shadow-2xs",
                isDone && "bg-white border-neutral-200/60 opacity-90",
                isPending && "bg-neutral-50/30 border-neutral-100 opacity-50",
                isStepFailed && "bg-red-50/50 border-red-200 text-red-900"
              )}
            >
              {/* Step Indicator Circle */}
              <div className="shrink-0 mt-0.5">
                {isDone ? (
                  <div className="w-6 h-6 rounded-full bg-[var(--color-success)] flex items-center justify-center text-white shadow-xs">
                    <svg className="w-3.5 h-3.5 stroke-[3]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                ) : isActive ? (
                  <div className="relative w-6 h-6 flex items-center justify-center">
                    <div className="absolute inset-0 rounded-full border-2 border-[var(--color-primary-blue)] opacity-30 animate-ping" />
                    <div className="w-5 h-5 rounded-full border-2 border-[var(--color-primary-blue)] border-t-transparent animate-spin" />
                  </div>
                ) : isStepFailed ? (
                  <div className="w-6 h-6 rounded-full bg-red-600 flex items-center justify-center text-white font-bold text-xs">
                    ✕
                  </div>
                ) : (
                  <div className="w-6 h-6 rounded-full border-2 border-neutral-300 bg-white flex items-center justify-center text-[10px] font-bold text-neutral-400">
                    {idx + 1}
                  </div>
                )}
              </div>

              {/* Step Details */}
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-semibold text-neutral-900 font-sans-ui tracking-compact">
                  {step.label}
                </h3>
                <p className="text-xs text-neutral-500 mt-0.5 leading-relaxed font-sans-ui">
                  {step.description}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
