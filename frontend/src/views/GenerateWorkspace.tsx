import { useCallback, useMemo, useState } from "react";

import { postOutline, streamExecute } from "../api/generateApi";
import GenerateInputForm from "../components/generate/GenerateInputForm";
import GenerationProgress from "../components/generate/GenerationProgress";
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

  const handleReset = useCallback(() => {
    setPhase("input");
    setOutline(null);
    setSteps([]);
    setResult(null);
    setErrorMessage(undefined);
    setBusy(false);
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
          <SyllabusOutput syllabus={result.syllabus} />
          <QuizOutput quiz={result.quiz} />
          <div className="flex justify-end">
            <button
              type="button"
              onClick={handleReset}
              className="cursor-pointer rounded-full border border-slate-300 bg-white px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-700 transition-colors duration-200 hover:bg-slate-50"
            >
              Start over
            </button>
          </div>
        </>
      ) : null}
    </div>
  );
}
