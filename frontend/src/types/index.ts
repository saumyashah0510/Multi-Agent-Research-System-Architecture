// Shared TypeScript Type Definitions
export interface Paper {
  id: string;
  title: string;
  authors: string[];
  abstract: string;
  publishedYear: number;
  isSelected?: boolean;
}

export interface ReviewTask {
  id: string;
  query: string;
  status: "pending" | "discovering" | "screening" | "synthesizing" | "completed";
  papers: Paper[];
}
