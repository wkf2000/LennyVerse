import { useEffect, useMemo, useRef, useState } from "react";
import * as d3 from "d3";

import type { GraphEdge, GraphNode } from "../types/graph";

type ForceNode = GraphNode & d3.SimulationNodeDatum;
type ForceLink = GraphEdge & d3.SimulationLinkDatum<ForceNode>;

interface GraphCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedNodeId?: string;
  searchTerm: string;
  onNodeSelect: (nodeId: string) => void;
}

const NODE_COLORS: Record<GraphNode["type"], string> = {
  guest: "#f59e0b",
  topic: "#fb7185",
  content: "#fcd34d",
  concept: "#c4b5fd",
};

export default function GraphCanvas({
  nodes,
  edges,
  selectedNodeId,
  searchTerm,
  onNodeSelect,
}: GraphCanvasProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [size, setSize] = useState({ width: 1000, height: 700 });

  const normalizedSearch = searchTerm.trim().toLowerCase();
  const matchedNodeIds = useMemo(() => {
    if (!normalizedSearch) {
      return new Set<string>();
    }
    return new Set(
      nodes
        .filter((node) => node.label.toLowerCase().includes(normalizedSearch))
        .map((node) => node.id),
    );
  }, [nodes, normalizedSearch]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }
    const observer = new ResizeObserver(() => {
      const bounds = container.getBoundingClientRect();
      setSize({
        width: Math.max(bounds.width, 320),
        height: Math.max(bounds.height, 320),
      });
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const svgElement = svgRef.current;
    if (!svgElement) {
      return;
    }

    const width = size.width;
    const height = size.height;
    const svg = d3.select(svgElement);
    svg.selectAll("*").remove();

    const root = svg.append("g");
    const zoom = d3.zoom<SVGSVGElement, unknown>().scaleExtent([0.3, 2.5]).on("zoom", (event) => {
      root.attr("transform", event.transform.toString());
    });
    svg.call(zoom);

    const forceNodes: ForceNode[] = nodes.map((node) => ({ ...node }));
    const forceLinks: ForceLink[] = edges.map((edge) => ({ ...edge, source: edge.sourceNodeId, target: edge.targetNodeId }));
    const linkedByNode = new Map<string, Set<string>>();

    const ensureLinkedSet = (nodeId: string): Set<string> => {
      let linked = linkedByNode.get(nodeId);
      if (!linked) {
        linked = new Set<string>([nodeId]);
        linkedByNode.set(nodeId, linked);
      }
      return linked;
    };

    for (const edge of forceLinks) {
      ensureLinkedSet(edge.sourceNodeId).add(edge.targetNodeId);
      ensureLinkedSet(edge.targetNodeId).add(edge.sourceNodeId);
    }

    const simulation = d3
      .forceSimulation(forceNodes)
      .force(
        "link",
        d3
          .forceLink<ForceNode, ForceLink>(forceLinks)
          .id((d) => d.id)
          .distance(90)
          .strength(0.6),
      )
      .force("charge", d3.forceManyBody().strength(-130))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide<ForceNode>().radius((d) => (d.type === "content" ? 8 : 11)));

    const edgeSelection = root
      .append("g")
      .attr("stroke-linecap", "round")
      .selectAll("line")
      .data(forceLinks)
      .join("line")
      .attr("stroke", "#b59f7a")
      .attr("stroke-opacity", 0.35)
      .attr("stroke-width", (d) => Math.max(1, Math.min(d.weight, 4)));

    const nodeSelection = root
      .append("g")
      .selectAll("circle")
      .data(forceNodes)
      .join("circle")
      .attr("r", (d) => (d.type === "content" ? 7 : 10))
      .attr("fill", (d) => NODE_COLORS[d.type] ?? "#e8e8e8")
      .attr("stroke", "#0a0f1a")
      .attr("stroke-width", 1.5)
      .style("cursor", "pointer")
      .on("click", (_event, d) => onNodeSelect(d.id))
      .on("mouseover", (_event, d) => applyVisualState(d.id))
      .on("mouseout", () => applyVisualState(selectedNodeId));

    nodeSelection.append("title").text((d) => `${d.label} (${d.type})`);

    const labelSelection = root
      .append("g")
      .selectAll("text")
      .data(forceNodes)
      .join("text")
      .text((d) => d.label)
      .attr("font-size", 11)
      .attr("fill", "#e8e8e8")
      .attr("text-anchor", "middle")
      .attr("dy", -13)
      .style("pointer-events", "none");

    const dragBehavior = d3
      .drag<SVGCircleElement, ForceNode>()
      .on("start", (event, d) => {
        if (!event.active) {
          simulation.alphaTarget(0.3).restart();
        }
        d.fx = d.x;
        d.fy = d.y;
      })
      .on("drag", (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on("end", (event, d) => {
        if (!event.active) {
          simulation.alphaTarget(0);
        }
        d.fx = null;
        d.fy = null;
      });
    nodeSelection.call(dragBehavior);

    simulation.on("tick", () => {
      edgeSelection
        .attr("x1", (d) => (d.source as ForceNode).x ?? 0)
        .attr("y1", (d) => (d.source as ForceNode).y ?? 0)
        .attr("x2", (d) => (d.target as ForceNode).x ?? 0)
        .attr("y2", (d) => (d.target as ForceNode).y ?? 0);

      nodeSelection.attr("cx", (d) => d.x ?? 0).attr("cy", (d) => d.y ?? 0);
      labelSelection.attr("x", (d) => d.x ?? 0).attr("y", (d) => d.y ?? 0);
    });

    applyVisualState(selectedNodeId);

    function applyVisualState(activeNodeId?: string): void {
      const hasSearch = normalizedSearch.length > 0;
      const activeLinked = activeNodeId ? linkedByNode.get(activeNodeId) ?? new Set<string>() : undefined;

      nodeSelection
        .attr("opacity", (node) => {
          if (hasSearch && !matchedNodeIds.has(node.id)) {
            return 0.2;
          }
          if (!activeNodeId) {
            return 1;
          }
          return activeLinked?.has(node.id) ? 1 : 0.25;
        })
        .attr("stroke-width", (node) => (node.id === activeNodeId ? 3 : 1.5));

      edgeSelection.attr("stroke-opacity", (edge) => {
        const sourceNode = edge.source as ForceNode;
        const targetNode = edge.target as ForceNode;
        const searchMatch =
          !hasSearch || matchedNodeIds.has(sourceNode.id) || matchedNodeIds.has(targetNode.id);
        if (!searchMatch) {
          return 0.06;
        }
        if (!activeNodeId) {
          return 0.35;
        }
        return sourceNode.id === activeNodeId || targetNode.id === activeNodeId ? 0.9 : 0.12;
      });

      labelSelection.attr("opacity", (node) => {
        if (hasSearch && matchedNodeIds.has(node.id)) {
          return 1;
        }
        if (!activeNodeId) {
          return hasSearch ? 0.35 : 0.7;
        }
        return activeLinked?.has(node.id) ? 1 : 0.2;
      });
    }

    return () => {
      simulation.stop();
    };
  }, [nodes, edges, matchedNodeIds, onNodeSelect, normalizedSearch, selectedNodeId, size.height, size.width]);

  return (
    <div ref={containerRef} className="h-full w-full rounded-xl border border-slate-700/70 bg-[#0a0f1a]">
      <svg ref={svgRef} className="h-full w-full" />
    </div>
  );
}
