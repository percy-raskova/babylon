/**
 * AnalysisPage — post-MVP analysis dashboard.
 *
 * Spec 061 US6 (T103): wired to useTimeseries; the topology graph
 * remains a placeholder (Constitution-aligned d3-force renderer is
 * out of scope per spec 061 plan.md).
 */

import { useParams } from "react-router";
import { BblBadge, BblLabel, BblPanel, Sparkline } from "@/components/bbl";
import { PageHeader } from "@/components/layout/PageHeader";
import { TopologyGraphPlaceholder } from "@/components/viz";
import { TradePanel } from "./TradePanel";
import { useTimeseries } from "@/hooks/useTimeseries";

function compactSeries(series: (number | null)[]): number[] {
  return series.filter((v): v is number => typeof v === "number");
}

export function AnalysisPage() {
  const { id: gameId } = useParams<{ id: string }>();
  const { data: ts } = useTimeseries(gameId ?? null);

  const metrics: { label: string; data: number[]; color: string }[] = [
    { label: "RENT", data: compactSeries(ts.imperial_rent), color: "#a070d0" },
    { label: "CON", data: compactSeries(ts.consciousness), color: "#80b0e0" },
    { label: "SOL", data: compactSeries(ts.solidarity), color: "#40c040" },
    { label: "HEAT", data: compactSeries(ts.heat), color: "#e04040" },
    { label: "WEALTH", data: compactSeries(ts.wealth), color: "#c8a860" },
    { label: "BIOCAP", data: compactSeries(ts.biocapacity), color: "#7ab038" },
  ];

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <PageHeader
        title="Analysis"
        subtitle="Time-series analysis and social graph topology"
        breadcrumbs={["Operation", "Analysis"]}
        right={<BblBadge color="#a070d0">post-MVP</BblBadge>}
      />

      <div className="grid min-h-0 flex-1 grid-cols-2 gap-3 p-3">
        <BblPanel
          title="Social Graph Topology"
          right={<BblBadge color="#787878">d3-force</BblBadge>}
        >
          <TopologyGraphPlaceholder className="h-full min-h-[300px]" />
        </BblPanel>

        <BblPanel
          title="Time-Series Dashboard"
          right={<BblBadge color="#787878">{ts.ticks.length} ticks</BblBadge>}
        >
          <div className="flex flex-col gap-4">
            <BblLabel color="#c8a860">Aggregate Metrics</BblLabel>
            <div className="grid grid-cols-2 gap-6">
              {metrics.map((m) => (
                <Sparkline
                  key={m.label}
                  data={m.data}
                  color={m.color}
                  label={m.label}
                  w={200}
                  h={50}
                />
              ))}
            </div>

            <BblLabel color="#787878">Correlations</BblLabel>
            <div className="rounded border border-dashed border-soot bg-void p-4 text-center text-[11px] text-chassis">
              Correlation matrix and UpSet intersection plots are out of scope for spec 061.
            </div>
          </div>
        </BblPanel>
      </div>

      <div className="grid grid-cols-1 gap-3 p-3 pt-0">
        <TradePanel gameId={gameId ?? null} />
      </div>
    </div>
  );
}
