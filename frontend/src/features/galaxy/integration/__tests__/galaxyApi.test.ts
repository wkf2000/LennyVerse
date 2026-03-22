import { describe, expect, it, vi } from "vitest";

import { fetchGalaxyNodeDetailWithRetry, fetchGalaxySnapshot } from "@/features/galaxy/integration/galaxyApi";

describe("galaxyApi integration layer", () => {
  it("validates supported snapshot schema", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          version: "snapshot-test",
          generated_at: "2026-03-21T00:00:00+00:00",
          schema_version: 1,
          compatibility: { minimum_client_schema: 1, current_schema: 1 },
          bounds: { x: [-1, 1], y: [-1, 1], z: [-1, 1] },
          nodes: [],
          edges: [],
          clusters: [],
          filter_facets: { tags: [], guests: [], date_min: null, date_max: null, source_types: [] },
        }),
        { status: 200 },
      ),
    );

    const snapshot = await fetchGalaxySnapshot();
    expect(snapshot.schema_version).toBe(1);
  });

  it("retries node detail once before failing", async () => {
    vi.spyOn(global, "fetch")
      .mockResolvedValueOnce(new Response("bad", { status: 500 }))
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            id: "doc:alpha",
            title: "Alpha",
            source_type: "newsletter",
            published_at: null,
            description: null,
            summary: null,
            tags: [],
            guest_names: [],
            related_document_ids: [],
            reader_url: "/reader/doc:alpha",
          }),
          { status: 200 },
        ),
      );

    const detail = await fetchGalaxyNodeDetailWithRetry("doc:alpha");
    expect(detail.id).toBe("doc:alpha");
  });
});
