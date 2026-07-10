/**
 * IndexPage preview — the Wire's story archive tab. `index`/`activeId`/
 * `onOpen` are direct props, but IndexPage unconditionally renders
 * `<BlocFlowLines gameId={gameId} />` at the top, which is hook-driven
 * (`useTradeFlows` → `panels.tradeFlows`, fetch-on-mount). Two ways past
 * that fetch are used here: seed `panels.tradeFlows.data` + stub `fetch`
 * to a no-op (Populated/NoSelection — a real gameId would otherwise race
 * the seed with a real 404 fetch against the static preview server, see
 * wire.md learnings), or simply pass `gameId={null}` (EmptyIndex — the
 * hook's mount effect no-ops on a falsy gameId, so BlocFlowLines shows its
 * own honest-empty "No boundary flows yet" for free).
 *
 * Page-level width (~1100px) — cfg.overrides.IndexPage = {cardMode:
 * "single", primaryStory: "Populated", viewport: "1100x820"} recommended
 * (see wire.md): both for the width and because the nested BlocFlowLines'
 * store state would otherwise leak across cells sharing one store instance
 * on the non-story combined card.
 */
import { IndexPage, useStore } from "babylon-cockpit";

const INDEX = [
  {
    id: "WC-RAID-0104",
    tick: 104,
    slug: "FEDERAL RAID · WCLF HALL · DEARBORN",
    hed: {
      c: "Federal Authorities Conduct Security Operation in Dearborn",
      l: "PIGS RAIDED THE LABOR HALL // 14 COMRADES SNATCHED",
      i: "BREACH // WCLF-DEARBORN // 14× DETAINED",
    },
    coverage: ["c", "l", "i"] as ("c" | "l" | "i")[],
    pinned: true,
    severity: "critical" as const,
  },
  {
    id: "WC-STRIKE-0103",
    tick: 103,
    slug: "STERLING ASSEMBLY · DEARBORN · WALKOUT CALL",
    hed: {
      c: "Stellantis Reports Anticipated Production Disruption at Sterling Plant",
      l: "STERLING CREW VOTES TO WALK AT DAWN // A-SHIFT SOLID",
      i: "LABOR ACTION // STERLING ASSY // T-71H STRIKE CALL",
    },
    coverage: ["c", "l", "i"] as ("c" | "l" | "i")[],
    severity: "warning" as const,
  },
  {
    id: "WC-RENT-0102",
    tick: 102,
    slug: "RENT SCHEDULE · WAYNE CO PORTFOLIO · 26163",
    hed: {
      c: "Market Correction Brings Wayne County Rents to Regional Average",
      l: "LANDLORD CLASS SQUEEZES HARDER // 18% HIKE IN ONE QUARTER",
      i: "RENT EXTRACTION Φ +0.042 // WAYNE-CORE / DEARBORN-S",
    },
    coverage: ["c", "l", "i"] as ("c" | "l" | "i")[],
    severity: "warning" as const,
  },
  {
    id: "WC-CONSC-0101",
    tick: 101,
    slug: "READING CIRCLES · WCLF PERIPHERY",
    hed: {
      c: "Local Book Clubs Draw Renewed Interest from Younger Readers",
      l: "STUDY GROUPS HITTING 200+ A WEEK // THE MASS LINE HOLDS",
      i: "CONSCIOUSNESS Δ +0.022 // WCLF-PERIPHERY",
    },
    coverage: ["c", "l", "i"] as ("c" | "l" | "i")[],
    severity: "info" as const,
  },
  {
    id: "WC-INFORMANT-0100",
    tick: 100,
    slug: "INFORMANT · SOLIDARITY-NET",
    hed: {
      c: "FBI Confirms Cooperating Witness in Ongoing Inquiry",
      l: "RAT IN THE KITCHEN // BURNED COMRADE NAMED FRIDAY",
      i: "CHS-7 ACTIVE // WCLF/SOLIDARITY-NET // HEAT +0.071",
    },
    coverage: ["c", "l", "i"] as ("c" | "l" | "i")[],
    severity: "critical" as const,
  },
  {
    id: "WC-AID-0099",
    tick: 99,
    slug: "MUTUAL AID · DEARBORN-S BIOCAP CRISIS",
    hed: {
      c: "Faith Groups Coordinate Food Drive in Affected Neighborhoods",
      l: "NEIGHBORS FED 1,400 LAST WEEK WHILE CITY HALL SLEPT",
      i: "RESOURCE TRANSFER 1.4K HH // ALLIED-ORG CLUSTER",
    },
    coverage: ["c", "l"] as ("c" | "l" | "i")[],
    severity: "info" as const,
  },
];

const TRADE_FLOWS = {
  tick: 104,
  has_data: true,
  blocs: [
    {
      node_id: "bloc-cn",
      label: "China",
      kind: "international" as const,
      latest: { phi_year_inflow: 812.4, bilateral_trade_value: 4210.7, bilateral_trade_tons: 98000, erdi_ratio: 1.34 },
      phi_series: [
        { tick: 100, magnitude: 740 },
        { tick: 101, magnitude: 765 },
        { tick: 102, magnitude: 788 },
        { tick: 103, magnitude: 801 },
        { tick: 104, magnitude: 812.4 },
      ],
      trade_series: [
        { tick: 100, magnitude: 3900 },
        { tick: 101, magnitude: 4020 },
        { tick: 102, magnitude: 4105 },
        { tick: 103, magnitude: 4180 },
        { tick: 104, magnitude: 4210.7 },
      ],
    },
    {
      node_id: "bloc-eu",
      label: "EU Bloc",
      kind: "international" as const,
      latest: { phi_year_inflow: 301.2, bilateral_trade_value: 2870.5, bilateral_trade_tons: 61000, erdi_ratio: 0.92 },
      phi_series: [
        { tick: 100, magnitude: 330 },
        { tick: 101, magnitude: 322 },
        { tick: 102, magnitude: 315 },
        { tick: 103, magnitude: 308 },
        { tick: 104, magnitude: 301.2 },
      ],
      trade_series: [
        { tick: 100, magnitude: 2750 },
        { tick: 101, magnitude: 2790 },
        { tick: 102, magnitude: 2820 },
        { tick: 103, magnitude: 2850 },
        { tick: 104, magnitude: 2870.5 },
      ],
    },
    {
      node_id: "dom-rest",
      label: "Domestic Rest (ex-MI)",
      kind: "domestic_rest" as const,
      latest: { phi_year_inflow: 0, bilateral_trade_value: 1540.9, bilateral_trade_tons: 45210, erdi_ratio: 1.0 },
      phi_series: [],
      trade_series: [
        { tick: 100, magnitude: 1420 },
        { tick: 101, magnitude: 1465 },
        { tick: 102, magnitude: 1498 },
        { tick: 103, magnitude: 1520 },
        { tick: 104, magnitude: 1540.9 },
      ],
    },
  ],
};

function seedTradeFlows(patch: Record<string, unknown>) {
  useStore.setState((s: any) => ({
    panels: {
      ...s.panels,
      tradeFlows: { ...s.panels.tradeFlows, fetch: async () => {}, loading: false, error: null, ...patch },
    },
  }));
}

function Frame({ children }: { children?: unknown }) {
  // Inline style, not a Tailwind arbitrary-value class — see wire.md: the DS
  // package's Tailwind content-scan doesn't cover .design-sync/previews/, so
  // `w-[1100px]` compiles to nothing and silently no-ops. Sized to 840x640
  // (not the ~1100px "page-level" ideal) to stay inside the capture
  // pipeline's fixed 900x700 viewport (no cardMode/viewport override is
  // available to this preview file) — see wire.md for the cfg.overrides
  // recommendation that would let the production card go wider.
  return (
    <div className="bg-void p-2" style={{ width: 840, height: 640 }}>
      {children as never}
    </div>
  );
}

export function Populated() {
  seedTradeFlows({ data: TRADE_FLOWS });
  return (
    <Frame>
      <IndexPage index={INDEX} activeId="WC-RAID-0104" onOpen={() => {}} gameId="g-preview-104" />
    </Frame>
  );
}

export function NoSelection() {
  seedTradeFlows({ data: TRADE_FLOWS });
  return (
    <Frame>
      <IndexPage index={INDEX} activeId={null} onOpen={() => {}} gameId="g-preview-104" />
    </Frame>
  );
}

export function EmptyIndex() {
  return (
    <Frame>
      <IndexPage index={[]} activeId={null} onOpen={() => {}} gameId={null} />
    </Frame>
  );
}
