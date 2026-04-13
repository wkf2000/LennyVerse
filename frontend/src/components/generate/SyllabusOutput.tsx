import type { GeneratedSyllabus } from "../../types/generate";

interface SyllabusOutputProps {
  syllabus: GeneratedSyllabus;
}

function renderTextWithCitations(text: string): JSX.Element {
  const citationPattern = /(\[cite:[^\]]+])/g;
  const parts = text.split(citationPattern).filter(Boolean);
  return (
    <>
      {parts.map((part, index) =>
        part.startsWith("[cite:") ? (
          <a
            key={`${part}-${index}`}
            href={`/explore?q=${encodeURIComponent(part)}`}
            className="ml-1 inline-flex rounded bg-amber-100 px-1 py-0.5 text-[11px] font-medium text-amber-900 hover:bg-amber-200"
            title="View source context"
          >
            {part}
          </a>
        ) : (
          <span key={`${part}-${index}`}>{part}</span>
        )
      )}
    </>
  );
}

export default function SyllabusOutput({ syllabus }: SyllabusOutputProps): JSX.Element {
  return (
    <section className="rounded-2xl border border-indigo-100 bg-white/95 p-6 shadow-sm">
      <h2 className="text-xl font-semibold text-slate-900">Your Playbook</h2>
      <p className="mt-2 text-sm text-slate-600">
        {syllabus.topic} · {syllabus.difficulty}
      </p>

      <div className="mt-5 space-y-4">
        {syllabus.weeks.map((week) => (
          <article key={`week-${week.week_number}`} className="rounded-2xl border border-indigo-100 bg-white/95 p-6">
            <div className="flex items-center justify-between gap-2">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">
                  Phase {week.week_number}
                </p>
                <h3 className="mt-1 text-base font-semibold text-slate-900">{week.theme}</h3>
              </div>
              <span
                className={`rounded-full px-2 py-1 text-xs font-medium uppercase tracking-wide ${
                  week.status === "complete" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-900"
                }`}
              >
                {week.status}
              </span>
            </div>

            <div className="mt-3">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Objectives</h4>
              <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-700">
                {week.learning_objectives.map((objective, index) => (
                  <li key={`${week.week_number}-objective-${index}`}>{objective}</li>
                ))}
              </ul>
            </div>

            <div className="mt-3">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Summary</h4>
              <p className="mt-1 text-sm text-slate-700">{renderTextWithCitations(week.narrative_summary)}</p>
            </div>

            <div className="mt-3">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Sources</h4>
              <ul className="mt-1 space-y-3">
                {week.readings.map((reading) => (
                  <li key={`${week.week_number}-${reading.content_id}`} className="rounded-lg border border-slate-200 bg-white p-4">
                    <p className="text-sm font-medium text-slate-900">{reading.title}</p>
                    <p className="mt-1 text-xs uppercase tracking-wide text-slate-500">{reading.content_type}</p>
                    {reading.key_concepts?.length > 0 && (
                      <div className="mt-3">
                        <h5 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Key Frameworks</h5>
                        <div className="mt-1.5 flex flex-wrap gap-2">
                          {reading.key_concepts.map((concept, ci) => (
                            <span
                              key={`${week.week_number}-${reading.content_id}-concept-${ci}`}
                              className="inline-block rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-900"
                            >
                              {concept}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {reading.notable_quotes?.length > 0 && (
                      <div className="mt-3 space-y-2">
                        {reading.notable_quotes.map((quote, qi) => (
                          <blockquote
                            key={`${week.week_number}-${reading.content_id}-quote-${qi}`}
                            className="border-l-4 border-indigo-300 bg-indigo-50/50 pl-4 py-3 rounded-r-lg text-sm italic text-slate-700"
                          >
                            &ldquo;{quote}&rdquo;
                            <footer className="mt-1 text-xs font-medium text-indigo-600 not-italic">
                              — from {reading.title}
                            </footer>
                          </blockquote>
                        ))}
                      </div>
                    )}
                    {reading.discussion_hooks?.length > 0 && (
                      <div className="mt-3 rounded-lg bg-emerald-50 border border-emerald-200 p-3">
                        <h5 className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Action Items</h5>
                        <ul className="mt-2 space-y-1.5 text-sm text-slate-700">
                          {reading.discussion_hooks.map((hook, hi) => (
                            <li key={`${week.week_number}-${reading.content_id}-hook-${hi}`} className="flex items-start gap-2">
                              <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500"></span>
                              <span>{hook}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </div>

            <div className="mt-3">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Key takeaways</h4>
              <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-700">
                {week.key_takeaways.map((takeaway, index) => (
                  <li key={`${week.week_number}-takeaway-${index}`}>{takeaway}</li>
                ))}
              </ul>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
