/**
 * TranslationFooter preview — euphemism sync footer below the triptych.
 * Pure props, no story dependency. `activeEuph` is a controlled prop, so
 * the "active translation" split-view (normally hover-triggered) renders
 * statically by just setting it directly. Page-level width (~1100px), but
 * short (a footer bar) — grid mode would squeeze it into a narrow column.
 */
import { TranslationFooter } from "babylon-cockpit";

const FILTERS = [
  { id: "ownership" as const, label: "Ownership", desc: "", hits: 3, color: "var(--babylon-rent)" },
  { id: "advertising" as const, label: "Advertising", desc: "", hits: 2, color: "var(--babylon-heat)" },
  { id: "sourcing" as const, label: "Sourcing", desc: "", hits: 5, color: "var(--babylon-cadre)" },
  { id: "flak" as const, label: "Flak", desc: "", hits: 2, color: "var(--babylon-rupture)" },
  { id: "ideology" as const, label: "Anti-radical ideology", desc: "", hits: 4, color: "var(--babylon-laser)" },
];

const EUPHEMISMS = {
  raid: { c: "security operation", l: "RAID", filter: "sourcing" as const, note: "State spokesperson is sole source. Verb erased: who breached whom?" },
  hq: { c: "community center", l: "WCLF HALL / OUR HALL", filter: "ownership" as const, note: "Property classification scrubbed. 11-year-old federation HQ at 7100 Schaefer." },
};

function Frame({ children }: { children?: unknown }) {
  // Inline style, not a Tailwind arbitrary-value class — see wire.md: the DS
  // package's Tailwind content-scan doesn't cover .design-sync/previews/, so
  // `w-[1100px]` compiles to nothing and silently no-ops. 840px (not the
  // ~1100px "page-level" ideal) to stay inside the capture pipeline's fixed
  // 900x700 viewport. No fixed height — this is a short footer bar.
  return (
    <div className="bg-void p-2" style={{ width: 840 }}>
      {children as never}
    </div>
  );
}

export function Idle() {
  return (
    <Frame>
      <TranslationFooter
        activeEuph={null}
        setActiveEuph={() => {}}
        euphAlways={false}
        setEuphAlways={() => {}}
        euphemisms={EUPHEMISMS}
        filters={FILTERS}
        onOpenPatterns={() => {}}
      />
    </Frame>
  );
}

export function ActiveTranslation() {
  return (
    <Frame>
      <TranslationFooter
        activeEuph="raid"
        setActiveEuph={() => {}}
        euphAlways={false}
        setEuphAlways={() => {}}
        euphemisms={EUPHEMISMS}
        filters={FILTERS}
        onOpenPatterns={() => {}}
      />
    </Frame>
  );
}

export function AlwaysOnToggle() {
  return (
    <Frame>
      <TranslationFooter
        activeEuph={null}
        setActiveEuph={() => {}}
        euphAlways={true}
        setEuphAlways={() => {}}
        euphemisms={EUPHEMISMS}
        filters={FILTERS}
        onOpenPatterns={() => {}}
      />
    </Frame>
  );
}
