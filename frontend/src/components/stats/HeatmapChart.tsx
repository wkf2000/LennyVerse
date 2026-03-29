import * as d3 from "d3";
import { useEffect, useRef } from "react";

import type { HeatmapItem } from "../../api/statsApi";

interface HeatmapChartProps {
  data: HeatmapItem[];
}

interface WeekCell {
  year: number;
  week: number;
  podcasts: number;
  newsletters: number;
  titles: string[];
}

const CELL_SIZE = 14;
const CELL_GAP = 2;

export default function HeatmapChart({ data }: HeatmapChartProps): JSX.Element {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!svgRef.current || !containerRef.current || data.length === 0) return;

    const cellMap = new Map<string, WeekCell>();
    for (const item of data) {
      const key = `${item.year}-${item.week}`;
      if (!cellMap.has(key)) {
        cellMap.set(key, { year: item.year, week: item.week, podcasts: 0, newsletters: 0, titles: [] });
      }
      const cell = cellMap.get(key)!;
      if (item.type === "podcast") cell.podcasts++;
      else cell.newsletters++;
      cell.titles.push(item.title);
    }

    const cells = Array.from(cellMap.values());
    const years = Array.from(new Set(cells.map((c) => c.year))).sort();
    const maxCount = Math.max(...cells.map((c) => c.podcasts + c.newsletters), 1);

    const margin = { top: 30, right: 16, bottom: 16, left: 50 };
    const width = 52 * (CELL_SIZE + CELL_GAP) + margin.left + margin.right;
    const height = years.length * (CELL_SIZE + CELL_GAP) + margin.top + margin.bottom;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    svg.attr("width", width).attr("height", height);

    const opacityScale = d3.scaleLinear().domain([0, maxCount]).range([0.15, 1]);

    function cellColor(cell: WeekCell): string {
      if (cell.podcasts > 0 && cell.newsletters > 0) return "#f59e0b";
      if (cell.podcasts > 0) return "#6366f1";
      return "#10b981";
    }

    svg
      .selectAll("text.year-label")
      .data(years)
      .join("text")
      .attr("class", "year-label")
      .attr("x", margin.left - 8)
      .attr("y", (_, i) => margin.top + i * (CELL_SIZE + CELL_GAP) + CELL_SIZE / 2)
      .attr("text-anchor", "end")
      .attr("dominant-baseline", "middle")
      .style("font-size", "11px")
      .style("fill", "#64748b")
      .text((d) => String(d));

    const monthStarts = [1, 5, 9, 14, 18, 22, 27, 31, 35, 40, 44, 48];
    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    svg
      .selectAll("text.month-label")
      .data(monthNames)
      .join("text")
      .attr("class", "month-label")
      .attr("x", (_, i) => margin.left + monthStarts[i] * (CELL_SIZE + CELL_GAP))
      .attr("y", margin.top - 8)
      .style("font-size", "10px")
      .style("fill", "#94a3b8")
      .text((d) => d);

    const tooltip = d3.select(tooltipRef.current!);

    for (const cell of cells) {
      const yearIdx = years.indexOf(cell.year);
      const x = margin.left + (cell.week - 1) * (CELL_SIZE + CELL_GAP);
      const y = margin.top + yearIdx * (CELL_SIZE + CELL_GAP);
      const total = cell.podcasts + cell.newsletters;

      svg
        .append("rect")
        .attr("x", x)
        .attr("y", y)
        .attr("width", CELL_SIZE)
        .attr("height", CELL_SIZE)
        .attr("rx", 2)
        .attr("fill", cellColor(cell))
        .attr("opacity", opacityScale(total))
        .style("cursor", "pointer")
        .on("mouseover", (event: MouseEvent) => {
          let html = `<div style="font-weight:600;margin-bottom:4px;color:#334155">${cell.year} W${cell.week}</div>`;
          if (cell.podcasts > 0) html += `<div style="color:#6366f1">${cell.podcasts} podcast${cell.podcasts > 1 ? "s" : ""}</div>`;
          if (cell.newsletters > 0) html += `<div style="color:#10b981">${cell.newsletters} newsletter${cell.newsletters > 1 ? "s" : ""}</div>`;
          for (const title of cell.titles.slice(0, 5)) {
            html += `<div style="color:#64748b;font-size:11px;margin-top:2px">${title}</div>`;
          }
          if (cell.titles.length > 5) {
            html += `<div style="color:#94a3b8;font-size:11px">+${cell.titles.length - 5} more</div>`;
          }
          const containerRect = containerRef.current!.getBoundingClientRect();
          tooltip
            .html(html)
            .style("left", `${event.clientX - containerRect.left + 12}px`)
            .style("top", `${event.clientY - containerRect.top - 10}px`)
            .style("opacity", "1");
        })
        .on("mouseleave", () => {
          tooltip.style("opacity", "0");
        });
    }

    for (const year of years) {
      const yearIdx = years.indexOf(year);
      for (let w = 1; w <= 52; w++) {
        const key = `${year}-${w}`;
        if (!cellMap.has(key)) {
          svg
            .append("rect")
            .attr("x", margin.left + (w - 1) * (CELL_SIZE + CELL_GAP))
            .attr("y", margin.top + yearIdx * (CELL_SIZE + CELL_GAP))
            .attr("width", CELL_SIZE)
            .attr("height", CELL_SIZE)
            .attr("rx", 2)
            .attr("fill", "#e2e8f0")
            .attr("opacity", 0.3);
        }
      }
    }
  }, [data]);

  if (data.length === 0) {
    return (
      <div className="grid h-48 place-items-center text-sm text-slate-500">
        No publishing data available.
      </div>
    );
  }

  return (
    <div ref={containerRef} className="relative overflow-x-auto">
      <svg ref={svgRef} />
      <div
        ref={tooltipRef}
        className="pointer-events-none absolute rounded-lg border border-slate-200 bg-white p-3 text-sm shadow-lg"
        style={{ opacity: 0 }}
      />
    </div>
  );
}
