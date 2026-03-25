import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

describe("search", () => {
  it("smoke: testing library renders", () => {
    render(<div data-testid="search-smoke">search harness</div>);
    expect(screen.getByTestId("search-smoke")).toBeInTheDocument();
  });
});
