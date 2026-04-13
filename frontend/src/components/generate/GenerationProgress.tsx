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
      <h2 className="text-xl font-semibold text-slate-900">Building Your Playbook ⚙️</h2>
      <p className="mt-2 text-sm text-slate-600">
        {active ? "Sourcing insights from Lenny's archive and building your playbook." : "Playbook complete."}
      </p>

      <ol className="mt-5 space-y-2 rounded-lg bg-slate-900 p-3 font-mono text-xs text-slate-100">
        {steps.length === 0 ? (
          <li className="flex items-center gap-2 text-slate-300">
            {active ? (
              <svg
                className="h-3.5 w-3.5 animate-spin"
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
            ) : null}
            Waiting for events...
          </li>
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
                {typeof step.week === "number" ? <p className="text-slate-400">phase {step.week}</p> : null}
              </div>
            </li>
          ))
        )}
      </ol>
    </section>
  );
}
