import { useCallback, useMemo, useState } from "react";

import { postOutline, sharePlaybook, streamExecute } from "../api/generateApi";
import GenerateInputForm from "../components/generate/GenerateInputForm";
import GenerationProgress from "../components/generate/GenerationProgress";
import OutlineReview from "../components/generate/OutlineReview";
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
  const [shareStatus, setShareStatus] = useState<"idle" | "sharing" | "shared" | "error">("idle");
  const [shareSlug, setShareSlug] = useState<string | null>(null);
  const [persona, setPersona] = useState<{ role?: string; companyStage?: string }>({});
  const canShowOutput = useMemo(() => phase === "complete" && result !== null, [phase, result]);

  const handleGenerateOutline = useCallback(async (topic: string, numWeeks: number, difficulty: DifficultyLevel, role?: string, companyStage?: string) => {
    setBusy(true);
    setErrorMessage(undefined);
    setResult(null);
    setSteps([]);
    setPersona({ role, companyStage });
    try {
      const response = await postOutline({ topic, num_weeks: numWeeks, difficulty, role, company_stage: companyStage });
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
            role: persona.role,
            company_stage: persona.companyStage,
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

  const handleShare = useCallback(async () => {
    if (!result) return;
    setShareStatus("sharing");
    try {
      const slug = await sharePlaybook(result);
      setShareSlug(slug);
      setShareStatus("shared");
      const url = `${window.location.origin}/playbook/${slug}`;
      await navigator.clipboard.writeText(url);
    } catch {
      setShareStatus("error");
    }
  }, [result]);

  const handleReset = useCallback(() => {
    setPhase("input");
    setOutline(null);
    setSteps([]);
    setResult(null);
    setErrorMessage(undefined);
    setBusy(false);
    setShareStatus("idle");
    setShareSlug(null);
    setPersona({});
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
          <div className="flex items-center gap-3">
            {shareStatus === "shared" && shareSlug ? (
              <div className="flex items-center gap-2 rounded-full border border-emerald-300 bg-emerald-50 px-4 py-2 text-xs font-semibold text-emerald-800">
                <span>✓ Copied!</span>
                <span className="font-mono text-emerald-600">{window.location.origin}/playbook/{shareSlug}</span>
              </div>
            ) : shareStatus === "error" ? (
              <button
                type="button"
                onClick={handleShare}
                className="cursor-pointer rounded-full border border-rose-300 bg-rose-50 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-rose-700 transition-all hover:bg-rose-100"
              >
                Couldn&apos;t share — try again
              </button>
            ) : (
              <button
                type="button"
                onClick={handleShare}
                disabled={shareStatus === "sharing"}
                className="cursor-pointer rounded-full border border-indigo-300 bg-indigo-50 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-indigo-800 transition-all duration-200 hover:bg-indigo-100 hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {shareStatus === "sharing" ? "Sharing..." : "Share this playbook"}
              </button>
            )}
          </div>
          <div className="flex justify-end">
            <button
              type="button"
              onClick={handleReset}
              className="cursor-pointer rounded-full border border-slate-300 bg-white px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-700 transition-all duration-200 motion-safe:hover:-translate-y-0.5 hover:bg-slate-50 hover:shadow-sm"
            >
              Start over
            </button>
          </div>
        </>
      ) : null}
    </div>
  );
}
