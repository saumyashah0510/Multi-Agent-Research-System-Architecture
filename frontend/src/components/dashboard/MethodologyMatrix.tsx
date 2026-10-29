/**
 * MethodologyMatrix Component
 *
 * Assignee Task (Issue FE-08):
 * - Render comparative methodology matrix extracted by Agent 07
 * - Table format comparing Method Name, Papers Used, Strengths, and Limitations
 * - Provide search filter to quickly inspect specific approaches or algorithms
 * - Responsive table with horizontal scroll support on small screens
 */

import React, { useState } from "react";
import { Search, Layers, CheckCircle2, AlertTriangle } from "lucide-react";
import { MethodologyItem } from "../../types";

export interface MethodologyMatrixProps {
  matrix: MethodologyItem[];
  className?: string;
}

export const MethodologyMatrix: React.FC<MethodologyMatrixProps> = ({ matrix, className = "" }) => {
  const [searchTerm, setSearchTerm] = useState("");

  // TODO (Assignee - FE-08):
  // 1. Filter matrix rows by searchTerm (matching method_name or paper title)
  // 2. Render responsive table with headers: Methodology, Target Papers, Strengths, Limitations
  // 3. Highlight strengths with subtle emerald styling and limitations with amber/rose styling
  // 4. Handle empty state if no methodology comparisons were generated

  const filteredMatrix = matrix.filter(
    (item) =>
      item.method_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.papers_used.some((p) => p.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <div className={`w-full bg-white rounded-2xl border border-neutral-200 shadow-xs p-5 sm:p-6 space-y-4 ${className}`}>
      {/* Header with Title and Search Input */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-neutral-100">
        <div className="flex items-center gap-2">
          <Layers className="w-5 h-5 text-indigo-600" />
          <h3 className="font-serif text-lg font-bold text-neutral-900">
            Methodology Comparison Matrix
          </h3>
          <span className="text-xs bg-neutral-100 text-neutral-700 font-semibold px-2 py-0.5 rounded-full">
            {matrix.length} methods
          </span>
        </div>

        <div className="relative w-full sm:w-64">
          <Search className="w-4 h-4 text-neutral-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search methods or papers..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-neutral-50 border border-neutral-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>
      </div>

      {/* Comparison Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-neutral-50 text-neutral-600 uppercase tracking-wider text-[11px] border-b border-neutral-200">
              <th className="py-2.5 px-3 font-semibold">Methodology</th>
              <th className="py-2.5 px-3 font-semibold">Papers Applied</th>
              <th className="py-2.5 px-3 font-semibold">Advantages / Strengths</th>
              <th className="py-2.5 px-3 font-semibold">Known Limitations</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-100">
            {filteredMatrix.length > 0 ? (
              filteredMatrix.map((item, idx) => (
                <tr key={idx} className="hover:bg-neutral-50/60 transition-colors">
                  <td className="py-3 px-3 font-semibold text-neutral-900 align-top">
                    {item.method_name}
                  </td>
                  <td className="py-3 px-3 text-neutral-700 align-top">
                    <div className="flex flex-wrap gap-1">
                      {item.papers_used.map((paper, pIdx) => (
                        <span
                          key={pIdx}
                          className="bg-neutral-100 text-neutral-800 text-[10px] px-2 py-0.5 rounded-md"
                        >
                          {paper}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="py-3 px-3 align-top text-neutral-700">
                    <ul className="space-y-1">
                      {item.strengths.map((str, sIdx) => (
                        <li key={sIdx} className="flex items-start gap-1.5 text-[11px]">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                          <span>{str}</span>
                        </li>
                      ))}
                    </ul>
                  </td>
                  <td className="py-3 px-3 align-top text-neutral-700">
                    <ul className="space-y-1">
                      {item.limitations.map((lim, lIdx) => (
                        <li key={lIdx} className="flex items-start gap-1.5 text-[11px]">
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
                          <span>{lim}</span>
                        </li>
                      ))}
                    </ul>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={4} className="py-8 text-center text-neutral-400">
                  No methodologies match your search query.
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
