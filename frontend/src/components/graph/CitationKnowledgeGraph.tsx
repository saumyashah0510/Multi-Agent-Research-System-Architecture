/**
 * CitationKnowledgeGraph Component
 *
 * Implements Issue [FE-14]: Interactive D3.js Citation Knowledge Graph
 * - Interactive D3 force simulation with collision avoidance, center pull, and link tension
 * - Actual thematic cluster grouping force (cluster attraction towards spatial centroids)
 * - Dynamic responsiveness via ResizeObserver measuring container dimensions
 * - Categorical cluster color distribution (#3B82F6, #10B981, #8B5CF6, #F59E0B, #EC4899, #06B6D4)
 * - Draggable nodes with displacement tracking to prevent accidental selections while allowing clicks
 * - Interactive zoom & pan via mouse drag/scroll and UI buttons (Zoom In, Zoom Out, Reset)
 * - Click-to-inspect side card detailing paper metadata (Title, Authors, Year, Relevance, Cluster, URL)
 * - Hover & selection highlighting: highlights connected neighbors/edges in #4F46E5, dims unlinked nodes to 0.25 opacity
 * - Floating bottom-left cluster legend matching native Scholaris design system tokens
 * - Graceful empty state when no approved papers exist
 * - Memory-leak free lifecycle management with proper simulation, zoom, event, and observer cleanup
 */

import React, { useEffect, useState, useRef, useMemo, useCallback } from "react";
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

// Categorical palette for thematic clusters (FE-14 mandatory specification)
export const CLUSTER_COLORS = [
  "#3B82F6", // Blue
  "#10B981", // Emerald
  "#8B5CF6", // Purple
  "#F59E0B", // Amber
  "#EC4899", // Pink
  "#06B6D4", // Cyan
];

// Neutral grey color for isolated nodes (zero valid connections)
export const ISOLATED_NODE_COLOR = "#94A3B8";

const DEFAULT_COLOR = "#3B82F6";

/**
 * Calculates spatial centroid target coordinates for a node's thematic cluster.
 * Distributes unique clusters circularly around the canvas center to create natural,
 * visually distinguishable spatial groupings while avoiding overlap.
 */
function getClusterTarget(
  node: GraphNode,
  width: number,
  height: number,
  clusters: string[]
): { x: number; y: number } {
  const centerX = width / 2;
  const centerY = height / 2;
  if (!node.cluster || clusters.length === 0) {
    return { x: centerX, y: centerY };
  }
  const idx = clusters.indexOf(node.cluster.trim());
  if (idx < 0) {
    return { x: centerX, y: centerY };
  }
  const radius = Math.min(width, height) * 0.28;
  const angle = (idx / clusters.length) * 2 * Math.PI - Math.PI / 2;
  return {
    x: centerX + radius * Math.cos(angle),
    y: centerY + radius * Math.sin(angle),
  };
}

export const CitationKnowledgeGraph: React.FC<CitationKnowledgeGraphProps> = ({
  reviewId,
}) => {
  const [data, setData] = useState<CitationGraphResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [dimensions, setDimensions] = useState<{ width: number; height: number }>({
    width: 800,
    height: 500,
  });

  const containerRef = useRef<HTMLDivElement>(null);
  const canvasContainerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const zoomBehaviorRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const simulationRef = useRef<d3.Simulation<GraphNode, GraphLink> | null>(null);
  const selectedNodeRef = useRef<GraphNode | null>(null);
  const highlightFnRef = useRef<((node: GraphNode | null) => void) | null>(null);
  const updateLabelsFnRef = useRef<((selected: GraphNode | null) => void) | null>(null);

  // Identify set of node IDs that have at least one valid link connection
  const connectedNodeIds = useMemo(() => {
    if (!data?.nodes || !data?.links) return new Set<string>();
    const validNodeIdSet = new Set<string>(data.nodes.map((n) => n.id));
    const connected = new Set<string>();
    for (const l of data.links) {
      const sId = typeof l.source === "object" && l.source !== null ? (l.source as GraphNode).id : String(l.source);
      const tId = typeof l.target === "object" && l.target !== null ? (l.target as GraphNode).id : String(l.target);
      if (validNodeIdSet.has(sId) && validNodeIdSet.has(tId)) {
        connected.add(sId);
        connected.add(tId);
      }
    }
    return connected;
  }, [data]);

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

  const getNodeColor = useCallback(
    (node: GraphNode, fallbackIndex: number = 0): string => {
      // Isolated nodes (zero valid connections) receive neutral grey color
      if (!connectedNodeIds.has(node.id)) {
        return ISOLATED_NODE_COLOR;
      }
      if (node.cluster && node.cluster.trim()) {
        const scaled = clusterColorScale(node.cluster.trim());
        if (scaled) return scaled;
      }
      const fallback = CLUSTER_COLORS[fallbackIndex % CLUSTER_COLORS.length];
      return fallback ?? DEFAULT_COLOR;
    },
    [connectedNodeIds, clusterColorScale]
  );

  // Responsive container observer measuring dynamic width and height
  useEffect(() => {
    const container = canvasContainerRef.current;
    if (!container) return;

    const measure = () => {
      const rect = container.getBoundingClientRect();
      const w = Math.round(rect.width);
      const h = Math.round(rect.height);
      if (w > 0 && h > 0) {
        setDimensions((prev) => {
          if (Math.abs(prev.width - w) > 2 || Math.abs(prev.height - h) > 2) {
            return { width: w, height: Math.max(h, 480) };
          }
          return prev;
        });
      }
    };

    measure();

    if (typeof ResizeObserver !== "undefined") {
      const observer = new ResizeObserver((entries) => {
        for (const entry of entries) {
          const { width: w, height: h } = entry.contentRect;
          if (w > 0 && h > 0) {
            setDimensions((prev) => {
              const rw = Math.round(w);
              const rh = Math.round(Math.max(h, 480));
              if (Math.abs(prev.width - rw) > 2 || Math.abs(prev.height - rh) > 2) {
                return { width: rw, height: rh };
              }
              return prev;
            });
          }
        }
      });
      observer.observe(container);
      return () => observer.disconnect();
    } else {
      window.addEventListener("resize", measure);
      return () => window.removeEventListener("resize", measure);
    }
  }, []);

  // Clear selection and restore unhighlighted graph state
  const clearSelection = useCallback(() => {
    setSelectedNode(null);
    selectedNodeRef.current = null;
    if (updateLabelsFnRef.current) {
      updateLabelsFnRef.current(null);
    }
    if (highlightFnRef.current) {
      highlightFnRef.current(null);
    }
  }, []);

  // Synchronize selectedNode ref and propagate highlighting / label visibility updates
  useEffect(() => {
    selectedNodeRef.current = selectedNode;
    if (highlightFnRef.current) {
      highlightFnRef.current(selectedNode);
    }
    if (updateLabelsFnRef.current) {
      updateLabelsFnRef.current(selectedNode);
    }
  }, [selectedNode]);

  // Fetch graph topology via fetchReviewGraph
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
          // By default, no node is selected to keep graph clean and uncluttered
          setSelectedNode(null);
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

  // Handle dynamic container resizing without destroying the active SVG or desyncing zoom
  useEffect(() => {
    if (!simulationRef.current || !svgRef.current) return;
    const { width, height } = dimensions;

    // Update SVG viewBox attribute
    d3.select(svgRef.current).attr("viewBox", `0 0 ${width} ${height}`);

    // Update force center
    simulationRef.current.force("center", d3.forceCenter(width / 2, height / 2));

    // Update thematic cluster spatial targets for new viewport center
    simulationRef.current.force(
      "clusterX",
      d3.forceX<GraphNode>((d) => getClusterTarget(d, width, height, uniqueClusters).x).strength(0.22)
    );
    simulationRef.current.force(
      "clusterY",
      d3.forceY<GraphNode>((d) => getClusterTarget(d, width, height, uniqueClusters).y).strength(0.22)
    );

    // Gently glide layout into new dimensions
    simulationRef.current.alpha(0.2).restart();
  }, [dimensions, uniqueClusters]);

  // Setup D3 Force Simulation, Zoom, Drag, and Highlighting
  useEffect(() => {
    if (!svgRef.current || !data || !data.nodes || data.nodes.length === 0) {
      return;
    }

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const { width, height } = dimensions;
    svg.attr("viewBox", `0 0 ${width} ${height}`);

    // Create cloned copies so D3 simulation mutations do not alter props or state
    const nodes: GraphNode[] = data.nodes.map((d) => ({ ...d }));
    const rawLinks: GraphLink[] = data.links ? data.links.map((d) => ({ ...d })) : [];

    // Filter out dangling links with missing endpoints to prevent D3 forceLink crashes
    const nodeMap = new Map<string, GraphNode>();
    nodes.forEach((n) => nodeMap.set(n.id, n));

    const validLinks: GraphLink[] = rawLinks.filter((l) => {
      const sId = typeof l.source === "object" ? l.source.id : String(l.source);
      const tId = typeof l.target === "object" ? l.target.id : String(l.target);
      return nodeMap.has(sId) && nodeMap.has(tId);
    });

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

    // Initialize D3 Force Simulation with actual thematic clustering and collision avoidance
    const simulation = d3.forceSimulation<GraphNode>(nodes)
      .force(
        "link",
        d3.forceLink<GraphNode, GraphLink>(validLinks)
          .id((d) => d.id)
          .distance(90)
      )
      .force("charge", d3.forceManyBody().strength(-180))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide<GraphNode>().radius(28))
      // Actual thematic cluster attraction forces
      .force(
        "clusterX",
        d3.forceX<GraphNode>((d) => getClusterTarget(d, width, height, uniqueClusters).x).strength(0.22)
      )
      .force(
        "clusterY",
        d3.forceY<GraphNode>((d) => getClusterTarget(d, width, height, uniqueClusters).y).strength(0.22)
      );

    simulationRef.current = simulation;

    // Render Links
    const linkGroup = g.append("g").attr("class", "graph-links");
    const linkElements = linkGroup
      .selectAll<SVGLineElement, GraphLink>("line")
      .data(validLinks)
      .join("line")
      .attr("stroke", "#CBD5E1")
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", (d) => Math.max(1.5, (d.weight || 0.5) * 3))
      .attr("stroke-dasharray", (d) => (d.type === "co_authorship" ? "4,4" : null));

    // Node Drag Behavior: track draggedNodeId using client-pixel displacement matching clickDistance(4)
    const getClientCoordinates = (sourceEvent: unknown): { x: number; y: number } | null => {
      if (!sourceEvent || typeof sourceEvent !== "object") return null;
      const evt = sourceEvent as {
        clientX?: number;
        clientY?: number;
        touches?: ArrayLike<{ clientX: number; clientY: number }>;
        changedTouches?: ArrayLike<{ clientX: number; clientY: number }>;
      };
      if (evt.touches && evt.touches.length > 0 && evt.touches[0]) {
        return { x: evt.touches[0].clientX, y: evt.touches[0].clientY };
      }
      if (evt.changedTouches && evt.changedTouches.length > 0 && evt.changedTouches[0]) {
        return { x: evt.changedTouches[0].clientX, y: evt.changedTouches[0].clientY };
      }
      if (typeof evt.clientX === "number" && typeof evt.clientY === "number") {
        return { x: evt.clientX, y: evt.clientY };
      }
      return null;
    };

    let dragStartClientX: number | null = null;
    let dragStartClientY: number | null = null;
    let dragStartX = 0;
    let dragStartY = 0;
    let draggedNodeId: string | null = null;
    let clearDragTimer: ReturnType<typeof setTimeout> | null = null;

    const drag = d3.drag<SVGGElement, GraphNode>()
      .clickDistance(4)
      .on("start", (event, d) => {
        const clientCoords = getClientCoordinates(event.sourceEvent);
        if (clientCoords) {
          dragStartClientX = clientCoords.x;
          dragStartClientY = clientCoords.y;
        } else {
          dragStartClientX = null;
          dragStartClientY = null;
        }
        dragStartX = event.x;
        dragStartY = event.y;
        draggedNodeId = null;
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on("drag", (event, d) => {
        const clientCoords = getClientCoordinates(event.sourceEvent);
        if (clientCoords && dragStartClientX !== null && dragStartClientY !== null) {
          if (Math.hypot(clientCoords.x - dragStartClientX, clientCoords.y - dragStartClientY) > 4) {
            draggedNodeId = d.id;
          }
        } else if (Math.hypot(event.x - dragStartX, event.y - dragStartY) > 4) {
          draggedNodeId = d.id;
        }
        d.fx = event.x;
        d.fy = event.y;
      })
      .on("end", (event, d) => {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
        dragStartClientX = null;
        dragStartClientY = null;
        // Clear draggedNodeId on next tick so immediate trailing click is caught,
        // while subsequent clicks are never blocked.
        if (draggedNodeId) {
          if (clearDragTimer) clearTimeout(clearDragTimer);
          clearDragTimer = setTimeout(() => {
            draggedNodeId = null;
          }, 0);
        }
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

    // Selected Node Title Label: hidden by default, displayed only when node is selected
    const labelElements = nodeElements
      .append("text")
      .attr("class", "node-label text-xs font-sans font-semibold select-none pointer-events-none")
      .attr("data-testid", "node-canvas-label")
      .attr("x", 24)
      .attr("y", 4)
      .attr("fill", "#0F172A")
      .attr("stroke", "#FFFFFF")
      .attr("stroke-width", 3.5)
      .attr("stroke-linejoin", "round")
      .style("paint-order", "stroke fill")
      .style("display", (d) => (selectedNodeRef.current?.id === d.id ? "inline" : "none"))
      .text((d) => d.label);

    const updateSelectedNodeUI = (selected: GraphNode | null) => {
      labelElements.style("display", (d) => (selected && d.id === selected.id ? "inline" : "none"));
    };
    updateLabelsFnRef.current = updateSelectedNodeUI;

    // Native tooltip
    nodeElements.append("title").text((d) => d.label);

    // Link connection checker
    const isLinkConnected = (l: GraphLink, nodeId: string): boolean => {
      const sId = typeof l.source === "object" ? (l.source as GraphNode).id : String(l.source);
      const tId = typeof l.target === "object" ? (l.target as GraphNode).id : String(l.target);
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

      validLinks.forEach((l) => {
        const sId = typeof l.source === "object" ? (l.source as GraphNode).id : String(l.source);
        const tId = typeof l.target === "object" ? (l.target as GraphNode).id : String(l.target);
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
      .on("click", (_event, d) => {
        // Suppress selection only if this click is the immediate trailing release of dragging THIS specific node
        if (draggedNodeId === d.id) {
          draggedNodeId = null;
          return;
        }
        draggedNodeId = null;
        setSelectedNode(d);
        selectedNodeRef.current = d;
        updateSelectedNodeUI(d);
        applyHighlight(d);
      });

    // Background Canvas Click: deselect and reset highlight
    svg.on("click", (event) => {
      if (event.target === svg.node()) {
        clearSelection();
      }
    });

    // Force simulation tick updates
    simulation.on("tick", () => {
      linkElements
        .attr("x1", (d) => {
          const s = d.source as GraphNode;
          return typeof s === "object" && typeof s.x === "number" ? s.x : 0;
        })
        .attr("y1", (d) => {
          const s = d.source as GraphNode;
          return typeof s === "object" && typeof s.y === "number" ? s.y : 0;
        })
        .attr("x2", (d) => {
          const t = d.target as GraphNode;
          return typeof t === "object" && typeof t.x === "number" ? t.x : 0;
        })
        .attr("y2", (d) => {
          const t = d.target as GraphNode;
          return typeof t === "object" && typeof t.y === "number" ? t.y : 0;
        });

      nodeElements.attr(
        "transform",
        (d) => `translate(${typeof d.x === "number" ? d.x : 0}, ${typeof d.y === "number" ? d.y : 0})`
      );
    });

    return () => {
      if (clearDragTimer) clearTimeout(clearDragTimer);
      simulation.stop();
      svg.on(".zoom", null);
      svg.on("click", null);
      svg.selectAll("*").remove();
      simulationRef.current = null;
      zoomBehaviorRef.current = null;
      highlightFnRef.current = null;
      updateLabelsFnRef.current = null;
    };
  }, [data, getNodeColor, clearSelection]);

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
      style={{
        backgroundColor: "var(--surface-card)",
        borderColor: "var(--border-default)",
        borderRadius: "var(--radius-lg)",
        boxShadow: "var(--shadow-card)",
        minHeight: "600px",
      }}
      className="relative w-full border overflow-hidden flex flex-col"
    >
      {/* Header Bar */}
      <div
        style={{
          borderBottom: "1px solid var(--border-subtle)",
          backgroundColor: "var(--surface-card)",
        }}
        className="px-5 sm:px-6 py-3.5 flex flex-wrap items-center justify-between gap-3"
      >
        <div className="flex items-center gap-2.5">
          <div
            style={{
              backgroundColor: "var(--tint-lavender)",
              color: "var(--lavender-dark)",
              borderRadius: "var(--radius-sm)",
            }}
            className="w-8 h-8 flex items-center justify-center shrink-0"
          >
            <Network className="w-4 h-4" />
          </div>
          <div>
            <h2
              style={{ color: "var(--text-primary)", fontFamily: "var(--font-sans)" }}
              className="text-sm font-semibold tracking-tight"
            >
              Citation Knowledge Graph
            </h2>
            <p
              style={{ color: "var(--text-secondary)" }}
              className="text-xs"
            >
              Interactive topology mapping thematic clusters, citations, and co-authorship
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {data && (
            <div className="flex items-center gap-2 text-xs mr-1">
              <span
                data-testid="total-papers-badge"
                style={{
                  backgroundColor: "var(--surface-page)",
                  borderColor: "var(--border-default)",
                  borderRadius: "var(--radius-pill)",
                  color: "var(--text-secondary)",
                }}
                className="inline-flex items-center gap-1 px-2.5 py-1 border font-medium text-xs"
              >
                <span className="font-semibold text-[var(--text-primary)]">{data.total_nodes}</span> Papers
              </span>
              <span
                data-testid="total-connections-badge"
                style={{
                  backgroundColor: "var(--surface-page)",
                  borderColor: "var(--border-default)",
                  borderRadius: "var(--radius-pill)",
                  color: "var(--text-secondary)",
                }}
                className="inline-flex items-center gap-1 px-2.5 py-1 border font-medium text-xs"
              >
                <span className="font-semibold text-[var(--text-primary)]">{data.total_links}</span> Connections
              </span>
            </div>
          )}

          {/* Zoom Controls */}
          <div
            style={{
              backgroundColor: "var(--surface-card)",
              borderColor: "var(--border-default)",
              borderRadius: "var(--radius-sm)",
            }}
            className="flex items-center border overflow-hidden shadow-2xs"
          >
            <button
              type="button"
              onClick={handleZoomIn}
              style={{ color: "var(--text-secondary)" }}
              className="p-1.5 hover:bg-[var(--tint-sky)]/50 hover:text-[var(--sky-dark)] transition-colors cursor-pointer"
              title="Zoom In"
              aria-label="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={handleZoomOut}
              style={{
                color: "var(--text-secondary)",
                borderLeft: "1px solid var(--border-default)",
              }}
              className="p-1.5 hover:bg-[var(--tint-sky)]/50 hover:text-[var(--sky-dark)] transition-colors cursor-pointer"
              title="Zoom Out"
              aria-label="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={handleResetZoom}
              style={{
                color: "var(--text-secondary)",
                borderLeft: "1px solid var(--border-default)",
              }}
              className="p-1.5 hover:bg-[var(--tint-sky)]/50 hover:text-[var(--sky-dark)] transition-colors cursor-pointer"
              title="Reset Zoom"
              aria-label="Reset Zoom"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Canvas Area */}
      <div
        ref={canvasContainerRef}
        style={{
          background: "radial-gradient(ellipse at center, #FFFFFF 0%, var(--surface-page) 100%)",
        }}
        className="relative flex-1 min-h-[480px] flex items-center justify-center overflow-hidden"
      >
        {isLoading && (
          <div className="flex flex-col items-center gap-2 text-[var(--text-secondary)]">
            <Loader2 className="w-6 h-6 animate-spin text-[var(--lavender-dark)]" />
            <span className="text-xs font-medium">Constructing knowledge graph...</span>
          </div>
        )}

        {error && (
          <div
            style={{
              backgroundColor: "var(--surface-card)",
              borderColor: "var(--status-error)",
              borderRadius: "var(--radius-md)",
            }}
            className="flex flex-col items-center gap-2 text-[var(--status-error-text)] p-6 text-center max-w-md border shadow-sm"
          >
            <AlertCircle className="w-6 h-6" />
            <p className="text-xs font-medium">{error}</p>
          </div>
        )}

        {!isLoading && !error && (!data || data.nodes.length === 0) && (
          <div className="flex flex-col items-center gap-2 text-[var(--text-secondary)] p-8 text-center max-w-sm">
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
              data-testid="citation-graph-canvas"
              className="w-full h-full cursor-grab active:cursor-grabbing"
              preserveAspectRatio="xMidYMid meet"
            />

            {/* Selected Node Inspector Sidebar Card */}
            {selectedNode && (
              <div
                data-testid="paper-inspector-card"
                style={{
                  backgroundColor: "rgba(255, 255, 255, 0.97)",
                  borderColor: "var(--border-default)",
                  borderRadius: "var(--radius-md)",
                  boxShadow: "var(--shadow-container)",
                }}
                className="absolute top-3 sm:top-4 right-3 sm:right-4 w-72 sm:w-80 max-w-[calc(100%-1.5rem)] backdrop-blur-sm border p-4 space-y-3 text-xs z-20 animate-in fade-in duration-200"
              >
                {/* Card Header */}
                <div className="flex items-start justify-between gap-2 pb-1 border-b border-[var(--border-subtle)]">
                  <div className="flex items-center gap-1.5">
                    <span
                      style={{
                        backgroundColor: "var(--tint-lavender)",
                        color: "var(--lavender-dark)",
                        borderRadius: "var(--radius-sm)",
                      }}
                      className="w-5 h-5 flex items-center justify-center shrink-0"
                    >
                      <FileText className="w-3 h-3" />
                    </span>
                    <span
                      style={{ color: "var(--text-secondary)" }}
                      className="font-semibold uppercase tracking-wider text-[11px]"
                    >
                      Selected Paper
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    {selectedNode.relevance_score !== null &&
                      selectedNode.relevance_score !== undefined && (
                        <span
                          style={{
                            backgroundColor: "var(--tint-mint)",
                            color: "var(--color-success-dark)",
                            borderColor: "var(--color-success-border)",
                            borderRadius: "var(--radius-pill)",
                          }}
                          className="px-2 py-0.5 border font-semibold text-[11px]"
                        >
                          {Math.round(selectedNode.relevance_score * 100)}% Match
                        </span>
                      )}
                    <button
                      type="button"
                      onClick={clearSelection}
                      style={{
                        borderRadius: "var(--radius-sm)",
                        color: "var(--text-secondary)",
                      }}
                      className="p-1 hover:bg-[var(--surface-muted)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
                      title="Close Inspector"
                      aria-label="Close Inspector"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Paper Title */}
                <h3
                  data-testid="inspector-paper-title"
                  style={{
                    color: "var(--text-primary)",
                    fontFamily: "var(--font-serif)",
                  }}
                  className="text-sm font-bold leading-snug"
                >
                  {selectedNode.label}
                </h3>

                {/* Paper Authors */}
                {selectedNode.authors && selectedNode.authors.length > 0 && (
                  <div className="flex items-center gap-2">
                    <User className="w-3.5 h-3.5 shrink-0 text-[var(--text-secondary)]" />
                    <span style={{ color: "var(--text-secondary)" }} className="truncate">
                      {selectedNode.authors.slice(0, 3).join(", ")}
                      {selectedNode.authors.length > 3 && " et al."}
                    </span>
                  </div>
                )}

                {/* Publication Year */}
                {selectedNode.year && (
                  <div className="flex items-center gap-2">
                    <Calendar className="w-3.5 h-3.5 shrink-0 text-[var(--text-secondary)]" />
                    <span style={{ color: "var(--text-secondary)" }}>
                      Published {selectedNode.year}
                    </span>
                  </div>
                )}

                {/* Citation Count */}
                {typeof selectedNode.citation_count === "number" && (
                  <div className="flex items-center gap-2">
                    <Bookmark className="w-3.5 h-3.5 shrink-0 text-[var(--text-secondary)]" />
                    <span style={{ color: "var(--text-secondary)" }}>
                      {selectedNode.citation_count.toLocaleString()} Citations
                    </span>
                  </div>
                )}

                {/* Thematic Cluster Pill */}
                {selectedNode.cluster && (
                  <div className="pt-0.5">
                    <span
                      data-testid="inspector-paper-cluster"
                      style={{
                        backgroundColor: "var(--tint-sky)",
                        color: "var(--sky-dark)",
                        borderColor: "var(--border-sky)",
                        borderRadius: "var(--radius-sm)",
                      }}
                      className="inline-block px-2.5 py-1 border text-xs font-semibold"
                    >
                      Theme: {selectedNode.cluster}
                    </span>
                  </div>
                )}

                {/* External Document Link */}
                {selectedNode.url && (
                  <div className="pt-2 border-t border-[var(--border-subtle)]">
                    <a
                      href={selectedNode.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        backgroundColor: "var(--surface-card)",
                        border: "1px solid var(--border-default)",
                        borderRadius: "var(--radius-sm)",
                        color: "var(--sky-dark)",
                      }}
                      className="inline-flex items-center justify-between w-full px-3 py-1.5 font-semibold text-xs transition-colors hover:bg-[var(--tint-sky)]/50 hover:border-[var(--sky-dark)] shadow-2xs cursor-pointer"
                    >
                      <span>Open Source Document</span>
                      <ExternalLink className="w-3.5 h-3.5 shrink-0 ml-1.5" />
                    </a>
                  </div>
                )}
              </div>
            )}

            {/* Thematic Cluster Color Legend */}
            {uniqueClusters.length > 0 && (
              <div
                style={{
                  backgroundColor: "rgba(255, 255, 255, 0.95)",
                  borderColor: "var(--border-default)",
                  borderRadius: "var(--radius-md)",
                  boxShadow: "var(--shadow-card)",
                }}
                className="absolute bottom-3 left-3 sm:left-4 max-w-[calc(100%-1.5rem)] sm:max-w-xl flex flex-wrap items-center gap-2 sm:gap-3 backdrop-blur-xs px-3 sm:px-3.5 py-2 border text-xs z-10"
              >
                <span
                  style={{ color: "var(--text-secondary)" }}
                  className="font-semibold uppercase tracking-wider text-[11px]"
                >
                  Thematic Clusters:
                </span>
                {uniqueClusters.map((clusterName, cIdx) => (
                  <div key={clusterName} className="flex items-center gap-1.5">
                    <span
                      className="w-2.5 h-2.5 rounded-full shrink-0 shadow-2xs"
                      style={{
                        backgroundColor:
                          CLUSTER_COLORS[cIdx % CLUSTER_COLORS.length] ?? DEFAULT_COLOR,
                      }}
                    />
                    <span
                      style={{ color: "var(--text-primary)" }}
                      className="truncate max-w-[130px] sm:max-w-[170px] font-medium text-xs"
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
