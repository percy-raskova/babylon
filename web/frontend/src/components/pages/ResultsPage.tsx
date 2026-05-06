/**
 * ResultsPage — tick resolution summary.
 * Shows player actions, NPC actions, and tensor diff.
 */

import { PageHeader } from "@/components/layout/PageHeader";
import { BblPanel, BblBadge, BblData, BblLabel } from "@/components/bbl";
import { TICK, ORGS } from "@/fixtures/v2-mock-data";

export function ResultsPage() {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <PageHeader
        title="Results"
        subtitle={`Tick ${TICK} resolution summary`}
        breadcrumbs={["Operation", "Results"]}
        right={<BblBadge color="#787878">read-only</BblBadge>}
      />

      <div className="grid min-h-0 flex-1 grid-cols-2 gap-3 p-3">
        {/* Player Actions */}
        <BblPanel title="Player Actions" accent="#c8a860">
          <table className="w-full text-left text-[11px]">
            <thead>
              <tr className="border-b border-soot text-[9px] uppercase tracking-wider text-ash">
                <th className="pb-2">Org</th>
                <th className="pb-2">Verb</th>
                <th className="pb-2">Target</th>
                <th className="pb-2">Outcome</th>
              </tr>
            </thead>
            <tbody>
              {ORGS.filter((o) => o.player_controlled && o.last_action).map((o) => (
                <tr key={o.id} className="border-b border-soot/50">
                  <td className="py-2 font-semibold text-bone">{o.short}</td>
                  <td className="py-2">
                    <BblBadge color="#c8a860">{o.last_action!.verb}</BblBadge>
                  </td>
                  <td className="py-2 text-ash">{o.last_action!.target}</td>
                  <td className="py-2">
                    <BblData color="#40c040" size={10}>
                      {o.last_action!.outcome}
                    </BblData>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </BblPanel>

        {/* NPC Actions */}
        <BblPanel title="NPC Actions" accent="#787878">
          <div className="flex flex-col gap-2">
            {ORGS.filter((o) => !o.player_controlled).map((o) => (
              <div key={o.id} className="rounded border border-soot bg-void p-2">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-semibold text-bone">{o.short}</span>
                  <BblBadge color="#787878">{o.ooda_phase}</BblBadge>
                </div>
                <div className="mt-1 text-[9px] text-ash">
                  OODA cycle in progress · last observed T-{o.last_observed_tick ?? "?"}
                </div>
              </div>
            ))}
          </div>
        </BblPanel>

        {/* Tensor diff */}
        <BblPanel title="State Tensor Diff" style={{ gridColumn: "1 / span 2" }}>
          <div className="grid grid-cols-6 gap-4">
            {[
              { label: "RENT", value: 0.31, delta: +0.02, color: "#a070d0" },
              { label: "CON", value: 0.38, delta: +0.04, color: "#80b0e0" },
              { label: "SOL", value: 0.42, delta: +0.03, color: "#40c040" },
              { label: "HEAT", value: 0.71, delta: +0.12, color: "#e04040" },
              { label: "WEALTH", value: 0.32, delta: -0.01, color: "#c8a860" },
              { label: "BIOCAP", value: 0.51, delta: -0.02, color: "#7ab038" },
            ].map((m) => (
              <div key={m.label} className="flex flex-col gap-1">
                <BblLabel>{m.label}</BblLabel>
                <BblData color={m.color} size={14}>
                  {m.value.toFixed(3)}
                </BblData>
                <span
                  className={`font-mono text-[10px] ${
                    m.delta > 0 ? "text-data-green" : "text-phosphor-red"
                  }`}
                >
                  {m.delta > 0 ? "▲" : "▼"} {Math.abs(m.delta).toFixed(3)}
                </span>
              </div>
            ))}
          </div>
        </BblPanel>
      </div>
    </div>
  );
}
