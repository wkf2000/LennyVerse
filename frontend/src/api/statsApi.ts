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
