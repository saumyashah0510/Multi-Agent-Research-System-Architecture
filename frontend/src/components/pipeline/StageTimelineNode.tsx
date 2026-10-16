import React from "react";
import { CircleCheck, CircleAlert } from "lucide-react";
import { StageStatus } from "./types";

interface StageTimelineNodeProps {
  status: StageStatus;
  className?: string;
}

export const StageTimelineNode: React.FC<StageTimelineNodeProps> = ({
  status,
  className = "",
}) => {
  return (
    <div
      className={`relative flex items-center justify-center shrink-0 w-8 h-8 ${className}`}
      aria-hidden="true"
    >
      {status === "completed" && (
        <div className="flex items-center justify-center w-8 h-8 transition-transform duration-200">
          {/* Library-imported CircleCheck */}
          <CircleCheck
            className="w-7 h-7 sm:w-8 sm:h-8 text-[var(--color-success)] stroke-[2.2]"
            aria-label="Stage completed"
          />
        </div>
      )}

      {status === "running" && (
        <div
          className="w-7 h-7 sm:w-7.5 sm:h-7.5 rounded-full border-2 border-[var(--color-primary-blue)] bg-white flex items-center justify-center shadow-xs"
          title="Stage in progress"
        >
          <div className="w-3 h-3 rounded-full border-2 border-[var(--color-primary-blue)] border-t-transparent animate-spin" />
        </div>
      )}

      {status === "pending" && (
        <div
          className="w-7 h-7 sm:w-7.5 sm:h-7.5 rounded-full border-2 border-neutral-300 bg-white shadow-xs"
          title="Stage pending"
        />
      )}

      {status === "failed" && (
        <div
          className="w-7 h-7 sm:w-7.5 sm:h-7.5 rounded-full bg-red-600 text-white flex items-center justify-center shadow-xs"
          title="Stage failed"
        >
          <CircleAlert className="w-4 h-4 stroke-[2.5]" />
        </div>
      )}
    </div>
  );
};
