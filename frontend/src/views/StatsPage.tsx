import * as d3 from "d3";
import { useEffect, useRef, useState } from "react";

import {
  fetchTopicTrends,
  fetchHeatmapData,
  fetchContentBreakdown,
} from "../api/statsApi";
import type {
  TopicTrendsResponse,
  HeatmapResponse,
  ContentBreakdownResponse,
} from "../api/statsApi";
import HeatmapChart from "../components/stats/HeatmapChart";
import ContentBreakdownChart from "../components/stats/ContentBreakdownChart";

function FeatureIconPlaybook(): JSX.Element {
  return (
    <svg className="h-8 w-8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
    </svg>
  );
}

function FeatureIconGraph(): JSX.Element {
  return (
    <svg className="h-8 w-8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244" />
    </svg>
  );
}

function FeatureIconAsk(): JSX.Element {
  return (
    <svg className="h-8 w-8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 01-.825-.242m9.345-8.334a2.126 2.126 0 00-.476-.095 48.64 48.64 0 00-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0011.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155" />
    </svg>
  );
}

function FeatureIconInsights(): JSX.Element {
  return (
    <svg className="h-8 w-8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
    </svg>
  );
}

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
    ])
      .then(([trends, heatmap, breakdown]) => {
        if (cancelled) return;
        if (trends) {
          setTrendsData(trends);
          const top5 = new Set(trends.summary.top_topics.slice(0, 5).map((t) => t.topic));
          setSelectedTopics(top5);
        }
        if (heatmap) setHeatmapData(heatmap);
        if (breakdown) setBreakdownData(breakdown);

        if (!trends && !heatmap && !breakdown) {
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

  return (
    <>
      <header className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-indigo-700">LennyVerse</p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">
          About LennyVerse
        </h1>
        <p className="mt-3 max-w-3xl text-sm text-slate-600">
          A knowledge engine built on Lenny Rachitsky&apos;s archive of 638 podcast episodes and 350+ newsletter posts
        </p>
      </header>

      <section className="mb-14" aria-labelledby="about-features-heading">
        <div className="mb-8 max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-600">What you can do</p>
          <h2 id="about-features-heading" className="mt-2 text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
            Features
          </h2>
          <p className="mt-2 text-base leading-relaxed text-slate-600">
            Four ways to work with Lenny&apos;s archive — from tailored playbooks to corpus-level analytics.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <article className="group flex min-h-[220px] flex-col rounded-2xl border border-indigo-100/90 bg-white/95 p-8 shadow-sm shadow-indigo-100/50 transition-shadow duration-200 motion-reduce:transition-none motion-safe:hover:shadow-md motion-safe:hover:shadow-indigo-200/60">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 transition-colors duration-200 group-hover:bg-indigo-100 motion-reduce:transition-none">
              <FeatureIconPlaybook />
            </div>
            <h3 className="mt-5 text-xl font-semibold tracking-tight text-slate-900">Playbook</h3>
            <p className="mt-3 flex-1 text-base leading-relaxed text-slate-600">
              Get an actionable, personalized plan grounded in Lenny&apos;s archive — tailored to your role, stage, and
              challenge.
            </p>
          </article>

          <article className="group flex min-h-[220px] flex-col rounded-2xl border border-indigo-100/90 bg-white/95 p-8 shadow-sm shadow-indigo-100/50 transition-shadow duration-200 motion-reduce:transition-none motion-safe:hover:shadow-md motion-safe:hover:shadow-indigo-200/60">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 transition-colors duration-200 group-hover:bg-indigo-100 motion-reduce:transition-none">
              <FeatureIconGraph />
            </div>
            <h3 className="mt-5 text-xl font-semibold tracking-tight text-slate-900">Knowledge graph</h3>
            <p className="mt-3 flex-1 text-base leading-relaxed text-slate-600">
              Explore how guests, topics, frameworks, and episodes connect — visualized as an interactive graph you can
              navigate.
            </p>
          </article>

          <article className="group flex min-h-[220px] flex-col rounded-2xl border border-indigo-100/90 bg-white/95 p-8 shadow-sm shadow-indigo-100/50 transition-shadow duration-200 motion-reduce:transition-none motion-safe:hover:shadow-md motion-safe:hover:shadow-indigo-200/60">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 transition-colors duration-200 group-hover:bg-indigo-100 motion-reduce:transition-none">
              <FeatureIconAsk />
            </div>
            <h3 className="mt-5 text-xl font-semibold tracking-tight text-slate-900">Ask the archive</h3>
            <p className="mt-3 flex-1 text-base leading-relaxed text-slate-600">
              Ask anything across the full corpus and get answers grounded in real episodes and newsletters — with
              citations you can verify.
            </p>
          </article>

          <article className="group flex min-h-[220px] flex-col rounded-2xl border border-indigo-100/90 bg-white/95 p-8 shadow-sm shadow-indigo-100/50 transition-shadow duration-200 motion-reduce:transition-none motion-safe:hover:shadow-md motion-safe:hover:shadow-indigo-200/60">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 transition-colors duration-200 group-hover:bg-indigo-100 motion-reduce:transition-none">
              <FeatureIconInsights />
            </div>
            <h3 className="mt-5 text-xl font-semibold tracking-tight text-slate-900">Corpus insights</h3>
            <p className="mt-3 flex-1 text-base leading-relaxed text-slate-600">
              See publishing cadence, content mix, and how topics trend over time — a high-level view of Lenny&apos;s
              archive.
            </p>
          </article>
        </div>
      </section>

      {error ? (
        <div className="mb-4 rounded-md border border-rose-300 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>
      ) : null}

      <section className="mb-6" aria-labelledby="about-stats-heading">
        <div className="mb-8 max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-600">By the numbers</p>
          <h2 id="about-stats-heading" className="mt-2 text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
            Stats
          </h2>
          <p className="mt-2 text-base leading-relaxed text-slate-600">
            Live metrics and charts from the indexed corpus — totals, activity, breakdowns, and topic trends.
          </p>
        </div>

        {trendsData ? (
          <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-2xl border border-indigo-100/90 bg-white/95 p-6 shadow-sm shadow-indigo-100/50">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Total content</p>
              <p className="mt-2 text-3xl font-semibold tabular-nums tracking-tight text-slate-900">
                {trendsData.summary.total_content}
              </p>
              <p className="mt-2 text-sm leading-snug text-slate-600">Indexed items across podcasts and newsletters</p>
            </div>
            <div className="rounded-2xl border border-indigo-100/90 bg-white/95 p-6 shadow-sm shadow-indigo-100/50">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Podcasts</p>
              <p className="mt-2 text-3xl font-semibold tabular-nums tracking-tight text-slate-900">
                {trendsData.summary.total_podcasts}
              </p>
              <p className="mt-2 text-sm leading-snug text-slate-600">Episodes in the graph and search index</p>
            </div>
            <div className="rounded-2xl border border-indigo-100/90 bg-white/95 p-6 shadow-sm shadow-indigo-100/50">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Newsletters</p>
              <p className="mt-2 text-3xl font-semibold tabular-nums tracking-tight text-slate-900">
                {trendsData.summary.total_newsletters}
              </p>
              <p className="mt-2 text-sm leading-snug text-slate-600">Posts available for Q&amp;A and playbooks</p>
            </div>
            <div className="rounded-2xl border border-indigo-100/90 bg-white/95 p-6 shadow-sm shadow-indigo-100/50">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Date range</p>
              <p className="mt-2 text-3xl font-semibold tabular-nums tracking-tight text-slate-900">
                {hasDateRange ? `${startYear}–${endYear}` : "N/A"}
              </p>
              <p className="mt-2 text-sm leading-snug text-slate-600">Span of published material in this dataset</p>
            </div>
          </div>
        ) : null}

        {/* Publishing activity */}
        <div className="mb-6">
          <h3 className="mb-3 text-base font-semibold text-slate-900">Publishing activity</h3>
          <div className="rounded-2xl border border-indigo-100/90 bg-white/95 p-5 shadow-sm shadow-indigo-100/50">
            {heatmapData ? (
              <HeatmapChart data={heatmapData.items} />
            ) : (
              <div className="grid h-48 place-items-center text-sm text-slate-500">
                No publishing data available.
              </div>
            )}
          </div>
        </div>

        {/* Content breakdown */}
        <div className="mb-6">
          <h3 className="mb-3 text-base font-semibold text-slate-900">Content breakdown</h3>
          <div className="rounded-2xl border border-indigo-100/90 bg-white/95 p-5 shadow-sm shadow-indigo-100/50">
            {breakdownData ? (
              <ContentBreakdownChart data={breakdownData.breakdown} />
            ) : (
              <div className="grid h-48 place-items-center text-sm text-slate-500">
                No content breakdown data available.
              </div>
            )}
          </div>
        </div>

        {/* Topic trends */}
        {trendsData ? (
          <div className="mb-6">
            <h3 className="mb-3 text-base font-semibold text-slate-900">Topic trends</h3>

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

            {/* D3 line chart */}
            <div
              ref={chartContainerRef}
              className="relative rounded-2xl border border-indigo-100/90 bg-white/95 p-5 shadow-sm shadow-indigo-100/50"
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
      </section>
    </>
  );
}
