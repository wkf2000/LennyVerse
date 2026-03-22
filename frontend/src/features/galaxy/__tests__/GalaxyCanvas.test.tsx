import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { GalaxyCanvas } from "@/features/galaxy/GalaxyCanvas";
import { defaultGalaxyFilters } from "@/features/galaxy/galaxyScene";
import type { GalaxySnapshot } from "@/features/galaxy/types";

vi.mock("@react-three/fiber", () => ({
  Canvas: (_props: { children: ReactNode }) => <div data-testid="mock-canvas" />,
}));

vi.mock("@react-three/drei", () => ({
  OrbitControls: () => <div data-testid="mock-orbit-controls" />,
  Stars: () => null,
}));

const SNAPSHOT: GalaxySnapshot = {
  version: "snapshot-test",
  generated_at: "2026-03-21T00:00:00+00:00",
  schema_version: 1,
  compatibility: {
    minimum_client_schema: 1,
    current_schema: 1,
  },
  bounds: {
    x: [-1, 1],
    y: [-1, 1],
    z: [-1, 1],
  },
  nodes: [
    {
      id: "doc:a",
      title: "A",
      source_type: "newsletter",
      published_at: "2026-03-21T00:00:00+00:00",
      tags: ["ai"],
      guest_names: ["Lenny"],
      cluster_id: "cluster:tag:ai",
      position: { x: 0, y: 0, z: 0 },
      influence_score: 0.5,
      star_size: 1.6,
      star_brightness: 0.7,
    },
    {
      id: "doc:b",
      title: "B",
      source_type: "podcast",
      published_at: "2026-03-22T00:00:00+00:00",
      tags: ["product"],
      guest_names: ["Jane"],
      cluster_id: "cluster:tag:product",
      position: { x: 0.5, y: 0.3, z: -0.2 },
      influence_score: 0.3,
      star_size: 1.2,
      star_brightness: 0.55,
    },
  ],
  edges: [
    {
      source: "doc:a",
      target: "doc:b",
      weight: 1.2,
      edge_tier: "low",
    },
  ],
  clusters: [],
  filter_facets: {
    tags: ["ai", "product"],
    guests: ["Lenny", "Jane"],
    date_min: "2026-03-21T00:00:00+00:00",
    date_max: "2026-03-22T00:00:00+00:00",
    source_types: ["newsletter", "podcast"],
  },
};

describe("GalaxyCanvas", () => {
  it("renders counts and canvas shell", () => {
    render(<GalaxyCanvas snapshot={SNAPSHOT} filters={defaultGalaxyFilters()} />);

    expect(screen.getByTestId("galaxy-canvas-shell")).toBeInTheDocument();
    expect(screen.getByTestId("galaxy-scene-stats")).toHaveTextContent("2 stars");
    expect(screen.getByTestId("galaxy-scene-stats")).toHaveTextContent("1 links");
    expect(screen.getByTestId("mock-canvas")).toBeInTheDocument();
  });

  it("shows empty state when no nodes are available", () => {
    render(<GalaxyCanvas snapshot={{ ...SNAPSHOT, nodes: [], edges: [] }} filters={defaultGalaxyFilters()} />);

    expect(screen.getByText("No galaxy nodes are currently available.")).toBeInTheDocument();
  });
});
