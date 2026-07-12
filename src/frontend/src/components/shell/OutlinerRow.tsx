/**
 * One selectable Outliner row — org/community/faction entries all share
 * this shape (label + optional sublabel + selected-state styling).
 *
 * `compact` (Design Bible §5.1 "compact-density mode AT LAUNCH" — list
 * surfaces degrade with player success, so the tighter row is shipped now
 * rather than retrofitted) drops the sublabel line and tightens vertical
 * padding; it never changes what data is shown, only its density.
 */

interface OutlinerRowProps {
  label: string;
  sublabel?: string;
  selected?: boolean;
  compact?: boolean;
  onClick: () => void;
}

export function OutlinerRow({
  label,
  sublabel,
  selected = false,
  compact = false,
  onClick,
}: OutlinerRowProps): React.JSX.Element {
  return (
    <button
      onClick={onClick}
      className={`flex flex-col items-start rounded px-2 text-left ${compact ? "py-0.5" : "py-1"} ${
        selected ? "bg-spire/10 text-spire" : "text-bone hover:bg-rebar"
      }`}
    >
      <span className="truncate text-[11px]">{label}</span>
      {sublabel && !compact && <span className="text-[9px] text-ash">{sublabel}</span>}
    </button>
  );
}
