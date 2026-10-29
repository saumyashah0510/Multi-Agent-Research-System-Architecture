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

// 12 Unified Review Lifecycle & Agent Status Enums (1-to-1 Agent Mapping)
export type ReviewStatus =
  | "PENDING"
  | "QUERY_EXPANSION"        // Agent 01
  | "PAPER_DISCOVERY"        // Agent 02
  | "SCREENING"              // Agent 03
  | "AWAITING_USER_INPUT"    // Agent 04 (HITL Interrupt)
  | "PDF_EXTRACTION"         // Agent 05
  | "VECTOR_EMBEDDING"       // Agent 06
  | "GAP_ANALYSIS"           // Agent 07
  | "CITATION_VERIFICATION"  // Agent 08
  | "REPORT_SYNTHESIS"       // Agent 09
  | "COMPLETED"
  | "FAILED";

export interface AgentLog {
  id: string;
  timestamp: string;
  agentName: "SearchAgent" | "ScreeningAgent" | "SynthesisAgent" | "Orchestrator";
  message: string;
  level: "info" | "success" | "warning" | "error";
}

export interface MethodologyItem {
  method_name: string;
  papers_used: string[];
  strengths: string[];
  limitations: string[];
}

export interface ThematicCluster {
  theme: string;
  summary: string;
  citations: string[];
}

export interface SynthesizedReview {
  title: string;
  executive_summary: string;
  thematic_clusters: ThematicCluster[];
  methodology_matrix: MethodologyItem[];
  research_gaps: string[];
  conclusion?: string;
  references?: Array<{
    title?: string;
    authors?: string[];
    year?: number;
    url?: string;
    matched_passage?: string;
  }>;
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

export interface SourceChunk {
  chunk_id: number;
  paper_id?: number;
  title: string;
  text: string;
  relevance_score: number;
}

export interface ChatMessage {
  id?: string;
  role: "user" | "assistant";
  content: string;
  timestamp?: string;
  sources?: SourceChunk[];
}

export interface ChatResponse {
  response: string;
  sources: SourceChunk[];
}

export interface ReviewHistoryItem {
  id: string;
  query: string;
  status:
    | "pending"
    | "discovering"
    | "awaiting_approval"
    | "extracting"
    | "embedding"
    | "synthesizing"
    | "completed"
    | "failed";
  paper_count?: number;
  created_at: string;
  pdf_url?: string;
}
