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
            href={`/search?q=${encodeURIComponent(part)}`}
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
    <section className="rounded-2xl border border-slate-200 bg-white p-6">
      <h2 className="text-xl font-semibold text-slate-900">Generated Syllabus</h2>
      <p className="mt-2 text-sm text-slate-600">
        {syllabus.topic} · {syllabus.difficulty}
      </p>

      <div className="mt-5 space-y-4">
        {syllabus.weeks.map((week) => (
          <article key={`week-${week.week_number}`} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-base font-semibold text-slate-900">
                Week {week.week_number}: {week.theme}
              </h3>
              <span
                className={`rounded-full px-2 py-1 text-xs font-medium uppercase tracking-wide ${
                  week.status === "complete" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-900"
                }`}
              >
                {week.status}
              </span>
            </div>

            <div className="mt-3">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Learning objectives</h4>
              <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-700">
                {week.learning_objectives.map((objective, index) => (
                  <li key={`${week.week_number}-objective-${index}`}>{objective}</li>
                ))}
              </ul>
            </div>

            <div className="mt-3">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Narrative summary</h4>
              <p className="mt-1 text-sm text-slate-700">{renderTextWithCitations(week.narrative_summary)}</p>
            </div>

            <div className="mt-3">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Readings</h4>
              <ul className="mt-1 space-y-2">
                {week.readings.map((reading) => (
                  <li key={`${week.week_number}-${reading.content_id}`} className="rounded-md border border-slate-200 bg-white p-3">
                    <p className="text-sm font-medium text-slate-900">{reading.title}</p>
                    <p className="mt-1 text-xs uppercase tracking-wide text-slate-500">{reading.content_type}</p>
                    {reading.key_concepts.length > 0 ? (
                      <p className="mt-1 text-sm text-slate-700">Key concepts: {reading.key_concepts.join(", ")}</p>
                    ) : null}
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
