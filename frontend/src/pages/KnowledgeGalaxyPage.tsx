import { useMemo, useState } from "react";

import { PrdAppNavigation } from "@/components/PrdAppNavigation";
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
    <div className="lv-app">
      <PrdAppNavigation />
      <main className="galaxy-page">
        <header className="galaxy-header">
          <p className="galaxy-eyebrow">VIZ-1 · Data visualization</p>
          <h1 className="galaxy-title">Knowledge Galaxy</h1>
          <p className="galaxy-subtitle">638 documents as a living 3D constellation — zoom, filter, follow the threads.</p>
        </header>

        {loading ? (
          <div className="galaxy-status galaxy-status--pulse">Loading galaxy snapshot…</div>
        ) : error ? (
          <div className="galaxy-status galaxy-status--error">
            <p>Knowledge Galaxy is temporarily unavailable.</p>
            <p>{error}</p>
            <button type="button" className="lv-btn lv-btn--primary" onClick={() => void reload()}>
              Retry
            </button>
          </div>
        ) : snapshot ? (
          <section className="galaxy-layout">
            <GalaxyFilterPanel
              facets={snapshot.filter_facets}
              filters={filters}
              onChange={setFilters}
              onReset={() => setFilters(defaultGalaxyFilters())}
            />
            <div className="galaxy-main-column">
              <GalaxyCanvas snapshot={snapshot} filters={filters} onSelectNode={setSelectedNodeId} />
              <p className="galaxy-canvas-hint" aria-live="polite">
                {selectedNode ? (
                  <>
                    Selected: <strong>{selectedNode.title}</strong>
                    <span className="galaxy-canvas-hint__meta"> — see the right panel for full detail</span>
                  </>
                ) : (
                  <>Drag to orbit · scroll to zoom · click a star to inspect</>
                )}
              </p>
            </div>
            <div className="galaxy-side-column">
              <GalaxyDetailDrawer nodeId={selectedNodeId} />
              <GalaxyLegend />
            </div>
          </section>
        ) : (
          <div className="galaxy-status">No data available.</div>
        )}
      </main>
    </div>
  );
}
