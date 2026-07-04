/**
 * Session picker — lists sessions with committed ticks in the simulation DB.
 */

import type { ObservatorySession } from "./types";

interface SessionPickerProps {
  sessions: ObservatorySession[];
  onSelect: (session: ObservatorySession) => void;
}

export function SessionPicker({ sessions, onSelect }: SessionPickerProps) {
  if (sessions.length === 0) {
    return (
      <div role="status" className="p-8 text-center text-sm text-ash">
        No simulation sessions found. Run a session (e.g.{" "}
        <code className="text-silver">mise run sim:probe</code>) to populate the Observatory.
      </div>
    );
  }

  return (
    <ul className="divide-y divide-soot" data-testid="session-list">
      {sessions.map((session) => (
        <li key={session.session_id}>
          <button
            type="button"
            onClick={() => onSelect(session)}
            className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-dark-metal"
          >
            <span className="flex flex-col">
              <span className="font-mono text-sm text-bone">{session.session_id}</span>
              <span className="text-xs text-ash">
                {session.scenario ?? "unknown scenario"}
                {session.status ? ` · ${session.status}` : ""}
              </span>
            </span>
            <span className="flex flex-col items-end text-xs text-silver">
              <span>
                ticks {session.min_tick}–{session.max_tick}
              </span>
              <span className="text-ash">
                {session.tick_count} committed · {session.checkpoint_count} checkpoints
              </span>
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
