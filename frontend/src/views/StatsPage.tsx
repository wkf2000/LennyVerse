import * as d3 from "d3";
import { useEffect, useRef, useState } from "react";

import {
  fetchTopicTrends,
  fetchHeatmapData,
  fetchContentBreakdown,
  fetchTopGuests,
} from "../api/statsApi";
import type {
  TopicTrendsResponse,
  HeatmapResponse,
  ContentBreakdownResponse,
  TopGuestsResponse,
} from "../api/statsApi";
import HeatmapChart from "../components/stats/HeatmapChart";
import ContentBreakdownChart from "../components/stats/ContentBreakdownChart";
import GuestLeaderboard from "../components/stats/GuestLeaderboard";

const TOPIC_COLORS: Record<string, string> = {
  ai: "#6366f1",
  analytics: "#f59e0b",
  b2b: "#10b981",
  b2c: "#ef4444",
  career: "#8b5cf6",
  design: "#ec4899",
  engineering: "#14b8a6",
  "go-to-market": "#f97316",
  growth: "#22c55e",
  leadership: "#3b82f6",
  newsletter: "#a855f7",
  organization: "#78716c",
  podcast: "#06b6d4",
  pricing: "#eab308",
  "product-management": "#0ea5e9",
  startups: "#e11d48",
  strategy: "#64748b",
};

export default function StatsPage(): JSX.Element {
  const [trendsData, setTrendsData] = useState<TopicTrendsResponse | null>(null);
  const [heatmapData, setHeatmapData] = useState<HeatmapResponse | null>(null);
  const [breakdownData, setBreakdownData] = useState<ContentBreakdownResponse | null>(null);
  const [guestsData, setGuestsData] = useState<TopGuestsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | undefined>();
  const [selectedTopics, setSelectedTopics] = useState<Set<string>>(new Set());

  const svgRef = useRef<SVGSVGElement>(null);
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(undefined);

    Promise.all([
      fetchTopicTrends().catch(() => null),
      fetchHeatmapData().catch(() => null),
      fetchContentBreakdown().catch(() => null),
      fetchTopGuests().catch(() => null),
    ])
      .then(([trends, heatmap, breakdown, guests]) => {
        if (cancelled) return;
        if (trends) {
          setTrendsData(trends);
          const top5 = new Set(trends.summary.top_topics.slice(0, 5).map((t) => t.topic));
          setSelectedTopics(top5);
        }
        if (heatmap) setHeatmapData(heatmap);
        if (breakdown) setBreakdownData(breakdown);
        if (guests) setGuestsData(guests);

        if (!trends && !heatmap && !breakdown && !guests) {
          setError("Failed to load statistics.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  function toggleTopic(topic: string): void {
    setSelectedTopics((prev) => {
      const next = new Set(prev);
      if (next.has(topic)) {
        next.delete(topic);
      } else {
        next.add(topic);
      }
      return next;
    });
  }

  // D3 chart rendering
  useEffect(() => {
    if (!trendsData || !svgRef.current || !chartContainerRef.current) return;

    const containerWidth = chartContainerRef.current.clientWidth;
    const width = containerWidth;
    const height = 500;
    const margin = { top: 20, right: 30, bottom: 60, left: 60 };

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    svg.attr("width", width).attr("height", height);

    if (selectedTopics.size === 0) return;

    // Data transformation
    const allQuarters = Array.from(new Set(trendsData.trends.map((t) => t.quarter)));
    // quarters already sorted chronologically from backend

    const trendMap = new Map<string, Map<string, number>>();
    for (const item of trendsData.trends) {
      if (!trendMap.has(item.topic)) {
        trendMap.set(item.topic, new Map());
      }
      trendMap.get(item.topic)!.set(item.quarter, item.count);
    }

    const series: { topic: string; values: { quarter: string; count: number }[] }[] = [];
    let maxCount = 0;
    for (const topic of selectedTopics) {
      const topicMap = trendMap.get(topic) ?? new Map<string, number>();
      const values = allQuarters.map((q) => {
        const count = topicMap.get(q) ?? 0;
        if (count > maxCount) maxCount = count;
        return { quarter: q, count };
      });
      series.push({ topic, values });
    }

    // Scales
    const xScale = d3
      .scalePoint<string>()
      .domain(allQuarters)
      .range([margin.left, width - margin.right]);

    const yScale = d3
      .scaleLinear()
      .domain([0, Math.max(1, maxCount)])
      .range([height - margin.bottom, margin.top])
      .nice();

    // Grid lines
    const yTicks = yScale.ticks();
    svg
      .append("g")
      .selectAll("line")
      .data(yTicks)
      .join("line")
      .attr("x1", margin.left)
      .attr("x2", width - margin.right)
      .attr("y1", (d) => yScale(d))
      .attr("y2", (d) => yScale(d))
      .attr("stroke", "#e2e8f0")
      .attr("stroke-opacity", 0.5);

    // X axis
    const xAxis = d3.axisBottom(xScale);
    svg
      .append("g")
      .attr("transform", `translate(0,${height - margin.bottom})`)
      .call(xAxis)
      .call((g) => g.select(".domain").remove())
      .selectAll("text")
      .attr("transform", "rotate(-45)")
      .attr("text-anchor", "end")
      .style("font-size", "11px")
      .style("fill", "#64748b");

    // Y axis
    const yAxis = d3.axisLeft(yScale);
    svg
      .append("g")
      .attr("transform", `translate(${margin.left},0)`)
      .call(yAxis)
      .call((g) => g.select(".domain").remove())
      .selectAll("text")
      .style("font-size", "11px")
      .style("fill", "#64748b");

    // Lines
    const lineGen = d3
      .line<{ quarter: string; count: number }>()
      .x((d) => xScale(d.quarter)!)
      .y((d) => yScale(d.count))
      .curve(d3.curveMonotoneX);

    for (const s of series) {
      svg
        .append("path")
        .datum(s.values)
        .attr("d", lineGen)
        .attr("fill", "none")
        .attr("stroke", TOPIC_COLORS[s.topic] ?? "#94a3b8")
        .attr("stroke-width", 2);
    }

    // Tooltip vertical line
    const verticalLine = svg
      .append("line")
      .attr("y1", margin.top)
      .attr("y2", height - margin.bottom)
      .attr("stroke", "#94a3b8")
      .attr("stroke-width", 1)
      .attr("stroke-dasharray", "4,4")
      .style("opacity", 0);

    // Tooltip div
    const tooltip = d3.select(tooltipRef.current!);
    tooltip.style("opacity", "0");

    // Overlay for mouse events
    svg
      .append("rect")
      .attr("x", margin.left)
      .attr("y", margin.top)
      .attr("width", width - margin.left - margin.right)
      .attr("height", height - margin.top - margin.bottom)
      .attr("fill", "transparent")
      .on("mousemove", (event: MouseEvent) => {
        const [mx] = d3.pointer(event);
        // Find nearest quarter
        let nearestQuarter = allQuarters[0];
        let nearestDist = Infinity;
        for (const q of allQuarters) {
          const qx = xScale(q)!;
          const dist = Math.abs(mx - qx);
          if (dist < nearestDist) {
            nearestDist = dist;
            nearestQuarter = q;
          }
        }

        const qx = xScale(nearestQuarter)!;
        verticalLine.attr("x1", qx).attr("x2", qx).style("opacity", 1);

        // Build tooltip content
        const entries = series
          .map((s) => {
            const point = s.values.find((v) => v.quarter === nearestQuarter);
            return { topic: s.topic, count: point?.count ?? 0 };
          })
          .sort((a, b) => b.count - a.count);

        let html = `<div style="font-weight:600;margin-bottom:6px;color:#334155">${nearestQuarter}</div>`;
        for (const e of entries) {
          const color = TOPIC_COLORS[e.topic] ?? "#94a3b8";
          html += `<div style="display:flex;align-items:center;gap:6px;margin-bottom:2px">`;
          html += `<span style="display:inline-block;width:8px;height:8px;border-radius:9999px;background:${color};flex-shrink:0"></span>`;
          html += `<span style="color:#475569">${e.topic}</span>`;
          html += `<span style="margin-left:auto;font-weight:500;color:#1e293b">${e.count}</span>`;
          html += `</div>`;
        }

        const containerRect = chartContainerRef.current!.getBoundingClientRect();
        const svgRect = svgRef.current!.getBoundingClientRect();
        const tooltipX = qx + (svgRect.left - containerRect.left) + 12;
        const tooltipY = event.clientY - containerRect.top - 20;

        tooltip
          .html(html)
          .style("left", `${tooltipX}px`)
          .style("top", `${tooltipY}px`)
          .style("opacity", "1");
      })
      .on("mouseleave", () => {
        verticalLine.style("opacity", 0);
        tooltip.style("opacity", "0");
      });
  }, [trendsData, selectedTopics]);

  if (loading) {
    return (
      <div className="grid h-96 place-items-center text-sm text-slate-600">Loading statistics...</div>
    );
  }

  const startYear = trendsData ? trendsData.summary.date_range.start.slice(0, 4) : "";
  const endYear = trendsData ? trendsData.summary.date_range.end.slice(0, 4) : "";
  const hasDateRange = Boolean(startYear && endYear);
  const corpusLabel = trendsData
    ? `${trendsData.summary.total_content} total items (${trendsData.summary.total_podcasts} podcasts, ${trendsData.summary.total_newsletters} newsletters)`
    : "";

  return (
    <>
      <header className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-indigo-700">LennyVerse</p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">
          Content DNA Stats Dashboard
        </h1>
        <p className="mt-3 max-w-3xl text-sm text-slate-600">
          Publishing activity, content breakdown, top guests, and topic trends across {corpusLabel}
        </p>
      </header>

      {error ? (
        <div className="mb-4 rounded-md border border-rose-300 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>
      ) : null}

      {/* Summary cards */}
      {trendsData ? (
        <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
          <div className="rounded-xl border border-indigo-100 bg-white/90 p-4 shadow-sm shadow-indigo-100/70">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Total Content</p>
            <p className="mt-1 text-2xl font-semibold text-slate-900">{trendsData.summary.total_content}</p>
          </div>
          <div className="rounded-xl border border-indigo-100 bg-white/90 p-4 shadow-sm shadow-indigo-100/70">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Podcasts</p>
            <p className="mt-1 text-2xl font-semibold text-slate-900">{trendsData.summary.total_podcasts}</p>
          </div>
          <div className="rounded-xl border border-indigo-100 bg-white/90 p-4 shadow-sm shadow-indigo-100/70">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Newsletters</p>
            <p className="mt-1 text-2xl font-semibold text-slate-900">{trendsData.summary.total_newsletters}</p>
          </div>
          <div className="rounded-xl border border-indigo-100 bg-white/90 p-4 shadow-sm shadow-indigo-100/70">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Date Range</p>
            <p className="mt-1 text-2xl font-semibold text-slate-900">
              {hasDateRange ? `${startYear} - ${endYear}` : "N/A"}
            </p>
          </div>
        </div>
      ) : null}

      {/* Publishing Activity section */}
      <div className="mb-6">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Publishing Activity</h2>
        <div className="rounded-xl border border-indigo-100 bg-white/90 p-4 shadow-sm shadow-indigo-100/70">
          {heatmapData ? (
            <HeatmapChart data={heatmapData.items} />
          ) : (
            <div className="grid h-48 place-items-center text-sm text-slate-500">
              No publishing data available.
            </div>
          )}
        </div>
      </div>

      {/* Two-column grid: Content Breakdown + Top Guests */}
      <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Content Breakdown</h2>
          <div className="rounded-xl border border-indigo-100 bg-white/90 p-4 shadow-sm shadow-indigo-100/70">
            {breakdownData ? (
              <ContentBreakdownChart data={breakdownData.breakdown} />
            ) : (
              <div className="grid h-48 place-items-center text-sm text-slate-500">
                No content breakdown data available.
              </div>
            )}
          </div>
        </div>
        <div>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Top Guests</h2>
          <div className="rounded-xl border border-indigo-100 bg-white/90 p-4 shadow-sm shadow-indigo-100/70">
            {guestsData ? (
              <GuestLeaderboard data={guestsData.guests} />
            ) : (
              <div className="grid h-48 place-items-center text-sm text-slate-500">
                No guest data available.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Topic Trends section */}
      {trendsData ? (
        <div className="mb-6">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Topic Trends</h2>

          {/* Topic pill selector */}
          <div className="mb-4 flex flex-wrap gap-2">
            {trendsData.summary.top_topics.map((t) => {
              const isActive = selectedTopics.has(t.topic);
              const color = TOPIC_COLORS[t.topic] ?? "#94a3b8";
              return (
                <button
                  key={t.topic}
                  type="button"
                  className={`flex cursor-pointer items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-all duration-200 motion-reduce:transition-none motion-safe:hover:-translate-y-0.5 ${
                    isActive
                      ? "border-indigo-300 bg-indigo-100 text-indigo-900"
                      : "border-slate-300 text-slate-600 hover:border-indigo-200 hover:bg-indigo-50"
                  }`}
                  onClick={() => toggleTopic(t.topic)}
                >
                  <span
                    className="inline-block h-2 w-2 rounded-full"
                    style={{ background: color }}
                  />
                  {t.topic}
                </button>
              );
            })}
          </div>

          {/* D3 Line Chart */}
          <div
            ref={chartContainerRef}
            className="relative rounded-xl border border-indigo-100 bg-white/90 p-4 shadow-sm shadow-indigo-100/70"
          >
            {selectedTopics.size === 0 ? (
              <div className="grid h-96 place-items-center text-sm text-slate-500">
                Select at least one topic to see trends.
              </div>
            ) : (
              <svg ref={svgRef} className="w-full" />
            )}
            <div
              ref={tooltipRef}
              className="pointer-events-none absolute rounded-lg border border-slate-200 bg-white p-3 text-sm shadow-lg"
              style={{ opacity: 0 }}
            />
          </div>
        </div>
      ) : null}
    </>
  );
}
