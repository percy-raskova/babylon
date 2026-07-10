/**
 * PatternsPage - Manufacturing Consent dashboard.
 * Spec 094: ports PatternsPage from wire-pages.jsx.
 */

import type { EuphemismEntry, ManufacturingConsentFilter, WireStory } from "@/types/wire";

interface Props {
  euphemisms: Record<string, EuphemismEntry>;
  filters: ManufacturingConsentFilter[];
  story: WireStory | null;
}

export function PatternsPage({ euphemisms, filters, story }: Props) {
  const totalHits = filters.reduce((s, f) => s + f.hits, 0);
  const consentScore = Math.min(100, Math.round((totalHits / 20) * 100));
  const euphCount = Object.keys(euphemisms).length;

  return (
    <div className="h-full overflow-y-auto p-4" style={{ background: "var(--babylon-void)" }}>
      <div className="mb-4">
        <div className="wire-label mb-1">{"\u25b8"} Pattern Analysis</div>
        <div className="text-[18px] font-bold" style={{ color: "var(--babylon-bone)" }}>
          Manufacturing Consent - live audit
        </div>
        <div
          className="mt-1 text-[11px]"
          style={{
            color: "var(--babylon-fog)",
            fontFamily: "var(--font-mono)",
            letterSpacing: "0.14em",
          }}
        >
          {story ? `STORY ${story.id}` : "NO ACTIVE STORY"} - {totalHits} FILTER HITS - {euphCount}{" "}
          EUPHEMISMS
        </div>
      </div>

      {/* Score panel */}
      <div className="mb-4 grid gap-3" style={{ gridTemplateColumns: "1fr 300px" }}>
        <div
          className="rounded border p-4"
          style={{ background: "var(--babylon-concrete)", borderColor: "var(--babylon-rebar)" }}
        >
          <div className="wire-label mb-1">Manufactured-consent score</div>
          <div className="flex items-baseline gap-3">
            <span
              className="text-[48px] font-bold leading-none"
              style={{ color: "var(--babylon-laser)", textShadow: "0 0 18px rgba(255,51,68,0.4)" }}
            >
              {consentScore}
            </span>
            <span
              className="text-[14px]"
              style={{ color: "var(--babylon-fog)", fontFamily: "var(--font-mono)" }}
            >
              / 100
            </span>
          </div>
        </div>
        <div
          className="rounded border p-3"
          style={{ background: "var(--babylon-concrete)", borderColor: "var(--babylon-rebar)" }}
        >
          <div className="wire-label mb-2" style={{ color: "var(--babylon-rupture)" }}>
            The thesis
          </div>
          <div
            className="text-[12px] italic"
            style={{ color: "var(--babylon-fog)", lineHeight: 1.6 }}
          >
            &ldquo;The mass media serve as a system for communicating messages and symbols to the
            general populace.&rdquo;
          </div>
          <div
            className="mt-2 text-[10px]"
            style={{
              color: "var(--babylon-ash)",
              fontFamily: "var(--font-mono)",
              letterSpacing: "0.14em",
            }}
          >
            {"\u2014"} HERMAN &amp; CHOMSKY - 1988
          </div>
        </div>
      </div>

      {/* Five filters */}
      <div className="mb-4">
        <div className="wire-label mb-2">{"\u25b8"} Five filters</div>
        <div
          className="grid gap-2"
          style={{ gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))" }}
        >
          {filters.map((f) => (
            <div
              key={f.id}
              className="rounded border p-3"
              style={{ background: "var(--babylon-concrete)", borderColor: "var(--babylon-rebar)" }}
            >
              <div className="mb-1 flex items-baseline justify-between">
                <span
                  className="text-[13px] font-semibold"
                  style={{ color: "var(--babylon-bone)" }}
                >
                  {f.label}
                </span>
                <span
                  className="text-[13px] font-bold"
                  style={{ color: f.color, fontFamily: "var(--font-mono)" }}
                >
                  x{f.hits}
                </span>
              </div>
              <div
                className="mb-2 text-[11px]"
                style={{ color: "var(--babylon-fog)", lineHeight: 1.5 }}
              >
                {f.desc}
              </div>
              <div
                className="h-1 rounded-full overflow-hidden"
                style={{ background: "var(--babylon-rebar)" }}
              >
                <div
                  style={{
                    width: `${(Math.min(f.hits, 5) / 5) * 100}%`,
                    height: "100%",
                    background: f.color,
                    boxShadow: `0 0 8px ${f.color}`,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Euphemism table */}
      {euphCount > 0 && (
        <div>
          <div className="wire-label mb-2">
            {"\u25b8"} Euphemism map - {euphCount} detected
          </div>
          <div
            className="rounded border overflow-hidden"
            style={{ background: "var(--babylon-concrete)", borderColor: "var(--babylon-rebar)" }}
          >
            <div
              className="grid gap-3 px-4 py-2 border-b"
              style={{
                gridTemplateColumns: "1fr 1fr 1.2fr 130px",
                borderColor: "var(--babylon-rebar)",
                background: "rgba(255,255,255,0.02)",
              }}
            >
              <span className="wire-label" style={{ color: "var(--babylon-cadre)" }}>
                Continental said
              </span>
              <span className="wire-label" style={{ color: "var(--babylon-solidarity)" }}>
                Free Signal said
              </span>
              <span className="wire-label">Editorial intervention</span>
              <span className="wire-label" style={{ color: "var(--babylon-ash)" }}>
                Filter
              </span>
            </div>
            {Object.entries(euphemisms).map(([id, e]) => (
              <div
                key={id}
                className="grid gap-3 px-4 py-2 border-b items-baseline"
                style={{
                  gridTemplateColumns: "1fr 1fr 1.2fr 130px",
                  borderColor: "var(--babylon-rebar)",
                }}
              >
                <span
                  className="text-[12px]"
                  style={{
                    color: "var(--babylon-bone)",
                    textDecoration: "line-through",
                    textDecorationColor: "var(--babylon-laser)",
                  }}
                >
                  &ldquo;{e.c}&rdquo;
                </span>
                <span
                  className="text-[11px] font-semibold"
                  style={{ color: "#b4ffd1", fontFamily: "var(--font-mono)" }}
                >
                  {e.l}
                </span>
                <span
                  className="text-[11px]"
                  style={{ color: "var(--babylon-fog)", lineHeight: 1.5 }}
                >
                  {e.note}
                </span>
                <span
                  className="text-[9px] uppercase"
                  style={{
                    color: "var(--babylon-ash)",
                    fontFamily: "var(--font-mono)",
                    letterSpacing: "0.14em",
                  }}
                >
                  {e.filter}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
