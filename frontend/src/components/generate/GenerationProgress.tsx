import type { StepLogPayload } from "../../types/generate";

interface GenerationProgressProps {
  active: boolean;
  steps: StepLogPayload[];
}

function statusGlyph(status: StepLogPayload["status"]): string {
  if (status === "done") {
    return "✓";
  }
  if (status === "error") {
    return "✕";
  }
  return "…";
}

function statusClasses(status: StepLogPayload["status"]): string {
  if (status === "done") {
    return "bg-emerald-100 text-emerald-800";
  }
  if (status === "error") {
    return "bg-rose-100 text-rose-800";
  }
  return "bg-amber-100 text-amber-900";
}

export default function GenerationProgress({ active, steps }: GenerationProgressProps): JSX.Element {
  return (
    <section className="rounded-2xl border border-indigo-100 bg-white/95 p-6 shadow-sm shadow-indigo-100/70">
      <h2 className="text-xl font-semibold text-slate-900">Generation Progress ⚙️</h2>
      <p className="mt-2 text-sm text-slate-600">
        {active ? "The agent is generating your syllabus and quiz." : "Generation finished."}
      </p>

      <ol className="mt-5 space-y-2 rounded-lg bg-slate-900 p-3 font-mono text-xs text-slate-100">
        {steps.length === 0 ? (
          <li className="text-slate-300">Waiting for events...</li>
        ) : (
          steps.map((step, index) => (
            <li key={`${index}-${step.node}-${step.message}`} className="flex items-start gap-2">
              <span className={`mt-[1px] inline-flex h-5 w-5 items-center justify-center rounded-full ${statusClasses(step.status)}`}>
                {statusGlyph(step.status)}
              </span>
              <div>
                <p>
                  <span className="text-indigo-200">{step.node}</span> - {step.message}
                </p>
                {typeof step.week === "number" ? <p className="text-slate-400">week {step.week}</p> : null}
              </div>
            </li>
          ))
        )}
      </ol>
    </section>
  );
}
