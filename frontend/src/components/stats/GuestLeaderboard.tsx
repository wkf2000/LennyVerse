import type { GuestCountItem } from "../../api/statsApi";

interface GuestLeaderboardProps {
  data: GuestCountItem[];
}

export default function GuestLeaderboard({ data }: GuestLeaderboardProps): JSX.Element {
  if (data.length === 0) {
    return (
      <div className="grid h-48 place-items-center text-sm text-slate-500">
        No guest data available.
      </div>
    );
  }

  const maxCount = Math.max(...data.map((g) => g.count), 1);

  return (
    <div className="space-y-1.5">
      {data.map((guest, idx) => (
        <div
          key={guest.guest}
          className="group flex items-center gap-3 rounded-lg px-2 py-1.5 transition-colors hover:bg-indigo-50"
        >
          <span className="w-6 text-right text-xs font-medium text-slate-400">{idx + 1}</span>
          <span className="min-w-0 flex-1 truncate text-sm text-slate-700 group-hover:text-slate-900">
            {guest.guest}
          </span>
          <div className="flex w-32 items-center gap-2">
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-indigo-500 transition-all"
                style={{ width: `${(guest.count / maxCount) * 100}%` }}
              />
            </div>
            <span className="w-6 text-right text-xs font-semibold text-slate-600">{guest.count}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
