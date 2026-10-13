import { useState } from "react";
import { cn } from "../../lib/utils";
import type { SynthesizedReport } from "../../types";

export interface ReportViewProps {
  report: SynthesizedReport;
  className?: string;
}

export default function ReportView({ report, className = "" }: ReportViewProps) {
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);

  const title = report.title || "Synthesized Literature Review Report";
  const executiveSummary =
    report.executive_summary || report.summary || "No executive summary available.";
  const thematicClusters = report.thematic_clusters || [];
  const methodologyMatrix = report.methodology_matrix || [];
  const researchGaps = report.research_gaps || [];
  const references = report.references || [];

  const handleCopyReport = async () => {
    try {
      const formattedText = [
        `==================================================`,
        `SYNTHESIZED LITERATURE REVIEW: ${title.toUpperCase()}`,
        `==================================================\n`,
        `EXECUTIVE SUMMARY:`,
        `${executiveSummary}\n`,
        `THEMATIC CLUSTERS:`,
        thematicClusters.length > 0
          ? thematicClusters
              .map(
                (tc) =>
                  `• ${tc.theme}:\n  ${tc.summary}\n  Citations: ${tc.citations.join(", ")}`
              )
              .join("\n\n")
          : "None specified.\n",
        `METHODOLOGY MATRIX:`,
        methodologyMatrix.length > 0
          ? methodologyMatrix
              .map((m) => `• ${m.method}: ${m.papers.join(", ")}`)
              .join("\n")
          : "None specified.\n",
        `RESEARCH GAPS:`,
        researchGaps.length > 0
          ? researchGaps.map((gap) => `• ${gap}`).join("\n")
          : "None specified.\n",
        `REFERENCES & BIBLIOGRAPHY:`,
        references.length > 0
          ? references
              .map(
                (ref, idx) =>
                  `${idx + 1}. ${ref.authors} (${ref.year || "n.d."}). "${ref.title}". ${
                    ref.venue ? ref.venue + "." : ""
                  }${ref.url ? " Available: " + ref.url : ""}`
              )
              .join("\n")
          : "None listed.",
      ].join("\n");

      await navigator.clipboard.writeText(formattedText);
      setCopyFeedback("Copied to clipboard!");
      setTimeout(() => setCopyFeedback(null), 2500);
    } catch (err) {
      console.error("Failed to copy report text:", err);
      setCopyFeedback("Copy failed");
      setTimeout(() => setCopyFeedback(null), 2500);
    }
  };

  const handleExportPDF = () => {
    window.print();
  };

  return (
    <div
      id="synthesized-report-view"
      className={cn(
        "w-full bg-white rounded-2xl border border-neutral-200/80 shadow-xs p-6 sm:p-9 space-y-8 animate-in fade-in duration-300 print:shadow-none print:border-none print:p-0 print:m-0",
        className
      )}
    >
      {/* Header Action Bar (Hidden during PDF print) */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-neutral-100 print:hidden">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-[var(--color-pill-sky)] text-neutral-800">
          <span>✦ Synthesized Report</span>
          <span className="bg-white text-neutral-900 font-bold px-2 py-0.5 rounded-full text-[10px] shadow-2xs">
            Completed
          </span>
        </div>

        {/* Action Buttons: Copy Report & Export PDF */}
        <div className="flex flex-wrap items-center gap-2.5">
          {copyFeedback && (
            <span className="text-xs font-medium text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full animate-in fade-in duration-150">
              ✓ {copyFeedback}
            </span>
          )}

          {/* Copy Report Button */}
          <button
            type="button"
            onClick={handleCopyReport}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-neutral-100 hover:bg-neutral-200/80 text-neutral-800 transition-colors cursor-pointer border border-neutral-200/60"
            title="Copy plain-text report to clipboard"
          >
            <svg className="w-3.5 h-3.5 text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            <span>Copy Report</span>
          </button>

          {/* Export PDF Button */}
          <button
            type="button"
            onClick={handleExportPDF}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-neutral-900 hover:bg-black text-white shadow-xs transition-colors cursor-pointer"
            title="Export report as PDF using browser print"
          >
            <svg className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span>Export PDF</span>
          </button>
        </div>
      </div>

      {/* Main Report Document Title */}
      <div className="space-y-2">
        <h1 className="font-serif text-2xl sm:text-4xl font-bold text-neutral-900 tracking-compact leading-tight">
          {title}
        </h1>
        <p className="text-xs text-neutral-500 font-sans-ui">
          Automated Systematic Synthesis Report · Generated by Scholaris Multi-Agent Pipeline
        </p>
      </div>

      {/* SECTION A: EXECUTIVE SUMMARY */}
      <section className="space-y-3 break-inside-avoid">
        <h2 className="font-serif text-lg sm:text-xl font-bold text-neutral-900 border-b border-neutral-100 pb-1.5">
          Executive Summary
        </h2>
        <div className="bg-neutral-50/70 border border-neutral-200/60 rounded-xl p-4 sm:p-5 text-neutral-800 text-sm sm:text-base leading-relaxed font-sans-ui whitespace-pre-line">
          {executiveSummary}
        </div>
      </section>

      {/* SECTION B: THEMATIC CLUSTERS */}
      <section className="space-y-4 break-inside-avoid">
        <h2 className="font-serif text-lg sm:text-xl font-bold text-neutral-900 border-b border-neutral-100 pb-1.5">
          Thematic Clusters
        </h2>
        {thematicClusters.length === 0 ? (
          <p className="text-xs text-neutral-400 italic">No thematic clusters extracted.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {thematicClusters.map((cluster, idx) => (
              <div
                key={cluster.theme || idx}
                className="bg-white rounded-xl border border-neutral-200/80 p-4 space-y-2.5 shadow-2xs hover:shadow-xs transition-all flex flex-col justify-between"
              >
                <div className="space-y-1.5">
                  <h3 className="font-serif text-base font-bold text-neutral-900 leading-snug">
                    {cluster.theme}
                  </h3>
                  <p className="text-xs sm:text-sm text-neutral-700 leading-relaxed font-sans-ui">
                    {cluster.summary}
                  </p>
                </div>

                {/* Citation Badges */}
                {cluster.citations && cluster.citations.length > 0 && (
                  <div className="pt-2 flex flex-wrap items-center gap-1.5 border-t border-neutral-100">
                    <span className="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">
                      Citations:
                    </span>
                    {cluster.citations.map((cite) => (
                      <span
                        key={cite}
                        className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-[var(--color-pill-sky)] text-neutral-800 shadow-2xs"
                      >
                        {cite}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* SECTION C: METHODOLOGY MATRIX */}
      <section className="space-y-3 break-inside-avoid">
        <h2 className="font-serif text-lg sm:text-xl font-bold text-neutral-900 border-b border-neutral-100 pb-1.5">
          Methodology Comparison Matrix
        </h2>
        {methodologyMatrix.length === 0 ? (
          <p className="text-xs text-neutral-400 italic">No methodology comparison data available.</p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-neutral-200/80">
            <table className="w-full text-left border-collapse text-xs sm:text-sm">
              <thead>
                <tr className="bg-neutral-100/80 text-neutral-800 font-semibold border-b border-neutral-200/80">
                  <th className="p-3 sm:p-3.5 w-1/3">Methodology / Technique</th>
                  <th className="p-3 sm:p-3.5">Associated Papers &amp; Studies</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-200/60">
                {methodologyMatrix.map((item, idx) => (
                  <tr key={item.method || idx} className="hover:bg-neutral-50/60 transition-colors">
                    <td className="p-3 sm:p-3.5 font-semibold text-neutral-900 align-top font-sans-ui">
                      {item.method}
                    </td>
                    <td className="p-3 sm:p-3.5 text-neutral-700 align-top font-sans-ui">
                      <div className="flex flex-wrap gap-1.5">
                        {Array.isArray(item.papers) ? (
                          item.papers.map((paper) => (
                            <span
                              key={paper}
                              className="px-2 py-0.5 rounded bg-neutral-100 text-neutral-800 text-xs border border-neutral-200/60"
                            >
                              {paper}
                            </span>
                          ))
                        ) : (
                          <span>{String(item.papers)}</span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* SECTION D: RESEARCH GAPS */}
      <section className="space-y-3 break-inside-avoid">
        <h2 className="font-serif text-lg sm:text-xl font-bold text-neutral-900 border-b border-neutral-100 pb-1.5">
          Identified Research Gaps &amp; Future Directions
        </h2>
        {researchGaps.length === 0 ? (
          <p className="text-xs text-neutral-400 italic">No research gaps specified.</p>
        ) : (
          <ul className="space-y-2 list-none font-sans-ui text-xs sm:text-sm">
            {researchGaps.map((gap, idx) => (
              <li key={idx} className="flex items-start gap-2.5 text-neutral-800 bg-amber-50/50 border border-amber-200/60 p-3 rounded-xl">
                <span className="text-amber-600 font-bold shrink-0 mt-0.5">✦</span>
                <span className="leading-relaxed">{gap}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* SECTION E: REFERENCES & BIBLIOGRAPHY */}
      <section className="space-y-3 break-inside-avoid pt-2">
        <h2 className="font-serif text-lg sm:text-xl font-bold text-neutral-900 border-b border-neutral-100 pb-1.5">
          References &amp; Bibliography
        </h2>
        {references.length === 0 ? (
          <p className="text-xs text-neutral-400 italic">No reference metadata provided.</p>
        ) : (
          <ol className="space-y-2.5 list-decimal list-inside text-xs sm:text-sm font-sans-ui text-neutral-800">
            {references.map((ref, idx) => {
              const hasValidUrl =
                typeof ref.url === "string" &&
                (ref.url.startsWith("http://") || ref.url.startsWith("https://"));
              return (
                <li key={ref.id || idx} className="pl-1 leading-relaxed border-b border-neutral-100/80 pb-2">
                  <span className="font-semibold">{ref.authors}</span> ({ref.year || "n.d."}).{" "}
                  <span className="italic font-medium text-neutral-900">&ldquo;{ref.title}&rdquo;</span>.{" "}
                  {ref.venue && <span className="text-neutral-600">{ref.venue}. </span>}
                  {hasValidUrl && (
                    <a
                      href={ref.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[var(--color-primary-blue)] hover:underline ml-1 font-mono text-[11px]"
                    >
                      [Link]
                    </a>
                  )}
                </li>
              );
            })}
          </ol>
        )}
      </section>
    </div>
  );
}
