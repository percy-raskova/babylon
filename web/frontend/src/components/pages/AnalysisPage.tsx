/**
 * AnalysisPage — post-MVP analysis dashboard.
 *
 * Displays the topology graph, time-series analysis grid, and comparative metrics.
 * Currently uses placeholder visualizations.
 */

import { PageHeader } from "@/components/layout/PageHeader";
import { BblPanel, BblBadge, BblLabel, Sparkline } from "@/components/bbl";
import { TopologyGraphPlaceholder } from "@/components/viz";
import { TIMESERIES } from "@/fixtures/v2-mock-data";

export function AnalysisPage() {
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
        title="Analysis"
        subtitle="Time-series analysis and social graph topology"
        breadcrumbs={["Operation", "Analysis"]}
        right={<BblBadge color="#a070d0">post-MVP</BblBadge>}
      />

      <div className="grid min-h-0 flex-1 grid-cols-2 gap-3 p-3">
        {/* Topology graph */}
        <BblPanel
          title="Social Graph Topology"
          right={<BblBadge color="#787878">d3-force</BblBadge>}
        >
          <TopologyGraphPlaceholder className="h-full min-h-[300px]" />
        </BblPanel>

        {/* Time series grid */}
        <BblPanel
          title="Time-Series Dashboard"
          right={<BblBadge color="#787878">UpSet plot pending</BblBadge>}
        >
          <div className="flex flex-col gap-4">
            <BblLabel color="#c8a860">Aggregate Metrics (10-tick window)</BblLabel>
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
              Correlation matrix, UpSet intersection plots, and dialectical phase-space projections
              will render here.
            </div>
          </div>
        </BblPanel>
      </div>
    </div>
  );
}
