import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import HeatmapChart from "../HeatmapChart";
import ContentBreakdownChart from "../ContentBreakdownChart";
import GuestLeaderboard from "../GuestLeaderboard";

describe("HeatmapChart", () => {
  it("renders empty state when no data", () => {
    render(<HeatmapChart data={[]} />);
    expect(screen.getByText("No publishing data available.")).toBeInTheDocument();
  });

  it("renders SVG when data is provided", () => {
    const data = [
      { year: 2023, week: 11, type: "podcast", title: "Ep 1", published_at: "2023-03-15" },
      { year: 2023, week: 12, type: "newsletter", title: "NL 1", published_at: "2023-03-20" },
    ];
    const { container } = render(<HeatmapChart data={data} />);
    expect(container.querySelector("svg")).toBeInTheDocument();
  });
});

describe("ContentBreakdownChart", () => {
  it("renders empty state when no data", () => {
    render(<ContentBreakdownChart data={[]} />);
    expect(screen.getByText("No content breakdown data available.")).toBeInTheDocument();
  });

  it("renders SVG when data is provided", () => {
    const data = [
      { quarter: "2023-Q1", type: "podcast", count: 10, avg_word_count: 5000 },
      { quarter: "2023-Q1", type: "newsletter", count: 15, avg_word_count: 2000 },
    ];
    const { container } = render(<ContentBreakdownChart data={data} />);
    expect(container.querySelector("svg")).toBeInTheDocument();
  });
});

describe("GuestLeaderboard", () => {
  it("renders empty state when no data", () => {
    render(<GuestLeaderboard data={[]} />);
    expect(screen.getByText("No guest data available.")).toBeInTheDocument();
  });

  it("renders guest names when data is provided", () => {
    const data = [
      { guest: "Shreyas Doshi", count: 10 },
      { guest: "Elena Verna", count: 8 },
    ];
    render(<GuestLeaderboard data={data} />);
    expect(screen.getByText("Shreyas Doshi")).toBeInTheDocument();
    expect(screen.getByText("Elena Verna")).toBeInTheDocument();
  });
});
