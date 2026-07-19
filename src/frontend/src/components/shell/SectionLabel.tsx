/**
 * SectionLabel — small uppercase section header, shared by dashboard-style
 * panels (extracted from `EconomyDashboard.tsx` when `CircuitPage` became
 * this component's second consumer, Track 2 T2-7).
 */

export function SectionLabel({ children }: { children: React.ReactNode }): React.JSX.Element {
  return <p className="mb-1 text-[9px] uppercase tracking-widest text-ksbc-muted-2">{children}</p>;
}
