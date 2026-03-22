import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { GalaxyDetailDrawer } from "@/features/galaxy/GalaxyDetailDrawer";

describe("GalaxyDetailDrawer", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("loads and renders node detail when node is selected", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "doc:a",
          title: "Alpha",
          source_type: "newsletter",
          published_at: null,
          description: null,
          summary: null,
          tags: ["ai"],
          guest_names: ["Lenny"],
          related_document_ids: [],
          reader_url: "/reader/doc:a",
        }),
        { status: 200 },
      ),
    );

    render(<GalaxyDetailDrawer nodeId="doc:a" />);

    await waitFor(() => expect(screen.getByText("Alpha")).toBeInTheDocument());
    expect(screen.getByText("Open full document")).toHaveAttribute("href", "/reader/doc:a");
  });

  it("shows graceful error if detail fetch fails after retry", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(new Response("bad", { status: 500 }));

    render(<GalaxyDetailDrawer nodeId="doc:missing" />);

    await waitFor(() =>
      expect(screen.getByText("Failed to load node details. Please try again.")).toBeInTheDocument(),
    );
  });
});
