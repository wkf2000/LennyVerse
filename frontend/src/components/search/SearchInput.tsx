import type { FormEvent } from "react";

export interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  placeholder?: string;
}

export default function SearchInput({
  value,
  onChange,
  onSubmit,
  disabled = false,
  placeholder = "Ask anything about Lenny's archive...",
}: SearchInputProps): JSX.Element {
  function handleSubmit(event: FormEvent): void {
    event.preventDefault();
    if (!disabled && value.trim()) {
      onSubmit();
    }
  }

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <label className="block">
        <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
          Ask the archive
        </span>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-stretch">
          <input
            className="w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none transition-colors duration-200 focus:border-amber-400 focus:bg-white motion-reduce:transition-none disabled:opacity-60"
            value={value}
            onChange={(event) => onChange(event.target.value)}
            disabled={disabled}
            placeholder={placeholder}
            aria-label="Search query"
          />
          <button
            type="submit"
            disabled={disabled || !value.trim()}
            className="shrink-0 rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-amber-100 transition-colors hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Search
          </button>
        </div>
      </label>
    </form>
  );
}
