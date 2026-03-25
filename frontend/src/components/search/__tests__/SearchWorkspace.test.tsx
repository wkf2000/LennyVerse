import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { SearchResult } from "../../../types/search";
import SearchWorkspace from "../SearchWorkspace";

const postSearch = vi.fn();
const streamChat = vi.fn();

vi.mock("../../../api/searchApi", () => ({
  postSearch: (...args: unknown[]) => postSearch(...args),
  streamChat: (...args: unknown[]) => streamChat(...args),
  buildCitationLookup: vi.fn(),
  consumeSseReadableStream: vi.fn(),
  consumeSseText: vi.fn(),
  parseChatSseEvent: vi.fn(),
  parseSseMessageBlock: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function sampleResult(overrides: Partial<SearchResult> = {}): SearchResult {
  return {
    id: "chunk-1",
    score: 0.91,
    title: "Source Alpha",
    guest: "Guest One",
    date: "2024-06-01",
    tags: ["growth"],
    excerpt: "This is the excerpt body used for list and detail panels.",
    content_id: "content-1",
    chunk_index: 0,
    ...overrides,
  };
}

describe("SearchWorkspace", () => {
  it("shows loading copy while search request is in flight", async () => {
    let releaseSearch: (() => void) | undefined;
    const searchGate = new Promise<void>((resolve) => {
      releaseSearch = resolve;
    });

    postSearch.mockImplementation(async () => {
      await searchGate;
      return { query: "growth", results: [sampleResult()] };
    });
    streamChat.mockImplementation(async (_request, handlers) => {
      handlers.onDone?.({
        latency_ms: 0,
        token_usage: { input_tokens: null, output_tokens: null, total_tokens: null },
        source_count: 1,
        partial: false,
      });
    });

    render(<SearchWorkspace />);
    fireEvent.change(screen.getByLabelText("Search query"), { target: { value: "growth" } });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));

    expect(screen.getByText("Searching Lenny's archive...")).toBeInTheDocument();

    releaseSearch?.();
    await waitFor(() => {
      expect(screen.queryByText("Searching Lenny's archive...")).not.toBeInTheDocument();
    });
  });

  it("shows prelude while stream is active before first answer delta", async () => {
    postSearch.mockResolvedValue({ query: "growth", results: [sampleResult()] });

    let releaseStream: (() => void) | undefined;
    const streamGate = new Promise<void>((resolve) => {
      releaseStream = resolve;
    });

    streamChat.mockImplementation(async (_request, handlers) => {
      await streamGate;
      handlers.onDone?.({
        latency_ms: 0,
        token_usage: { input_tokens: null, output_tokens: null, total_tokens: null },
        source_count: 1,
        partial: false,
      });
    });

    render(<SearchWorkspace />);
    fireEvent.change(screen.getByLabelText("Search query"), { target: { value: "growth" } });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => {
      expect(screen.getByText("Thinking with sources...")).toBeInTheDocument();
    });

    releaseStream?.();
    await waitFor(() => {
      expect(screen.queryByText("Thinking with sources...")).not.toBeInTheDocument();
    });
  });

  it("renders sources while the chat stream is still active", async () => {
    postSearch.mockResolvedValue({ query: "growth", results: [sampleResult()] });

    let releaseStream: (() => void) | undefined;
    const streamGate = new Promise<void>((resolve) => {
      releaseStream = resolve;
    });

    streamChat.mockImplementation(async (_request, handlers) => {
      handlers.onAnswerDelta?.({ text_delta: "Partial " });
      await streamGate;
      handlers.onDone?.({
        latency_ms: 1,
        token_usage: { input_tokens: null, output_tokens: null, total_tokens: null },
        source_count: 1,
        partial: false,
      });
    });

    render(<SearchWorkspace />);

    fireEvent.change(screen.getByLabelText("Search query"), { target: { value: "growth" } });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => {
      expect(screen.getByText("Source Alpha")).toBeInTheDocument();
    });
    expect(screen.getByTestId("answer-stream-text")).toHaveTextContent(/Partial/);

    releaseStream?.();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Search" })).not.toBeDisabled();
    });
    expect(streamChat).toHaveBeenCalledTimes(1);
  });

  it("opens source detail content when a source row is selected", async () => {
    const result = sampleResult({
      id: "chunk-detail",
      title: "Deep Dive Episode",
      excerpt: "Unique excerpt snippet for the detail panel.",
    });
    postSearch.mockResolvedValue({ query: "q", results: [result] });
    streamChat.mockImplementation(async (_request, handlers) => {
      handlers.onDone?.({
        latency_ms: 0,
        token_usage: { input_tokens: null, output_tokens: null, total_tokens: null },
        source_count: 1,
        partial: false,
      });
    });

    render(<SearchWorkspace />);
    fireEvent.change(screen.getByLabelText("Search query"), { target: { value: "q" } });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => {
      expect(screen.getByTestId("source-row-chunk-detail")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("source-row-chunk-detail"));

    expect(screen.getByRole("heading", { name: "Deep Dive Episode", level: 3 })).toBeInTheDocument();
    expect(screen.getByTestId("source-detail-excerpt")).toHaveTextContent(
      "Unique excerpt snippet for the detail panel.",
    );
  });

  it("shows partial-failure banner, preserves partial answer, and retries chat only when stream errors with sources", async () => {
    postSearch.mockResolvedValue({ query: "growth", results: [sampleResult({ id: "chunk-a", title: "Source A" })] });
    streamChat.mockImplementation(async (_request, handlers) => {
      handlers.onAnswerDelta?.({ text_delta: "Partial answer " });
      handlers.onError?.({ code: "stream_error", message: "Upstream failure", retryable: true });
    });

    render(<SearchWorkspace />);
    fireEvent.change(screen.getByLabelText("Search query"), { target: { value: "growth" } });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => {
      expect(screen.getByTestId("chat-partial-failure-banner")).toBeInTheDocument();
    });
    expect(screen.getByTestId("answer-stream-text")).toHaveTextContent("Partial answer");
    expect(screen.getByText("Upstream failure")).toBeInTheDocument();
    expect(screen.getByText("Source A")).toBeInTheDocument();

    streamChat.mockImplementation(async (_request, handlers) => {
      handlers.onAnswerDelta?.({ text_delta: "Recovered " });
      handlers.onDone?.({
        latency_ms: 0,
        token_usage: { input_tokens: null, output_tokens: null, total_tokens: null },
        source_count: 1,
        partial: false,
      });
    });

    fireEvent.click(screen.getByRole("button", { name: "Generate answer from these sources" }));

    await waitFor(() => {
      expect(screen.queryByTestId("chat-partial-failure-banner")).not.toBeInTheDocument();
    });
    expect(postSearch).toHaveBeenCalledTimes(1);
    expect(streamChat).toHaveBeenCalledTimes(2);
    expect(streamChat).toHaveBeenLastCalledWith(
      { query: "growth", k: 12 },
      expect.any(Object),
    );
    await waitFor(() => {
      expect(screen.getByTestId("answer-stream-text")).toHaveTextContent("Recovered");
    });
  });

  it("marks cited sources and highlights citation span in detail when row is selected", async () => {
    const excerpt = "Start of excerpt. CITED_PART middle. End.";
    const result = sampleResult({
      id: "chunk-cite",
      title: "Cited Episode",
      excerpt,
    });
    postSearch.mockResolvedValue({ query: "q", results: [result] });
    streamChat.mockImplementation(async (_request, handlers) => {
      handlers.onCitationUsed?.({
        source_ref: {
          id: "chunk-cite",
          span: { start: excerpt.indexOf("CITED_PART"), end: excerpt.indexOf("CITED_PART") + "CITED_PART".length },
        },
      });
      handlers.onDone?.({
        latency_ms: 0,
        token_usage: { input_tokens: null, output_tokens: null, total_tokens: null },
        source_count: 1,
        partial: false,
      });
    });

    render(<SearchWorkspace />);
    fireEvent.change(screen.getByLabelText("Search query"), { target: { value: "q" } });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => {
      expect(screen.getByText("Cited")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("source-row-chunk-cite"));

    expect(screen.getByTestId("citation-marker")).toHaveTextContent("CITED_PART");
  });

  it("shows insufficient-evidence suggestions when the stream completes with zero sources", async () => {
    postSearch.mockResolvedValue({ query: "q", results: [] });
    streamChat.mockImplementation(async (_request, handlers) => {
      handlers.onDone?.({
        latency_ms: 0,
        token_usage: { input_tokens: null, output_tokens: null, total_tokens: null },
        source_count: 0,
        partial: false,
      });
    });

    render(<SearchWorkspace />);
    fireEvent.change(screen.getByLabelText("Search query"), { target: { value: "q" } });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => {
      expect(
        screen.getByText("Not enough evidence in the archive for a grounded answer."),
      ).toBeInTheDocument();
    });
    const suggestionButton = screen.getByRole("button", { name: /B2B SaaS growth/ });
    expect(suggestionButton).toBeInTheDocument();

    fireEvent.click(suggestionButton);

    await waitFor(() => {
      expect(postSearch).toHaveBeenCalledTimes(2);
    });
    expect(postSearch).toHaveBeenNthCalledWith(2, {
      query: "B2B SaaS growth and go-to-market strategy",
      k: 12,
    });
  });
});
