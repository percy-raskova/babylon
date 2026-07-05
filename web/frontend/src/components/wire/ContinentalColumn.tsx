/**
 * ContinentalColumn — Corporate/Continental press column.
 * Spec 094: ports wire-corporate.jsx as fresh TypeScript.
 */

import type { WireStory, WireRun } from "@/types/wire";

interface Props {
  story: WireStory | null;
  activeEuph: string | null;
  setActiveEuph: (id: string | null) => void;
  activeSup: number | null;
  setActiveSup: (n: number | null) => void;
  euphAlways: boolean;
}

function renderRun(
  run: WireRun,
  idx: string,
  activeEuph: string | null,
  setActiveEuph: (id: string | null) => void,
  activeSup: number | null,
  setActiveSup: (n: number | null) => void,
  euphAlways: boolean,
) {
  if (typeof run === "string") return run;
  if ("sup" in run) {
    return (
      <sup
        key={`sup-${idx}`}
        className={`sup ${activeSup === run.sup ? "active" : ""}`}
        onClick={() => setActiveSup(activeSup === run.sup ? null : run.sup)}
      >
        {run.sup}
      </sup>
    );
  }
  if ("euph" in run) {
    return (
      <span
        key={`euph-${idx}`}
        className={`euph ${activeEuph === run.euph ? "active" : ""}`}
        data-euph={run.euph}
        onMouseEnter={() => setActiveEuph(run.euph)}
        onMouseLeave={() => !euphAlways && setActiveEuph(null)}
        onClick={() => setActiveEuph(activeEuph === run.euph ? null : run.euph)}
      >
        {run.text}
      </span>
    );
  }
  return null;
}

export function ContinentalColumn({
  story,
  activeEuph,
  setActiveEuph,
  activeSup,
  setActiveSup,
  euphAlways,
}: Props) {
  if (!story) {
    return (
      <div className="col-wrap col-continental">
        <div
          className="col-body flex items-center justify-center text-sm"
          style={{ color: "var(--babylon-ash)" }}
        >
          No active story
        </div>
      </div>
    );
  }

  const c = story.continental;

  return (
    <div className="col-wrap col-continental">
      <div className="col-head">
        <span className="wire-label" style={{ color: "var(--babylon-cadre)" }}>
          CHANNEL - CORPORATE
        </span>
        <span className="wire-kicker" style={{ color: "var(--babylon-ash)" }}>
          {c.kicker}
        </span>
      </div>

      <div className="col-body">
        {/* Masthead */}
        <div
          className="flex items-center justify-between border-b px-5 py-3"
          style={{ borderColor: "var(--babylon-wet-steel)" }}
        >
          <div className="flex items-center gap-3">
            <div
              className="flex h-8 w-8 items-center justify-center rounded-full border text-[10px] font-bold"
              style={{ borderColor: "var(--babylon-bone)", color: "var(--babylon-bone)" }}
            >
              {c.monogram}
            </div>
            <div>
              <div
                className="text-[16px] font-bold"
                style={{ letterSpacing: "0.3em", color: "var(--babylon-bone)" }}
              >
                {c.brand}
              </div>
            </div>
          </div>
        </div>

        {/* Story body */}
        <div className="px-5 py-4">
          <div className="wire-kicker mb-2" style={{ color: "var(--babylon-cadre)" }}>
            {c.kicker}
          </div>
          <h1 className="hed mb-2">{c.hed}</h1>
          <p className="dek mb-3">{c.dek}</p>
          <div
            className="mb-4 border-b pb-2 text-[9px]"
            style={{
              borderColor: "var(--babylon-rebar)",
              color: "var(--babylon-ash)",
              fontFamily: "var(--font-mono)",
              letterSpacing: "0.14em",
              textTransform: "uppercase",
            }}
          >
            {c.byline}
          </div>

          {c.paragraphs.map((para, pi) => (
            <p key={pi}>
              {para.map((run, ri) =>
                renderRun(
                  run,
                  `${pi}-${ri}`,
                  activeEuph,
                  setActiveEuph,
                  activeSup,
                  setActiveSup,
                  euphAlways,
                ),
              )}
            </p>
          ))}
        </div>

        {/* Bibliography */}
        {c.bibliography.length > 0 && (
          <div
            className="border-t px-5 py-3"
            style={{ borderColor: "var(--babylon-rebar)", background: "rgba(0,0,0,0.18)" }}
          >
            <div className="wire-label mb-2">References - Retrieved from corpus</div>
            {c.bibliography.map((b) => (
              <div
                key={b.n}
                className="flex gap-2 py-1"
                style={{
                  borderLeft:
                    activeSup === b.n ? "2px solid var(--babylon-spire)" : "2px solid transparent",
                  paddingLeft: 6,
                  background: activeSup === b.n ? "rgba(77,217,230,0.05)" : "transparent",
                }}
              >
                <span className="sup">{b.n}.</span>
                <span
                  className="flex-1 text-[11px]"
                  style={{ fontFamily: "var(--font-mono)", color: "var(--babylon-fog)" }}
                >
                  <span style={{ color: "var(--babylon-bone)" }}>{b.src}</span>
                  <span style={{ color: "var(--babylon-ash)" }}> - {b.kind} - </span>
                  <span style={{ color: "var(--babylon-fog)" }}>{b.id}</span>
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
