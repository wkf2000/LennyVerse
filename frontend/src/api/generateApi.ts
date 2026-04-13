import { parseSseMessageBlock } from "./searchApi";
import type {
  ExecuteRequest,
  GenerateDonePayload,
  GenerateErrorPayload,
  GenerateResultPayload,
  GenerateSseEvent,
  OutlineRequest,
  OutlineResponse,
  StepLogPayload,
} from "../types/generate";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export interface GenerateStreamHandlers {
  onStepLog?: (payload: StepLogPayload) => void;
  onResult?: (payload: GenerateResultPayload) => void;
  onError?: (payload: GenerateErrorPayload) => void;
  onDone?: (payload: GenerateDonePayload) => void;
}

export async function postInfographic(syllabus: import("../types/generate").GeneratedSyllabus): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/api/generate/infographic`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ syllabus }),
  });
  if (!response.ok) {
    throw new Error(`Infographic generation failed (${response.status})`);
  }
  const data = (await response.json()) as { html: string };
  return data.html;
}

export async function postOutline(request: OutlineRequest): Promise<OutlineResponse> {
  const response = await fetch(`${API_BASE_URL}/api/generate/outline`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`Outline generation failed (${response.status})`);
  }
  return (await response.json()) as OutlineResponse;
}

export function parseGenerateSseEvent(eventName: string, data: string): GenerateSseEvent {
  const parsed: unknown = JSON.parse(data);
  switch (eventName) {
    case "step_log":
      return { type: "step_log", payload: parsed as StepLogPayload };
    case "result":
      return { type: "result", payload: parsed as GenerateResultPayload };
    case "error":
      return { type: "error", payload: parsed as GenerateErrorPayload };
    case "done":
      return { type: "done", payload: parsed as GenerateDonePayload };
    default:
      throw new Error(`Unknown generate SSE event: ${eventName}`);
  }
}

function dispatchGenerateEvent(event: GenerateSseEvent, handlers: GenerateStreamHandlers): void {
  switch (event.type) {
    case "step_log":
      handlers.onStepLog?.(event.payload);
      break;
    case "result":
      handlers.onResult?.(event.payload);
      break;
    case "error":
      handlers.onError?.(event.payload);
      break;
    case "done":
      handlers.onDone?.(event.payload);
      break;
  }
}

function tryConsumeSseBlock(block: string, handlers: GenerateStreamHandlers): void {
  const parsedBlock = parseSseMessageBlock(block);
  if (!parsedBlock) {
    return;
  }
  const { event, data } = parsedBlock;
  if (!data.trim()) {
    return;
  }
  try {
    const parsedEvent = parseGenerateSseEvent(event, data);
    dispatchGenerateEvent(parsedEvent, handlers);
  } catch {
    // Ignore malformed frames and unknown events.
  }
}

async function consumeSseReadableStream(
  stream: ReadableStream<Uint8Array>,
  handlers: GenerateStreamHandlers
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

export async function streamExecute(
  request: ExecuteRequest,
  handlers: GenerateStreamHandlers
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/generate/execute`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Generation stream failed (${response.status})`);
  }
  if (!response.body) {
    throw new Error("Generation stream has no response body");
  }

  await consumeSseReadableStream(response.body, handlers);
}

export async function sharePlaybook(payload: GenerateResultPayload): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/api/playbooks/share`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Share failed (${response.status})`);
  }
  const data = (await response.json()) as { slug: string };
  return data.slug;
}

export async function fetchSharedPlaybook(slug: string): Promise<GenerateResultPayload> {
  const response = await fetch(`${API_BASE_URL}/api/playbooks/share/${encodeURIComponent(slug)}`);
  if (!response.ok) {
    throw new Error(response.status === 404 ? "Playbook not found" : `Failed to load playbook (${response.status})`);
  }
  return (await response.json()) as GenerateResultPayload;
}
