/**
 * A single top-bar metric chip with Constitution III.11 null-honesty:
 * `null`/`undefined` renders as a visibly distinct "no data" state, never
 * a fabricated `0`.
 */

interface StatChipProps {
  label: string;
  value: number | null | undefined;
  format: (v: number) => string;
  colorClassName?: string;
}

export function StatChip({
  label,
  value,
  format,
  colorClassName = "text-bone",
}: StatChipProps): React.JSX.Element {
  const hasData = value !== null && value !== undefined;

  return (
    <div
      className="flex items-center gap-1.5 rounded border border-rebar bg-concrete px-2.5 py-1"
      data-testid={`stat-${label.toLowerCase()}`}
    >
      <span className="text-[9px] uppercase tracking-widest text-ash">{label}</span>
      <span
        className={`font-mono text-[11px] font-semibold ${
          hasData ? colorClassName : "italic text-shroud"
        }`}
      >
        {hasData ? format(value) : "no data"}
      </span>
    </div>
  );
}
