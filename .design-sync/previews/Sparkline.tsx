/**
 * Sparkline preview — compact SVG time-series (Briefing/Analysis strips).
 * Pure props, no store. The empty-with-label state is the component's own
 * designed honest-empty (`SparklinePlaceholder`) — a labeled em-dash row
 * that keeps the metrics strip aligned before the first tick lands.
 */
import { Sparkline } from "babylon-cockpit";

function Frame({ children }: { children?: unknown }) {
  return <div className="flex items-start gap-8 bg-void p-4">{children as never}</div>;
}

const RENT_TREND = [
  8.2, 9.6, 10.1, 11.4, 12.0, 13.8, 15.2, 16.0, 17.9, 19.1, 20.4, 21.0, 22.8, 24.1, 25.0, 26.6, 27.9,
  29.0, 30.2, 31.4,
];
const PROFIT_RATE_DECLINE = [
  0.24, 0.235, 0.229, 0.221, 0.214, 0.203, 0.196, 0.188, 0.179, 0.171, 0.163, 0.154, 0.147, 0.139,
  0.131, 0.124, 0.117, 0.111, 0.104, 0.096,
];

export function ImperialRentTrend() {
  return (
    <Frame>
      <Sparkline data={RENT_TREND} color="var(--babylon-rent)" w={140} h={32} label="Φ Rent" />
    </Frame>
  );
}

export function ProfitRateDecline() {
  return (
    <Frame>
      <Sparkline
        data={PROFIT_RATE_DECLINE}
        color="var(--babylon-heat)"
        w={140}
        h={32}
        label="Profit Rate"
      />
    </Frame>
  );
}

export function HonestEmptyPlaceholder() {
  return (
    <Frame>
      <Sparkline data={[]} color="var(--babylon-cadre)" w={140} h={32} label="Solidarity Edges" />
    </Frame>
  );
}
