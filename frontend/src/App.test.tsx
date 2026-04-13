import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

function stubFetchForApp(): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ nodes: [], edges: [] }),
      } as Response),
    ),
  );
}

describe("App URL view sync", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    vi.unstubAllGlobals();
    stubFetchForApp();
    window.history.pushState({}, "", "/");
  });

  it("initial /explore path selects explore view", () => {
    window.history.pushState({}, "", "/explore");
    render(<App />);
    expect(
      screen.getByRole("heading", { name: /Explore the archive with grounded answers/i }),
    ).toBeInTheDocument();
  });

  it("switching to explore updates URL path to /explore", () => {
    render(<App />);
    const nav = screen.getByRole("navigation");
    fireEvent.click(within(nav).getByRole("button", { name: /^explore$/ }));
    expect(window.location.pathname).toBe("/explore");
  });

  it("initial / path shows home landing page", () => {
    render(<App />);
    expect(
      screen.getByRole("heading", {
        level: 1,
        name: /Lenny's Second Brain/i,
      }),
    ).toBeInTheDocument();
  });

  it("switching to playbook updates URL path to /playbook", () => {
    render(<App />);
    const nav = screen.getByRole("navigation");
    fireEvent.click(within(nav).getByRole("button", { name: /^playbook$/ }));
    expect(window.location.pathname).toBe("/playbook");
  });

  it("marks playbook nav button current when on /playbook", () => {
    window.history.pushState({}, "", "/playbook");
    render(<App />);
    const nav = screen.getByRole("navigation");
    const playbookBtn = within(nav).getByRole("button", { name: /^playbook$/ });
    expect(playbookBtn).toHaveAttribute("aria-current", "page");
    expect(playbookBtn).toHaveClass("bg-slate-900");
  });
});
