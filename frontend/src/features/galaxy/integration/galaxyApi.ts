import type { GalaxyNodeDetail, GalaxySnapshot } from "@/features/galaxy/types";

export const REQUIRED_GALAXY_SCHEMA_VERSION = 1;

export async function fetchGalaxySnapshot(): Promise<GalaxySnapshot> {
  const response = await fetch("/api/v1/galaxy/snapshot");
  if (!response.ok) {
    throw new Error(`Snapshot request failed (${response.status})`);
  }
  const payload = (await response.json()) as GalaxySnapshot;
  if (payload.schema_version !== REQUIRED_GALAXY_SCHEMA_VERSION) {
    throw new Error(`Unsupported schema version: ${payload.schema_version}`);
  }
  return payload;
}

export async function fetchGalaxyNodeDetail(nodeId: string): Promise<GalaxyNodeDetail> {
  const response = await fetch(`/api/v1/galaxy/node/${encodeURIComponent(nodeId)}`);
  if (!response.ok) {
    throw new Error(`Node detail request failed (${response.status})`);
  }
  return (await response.json()) as GalaxyNodeDetail;
}

export async function fetchGalaxyNodeDetailWithRetry(nodeId: string): Promise<GalaxyNodeDetail> {
  const first = await tryFetchNodeWithTimeout(nodeId);
  if (first !== null) {
    return first;
  }
  const second = await tryFetchNodeWithTimeout(nodeId);
  if (second !== null) {
    return second;
  }
  throw new Error("Failed to load node details. Please try again.");
}

async function tryFetchNodeWithTimeout(nodeId: string): Promise<GalaxyNodeDetail | null> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 3000);
  try {
    const response = await fetch(`/api/v1/galaxy/node/${encodeURIComponent(nodeId)}`, { signal: controller.signal });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as GalaxyNodeDetail;
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}
