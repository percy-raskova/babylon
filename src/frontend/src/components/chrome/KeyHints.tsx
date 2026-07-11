/**
 * KeyHints — the keyboard-hint footer row (DESIGN_BIBLE.md §9b: "A
 * keyboard-hint footer row on every dialog — the installer's soul; we
 * already have Q/E/space/1-2-3"). A tiny presentational primitive: the
 * real bindings live in `useSpeedShortcut` (number keys 1/2/3),
 * `store/orchestrator.ts`'s `KeyQ`/`KeyE` lens-cycle listener, the
 * spacebar pause/resume toggle (also `orchestrator.ts`), and
 * `InspectionStack`'s own Escape handler — this component renders the
 * hint text, it does not bind any key itself (that would double-fire the
 * shortcuts those modules already own).
 */

export interface KeyHint {
  keys: string;
  label: string;
}

/** The default global hint set (bible §9b/§5.3) — pass a subset via `hints` to scope to a dialog. */
export const DEFAULT_KEY_HINTS: KeyHint[] = [
  { keys: "Space", label: "pause" },
  { keys: "1/2/3", label: "speed" },
  { keys: "Q/E", label: "lens" },
  { keys: "Esc", label: "close" },
];

interface KeyHintsProps {
  /** Defaults to the full global set; hosts pass a subset relevant to what they show. */
  hints?: KeyHint[];
}

export function KeyHints({ hints = DEFAULT_KEY_HINTS }: KeyHintsProps): React.JSX.Element {
  return (
    <div
      data-testid="key-hints"
      className="flex flex-wrap items-center gap-x-3 gap-y-0.5 border-t border-ksbc-muted-3 px-2 py-1 font-mono text-[9px] uppercase tracking-widest text-ksbc-muted-2"
    >
      {hints.map((hint) => (
        <span key={hint.keys} className="flex items-center gap-1">
          <span className="border border-ksbc-muted-1 bg-plate px-1 text-accent-gold">
            {hint.keys}
          </span>
          <span>{hint.label}</span>
        </span>
      ))}
    </div>
  );
}
