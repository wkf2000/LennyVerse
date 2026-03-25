import type { SearchResult } from "../../types/search";

export interface SourcesListProps {
  results: SearchResult[];
  selectedId?: string;
  citedIds?: ReadonlySet<string>;
  onSelect: (id: string) => void;
}

export default function SourcesList({ results, selectedId, citedIds, onSelect }: SourcesListProps): JSX.Element {
  return (
    <section className="flex min-h-[220px] flex-col rounded-2xl border border-slate-200 bg-white p-4 shadow-sm lg:min-h-0 lg:max-h-[42vh]">
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
                  className={`w-full rounded-xl border p-3 text-left text-sm transition-colors motion-reduce:transition-none ${
                    selected
                      ? "border-amber-400 bg-amber-50 ring-1 ring-amber-300"
                      : cited
                        ? "border-amber-200/80 bg-amber-50/50 hover:border-amber-300"
                        : "border-slate-200 bg-slate-50/80 hover:border-amber-200 hover:bg-white"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-medium text-slate-900">{result.title}</span>
                    {cited ? (
                      <span className="shrink-0 rounded bg-amber-200/80 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-amber-900">
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
