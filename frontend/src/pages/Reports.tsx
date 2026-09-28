import { useState } from "react";
import { Card } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";

export default function Reports() {
  const [activeTab, setActiveTab] = useState<"current" | "history">("current");
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerate = () => {
    setIsGenerating(true);
    setTimeout(() => {
      setIsGenerating(false);
      alert("New synthesis report compiled successfully!");
    }, 1500);
  };

  const handleExportMarkdown = () => {
    const markdownContent = `# Automated Literature Review: Adaptive Retrieval & Agentic Synthesis in LLMs

**Date**: September 28, 2026  
**Corpus**: 4 preprints & peer-reviewed publications  
**Synthesis Model**: Scholaris Multi-Agent Pipeline (LangGraph v0.2)  

## 1. Executive Summary
This review systematically investigates recent advancements in multi-agent adaptive retrieval architectures...
`;
    const blob = new Blob([markdownContent], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "Scholaris_Literature_Review_Report.md";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div id="reports-page" className="w-full space-y-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-black/5 pb-6">
        <div>
          <h1 className="font-serif text-3xl sm:text-4xl font-normal text-neutral-900 tracking-tight">
            Literature Review Reports
          </h1>
          <p className="text-sm text-neutral-600 mt-1 font-sans-ui">
            Automated deep synthesis, comparative taxonomy matrices, and export-ready drafts.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <Button
            variant="outline"
            onClick={handleExportMarkdown}
            leftIcon={<span>📥</span>}
            className="text-xs sm:text-sm"
          >
            Export Markdown
          </Button>
          <Button
            variant="accent"
            onClick={handleGenerate}
            isLoading={isGenerating}
            leftIcon={<span>✨</span>}
            className="text-xs sm:text-sm"
          >
            Generate New Report
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-neutral-200">
        <button
          onClick={() => setActiveTab("current")}
          className={`pb-2.5 px-3 text-sm font-semibold tracking-compact border-b-2 transition-all cursor-pointer ${
            activeTab === "current"
              ? "border-black text-black"
              : "border-transparent text-neutral-500 hover:text-neutral-800"
          }`}
        >
          Active Review Draft (v1.2)
        </button>
        <button
          onClick={() => setActiveTab("history")}
          className={`pb-2.5 px-3 text-sm font-semibold tracking-compact border-b-2 transition-all cursor-pointer ${
            activeTab === "history"
              ? "border-black text-black"
              : "border-transparent text-neutral-500 hover:text-neutral-800"
          }`}
        >
          Report History (3 Drafts)
        </button>
      </div>

      {activeTab === "current" ? (
        /* Report Document Container */
        <Card variant="default" className="p-6 sm:p-10 bg-white shadow-md border-neutral-200/90 space-y-8">
          {/* Document Header */}
          <div className="border-b border-neutral-100 pb-6 space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="accent" className="text-xs font-semibold">
                Synthesized by Scholaris
              </Badge>
              <span className="text-xs text-neutral-500 font-mono">
                Generated: September 28, 2026 • 4 Papers Analyzed
              </span>
            </div>
            <h2 className="font-serif text-2xl sm:text-3xl text-neutral-900 leading-snug">
              Adaptive Retrieval & Error Verification in Multi-Agent Academic Systems
            </h2>
            <p className="text-xs text-neutral-500">
              Corpus: arXiv:2403.08119, NeurIPS 2024 Preprints, ACL 2023, IEEE TSE 2024
            </p>
          </div>

          {/* Section 1: Executive Abstract */}
          <section className="space-y-3">
            <h3 className="font-serif text-lg font-semibold text-neutral-900 border-l-4 border-black pl-3">
              1. Executive Synthesis & Abstract
            </h3>
            <p className="text-sm text-neutral-700 leading-relaxed">
              Recent advancements in literature synthesis indicate a paradigm shift from passive
              single-turn Retrieval-Augmented Generation (RAG) toward stateful, multi-agent reasoning loops.
              Across the evaluated corpus, standard dense bi-encoder models demonstrate a baseline failure rate
              of approximately 38% on complex cross-paper methodological comparison tasks. By incorporating
              iterative graph-guided traversal and self-correction verification checkpoints, recent frameworks
              achieve up to a <strong>41% reduction in factual hallucination</strong> while establishing
              verifiable citation grounding.
            </p>
          </section>

          {/* Section 2: Taxonomy & Comparative Matrix */}
          <section className="space-y-4">
            <h3 className="font-serif text-lg font-semibold text-neutral-900 border-l-4 border-black pl-3">
              2. Taxonomy & Comparative Matrix
            </h3>
            <div className="overflow-x-auto rounded-xl border border-neutral-200">
              <table className="w-full text-left text-xs tracking-compact">
                <thead className="bg-neutral-50 text-neutral-700 border-b border-neutral-200">
                  <tr>
                    <th className="p-3 font-semibold">Framework / Paper</th>
                    <th className="p-3 font-semibold">Retrieval Mechanism</th>
                    <th className="p-3 font-semibold">Verification Strategy</th>
                    <th className="p-3 font-semibold">Key Benchmark</th>
                    <th className="p-3 font-semibold">Reported Limitation</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-100 text-neutral-800">
                  <tr className="hover:bg-neutral-50/50">
                    <td className="p-3 font-medium">Rostova et al. (2024)</td>
                    <td className="p-3">Graph-guided Iterative</td>
                    <td className="p-3">Multi-hop contradiction test</td>
                    <td className="p-3 font-mono text-[11px]">MultiHopQA</td>
                    <td className="p-3 text-neutral-500">1.8x higher compute cost</td>
                  </tr>
                  <tr className="hover:bg-neutral-50/50">
                    <td className="p-3 font-medium">Thorne et al. (2024)</td>
                    <td className="p-3">Consensus-driven</td>
                    <td className="p-3">Self-correction loops</td>
                    <td className="p-3 font-mono text-[11px]">LitSynthesize</td>
                    <td className="p-3 text-neutral-500">Requires strict human validation</td>
                  </tr>
                  <tr className="hover:bg-neutral-50/50">
                    <td className="p-3 font-medium">Sato et al. (2023)</td>
                    <td className="p-3">Hybrid Dense-Sparse (ColBERT)</td>
                    <td className="p-3">Lexical reranker check</td>
                    <td className="p-3 font-mono text-[11px]">SciFact & BioASQ</td>
                    <td className="p-3 text-neutral-500">Struggles with formula notations</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          {/* Section 3: Identified Research Gaps */}
          <section className="space-y-3">
            <h3 className="font-serif text-lg font-semibold text-neutral-900 border-l-4 border-black pl-3">
              3. Critical Research Gaps & Open Challenges
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="p-4 rounded-xl bg-neutral-50 border border-neutral-200/80 space-y-1">
                <span className="text-xs font-semibold text-rose-700">Gap 1 • Long-Context Drift</span>
                <p className="text-xs text-neutral-600 leading-relaxed">
                  Memory degradation across long iterative review cycles still leads to attention dilution when synthesizing beyond 20 concurrent full-text papers.
                </p>
              </div>
              <div className="p-4 rounded-xl bg-neutral-50 border border-neutral-200/80 space-y-1">
                <span className="text-xs font-semibold text-amber-700">Gap 2 • Mathematical & Table Parsing</span>
                <p className="text-xs text-neutral-600 leading-relaxed">
                  Dense bi-encoders routinely miss tabular quantitative empirical claims embedded in complex multi-column PDF formatting.
                </p>
              </div>
            </div>
          </section>

          {/* Section 4: Consolidated Bibliography */}
          <section className="space-y-3 pt-4 border-t border-neutral-100">
            <h3 className="font-serif text-lg font-semibold text-neutral-900">
              4. Consolidated Bibliography
            </h3>
            <ol className="list-decimal list-inside space-y-2 text-xs text-neutral-700 font-sans leading-relaxed">
              <li>
                Rostova, E., Vance, M., et al. (2024). <em>Benchmarking Adaptive Retrieval Strategies in Multi-Hop Reasoning</em>. arXiv:2403.08119.
              </li>
              <li>
                Thorne, J., Lin, S., & Miller, D. K. (2024). <em>Self-Correction and Verification Loops in Agentic Literature Synthesis</em>. NeurIPS Preprints.
              </li>
              <li>
                Sato, K., Pendelton, A., & Chen, X. (2023). <em>Dense Passage Embeddings vs. Hybrid Search for Scientific Literature</em>. ACL Findings.
              </li>
            </ol>
          </section>
        </Card>
      ) : (
        /* Report History */
        <div className="space-y-3">
          {[
            {
              title: "Adaptive Retrieval & Error Verification (v1.2)",
              date: "Today, 10:45 AM",
              papers: 4,
              status: "Current",
            },
            {
              title: "Systematic Review on Sparse Autoencoders in LLMs (v1.0)",
              date: "Sept 25, 2026",
              papers: 8,
              status: "Archived",
            },
            {
              title: "Graph Neural Networks for Molecular Discovery (v2.1)",
              date: "Sept 18, 2026",
              papers: 14,
              status: "Archived",
            },
          ].map((report, idx) => (
            <Card key={idx} className="p-5 bg-white flex items-center justify-between">
              <div>
                <span className="text-xs text-neutral-500">{report.date}</span>
                <h4 className="text-base font-semibold text-neutral-900 mt-0.5">{report.title}</h4>
                <span className="text-xs text-neutral-600">{report.papers} papers analyzed</span>
              </div>
              <Button size="sm" variant="outline" onClick={() => setActiveTab("current")}>
                View Report
              </Button>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
