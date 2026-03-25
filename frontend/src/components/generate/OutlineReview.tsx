import type { OutlineResponse, WeekOutline } from "../../types/generate";

interface OutlineReviewProps {
  disabled: boolean;
  outline: OutlineResponse;
  onApprove: (editedOutline: WeekOutline[]) => void;
  onBack: () => void;
}

export default function OutlineReview({
  disabled,
  outline,
  onApprove,
  onBack,
}: OutlineReviewProps): JSX.Element {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-amber-700">Outline Review</p>
        <h2 className="mt-2 text-xl font-semibold text-slate-900">{outline.topic}</h2>
        <p className="mt-2 text-sm text-slate-600">
          {outline.num_weeks} weeks · {outline.difficulty} · {outline.corpus_coverage}
        </p>
      </header>

      {outline.low_coverage ? (
        <div className="mt-4 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          Limited source material found for this topic. You can still continue, but review readings carefully.
        </div>
      ) : null}

      <div className="mt-5 space-y-3">
        {outline.weeks.map((week) => (
          <article key={`${week.week_number}-${week.theme}`} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-base font-semibold text-slate-900">
                Week {week.week_number}: {week.theme}
              </h3>
              <span className="rounded-full bg-amber-100 px-2 py-1 text-xs font-medium uppercase tracking-wide text-amber-900">
                {week.readings.length} reading{week.readings.length === 1 ? "" : "s"}
              </span>
            </div>
            <p className="mt-2 text-sm text-slate-700">{week.description}</p>

            <ul className="mt-3 space-y-2">
              {week.readings.map((reading) => (
                <li key={`${week.week_number}-${reading.content_id}`} className="rounded-md border border-slate-200 bg-white p-3">
                  <p className="text-sm font-medium text-slate-900">{reading.title}</p>
                  <p className="mt-1 text-xs uppercase tracking-wide text-slate-500">{reading.content_type}</p>
                  <p className="mt-1 text-sm text-slate-700">{reading.relevance_summary}</p>
                </li>
              ))}
            </ul>
          </article>
        ))}
      </div>

      <div className="mt-6 flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={onBack}
          disabled={disabled}
          className="cursor-pointer rounded-full border border-slate-300 bg-white px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-700 transition-colors duration-200 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Back
        </button>
        <button
          type="button"
          onClick={() => onApprove(outline.weeks)}
          disabled={disabled}
          className="cursor-pointer rounded-full bg-slate-900 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-amber-100 transition-colors duration-200 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Approve and generate
        </button>
      </div>
    </section>
  );
}
