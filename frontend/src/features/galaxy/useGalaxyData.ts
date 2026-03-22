import { useCallback, useEffect, useState } from "react";

import { fetchGalaxySnapshot } from "@/features/galaxy/integration/galaxyApi";
import type { GalaxySnapshot } from "@/features/galaxy/types";

interface UseGalaxyDataResult {
  loading: boolean;
  error: string | null;
  snapshot: GalaxySnapshot | null;
  reload: () => Promise<void>;
}

export function useGalaxyData(): UseGalaxyDataResult {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [snapshot, setSnapshot] = useState<GalaxySnapshot | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = await fetchGalaxySnapshot();
      setSnapshot(payload);
    } catch (err) {
      setSnapshot(null);
      setError(err instanceof Error ? err.message : "Unknown snapshot load error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return { loading, error, snapshot, reload: load };
}
