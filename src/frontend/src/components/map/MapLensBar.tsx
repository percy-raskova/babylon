/**
 * MapLensBar — replaces `MapModeSelector` (spec-113 Lane B, architecture
 * §3.3, DESIGN_BIBLE.md §3.3). Renders grouped, registry-driven lens buttons
 * (Paradox map-mode idiom: group label chip + button cluster per
 * `LENS_GROUPS`) instead of the old flat 5-button row hardcoded to the
 * spec-093 `LensMode` set.
 *
 * Keeps `data-testid="map-mode-selector"` on the outer wrapper and
 * `lens-mode-<id>` per button — the exact contract `map-lens-cycling.spec.ts`
 * / `briefing-map-smoke.spec.ts` / `MapStage.test.tsx` pin — so this is a
 * drop-in replacement at the DOM-contract level even though the lens ids it
 * renders have changed (stance/heat/habitability/faction/collapse ->
 * imperial_rent/exploitation_rate/heat/solidarity_index/stance/faction/
 * collapse/class_composition/habitability, registry order).
 */

import { LENS_GROUPS } from "@/lib/lenses/groups";
import { lensRegistryByGroup, type LensAvailabilityContext } from "@/lib/lenses/registry";
import { lensKey, type Lens } from "@/lib/lens";
import type { FactionSummary } from "@/components/map/mapLensLayers";

/**
 * Selection-grammar button class (DESIGN_BIBLE.md §9b: "gold inverse-video
 * for selected/active states... everywhere the same grammar") for the
 * densely-packed lens/framing chip rows. Deliberately leaner than
 * `installerKit.keyButtonClass` (no per-button offset shadow/press — that
 * grammar is reserved for the standalone chrome buttons the task brief
 * names explicitly); the enclosing group chip carries the hard shadow
 * instead, so many small buttons in a row don't stack overlapping shadows.
 */
function lensChipClass(active: boolean): string {
  return `rounded-none px-2 py-1 font-mono text-[11px] font-medium uppercase transition-colors ${
    active
      ? "bg-accent-gold text-selection-ink"
      : "text-ink hover:bg-plate hover:text-accent-crimson"
  }`;
}

interface MapLensBarProps {
  /** The currently active lens. */
  lens: Lens;
  /** Called with the new lens when a lens button is clicked. */
  onLensChange?: (lens: Lens) => void;
  /** Currently selected faction for the "faction" lens mode. */
  factionFilter?: string | null;
  /** Called when a faction is chosen from the "faction" lens's picker. */
  onFactionFilterChange?: (factionId: string | null) => void;
  factions?: FactionSummary[];
  /** Availability context forwarded to `lensRegistryByGroup` (registry.ts's degradation gate). */
  availability?: LensAvailabilityContext;
}

export function MapLensBar({
  lens,
  onLensChange,
  factionFilter = null,
  onFactionFilterChange,
  factions = [],
  availability = {},
}: MapLensBarProps) {
  const byGroup = lensRegistryByGroup(availability);
  const activeKey = lensKey(lens);

  return (
    <div className="flex flex-wrap items-center gap-1" data-testid="map-mode-selector">
      {LENS_GROUPS.map((group) => {
        const defs = byGroup.get(group.id) ?? [];
        if (defs.length === 0) return null;
        return (
          <div
            key={group.id}
            className="flex items-center gap-0.5 border-2 border-ksbc-muted-1 bg-plate p-0.5 shadow-[3px_3px_0_#000]"
            data-testid={`lens-group-${group.id}`}
          >
            <span className="px-1.5 text-[10px] font-medium uppercase tracking-wider text-ksbc-muted-2">
              {group.label}
            </span>
            {defs.map((def) => {
              const active = activeKey === lensKey(def.toLens());
              return (
                <button
                  key={def.id}
                  title={def.tooltip}
                  data-testid={`lens-mode-${def.id}`}
                  aria-pressed={active}
                  onClick={() => onLensChange?.(def.toLens())}
                  className={lensChipClass(active)}
                >
                  {def.label}
                </button>
              );
            })}
          </div>
        );
      })}
      {lens.kind === "faction" && factions.length > 0 && (
        <select
          data-testid="faction-filter-select"
          value={factionFilter ?? ""}
          onChange={(e) => onFactionFilterChange?.(e.target.value || null)}
          className="rounded-none border-2 border-ksbc-muted-1 bg-plate px-2 py-1 font-mono text-[11px] text-ink"
        >
          <option value="">Select faction…</option>
          {factions.map((f) => (
            <option key={f.id} value={f.id}>
              {f.id}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}
