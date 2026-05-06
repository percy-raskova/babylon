/**
 * BriefingPage — newspaper-style summary of the current tick.
 *
 * Layout: left map panel (60%), right dispatch panel (40%),
 * bottom full-width sparkline strip.
 *
 * Replaces the old GameShell as the /games/:id landing page.
 */

import { useNavigate, useParams } from "react-router";
import { PageHeader } from "@/components/layout/PageHeader";
import { BblPanel, BblBadge, BblData, BblLabel, Sparkline } from "@/components/bbl";
import { HexMapPlaceholder } from "@/components/viz";
import { TICK, EVENTS, TIMESERIES, ORGS } from "@/fixtures/v2-mock-data";

export function BriefingPage() {
  const navigate = useNavigate();
  const { id: gameId } = useParams<{ id: string }>();
  const criticalEvents = EVENTS.filter(
    (e) => e.severity === "critical" || e.severity === "warning",
  );
  const playerOrg = ORGS.find((o) => o.player_controlled);

  const metrics: { label: string; data: number[]; color: string }[] = [
    { label: "RENT", data: TIMESERIES.imperial_rent, color: "#a070d0" },
    { label: "CON", data: TIMESERIES.consciousness, color: "#80b0e0" },
    { label: "SOL", data: TIMESERIES.solidarity, color: "#40c040" },
    { label: "HEAT", data: TIMESERIES.heat, color: "#e04040" },
    { label: "WEALTH", data: TIMESERIES.wealth, color: "#c8a860" },
    { label: "BIOCAP", data: TIMESERIES.biocapacity, color: "#7ab038" },
  ];

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <PageHeader
        title="Briefing"
        subtitle={`Tick ${TICK} — Situation report for ${playerOrg?.short ?? "player"}`}
        breadcrumbs={["Operation", "Briefing"]}
        right={
          <div className="flex items-center gap-2">
            <BblBadge color="#c8a860">tick</BblBadge>
            <BblData color="#c8a860" size={16}>
              {TICK}
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
              {criticalEvents.slice(0, 3).map((evt) => (
                <div key={evt.id} className="rounded border border-soot bg-void p-3">
                  <div className="mb-1 flex items-center gap-2">
                    <BblBadge color={evt.severity === "critical" ? "#e04040" : "#e0a030"}>
                      {evt.severity}
                    </BblBadge>
                    <span className="text-[9px] text-chassis">T-{evt.tick}</span>
                  </div>
                  <div className="text-[12px] font-semibold text-bone">{evt.title}</div>
                  <div className="mt-1 text-[10px] leading-relaxed text-ash">{evt.body}</div>
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
