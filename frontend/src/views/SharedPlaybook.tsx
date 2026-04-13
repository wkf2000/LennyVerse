import { useEffect, useState } from "react";

import { fetchSharedPlaybook } from "../api/generateApi";
import type { GenerateResultPayload } from "../types/generate";
import SyllabusOutput from "../components/generate/SyllabusOutput";

interface SharedPlaybookProps {
  slug: string;
}

export default function SharedPlaybook({ slug }: SharedPlaybookProps): JSX.Element {
  const [data, setData] = useState<GenerateResultPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchSharedPlaybook(slug)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load playbook");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f4f7ff]">
        <p className="text-sm text-slate-500">Loading playbook...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-[#f4f7ff]">
        <p className="text-sm text-slate-600">{error || "Playbook not found"}</p>
        <a
          href="/"
          className="rounded-full bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:bg-indigo-500"
        >
          Go to Lenny&apos;s Second Brain
        </a>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-[#f4f7ff]">
      <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6">
        <header className="mb-8 text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-indigo-700">
            Lenny&apos;s Second Brain
          </p>
          <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">
            {data.syllabus.topic}
          </h1>
          <div className="mt-3 flex items-center justify-center gap-2">
            <span className="rounded-full bg-indigo-100 px-3 py-1 text-xs font-medium text-indigo-800">
              {data.syllabus.difficulty}
            </span>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
              {data.syllabus.weeks.length} phases
            </span>
          </div>
        </header>

        <SyllabusOutput syllabus={data.syllabus} />

        <footer className="mt-12 text-center">
          <p className="text-sm text-slate-500">
            Built with Lenny&apos;s Second Brain — powered by 638 episodes
          </p>
          <a
            href="/"
            className="mt-4 inline-flex rounded-full bg-indigo-600 px-8 py-3 text-sm font-semibold text-white shadow-sm transition-all hover:bg-indigo-500 hover:-translate-y-0.5"
          >
            Build your own playbook
          </a>
        </footer>
      </div>
    </main>
  );
}
