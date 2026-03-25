import { afterEach, describe, expect, it, vi } from "vitest";
import {
  buildCitationLookup,
  consumeSseText,
  parseChatSseEvent,
  parseSseMessageBlock,
  postSearch,
  streamChat,
} from "../searchApi";
import type { SearchResult } from "../../types/search";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function sampleResult(overrides: Partial<SearchResult> = {}): SearchResult {
  return {
    id: "chunk-1",
    score: 0.9,
    title: "T",
    guest: "G",
    date: "2024-01-01",
    tags: [],
    excerpt: "e",
    content_id: "c1",
    chunk_index: 0,
    ...overrides,
  };
}

describe("buildCitationLookup", () => {
  it("returns an empty map for no results", () => {
    expect(buildCitationLookup([]).size).toBe(0);
  });

  it("maps result id to SearchResult", () => {
    const a = sampleResult({ id: "a" });
    const b = sampleResult({ id: "b", title: "Other" });
    const map = buildCitationLookup([a, b]);
    expect(map.get("a")).toBe(a);
    expect(map.get("b")?.title).toBe("Other");
  });

  it("uses the last result when ids collide", () => {
    const first = sampleResult({ id: "dup", title: "first" });
    const second = sampleResult({ id: "dup", title: "second" });
    const map = buildCitationLookup([first, second]);
    expect(map.get("dup")?.title).toBe("second");
  });
});

describe("parseSseMessageBlock", () => {
  it("parses event and data lines", () => {
    const block = ["event: answer_delta", 'data: {"text_delta":"hi"}'].join("\n");
    expect(parseSseMessageBlock(block)).toEqual({
      event: "answer_delta",
      data: '{"text_delta":"hi"}',
    });
  });

  it("joins multiple data lines with newlines (SSE multi-line data fields)", () => {
    const block = ["event: ping", "data: hello", "data: world"].join("\n");
    const parsed = parseSseMessageBlock(block);
    expect(parsed?.event).toBe("ping");
    expect(parsed?.data).toBe("hello\nworld");
  });

  it("returns null when there is no data field", () => {
    expect(parseSseMessageBlock("event: ping")).toBeNull();
  });
});

describe("parseChatSseEvent", () => {
  it("parses answer_delta", () => {
    expect(parseChatSseEvent("answer_delta", '{"text_delta":"x"}')).toEqual({
      type: "answer_delta",
      payload: { text_delta: "x" },
    });
  });

  it("parses citation_used with source_ref span metadata", () => {
    const json = JSON.stringify({
      source_ref: { id: "chunk-1", span: { start: 0, end: 12 } },
    });
    expect(parseChatSseEvent("citation_used", json)).toEqual({
      type: "citation_used",
      payload: {
        source_ref: { id: "chunk-1", span: { start: 0, end: 12 } },
      },
    });
  });

  it("parses error and done", () => {
    expect(
      parseChatSseEvent("error", '{"code":"E","message":"m","retryable":true}')
    ).toEqual({
      type: "error",
      payload: { code: "E", message: "m", retryable: true },
    });
    expect(
      parseChatSseEvent(
        "done",
        JSON.stringify({
          latency_ms: 10,
          token_usage: { input_tokens: null, output_tokens: 2, total_tokens: null },
          source_count: 4,
          partial: false,
        })
      )
    ).toEqual({
      type: "done",
      payload: {
        latency_ms: 10,
        token_usage: { input_tokens: null, output_tokens: 2, total_tokens: null },
        source_count: 4,
        partial: false,
      },
    });
  });

  it("throws on unknown event names", () => {
    expect(() => parseChatSseEvent("unknown", "{}")).toThrow(/Unknown chat SSE event/);
  });
});

describe("consumeSseText", () => {
  it("dispatches handlers for a multi-event SSE payload", async () => {
    const deltas: string[] = [];
    const citations: string[] = [];
    let donePayload: unknown;

    const sse = [
      "event: answer_delta",
      'data: {"text_delta":"Hello "}',
      "",
      "event: citation_used",
      'data: {"source_ref":{"id":"s1"}}',
      "",
      "event: done",
      'data: {"latency_ms":1,"token_usage":{"input_tokens":1,"output_tokens":1,"total_tokens":2},"source_count":1,"partial":false}',
      "",
    ].join("\n");

    await consumeSseText(sse, {
      onAnswerDelta: (p) => deltas.push(p.text_delta),
      onCitationUsed: (p) => citations.push(p.source_ref.id),
      onDone: (p) => {
        donePayload = p;
      },
    });

    expect(deltas).toEqual(["Hello "]);
    expect(citations).toEqual(["s1"]);
    expect(donePayload).toMatchObject({ partial: false, source_count: 1 });
  });

  it("ignores blocks with unknown events", async () => {
    const called: string[] = [];
    await consumeSseText(
      ["event: unknown", "data: {}", "", 'event: answer_delta', 'data: {"text_delta":"x"}', ""].join(
        "\n"
      ),
      {
        onAnswerDelta: () => called.push("d"),
      }
    );
    expect(called).toEqual(["d"]);
  });
});

describe("postSearch", () => {
  it("POSTs JSON to /api/search and returns parsed body", async () => {
    const body: unknown = { query: "q", results: [] };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => body,
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await postSearch({ query: "growth", k: 5 });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url.endsWith("/api/search")).toBe(true);
    expect(init.method).toBe("POST");
    expect(init.headers).toMatchObject({ "Content-Type": "application/json" });
    expect(JSON.parse(init.body as string)).toEqual({ query: "growth", k: 5 });
    expect(result).toEqual(body);
  });

  it("throws when the response is not ok", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
      })
    );
    await expect(postSearch({ query: "x" })).rejects.toThrow(/503/);
  });
});

describe("streamChat", () => {
  it("reads the SSE body and invokes handlers", async () => {
    const sseChunk =
      'event: answer_delta\ndata: {"text_delta":"a"}\n\nevent: done\ndata: {"latency_ms":0,"token_usage":{"input_tokens":0,"output_tokens":0,"total_tokens":0},"source_count":0,"partial":false}\n\n';

    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(sseChunk.slice(0, 20)));
        controller.enqueue(new TextEncoder().encode(sseChunk.slice(20)));
        controller.close();
      },
    });

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        body: stream,
      })
    );

    const text: string[] = [];
    await streamChat({ query: "q" }, {
      onAnswerDelta: (p) => text.push(p.text_delta),
      onDone: () => {},
    });

    expect(text).toEqual(["a"]);
  });

  it("throws when the response is not ok", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
      })
    );
    await expect(streamChat({ query: "x" }, {})).rejects.toThrow(/400/);
  });

  it("throws when there is no body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        body: null,
      })
    );
    await expect(streamChat({ query: "x" }, {})).rejects.toThrow(/no response body/);
  });
});
