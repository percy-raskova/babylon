/**
 * LiberatedColumn — Free Signal pirate-radio phosphor terminal.
 * Spec 094: ports wire-liberated.jsx as fresh TypeScript.
 */

import type { WireStory, WireRun } from "@/types/wire";

interface Props {
  story: WireStory | null;
  activeEuph: string | null;
  setActiveEuph: (id: string | null) => void;
  euphAlways: boolean;
}

function renderRun(
  run: WireRun,
  idx: string,
  activeEuph: string | null,
  setActiveEuph: (id: string | null) => void,
  euphAlways: boolean,
) {
  if (typeof run === "string") return run;
  if ("euph" in run) {
    return (
      <span
        key={`euph-${idx}`}
        className={`euph phos ${activeEuph === run.euph ? "active" : ""}`}
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

export function LiberatedColumn({ story, activeEuph, setActiveEuph, euphAlways }: Props) {
  if (!story) {
    return (
      <div className="col-wrap col-liberated">
        <div
          className="col-body flex items-center justify-center text-sm"
          style={{ color: "var(--babylon-ash)" }}
        >
          No active story
        </div>
      </div>
    );
  }

  const l = story.liberated;

  return (
    <div className="col-wrap col-liberated">
      <div
        className="col-head"
        style={{ background: "rgba(95,191,122,0.04)", borderBottomColor: "rgba(127,224,161,0.18)" }}
      >
        <span className="wire-label" style={{ color: "#7fe0a1" }}>
          CHANNEL - LIBERATED
        </span>
        <span className="wire-kicker" style={{ color: "rgba(127,224,161,0.6)" }}>
          OP // {l.operator}
        </span>
      </div>

      <div className="col-body" style={{ padding: 0 }}>
        {/* Signal head */}
        <div
          className="flex justify-between items-start gap-3 border-b px-5 py-3"
          style={{ borderColor: "rgba(127,224,161,0.32)", borderBottomStyle: "dashed" }}
        >
          <div className="flex flex-col gap-1">
            <div
              className="text-[11px] font-bold"
              style={{
                letterSpacing: "0.3em",
                color: "#b4ffd1",
                textShadow: "0 0 8px rgba(95,191,122,0.55)",
              }}
            >
              {l.brand} - {l.callsign}
            </div>
          </div>
        </div>

        <div
          className="px-3 py-1 text-[10px]"
          style={{
            color: "rgba(127,224,161,0.72)",
            borderTop: "1px dashed rgba(127,224,161,0.22)",
            borderBottom: "1px dashed rgba(127,224,161,0.22)",
            fontFamily: "var(--font-mono)",
            letterSpacing: "0.14em",
          }}
        >
          {l.pre}
        </div>

        {/* Hed */}
        <div className="px-5 pt-3 pb-1">
          <h1 className="hed">{l.hed}</h1>
        </div>

        {/* Story body */}
        <div className="py-2">
          {l.paragraphs.map((para, pi) => (
            <div
              key={pi}
              className="grid gap-3 px-5 py-2"
              style={{
                gridTemplateColumns: "1fr",
                borderBottom:
                  pi < l.paragraphs.length - 1 ? "1px dashed rgba(127,224,161,0.1)" : "none",
              }}
            >
              <p>
                <span className="phos">
                  {para.body.map((run, ri) =>
                    renderRun(run, `${pi}-${ri}`, activeEuph, setActiveEuph, euphAlways),
                  )}
                </span>
                {pi === l.paragraphs.length - 1 && <span className="cursor" />}
              </p>

              {para.margin && (
                <div
                  className={`tilt-${(pi % 3) + 1} text-[14px]`}
                  style={{
                    color: "#ffd76b",
                    fontFamily: "var(--font-mono)",
                    textShadow: "0 0 6px rgba(217,160,44,0.4)",
                  }}
                >
                  <span className="inline-block mr-1">{"\u21b3"}</span>
                  {para.margin.note}
                  <span className="block text-[12px]" style={{ color: "#ffe9a3", opacity: 0.85 }}>
                    {"\u2014 "}
                    {para.margin.ref}
                  </span>
                </div>
              )}
            </div>
          ))}
        </div>

        <div
          className="px-3 py-1 text-[10px]"
          style={{
            color: "rgba(127,224,161,0.72)",
            borderTop: "1px dashed rgba(127,224,161,0.22)",
            borderBottom: "1px dashed rgba(127,224,161,0.22)",
            fontFamily: "var(--font-mono)",
            letterSpacing: "0.14em",
          }}
        >
          {l.post}
        </div>
      </div>
    </div>
  );
}
