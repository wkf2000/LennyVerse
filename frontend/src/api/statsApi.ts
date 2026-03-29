const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export interface TopicTrendItem {
  quarter: string;
  topic: string;
  count: number;
}

export interface TopicCount {
  topic: string;
  count: number;
}

export interface DateRange {
  start: string;
  end: string;
}

export interface StatsSummary {
  total_content: number;
  total_podcasts: number;
  total_newsletters: number;
  date_range: DateRange;
  top_topics: TopicCount[];
}

export interface TopicTrendsResponse {
  trends: TopicTrendItem[];
  summary: StatsSummary;
}

export async function fetchTopicTrends(): Promise<TopicTrendsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/stats/topic-trends`);
  if (!response.ok) {
    throw new Error(`Failed to load statistics (${response.status})`);
  }
  return (await response.json()) as TopicTrendsResponse;
}

export interface HeatmapItem {
  year: number;
  week: number;
  type: string;
  title: string;
  published_at: string;
}

export interface HeatmapResponse {
  items: HeatmapItem[];
}

export interface ContentBreakdownItem {
  quarter: string;
  type: string;
  count: number;
  avg_word_count: number;
}

export interface ContentBreakdownResponse {
  breakdown: ContentBreakdownItem[];
}

export interface GuestCountItem {
  guest: string;
  count: number;
}

export interface TopGuestsResponse {
  guests: GuestCountItem[];
}

export async function fetchHeatmapData(): Promise<HeatmapResponse> {
  const response = await fetch(`${API_BASE_URL}/api/stats/heatmap`);
  if (!response.ok) {
    throw new Error(`Failed to load heatmap data (${response.status})`);
  }
  return (await response.json()) as HeatmapResponse;
}

export async function fetchContentBreakdown(): Promise<ContentBreakdownResponse> {
  const response = await fetch(`${API_BASE_URL}/api/stats/content-breakdown`);
  if (!response.ok) {
    throw new Error(`Failed to load content breakdown (${response.status})`);
  }
  return (await response.json()) as ContentBreakdownResponse;
}

export async function fetchTopGuests(): Promise<TopGuestsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/stats/top-guests`);
  if (!response.ok) {
    throw new Error(`Failed to load top guests (${response.status})`);
  }
  return (await response.json()) as TopGuestsResponse;
}
