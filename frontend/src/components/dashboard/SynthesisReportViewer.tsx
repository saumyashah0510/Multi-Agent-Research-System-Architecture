/**
 * SynthesisReportViewer Component
 *
 * Renders the synthesized literature review report:
 * - Stats summary row + section jump pills
 * - Executive Summary
 * - Thematic Clusters (alternating soft tinted cards)
 * - Comparative Methodology Matrix
 * - Research Gaps & Open Challenges
 * - Conclusion & Future Directions
 * - Verified References using reusable ReferenceCard components
 */

import React, { useState } from "react";
import { SynthesizedReview } from "../../types";
import MethodologyMatrix from "./MethodologyMatrix";
import ReferenceCard from "./ReferenceCard";

export interface SynthesisReportViewerProps {
  report: SynthesizedReview;
  className?: string;
}

export function formatReportAsMarkdown(report: SynthesizedReview): string {
  let md = `# ${report.title}\n\n`;
  md += `## Executive Summary\n\n${report.executive_summary}\n\n`;

  if (report.thematic_clusters && report.thematic_clusters.length > 0) {
    md += `## Thematic Clusters & Comparative Analysis\n\n`;
    report.thematic_clusters.forEach((cluster, idx) => {
      md += `### ${idx + 1}. ${cluster.theme}\n\n${cluster.summary}\n\n`;
      if (cluster.citations && cluster.citations.length > 0) {
        md += `**Cited Literature:** ${cluster.citations.join(", ")}\n\n`;
      }
    });
  }

  if (report.methodology_matrix && report.methodology_matrix.length > 0) {
    const escapeMarkdownCell = (value: string): string =>
      String(value).replace(/\|/g, "\\|").replace(/\r?\n+/g, " ").trim();

    md += `## Comparative Methodology Matrix\n\n`;
    md += `| Methodology | Papers Evaluated | Strengths | Limitations |\n`;
    md += `| :--- | :--- | :--- | :--- |\n`;
    report.methodology_matrix.forEach((item) => {
      const methodName = escapeMarkdownCell(item.method_name || "");
      const papers = item.papers_used?.map(escapeMarkdownCell).join("<br>") || "";
      const strengths = item.strengths?.map(escapeMarkdownCell).join("<br>") || "";
      const limitations = item.limitations?.map(escapeMarkdownCell).join("<br>") || "";
      md += `| **${methodName}** | ${papers} | ${strengths} | ${limitations} |\n`;
    });
    md += "\n";
  }

  if (report.research_gaps && report.research_gaps.length > 0) {
    md += `## Unresolved Research Gaps & Open Challenges\n\n`;
    report.research_gaps.forEach((gap, idx) => {
      md += `${idx + 1}. ${gap}\n`;
    });
    md += "\n";
  }

  if (report.conclusion) {
    md += `## Conclusion & Future Directions\n\n${report.conclusion}\n\n`;
  }

  if (report.references && report.references.length > 0) {
    md += `## References & Bibliography\n\n`;
    report.references.forEach((ref, idx) => {
      const authors = ref.authors?.join(", ") || "Unknown Authors";
      const year = ref.year ? ` (${ref.year})` : "";
      md += `${idx + 1}. **${ref.title || "Untitled Paper"}** by ${authors}${year}`;
      if (ref.url) {
        md += ` <${ref.url}>`;
      }
      if (ref.matched_passage) {
        md += ` (Grounding: *"${ref.matched_passage}"*)`;
      }
      md += "\n";
    });
    md += "\n";
  }

  return md;
}

const CLUSTER_TINTS = [
  { bg: "var(--tint-mint)", border: "#bfe8b2" },
  { bg: "var(--tint-sky)", border: "#b2dbfa" },
  { bg: "var(--tint-lavender)", border: "#c2c5f6" },
  { bg: "var(--tint-mint)", border: "#bfe8b2" },
];

export const SynthesisReportViewer: React.FC<SynthesisReportViewerProps> = ({
  report,
  className = "",
}) => {
  const [activeSection, setActiveSection] = useState<string>("summary");

  const thematicClusters = report.thematic_clusters || [];
  const methodologyMatrix = report.methodology_matrix || [];
  const researchGaps = report.research_gaps || [];
  const references = report.references || [];

  const clustersCount = thematicClusters.length;
  const methodsCount = methodologyMatrix.length;
  const gapsCount = researchGaps.length;
  const refsCount = references.length;

  const sections = [
    { id: "summary", label: "Summary", show: true },
    { id: "clusters", label: "Clusters", show: clustersCount > 0 },
    { id: "matrix", label: "Matrix", show: methodsCount > 0 },
    { id: "gaps", label: "Gaps", show: gapsCount > 0 },
    { id: "conclusion", label: "Conclusion", show: Boolean(report.conclusion) },
    { id: "references", label: "References", show: refsCount > 0 },
  ].filter((s) => s.show);

  const scrollToSection = (id: string) => {
    setActiveSection(id);
    const el = document.getElementById(`section-${id}`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  return (
    <div className={`w-full space-y-6 ${className}`}>
      {/* 4 Stat Cards Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-white rounded-xl border border-neutral-200/80 px-4 py-3.5 shadow-2xs">
          <p className="font-serif text-2xl font-bold text-neutral-900 tabular-nums leading-none">
            {refsCount}
          </p>
          <p className="font-sans text-xs text-neutral-500 mt-1.5">Papers analyzed</p>
        </div>
        <div className="bg-white rounded-xl border border-neutral-200/80 px-4 py-3.5 shadow-2xs">
          <p className="font-serif text-2xl font-bold text-neutral-900 tabular-nums leading-none">
            {methodsCount}
          </p>
          <p className="font-sans text-xs text-neutral-500 mt-1.5">Methodologies</p>
        </div>
        <div className="bg-white rounded-xl border border-neutral-200/80 px-4 py-3.5 shadow-2xs">
          <p className="font-serif text-2xl font-bold text-neutral-900 tabular-nums leading-none">
            {gapsCount}
          </p>
          <p className="font-sans text-xs text-neutral-500 mt-1.5">Research gaps</p>
        </div>
        <div className="bg-white rounded-xl border border-neutral-200/80 px-4 py-3.5 shadow-2xs">
          <p className="font-serif text-2xl font-bold text-neutral-900 tabular-nums leading-none">
            {clustersCount}
          </p>
          <p className="font-sans text-xs text-neutral-500 mt-1.5">Thematic clusters</p>
        </div>
      </div>

      {/* Section Jump Pills */}
      <div className="flex flex-wrap items-center gap-1.5">
        {sections.map((sec) => (
          <button
            key={sec.id}
            type="button"
            onClick={() => scrollToSection(sec.id)}
            style={{ borderRadius: "var(--radius-sm)" }}
            className={`px-3 py-1.5 text-xs font-semibold transition-all cursor-pointer select-none ${
              activeSection === sec.id
                ? "bg-neutral-900 text-white shadow-2xs"
                : "bg-white text-neutral-600 hover:text-neutral-900 hover:bg-neutral-50 border border-neutral-200/80"
            }`}
          >
            {sec.label}
          </button>
        ))}
      </div>

      {/* Executive Summary */}
      <section
        id="section-summary"
        className="w-full bg-white rounded-2xl border border-neutral-200/85 shadow-xs p-5 sm:p-7 space-y-3 scroll-mt-20"
      >
        <h2 className="font-serif text-lg sm:text-xl font-bold text-neutral-900 tracking-compact">
          Executive summary
        </h2>
        <div className="text-neutral-700 leading-relaxed font-sans text-xs sm:text-[13.5px] whitespace-pre-line space-y-3">
          {report.executive_summary}
        </div>
      </section>

      {/* Thematic Clusters Section */}
      {clustersCount > 0 && (
        <section id="section-clusters" className="space-y-3.5 scroll-mt-20">
          <h2 className="font-serif text-lg sm:text-xl font-bold text-neutral-900 tracking-compact">
            Thematic clusters
          </h2>

          <div className="space-y-3">
            {thematicClusters.map((cluster, idx) => {
              const tint = CLUSTER_TINTS[idx % CLUSTER_TINTS.length] ?? {
                bg: "var(--tint-mint)",
                border: "#c7edd5",
              };
              return (
                <div
                  key={idx}
                  style={{
                    backgroundColor: tint.bg,
                    borderColor: tint.border,
                  }}
                  className="rounded-2xl border p-5 sm:p-6 space-y-2.5 shadow-2xs"
                >
                  <h3 className="font-serif text-sm sm:text-base font-bold text-neutral-900">
                    {idx + 1}. {cluster.theme}
                  </h3>
                  <p className="text-xs sm:text-[13px] text-neutral-700 leading-relaxed whitespace-pre-line">
                    {cluster.summary}
                  </p>
                  {cluster.citations && cluster.citations.length > 0 && (
                    <div className="pt-2">
                      <span
                        style={{ borderRadius: "var(--radius-sm)" }}
                        className="inline-flex flex-wrap items-center gap-x-1.5 px-3 py-1.5 bg-white/85 border border-black/10 text-[11px] text-neutral-700 shadow-2xs"
                      >
                        <span className="font-semibold text-neutral-600">
                          Cited:
                        </span>
                        <span>{cluster.citations.join(" · ")}</span>
                      </span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Comparative Methodology Matrix Section */}
      {methodsCount > 0 && (
        <section id="section-matrix" className="scroll-mt-20">
          <MethodologyMatrix matrix={methodologyMatrix} references={references} />
        </section>
      )}

      {/* Research Gaps Section */}
      {gapsCount > 0 && (
        <section id="section-gaps" className="space-y-3.5 scroll-mt-20">
          <h2 className="font-serif text-lg sm:text-xl font-bold text-neutral-900 tracking-compact">
            Research gaps
          </h2>

          <ul className="space-y-2.5">
            {researchGaps.map((gap, gIdx) => (
              <li
                key={gIdx}
                className="flex items-start gap-3 text-xs sm:text-[13px] text-neutral-800 bg-white p-4 sm:p-4.5 rounded-xl border border-neutral-200/85 shadow-2xs hover:border-neutral-300 transition-colors"
              >
                <span className="w-6 h-6 rounded-full bg-amber-100 text-amber-800 border border-amber-200/80 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5 tabular-nums">
                  {gIdx + 1}
                </span>
                <span className="leading-relaxed">{gap}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Conclusion & Future Directions */}
      {report.conclusion && (
        <section
          id="section-conclusion"
          className="w-full bg-white rounded-2xl border border-neutral-200/85 shadow-xs p-5 sm:p-7 space-y-3 scroll-mt-20"
        >
          <h2 className="font-serif text-lg sm:text-xl font-bold text-neutral-900 tracking-compact">
            Conclusion &amp; future directions
          </h2>
          <div className="text-xs sm:text-[13.5px] text-neutral-700 leading-relaxed font-sans whitespace-pre-line space-y-3">
            {report.conclusion}
          </div>
        </section>
      )}

      {/* References & Bibliography Section (Reusable ReferenceCard) */}
      {refsCount > 0 && (
        <section id="section-references" className="space-y-3.5 scroll-mt-20">
          <h2 className="font-serif text-lg sm:text-xl font-bold text-neutral-900 tracking-compact">
            References
          </h2>

          <div className="space-y-2.5">
            {references.map((ref, rIdx) => (
              <ReferenceCard key={rIdx} reference={ref} index={rIdx} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
};

export default SynthesisReportViewer;
