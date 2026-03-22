import type { ChangeEvent } from "react";

import type { FilterFacets, GalaxyFilters } from "@/features/galaxy/types";

interface GalaxyFilterPanelProps {
  facets: FilterFacets;
  filters: GalaxyFilters;
  onChange: (next: GalaxyFilters) => void;
  onReset: () => void;
}

export function GalaxyFilterPanel({ facets, filters, onChange, onReset }: GalaxyFilterPanelProps) {
  const activeCount = filters.tags.size + filters.guests.size + filters.sourceTypes.size;

  return (
    <aside className="galaxy-panel galaxy-filters" aria-label="Galaxy filters">
      <h2 className="galaxy-panel__title">Filters</h2>
      <p className="galaxy-filters__active">
        <span className="galaxy-filters__active-label">Active filters</span>
        <span className="galaxy-filters__active-count">{activeCount}</span>
      </p>
      <FilterSelect
        label="Tags"
        options={facets.tags}
        selected={filters.tags}
        onChange={(next) => onChange({ ...filters, tags: next })}
      />
      <FilterSelect
        label="Guests"
        options={facets.guests}
        selected={filters.guests}
        onChange={(next) => onChange({ ...filters, guests: next })}
      />
      <FilterSelect
        label="Source Types"
        options={facets.source_types}
        selected={filters.sourceTypes}
        onChange={(next) => onChange({ ...filters, sourceTypes: next })}
      />
      <button type="button" className="lv-btn lv-btn--ghost" onClick={onReset}>
        Reset filters
      </button>
    </aside>
  );
}

function FilterSelect({
  label,
  options,
  selected,
  onChange,
}: {
  label: string;
  options: string[];
  selected: Set<string>;
  onChange: (next: Set<string>) => void;
}) {
  const handleChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const next = new Set<string>(Array.from(event.target.selectedOptions).map((option) => option.value));
    onChange(next);
  };

  return (
    <label className="galaxy-filter-group">
      <span>{label}</span>
      <select multiple value={Array.from(selected)} onChange={handleChange} aria-label={label}>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}
