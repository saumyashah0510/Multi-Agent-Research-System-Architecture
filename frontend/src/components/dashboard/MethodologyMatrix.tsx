/**
 * MethodologyMatrix Component
 *
 * Assignee Task (Issue FE-08):
 * - Render comparative methodology matrix extracted by Agent 07
 * - Table format comparing Method Name, Papers Applied, Strengths, and Limitations
 * - Provide real-time search filter to quickly inspect specific approaches or algorithms
 * - Responsive table with horizontal scroll support on small screens
 */

import React, { useState } from "react";
import { Search, Layers, CheckCircle2, AlertTriangle, X } from "lucide-react";
import { MethodologyItem } from "../../types";

export interface MethodologyMatrixProps {
  matrix: MethodologyItem[];
  className?: string;
}

export const MethodologyMatrix: React.FC<MethodologyMatrixProps> = ({
  matrix,
  className = "",
}) => {
  const [searchTerm, setSearchTerm] = useState("");

  const safeMatrix = Array.isArray(matrix) ? matrix : [];

  const filteredMatrix = safeMatrix.filter((item) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    const matchesMethod = item.method_name?.toLowerCase().includes(term);
    const matchesPaper = item.papers_used?.some((p) =>
      String(p).toLowerCase().includes(term)
    );
    const matchesStrengths = item.strengths?.some((s) =>
      String(s).toLowerCase().includes(term)
    );
    const matchesLimitations = item.limitations?.some((l) =>
      String(l).toLowerCase().includes(term)
    );
    return Boolean(matchesMethod || matchesPaper || matchesStrengths || matchesLimitations);
  });

  return (
    <div
      className={`w-full bg-white rounded-2xl border border-neutral-200/90 shadow-xs p-5 sm:p-6 space-y-4 ${className}`}
    >
      {/* Header with Title and Search Input */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-neutral-100">
        <div className="flex items-center gap-2 flex-wrap">
          <Layers className="w-5 h-5 text-indigo-600 shrink-0" />
          <h3 className="font-serif text-lg sm:text-xl font-bold text-neutral-900">
            Methodology Comparison Matrix
          </h3>
          <span className="text-xs bg-neutral-100 text-neutral-700 font-semibold px-2.5 py-0.5 rounded-full border border-neutral-200">
            {searchTerm.trim()
              ? `${filteredMatrix.length} of ${safeMatrix.length} methods`
              : `${safeMatrix.length} methods`}
          </span>
        </div>

        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 text-neutral-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search methods, papers, or criteria..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-8 py-1.5 text-xs bg-neutral-50 border border-neutral-200 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:bg-white transition-all text-neutral-900"
            aria-label="Filter methodology matrix"
          />
          {searchTerm && (
            <button
              type="button"
              onClick={() => setSearchTerm("")}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600 p-0.5 rounded cursor-pointer"
              aria-label="Clear search input"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Responsive Comparison Table with Horizontal Scroll Support */}
      <div className="overflow-x-auto -mx-5 sm:mx-0 px-5 sm:px-0">
        <table className="w-full min-w-[720px] text-left text-xs border-collapse">
          <thead>
            <tr className="bg-neutral-50 text-neutral-600 uppercase tracking-wider text-[11px] border-b border-neutral-200">
              <th className="py-3 px-3.5 font-semibold w-1/4">Methodology</th>
              <th className="py-3 px-3.5 font-semibold w-1/4">Papers Applied</th>
              <th className="py-3 px-3.5 font-semibold w-1/4">Advantages / Strengths</th>
              <th className="py-3 px-3.5 font-semibold w-1/4">Known Limitations</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-100">
            {filteredMatrix.length > 0 ? (
              filteredMatrix.map((item, idx) => (
                <tr
                  key={idx}
                  className="hover:bg-neutral-50/70 transition-colors group"
                >
                  {/* Methodology Name */}
                  <td className="py-3.5 px-3.5 font-semibold text-neutral-900 align-top">
                    <span className="font-serif text-[13px] sm:text-sm font-bold text-neutral-900 group-hover:text-indigo-900 transition-colors">
                      {item.method_name}
                    </span>
                  </td>

                  {/* Target Papers Applied */}
                  <td className="py-3.5 px-3.5 text-neutral-700 align-top">
                    {item.papers_used && item.papers_used.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5">
                        {item.papers_used.map((paper, pIdx) => (
                          <span
                            key={pIdx}
                            className="bg-neutral-100 text-neutral-800 border border-neutral-200/80 text-[10.5px] px-2 py-0.5 rounded-md inline-block max-w-full truncate font-medium"
                            title={paper}
                          >
                            {paper}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-neutral-400 text-[11px] italic">Not specified</span>
                    )}
                  </td>

                  {/* Advantages & Strengths */}
                  <td className="py-3.5 px-3.5 align-top text-neutral-700">
                    {item.strengths && item.strengths.length > 0 ? (
                      <ul className="space-y-1.5">
                        {item.strengths.map((str, sIdx) => (
                          <li
                            key={sIdx}
                            className="flex items-start gap-1.5 text-[11.5px] leading-snug"
                          >
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                            <span>{str}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <span className="text-neutral-400 text-[11px] italic">No strengths listed</span>
                    )}
                  </td>

                  {/* Known Limitations */}
                  <td className="py-3.5 px-3.5 align-top text-neutral-700">
                    {item.limitations && item.limitations.length > 0 ? (
                      <ul className="space-y-1.5">
                        {item.limitations.map((lim, lIdx) => (
                          <li
                            key={lIdx}
                            className="flex items-start gap-1.5 text-[11.5px] leading-snug text-neutral-600"
                          >
                            <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
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
                  {safeMatrix.length === 0 ? (
                    <div className="space-y-1">
                      <p className="font-medium text-neutral-600">No methodology matrix available</p>
                      <p className="text-xs text-neutral-400">
                        Methodology comparisons will appear here once Agent 07 finishes analyzing approved literature.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <p className="text-neutral-600">
                        No methodologies match &ldquo;<span className="font-semibold">{searchTerm}</span>&rdquo;.
                      </p>
                      <button
                        type="button"
                        onClick={() => setSearchTerm("")}
                        className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold underline cursor-pointer"
                      >
                        Clear search filter
                      </button>
                    </div>
                  )}
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
