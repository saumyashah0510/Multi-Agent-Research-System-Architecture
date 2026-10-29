/**
 * SynthesisReportViewer Component
 *
 * Assignee Task (Issue FE-08):
 * - Render publication-grade literature review synthesized by Agent 09
 * - Display Executive Summary, Thematic Clusters, Research Gaps, and References
 * - Format citations and academic references with external links
 * - Support copy-to-markdown or clean export formatting
 */

import React from "react";
import { BookOpen, Compass, ExternalLink, Bookmark } from "lucide-react";
import { SynthesizedReview } from "../../types";

export interface SynthesisReportViewerProps {
  report: SynthesizedReview;
  className?: string;
}

export const SynthesisReportViewer: React.FC<SynthesisReportViewerProps> = ({ report, className = "" }) => {
  // TODO (Assignee - FE-08):
  // 1. Render formal academic Title and Executive Summary in an elegant hero container
  // 2. Map thematic_clusters into multi-column or stacked cards with cited paper keys
  // 3. Render 3-5 research gaps highlighted with actionable callout styling
  // 4. Render references bibliography with author lists, years, and verified source quotes

  return (
    <div className={`w-full space-y-6 ${className}`}>
      {/* Title & Executive Summary Card */}
      <div className="w-full bg-white rounded-2xl border border-neutral-200 shadow-xs p-6 sm:p-8 space-y-4">
        <div className="flex items-center gap-2 text-indigo-600 text-xs font-semibold uppercase tracking-wider">
          <BookOpen className="w-4 h-4" />
          <span>Synthesized Literature Review</span>
        </div>

        <h2 className="font-serif text-2xl sm:text-3xl font-bold text-neutral-900 leading-snug">
          {report.title}
        </h2>

        <div className="p-4 sm:p-5 bg-neutral-50 rounded-xl border border-neutral-100 text-neutral-700 text-sm leading-relaxed">
          <p className="font-medium text-neutral-900 mb-1 text-xs uppercase tracking-wide">
            Executive Summary
          </p>
          <p>{report.executive_summary}</p>
        </div>
      </div>

      {/* Thematic Clusters Section */}
      {report.thematic_clusters && report.thematic_clusters.length > 0 && (
        <div className="space-y-4">
          <h3 className="font-serif text-xl font-bold text-neutral-900 flex items-center gap-2">
            <Bookmark className="w-5 h-5 text-indigo-600" />
            <span>Thematic Clusters & Core Findings</span>
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {report.thematic_clusters.map((cluster, idx) => (
              <div
                key={idx}
                className="bg-white rounded-2xl border border-neutral-200 shadow-xs p-5 space-y-3"
              >
                <h4 className="font-serif text-base font-bold text-neutral-900">
                  {cluster.theme}
                </h4>
                <p className="text-xs text-neutral-600 leading-relaxed">
                  {cluster.summary}
                </p>
                {cluster.citations && cluster.citations.length > 0 && (
                  <div className="pt-2 border-t border-neutral-100 flex flex-wrap gap-1.5 items-center">
                    <span className="text-[10px] text-neutral-400 uppercase font-semibold">Citations:</span>
                    {cluster.citations.map((cite, cIdx) => (
                      <span
                        key={cIdx}
                        className="bg-indigo-50 text-indigo-700 text-[10px] font-medium px-2 py-0.5 rounded-md"
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
      {report.research_gaps && report.research_gaps.length > 0 && (
        <div className="w-full bg-white rounded-2xl border border-neutral-200 shadow-xs p-6 space-y-3">
          <h3 className="font-serif text-lg font-bold text-neutral-900 flex items-center gap-2">
            <Compass className="w-5 h-5 text-amber-500" />
            <span>Identified Research Gaps & Open Challenges</span>
          </h3>
          <ul className="space-y-2">
            {report.research_gaps.map((gap, gIdx) => (
              <li
                key={gIdx}
                className="flex items-start gap-2.5 text-xs text-neutral-700 bg-amber-50/50 p-3 rounded-xl border border-amber-100"
              >
                <span className="w-5 h-5 rounded-full bg-amber-100 text-amber-800 text-[10px] font-bold flex items-center justify-center shrink-0">
                  {gIdx + 1}
                </span>
                <span className="leading-relaxed">{gap}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* References Section */}
      {report.references && report.references.length > 0 && (
        <div className="w-full bg-white rounded-2xl border border-neutral-200 shadow-xs p-6 space-y-3">
          <h3 className="font-serif text-lg font-bold text-neutral-900">
            Verified References & Bibliography
          </h3>
          <ol className="divide-y divide-neutral-100 text-xs text-neutral-700">
            {report.references.map((ref, rIdx) => (
              <li key={rIdx} className="py-2.5 flex items-start justify-between gap-4">
                <div>
                  <p className="font-semibold text-neutral-900">{ref.title || `Reference #${rIdx + 1}`}</p>
                  <p className="text-[11px] text-neutral-500">
                    {ref.authors?.join(", ") || "Authors unlisted"} · {ref.year || "n.d."}
                  </p>
                  {ref.matched_passage && (
                    <p className="text-[10px] text-neutral-600 bg-neutral-50 p-2 rounded-md mt-1 border-l-2 border-indigo-500 italic">
                      "{ref.matched_passage}"
                    </p>
                  )}
                </div>
                {ref.url && (
                  <a
                    href={ref.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-indigo-600 hover:text-indigo-800 shrink-0 p-1 rounded-md hover:bg-neutral-100 transition-colors"
                  >
                    <ExternalLink className="w-4 h-4" />
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
