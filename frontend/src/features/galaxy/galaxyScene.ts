import type { GalaxyEdge, GalaxyFilters, GalaxyNode, GalaxySnapshot } from "@/features/galaxy/types";

export interface GalaxySceneData {
  nodes: GalaxyNode[];
  edges: GalaxyEdge[];
  nodeById: Map<string, GalaxyNode>;
}

export function defaultGalaxyFilters(): GalaxyFilters {
  return {
    tags: new Set<string>(),
    guests: new Set<string>(),
    sourceTypes: new Set<string>(),
  };
}

export function buildGalaxyScene(snapshot: GalaxySnapshot, filters: GalaxyFilters): GalaxySceneData {
  const filteredNodes = snapshot.nodes.filter((node) => matchesFilters(node, filters));
  const visibleNodeIds = new Set(filteredNodes.map((node) => node.id));
  const filteredEdges = (snapshot.edges ?? []).filter(
    (edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target),
  );
  return {
    nodes: filteredNodes,
    edges: filteredEdges,
    nodeById: new Map(filteredNodes.map((node) => [node.id, node])),
  };
}

function matchesFilters(node: GalaxyNode, filters: GalaxyFilters): boolean {
  if (filters.tags.size > 0 && !node.tags.some((tag) => filters.tags.has(tag))) {
    return false;
  }
  if (filters.guests.size > 0 && !node.guest_names.some((guest) => filters.guests.has(guest))) {
    return false;
  }
  if (filters.sourceTypes.size > 0 && !filters.sourceTypes.has(node.source_type)) {
    return false;
  }
  return true;
}
