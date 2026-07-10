/**
 * One selectable Outliner row — org/community/faction entries all share
 * this shape (label + optional sublabel + selected-state styling).
 */

interface OutlinerRowProps {
  label: string;
  sublabel?: string;
  selected?: boolean;
  onClick: () => void;
}

export function OutlinerRow({
  label,
  sublabel,
  selected = false,
  onClick,
}: OutlinerRowProps): React.JSX.Element {
  return (
    <button
      onClick={onClick}
      className={`flex flex-col items-start rounded px-2 py-1 text-left ${
        selected ? "bg-spire/10 text-spire" : "text-bone hover:bg-rebar"
      }`}
    >
      <span className="truncate text-[11px]">{label}</span>
      {sublabel && <span className="text-[9px] text-ash">{sublabel}</span>}
    </button>
  );
}
