import { useCallback, useMemo, useState } from "react";

import { postInfographic, postOutline, streamExecute } from "../api/generateApi";
import GenerateInputForm from "../components/generate/GenerateInputForm";
import GenerationProgress from "../components/generate/GenerationProgress";
import InfographicPopup from "../components/generate/InfographicPopup";
import OutlineReview from "../components/generate/OutlineReview";
import QuizOutput from "../components/generate/QuizOutput";
import SyllabusOutput from "../components/generate/SyllabusOutput";
import type {
  DifficultyLevel,
  GenerateResultPayload,
  OutlineResponse,
  StepLogPayload,
  WeekOutline,
} from "../types/generate";

type Phase = "input" | "outline" | "generating" | "complete";

export default function GenerateWorkspace(): JSX.Element {
  const [phase, setPhase] = useState<Phase>("input");
  const [outline, setOutline] = useState<OutlineResponse | null>(null);
  const [steps, setSteps] = useState<StepLogPayload[]>([]);
  const [result, setResult] = useState<GenerateResultPayload | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);
  const [infographicHtml, setInfographicHtml] = useState<string | null>(null);
  const [infographicLoading, setInfographicLoading] = useState(false);

  const canShowOutput = useMemo(() => phase === "complete" && result !== null, [phase, result]);

  const handleGenerateOutline = useCallback(async (topic: string, numWeeks: number, difficulty: DifficultyLevel) => {
    setBusy(true);
    setErrorMessage(undefined);
    setResult(null);
    setSteps([]);
    try {
      const response = await postOutline({ topic, num_weeks: numWeeks, difficulty });
      setOutline(response);
      setPhase("outline");
    } catch (error: unknown) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to generate outline.");
    } finally {
      setBusy(false);
    }
  }, []);

  const handleApproveOutline = useCallback(
    async (approvedOutline: WeekOutline[]) => {
      if (!outline) {
        return;
      }
      setBusy(true);
      setErrorMessage(undefined);
      setResult(null);
      setSteps([]);
      setPhase("generating");

      try {
        await streamExecute(
          {
            topic: outline.topic,
            num_weeks: outline.num_weeks,
            difficulty: outline.difficulty,
            approved_outline: approvedOutline,
          },
          {
            onStepLog: (payload) => setSteps((current) => [...current, payload]),
            onResult: (payload) => setResult(payload),
            onError: (payload) => setErrorMessage(payload.message),
            onDone: () => setPhase("complete"),
          }
        );
      } catch (error: unknown) {
        setErrorMessage(error instanceof Error ? error.message : "Generation failed.");
        setPhase("outline");
      } finally {
        setBusy(false);
      }
    },
    [outline]
  );

  const handleGenerateInfographic = useCallback(async () => {
    if (!result) return;
    setInfographicLoading(true);
    setErrorMessage(undefined);
    try {
      const html = await postInfographic(result.syllabus);
      setInfographicHtml(html);
    } catch (error: unknown) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to generate infographic.");
    } finally {
      setInfographicLoading(false);
    }
  }, [result]);

  const handleReset = useCallback(() => {
    setPhase("input");
    setOutline(null);
    setSteps([]);
    setResult(null);
    setErrorMessage(undefined);
    setBusy(false);
    setInfographicHtml(null);
    setInfographicLoading(false);
  }, []);

  return (
    <div className="flex flex-col gap-4">
      {errorMessage ? (
        <div className="rounded-md border border-rose-300 bg-rose-50 p-3 text-sm text-rose-700">{errorMessage}</div>
      ) : null}

      {phase === "input" ? <GenerateInputForm disabled={busy} onSubmit={handleGenerateOutline} /> : null}

      {phase === "outline" && outline ? (
        <OutlineReview
          disabled={busy}
          outline={outline}
          onApprove={handleApproveOutline}
          onBack={handleReset}
        />
      ) : null}

      {phase === "generating" ? <GenerationProgress active={busy} steps={steps} /> : null}

      {canShowOutput && result ? (
        <>
          <GenerationProgress active={false} steps={steps} />
          <button
            type="button"
            onClick={handleGenerateInfographic}
            disabled={infographicLoading}
            className="inline-flex cursor-pointer items-center gap-2 self-start rounded-full border border-amber-300 bg-amber-50 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-amber-800 transition-all duration-200 motion-safe:hover:-translate-y-0.5 hover:bg-amber-100 hover:shadow-sm disabled:cursor-not-allowed disabled:opacity-50"
          >
            {infographicLoading ? (
              <>
                <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Generating infographic...
              </>
            ) : (
              "Generate infographic"
            )}
          </button>
          <SyllabusOutput syllabus={result.syllabus} />
          <QuizOutput quiz={result.quiz} />
          <div className="flex justify-end">
            <button
              type="button"
              onClick={handleReset}
              className="cursor-pointer rounded-full border border-slate-300 bg-white px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-700 transition-all duration-200 motion-safe:hover:-translate-y-0.5 hover:bg-slate-50 hover:shadow-sm"
            >
              Start over
            </button>
          </div>

          {infographicHtml ? (
            <InfographicPopup html={infographicHtml} onClose={() => setInfographicHtml(null)} />
          ) : null}
        </>
      ) : null}
    </div>
  );
}
