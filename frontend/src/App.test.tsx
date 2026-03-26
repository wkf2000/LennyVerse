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

  it("initial /about path shows About page heading", () => {
    window.history.pushState({}, "", "/about");
    render(<App />);
    expect(
      screen.getByRole("heading", {
        level: 1,
        name: /A teaching assistant built on Lenny Rachitsky's archive/i,
      }),
    ).toBeInTheDocument();
  });

  it("switching to about updates URL path to /about", () => {
    render(<App />);
    const nav = screen.getByRole("navigation");
    fireEvent.click(within(nav).getByRole("button", { name: /^about$/ }));
    expect(window.location.pathname).toBe("/about");
  });

  it("marks About nav button current when on /about", () => {
    window.history.pushState({}, "", "/about");
    render(<App />);
    const nav = screen.getByRole("navigation");
    const aboutBtn = within(nav).getByRole("button", { name: /^about$/ });
    expect(aboutBtn).toHaveAttribute("aria-current", "page");
    expect(aboutBtn).toHaveClass("bg-slate-900");
  });
});
