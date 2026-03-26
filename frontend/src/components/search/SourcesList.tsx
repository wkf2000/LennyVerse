import type { SearchResult } from "../../types/search";

export interface SourcesListProps {
  results: SearchResult[];
  selectedId?: string;
  citedIds?: ReadonlySet<string>;
  onSelect: (id: string) => void;
}

export default function SourcesList({ results, selectedId, citedIds, onSelect }: SourcesListProps): JSX.Element {
  return (
    <section className="flex min-h-[220px] flex-col rounded-2xl border border-indigo-100 bg-white/95 p-4 shadow-sm shadow-indigo-100/70 lg:min-h-0 lg:max-h-[42vh]">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Sources</h2>
      {results.length === 0 ? (
        <p className="mt-4 text-sm text-slate-500">No sources yet. Results appear as soon as search returns.</p>
      ) : (
        <ul className="mt-3 flex flex-1 flex-col gap-2 overflow-y-auto pr-1">
          {results.map((result) => {
            const selected = result.id === selectedId;
            const cited = citedIds?.has(result.id) ?? false;
            return (
              <li key={result.id}>
                <button
                  type="button"
                  data-testid={`source-row-${result.id}`}
                  onClick={() => onSelect(result.id)}
                  className={`w-full rounded-xl border p-3 text-left text-sm transition-all duration-200 motion-reduce:transition-none motion-safe:hover:-translate-y-0.5 ${
                    selected
                      ? "border-indigo-300 bg-indigo-50 ring-1 ring-indigo-200 shadow-sm shadow-indigo-200/60"
                      : cited
                        ? "border-indigo-200/80 bg-indigo-50/50 hover:border-indigo-300 hover:shadow-sm hover:shadow-indigo-200/50"
                        : "border-slate-200 bg-slate-50/80 hover:border-indigo-200 hover:bg-white hover:shadow-sm hover:shadow-indigo-200/50"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-medium text-slate-900">{result.title}</span>
                    {cited ? (
                      <span className="shrink-0 rounded bg-indigo-200/80 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-indigo-900">
                        Cited
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-1 line-clamp-2 text-xs text-slate-600">{result.excerpt}</p>
                  <p className="mt-2 text-xs text-slate-500">
                    {[result.guest, result.date].filter(Boolean).join(" · ")}
                    {Number.isFinite(result.score) ? ` · score ${result.score.toFixed(2)}` : ""}
                  </p>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
