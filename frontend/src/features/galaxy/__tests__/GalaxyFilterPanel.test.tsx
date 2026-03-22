import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { GalaxyFilterPanel } from "@/features/galaxy/GalaxyFilterPanel";
import { defaultGalaxyFilters } from "@/features/galaxy/galaxyScene";

describe("GalaxyFilterPanel", () => {
  it("updates selected filters and triggers reset", async () => {
    const onChange = vi.fn();
    const onReset = vi.fn();
    render(
      <GalaxyFilterPanel
        facets={{
          tags: ["ai", "product"],
          guests: ["Lenny", "Jane"],
          date_min: null,
          date_max: null,
          source_types: ["newsletter", "podcast"],
        }}
        filters={defaultGalaxyFilters()}
        onChange={onChange}
        onReset={onReset}
      />,
    );

    const tagsSelect = screen.getByLabelText("Tags");
    await userEvent.selectOptions(tagsSelect, ["ai"]);
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange.mock.calls[0][0].tags.has("ai")).toBe(true);

    fireEvent.click(screen.getByText("Reset Filters"));
    expect(onReset).toHaveBeenCalledTimes(1);
  });
});
