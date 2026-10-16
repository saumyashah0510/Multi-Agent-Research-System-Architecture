export type StageStatus = "pending" | "running" | "completed" | "failed";

export interface PipelineStage {
  id: string;
  title: string;
  description: string;
  supportingStatus: string;
  status: StageStatus;
  message?: string | null;
  detail?: string | null;
  progress?: number | null; // Genuine progress percentage (0 - 100) if available, otherwise null
  result?: string | null;
  error?: string | null;
}

export interface PipelineProgressState {
  stages: PipelineStage[];
  isCompleted: boolean;
  isMock: boolean;
  activeStageId: string | null;
  query?: string;
  totalPapersScreened?: number;
  relevantPapersRetained?: number;
}

export const INITIAL_DEMO_STAGES: PipelineStage[] = [
  {
    id: "query-expansion",
    title: "Query Expansion",
    description: "Generating focused search queries from your research topic.",
    supportingStatus: "Identifying related terminology, concepts, and academic keywords...",
    status: "pending",
    message: null,
    detail: null,
    progress: null,
    result: "3 search queries generated",
    error: null,
  },
  {
    id: "academic-search",
    title: "Academic Search",
    description: "Searching multiple academic sources for relevant literature.",
    supportingStatus: "Searching arXiv, Semantic Scholar and Crossref...",
    status: "pending",
    message: null,
    detail: null,
    progress: null,
    result: "24 candidate papers discovered",
    error: null,
  },
  {
    id: "relevance-screening",
    title: "Relevance Screening",
    description: "Evaluating discovered papers against your research topic.",
    supportingStatus: "Scoring papers for relevance and filtering low-value results...",
    status: "pending",
    message: null,
    detail: null,
    progress: null,
    result: "24 papers screened · 10 relevant papers retained",
    error: null,
  },
];
