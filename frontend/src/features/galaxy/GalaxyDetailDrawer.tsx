import { useEffect, useState } from "react";

import { fetchGalaxyNodeDetailWithRetry } from "@/features/galaxy/integration/galaxyApi";
import type { GalaxyNodeDetail } from "@/features/galaxy/types";

interface GalaxyDetailDrawerProps {
  nodeId: string | null;
}

export function GalaxyDetailDrawer({ nodeId }: GalaxyDetailDrawerProps) {
  const [detail, setDetail] = useState<GalaxyNodeDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!nodeId) {
      setDetail(null);
      setError(null);
      setLoading(false);
      return;
    }

    let active = true;
    const run = async () => {
      setLoading(true);
      setError(null);
      if (!active) {
        return;
      }
      try {
        const result = await fetchGalaxyNodeDetailWithRetry(nodeId);
        if (!active) {
          return;
        }
        setDetail(result);
      } catch {
        setDetail(null);
        setError("Failed to load node details. Please try again.");
      }
      setLoading(false);
    };
    void run();

    return () => {
      active = false;
    };
  }, [nodeId]);

  return (
    <aside className="galaxy-status" aria-label="Galaxy detail drawer">
      <h2>Detail</h2>
      {!nodeId ? (
        <p>Select a node to inspect details.</p>
      ) : loading ? (
        <p>Loading node details...</p>
      ) : error ? (
        <p>{error}</p>
      ) : detail ? (
        <>
          <strong>{detail.title}</strong>
          <div>Source: {detail.source_type}</div>
          <div>Guests: {detail.guest_names.join(", ") || "None"}</div>
          <div>Tags: {detail.tags.join(", ") || "None"}</div>
          <a href={detail.reader_url}>Open full document</a>
        </>
      ) : (
        <p>No details available.</p>
      )}
    </aside>
  );
}
