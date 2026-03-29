export default function AboutPage(): JSX.Element {
  return (
    <section className="mx-auto max-w-7xl px-4 pb-8 pt-24 sm:px-6 lg:px-8">
      <header className="mb-10">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-indigo-700">LennyVerse 💡</p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">
          A teaching assistant built on Lenny Rachitsky&apos;s archive
        </h1>
        <p className="mt-3 max-w-3xl text-sm text-slate-600">
          Explore the corpus visually, ask grounded questions with citations, and generate syllabus and quiz drafts
          that trace back to real episodes and newsletters
        </p>
      </header>

      <div className="max-w-3xl space-y-6 text-sm leading-6 text-slate-700">
        <section aria-labelledby="about-audience" className="rounded-2xl border border-indigo-100 bg-white/90 p-5 shadow-sm">
          <h2 id="about-audience" className="text-lg font-semibold tracking-tight text-slate-900">
            Who it&apos;s for 🎯
          </h2>
          <p className="mt-2">
            College instructors teaching product management, entrepreneurship, growth, and leadership—especially
            anyone who wants to anchor classes in practitioner content. The app is also a focused demo for
            hackathons and technical interviews: graph visualization, retrieval-augmented generation, and a
            visible multi-step generation flow.
          </p>
        </section>

        <section aria-labelledby="about-capabilities" className="rounded-2xl border border-indigo-100 bg-white/90 p-5 shadow-sm">
          <h2 id="about-capabilities" className="text-lg font-semibold tracking-tight text-slate-900">
            What you can do here ✨
          </h2>
          <ul className="mt-3 list-inside list-disc space-y-2">
            <li>
              <strong className="font-medium text-slate-800">Knowledge graph</strong> — Browse guests, topics, and
              content and how they connect across hundreds of posts and podcast episodes.
            </li>
            <li>
              <strong className="font-medium text-slate-800">Grounded explore</strong> — Ask a question and get an
              answer backed by retrieved excerpts you can inspect.
            </li>
            <li>
              <strong className="font-medium text-slate-800">Teaching modules</strong> — Request an outline, review
              it, then run streamed generation for a structured teaching modules and assessments with transparent step logs and grounded sources.
            </li>
          </ul>
        </section>

        <section aria-labelledby="about-corpus" className="rounded-2xl border border-indigo-100 bg-white/90 p-5 shadow-sm">
          <h2 id="about-corpus" className="text-lg font-semibold tracking-tight text-slate-900">
            Corpus and attribution 📚
          </h2>
          <p className="mt-2">
            The underlying library is a curated set of roughly six hundred thirty-eight newsletters and podcast
            transcripts from <strong className="font-medium text-slate-800">Lenny Rachitsky&apos;s</strong> public
            work. LennyVerse is an <strong className="font-medium text-slate-800">independent educational project</strong>
            ; it is not affiliated with or endorsed by Lenny or his properties. Use generated materials as drafts you
            review and adapt for your classroom.
          </p>
        </section>

        <section aria-labelledby="about-ethics" className="rounded-2xl border border-indigo-100 bg-white/90 p-5 shadow-sm">
          <h2 id="about-ethics" className="text-lg font-semibold tracking-tight text-slate-900">
            Ethics and mission 🌱
          </h2>
          <p className="mt-2">
            We built this to augment educators, not replace them. By providing transparent retrieval, visible generation steps, 
            and verifiable citations, we keep the human in the loop. While not formally sponsored by the university, 
            our design is rooted in Gonzaga-style mission framing: prioritizing care for the whole person, 
            ethical tech integration, and a commitment to service.
          </p>
        </section>

        <section aria-labelledby="about-tech" className="rounded-2xl border border-indigo-100 bg-white/90 p-5 shadow-sm">
          <h2 id="about-tech" className="text-lg font-semibold tracking-tight text-slate-900">
            How it&apos;s built 🛠️
          </h2>
          <p className="mt-2">
            A Vite and React frontend talks to a FastAPI backend. Content and vectors live in Postgres via Supabase
            (including pgvector). Language models are invoked through an OpenAI-compatible API so the stack can run
            on local or hosted inference without locking to a single vendor.
          </p>
        </section>
      </div>
    </section>
  );
}
