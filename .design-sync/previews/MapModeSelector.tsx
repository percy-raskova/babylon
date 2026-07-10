/**
 * MapModeSelector preview — the spec-070 political-topology lens cycler
 * (stance/heat/habitability/faction/collapse). Controlled component: the
 * active lens is a prop, so cells just vary it. The faction picker only
 * shows when lens.kind === "faction" AND factions is non-empty (FR-025).
 */
import { MapModeSelector } from "babylon-cockpit";

const FACTIONS = [
  { id: "FAC_COMPRADOR_BLOC", colonial_stance: "uphold" },
  { id: "FAC_NEW_AFRIKAN_UNITY", colonial_stance: "abolish" },
  { id: "FAC_LIBERAL_TECHNOCRAT", colonial_stance: "ignore" },
];

// Inline style for width: .design-sync/previews/ isn't in Tailwind's
// content-scan root, so w-[620px] never compiles (see learnings).
function Frame({ children }: { children?: unknown }) {
  return (
    <div className="flex items-center bg-void p-3" style={{ width: 620 }}>
      {children as never}
    </div>
  );
}

export function StanceActive() {
  return (
    <Frame>
      <MapModeSelector lens={{ kind: "stance" }} onLensChange={() => {}} />
    </Frame>
  );
}

export function CollapseActive() {
  return (
    <Frame>
      <MapModeSelector lens={{ kind: "collapse" }} onLensChange={() => {}} />
    </Frame>
  );
}

export function FactionActiveWithPicker() {
  return (
    <Frame>
      <MapModeSelector
        lens={{ kind: "faction" }}
        onLensChange={() => {}}
        factionFilter="FAC_NEW_AFRIKAN_UNITY"
        onFactionFilterChange={() => {}}
        factions={FACTIONS}
      />
    </Frame>
  );
}

export function MetricLensNoneActive() {
  return (
    <Frame>
      <MapModeSelector lens={{ kind: "metric", metric: "profit_rate" }} onLensChange={() => {}} />
    </Frame>
  );
}
