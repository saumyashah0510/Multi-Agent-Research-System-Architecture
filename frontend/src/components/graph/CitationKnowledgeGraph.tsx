/**
 * CitationKnowledgeGraph Component
 *
 * Assignee Task (Issue FE-14):
 * 1. Install D3 dependencies:
 *    npm install d3
 *    npm install -D @types/d3
 * 2. Fetch graph topology via fetchReviewGraph(reviewId) (GET /api/v1/reviews/{id}/graph).
 * 3. Initialize D3 Force Simulation:
 *    - d3.forceSimulation<GraphNode>(nodes)
 *    - d3.forceLink<GraphNode, GraphLink>(links).id(d => d.id).distance(100)
 *    - d3.forceManyBody().strength(-200)
 *    - d3.forceCenter(width / 2, height / 2)
 *    - d3.forceCollide().radius(30)
 * 4. Add interactive zoom and pan via d3.zoom().
 * 5. Add node dragging behavior via d3.drag().
 * 6. Color-code nodes by their thematic cluster and highlight connected edges on click/hover.
 */

import React, { useEffect, useState, useRef } from "react";
import {
  Network,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  ExternalLink,
  Loader2,
  AlertCircle,
  FileText,
  User,
  Calendar,
  Layers,
} from "lucide-react";
import { fetchReviewGraph } from "../../lib/api";
import { CitationGraphResponse, GraphNode } from "../../types";

interface CitationKnowledgeGraphProps {
  reviewId: string;
}

const CLUSTER_COLORS = [
  "#3B82F6", // blue
  "#10B981", // emerald
  "#8B5CF6", // purple
  "#F59E0B", // amber
  "#EC4899", // pink
  "#06B6D4", // cyan
];

export const CitationKnowledgeGraph: React.FC<CitationKnowledgeGraphProps> = ({
  reviewId,
}) => {
  const [data, setData] = useState<CitationGraphResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [zoomLevel, setZoomLevel] = useState<number>(1);

  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  // Derive unique clusters for consistent color mapping across the graph
  const uniqueClusters = React.useMemo(() => {
    if (!data?.nodes) return [];
    const clusters = new Set<string>();
    data.nodes.forEach((n) => {
      if (n.cluster && n.cluster.trim()) {
        clusters.add(n.cluster.trim());
      }
    });
    return Array.from(clusters);
  }, [data]);

  const getNodeColor = (node: GraphNode, fallbackIndex: number): string => {
    if (node.cluster && node.cluster.trim()) {
      const cIdx = uniqueClusters.indexOf(node.cluster.trim());
      if (cIdx >= 0) {
        return CLUSTER_COLORS[cIdx % CLUSTER_COLORS.length] || "#3B82F6";
      }
    }
    return CLUSTER_COLORS[fallbackIndex % CLUSTER_COLORS.length] || "#3B82F6";
  };

  useEffect(() => {
    let isMounted = true;
    async function loadGraph() {
      if (!reviewId) return;
      setIsLoading(true);
      setError(null);
      try {
        const result = await fetchReviewGraph(reviewId);
        if (isMounted) {
          setData(result);
          if (result.nodes && result.nodes.length > 0) {
            setSelectedNode(result.nodes[0] ?? null);
          }
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || "Failed to load citation knowledge graph");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }
    loadGraph();
    return () => {
      isMounted = false;
    };
  }, [reviewId]);

  // TODO (Assignee - FE-14):
  // Integrate d3.forceSimulation on svgRef once d3 and @types/d3 are installed.
  // const svg = d3.select(svgRef.current);
  // const simulation = d3.forceSimulation(data.nodes)
  //   .force("link", d3.forceLink(data.links).id((d: any) => d.id).distance(100))
  //   .force("charge", d3.forceManyBody().strength(-200))
  //   .force("center", d3.forceCenter(width / 2, height / 2));

  const handleZoomIn = () => setZoomLevel((z) => Math.min(z + 0.2, 2.5));
  const handleZoomOut = () => setZoomLevel((z) => Math.max(z - 0.2, 0.5));
  const handleResetZoom = () => setZoomLevel(1);

  return (
    <div
      ref={containerRef}
      className="relative w-full bg-white rounded-2xl border border-neutral-200/90 shadow-xs overflow-hidden flex flex-col"
      style={{ minHeight: "580px" }}
    >
      {/* Header Bar */}
      <div className="px-6 py-4 border-b border-neutral-100 flex flex-wrap items-center justify-between gap-3 bg-neutral-50/50">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center text-indigo-600">
            <Network className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-neutral-900">
              Citation Knowledge Graph
            </h2>
            <p className="text-xs text-neutral-500">
              Interactive topology mapping thematic clusters, citations, and co-authorship
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {data && (
            <div className="flex items-center gap-2 text-xs text-neutral-500 mr-2">
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-neutral-100 font-medium">
                {data.total_nodes} Papers
              </span>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-neutral-100 font-medium">
                {data.total_links} Connections
              </span>
            </div>
          )}

          {/* Zoom Controls */}
          <div className="flex items-center border border-neutral-200 rounded-lg bg-white overflow-hidden shadow-2xs">
            <button
              type="button"
              onClick={handleZoomIn}
              className="p-1.5 hover:bg-neutral-100 text-neutral-600 transition-colors"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={handleZoomOut}
              className="p-1.5 hover:bg-neutral-100 text-neutral-600 transition-colors border-l border-neutral-200"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={handleResetZoom}
              className="p-1.5 hover:bg-neutral-100 text-neutral-600 transition-colors border-l border-neutral-200"
              title="Reset Zoom"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Canvas Area */}
      <div className="relative flex-1 min-h-[460px] bg-radial from-neutral-50/50 to-white flex items-center justify-center overflow-hidden">
        {isLoading && (
          <div className="flex flex-col items-center gap-2 text-neutral-500">
            <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
            <span className="text-xs font-medium">Constructing knowledge graph...</span>
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center gap-2 text-amber-700 p-6 text-center max-w-md">
            <AlertCircle className="w-6 h-6" />
            <p className="text-xs">{error}</p>
          </div>
        )}

        {!isLoading && !error && (!data || data.nodes.length === 0) && (
          <div className="flex flex-col items-center gap-2 text-neutral-400 p-8 text-center max-w-sm">
            <Layers className="w-8 h-8 stroke-[1.5]" />
            <p className="text-xs">
              No approved papers found for this review session to construct the knowledge graph.
            </p>
          </div>
        )}

        {!isLoading && !error && data && data.nodes.length > 0 && (
          <>
            {/* SVG Interactive Canvas */}
            <svg
              ref={svgRef}
              className="w-full h-full cursor-grab active:cursor-grabbing"
              viewBox="0 0 800 500"
            >
              <g
                transform={`scale(${zoomLevel}) translate(${400 * (1 - zoomLevel)}, ${
                  250 * (1 - zoomLevel)
                })`}
              >
                {/* Simulated Links */}
                {data.links.map((link, idx) => {
                  const sourceNode =
                    typeof link.source === "object"
                      ? link.source
                      : data.nodes.find((n) => n.id === link.source);
                  const targetNode =
                    typeof link.target === "object"
                      ? link.target
                      : data.nodes.find((n) => n.id === link.target);

                  const sIdx = data.nodes.indexOf(sourceNode as GraphNode);
                  const tIdx = data.nodes.indexOf(targetNode as GraphNode);

                  // Radial coordinate distribution for initial fallback view
                  const total = data.nodes.length;
                  const sAngle = (sIdx / total) * 2 * Math.PI;
                  const tAngle = (tIdx / total) * 2 * Math.PI;
                  const x1 = 400 + 180 * Math.cos(sAngle);
                  const y1 = 250 + 180 * Math.sin(sAngle);
                  const x2 = 400 + 180 * Math.cos(tAngle);
                  const y2 = 250 + 180 * Math.sin(tAngle);

                  return (
                    <line
                      key={`link-${idx}`}
                      x1={x1}
                      y1={y1}
                      x2={x2}
                      y2={y2}
                      stroke="#E2E8F0"
                      strokeWidth={Math.max(1, (link.weight || 0.5) * 3)}
                      strokeDasharray={
                        link.type === "co_authorship" ? "4,4" : undefined
                      }
                    />
                  );
                })}

                {/* Simulated Nodes */}
                {data.nodes.map((node, idx) => {
                  const angle = (idx / data.nodes.length) * 2 * Math.PI;
                  const cx = 400 + 180 * Math.cos(angle);
                  const cy = 250 + 180 * Math.sin(angle);
                  const isSelected = selectedNode?.id === node.id;
                  const color = getNodeColor(node, idx);

                  return (
                    <g
                      key={node.id}
                      transform={`translate(${cx}, ${cy})`}
                      onClick={() => setSelectedNode(node)}
                      className="cursor-pointer transition-transform duration-150 hover:scale-110"
                    >
                      <circle
                        r={isSelected ? 18 : 14}
                        fill={color}
                        fillOpacity={0.9}
                        stroke={isSelected ? "#1E293B" : "#FFFFFF"}
                        strokeWidth={isSelected ? 3 : 2}
                        className="shadow-sm"
                      />
                      <text
                        dy={26}
                        textAnchor="middle"
                        className="text-[10px] font-sans fill-neutral-700 select-none pointer-events-none font-medium"
                      >
                        {node.label.length > 20
                          ? `${node.label.slice(0, 18)}...`
                          : node.label}
                      </text>
                    </g>
                  );
                })}
              </g>
            </svg>

            {/* Selected Node Inspector Sidebar Card */}
            {selectedNode && (
              <div className="absolute top-4 right-4 w-72 bg-white/95 backdrop-blur-sm rounded-xl border border-neutral-200/90 shadow-lg p-4 space-y-3 text-xs animate-in fade-in">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-1.5 text-neutral-500 font-medium">
                    <FileText className="w-3.5 h-3.5 text-indigo-600" />
                    <span>Selected Paper</span>
                  </div>
                  {selectedNode.relevance_score && (
                    <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-semibold text-[10px]">
                      {Math.round(selectedNode.relevance_score * 100)}% Match
                    </span>
                  )}
                </div>

                <h3 className="font-serif font-bold text-neutral-900 text-xs leading-snug">
                  {selectedNode.label}
                </h3>

                {selectedNode.authors && selectedNode.authors.length > 0 && (
                  <div className="flex items-center gap-1.5 text-neutral-600">
                    <User className="w-3.5 h-3.5 shrink-0 text-neutral-400" />
                    <span className="truncate">
                      {selectedNode.authors.slice(0, 3).join(", ")}
                      {selectedNode.authors.length > 3 && " et al."}
                    </span>
                  </div>
                )}

                {selectedNode.year && (
                  <div className="flex items-center gap-1.5 text-neutral-600">
                    <Calendar className="w-3.5 h-3.5 shrink-0 text-neutral-400" />
                    <span>Published {selectedNode.year}</span>
                  </div>
                )}

                {selectedNode.cluster && (
                  <div className="pt-1">
                    <span className="inline-block px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 text-[10px] font-medium">
                      Cluster: {selectedNode.cluster}
                    </span>
                  </div>
                )}

                {selectedNode.url && (
                  <div className="pt-2 border-t border-neutral-100">
                    <a
                      href={selectedNode.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-indigo-600 hover:text-indigo-800 font-medium transition-colors"
                    >
                      <span>Open Source Document</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                )}
              </div>
            )}

            {/* Thematic Cluster Color Legend */}
            {uniqueClusters.length > 0 && (
              <div className="absolute bottom-3 left-4 max-w-xl flex flex-wrap items-center gap-3 bg-white/95 backdrop-blur-xs px-3.5 py-2 rounded-xl border border-neutral-200/90 shadow-sm text-xs text-neutral-600">
                <span className="font-semibold text-neutral-500 uppercase tracking-wider text-[10px]">
                  Thematic Clusters:
                </span>
                {uniqueClusters.map((clusterName, cIdx) => (
                  <div key={clusterName} className="flex items-center gap-1.5">
                    <span
                      className="w-2.5 h-2.5 rounded-full shrink-0"
                      style={{
                        backgroundColor:
                          CLUSTER_COLORS[cIdx % CLUSTER_COLORS.length] || "#3B82F6",
                      }}
                    />
                    <span
                      className="truncate max-w-[150px] font-medium text-[11px]"
                      title={clusterName}
                    >
                      {clusterName}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default CitationKnowledgeGraph;
