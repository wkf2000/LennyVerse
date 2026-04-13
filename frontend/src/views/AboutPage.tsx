export default function AboutPage(): JSX.Element {
  return (
    <section className="mx-auto max-w-7xl px-4 pb-8 pt-24 sm:px-6 lg:px-8">
      <header className="mb-10">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-indigo-700">Lenny&apos;s Second Brain 💡</p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">
          Built for Lenny&apos;s Challenge
        </h1>
        <p className="mt-3 max-w-3xl text-sm text-slate-600">
          A knowledge graph and personalized playbook engine built on 638 episodes of Lenny&apos;s Newsletter and podcast
        </p>
      </header>

      <div className="max-w-3xl space-y-6 text-sm leading-6 text-slate-700">
        <section className="rounded-2xl border border-indigo-100 bg-white/90 p-5 shadow-sm">
          <h2 className="text-lg font-semibold tracking-tight text-slate-900">
            What is this? 🧠
          </h2>
          <p className="mt-2">
            Lenny&apos;s Second Brain turns 638 episodes and 350+ newsletter posts into an interactive
            knowledge graph and a personalized playbook generator. Ask questions, explore connections
            between guests, topics, and frameworks, or build an actionable plan tailored to your role
            and challenge — all grounded in Lenny&apos;s archive with direct citations.
          </p>
        </section>

        <section className="rounded-2xl border border-indigo-100 bg-white/90 p-5 shadow-sm">
          <h2 className="text-lg font-semibold tracking-tight text-slate-900">
            How it&apos;s built 🛠️
          </h2>
          <p className="mt-2">
            A Vite + React frontend talks to a FastAPI backend. Content and vectors live in Postgres via Supabase
            (including pgvector). A Neo4j knowledge graph powers the visualization. Language models are invoked
            through an OpenAI-compatible API for RAG search and playbook generation.
          </p>
        </section>

        <div className="pt-2">
          <a
            href="/"
            className="inline-flex items-center gap-2 rounded-full bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:bg-indigo-500 hover:-translate-y-0.5"
          >
            ← Back to Lenny&apos;s Second Brain
          </a>
        </div>
      </div>
    </section>
  );
}
