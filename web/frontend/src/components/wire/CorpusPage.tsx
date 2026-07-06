/**
 * CorpusPage - RAG retrieval browser tab.
 * Spec 094: ports CorpusPage from wire-pages.jsx.
 */

import { useState } from "react";
import type { WireStory } from "@/types/wire";

interface Props {
  story: WireStory | null;
}

interface ChunkEntry {
  chunk: string;
  sim: number;
  src: string;
  kind: string;
  id: string;
  channel: "continental" | "liberated" | "intel";
  note?: string;
}

function channelColor(c: string): string {
  if (c === "continental") return "var(--babylon-cadre)";
  if (c === "liberated") return "var(--babylon-solidarity)";
  return "var(--babylon-rupture)";
}

function simColor(sim: number): string {
  if (sim > 0.85) return "var(--babylon-spire)";
  if (sim > 0.75) return "var(--babylon-cadre)";
  return "var(--babylon-ash)";
}

export function CorpusPage({ story }: Props) {
  const [channelFilter, setChannelFilter] = useState<string>("all");

  if (!story) {
    return (
      <div
        className="flex h-full items-center justify-center text-sm"
        style={{ color: "var(--babylon-ash)" }}
      >
        No active story
      </div>
    );
  }

  const chunks: ChunkEntry[] = [];
  story.continental.bibliography.forEach((b) =>
    chunks.push({
      chunk: b.chunk,
      sim: b.sim,
      src: b.src,
      kind: b.kind,
      id: b.id,
      channel: "continental",
    }),
  );
  story.liberated.paragraphs.forEach((p) => {
    if (p.margin) {
      chunks.push({
        chunk: p.margin.chunk,
        sim: 0.85,
        src: p.margin.ref,
        kind: "field witness",
        id: p.margin.ref,
        channel: "liberated",
        note: p.margin.note,
      });
    }
  });
  story.intel.refs.forEach((r) =>
    chunks.push({ chunk: r.id, sim: r.sim, src: r.src, kind: r.tag, id: r.id, channel: "intel" }),
  );

  const shown =
    channelFilter === "all" ? chunks : chunks.filter((c) => c.channel === channelFilter);

  return (
    <div className="h-full overflow-y-auto p-4" style={{ background: "var(--babylon-void)" }}>
      <div className="mb-4 flex items-baseline justify-between">
        <div>
          <div className="wire-label mb-1">{"\u25b8"} Corpus retrieval</div>
          <div className="text-[18px] font-bold" style={{ color: "var(--babylon-bone)" }}>
            The Archive
          </div>
          <div
            className="mt-1 text-[11px]"
            style={{
              color: "var(--babylon-fog)",
              fontFamily: "var(--font-mono)",
              letterSpacing: "0.14em",
            }}
          >
            {chunks.length} CHUNKS RETRIEVED FOR {story.id}
          </div>
        </div>
        <div className="flex gap-1">
          {["all", "continental", "liberated", "intel"].map((k) => (
            <button
              key={k}
              onClick={() => setChannelFilter(k)}
              className={`wire-btn-ghost ${channelFilter === k ? "active" : ""}`}
            >
              {k === "all" ? "All" : k.charAt(0).toUpperCase() + k.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-2">
        {shown.map((c, idx) => (
          <div
            key={`${c.chunk}-${idx}`}
            className="grid items-center gap-3 rounded border p-3"
            style={{
              background: "var(--babylon-concrete)",
              borderColor: "var(--babylon-rebar)",
              borderLeft: `3px solid ${channelColor(c.channel)}`,
              gridTemplateColumns: "auto 1fr auto",
            }}
          >
            <div className="flex min-w-[120px] flex-col gap-1">
              <span className="wire-label" style={{ color: channelColor(c.channel) }}>
                {c.channel}
              </span>
              <span
                className="text-[11px]"
                style={{ color: "var(--babylon-bone)", fontFamily: "var(--font-mono)" }}
              >
                {c.chunk}
              </span>
            </div>
            <div className="flex min-w-0 flex-col gap-0.5">
              <span
                className="text-[12px]"
                style={{ color: "var(--babylon-bone)", fontWeight: 500 }}
              >
                {c.src}
              </span>
              <span
                className="text-[10px] uppercase"
                style={{
                  color: "var(--babylon-ash)",
                  fontFamily: "var(--font-mono)",
                  letterSpacing: "0.12em",
                }}
              >
                {c.kind} - {c.id}
              </span>
              {c.note && (
                <span className="mt-1 text-[11px]" style={{ color: "var(--babylon-fog)" }}>
                  &ldquo;{c.note}&rdquo;
                </span>
              )}
            </div>
            <div className="flex min-w-[90px] flex-col items-end gap-1">
              <span className="wire-label">similarity</span>
              <span className="text-[14px] font-bold" style={{ color: simColor(c.sim) }}>
                {c.sim.toFixed(2)}
              </span>
              <div
                className="h-0.5 w-[70px] rounded-full overflow-hidden"
                style={{ background: "var(--babylon-rebar)" }}
              >
                <div
                  style={{ width: `${c.sim * 100}%`, height: "100%", background: simColor(c.sim) }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div
        className="mt-4 rounded border border-dashed p-3"
        style={{ borderColor: "var(--babylon-rebar)" }}
      >
        <div className="wire-label mb-1" style={{ color: "var(--babylon-rupture)" }}>
          Note - Archive is observer-only
        </div>
        <div className="text-[12px]" style={{ color: "var(--babylon-fog)", lineHeight: 1.55 }}>
          Per Constitution VIII, The Archive provides semantic history for narrative but never
          controls simulation state. Retrieval here is read-only.
        </div>
      </div>
    </div>
  );
}
