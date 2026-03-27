import { useCallback, useMemo, useRef, useState } from "react";

import { postSearch, streamChat, type ChatStreamHandlers } from "../../api/searchApi";
import type { SearchResult } from "../../types/search";
import AnswerStreamPanel from "./AnswerStreamPanel";
import SearchInput from "./SearchInput";
import SourceDetailPanel from "./SourceDetailPanel";
import SourcesList from "./SourcesList";

export const INSUFFICIENT_EVIDENCE_SUGGESTIONS: readonly string[] = [
  "B2B SaaS growth and go-to-market strategy",
  "Product retention and user engagement",
  "Pricing, packaging, and monetization for startups",
];

const STARTER_QUESTIONS: readonly string[] = [
  "What are the most common mistakes companies make when building AI products",
  "What are the most common paths for a new grad to break into product management?",
  "How can I use AI to help me practice and prepare for PM interviews?",
  "What is the 'Ladder versus Map' career framework?",
  "How can I empirically measure if my product has achieved product-market fit (PMF)?",
];

export interface SearchWorkspaceProps {
  postSearchFn?: typeof postSearch;
  streamChatFn?: typeof streamChat;
}

export default function SearchWorkspace({
  postSearchFn = postSearch,
  streamChatFn = streamChat,
}: SearchWorkspaceProps): JSX.Element {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [selectedId, setSelectedId] = useState<string | undefined>();
  const [citationSpans, setCitationSpans] = useState<Map<string, { start: number; end: number }>>(new Map());
  const [citedIds, setCitedIds] = useState<Set<string>>(new Set());
  const [isSearching, setIsSearching] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [answerText, setAnswerText] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | undefined>();
  const [insufficientEvidence, setInsufficientEvidence] = useState(false);
  const lastStreamQueryRef = useRef("");

  const highlightSpan = useMemo(() => {
    if (!selectedId) {
      return null;
    }
    return citationSpans.get(selectedId) ?? null;
  }, [citationSpans, selectedId]);

  const selectedResult = useMemo(
    () => results.find((result) => result.id === selectedId) ?? null,
    [results, selectedId],
  );

  const busy = isSearching || isStreaming;

  const buildChatHandlers = useCallback((): ChatStreamHandlers => {
    return {
      onAnswerDelta: (payload) => {
        setAnswerText((previous) => previous + payload.text_delta);
      },
      onCitationUsed: (payload) => {
        const sourceId = payload.source_ref.id;
        setCitedIds((previous) => new Set(previous).add(sourceId));
        const span = payload.source_ref.span;
        if (span && span.end > span.start) {
          setCitationSpans((previous) => {
            const next = new Map(previous);
            next.set(sourceId, { start: span.start, end: span.end });
            return next;
          });
        }
      },
      onError: (payload) => {
        setErrorMessage(payload.message);
      },
      onDone: (payload) => {
        if (payload.source_count === 0) {
          setInsufficientEvidence(true);
        }
      },
    };
  }, []);

  const runChatForCurrentQuery = useCallback(async (): Promise<void> => {
    const trimmed = lastStreamQueryRef.current;
    if (!trimmed) {
      return;
    }
    setIsStreaming(true);
    try {
      await streamChatFn({ query: trimmed, k: 12 }, buildChatHandlers());
    } catch (error: unknown) {
      setErrorMessage(error instanceof Error ? error.message : "Chat stream failed.");
    } finally {
      setIsStreaming(false);
    }
  }, [buildChatHandlers, streamChatFn]);

  const handleRetryAnswerFromSources = useCallback(async (): Promise<void> => {
    if (results.length === 0 || !lastStreamQueryRef.current) {
      return;
    }
    setErrorMessage(undefined);
    setInsufficientEvidence(false);
    setAnswerText("");
    setCitedIds(new Set());
    setCitationSpans(new Map());
    await runChatForCurrentQuery();
  }, [results.length, runChatForCurrentQuery]);

  const executeSearch = useCallback(
    async (rawQuery: string): Promise<void> => {
      const trimmed = rawQuery.trim();
      if (!trimmed) {
        return;
      }

      lastStreamQueryRef.current = trimmed;
      setErrorMessage(undefined);
      setInsufficientEvidence(false);
      setAnswerText("");
      setCitedIds(new Set());
      setCitationSpans(new Map());
      setSelectedId(undefined);
      setResults([]);
      setIsSearching(true);

      try {
        const searchPayload = await postSearchFn({ query: trimmed, k: 12 });
        setResults(searchPayload.results);
      } catch (error: unknown) {
        setIsSearching(false);
        setErrorMessage(error instanceof Error ? error.message : "Exploration failed.");
        return;
      }

      setIsSearching(false);
      setIsStreaming(true);

      try {
        await streamChatFn({ query: trimmed, k: 12 }, buildChatHandlers());
      } catch (error: unknown) {
        setErrorMessage(error instanceof Error ? error.message : "Chat stream failed.");
      } finally {
        setIsStreaming(false);
      }
    },
    [buildChatHandlers, postSearchFn, streamChatFn],
  );

  const handleSubmit = useCallback(() => {
    void executeSearch(query);
  }, [executeSearch, query]);

  const handleSuggestedQueryClick = useCallback(
    (suggestion: string) => {
      setQuery(suggestion);
      void executeSearch(suggestion);
    },
    [executeSearch],
  );

  return (
    <div className="flex flex-col gap-4">
      {!answerText && !isSearching && !isStreaming && results.length === 0 ? (
        <div className="flex flex-wrap gap-2">
          {STARTER_QUESTIONS.map((q) => (
            <button
              key={q}
              type="button"
              className="cursor-pointer rounded-full border border-indigo-200 bg-indigo-50/80 px-3 py-1.5 text-xs text-indigo-700 transition-all duration-200 hover:border-indigo-300 hover:bg-indigo-100 hover:shadow-sm hover:shadow-indigo-200/50 motion-safe:hover:-translate-y-0.5"
              onClick={() => handleSuggestedQueryClick(q)}
            >
              {q}
            </button>
          ))}
        </div>
      ) : null}
      <SearchInput value={query} onChange={setQuery} onSubmit={handleSubmit} disabled={busy} />

      <div className="flex flex-col gap-4 lg:max-h-[min(78vh,920px)] lg:min-h-[520px]">
        <AnswerStreamPanel
          searchLoading={isSearching}
          streamActive={isStreaming}
          answerText={answerText}
          errorMessage={errorMessage}
          sourcesAvailable={results.length > 0}
          onRetryAnswer={() => {
            void handleRetryAnswerFromSources();
          }}
          insufficientEvidence={insufficientEvidence}
          suggestedQueries={INSUFFICIENT_EVIDENCE_SUGGESTIONS}
          onSuggestedQueryClick={handleSuggestedQueryClick}
        />

        <div className="grid flex-1 grid-cols-1 gap-4 lg:min-h-0 lg:grid-cols-2">
          <SourcesList
            results={results}
            selectedId={selectedId}
            citedIds={citedIds}
            onSelect={setSelectedId}
          />
          <SourceDetailPanel result={selectedResult} highlightSpan={highlightSpan} />
        </div>
      </div>
    </div>
  );
}
