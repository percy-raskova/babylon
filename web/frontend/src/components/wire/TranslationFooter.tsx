/**
 * TranslationFooter - euphemism sync footer below the triptych.
 * Spec 094: ports TranslationFooter from wire-app.jsx.
 */

import type { EuphemismEntry, ManufacturingConsentFilter } from "@/types/wire";

interface Props {
  activeEuph: string | null;
  setActiveEuph: (id: string | null) => void;
  euphAlways: boolean;
  setEuphAlways: (v: boolean) => void;
  euphemisms: Record<string, EuphemismEntry>;
  filters: ManufacturingConsentFilter[];
  onOpenPatterns: () => void;
}

export function TranslationFooter({
  activeEuph,
  euphAlways,
  setEuphAlways,
  euphemisms,
  filters,
  onOpenPatterns,
}: Props) {
  const active = activeEuph ? euphemisms[activeEuph] : null;
  const total = Object.keys(euphemisms).length;
  const filterTotal = filters.reduce((s, f) => s + f.hits, 0);

  return (
    <div
      className="flex shrink-0 items-center gap-4 border-t px-4 py-2"
      style={{
        borderColor: "var(--babylon-rebar)",
        background: "linear-gradient(180deg, #0a0d13 0%, var(--babylon-void) 100%)",
        minHeight: 48,
      }}
    >
      <span
        className="wire-label shrink-0"
        style={{ color: active ? "var(--babylon-laser)" : "var(--babylon-ash)" }}
      >
        {"\u25b8"} Euphemism map
      </span>

      {active ? (
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <span
            className="truncate text-[13px]"
            style={{
              color: "var(--babylon-bone)",
              textDecoration: "line-through",
              textDecorationColor: "var(--babylon-laser)",
              maxWidth: "32%",
            }}
          >
            &ldquo;{active.c}&rdquo;
          </span>
          <span
            className="shrink-0 text-[14px]"
            style={{ color: "var(--babylon-laser)", fontFamily: "var(--font-mono)" }}
          >
            {"\u2192"}
          </span>
          <span
            className="truncate text-[12px] font-semibold"
            style={{
              color: "#b4ffd1",
              textShadow: "0 0 6px rgba(95,191,122,0.4)",
              maxWidth: "32%",
              fontFamily: "var(--font-mono)",
            }}
          >
            {active.l}
          </span>
          <span
            className="shrink-0 px-2 py-0.5 text-[9px]"
            style={{
              color: "var(--babylon-rupture)",
              border: "1px solid rgba(212,160,44,0.4)",
              borderRadius: 3,
              fontFamily: "var(--font-mono)",
              letterSpacing: "0.18em",
              textTransform: "uppercase",
            }}
          >
            FILTER - {active.filter}
          </span>
          <span
            className="min-w-0 flex-1 truncate text-[12px]"
            style={{ color: "var(--babylon-fog)" }}
          >
            {active.note}
          </span>
        </div>
      ) : (
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <span className="truncate text-[12px]" style={{ color: "var(--babylon-fog)" }}>
            Hover a flagged term to see how the same fact is rendered across registers.
          </span>
          <div className="ml-auto flex shrink-0 gap-3">
            <span
              className="text-[10px]"
              style={{
                color: "var(--babylon-ash)",
                fontFamily: "var(--font-mono)",
                letterSpacing: "0.14em",
              }}
            >
              EUPHEMISMS{" "}
              <span style={{ color: "var(--babylon-laser)", fontWeight: 700 }}>{total}</span>
            </span>
            <span
              className="text-[10px]"
              style={{
                color: "var(--babylon-ash)",
                fontFamily: "var(--font-mono)",
                letterSpacing: "0.14em",
              }}
            >
              FILTER HITS{" "}
              <span style={{ color: "var(--babylon-heat)", fontWeight: 700 }}>{filterTotal}</span>
            </span>
          </div>
        </div>
      )}

      <div className="flex shrink-0 items-center gap-2">
        <label className="flex cursor-pointer items-center gap-1.5">
          <span
            className="text-[9px]"
            style={{
              color: "var(--babylon-fog)",
              fontFamily: "var(--font-mono)",
              letterSpacing: "0.16em",
            }}
          >
            ALWAYS ON
          </span>
          <span
            className="relative rounded-full transition-colors"
            style={{
              width: 22,
              height: 12,
              background: euphAlways ? "var(--babylon-spire)" : "var(--babylon-rebar)",
            }}
          >
            <span
              className="absolute rounded-full transition-all"
              style={{
                top: 1,
                left: euphAlways ? 11 : 1,
                width: 10,
                height: 10,
                background: euphAlways ? "var(--babylon-void)" : "var(--babylon-fog)",
              }}
            />
          </span>
          <input
            type="checkbox"
            checked={euphAlways}
            onChange={(e) => setEuphAlways(e.target.checked)}
            style={{ display: "none" }}
          />
        </label>
        <button className="wire-btn-ghost" onClick={onOpenPatterns}>
          Open Patterns {"\u25b8"}
        </button>
      </div>
    </div>
  );
}
