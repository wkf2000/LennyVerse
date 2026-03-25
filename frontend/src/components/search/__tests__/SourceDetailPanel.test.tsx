import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { SearchResult } from "../../../types/search";
import SourceDetailPanel from "../SourceDetailPanel";

function sampleResult(overrides: Partial<SearchResult> = {}): SearchResult {
  return {
    id: "chunk-1",
    score: 0.88,
    title: "Highlighted Citation Demo",
    guest: null,
    date: null,
    tags: [],
    excerpt: "0123456789abcdefghij",
    content_id: "c1",
    chunk_index: 2,
    ...overrides,
  };
}

describe("SourceDetailPanel", () => {
  it("renders empty state when no source is selected", () => {
    render(<SourceDetailPanel result={null} />);
    expect(screen.getByText(/Select a source row/)).toBeInTheDocument();
  });

  it("renders a highlighted citation span inside the excerpt", () => {
    const result = sampleResult();
    render(<SourceDetailPanel result={result} highlightSpan={{ start: 10, end: 15 }} />);

    expect(screen.getByTestId("source-detail-excerpt")).toBeInTheDocument();
    const marker = screen.getByTestId("citation-marker");
    expect(marker).toHaveTextContent("abcde");
    expect(screen.getByTestId("source-detail-excerpt").textContent).toContain("0123456789");
    expect(screen.getByTestId("source-detail-excerpt").textContent).toContain("fghij");
  });
});
