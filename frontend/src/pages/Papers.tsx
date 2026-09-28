import React, { useState, useRef } from "react";
import { Card } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";

interface Paper {
  id: string;
  title: string;
  authors: string;
  venue: string;
  year: number;
  citations: number;
  relevance: number;
  status: "approved" | "screened" | "pending";
  abstract: string;
  tags: string[];
}

const initialPapers: Paper[] = [
  {
    id: "1",
    title: "Benchmarking Adaptive Retrieval Strategies in Multi-Hop Reasoning",
    authors: "Elena Rostova, Marcus Vance, Priya Sharma, et al.",
    venue: "arXiv:2403.08119 [cs.AI]",
    year: 2024,
    citations: 142,
    relevance: 98,
    status: "approved",
    abstract:
      "We propose an iterative graph-guided retrieval mechanism that dynamically decides when and what to retrieve for complex multi-agent reasoning tasks, reducing hallucination rates by 41% across standard question-answering benchmarks.",
    tags: ["Adaptive Retrieval", "Multi-Hop", "Hallucination Reduction", "LangGraph"],
  },
  {
    id: "2",
    title: "Self-Correction and Verification Loops in Agentic Literature Synthesis",
    authors: "Julian Thorne, Sarah Lin, David K. Miller",
    venue: "NeurIPS 2024 Preprints",
    year: 2024,
    citations: 89,
    relevance: 94,
    status: "approved",
    abstract:
      "This paper analyzes automated verification feedback loops that prevent error propagation in multi-agent literature synthesis. We present a formal Taxonomy of Synthesis Errors and demonstrate verifiable consensus generation.",
    tags: ["Agentic Synthesis", "Self-Correction", "Literature Review", "Verification"],
  },
  {
    id: "3",
    title: "Dense Passage Embeddings vs. Hybrid Sparse-Dense Search for Scientific Literature",
    authors: "Kenji Sato, Arthur Pendelton, Xiao Chen",
    venue: "ACL 2023 Findings",
    year: 2023,
    citations: 215,
    relevance: 91,
    status: "screened",
    abstract:
      "A systematic comparison of BM25, ColBERT, and modern dense bi-encoder models across biomedical and computer science paper corpora, uncovering key retrieval failure modes on mathematical equations.",
    tags: ["Vector Search", "Hybrid Retrieval", "BM25", "ColBERT"],
  },
  {
    id: "4",
    title: "Automated Systematic Literature Reviews: Opportunities and Limitations with LLMs",
    authors: "Rachel Green, Thomas O'Connor, Amir Habib",
    venue: "IEEE Transactions on Software Engineering 2024",
    year: 2024,
    citations: 64,
    relevance: 87,
    status: "pending",
    abstract:
      "We evaluate autonomous LLM pipelines on systematic literature mapping according to PRISMA guidelines. Human-in-the-loop screening remains crucial for nuanced boundary cases and niche methodological nuances.",
    tags: ["Systematic Review", "PRISMA", "Human-in-the-Loop", "Evaluation"],
  },
];

export default function Papers() {
  const [papers, setPapers] = useState<Paper[]>(initialPapers);
  const [filter, setFilter] = useState<"all" | "approved" | "screened" | "pending">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const filteredPapers = papers.filter((paper) => {
    const matchesFilter = filter === "all" || paper.status === filter;
    const matchesSearch =
      paper.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      paper.authors.toLowerCase().includes(searchQuery.toLowerCase()) ||
      paper.tags.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesFilter && matchesSearch;
  });

  const handleCopyBibtex = (paper: Paper) => {
    const bibtex = `@article{${paper.id}_${paper.year},
  title={${paper.title}},
  author={${paper.authors}},
  journal={${paper.venue}},
  year={${paper.year}}
}`;
    navigator.clipboard.writeText(bibtex);
    setCopiedId(paper.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleUploadPaper = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const newPaper: Paper = {
        id: String(Date.now()),
        title: file.name.replace(/\.[^/.]+$/, ""),
        authors: "Uploaded Document • Local Corpus",
        venue: "Manual Ingestion / PDF",
        year: 2025,
        citations: 0,
        relevance: 100,
        status: "approved",
        abstract: "Custom uploaded paper pending multi-agent extraction and semantic indexing.",
        tags: ["Uploaded Document", "Custom Ingestion"],
      };
      setPapers([newPaper, ...papers]);
    }
  };

  return (
    <div id="papers-page" className="w-full space-y-8 max-w-6xl mx-auto">
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleUploadPaper}
        accept=".pdf,.doc,.docx"
        className="hidden"
      />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-black/5 pb-6">
        <div>
          <h1 className="font-serif text-3xl sm:text-4xl font-normal text-neutral-900 tracking-tight">
            Academic Papers Library
          </h1>
          <p className="text-sm text-neutral-600 mt-1 font-sans-ui">
            Curate, screen, and inspect discovered preprints and peer-reviewed literature.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={() => fileInputRef.current?.click()}
            leftIcon={<span>📄</span>}
            className="text-xs sm:text-sm"
          >
            Upload PDF
          </Button>
          <Button
            variant="default"
            onClick={() => {
              const allBib = papers
                .map(
                  (p) => `@article{${p.id}, title={${p.title}}, author={${p.authors}}, year={${p.year}}}`
                )
                .join("\n\n");
              navigator.clipboard.writeText(allBib);
              alert("All citations copied to clipboard in BibTeX format!");
            }}
            className="text-xs sm:text-sm"
          >
            Export All BibTeX
          </Button>
        </div>
      </div>

      {/* Search & Filter Tabs Bar */}
      <div className="flex flex-col sm:flex-row gap-4 items-stretch sm:items-center justify-between">
        {/* Search Input */}
        <div className="relative flex-1 max-w-md">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search papers by title, author, or keyword..."
            className="w-full bg-white rounded-full px-4 py-2.5 pl-10 text-sm border border-neutral-200/80 shadow-xs outline-none focus:ring-2 focus:ring-black tracking-compact"
          />
          <span className="absolute left-3.5 top-3 text-neutral-400">🔍</span>
        </div>

        {/* Status Filter Chips */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
          {[
            { key: "all", label: "All Papers", count: papers.length },
            {
              key: "approved",
              label: "Approved",
              count: papers.filter((p) => p.status === "approved").length,
            },
            {
              key: "screened",
              label: "Screened",
              count: papers.filter((p) => p.status === "screened").length,
            },
            {
              key: "pending",
              label: "Pending",
              count: papers.filter((p) => p.status === "pending").length,
            },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setFilter(tab.key as any)}
              className={`px-3.5 py-1.5 rounded-full text-xs font-medium tracking-compact transition-all cursor-pointer whitespace-nowrap border ${
                filter === tab.key
                  ? "bg-neutral-900 text-white border-neutral-900 shadow-xs"
                  : "bg-white/80 text-neutral-700 border-neutral-200 hover:bg-white"
              }`}
            >
              {tab.label} ({tab.count})
            </button>
          ))}
        </div>
      </div>

      {/* Papers List */}
      <div className="space-y-4">
        {filteredPapers.map((paper) => (
          <Card
            key={paper.id}
            variant="default"
            className="p-5 sm:p-6 bg-white hover:shadow-md transition-all duration-200 border-neutral-200/80"
          >
            <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
              <div className="space-y-2 flex-1">
                {/* Badges row */}
                <div className="flex flex-wrap items-center gap-2">
                  <Badge
                    variant={paper.relevance >= 90 ? "accent" : "secondary"}
                    className="text-xs"
                  >
                    {paper.relevance}% Relevance Score
                  </Badge>

                  <span
                    className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
                      paper.status === "approved"
                        ? "bg-emerald-100 text-emerald-800"
                        : paper.status === "screened"
                        ? "bg-blue-100 text-blue-800"
                        : "bg-amber-100 text-amber-800"
                    }`}
                  >
                    {paper.status.toUpperCase()}
                  </span>

                  <span className="text-xs text-neutral-500 font-mono">
                    {paper.venue} • {paper.year}
                  </span>
                </div>

                {/* Title */}
                <h2 className="text-lg sm:text-xl font-semibold text-neutral-900 leading-snug tracking-compact">
                  {paper.title}
                </h2>

                {/* Authors */}
                <p className="text-xs sm:text-sm text-neutral-600 font-medium">
                  {paper.authors}
                </p>

                {/* Abstract */}
                <p className="text-xs sm:text-sm text-neutral-700 leading-relaxed pt-1">
                  {paper.abstract}
                </p>

                {/* Tags */}
                <div className="flex flex-wrap gap-1.5 pt-2">
                  {paper.tags.map((tag) => (
                    <span
                      key={tag}
                      className="px-2 py-0.5 rounded text-[11px] font-medium bg-neutral-100 text-neutral-600 border border-neutral-200/60"
                    >
                      #{tag}
                    </span>
                  ))}
                  <span className="text-xs text-neutral-500 self-center ml-2">
                    📈 {paper.citations} citations
                  </span>
                </div>
              </div>

              {/* Action Buttons Column */}
              <div className="flex md:flex-col gap-2 shrink-0 self-end md:self-start">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => alert(`Opening PDF viewer for: ${paper.title}`)}
                  className="text-xs"
                >
                  View PDF
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => handleCopyBibtex(paper)}
                  className="text-xs"
                >
                  {copiedId === paper.id ? "✓ Copied" : "Cite BibTeX"}
                </Button>
              </div>
            </div>
          </Card>
        ))}

        {filteredPapers.length === 0 && (
          <Card className="p-12 text-center bg-white/60 border-dashed border-2 border-neutral-300">
            <span className="text-3xl mb-2 block">🔍</span>
            <h3 className="text-base font-semibold text-neutral-800">
              No papers found matching criteria
            </h3>
            <p className="text-xs text-neutral-500 mt-1">
              Try adjusting your search terms or filters above.
            </p>
          </Card>
        )}
      </div>
    </div>
  );
}
