import { useEffect, useMemo, useState } from "react";

import { fetchContentSummary, fetchGraph, fetchNodeDetail } from "./api/graphApi";
import GraphCanvas from "./components/GraphCanvas";
import SearchWorkspace from "./components/search/SearchWorkspace";
import type { GraphResponse, NodeDetail, NodeType } from "./types/graph";
import AboutPage from "./views/AboutPage";
import GenerateWorkspace from "./views/GenerateWorkspace";
import StatsPage from "./views/StatsPage";

const INITIAL_GRAPH: GraphResponse = {
  nodes: [],
  edges: [],
};

const NODE_TYPE_ORDER: NodeType[] = ["guest", "topic", "content", "concept"];
const MAX_RELATED_CONTENT_ITEMS = 5;
const VIEWS = ["graph", "stats", "explore", "generate", "about"] as const;
const NAV_VIEWS = ["graph", "stats", "explore", "generate", "about"] as const;

type View = (typeof VIEWS)[number];

const VIEW_PATHS: Record<View, string> = {
  graph: "/",
  explore: "/explore",
  generate: "/generate",
  stats: "/stats",
  about: "/about",
};
const VIEW_LABELS: Record<View, string> = {
  graph: "visualization",
  explore: "explore",
  generate: "generate",
  stats: "stats",
  about: "about",
};

function normalizePathname(pathname: string): string {
  if (pathname.length > 1 && pathname.endsWith("/")) {
    return pathname.replace(/\/+$/, "") || "/";
  }
  return pathname;
}

function viewFromPathname(pathname: string): View {
  const path = normalizePathname(pathname);
  for (const view of VIEWS) {
    if (VIEW_PATHS[view] === path) {
      return view;
    }
  }
  return "graph";
}

function formatDateInputValue(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function getInitialDateRange(): { startDate: string; endDate: string } {
  const end = new Date();
  const start = new Date(end);
  start.setMonth(start.getMonth() - 2);
  return {
    startDate: formatDateInputValue(start),
    endDate: formatDateInputValue(end),
  };
}

export default function App(): JSX.Element {
  const initialDateRange = getInitialDateRange();
  const [graphData, setGraphData] = useState<GraphResponse>(INITIAL_GRAPH);
  const [selectedNodeId, setSelectedNodeId] = useState<string>();
  const [selectedNodeDetail, setSelectedNodeDetail] = useState<NodeDetail | null>(null);
  const [graphLoading, setGraphLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [graphError, setGraphError] = useState<string>();
  const [searchTerm, setSearchTerm] = useState("");
  const [topicFilter, setTopicFilter] = useState("");
  const [startDate, setStartDate] = useState(initialDateRange.startDate);
  const [endDate, setEndDate] = useState(initialDateRange.endDate);
  const [nodeTypes, setNodeTypes] = useState<NodeType[]>(["guest", "topic", "content"]);
  const [activeView, setActiveView] = useState<View>(() => viewFromPathname(window.location.pathname));
  const [showHeroCopy, setShowHeroCopy] = useState(false);
  const [summaryPopup, setSummaryPopup] = useState<{ title: string; summary: string | null; loading: boolean } | null>(null);

  useEffect(() => {
    const handlePopState = (): void => {
      setActiveView(viewFromPathname(window.location.pathname));
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  function goToView(view: View): void {
    const target = VIEW_PATHS[view];
    if (normalizePathname(window.location.pathname) !== target) {
      window.history.pushState(null, "", target);
    }
    setActiveView(view);
  }

  useEffect(() => {
    let cancelled = false;
    setGraphLoading(true);
    setGraphError(undefined);

    fetchGraph({
      nodeTypes,
      topic: topicFilter.trim() || undefined,
      startDate: startDate || undefined,
      endDate: endDate || undefined,
    })
      .then((payload) => {
        if (cancelled) {
          return;
        }
        setGraphData(payload);
        if (selectedNodeId && !payload.nodes.some((node) => node.id === selectedNodeId)) {
          setSelectedNodeId(undefined);
          setSelectedNodeDetail(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setGraphError(error instanceof Error ? error.message : "Failed to load graph data.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setGraphLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [endDate, nodeTypes, selectedNodeId, startDate, topicFilter]);

  useEffect(() => {
    if (!selectedNodeId) {
      setSelectedNodeDetail(null);
      return;
    }
    let cancelled = false;
    setDetailLoading(true);
    fetchNodeDetail(selectedNodeId)
      .then((payload) => {
        if (!cancelled) {
          setSelectedNodeDetail(payload);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setSelectedNodeDetail(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setDetailLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedNodeId]);

  useEffect(() => {
    if (graphLoading) {
      setShowHeroCopy(false);
      return;
    }
    const timeout = window.setTimeout(() => setShowHeroCopy(true), 900);
    return () => window.clearTimeout(timeout);
  }, [graphLoading]);

  const graphStats = useMemo(
    () => ({
      nodes: graphData.nodes.length,
      edges: graphData.edges.length,
    }),
    [graphData.edges.length, graphData.nodes.length],
  );

  function handleContentClick(contentId: string, title: string): void {
    setSummaryPopup({ title, summary: null, loading: true });
    fetchContentSummary(contentId)
      .then((result) => {
        setSummaryPopup({ title, summary: result.summary, loading: false });
      })
      .catch(() => {
        setSummaryPopup({ title, summary: null, loading: false });
      });
  }

  function toggleNodeType(type: NodeType): void {
    setNodeTypes((current) => {
      if (current.includes(type)) {
        if (current.length === 1) {
          return current;
        }
        return current.filter((nodeType) => nodeType !== type);
      }
      return [...current, type];
    });
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#f4f7ff] text-slate-900">
      <div className="pointer-events-none absolute -left-24 top-20 h-64 w-64 rounded-full bg-indigo-200/50 blur-3xl motion-safe:animate-pulse" />
      <div className="pointer-events-none absolute -right-20 top-64 h-72 w-72 rounded-full bg-emerald-200/50 blur-3xl motion-safe:animate-pulse" />
      <div className="pointer-events-none absolute bottom-12 left-1/3 h-56 w-56 rounded-full bg-sky-200/40 blur-3xl motion-safe:animate-pulse" />

      <nav className="fixed right-4 top-4 z-50">
        <div className="flex items-center gap-1 rounded-full border border-indigo-200/80 bg-white/90 p-1 shadow-md shadow-indigo-100/70 backdrop-blur">
          {NAV_VIEWS.map((view) => {
            const isActive = activeView === view;
            return (
              <button
                key={view}
                type="button"
                aria-current={isActive ? "page" : undefined}
                className={`cursor-pointer rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-wide transition-all duration-200 motion-reduce:transition-none motion-safe:hover:-translate-y-0.5 ${
                  isActive
                    ? "bg-slate-900 text-indigo-50 shadow-sm shadow-indigo-300/40"
                    : "text-slate-600 hover:bg-indigo-50 hover:text-indigo-700 hover:shadow-sm hover:shadow-indigo-200/60"
                }`}
                onClick={() => goToView(view)}
              >
                {VIEW_LABELS[view]}
              </button>
            );
          })}
        </div>
      </nav>

      {activeView === "graph" ? (
        <section className="mx-auto max-w-7xl px-4 pb-8 pt-24 sm:px-6 lg:px-8">
          <header className="mb-5 flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-indigo-700">LennyVerse ✨</p>
              <h1 className="mt-2 text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">
                One knowledge graph for modern teaching
              </h1>
              <p className="mt-3 max-w-3xl text-sm text-slate-600">
                Explore 638 podcasts and newsletters with a graph-first view built for clarity, discovery, and course design
              </p>
            </div>
            <div className="flex gap-5 rounded-full border border-indigo-200 bg-indigo-50/90 px-4 py-2 text-sm text-slate-700 shadow-sm shadow-indigo-100">
              <span>{graphStats.nodes} nodes</span>
              <span>{graphStats.edges} edges</span>
            </div>
          </header>

          <section className="mb-4 grid gap-3 rounded-2xl border border-indigo-100 bg-white/90 p-4 shadow-sm shadow-indigo-100/70 backdrop-blur md:grid-cols-6">
            <label className="md:col-span-2">
              <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                Search nodes
              </span>
              <input
                className="w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none transition-colors duration-200 focus:border-indigo-400 focus:bg-white motion-reduce:transition-none"
                placeholder="Type a guest, topic, or title..."
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
              />
            </label>

            <label>
              <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                Topic filter
              </span>
              <input
                className="w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none transition-colors duration-200 focus:border-indigo-400 focus:bg-white motion-reduce:transition-none"
                placeholder="growth"
                value={topicFilter}
                onChange={(event) => setTopicFilter(event.target.value)}
              />
            </label>

            <label>
              <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                Start date
              </span>
              <input
                type="date"
                className="w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none transition-colors duration-200 focus:border-indigo-400 focus:bg-white motion-reduce:transition-none"
                value={startDate}
                onChange={(event) => setStartDate(event.target.value)}
              />
            </label>

            <label>
              <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                End date
              </span>
              <input
                type="date"
                className="w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none transition-colors duration-200 focus:border-indigo-400 focus:bg-white motion-reduce:transition-none"
                value={endDate}
                onChange={(event) => setEndDate(event.target.value)}
              />
            </label>

            <div>
              <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                Node types
              </span>
              <div className="flex flex-wrap gap-2 pt-1">
                {NODE_TYPE_ORDER.map((type) => (
                  <button
                    key={type}
                    type="button"
                    className={`cursor-pointer rounded-full border px-2.5 py-1 text-xs font-medium capitalize transition-all duration-200 motion-reduce:transition-none motion-safe:hover:-translate-y-0.5 ${
                      nodeTypes.includes(type)
                        ? "border-indigo-300 bg-indigo-100 text-indigo-900"
                        : "border-slate-300 text-slate-600 hover:border-indigo-200 hover:bg-indigo-50 hover:shadow-sm hover:shadow-indigo-200/50"
                    }`}
                    onClick={() => toggleNodeType(type)}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>
          </section>

          {graphError ? (
            <div className="mb-4 rounded-md border border-rose-300 bg-rose-50 p-3 text-sm text-rose-700">{graphError}</div>
          ) : null}

          <section className="grid h-[76vh] grid-cols-1 gap-4 lg:grid-cols-[1fr_360px]">
            <div className="relative">
              {graphLoading ? (
                <div className="absolute inset-0 z-10 grid place-items-center rounded-xl border border-slate-700 bg-slate-950/85 text-amber-100">
                  Loading graph...
                </div>
              ) : null}
              <GraphCanvas
                nodes={graphData.nodes}
                edges={graphData.edges}
                selectedNodeId={selectedNodeId}
                searchTerm={searchTerm}
                onNodeSelect={setSelectedNodeId}
              />
              <div
                className={`pointer-events-none absolute left-4 top-4 max-w-lg rounded-2xl border border-indigo-200/30 bg-indigo-950/70 p-4 text-indigo-50 backdrop-blur transition-opacity duration-500 motion-reduce:transition-none ${
                  showHeroCopy ? "opacity-100" : "opacity-0"
                }`}
              >
                <p className="text-xs uppercase tracking-[0.2em] text-indigo-200/90">Data Visualization Hero</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight">Lenny&apos;s intellectual universe</h2>
                <p className="mt-2 text-sm text-indigo-50/80">
                  638 episodes and posts, one knowledge graph, your next syllabus 🌿
                </p>
              </div>
            </div>

            <aside className="h-full rounded-xl border border-indigo-100 bg-white/95 p-4 shadow-sm shadow-indigo-100/70">
              {!selectedNodeId ? (
                <div className="grid h-full place-items-center text-center text-sm text-slate-500">
                  Click a node to inspect details and related content.
                </div>
              ) : detailLoading ? (
                <div className="text-sm text-slate-600">Loading node details...</div>
              ) : !selectedNodeDetail ? (
                <div className="text-sm text-slate-600">No detail available for this node.</div>
              ) : (
                <div className="h-full overflow-y-auto">
                  <h2 className="text-xl font-semibold text-slate-900">{selectedNodeDetail.node.label}</h2>
                  <p className="mt-1 text-xs uppercase tracking-wide text-slate-500">{selectedNodeDetail.node.type}</p>
                  <p className="mt-3 text-sm text-slate-700">
                    Connected nodes: {selectedNodeDetail.connected_node_count}
                  </p>

                  <div className="mt-5">
                    <h3 className="text-sm font-semibold text-slate-900">Related content</h3>
                    {selectedNodeDetail.related_content.length > MAX_RELATED_CONTENT_ITEMS ? (
                      <p className="mt-1 text-xs text-slate-500">
                        Showing top {MAX_RELATED_CONTENT_ITEMS} of {selectedNodeDetail.related_content.length}
                      </p>
                    ) : null}
                    <ul className="mt-2 space-y-2">
                      {selectedNodeDetail.related_content.length === 0 ? (
                        <li className="rounded-md border border-slate-200 bg-slate-50 p-2 text-sm text-slate-500">
                          No related content rows available.
                        </li>
                      ) : (
                        selectedNodeDetail.related_content.slice(0, MAX_RELATED_CONTENT_ITEMS).map((item) => (
                          <li
                            key={item.id}
                            className="cursor-pointer rounded-md border border-slate-200 bg-white p-2 transition-colors hover:border-indigo-300 hover:bg-indigo-50/50"
                            onClick={() => handleContentClick(item.id, item.title)}
                          >
                            <p className="text-sm font-medium text-slate-900">{item.title}</p>
                            <p className="mt-1 text-xs text-slate-500">
                              {item.content_type}
                              {item.published_at ? ` · ${item.published_at}` : ""}
                            </p>
                            {item.guest ? <p className="mt-1 text-xs text-slate-500">Guest: {item.guest}</p> : null}
                            <p className="mt-1 text-xs text-indigo-500">Click to view summary</p>
                          </li>
                        ))
                      )}
                    </ul>
                  </div>
                </div>
              )}
            </aside>
          </section>
        </section>
      ) : activeView === "explore" ? (
        <section className="mx-auto max-w-7xl px-4 pb-8 pt-24 sm:px-6 lg:px-8">
          <header className="mb-6">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-indigo-700">LennyVerse 🔎</p>
            <h1 className="mt-2 text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">
              Explore the archive with grounded answers
            </h1>
            <p className="mt-3 max-w-3xl text-sm text-slate-600">
              Ask a question, discover sources, stream a cited answer, and inspect excerpts side-by-side
            </p>
          </header>
          <SearchWorkspace />
        </section>
      ) : activeView === "generate" ? (
        <section className="mx-auto max-w-7xl px-4 pb-8 pt-24 sm:px-6 lg:px-8">
          <header className="mb-6">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-indigo-700">LennyVerse 🧠</p>
            <h1 className="mt-2 text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">
              Build a syllabus and quiz from the archive
            </h1>
            <p className="mt-3 max-w-3xl text-sm text-slate-600">
              Generate a course outline first, review it, then run full syllabus and assessment generation with
              transparent step logs and grounded sources
            </p>
          </header>
          <GenerateWorkspace />
        </section>
      ) : activeView === "stats" ? (
        <section className="mx-auto max-w-7xl px-4 pb-8 pt-24 sm:px-6 lg:px-8">
          <StatsPage />
        </section>
      ) : activeView === "about" ? (
        <AboutPage />
      ) : null}

      {summaryPopup ? (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-black/40 backdrop-blur-sm"
          onClick={() => setSummaryPopup(null)}
        >
          <div
            className="mx-4 max-h-[80vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-indigo-200 bg-white p-6 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-3">
              <h3 className="text-lg font-semibold text-slate-900">{summaryPopup.title}</h3>
              <button
                type="button"
                className="shrink-0 cursor-pointer rounded-full p-1 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
                onClick={() => setSummaryPopup(null)}
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </button>
            </div>
            <div className="mt-4">
              {summaryPopup.loading ? (
                <p className="text-sm text-slate-500">Loading summary...</p>
              ) : summaryPopup.summary ? (
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{summaryPopup.summary}</p>
              ) : (
                <p className="text-sm text-slate-500">No summary available for this content.</p>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
