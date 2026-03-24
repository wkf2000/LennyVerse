import { useEffect, useMemo, useState } from "react";

import { fetchGraph, fetchNodeDetail } from "./api/graphApi";
import GraphCanvas from "./components/GraphCanvas";
import type { GraphResponse, NodeDetail, NodeType } from "./types/graph";

const INITIAL_GRAPH: GraphResponse = {
  nodes: [],
  edges: [],
};

const NODE_TYPE_ORDER: NodeType[] = ["guest", "topic", "content", "concept"];

export default function App(): JSX.Element {
  const [graphData, setGraphData] = useState<GraphResponse>(INITIAL_GRAPH);
  const [selectedNodeId, setSelectedNodeId] = useState<string>();
  const [selectedNodeDetail, setSelectedNodeDetail] = useState<NodeDetail | null>(null);
  const [graphLoading, setGraphLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [graphError, setGraphError] = useState<string>();
  const [searchTerm, setSearchTerm] = useState("");
  const [topicFilter, setTopicFilter] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [nodeTypes, setNodeTypes] = useState<NodeType[]>(["guest", "topic", "content"]);

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

  const graphStats = useMemo(
    () => ({
      nodes: graphData.nodes.length,
      edges: graphData.edges.length,
    }),
    [graphData.edges.length, graphData.nodes.length],
  );

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
    <main className="min-h-screen bg-slate-950 px-6 py-6 text-slate-100">
      <header className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Lenny&apos;s Teaching Assistant</h1>
          <p className="mt-1 text-sm text-slate-400">
            638 episodes and posts. One knowledge graph. Your next syllabus.
          </p>
        </div>
        <div className="flex gap-6 text-sm text-slate-300">
          <span>{graphStats.nodes} nodes</span>
          <span>{graphStats.edges} edges</span>
        </div>
      </header>

      <section className="mb-4 grid gap-3 rounded-xl border border-slate-800 bg-slate-900/70 p-4 md:grid-cols-6">
        <label className="md:col-span-2">
          <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400">
            Search nodes
          </span>
          <input
            className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-cyan-400"
            placeholder="Type a guest, topic, or title..."
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
          />
        </label>

        <label>
          <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400">
            Topic filter
          </span>
          <input
            className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-cyan-400"
            placeholder="growth"
            value={topicFilter}
            onChange={(event) => setTopicFilter(event.target.value)}
          />
        </label>

        <label>
          <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400">
            Start date
          </span>
          <input
            type="date"
            className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-cyan-400"
            value={startDate}
            onChange={(event) => setStartDate(event.target.value)}
          />
        </label>

        <label>
          <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400">
            End date
          </span>
          <input
            type="date"
            className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-cyan-400"
            value={endDate}
            onChange={(event) => setEndDate(event.target.value)}
          />
        </label>

        <div>
          <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400">
            Node types
          </span>
          <div className="flex flex-wrap gap-2 pt-1">
            {NODE_TYPE_ORDER.map((type) => (
              <button
                key={type}
                type="button"
                className={`rounded-full border px-2.5 py-1 text-xs font-medium capitalize transition ${
                  nodeTypes.includes(type)
                    ? "border-cyan-400 bg-cyan-500/20 text-cyan-100"
                    : "border-slate-700 text-slate-300 hover:border-slate-500"
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
        <div className="mb-4 rounded-md border border-rose-500/60 bg-rose-950/40 p-3 text-sm text-rose-200">
          {graphError}
        </div>
      ) : null}

      <section className="grid h-[76vh] grid-cols-1 gap-4 lg:grid-cols-[1fr_360px]">
        <div className="relative">
          {graphLoading ? (
            <div className="absolute inset-0 z-10 grid place-items-center rounded-xl border border-slate-700 bg-slate-950/85 text-slate-300">
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
        </div>

        <aside className="h-full rounded-xl border border-slate-800 bg-slate-900/70 p-4">
          {!selectedNodeId ? (
            <div className="grid h-full place-items-center text-center text-sm text-slate-400">
              Click a node to inspect details and related content.
            </div>
          ) : detailLoading ? (
            <div className="text-sm text-slate-300">Loading node details...</div>
          ) : !selectedNodeDetail ? (
            <div className="text-sm text-slate-300">No detail available for this node.</div>
          ) : (
            <div className="h-full overflow-y-auto">
              <h2 className="text-xl font-semibold">{selectedNodeDetail.node.label}</h2>
              <p className="mt-1 text-xs uppercase tracking-wide text-slate-400">
                {selectedNodeDetail.node.type}
              </p>
              <p className="mt-3 text-sm text-slate-300">
                Connected nodes: {selectedNodeDetail.connected_node_count}
              </p>

              <div className="mt-5">
                <h3 className="text-sm font-semibold text-slate-200">Related content</h3>
                <ul className="mt-2 space-y-2">
                  {selectedNodeDetail.related_content.length === 0 ? (
                    <li className="rounded-md border border-slate-800 bg-slate-950/60 p-2 text-sm text-slate-400">
                      No related content rows available.
                    </li>
                  ) : (
                    selectedNodeDetail.related_content.map((item) => (
                      <li key={item.id} className="rounded-md border border-slate-800 bg-slate-950/60 p-2">
                        <p className="text-sm font-medium text-slate-100">{item.title}</p>
                        <p className="mt-1 text-xs text-slate-400">
                          {item.content_type}
                          {item.published_at ? ` · ${item.published_at}` : ""}
                        </p>
                        {item.guest ? <p className="mt-1 text-xs text-slate-400">Guest: {item.guest}</p> : null}
                      </li>
                    ))
                  )}
                </ul>
              </div>
            </div>
          )}
        </aside>
      </section>
    </main>
  );
}
