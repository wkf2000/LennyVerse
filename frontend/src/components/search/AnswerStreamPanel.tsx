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

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

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

  const markdownComponents: Parameters<typeof ReactMarkdown>[0]["components"] = {
    h1: ({ children, ...props }) => (
      <h3 className="mt-4 text-lg font-semibold tracking-tight text-slate-950" {...props}>
        {children}
      </h3>
    ),
    h2: ({ children, ...props }) => (
      <h4 className="mt-4 text-base font-semibold tracking-tight text-slate-950" {...props}>
        {children}
      </h4>
    ),
    h3: ({ children, ...props }) => (
      <h5 className="mt-4 text-sm font-semibold tracking-tight text-slate-950" {...props}>
        {children}
      </h5>
    ),
    p: ({ children, ...props }) => (
      <p className="mt-3 whitespace-pre-wrap text-slate-800 first:mt-0" {...props}>
        {children}
      </p>
    ),
    a: ({ children, href, ...props }) => (
      <a
        className="font-medium text-indigo-700 underline decoration-indigo-200 underline-offset-2 transition-colors hover:text-indigo-900 hover:decoration-indigo-300"
        href={href}
        target="_blank"
        rel="noreferrer noopener"
        {...props}
      >
        {children}
      </a>
    ),
    ul: ({ children, ...props }) => (
      <ul className="mt-3 list-disc space-y-1 pl-5 text-slate-800 first:mt-0" {...props}>
        {children}
      </ul>
    ),
    ol: ({ children, ...props }) => (
      <ol className="mt-3 list-decimal space-y-1 pl-5 text-slate-800 first:mt-0" {...props}>
        {children}
      </ol>
    ),
    li: ({ children, ...props }) => (
      <li className="pl-1" {...props}>
        {children}
      </li>
    ),
    blockquote: ({ children, ...props }) => (
      <blockquote className="mt-3 border-l-2 border-indigo-200 pl-3 text-slate-700 first:mt-0" {...props}>
        {children}
      </blockquote>
    ),
    hr: (props) => <hr className="my-4 border-slate-200" {...props} />,
    code: ({ children, className, ...props }) => {
      const isBlock = typeof className === "string" && className.includes("language-");
      if (isBlock) {
        return (
          <code className={className} {...props}>
            {children}
          </code>
        );
      }
      return (
        <code
          className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[0.92em] text-slate-900"
          {...props}
        >
          {children}
        </code>
      );
    },
    pre: ({ children, ...props }) => (
      <pre
        className="mt-3 overflow-x-auto rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs leading-relaxed text-slate-900 first:mt-0"
        {...props}
      >
        {children}
      </pre>
    ),
  };

  return (
    <section
      className="flex h-[min(38vh,420px)] flex-col overflow-hidden rounded-2xl border border-indigo-100 bg-white/95 p-4 shadow-sm shadow-indigo-100/70"
      aria-live="polite"
    >
      <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Answer</h2>
      <div className="mt-3 min-h-0 flex-1 overflow-y-auto pr-2 text-sm leading-relaxed text-slate-800">
        {searchLoading ? (
          <div className="flex items-center gap-2 text-slate-500">
            <svg
              className="h-4 w-4 animate-spin"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <p>Exploring Lenny&apos;s archive...</p>
          </div>
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
              <div className="text-sm leading-relaxed text-slate-800" data-testid="answer-stream-text">
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                  {answerText}
                </ReactMarkdown>
              </div>
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
              <div className="text-sm leading-relaxed text-slate-800">
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                  {answerText}
                </ReactMarkdown>
              </div>
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
              <div className="text-sm leading-relaxed text-slate-800" data-testid="answer-stream-text">
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                  {answerText}
                </ReactMarkdown>
                {streamActive ? (
                  <span
                    className="ml-0.5 inline-block h-4 w-1 animate-pulse bg-indigo-500 align-middle"
                    aria-hidden
                  />
                ) : null}
              </div>
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
