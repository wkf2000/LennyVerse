import type { GraphFilters, GraphResponse, NodeDetail } from "../types/graph";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function fetchGraph(filters: GraphFilters): Promise<GraphResponse> {
  const query = new URLSearchParams();

  for (const nodeType of filters.nodeTypes) {
    query.append("nodeType", nodeType);
  }
  if (filters.topic) {
    query.set("topic", filters.topic);
  }
  if (filters.startDate) {
    query.set("start_date", filters.startDate);
  }
  if (filters.endDate) {
    query.set("end_date", filters.endDate);
  }

  const response = await fetch(`${API_BASE_URL}/api/graph?${query.toString()}`);
  if (!response.ok) {
    throw new Error(`Failed to load graph data (${response.status})`);
  }
  return (await response.json()) as GraphResponse;
}

export async function fetchNodeDetail(nodeId: string): Promise<NodeDetail> {
  const response = await fetch(`${API_BASE_URL}/api/graph/nodes/${encodeURIComponent(nodeId)}`);
  if (!response.ok) {
    throw new Error(`Failed to load node detail (${response.status})`);
  }
  return (await response.json()) as NodeDetail;
}
