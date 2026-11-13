import React from "react";
import { motion, useReducedMotion } from "framer-motion";
import {
  Sparkles,
  Search,
  Filter,
  LoaderCircle,
  CircleAlert,
  CircleCheck,
  FileText,
  Layers,
  GitCompare,
  ShieldCheck,
  BookOpen,
} from "lucide-react";
import { PipelineStage } from "./types";

interface StageCardProps {
  stage: PipelineStage;
  index: number;
  isCompact?: boolean;
}

interface StageStyleConfig {
  icon: React.ReactNode;
  bg: string;
  border: string;
  activeBorder: string;
  activeRing: string;
}

const DEFAULT_CONFIG: StageStyleConfig = {
  icon: <Sparkles className="w-4 h-4 text-neutral-800/80 shrink-0" aria-hidden="true" />,
  bg: "var(--tint-mint)",
  border: "border-[#bfe8b2]",
  activeBorder: "border-[#a5df97]",
  activeRing: "ring-[var(--color-success)]/20",
};

const STAGE_CONFIG: Record<string, StageStyleConfig> = {
  "query-expansion": DEFAULT_CONFIG,
  "academic-search": {
    icon: <Search className="w-4 h-4 text-neutral-800/80 shrink-0" aria-hidden="true" />,
    bg: "var(--tint-sky)",
    border: "border-[#b2dbfa]",
    activeBorder: "border-[#9ed2fa]",
    activeRing: "ring-blue-500/20",
  },
  "relevance-screening": {
    icon: <Filter className="w-4 h-4 text-neutral-800/80 shrink-0" aria-hidden="true" />,
    bg: "var(--tint-lavender)",
    border: "border-[#c2c5f6]",
    activeBorder: "border-[#b3b7f5]",
    activeRing: "ring-indigo-500/20",
  },
  "pdf-extraction": {
    icon: <FileText className="w-4 h-4 text-neutral-800/80 shrink-0" aria-hidden="true" />,
    bg: "var(--tint-sky)",
    border: "border-[#b2dbfa]",
    activeBorder: "border-[#9ed2fa]",
    activeRing: "ring-blue-500/20",
  },
  "vector-embedding": {
    icon: <Layers className="w-4 h-4 text-neutral-800/80 shrink-0" aria-hidden="true" />,
    bg: "var(--tint-lavender)",
    border: "border-[#c2c5f6]",
    activeBorder: "border-[#b3b7f5]",
    activeRing: "ring-indigo-500/20",
  },
  "gap-analysis": {
    icon: <GitCompare className="w-4 h-4 text-neutral-800/80 shrink-0" aria-hidden="true" />,
    bg: "var(--tint-mint)",
    border: "border-[#bfe8b2]",
    activeBorder: "border-[#a5df97]",
    activeRing: "ring-[var(--color-success)]/20",
  },
  "citation-verification": {
    icon: <ShieldCheck className="w-4 h-4 text-neutral-800/80 shrink-0" aria-hidden="true" />,
    bg: "var(--tint-sky)",
    border: "border-[#b2dbfa]",
    activeBorder: "border-[#9ed2fa]",
    activeRing: "ring-blue-500/20",
  },
  "report-synthesis": {
    icon: <BookOpen className="w-4 h-4 text-neutral-800/80 shrink-0" aria-hidden="true" />,
    bg: "var(--tint-mint)",
    border: "border-[#bfe8b2]",
    activeBorder: "border-[#a5df97]",
    activeRing: "ring-[var(--color-success)]/20",
  },
};

export const StageCard: React.FC<StageCardProps> = ({
  stage,
  index,
  isCompact = false,
}) => {
  const shouldReduceMotion = useReducedMotion();
  const config = STAGE_CONFIG[stage.id] ?? DEFAULT_CONFIG;

  const isQueued = stage.status === "pending" || isCompact;

  const cardStyleClass =
    stage.status === "failed"
      ? "bg-red-50 border-red-200 text-red-950 shadow-xs"
      : stage.status === "running"
      ? `${config.activeBorder} shadow-md ring-2 ${config.activeRing} text-neutral-900`
      : `${config.border} shadow-xs text-neutral-900 ${
          isQueued ? "opacity-75 hover:opacity-100" : ""
        }`;

  return (
    <motion.article
      initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: index * 0.05, ease: "easeOut" }}
      className={`w-full rounded-2xl border transition-all duration-300 relative overflow-hidden ${
        isQueued ? "p-3 sm:p-3.5" : "p-4 sm:p-5"
      } ${cardStyleClass}`}
      style={{ backgroundColor: stage.status === "failed" ? undefined : config.bg }}
      aria-label={`${stage.title} - Status: ${stage.status}`}
    >
      {/* Top Header Row: Title and subtle icon */}
      <div className={`flex items-center justify-between gap-3 ${isQueued ? "mb-0" : "mb-1"}`}>
        <h3
          className={`font-serif tracking-compact text-neutral-900 leading-[1.1] ${
            isQueued
              ? "text-[15px] sm:text-[15.5px] font-normal text-neutral-700"
              : "text-[17px] sm:text-[18px] font-medium"
          }`}
        >
          {stage.title}
        </h3>
        <div className="opacity-70 hover:opacity-100 transition-opacity">
          {config.icon}
        </div>
      </div>

      {/* Main Description (collapsed when queued/pending) */}
      {!isQueued && (
        <p className="font-sans text-[13px] sm:text-[13.5px] text-neutral-700 leading-snug">
          {stage.description}
        </p>
      )}

      {/* Supporting Status / Activity Detail (only when active/running) */}
      {!isQueued && stage.status === "running" && (
        <p className="font-sans text-[11.5px] sm:text-[12px] text-neutral-500 mt-0.5 leading-normal">
          {stage.supportingStatus}
        </p>
      )}

      {/* Genuine Progress Bar (rendered only if genuine 0-100 numerical progress exists) */}
      {stage.status === "running" && typeof stage.progress === "number" && (
        <div className="mt-2.5 w-full bg-[var(--tint-sky)] rounded-full h-1 overflow-hidden border border-[var(--color-pill-sky)]">
          <div
            className="bg-[var(--color-sky-dark)] h-full rounded-full transition-all duration-300"
            style={{ width: `${Math.min(Math.max(stage.progress, 0), 100)}%` }}
          />
        </div>
      )}

      {/* Completed Result Row with Library-Imported CircleCheck */}
      {stage.status === "completed" && stage.result && (
        <div
          className={`${
            isQueued ? "mt-1.5" : "mt-3"
          } flex items-center gap-2 text-[12px] sm:text-[12.5px] font-medium text-neutral-800`}
        >
          <CircleCheck className="w-4 h-4 text-[var(--color-success)] shrink-0 stroke-[2.2]" />
          <span>{stage.result}</span>
        </div>
      )}

      {/* Running Animated Status Indicator */}
      {stage.status === "running" && (
        <div className="mt-3 flex items-center gap-2 text-[12.5px] sm:text-[13px] font-semibold text-[var(--color-sky-dark)]">
          <LoaderCircle
            className="w-4 h-4 text-[var(--color-sky-dark)] animate-spin shrink-0 stroke-[2.5]"
            aria-hidden="true"
          />
          <span>{stage.message || stage.supportingStatus}</span>
        </div>
      )}

      {/* Failed Error Row */}
      {stage.status === "failed" && (
        <div className="mt-3 flex items-center gap-2 text-[12.5px] sm:text-[13px] font-medium text-red-800">
          <CircleAlert className="w-4 h-4 text-red-600 shrink-0" aria-hidden="true" />
          <span>{stage.error || "An error occurred while processing this stage."}</span>
        </div>
      )}
    </motion.article>
  );
};
