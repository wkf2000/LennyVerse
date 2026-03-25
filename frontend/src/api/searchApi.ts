import type {
  AnswerDeltaPayload,
  ChatDonePayload,
  ChatErrorPayload,
  ChatRequest,
  ChatSseEvent,
  CitationUsedPayload,
  SearchRequest,
  SearchResponse,
  SearchResult,
} from "../types/search";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export interface ChatStreamHandlers {
  onAnswerDelta?: (payload: AnswerDeltaPayload) => void;
  onCitationUsed?: (payload: CitationUsedPayload) => void;
  onError?: (payload: ChatErrorPayload) => void;
  onDone?: (payload: ChatDonePayload) => void;
}

export function buildCitationLookup(results: SearchResult[]): Map<string, SearchResult> {
  const map = new Map<string, SearchResult>();
  for (const result of results) {
    map.set(result.id, result);
  }
  return map;
}

export async function postSearch(request: SearchRequest): Promise<SearchResponse> {
  const response = await fetch(`${API_BASE_URL}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`Search failed (${response.status})`);
  }
  return (await response.json()) as SearchResponse;
}

/**
 * Parse one SSE `event` name and raw `data` line(s) into a typed chat event.
 * Exported for unit tests and callers that assemble SSE manually.
 */
export function parseChatSseEvent(eventName: string, data: string): ChatSseEvent {
  const parsed: unknown = JSON.parse(data);
  switch (eventName) {
    case "answer_delta":
      return { type: "answer_delta", payload: parsed as AnswerDeltaPayload };
    case "citation_used":
      return { type: "citation_used", payload: parsed as CitationUsedPayload };
    case "error":
      return { type: "error", payload: parsed as ChatErrorPayload };
    case "done":
      return { type: "done", payload: parsed as ChatDonePayload };
    default:
      throw new Error(`Unknown chat SSE event: ${eventName}`);
  }
}

/** Split a single SSE block (one message) into event name and joined data payload. */
export function parseSseMessageBlock(block: string): { event: string; data: string } | null {
  const lines = block.split(/\r?\n/);
  let event = "message";
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trimStart());
    }
  }

  if (dataLines.length === 0) {
    return null;
  }

  return { event, data: dataLines.join("\n") };
}

function dispatchChatSseEvent(event: ChatSseEvent, handlers: ChatStreamHandlers): void {
  switch (event.type) {
    case "answer_delta":
      handlers.onAnswerDelta?.(event.payload);
      break;
    case "citation_used":
      handlers.onCitationUsed?.(event.payload);
      break;
    case "error":
      handlers.onError?.(event.payload);
      break;
    case "done":
      handlers.onDone?.(event.payload);
      break;
  }
}

function tryConsumeSseBlock(block: string, handlers: ChatStreamHandlers): void {
  const parsedBlock = parseSseMessageBlock(block);
  if (!parsedBlock) {
    return;
  }
  const { event, data } = parsedBlock;
  if (!data.trim()) {
    return;
  }
  let sseEvent: ChatSseEvent;
  try {
    sseEvent = parseChatSseEvent(event, data);
  } catch {
    return;
  }
  dispatchChatSseEvent(sseEvent, handlers);
}

export async function consumeSseText(
  text: string,
  handlers: ChatStreamHandlers
): Promise<void> {
  const blocks = text.split(/\r?\n\r?\n/);
  for (const block of blocks) {
    if (block.trim()) {
      tryConsumeSseBlock(block, handlers);
    }
  }
}

export async function consumeSseReadableStream(
  stream: ReadableStream<Uint8Array>,
  handlers: ChatStreamHandlers
): Promise<void> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    for (;;) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
      const parts = buffer.split(/\r?\n\r?\n/);
      buffer = parts.pop() ?? "";
      for (const block of parts) {
        if (block.trim()) {
          tryConsumeSseBlock(block, handlers);
        }
      }
      if (done) {
        if (buffer.trim()) {
          tryConsumeSseBlock(buffer, handlers);
        }
        break;
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export async function streamChat(
  request: ChatRequest,
  handlers: ChatStreamHandlers
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Chat stream failed (${response.status})`);
  }

  const body = response.body;
  if (!body) {
    throw new Error("Chat stream has no response body");
  }

  await consumeSseReadableStream(body, handlers);
}
