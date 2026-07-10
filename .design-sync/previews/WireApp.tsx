/**
 * WireApp preview — main 4-tab Wire shell (WIRE triptych / INDEX / PATTERNS
 * / CORPUS). Store/hook-driven (`useWire` → `panels.wire`, fetch-on-mount);
 * `tab` is local `useState` defaulting to "wire" with no prop to force it,
 * so every cell here renders the WIRE (triptych) tab — the other three tabs
 * get their own dedicated preview files (IndexPage/PatternsPage/CorpusPage)
 * since WireApp can't be statically steered to them without a click.
 *
 * The mount effect always fires a real `fetchWire(gameId)` — seeding
 * `panels.wire.data` alone isn't enough (the effect's real `fetch` would
 * overwrite it with a 404 from the static preview server before the
 * screenshot settles). Each cell seeds data/loading/error AND stubs `fetch`
 * to a no-op, always spreading the existing panel slice to keep
 * `setMounted` intact (see wire.md learnings — same pattern needed by
 * WireTakeover and BlocFlowLines).
 *
 * Page-level width (~1100px) + store-multi-state: cfg.overrides.WireApp =
 * {cardMode: "single", primaryStory: "Populated", viewport: "1150x820"}
 * recommended (see wire.md).
 */
import { WireApp, useStore } from "babylon-cockpit";

const STORY = {
  id: "WC-RAID-0104",
  tick: 104,
  location: "Dearborn, Wayne County, MI (FIPS 26163)",
  time_local: "Tue 03:47 EDT",
  continental: {
    brand: "CONTINENTAL",
    monogram: "C•N",
    kicker: "NATIONAL · LAW ENFORCEMENT",
    hed: "Federal Authorities Conduct Security Operation in Dearborn, Detain 14 for Questioning",
    dek: "Department of Homeland Security says the pre-dawn action targeted a Wayne County address tied to an ongoing public-safety inquiry. No charges have been announced.",
    byline: "By J. Halvorsen and M. Pereira · Updated 5h ago",
    paragraphs: [
      [
        "DEARBORN, Mich. — Federal authorities conducted a coordinated ",
        { euph: "raid", text: "security operation" },
        " early Tuesday morning at a Wayne County ",
        { euph: "hq", text: "community center" },
        ", ",
        { euph: "arrest", text: "detaining 14 individuals for questioning" },
        " in connection with what officials described as “ongoing public-safety concerns.”",
        { sup: 1 },
      ],
      [
        "The operation, executed under a sealed warrant, recovered an ",
        { euph: "files", text: "undisclosed quantity of materials" },
        " from the premises. A small number of ",
        { euph: "rifles", text: "firearms" },
        " were also secured.",
        { sup: 2 },
      ],
    ],
    bibliography: [
      { n: 1, src: "DHS Office of Public Affairs", kind: "press release", id: "DHS-OPA-2026-0104-01", chunk: "chunk_corpus_dhs_pr_0104a", sim: 0.91 },
      { n: 2, src: "DHS Office of Public Affairs", kind: "press release", id: "DHS-OPA-2026-0104-01", chunk: "chunk_corpus_dhs_pr_0104b", sim: 0.88 },
    ],
  },
  liberated: {
    brand: "FREE SIGNAL",
    callsign: "WCLF-PIRATE-887",
    operator: "RASKOVA-2",
    hed: "PIGS RAIDED THE WCLF HALL // 14 COMRADES SNATCHED AT 0347",
    pre: "[ BEGIN TRANSMISSION · 0512Z · CIPHER: NONE · BROADCAST IN THE CLEAR ]",
    post: "[ END TRANSMISSION · TUNE 88.7 AT NEXT HOUR · DEATH TO IMPERIALISM ]",
    paragraphs: [
      {
        body: [
          "AT 0347 TUESDAY, FEDS WITH ",
          { euph: "violence", text: "BATTERING RAMS AND FLASHBANGS" },
          " BROKE THE FRONT DOOR OF THE ",
          { euph: "hq", text: "WCLF HALL ON SCHAEFER" },
          ".",
        ],
        margin: { ref: "AFFIDAVIT-WCLF-0104", chunk: "chunk_corpus_aff_0104", note: "front-door cam timestamp 03:47:22" },
      },
      {
        body: [
          "BRO. J. KAMINSKI, 71, A LIFETIME UAW LOCAL 600 MAN, WAS KNELT ON FOR ELEVEN MINUTES. HE WAS NOT RESISTING.",
        ],
        margin: { ref: "ER-RECORD / BEAUMONT-0104-0521", chunk: "chunk_corpus_er_0104", note: "admit 04:21 // GCS 14" },
      },
    ],
  },
  intel: {
    classification: "TS//SI//NOFORN",
    cable_id: "0104-A",
    origin: "FBI/HSI JOINT TASKFORCE — ▮▮▮▮▮▮ FIELD OFFICE",
    routing: ["▮▮▮▮▮▮/CT", "DHS/I&A", "DOJ/NSD"],
    caveat: "HANDLE VIA COMINT CHANNELS ONLY",
    subj: "BREACH OPERATION · WCLF-DEARBORN · POST-ACTION",
    fields: [
      ["EVENT", "BREACH / DETAIN / SEIZE"],
      ["DETAINEES", "14× PROCESSED · 0× CHARGED AT +18H"],
      ["CONFIDENCE", "HIGH · 0.84"],
    ] as [string, string][],
    assessment: ["Action precedes WCLF-CALLED REGIONAL STRIKE at T+71H. Timing assessed deliberate."],
    refs: [{ tag: "CHUNK", id: "chunk_corpus_sigint_0104", sim: 0.95, src: "SIGINT/88.7 capture" }],
    distribution: "▮▮▮▮▮▮ · NOFORN · 30D RETAIN",
  },
};

const INDEX = [
  {
    id: "WC-RAID-0104",
    tick: 104,
    slug: "FEDERAL RAID · WCLF HALL · DEARBORN",
    hed: { c: "Federal Authorities Conduct Security Operation in Dearborn", l: "PIGS RAIDED THE LABOR HALL // 14 COMRADES SNATCHED", i: "BREACH // WCLF-DEARBORN // 14× DETAINED" },
    coverage: ["c", "l", "i"] as ("c" | "l" | "i")[],
    pinned: true,
    severity: "critical" as const,
  },
  {
    id: "WC-STRIKE-0103",
    tick: 103,
    slug: "STERLING ASSEMBLY · DEARBORN · WALKOUT CALL",
    hed: { c: "Stellantis Reports Anticipated Production Disruption at Sterling Plant", l: "STERLING CREW VOTES TO WALK AT DAWN // A-SHIFT SOLID", i: "LABOR ACTION // STERLING ASSY // T-71H STRIKE CALL" },
    coverage: ["c", "l", "i"] as ("c" | "l" | "i")[],
    severity: "warning" as const,
  },
];

const EUPHEMISMS = {
  raid: { c: "security operation", l: "RAID", filter: "sourcing" as const, note: "State spokesperson is sole source. Verb erased: who breached whom?" },
  hq: { c: "community center", l: "WCLF HALL / OUR HALL", filter: "ownership" as const, note: "Property classification scrubbed. 11-year-old federation HQ at 7100 Schaefer." },
  arrest: { c: "detain for questioning", l: "SNATCH / ABDUCT", filter: "sourcing" as const, note: "‘Detain’ implies temporary; 14 are still held without charge at +18h." },
};

const FILTERS = [
  { id: "ownership" as const, label: "Ownership", desc: "", hits: 3, color: "var(--babylon-rent)" },
  { id: "advertising" as const, label: "Advertising", desc: "", hits: 2, color: "var(--babylon-heat)" },
  { id: "sourcing" as const, label: "Sourcing", desc: "", hits: 5, color: "var(--babylon-cadre)" },
  { id: "flak" as const, label: "Flak", desc: "", hits: 2, color: "var(--babylon-rupture)" },
  { id: "ideology" as const, label: "Anti-radical ideology", desc: "", hits: 4, color: "var(--babylon-laser)" },
];

const WIRE_FEED = {
  meta: {
    tick: 104,
    session: "wayne-county-001",
    operator: "RASKOVA-2",
    freq: "88.7 MHz",
    qth: "WAYNE CO / GRID EN82",
    classification: "TS//SI//NOFORN",
    cable_id: "0104-A",
    page_of: "006/104",
    timestamp_utc: "2026-07-06T05:12:00Z",
  },
  index: INDEX,
  euphemisms: EUPHEMISMS,
  story: STORY,
  filters: FILTERS,
};

function seedWire(patch: Record<string, unknown>) {
  useStore.setState((s: any) => ({
    panels: {
      ...s.panels,
      wire: { ...s.panels.wire, fetch: async () => {}, data: null, loading: false, error: null, ...patch },
    },
  }));
}

function Frame({ children }: { children?: unknown }) {
  // Inline style, not a Tailwind arbitrary-value class — see wire.md: the DS
  // package's Tailwind content-scan doesn't cover .design-sync/previews/, so
  // `w-[1150px]` compiles to nothing and silently no-ops. Sized to 852x640
  // (not the ~1150px full-takeover ideal) to stay inside the capture
  // pipeline's fixed 900x700 viewport — see wire.md for the cfg.overrides
  // {cardMode:"single", viewport:"1150x820"} recommendation for the
  // production card.
  return (
    <div className="bg-void p-2" style={{ width: 852, height: 640 }}>
      {children as never}
    </div>
  );
}

export function Populated() {
  seedWire({ data: WIRE_FEED });
  return (
    <Frame>
      <WireApp gameId="g-preview-104" />
    </Frame>
  );
}

export function Loading() {
  seedWire({ loading: true });
  return (
    <Frame>
      <WireApp gameId="g-preview-104" />
    </Frame>
  );
}

export function LoudFailure() {
  seedWire({ error: "Wire feed unreachable: HTTP 502" });
  return (
    <Frame>
      <WireApp gameId="g-preview-104" />
    </Frame>
  );
}

export function NoActiveStory() {
  seedWire({ data: { ...WIRE_FEED, story: null } });
  return (
    <Frame>
      <WireApp gameId="g-preview-104" />
    </Frame>
  );
}
