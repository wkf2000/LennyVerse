import * as d3 from "d3";
import { useEffect, useRef } from "react";

import type { ContentBreakdownItem } from "../../api/statsApi";

interface ContentBreakdownChartProps {
  data: ContentBreakdownItem[];
}

export default function ContentBreakdownChart({ data }: ContentBreakdownChartProps): JSX.Element {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!svgRef.current || !containerRef.current || data.length === 0) return;

    const quarters = Array.from(new Set(data.map((d) => d.quarter)));

    type QuarterData = { quarter: string; podcast: number; newsletter: number; avgWordCount: number };
    const quarterMap = new Map<string, QuarterData>();
    for (const q of quarters) {
      quarterMap.set(q, { quarter: q, podcast: 0, newsletter: 0, avgWordCount: 0 });
    }
    for (const item of data) {
      const qd = quarterMap.get(item.quarter)!;
      if (item.type === "podcast") {
        qd.podcast = item.count;
        qd.avgWordCount = Math.max(qd.avgWordCount, item.avg_word_count);
      } else {
        qd.newsletter = item.count;
        qd.avgWordCount = Math.max(qd.avgWordCount, item.avg_word_count);
      }
    }
    const series = quarters.map((q) => quarterMap.get(q)!);

    const containerWidth = containerRef.current.clientWidth;
    const width = containerWidth;
    const height = 360;
    const margin = { top: 20, right: 60, bottom: 60, left: 50 };

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    svg.attr("width", width).attr("height", height);

    const xScale = d3
      .scaleBand()
      .domain(quarters)
      .range([margin.left, width - margin.right])
      .padding(0.3);

    const maxCount = Math.max(...series.map((s) => s.podcast + s.newsletter), 1);
    const yScale = d3
      .scaleLinear()
      .domain([0, maxCount])
      .range([height - margin.bottom, margin.top])
      .nice();

    const maxWordCount = Math.max(...series.map((s) => s.avgWordCount), 1);
    const yScaleRight = d3
      .scaleLinear()
      .domain([0, maxWordCount])
      .range([height - margin.bottom, margin.top])
      .nice();

    svg
      .append("g")
      .selectAll("line")
      .data(yScale.ticks())
      .join("line")
      .attr("x1", margin.left)
      .attr("x2", width - margin.right)
      .attr("y1", (d) => yScale(d))
      .attr("y2", (d) => yScale(d))
      .attr("stroke", "#e2e8f0")
      .attr("stroke-opacity", 0.5);

    svg
      .append("g")
      .attr("transform", `translate(0,${height - margin.bottom})`)
      .call(d3.axisBottom(xScale))
      .call((g) => g.select(".domain").remove())
      .selectAll("text")
      .attr("transform", "rotate(-45)")
      .attr("text-anchor", "end")
      .style("font-size", "11px")
      .style("fill", "#64748b");

    svg
      .append("g")
      .attr("transform", `translate(${margin.left},0)`)
      .call(d3.axisLeft(yScale))
      .call((g) => g.select(".domain").remove())
      .selectAll("text")
      .style("font-size", "11px")
      .style("fill", "#64748b");

    svg
      .append("g")
      .attr("transform", `translate(${width - margin.right},0)`)
      .call(d3.axisRight(yScaleRight).tickFormat((d) => `${(Number(d) / 1000).toFixed(0)}k`))
      .call((g) => g.select(".domain").remove())
      .selectAll("text")
      .style("font-size", "11px")
      .style("fill", "#f59e0b");

    const tooltip = d3.select(tooltipRef.current!);

    for (const s of series) {
      const x = xScale(s.quarter)!;
      const barWidth = xScale.bandwidth();

      svg
        .append("rect")
        .attr("x", x)
        .attr("y", yScale(s.newsletter))
        .attr("width", barWidth)
        .attr("height", yScale(0) - yScale(s.newsletter))
        .attr("fill", "#10b981")
        .attr("rx", 2)
        .style("cursor", "pointer")
        .on("mouseover", (event: MouseEvent) => {
          const html = `<div style="font-weight:600;color:#334155">${s.quarter}</div>
            <div style="color:#6366f1">Podcasts: ${s.podcast}</div>
            <div style="color:#10b981">Newsletters: ${s.newsletter}</div>
            <div style="color:#f59e0b">Avg words: ${s.avgWordCount.toLocaleString()}</div>`;
          const containerRect = containerRef.current!.getBoundingClientRect();
          tooltip
            .html(html)
            .style("left", `${event.clientX - containerRect.left + 12}px`)
            .style("top", `${event.clientY - containerRect.top - 10}px`)
            .style("opacity", "1");
        })
        .on("mouseleave", () => tooltip.style("opacity", "0"));

      svg
        .append("rect")
        .attr("x", x)
        .attr("y", yScale(s.podcast + s.newsletter))
        .attr("width", barWidth)
        .attr("height", yScale(s.newsletter) - yScale(s.podcast + s.newsletter))
        .attr("fill", "#6366f1")
        .attr("rx", 2)
        .style("cursor", "pointer")
        .on("mouseover", (event: MouseEvent) => {
          const html = `<div style="font-weight:600;color:#334155">${s.quarter}</div>
            <div style="color:#6366f1">Podcasts: ${s.podcast}</div>
            <div style="color:#10b981">Newsletters: ${s.newsletter}</div>
            <div style="color:#f59e0b">Avg words: ${s.avgWordCount.toLocaleString()}</div>`;
          const containerRect = containerRef.current!.getBoundingClientRect();
          tooltip
            .html(html)
            .style("left", `${event.clientX - containerRect.left + 12}px`)
            .style("top", `${event.clientY - containerRect.top - 10}px`)
            .style("opacity", "1");
        })
        .on("mouseleave", () => tooltip.style("opacity", "0"));
    }

    const lineGen = d3
      .line<QuarterData>()
      .x((d) => xScale(d.quarter)! + xScale.bandwidth() / 2)
      .y((d) => yScaleRight(d.avgWordCount))
      .curve(d3.curveMonotoneX);

    svg
      .append("path")
      .datum(series)
      .attr("d", lineGen)
      .attr("fill", "none")
      .attr("stroke", "#f59e0b")
      .attr("stroke-width", 2)
      .attr("stroke-dasharray", "6,3");

    svg
      .selectAll("circle.word-dot")
      .data(series)
      .join("circle")
      .attr("class", "word-dot")
      .attr("cx", (d) => xScale(d.quarter)! + xScale.bandwidth() / 2)
      .attr("cy", (d) => yScaleRight(d.avgWordCount))
      .attr("r", 3)
      .attr("fill", "#f59e0b");
  }, [data]);

  if (data.length === 0) {
    return (
      <div className="grid h-48 place-items-center text-sm text-slate-500">
        No content breakdown data available.
      </div>
    );
  }

  return (
    <div ref={containerRef} className="relative">
      <svg ref={svgRef} className="w-full" />
      <div
        ref={tooltipRef}
        className="pointer-events-none absolute rounded-lg border border-slate-200 bg-white p-3 text-sm shadow-lg"
        style={{ opacity: 0 }}
      />
    </div>
  );
}
