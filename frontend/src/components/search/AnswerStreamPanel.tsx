export interface AnswerStreamPanelProps {
  searchLoading: boolean;
  streamActive: boolean;
  answerText: string;
  errorMessage?: string;
  /** When chat failed but search returned sources, show partial-failure UX and retry. */
  sourcesAvailable?: boolean;
  onRetryAnswer?: () => void;
  insufficientEvidence: boolean;
  suggestedQueries: readonly string[];
  onSuggestedQueryClick: (query: string) => void;
}

export default function AnswerStreamPanel({
  searchLoading,
  streamActive,
  answerText,
  errorMessage,
  sourcesAvailable = false,
  onRetryAnswer,
  insufficientEvidence,
  suggestedQueries,
  onSuggestedQueryClick,
}: AnswerStreamPanelProps): JSX.Element {
  const trimmedAnswer = answerText.trim();
  const showPrelude = streamActive && !trimmedAnswer && !searchLoading;
  const showDegradedChatError = Boolean(errorMessage && sourcesAvailable);
  const idle =
    !searchLoading &&
    !streamActive &&
    !errorMessage &&
    !insufficientEvidence &&
    !trimmedAnswer;

  return (
    <section className="rounded-2xl border border-indigo-100 bg-white/95 p-4 shadow-sm shadow-indigo-100/70" aria-live="polite">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Answer</h2>
      <div className="mt-3 min-h-[120px] text-sm leading-relaxed text-slate-800">
        {searchLoading ? (
          <p className="text-slate-500">Searching Lenny&apos;s archive...</p>
        ) : null}

        {!searchLoading && errorMessage && showDegradedChatError ? (
          <div
            className="space-y-3 rounded-xl border border-indigo-200 bg-indigo-50/80 p-3"
            data-testid="chat-partial-failure-banner"
            role="alert"
          >
            <p className="text-sm font-semibold text-indigo-950">Answer generation stopped early</p>
            <p className="text-sm text-rose-800">{errorMessage}</p>
            {trimmedAnswer ? (
              <p className="whitespace-pre-wrap text-slate-800" data-testid="answer-stream-text">
                {answerText}
              </p>
            ) : null}
            {onRetryAnswer ? (
              <button
                type="button"
                className="rounded-lg border border-indigo-300 bg-white px-3 py-2 text-sm font-medium text-indigo-900 shadow-sm transition-all duration-200 motion-safe:hover:-translate-y-0.5 hover:bg-indigo-50 hover:shadow-md"
                onClick={onRetryAnswer}
              >
                Generate answer from these sources
              </button>
            ) : null}
          </div>
        ) : null}

        {!searchLoading && errorMessage && !showDegradedChatError ? (
          <p className="text-rose-700" role="alert">
            {errorMessage}
          </p>
        ) : null}

        {!searchLoading && !errorMessage && insufficientEvidence ? (
          <div className="space-y-3">
            {trimmedAnswer ? (
              <p className="whitespace-pre-wrap text-slate-800">{answerText}</p>
            ) : null}
            <p className="font-medium text-slate-900">Not enough evidence in the archive for a grounded answer.</p>
            <p className="text-slate-600">Try one of these broader queries:</p>
            <ul className="flex flex-wrap gap-2">
              {suggestedQueries.map((suggestion) => (
                <li key={suggestion}>
                  <button
                    type="button"
                    className="rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-900 transition-all duration-200 motion-safe:hover:-translate-y-0.5 hover:bg-indigo-100 hover:shadow-sm hover:shadow-indigo-200/60"
                    onClick={() => onSuggestedQueryClick(suggestion)}
                  >
                    {suggestion}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {!searchLoading && !errorMessage && !insufficientEvidence ? (
          <>
            {showPrelude ? <p className="mb-2 italic text-slate-500">Thinking with sources...</p> : null}
            {trimmedAnswer ? (
              <p className="whitespace-pre-wrap" data-testid="answer-stream-text">
                {answerText}
                {streamActive ? (
                  <span
                    className="ml-0.5 inline-block h-4 w-1 animate-pulse bg-indigo-500 align-middle"
                    aria-hidden
                  />
                ) : null}
              </p>
            ) : null}
            {idle ? (
              <p className="text-slate-500">Submit a question to stream a grounded answer with citations.</p>
            ) : null}
          </>
        ) : null}
      </div>
    </section>
  );
}
