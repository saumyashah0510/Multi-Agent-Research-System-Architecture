/**
 * SynthesisReportViewer Component
 *
 * Assignee Task (Issue FE-08):
 * - Render publication-grade literature review synthesized by Agent 09
 * - Display formal Title, Executive Summary, Thematic Clusters, Research Gaps, and References
 * - Format citations and academic references with external links
 * - Support copy-to-markdown export formatting
 */

import React, { useState } from "react";
import {
  BookOpen,
  Compass,
  ExternalLink,
  Bookmark,
  Sparkles,
  ShieldCheck,
  Copy,
  Check,
  FileCheck2,
} from "lucide-react";
import { SynthesizedReview } from "../../types";

export interface SynthesisReportViewerProps {
  report: SynthesizedReview;
  className?: string;
}

function formatReportAsMarkdown(report: SynthesizedReview): string {
  let md = `# ${report.title}\n\n`;
  md += `## Executive Summary\n\n${report.executive_summary}\n\n`;

  if (report.thematic_clusters && report.thematic_clusters.length > 0) {
    md += `## Thematic Clusters & Core Findings\n\n`;
    report.thematic_clusters.forEach((cluster, idx) => {
      md += `### ${idx + 1}. ${cluster.theme}\n\n${cluster.summary}\n\n`;
      if (cluster.citations && cluster.citations.length > 0) {
        md += `*Citations:* ${cluster.citations.join(", ")}\n\n`;
      }
    });
  }

  if (report.research_gaps && report.research_gaps.length > 0) {
    md += `## Identified Research Gaps & Open Challenges\n\n`;
    report.research_gaps.forEach((gap, idx) => {
      md += `${idx + 1}. ${gap}\n`;
    });
    md += "\n";
  }

  if (report.conclusion) {
    md += `## Conclusion\n\n${report.conclusion}\n\n`;
  }

  if (report.references && report.references.length > 0) {
    md += `## Verified References & Bibliography\n\n`;
    report.references.forEach((ref, idx) => {
      const authors = ref.authors?.join(", ") || "Unknown Authors";
      const year = ref.year ? ` (${ref.year})` : "";
      md += `${idx + 1}. **${ref.title || "Untitled Paper"}** - ${authors}${year}`;
      if (ref.url) {
        md += ` [Link](${ref.url})`;
      }
      if (ref.matched_passage) {
        md += `\n   > "${ref.matched_passage}"`;
      }
      md += "\n\n";
    });
  }

  return md;
}

export const SynthesisReportViewer: React.FC<SynthesisReportViewerProps> = ({
  report,
  className = "",
}) => {
  const [isCopied, setIsCopied] = useState(false);

  const handleCopyMarkdown = async () => {
    try {
      const md = formatReportAsMarkdown(report);
      await navigator.clipboard.writeText(md);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch (err) {
      console.warn("Failed to copy markdown:", err);
    }
  };

  const thematicClusters = report.thematic_clusters || [];
  const researchGaps = report.research_gaps || [];
  const references = report.references || [];

  const clustersCount = thematicClusters.length;
  const gapsCount = researchGaps.length;
  const refsCount = references.length;

  return (
    <div className={`w-full space-y-6 ${className}`}>
      {/* Title & Executive Summary Hero Container */}
      <div className="w-full bg-white rounded-2xl border border-neutral-200/90 shadow-xs p-6 sm:p-8 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-indigo-600 text-xs font-semibold uppercase tracking-wider">
            <BookOpen className="w-4 h-4 shrink-0" />
            <span>Synthesized Literature Review</span>
          </div>

          <button
            type="button"
            onClick={handleCopyMarkdown}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-neutral-200 text-xs font-semibold text-neutral-700 hover:bg-neutral-50 active:scale-95 transition-all cursor-pointer shadow-2xs self-start sm:self-auto"
            title="Copy entire review as formatted Markdown"
          >
            {isCopied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-600" />
                <span className="text-emerald-700">Copied Markdown</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 text-neutral-500" />
                <span>Copy Markdown</span>
              </>
            )}
          </button>
        </div>

        <h2 className="font-serif text-2xl sm:text-3xl font-bold text-neutral-900 leading-snug tracking-tight">
          {report.title}
        </h2>

        {/* Review Metadata Stats Row */}
        <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-neutral-100">
          <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-neutral-600 bg-neutral-100 px-2.5 py-1 rounded-lg">
            <Bookmark className="w-3.5 h-3.5 text-indigo-600" />
            <span>{clustersCount} Thematic Clusters</span>
          </span>
          <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-neutral-600 bg-neutral-100 px-2.5 py-1 rounded-lg">
            <Compass className="w-3.5 h-3.5 text-amber-500" />
            <span>{gapsCount} Research Gaps</span>
          </span>
          <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-neutral-600 bg-neutral-100 px-2.5 py-1 rounded-lg">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            <span>{refsCount} Verified References</span>
          </span>
        </div>

        {/* Executive Summary Callout */}
        <div className="p-5 sm:p-6 bg-neutral-50/80 rounded-2xl border border-neutral-200/80 text-neutral-800 text-sm leading-relaxed shadow-xs">
          <div className="flex items-center gap-1.5 font-medium text-neutral-900 mb-2 text-xs uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
            <span>Executive Summary</span>
          </div>
          <p className="text-neutral-700 leading-relaxed font-sans text-[13px] sm:text-sm">
            {report.executive_summary}
          </p>
        </div>
      </div>

      {/* Thematic Clusters Section */}
      {clustersCount > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-serif text-xl font-bold text-neutral-900 flex items-center gap-2">
              <Bookmark className="w-5 h-5 text-indigo-600" />
              <span>Thematic Clusters & Core Findings</span>
            </h3>
            <span className="text-xs text-neutral-500 font-medium">
              {clustersCount} {clustersCount === 1 ? "theme" : "themes"}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {thematicClusters.map((cluster, idx) => (
              <div
                key={idx}
                className="bg-white rounded-2xl border border-neutral-200 shadow-xs p-5 space-y-3 flex flex-col justify-between hover:border-neutral-300 transition-colors"
              >
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 text-[10px] font-bold flex items-center justify-center shrink-0">
                      {idx + 1}
                    </span>
                    <h4 className="font-serif text-base font-bold text-neutral-900">
                      {cluster.theme}
                    </h4>
                  </div>
                  <p className="text-xs sm:text-[13px] text-neutral-600 leading-relaxed">
                    {cluster.summary}
                  </p>
                </div>

                {cluster.citations && cluster.citations.length > 0 && (
                  <div className="pt-3 border-t border-neutral-100 flex flex-wrap gap-1.5 items-center">
                    <span className="text-[10px] text-neutral-400 uppercase font-semibold">Citations:</span>
                    {cluster.citations.map((cite, cIdx) => (
                      <span
                        key={cIdx}
                        className="bg-indigo-50/80 text-indigo-700 border border-indigo-100/80 text-[10px] font-medium px-2 py-0.5 rounded-md"
                      >
                        {cite}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Research Gaps Section */}
      {gapsCount > 0 && (
        <div className="w-full bg-white rounded-2xl border border-neutral-200 shadow-xs p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-serif text-lg sm:text-xl font-bold text-neutral-900 flex items-center gap-2">
              <Compass className="w-5 h-5 text-amber-500" />
              <span>Identified Research Gaps & Open Challenges</span>
            </h3>
            <span className="text-xs text-neutral-500 font-medium">
              {gapsCount} {gapsCount === 1 ? "gap" : "gaps"}
            </span>
          </div>

          <ul className="space-y-2.5">
            {researchGaps.map((gap, gIdx) => (
              <li
                key={gIdx}
                className="flex items-start gap-3 text-xs sm:text-[13px] text-neutral-800 bg-amber-50/60 p-3.5 rounded-xl border border-amber-200/70 hover:border-amber-300 transition-colors"
              >
                <span className="w-5 h-5 rounded-full bg-amber-100 text-amber-800 border border-amber-200/80 text-[10px] font-bold flex items-center justify-center shrink-0 mt-0.5">
                  {gIdx + 1}
                </span>
                <span className="leading-relaxed">{gap}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Conclusion Section (if provided) */}
      {report.conclusion && (
        <div className="w-full bg-white rounded-2xl border border-neutral-200 shadow-xs p-6 space-y-3">
          <h3 className="font-serif text-lg sm:text-xl font-bold text-neutral-900 flex items-center gap-2">
            <FileCheck2 className="w-5 h-5 text-emerald-600" />
            <span>Conclusion & Future Directions</span>
          </h3>
          <p className="text-xs sm:text-[13px] text-neutral-700 leading-relaxed font-sans">
            {report.conclusion}
          </p>
        </div>
      )}

      {/* References & Bibliography Section */}
      {refsCount > 0 && (
        <div className="w-full bg-white rounded-2xl border border-neutral-200 shadow-xs p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-serif text-lg sm:text-xl font-bold text-neutral-900 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-600" />
              <span>Verified References & Bibliography</span>
            </h3>
            <span className="text-xs text-neutral-500 font-medium">
              {refsCount} {refsCount === 1 ? "entry" : "entries"}
            </span>
          </div>

          <ol className="divide-y divide-neutral-100 text-xs text-neutral-700">
            {references.map((ref, rIdx) => (
              <li key={rIdx} className="py-3 flex items-start justify-between gap-4 first:pt-0 last:pb-0">
                <div className="space-y-1 min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-neutral-900 text-xs sm:text-[13px]">
                      {ref.title || `Reference #${rIdx + 1}`}
                    </span>
                    {ref.year && (
                      <span className="bg-neutral-100 text-neutral-600 text-[10px] font-medium px-1.5 py-0.5 rounded">
                        {ref.year}
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-neutral-500">
                    {ref.authors && ref.authors.length > 0
                      ? ref.authors.join(", ")
                      : "Authors unlisted"}
                  </p>
                  {ref.matched_passage && (
                    <p className="text-[11px] text-neutral-600 bg-neutral-50 p-2.5 rounded-lg border-l-2 border-indigo-500 italic mt-1.5">
                      "{ref.matched_passage}"
                    </p>
                  )}
                </div>

                {ref.url && (
                  <a
                    href={ref.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-indigo-600 hover:text-indigo-800 shrink-0 px-2 py-1 rounded-lg hover:bg-neutral-100 text-xs font-semibold transition-colors cursor-pointer"
                    title="Open paper in new tab"
                  >
                    <span>Source</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
};

export default SynthesisReportViewer;
