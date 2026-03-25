import { useState } from "react";

import type { DifficultyLevel } from "../../types/generate";

interface GenerateInputFormProps {
  disabled: boolean;
  onSubmit: (topic: string, numWeeks: number, difficulty: DifficultyLevel) => void;
}

export default function GenerateInputForm({ disabled, onSubmit }: GenerateInputFormProps): JSX.Element {
  const [topic, setTopic] = useState("");
  const [numWeeks, setNumWeeks] = useState(8);
  const [difficulty, setDifficulty] = useState<DifficultyLevel>("intermediate");

  function handleSubmit(): void {
    const trimmed = topic.trim();
    if (!trimmed) {
      return;
    }
    onSubmit(trimmed, numWeeks, difficulty);
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6">
      <h2 className="text-xl font-semibold text-slate-900">Create a syllabus</h2>
      <p className="mt-2 text-sm text-slate-600">
        Provide a topic, course length, and difficulty level. The agent will propose an outline for review.
      </p>

      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <label className="md:col-span-2">
          <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Topic</span>
          <input
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
            disabled={disabled}
            placeholder="e.g. Product-Led Growth"
            className="w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none transition-colors duration-200 focus:border-amber-400 focus:bg-white motion-reduce:transition-none disabled:cursor-not-allowed disabled:opacity-70"
          />
        </label>

        <label>
          <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Weeks</span>
          <input
            type="number"
            min={2}
            max={16}
            value={numWeeks}
            onChange={(event) => setNumWeeks(Math.min(16, Math.max(2, Number(event.target.value) || 8)))}
            disabled={disabled}
            className="w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none transition-colors duration-200 focus:border-amber-400 focus:bg-white motion-reduce:transition-none disabled:cursor-not-allowed disabled:opacity-70"
          />
        </label>

        <label>
          <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Difficulty</span>
          <select
            value={difficulty}
            onChange={(event) => setDifficulty(event.target.value as DifficultyLevel)}
            disabled={disabled}
            className="w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none transition-colors duration-200 focus:border-amber-400 focus:bg-white motion-reduce:transition-none disabled:cursor-not-allowed disabled:opacity-70"
          >
            <option value="intro">Intro</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </select>
        </label>
      </div>

      <div className="mt-6 flex justify-end">
        <button
          type="button"
          disabled={disabled || !topic.trim()}
          onClick={handleSubmit}
          className="cursor-pointer rounded-full bg-slate-900 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-amber-100 transition-colors duration-200 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Generate outline
        </button>
      </div>
    </section>
  );
}
