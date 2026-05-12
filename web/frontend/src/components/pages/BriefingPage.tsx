/**
 * BriefingPage — newspaper-style summary of the current tick.
 *
 * Spec 061 US3 (T055, T056): wired to the real engine via
 * useGameState (snapshot + events) and useTimeseries (sparklines).
 * Replaces the prior fixture-driven mock.
 *
 * Layout: left map panel (60%), right dispatch panel (40%),
 * bottom full-width sparkline strip.
 */

import { useNavigate, useParams } from "react-router";
import { BblBadge, BblData, BblLabel, BblPanel, Sparkline } from "@/components/bbl";
import { PageHeader } from "@/components/layout/PageHeader";
import { HexMapPlaceholder } from "@/components/viz";
import { useGameState } from "@/hooks/useGameState";
import { useTimeseries } from "@/hooks/useTimeseries";
import type { GameEvent } from "@/types/game";

/** Spec 061 FR-012: severity → badge color token. */
function severityColor(severity: GameEvent["severity"]): string {
  switch (severity) {
    case "critical":
      return "#e04040";
    case "warning":
      return "#e0a030";
    case "informational":
    default:
      return "#787878";
  }
}

/** Drop the all-null tail so Sparkline doesn't render with gaps. */
function compactSeries(series: (number | null)[]): number[] {
  return series.filter((v): v is number => typeof v === "number");
}

export function BriefingPage() {
  const navigate = useNavigate();
  const { id: gameId } = useParams<{ id: string }>();
  const { snapshot } = useGameState(gameId ?? null);
  const { data: timeseries } = useTimeseries(gameId ?? null);

  const tick = snapshot?.tick ?? 0;
  const events: GameEvent[] = snapshot?.events ?? [];

  // Sort: critical first, then warning, then informational; within each
  // bucket, newest tick first.
  const SEVERITY_ORDER: Record<GameEvent["severity"], number> = {
    critical: 0,
    warning: 1,
    informational: 2,
  };
  const dispatchEvents = [...events]
    .sort((a, b) => {
      const sa = SEVERITY_ORDER[a.severity] ?? 2;
      const sb = SEVERITY_ORDER[b.severity] ?? 2;
      if (sa !== sb) return sa - sb;
      return b.tick - a.tick;
    })
    .slice(0, 3);

  // Player-controlled org subtitle (best-effort — falls back to "player").
  const playerOrgShort =
    (snapshot?.organizations ?? []).find((o) => Boolean(o.player_controlled))?.short_name ??
    "player";

  const metrics: { label: string; data: number[]; color: string }[] = [
    { label: "RENT", data: compactSeries(timeseries.imperial_rent), color: "#a070d0" },
    { label: "CON", data: compactSeries(timeseries.consciousness), color: "#80b0e0" },
    { label: "SOL", data: compactSeries(timeseries.solidarity), color: "#40c040" },
    { label: "HEAT", data: compactSeries(timeseries.heat), color: "#e04040" },
    { label: "WEALTH", data: compactSeries(timeseries.wealth), color: "#c8a860" },
    { label: "BIOCAP", data: compactSeries(timeseries.biocapacity), color: "#7ab038" },
  ];

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <PageHeader
        title="Briefing"
        subtitle={`Tick ${tick} — Situation report for ${playerOrgShort}`}
        breadcrumbs={["Operation", "Briefing"]}
        right={
          <div className="flex items-center gap-2">
            <BblBadge color="#c8a860">tick</BblBadge>
            <BblData color="#c8a860" size={16}>
              {tick}
            </BblData>
          </div>
        }
      />

      {/* Main content: Map + Dispatch */}
      <div className="grid min-h-0 flex-1 grid-cols-[3fr_2fr] gap-3 p-3">
        {/* Map placeholder */}
        <BblPanel title="Situation Map" right={<BblBadge color="#787878">heat layer</BblBadge>}>
          <HexMapPlaceholder className="h-full min-h-[200px]" />
        </BblPanel>

        {/* Dispatch panel */}
        <div className="flex min-h-0 flex-col gap-3">
          {/* Lead dispatch */}
          <BblPanel title="Priority Dispatch" accent="#e04040">
            <div className="flex flex-col gap-3">
              {dispatchEvents.length === 0 && (
                <div className="rounded border border-soot bg-void p-3 text-[10px] text-ash">
                  No events this tick.
                </div>
              )}
              {dispatchEvents.map((evt) => (
                <div key={evt.id} className="rounded border border-soot bg-void p-3">
                  <div className="mb-1 flex items-center gap-2">
                    <BblBadge color={severityColor(evt.severity)}>{evt.severity}</BblBadge>
                    <span className="text-[9px] text-chassis">T-{evt.tick}</span>
                  </div>
                  <div className="text-[12px] font-semibold text-bone">{evt.title}</div>
                  {evt.body && (
                    <div className="mt-1 text-[10px] leading-relaxed text-ash">{evt.body}</div>
                  )}
                </div>
              ))}
            </div>
          </BblPanel>

          {/* CTA */}
          <button
            onClick={() => navigate(`/games/${gameId}/orgs`)}
            className="shrink-0 rounded-md bg-gold px-4 py-3 text-[12px] font-bold uppercase tracking-[0.2em] text-void transition-all hover:brightness-110"
          >
            Take Actions ▸
          </button>
        </div>
      </div>

      {/* Bottom: Sparkline strip */}
      <div className="shrink-0 border-t border-soot bg-dark-metal px-3 py-2">
        <div className="mb-1">
          <BblLabel color="#c8a860">Key Metrics</BblLabel>
        </div>
        <div className="grid grid-cols-6 gap-4">
          {metrics.map((m) => (
            <Sparkline key={m.label} data={m.data} color={m.color} label={m.label} w={120} h={28} />
          ))}
        </div>
      </div>
    </div>
  );
}
