/**
 * IntelColumn - SIGINT cable column with structured fields + redactions.
 * Spec 094: ports wire-intel.jsx as fresh TypeScript.
 */

import type { WireStory } from "@/types/wire";

interface Props {
  story: WireStory | null;
}

/** Render text with redaction bars. */
function renderRedacted(s: string) {
  const parts = s.split(/(\u25ae+)/g);
  return parts.map((p, idx) =>
    /^\u25ae+$/.test(p) ? (
      <span key={idx} className="redact-dark">
        {p}
      </span>
    ) : (
      <span key={idx}>{p}</span>
    ),
  );
}

export function IntelColumn({ story }: Props) {
  if (!story) {
    return (
      <div className="col-wrap col-intel">
        <div
          className="col-body flex items-center justify-center text-sm"
          style={{ color: "var(--babylon-ash)" }}
        >
          No active story
        </div>
      </div>
    );
  }

  const i = story.intel;

  return (
    <div className="col-wrap col-intel">
      <div className="col-head">
        <span className="wire-label" style={{ color: "var(--babylon-rupture)" }}>
          CHANNEL - INTEL
        </span>
        <span className="wire-kicker" style={{ color: "var(--babylon-ash)" }}>
          CABLE {i.cable_id}
        </span>
      </div>

      <div className="cls-bar">{i.classification}</div>

      <div className="col-body">
        <div className="px-5 py-3 border-b" style={{ borderColor: "var(--babylon-rebar)" }}>
          <div className="field-row">
            <span className="k">SUBJ</span>
            <span className="v" style={{ color: "var(--babylon-bone)", fontWeight: 600 }}>
              {i.subj}
            </span>
          </div>
          <div className="field-row">
            <span className="k">ORIGIN</span>
            <span className="v">{renderRedacted(i.origin)}</span>
          </div>
          <div className="field-row">
            <span className="k">ROUTING</span>
            <span className="v flex flex-wrap gap-1">
              {i.routing.map((rr, idx) => (
                <span
                  key={idx}
                  className="inline-block border px-1.5 py-0.5 text-[9px]"
                  style={{
                    borderColor: "var(--babylon-rebar)",
                    color: "var(--babylon-fog)",
                    background: "rgba(255,255,255,0.02)",
                  }}
                >
                  {renderRedacted(rr)}
                </span>
              ))}
            </span>
          </div>
          <div className="field-row">
            <span className="k">CAVEAT</span>
            <span className="v" style={{ color: "var(--babylon-laser)", fontWeight: 600 }}>
              {i.caveat}
            </span>
          </div>
        </div>

        <div className="px-5 py-3 border-b" style={{ borderColor: "var(--babylon-rebar)" }}>
          <div className="wire-label mb-2" style={{ color: "var(--babylon-rupture)" }}>
            {"\u25b8"} Structured fields
          </div>
          {i.fields.map(([k, v]) => (
            <div key={k} className="field-row">
              <span className="k">{k}</span>
              <span className="v">{renderRedacted(v)}</span>
            </div>
          ))}
        </div>

        {i.assessment.length > 0 && (
          <div className="px-5 py-3 border-b" style={{ borderColor: "var(--babylon-rebar)" }}>
            <div className="wire-label mb-2" style={{ color: "var(--babylon-rupture)" }}>
              {"\u25b8"} Assessment
            </div>
            {i.assessment.map((a, idx) => (
              <p key={idx} className="assess">
                <span style={{ color: "var(--babylon-ash)", marginRight: 4 }}>
                  {"\u00a7"}
                  {idx + 1}.
                </span>
                {renderRedacted(a)}
              </p>
            ))}
          </div>
        )}

        {i.refs.length > 0 && (
          <div className="px-5 py-3 border-b" style={{ borderColor: "var(--babylon-rebar)" }}>
            <div className="wire-label mb-2" style={{ color: "var(--babylon-rupture)" }}>
              {"\u25b8"} Corpus references
            </div>
            {i.refs.map((ref, idx) => (
              <div
                key={idx}
                className="grid items-baseline gap-2 py-1"
                style={{
                  gridTemplateColumns: "auto 1fr auto",
                  borderBottom: "1px dotted var(--babylon-rebar)",
                }}
              >
                <span
                  className="text-[10px]"
                  style={{
                    color: "var(--babylon-rupture)",
                    fontFamily: "var(--font-mono)",
                    letterSpacing: "0.14em",
                  }}
                >
                  {ref.tag}
                </span>
                <span className="text-[11px]" style={{ color: "var(--babylon-bone)" }}>
                  {ref.id}
                  <span style={{ color: "var(--babylon-ash)" }}> - {ref.src}</span>
                </span>
                <span className="text-[10px]" style={{ color: "var(--babylon-spire)" }}>
                  sim {ref.sim.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        )}

        <div className="px-5 py-2">
          <div className="field-row">
            <span className="k">DIST</span>
            <span className="v" style={{ color: "var(--babylon-fog)" }}>
              {renderRedacted(i.distribution)}
            </span>
          </div>
        </div>
      </div>

      <div className="cls-bar" style={{ marginTop: "auto" }}>
        {i.classification}
      </div>
    </div>
  );
}
