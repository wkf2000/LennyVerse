import { useState } from "react";

import type { DifficultyLevel } from "../../types/generate";
import Spinner from "../Spinner";

interface GenerateInputFormProps {
  disabled: boolean;
  onSubmit: (topic: string, numWeeks: number, difficulty: DifficultyLevel, role?: string, companyStage?: string) => void;
}

const PRESETS = [
  {
    label: "Activation & Retention",
    description: "I'm a PM at a Series A startup. Users sign up but never come back.",
    topic: "User activation and retention strategies for early-stage startups",
    numWeeks: 4,
    role: "Product Manager",
    companyStage: "Series A",
  },
  {
    label: "Pricing Strategy",
    description: "I'm a solo founder. I have no idea how to price my product.",
    topic: "Product pricing strategy and monetization frameworks",
    numWeeks: 4,
    role: "Founder",
    companyStage: "Pre-PMF",
  },
  {
    label: "Onboarding Optimization",
    description: "I'm a growth lead. Our onboarding flow is leaking users.",
    topic: "User onboarding optimization and growth loops",
    numWeeks: 4,
    role: "Growth Lead",
    companyStage: "Growth Stage",
  },
  {
    label: "PM Foundations",
    description: "I'm a first-time PM. I want to learn the fundamentals.",
    topic: "Product management foundations and frameworks for new PMs",
    numWeeks: 4,
    role: "Product Manager",
  },
];

/** Backend `OutlineRequest` requires num_weeks >= 2; keep labels honest about phase count. */
const LENGTH_OPTIONS = [
  { label: "2-week sprint", value: 2 },
  { label: "30-day plan", value: 4 },
  { label: "90-day roadmap", value: 12 },
] as const;

export default function GenerateInputForm({ disabled, onSubmit }: GenerateInputFormProps): JSX.Element {
  const [showCustom, setShowCustom] = useState(false);
  const [topic, setTopic] = useState("");
  const [numWeeks, setNumWeeks] = useState(4);

  const [role, setRole] = useState("");
  const [companyStage, setCompanyStage] = useState("");

  function handlePresetClick(preset: (typeof PRESETS)[number]): void {
    if (disabled) return;
    onSubmit(preset.topic, preset.numWeeks, "intermediate", preset.role, preset.companyStage);
  }

  function handleCustomSubmit(): void {
    const trimmed = topic.trim();
    if (!trimmed) return;
    onSubmit(trimmed, numWeeks, "intermediate", role || undefined, companyStage || undefined);
  }

  return (
    <section className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2">
        {PRESETS.map((preset) => (
          <button
            key={preset.label}
            type="button"
            disabled={disabled}
            onClick={() => handlePresetClick(preset)}
            className="cursor-pointer rounded-2xl border border-indigo-100 bg-white/95 p-5 text-left shadow-sm transition-all duration-200 hover:border-indigo-300 hover:-translate-y-0.5 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0"
          >
            <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">{preset.label}</p>
            <p className="mt-2 text-sm text-slate-700">{preset.description}</p>
            {disabled ? (
              <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
                <Spinner className="h-3.5 w-3.5" /> Building playbook...
              </div>
            ) : null}
          </button>
        ))}
      </div>

      <div className="flex items-center gap-3">
        <div className="h-px flex-1 bg-slate-200" />
        <button
          type="button"
          onClick={() => setShowCustom((c) => !c)}
          className="cursor-pointer text-xs font-medium text-slate-500 transition-colors hover:text-indigo-600"
        >
          {showCustom ? "hide custom form" : "or describe your own challenge"}
        </button>
        <div className="h-px flex-1 bg-slate-200" />
      </div>

      {showCustom ? (
        <div className="rounded-2xl border border-indigo-100 bg-white/95 p-6 shadow-sm shadow-indigo-100/70">
          <h2 className="text-xl font-semibold text-slate-900">Custom playbook</h2>
          <p className="mt-2 text-sm text-slate-600">
            Describe your challenge and choose a playbook length.
          </p>

          <div className="mt-5 grid gap-4">
            <label>
              <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                Your challenge
              </span>
              <input
                value={topic}
                onChange={(event) => setTopic(event.target.value)}
                disabled={disabled}
                placeholder="e.g. How do I improve activation for my B2B SaaS product?"
                className="w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none transition-colors duration-200 focus:border-indigo-400 focus:bg-white motion-reduce:transition-none disabled:cursor-not-allowed disabled:opacity-70"
              />
            </label>

            <div className="grid gap-4 sm:grid-cols-2">
              <label>
                <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Your role
                </span>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  disabled={disabled}
                  className="w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none transition-colors duration-200 focus:border-indigo-400 focus:bg-white disabled:cursor-not-allowed disabled:opacity-70"
                >
                  <option value="">Any role</option>
                  <option value="Product Manager">Product Manager</option>
                  <option value="Founder">Founder</option>
                  <option value="Growth Lead">Growth Lead</option>
                  <option value="Engineering Manager">Engineering Manager</option>
                  <option value="Designer">Designer</option>
                </select>
              </label>
              <label>
                <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Company stage
                </span>
                <select
                  value={companyStage}
                  onChange={(e) => setCompanyStage(e.target.value)}
                  disabled={disabled}
                  className="w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none transition-colors duration-200 focus:border-indigo-400 focus:bg-white disabled:cursor-not-allowed disabled:opacity-70"
                >
                  <option value="">Any stage</option>
                  <option value="Pre-PMF">Pre-PMF</option>
                  <option value="Seed/Series A">Seed / Series A</option>
                  <option value="Growth Stage">Growth Stage</option>
                  <option value="Enterprise">Enterprise</option>
                </select>
              </label>
            </div>

            <div>
              <span className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                Playbook length
              </span>
              <div className="flex gap-2">
                {LENGTH_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    disabled={disabled}
                    onClick={() => setNumWeeks(opt.value)}
                    className={`cursor-pointer rounded-full border px-3 py-1.5 text-xs font-medium transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-50 ${
                      numWeeks === opt.value
                        ? "border-indigo-300 bg-indigo-100 text-indigo-900"
                        : "border-slate-200 text-slate-600 hover:border-indigo-200 hover:bg-indigo-50"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-6 flex justify-end">
            <button
              type="button"
              disabled={disabled || !topic.trim()}
              onClick={handleCustomSubmit}
              className="flex cursor-pointer items-center gap-2 rounded-full bg-indigo-600 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-indigo-50 shadow-sm shadow-indigo-300/40 transition-all duration-200 hover:bg-indigo-500 motion-safe:hover:-translate-y-0.5 hover:shadow-md hover:shadow-indigo-300/50 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0"
            >
              {disabled ? <Spinner className="h-3.5 w-3.5" /> : null}
              {disabled ? "Building..." : "Build my playbook"}
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
}
