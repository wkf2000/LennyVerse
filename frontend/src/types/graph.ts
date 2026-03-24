export type NodeType = "guest" | "topic" | "content" | "concept";

export interface GraphNode {
  id: string;
  type: NodeType;
  label: string;
  metadata: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  sourceNodeId: string;
  targetNodeId: string;
  relationshipType: string;
  weight: number;
  metadata: Record<string, unknown>;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface RelatedContent {
  id: string;
  title: string;
  content_type: string;
  published_at: string | null;
  guest: string | null;
  tags: string[];
  filename: string;
}

export interface NodeDetail {
  node: GraphNode;
  connected_node_count: number;
  related_content: RelatedContent[];
}

export interface GraphFilters {
  nodeTypes: NodeType[];
  topic?: string;
  startDate?: string;
  endDate?: string;
}
