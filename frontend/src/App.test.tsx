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

  it("initial /search path selects search view", () => {
    window.history.pushState({}, "", "/search");
    render(<App />);
    expect(
      screen.getByRole("heading", { name: /Search the archive with grounded answers/i }),
    ).toBeInTheDocument();
  });

  it("switching to search updates URL path to /search", () => {
    render(<App />);
    const nav = screen.getByRole("navigation");
    fireEvent.click(within(nav).getByRole("button", { name: /^search$/ }));
    expect(window.location.pathname).toBe("/search");
  });
});
