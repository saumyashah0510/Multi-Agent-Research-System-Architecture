// Shared TypeScript Type Definitions for Scholaris Multi-Agent Research System

export interface Paper {
  id: string;
  title: string;
  authors: string[];
  abstract: string;
  publishedYear: number;
  url?: string;
  venue?: string;
  citationCount?: number;
  relevanceScore?: number;
  isSelected?: boolean;
}

export type PipelineStep =
  | "idle"
  | "discovering"
  | "screening"
  | "human_in_loop"
  | "synthesizing"
  | "completed"
  | "failed";

export interface AgentLog {
  id: string;
  timestamp: string;
  agentName: "SearchAgent" | "ScreeningAgent" | "SynthesisAgent" | "Orchestrator";
  message: string;
  level: "info" | "success" | "warning" | "error";
}

export interface SynthesizedReport {
  title: string;
  summary: string;
  keyThemes: string[];
  methodologyMatrix?: Array<{
    paperTitle: string;
    methodology: string;
    findings: string;
  }>;
  researchGaps: string[];
  references: string[];
}

export interface ReviewTask {
  id: string;
  query: string;
  status: PipelineStep;
  createdAt: string;
  discoveredPapers: Paper[];
  screenedPapers: Paper[];
  approvedPapers: Paper[];
  synthesizedReview?: SynthesizedReport;
  logs?: AgentLog[];
}

export interface HealthStatusResponse {
  status: string;
  timestamp: string;
  services: {
    database: string;
    redis: string;
  };
}
