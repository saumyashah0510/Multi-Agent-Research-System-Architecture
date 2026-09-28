import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import ResearchInput from "../components/ResearchInput";
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";

export default function Dashboard() {
  const [searchParams] = useSearchParams();
  const currentTab = searchParams.get("tab") || "research";

  const [activeQuery, setActiveQuery] = useState<string | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [logs, setLogs] = useState<string[]>([
    "System initialized. Ready for research topic.",
  ]);

  const handleSearch = ({
    query,
    numPapers = 10,
    attachedFile,
  }: {
    query: string;
    numPapers?: number;
    attachedFile?: File | null;
  }) => {
    const cappedPapers = Math.min(numPapers, 20);
    setActiveQuery(query);
    setIsSearching(true);
    setLogs((prev) => [
      ...prev,
      `Initiating research on: "${query}" (Target: ${cappedPapers} papers)...`,
      attachedFile
        ? `[Ingestion Agent] Parsing uploaded document: ${attachedFile.name}...`
        : `[Search Agent] Querying academic vector indexes...`,
    ]);

    // Simulated search feedback for interactive responsiveness
    setTimeout(() => {
      setIsSearching(false);
      setLogs((prev) => [
        ...prev,
        `[Search Agent] Retrieved top ${cappedPapers} candidate preprints.`,
        `[Screening Agent] Scoring papers for relevance & citation methodology...`,
      ]);
    }, 1200);
  };

  const samplePrompts = [
    "Adaptive Retrieval Augmented Generation (Self-RAG)",
    "Graph Neural Networks for Molecular Property Prediction",
    "Mechanistic Interpretability in Sparse Autoencoders",
  ];

  return (
    <div id="dashboard-page" className="w-full flex flex-col items-center">
      {/* Figma Hero: Welcome Header */}
      <div className="text-center pt-2 sm:pt-6 pb-6 sm:pb-8 max-w-2xl px-4">
        <h1 className="font-serif text-3xl sm:text-5xl font-normal text-neutral-900 tracking-tight leading-tight">
          Welcome,
          <br />
          <span className="font-serif">What are you curious about?</span>
        </h1>
      </div>

      {/* Main Research Search Card from Figma */}
      <div className="w-full flex flex-col items-center mb-10 px-2 sm:px-0">
        <ResearchInput onSearch={handleSearch} isLoading={isSearching} />

        {/* Suggested Quick Topics */}
        {!activeQuery && (
          <div className="mt-4 flex flex-wrap items-center justify-center gap-2 text-xs text-neutral-500">
            <span className="font-medium text-neutral-400">Suggestions:</span>
            {samplePrompts.map((prompt) => (
              <button
                key={prompt}
                onClick={() =>
                  handleSearch({
                    query: prompt,
                    numPapers: 10,
                  })
                }
                className="px-3 py-1 rounded-full bg-white/70 hover:bg-white text-neutral-700 border border-neutral-200/60 shadow-xs transition-all hover:border-black/20 cursor-pointer"
              >
                {prompt}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Contextual Reports Card on Same Page if 'reports' tab clicked */}
      {currentTab === "reports" && (
        <div className="w-full max-w-4xl mx-auto mb-8">
          <Card variant="default" className="p-6 bg-white border-black/10 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-neutral-100 pb-3">
              <div className="flex items-center gap-2">
                <Badge variant="accent">Synthesis Report</Badge>
                <h3 className="font-serif text-lg font-semibold text-neutral-900">
                  Adaptive Retrieval & Literature Synthesis
                </h3>
              </div>
              <span className="text-xs text-neutral-500 font-mono">Consensus: 96%</span>
            </div>
            <p className="text-sm text-neutral-700 leading-relaxed">
              Based on the 4 analyzed candidate preprints, stateful multi-agent architectures achieve up to a <strong>41% reduction in factual hallucination</strong> through iterative graph traversal and self-correction verification checkpoints.
            </p>
          </Card>
        </div>
      )}

      {/* Main Literature & Agent Workspace Grid */}
      <div className="w-full grid grid-cols-1 lg:grid-cols-3 gap-6 sm:gap-8 mt-2">
        {/* Candidate Papers Container */}
        <div
          className={`lg:col-span-2 space-y-4 transition-all ${
            currentTab === "papers" ? "ring-2 ring-black/10 rounded-2xl p-2" : ""
          }`}
        >
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold text-neutral-900 tracking-compact">
                Discovered & Screened Papers
              </h2>
              {activeQuery && (
                <Badge variant="accent" className="text-xs">
                  Active Topic
                </Badge>
              )}
            </div>
            <span className="text-xs font-medium text-neutral-500">
              {activeQuery ? "Analyzing papers..." : "0 papers selected"}
            </span>
          </div>

          {activeQuery ? (
            <div className="space-y-3">
              <Card variant="default" className="p-5 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <span className="text-xs font-mono text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                      High Relevance • 96%
                    </span>
                    <h3 className="text-base font-semibold text-neutral-900 mt-2">
                      Benchmarking Adaptive Retrieval Strategies in Multi-Hop Reasoning
                    </h3>
                    <p className="text-xs text-neutral-500 mt-1">
                      arXiv:2403.08119 • Published 2024 • 142 Citations
                    </p>
                    <p className="text-xs text-neutral-600 mt-2 line-clamp-2">
                      We propose an iterative graph-guided retrieval mechanism that
                      dynamically decides when and what to retrieve for complex multi-agent
                      reasoning tasks.
                    </p>
                  </div>
                  <Button size="sm" variant="outline">
                    Inspect PDF
                  </Button>
                </div>
              </Card>

              <Card variant="default" className="p-5 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <span className="text-xs font-mono text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                      Relevance • 89%
                    </span>
                    <h3 className="text-base font-semibold text-neutral-900 mt-2">
                      Self-Correction and Verification Loops in Agentic Synthesis
                    </h3>
                    <p className="text-xs text-neutral-500 mt-1">
                      arXiv:2402.14820 • Published 2024 • 98 Citations
                    </p>
                    <p className="text-xs text-neutral-600 mt-2 line-clamp-2">
                      Analyzing verification feedback loops that prevent hallucination in
                      automated literature synthesis and structured hypothesis generation.
                    </p>
                  </div>
                  <Button size="sm" variant="outline">
                    Inspect PDF
                  </Button>
                </div>
              </Card>
            </div>
          ) : (
            <Card
              variant="default"
              className="p-10 sm:p-12 text-center bg-white/70 border-dashed border-2 border-neutral-300/80 shadow-none"
            >
              <div className="w-12 h-12 mx-auto rounded-full bg-[#E3FBD6] flex items-center justify-center text-xl mb-3">
                📚
              </div>
              <h3 className="text-sm font-semibold text-neutral-900">
                No Active Literature Search
              </h3>
              <p className="text-xs text-neutral-500 mt-1 max-w-sm mx-auto">
                Type your topic above or click one of the suggestions to trigger the
                multi-agent research and screening pipeline.
              </p>
            </Card>
          )}
        </div>

        {/* Agent Activity Feed Sidebar */}
        <div
          className={`space-y-4 transition-all ${
            currentTab === "chat" ? "ring-2 ring-black/10 rounded-2xl p-2" : ""
          }`}
        >
          <div className="flex items-center justify-between px-1">
            <h2 className="text-lg font-semibold text-neutral-900 tracking-compact">
              Live Agent Pipeline
            </h2>
            <span className="flex items-center gap-1.5 text-xs text-neutral-500 font-medium">
              <span
                className={`w-2 h-2 rounded-full ${
                  isSearching ? "bg-amber-400 animate-ping" : "bg-emerald-500"
                }`}
              />
              {isSearching ? "Active" : "Idle"}
            </span>
          </div>

          <Card variant="default" className="p-4 bg-white/90 shadow-sm border border-neutral-200">
            <CardHeader className="p-0 pb-3 border-b border-neutral-100 flex flex-row items-center justify-between">
              <CardTitle className="text-xs font-semibold text-neutral-800">
                Multi-Agent Execution Feed
              </CardTitle>
              <Badge variant="accent" className="text-[10px] py-0 px-2">
                LangGraph
              </Badge>
            </CardHeader>
            <CardContent className="p-0 pt-3">
              <div className="font-mono text-xs space-y-2 max-h-[300px] overflow-y-auto">
                {logs.map((log, index) => (
                  <div key={index} className="text-neutral-600 leading-relaxed">
                    <span className="text-neutral-400 mr-1.5">›</span>
                    {log}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
