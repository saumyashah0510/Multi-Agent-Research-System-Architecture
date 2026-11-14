/**
 * MethodologyMatrix Component
 *
 * Assignee Task (Issue FE-08):
 * - Render comparative methodology matrix extracted by Agent 07
 * - Table format comparing Method Name, Papers Applied, Strengths, and Limitations
 * - Provide real-time search filter to quickly inspect specific approaches or algorithms
 * - Responsive table with horizontal scroll support on small screens
 */

import React from "react";
import { Layers, CircleCheck, AlertCircle } from "lucide-react";
import { MethodologyItem } from "../../types";
import { ReferenceItem } from "./ReferenceCard";

export interface MethodologyMatrixProps {
  matrix: MethodologyItem[];
  references?: ReferenceItem[];
  className?: string;
}

function findReferenceHref(paper: string, references?: ReferenceItem[]): string {
  if (!references || references.length === 0) return "#section-references";

  const raw = paper.toLowerCase().trim();
  const coreName = raw.replace(/\[[^\]]*\]/g, "").replace(/\([^)]*\)/g, "").trim();
  const yearMatch = raw.match(/\b(19|20)\d{2}\b/);
  const year = yearMatch ? yearMatch[0] : null;
  const tokens = raw
    .split(/[^a-z0-9]+/)
    .filter((t) => t.length >= 4 && t !== "2024" && t !== "2025" && t !== "2026" && t !== "arxiv");

  // 1. Search all references for an exact or normalized title match first
  if (coreName.length >= 4) {
    const exactTitleIdx = references.findIndex(
      (ref) => (ref.title || "").toLowerCase().trim() === coreName
    );
    if (exactTitleIdx >= 0) return `#reference-${exactTitleIdx + 1}`;

    const titleMatches = references.reduce<number[]>((acc, ref, idx) => {
      if ((ref.title || "").toLowerCase().includes(coreName)) acc.push(idx);
      return acc;
    }, []);
    if (titleMatches.length === 1 && titleMatches[0] !== undefined) {
      return `#reference-${titleMatches[0] + 1}`;
    }
  }

  // 2. Fall back to token matching only when no title match exists; reject ambiguous matches
  if (tokens.length > 0) {
    if (year) {
      const yearTokenMatches = references.reduce<number[]>((acc, ref, idx) => {
        const title = (ref.title || "").toLowerCase();
        const authors = (ref.authors || []).join(" ").toLowerCase();
        const refYear = ref.year ? String(ref.year) : "";
        if (refYear === year && tokens.some((t) => authors.includes(t) || title.includes(t))) {
          acc.push(idx);
        }
        return acc;
      }, []);
      if (yearTokenMatches.length === 1 && yearTokenMatches[0] !== undefined) {
        return `#reference-${yearTokenMatches[0] + 1}`;
      }
    }

    const tokenMatches = references.reduce<number[]>((acc, ref, idx) => {
      const title = (ref.title || "").toLowerCase();
      const authors = (ref.authors || []).join(" ").toLowerCase();
      if (tokens.some((t) => title.includes(t) || authors.includes(t))) {
        acc.push(idx);
      }
      return acc;
    }, []);
    if (tokenMatches.length === 1 && tokenMatches[0] !== undefined) {
      return `#reference-${tokenMatches[0] + 1}`;
    }
  }

  return "#section-references";
}

export const MethodologyMatrix: React.FC<MethodologyMatrixProps> = ({
  matrix,
  references,
  className = "",
}) => {
  const safeMatrix = Array.isArray(matrix) ? matrix : [];

  return (
    <div
      className={`w-full bg-white rounded-2xl border border-neutral-200/90 shadow-xs p-5 sm:p-6 space-y-4 ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between gap-3 pb-3 border-b border-neutral-100">
        <div className="flex items-center gap-2.5 flex-wrap">
          <Layers className="w-5 h-5 text-[var(--color-sky-dark)] shrink-0" />
          <h3 className="font-serif text-lg sm:text-xl font-bold text-neutral-900">
            Comparative methodology matrix
          </h3>
          <span
            style={{ borderRadius: "var(--radius-sm)" }}
            className="text-xs bg-neutral-100 text-neutral-700 font-semibold px-2.5 py-0.5 border border-neutral-200/80"
          >
            {safeMatrix.length} methods
          </span>
        </div>
      </div>

      {/* Responsive Comparison Table with Horizontal Scroll Support */}
      <div className="overflow-x-auto -mx-5 sm:mx-0 px-5 sm:px-0">
        <table className="w-full min-w-[760px] text-left text-xs border-collapse">
          <thead>
            <tr className="bg-neutral-50 text-neutral-600 uppercase tracking-wider text-[11px] border-b border-neutral-200">
              <th className="py-3.5 px-4 font-semibold w-[22%]">Methodology</th>
              <th className="py-3.5 px-4 font-semibold w-[20%]">Papers Applied</th>
              <th className="py-3.5 px-4 font-semibold w-[29%]">
                <span className="inline-flex items-center gap-1.5">
                  <CircleCheck className="w-3.5 h-3.5 text-[var(--color-success)]" />
                  <span>Advantages</span>
                </span>
              </th>
              <th className="py-3.5 px-4 font-semibold w-[29%]">
                <span className="inline-flex items-center gap-1.5">
                  <AlertCircle className="w-3.5 h-3.5 text-amber-500" />
                  <span>Known Limitations</span>
                </span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-100">
            {safeMatrix.length > 0 ? (
              safeMatrix.map((item, idx) => (
                <tr
                  key={idx}
                  className="hover:bg-neutral-50/70 transition-colors"
                >
                  {/* Methodology Name */}
                  <td className="py-4 px-4 font-semibold text-neutral-900 align-top">
                    <span className="font-serif text-[13px] sm:text-sm font-bold text-neutral-900">
                      {item.method_name}
                    </span>
                  </td>

                  {/* Target Papers Applied */}
                  <td className="py-4 px-4 text-neutral-700 align-top">
                    {item.papers_used && item.papers_used.length > 0 ? (
                      <ul className="space-y-1.5">
                        {item.papers_used.map((paper, pIdx) => (
                          <li key={pIdx} className="flex items-start gap-2">
                            <span
                              aria-hidden="true"
                              className="w-1.5 h-1.5 rounded-full bg-neutral-400 shrink-0 mt-1.5"
                            />
                            <a
                              href={findReferenceHref(paper, references)}
                              className="text-[11.5px] font-medium text-neutral-700 underline decoration-neutral-300 underline-offset-2 hover:text-neutral-950 hover:decoration-neutral-600 transition-colors leading-snug"
                              title={`Jump to reference for ${paper}`}
                            >
                              {paper}
                            </a>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <span className="text-neutral-400 text-[11px] italic">Not specified</span>
                    )}
                  </td>

                  {/* Advantages & Strengths */}
                  <td className="py-4 px-4 align-top text-neutral-700">
                    {item.strengths && item.strengths.length > 0 ? (
                      <ul className="space-y-1.5">
                        {item.strengths.map((str, sIdx) => (
                          <li
                            key={sIdx}
                            className="flex items-start gap-2 text-[11.5px] leading-snug"
                          >
                            <CircleCheck className="w-3.5 h-3.5 text-[var(--color-success)] shrink-0 mt-0.5 stroke-[2.2]" />
                            <span>{str}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <span className="text-neutral-400 text-[11px] italic">No strengths listed</span>
                    )}
                  </td>

                  {/* Known Limitations */}
                  <td className="py-4 px-4 align-top text-neutral-700">
                    {item.limitations && item.limitations.length > 0 ? (
                      <ul className="space-y-1.5">
                        {item.limitations.map((lim, lIdx) => (
                          <li
                            key={lIdx}
                            className="flex items-start gap-2 text-[11.5px] leading-snug text-neutral-600"
                          >
                            <AlertCircle className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5 stroke-[2.2]" />
                            <span>{lim}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <span className="text-neutral-400 text-[11px] italic">No limitations listed</span>
                    )}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={4} className="py-10 text-center text-neutral-400">
                  <div className="space-y-1">
                    <p className="font-medium text-neutral-600">No methodology matrix available</p>
                    <p className="text-xs text-neutral-400">
                      Methodology comparisons will appear here once Agent 07 finishes analyzing approved literature.
                    </p>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default MethodologyMatrix;
