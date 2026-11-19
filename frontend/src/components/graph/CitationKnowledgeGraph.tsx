/**
 * CitationKnowledgeGraph Component
 *
 * Implements Issue [FE-14]: Interactive D3.js Citation Knowledge Graph
 * - Interactive D3 force simulation with collision avoidance, center pull, and link tension
 * - Categorical cluster color distribution (#3B82F6, #10B981, #8B5CF6, #F59E0B, #EC4899, #06B6D4)
 * - Draggable nodes to rearrange the graph layout
 * - Interactive zoom & pan via mouse drag/scroll and UI buttons (Zoom In, Zoom Out, Reset)
 * - Click-to-inspect side card detailing paper metadata (Title, Authors, Year, Relevance, Cluster, URL)
 * - Hover & selection highlighting: highlights connected neighbors/edges in #4F46E5, dims unlinked nodes to 0.25 opacity
 * - Floating bottom-left cluster legend mapping color swatches to cluster titles
 * - Graceful empty state when no approved papers exist
 */

import React, { useEffect, useState, useRef, useMemo } from "react";
import * as d3 from "d3";
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
  X,
  Bookmark,
} from "lucide-react";
import { fetchReviewGraph } from "../../lib/api";
import { CitationGraphResponse, GraphLink, GraphNode } from "../../types";

interface CitationKnowledgeGraphProps {
  reviewId: string;
}

// Categorical palette for thematic clusters (FE-14 specification)
export const CLUSTER_COLORS = [
  "#3B82F6", // Blue
  "#10B981", // Emerald
  "#8B5CF6", // Purple
  "#F59E0B", // Amber
  "#EC4899", // Pink
  "#06B6D4", // Cyan
];

const DEFAULT_COLOR = "#3B82F6";

export const CitationKnowledgeGraph: React.FC<CitationKnowledgeGraphProps> = ({
  reviewId,
}) => {
  const [data, setData] = useState<CitationGraphResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const zoomBehaviorRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const selectedNodeRef = useRef<GraphNode | null>(null);
  const highlightFnRef = useRef<((node: GraphNode | null) => void) | null>(null);

  // Derive unique clusters for consistent color mapping across the graph
  const uniqueClusters = useMemo(() => {
    if (!data?.nodes) return [];
    const clusters = new Set<string>();
    data.nodes.forEach((n) => {
      if (n.cluster && n.cluster.trim()) {
        clusters.add(n.cluster.trim());
      }
    });
    return Array.from(clusters);
  }, [data]);

  // Thematic Cluster Color Scale
  const clusterColorScale = useMemo(() => {
    return d3.scaleOrdinal<string>()
      .domain(uniqueClusters)
      .range(CLUSTER_COLORS);
  }, [uniqueClusters]);

  const getNodeColor = (node: GraphNode, fallbackIndex: number = 0): string => {
    if (node.cluster && node.cluster.trim()) {
      const scaled = clusterColorScale(node.cluster.trim());
      if (scaled) return scaled;
    }
    const fallback = CLUSTER_COLORS[fallbackIndex % CLUSTER_COLORS.length];
    return fallback ?? DEFAULT_COLOR;
  };

  // Synchronize selectedNode ref and propagate highlighting updates
  useEffect(() => {
    selectedNodeRef.current = selectedNode;
    if (highlightFnRef.current) {
      highlightFnRef.current(selectedNode);
    }
  }, [selectedNode]);

  // Fetch graph topology
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

  // Setup D3 Force Simulation, Zoom, Drag, and Highlighting
  useEffect(() => {
    if (!svgRef.current || !data || !data.nodes || data.nodes.length === 0) {
      return;
    }

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const width = 800;
    const height = 500;

    // Create cloned copies so D3 simulation mutations do not alter props or state
    const nodes: GraphNode[] = data.nodes.map((d) => ({ ...d }));
    const links: GraphLink[] = data.links.map((d) => ({ ...d }));

    // Root container group for zoom and pan transformations
    const g = svg.append("g").attr("class", "graph-root");

    // Initialize D3 Zoom behavior
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 4])
      .on("zoom", (event) => {
        g.attr("transform", event.transform.toString());
      });

    svg.call(zoom);
    zoomBehaviorRef.current = zoom;

    // Initialize D3 Force Simulation
    const simulation = d3.forceSimulation<GraphNode>(nodes)
      .force(
        "link",
        d3.forceLink<GraphNode, GraphLink>(links)
          .id((d) => d.id)
          .distance(90)
      )
      .force("charge", d3.forceManyBody().strength(-180))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide().radius(28));

    // Render Links
    const linkGroup = g.append("g").attr("class", "graph-links");
    const linkElements = linkGroup
      .selectAll<SVGLineElement, GraphLink>("line")
      .data(links)
      .join("line")
      .attr("stroke", "#CBD5E1")
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", (d) => Math.max(1.5, (d.weight || 0.5) * 3))
      .attr("stroke-dasharray", (d) => (d.type === "co_authorship" ? "4,4" : null));

    // Node Drag Behavior
    const drag = d3.drag<SVGGElement, GraphNode>()
      .on("start", (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on("drag", (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on("end", (event, d) => {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      });

    // Render Nodes
    const nodeGroup = g.append("g").attr("class", "graph-nodes");
    const nodeElements = nodeGroup
      .selectAll<SVGGElement, GraphNode>("g")
      .data(nodes)
      .join("g")
      .attr("class", "node-item cursor-grab active:cursor-grabbing")
      .call(drag);

    // Node Circles
    const circleElements = nodeElements
      .append("circle")
      .attr("r", (d) => (selectedNodeRef.current?.id === d.id ? 18 : 14))
      .attr("fill", (d, i) => getNodeColor(d, i))
      .attr("fill-opacity", 0.9)
      .attr("stroke", (d) => (selectedNodeRef.current?.id === d.id ? "#1E293B" : "#FFFFFF"))
      .attr("stroke-width", (d) => (selectedNodeRef.current?.id === d.id ? 3 : 2))
      .style("transition", "r 0.15s ease, stroke-width 0.15s ease");

    // Node Text Labels
    nodeElements
      .append("text")
      .attr("dy", 26)
      .attr("text-anchor", "middle")
      .attr("class", "text-xs font-sans fill-neutral-700 select-none pointer-events-none font-medium")
      .text((d) => (d.label.length > 20 ? `${d.label.slice(0, 18)}...` : d.label));

    // Native tooltip
    nodeElements.append("title").text((d) => d.label);

    // Link connection checker
    const isLinkConnected = (l: GraphLink, nodeId: string): boolean => {
      const sId = typeof l.source === "object" ? (l.source as GraphNode).id : l.source;
      const tId = typeof l.target === "object" ? (l.target as GraphNode).id : l.target;
      return sId === nodeId || tId === nodeId;
    };

    // Hover & Selection Highlighting Logic
    const applyHighlight = (targetNode: GraphNode | null) => {
      if (!targetNode) {
        nodeElements.style("opacity", 1);
        circleElements
          .attr("r", 14)
          .attr("stroke", "#FFFFFF")
          .attr("stroke-width", 2);

        linkElements
          .attr("stroke", "#CBD5E1")
          .attr("stroke-opacity", 0.6)
          .attr("stroke-width", (d) => Math.max(1.5, (d.weight || 0.5) * 3));
        return;
      }

      const neighborIds = new Set<string>();
      neighborIds.add(targetNode.id);

      links.forEach((l) => {
        const sId = typeof l.source === "object" ? (l.source as GraphNode).id : l.source;
        const tId = typeof l.target === "object" ? (l.target as GraphNode).id : l.target;
        if (sId === targetNode.id) neighborIds.add(tId);
        if (tId === targetNode.id) neighborIds.add(sId);
      });

      // Dim unconnected nodes to 0.25 opacity
      nodeElements.style("opacity", (d) => (neighborIds.has(d.id) ? 1 : 0.25));

      // Increase radius for focused node and neighbors
      circleElements
        .attr("r", (d) => (d.id === targetNode.id ? 18 : neighborIds.has(d.id) ? 15 : 14))
        .attr("stroke", (d) => (d.id === targetNode.id ? "#1E293B" : "#FFFFFF"))
        .attr("stroke-width", (d) => (d.id === targetNode.id ? 3 : 2));

      // Highlight connected links in #4F46E5 (Indigo) and dim others
      linkElements
        .attr("stroke", (l) => (isLinkConnected(l, targetNode.id) ? "#4F46E5" : "#CBD5E1"))
        .attr("stroke-opacity", (l) => (isLinkConnected(l, targetNode.id) ? 1 : 0.15))
        .attr("stroke-width", (l) => {
          const base = Math.max(1.5, (l.weight || 0.5) * 3);
          return isLinkConnected(l, targetNode.id) ? base + 1.5 : base;
        });
    };

    highlightFnRef.current = applyHighlight;

    // Apply initial highlight if selected node exists
    if (selectedNodeRef.current) {
      applyHighlight(selectedNodeRef.current);
    }

    // Interactive event handlers
    nodeElements
      .on("mouseenter", (_event, d) => {
        applyHighlight(d);
      })
      .on("mouseleave", () => {
        applyHighlight(selectedNodeRef.current);
      })
      .on("click", (event, d) => {
        if (event.defaultPrevented) return;
        setSelectedNode(d);
        selectedNodeRef.current = d;
        applyHighlight(d);
      });

    // Background Canvas Click: deselect and reset highlight
    svg.on("click", (event) => {
      if (event.target === svg.node()) {
        setSelectedNode(null);
        selectedNodeRef.current = null;
        applyHighlight(null);
      }
    });

    // Force simulation tick updates
    simulation.on("tick", () => {
      linkElements
        .attr("x1", (d) => (d.source as GraphNode).x ?? 0)
        .attr("y1", (d) => (d.source as GraphNode).y ?? 0)
        .attr("x2", (d) => (d.target as GraphNode).x ?? 0)
        .attr("y2", (d) => (d.target as GraphNode).y ?? 0);

      nodeElements.attr(
        "transform",
        (d) => `translate(${d.x ?? 0}, ${d.y ?? 0})`
      );
    });

    return () => {
      simulation.stop();
      svg.selectAll("*").remove();
      highlightFnRef.current = null;
    };
  }, [data]);

  // Smooth Zoom button handlers
  const handleZoomIn = () => {
    if (svgRef.current && zoomBehaviorRef.current) {
      d3.select(svgRef.current)
        .transition()
        .duration(250)
        .call(zoomBehaviorRef.current.scaleBy, 1.25);
    }
  };

  const handleZoomOut = () => {
    if (svgRef.current && zoomBehaviorRef.current) {
      d3.select(svgRef.current)
        .transition()
        .duration(250)
        .call(zoomBehaviorRef.current.scaleBy, 0.8);
    }
  };

  const handleResetZoom = () => {
    if (svgRef.current && zoomBehaviorRef.current) {
      d3.select(svgRef.current)
        .transition()
        .duration(250)
        .call(zoomBehaviorRef.current.transform, d3.zoomIdentity);
    }
  };

  return (
    <div
      ref={containerRef}
      className="relative w-full bg-white rounded-2xl border border-neutral-200/90 shadow-xs overflow-hidden flex flex-col"
      style={{ minHeight: "580px" }}
    >
      {/* Header Bar */}
      <div className="px-6 py-4 border-b border-neutral-100 flex flex-wrap items-center justify-between gap-3 bg-neutral-50/50">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-[var(--tint-lavender)] flex items-center justify-center text-[var(--lavender-dark)]">
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
            <Loader2 className="w-6 h-6 animate-spin text-[var(--lavender-dark)]" />
            <span className="text-xs font-medium">Constructing knowledge graph...</span>
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center gap-2 text-[var(--status-error-text)] p-6 text-center max-w-md">
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
              preserveAspectRatio="xMidYMid meet"
            />

            {/* Selected Node Inspector Sidebar Card */}
            {selectedNode && (
              <div className="absolute top-4 right-4 w-72 bg-white/95 backdrop-blur-sm rounded-xl border border-neutral-200/90 shadow-lg p-4 space-y-3 text-xs animate-in fade-in">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-1.5 text-neutral-500 font-medium">
                    <FileText className="w-3.5 h-3.5 text-[var(--lavender-dark)]" />
                    <span>Selected Paper</span>
                  </div>
                  <div className="flex items-center gap-1">
                    {selectedNode.relevance_score !== null &&
                      selectedNode.relevance_score !== undefined && (
                        <span className="px-2 py-0.5 rounded-full bg-[var(--tint-mint)] text-[var(--color-success-dark)] border border-[var(--color-success-border)] font-semibold text-xs">
                          {Math.round(selectedNode.relevance_score * 100)}% Match
                        </span>
                      )}
                    <button
                      type="button"
                      onClick={() => setSelectedNode(null)}
                      className="p-0.5 hover:bg-neutral-100 rounded text-neutral-400 hover:text-neutral-600 transition-colors"
                      title="Close Inspector"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
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

                {typeof selectedNode.citation_count === "number" && (
                  <div className="flex items-center gap-1.5 text-neutral-600">
                    <Bookmark className="w-3.5 h-3.5 shrink-0 text-neutral-400" />
                    <span>{selectedNode.citation_count} Citations</span>
                  </div>
                )}

                {selectedNode.cluster && (
                  <div className="pt-1">
                    <span className="inline-block px-2 py-0.5 rounded bg-[var(--tint-lavender)] text-[var(--lavender-dark)] text-xs font-medium">
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
                      className="inline-flex items-center gap-1 text-[var(--lavender-dark)] hover:opacity-80 font-medium transition-opacity"
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
                <span className="font-semibold text-neutral-500 uppercase tracking-wider text-xs">
                  Thematic Clusters:
                </span>
                {uniqueClusters.map((clusterName, cIdx) => (
                  <div key={clusterName} className="flex items-center gap-1.5">
                    <span
                      className="w-2.5 h-2.5 rounded-full shrink-0"
                      style={{
                        backgroundColor:
                          CLUSTER_COLORS[cIdx % CLUSTER_COLORS.length] ?? DEFAULT_COLOR,
                      }}
                    />
                    <span
                      className="truncate max-w-[150px] font-medium text-xs"
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
