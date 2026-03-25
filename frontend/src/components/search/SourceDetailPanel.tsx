import type { SearchResult } from "../../types/search";

export interface SourceDetailPanelProps {
  result: SearchResult | null;
  highlightSpan?: { start: number; end: number } | null;
}

function HighlightedExcerpt({
  excerpt,
  start,
  end,
}: {
  excerpt: string;
  start: number;
  end: number;
}): JSX.Element {
  const safeStart = Math.max(0, Math.min(start, excerpt.length));
  const safeEnd = Math.max(safeStart, Math.min(end, excerpt.length));
  const before = excerpt.slice(0, safeStart);
  const mid = excerpt.slice(safeStart, safeEnd);
  const after = excerpt.slice(safeEnd);

  return (
    <p className="text-sm leading-relaxed text-slate-800" data-testid="source-detail-excerpt">
      {before}
      {mid ? (
        <mark className="rounded bg-amber-200 px-0.5 text-slate-900" data-testid="citation-marker">
          {mid}
        </mark>
      ) : null}
      {after}
    </p>
  );
}

export default function SourceDetailPanel({ result, highlightSpan }: SourceDetailPanelProps): JSX.Element {
  if (!result) {
    return (
      <section className="flex min-h-[220px] flex-col rounded-2xl border border-slate-200 bg-white p-4 shadow-sm lg:min-h-0 lg:max-h-[42vh]">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Source detail</h2>
        <div className="mt-6 grid flex-1 place-items-center text-center text-sm text-slate-500">
          Select a source row to read the full excerpt and metadata.
        </div>
      </section>
    );
  }

  const hasSpan =
    highlightSpan !== undefined &&
    highlightSpan !== null &&
    highlightSpan.end > highlightSpan.start;

  return (
    <section className="flex min-h-[220px] flex-col rounded-2xl border border-slate-200 bg-white p-4 shadow-sm lg:min-h-0 lg:max-h-[42vh]">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Source detail</h2>
      <div className="mt-3 flex-1 overflow-y-auto">
        <h3 className="text-lg font-semibold text-slate-900">{result.title}</h3>
        <p className="mt-1 text-xs uppercase tracking-wide text-slate-500">
          {result.content_id} · chunk {result.chunk_index}
        </p>
        <dl className="mt-3 space-y-2 text-sm">
          {result.guest ? (
            <div>
              <dt className="text-xs font-semibold text-slate-500">Guest</dt>
              <dd className="text-slate-800">{result.guest}</dd>
            </div>
          ) : null}
          {result.date ? (
            <div>
              <dt className="text-xs font-semibold text-slate-500">Date</dt>
              <dd className="text-slate-800">{result.date}</dd>
            </div>
          ) : null}
          {result.tags.length > 0 ? (
            <div>
              <dt className="text-xs font-semibold text-slate-500">Tags</dt>
              <dd className="flex flex-wrap gap-1">
                {result.tags.map((tag) => (
                  <span key={tag} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700">
                    {tag}
                  </span>
                ))}
              </dd>
            </div>
          ) : null}
        </dl>
        <div className="mt-4">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Excerpt</h4>
          <div className="mt-1">
            {hasSpan && highlightSpan ? (
              <HighlightedExcerpt excerpt={result.excerpt} start={highlightSpan.start} end={highlightSpan.end} />
            ) : (
              <p className="text-sm leading-relaxed text-slate-800" data-testid="source-detail-excerpt">
                {result.excerpt}
              </p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
