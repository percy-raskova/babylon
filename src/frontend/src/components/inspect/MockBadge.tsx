/**
 * MockBadge — small, unobtrusive "MOCK" indicator for an `InspectionCard`
 * row whose value is a placeholder (owner's mock doctrine, Program 17 Wave 1
 * / W1.4): a feature that does not exist in the codebase yet still ships,
 * but is visibly badged — never a fabricated value presented as real
 * (Constitution III.11). Rendered by `ValueRow` when `row.mock` is `true`.
 */
export function MockBadge(): React.JSX.Element {
  return (
    <span
      data-testid="mock-badge"
      title="Placeholder — not backed by real simulation data yet"
      className="rounded border border-rupture px-1 py-0 text-[8px] uppercase tracking-widest text-rupture"
    >
      Mock
    </span>
  );
}
