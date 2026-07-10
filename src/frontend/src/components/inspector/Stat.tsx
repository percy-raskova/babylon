/** One label/value row with null-honesty — `null` renders as "no data". */

interface StatProps {
  label: string;
  value: number | string | null;
}

export function Stat({ label, value }: StatProps): React.JSX.Element {
  const hasData = value !== null;
  const display = typeof value === "number" ? value.toFixed(2) : value;

  return (
    <div className="flex justify-between py-0.5 text-[11px]">
      <span className="text-ash">{label}</span>
      <span className={`font-mono ${hasData ? "text-bone" : "italic text-shroud"}`}>
        {hasData ? display : "no data"}
      </span>
    </div>
  );
}
