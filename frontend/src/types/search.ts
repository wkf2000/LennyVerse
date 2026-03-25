/** Filters shared by search and chat requests (backend JSON shape). */
export interface SearchFilters {
  tags?: string[];
  date_from?: string;
  date_to?: string;
  type?: "podcast" | "newsletter";
}

export interface SearchRequest {
  query: string;
  k?: number;
  filters?: SearchFilters;
}

export interface SearchResult {
  id: string;
  score: number;
  title: string;
  guest: string | null;
  date: string | null;
  tags: string[];
  excerpt: string;
  content_id: string;
  chunk_index: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  query: string;
  k?: number;
  filters?: SearchFilters;
  history?: ChatMessage[];
}

/** SSE `answer_delta` data payload. */
export interface AnswerDeltaPayload {
  text_delta: string;
}

export interface SourceRef {
  id: string;
  span?: {
    start: number;
    end: number;
  } | null;
}

/** SSE `citation_used` data payload. */
export interface CitationUsedPayload {
  source_ref: SourceRef;
}

/** SSE `error` data payload. */
export interface ChatErrorPayload {
  code: string;
  message: string;
  retryable: boolean;
}

export interface TokenUsage {
  input_tokens: number | null;
  output_tokens: number | null;
  total_tokens: number | null;
}

/** SSE `done` data payload. */
export interface ChatDonePayload {
  latency_ms: number;
  token_usage: TokenUsage;
  source_count: number;
  partial: boolean;
}

export type ChatSseEvent =
  | { type: "answer_delta"; payload: AnswerDeltaPayload }
  | { type: "citation_used"; payload: CitationUsedPayload }
  | { type: "error"; payload: ChatErrorPayload }
  | { type: "done"; payload: ChatDonePayload };
