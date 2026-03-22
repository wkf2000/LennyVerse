import { useMemo, useState } from "react";

import { GalaxyCanvas } from "@/features/galaxy/GalaxyCanvas";
import { GalaxyDetailDrawer } from "@/features/galaxy/GalaxyDetailDrawer";
import { GalaxyFilterPanel } from "@/features/galaxy/GalaxyFilterPanel";
import { GalaxyLegend } from "@/features/galaxy/GalaxyLegend";
import { defaultGalaxyFilters } from "@/features/galaxy/galaxyScene";
import { useGalaxyData } from "@/features/galaxy/useGalaxyData";

export function KnowledgeGalaxyPage() {
  const { loading, error, snapshot, reload } = useGalaxyData();
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [filters, setFilters] = useState(defaultGalaxyFilters);

  const selectedNode = useMemo(() => {
    if (!snapshot || !selectedNodeId) {
      return null;
    }
    return snapshot.nodes.find((node) => node.id === selectedNodeId) ?? null;
  }, [snapshot, selectedNodeId]);

  return (
    <main className="galaxy-page">
      <header className="galaxy-header">
        <h1 className="galaxy-title">Knowledge Galaxy</h1>
        <p>Explore all documents as a true 3D constellation.</p>
      </header>

      {loading ? (
        <div className="galaxy-status">Loading galaxy snapshot...</div>
      ) : error ? (
        <div className="galaxy-status">
          <p>Knowledge Galaxy is temporarily unavailable.</p>
          <p>{error}</p>
          <button type="button" onClick={() => void reload()}>
            Retry
          </button>
        </div>
      ) : snapshot ? (
        <>
          <section className="galaxy-layout">
            <GalaxyFilterPanel
              facets={snapshot.filter_facets}
              filters={filters}
              onChange={setFilters}
              onReset={() => setFilters(defaultGalaxyFilters())}
            />
            <div>
              <GalaxyCanvas snapshot={snapshot} filters={filters} onSelectNode={setSelectedNodeId} />
              <section className="galaxy-status" aria-live="polite">
                {selectedNode ? (
                  <>
                    <strong>{selectedNode.title}</strong>
                    <div>Source: {selectedNode.source_type}</div>
                    <div>Tags: {selectedNode.tags.join(", ") || "None"}</div>
                  </>
                ) : (
                  "Select a node to inspect details."
                )}
              </section>
            </div>
            <div>
              <GalaxyDetailDrawer nodeId={selectedNodeId} />
              <GalaxyLegend />
            </div>
          </section>
        </>
      ) : (
        <div className="galaxy-status">No data available.</div>
      )}
    </main>
  );
}
