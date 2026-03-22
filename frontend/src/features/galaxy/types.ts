export type EdgeTier = "high" | "medium" | "low";

export interface Position3D {
  x: number;
  y: number;
  z: number;
}

export interface GalaxyNode {
  id: string;
  title: string;
  source_type: "newsletter" | "podcast" | "unknown";
  published_at: string | null;
  tags: string[];
  guest_names: string[];
  cluster_id: string;
  position: Position3D;
  influence_score: number;
  star_size: number;
  star_brightness: number;
}

export interface GalaxyEdge {
  source: string;
  target: string;
  weight: number;
  edge_tier: EdgeTier;
}

export interface GalaxyCluster {
  id: string;
  label: string;
  centroid: Position3D;
  node_count: number;
  dominant_tags: string[];
}

export interface FilterFacets {
  tags: string[];
  guests: string[];
  date_min: string | null;
  date_max: string | null;
  source_types: string[];
}

export interface GalaxySnapshot {
  version: string;
  generated_at: string;
  schema_version: number;
  compatibility: {
    minimum_client_schema: number;
    current_schema: number;
  };
  bounds: {
    x: [number, number];
    y: [number, number];
    z: [number, number];
  };
  nodes: GalaxyNode[];
  edges: GalaxyEdge[];
  clusters: GalaxyCluster[];
  filter_facets: FilterFacets;
}

export interface GalaxyFilters {
  tags: Set<string>;
  guests: Set<string>;
  sourceTypes: Set<string>;
}

export interface GalaxyNodeDetail {
  id: string;
  title: string;
  source_type: "newsletter" | "podcast" | "unknown";
  published_at: string | null;
  description: string | null;
  summary: string | null;
  tags: string[];
  guest_names: string[];
  related_document_ids: string[];
  reader_url: string;
}
