/**
 * WireTakeover preview — thin overlay wrapper (`<WireApp gameId={gameId}
 * />`, imports wire.css). Same store/hook-driven fetch-on-mount pattern as
 * WireApp.tsx (seed `panels.wire.data`/`loading`/`error` AND stub `fetch`
 * to a no-op, see wire.md). WireApp itself already gets 4 cells covering
 * loading/error/no-active-story, so this file stays minimal: one canonical
 * composition proving the wrapper + wire.css textures render, plus the
 * honest-empty brand-new-game state (mirrors `EMPTY_WIRE_FEED` from
 * src/types/wire.ts — not importable here since previews only pull from
 * "babylon-cockpit", so it's reconstructed inline).
 *
 * Page-level width (~1100px) + store-multi-state: cfg.overrides.WireTakeover
 * = {cardMode: "single", primaryStory: "Populated", viewport: "1150x820"}
 * recommended (see wire.md).
 */
import { WireTakeover, useStore } from "babylon-cockpit";

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
  index: [
    {
      id: "WC-RAID-0104",
      tick: 104,
      slug: "FEDERAL RAID · WCLF HALL · DEARBORN",
      hed: { c: "Federal Authorities Conduct Security Operation in Dearborn", l: "PIGS RAIDED THE LABOR HALL // 14 COMRADES SNATCHED", i: "BREACH // WCLF-DEARBORN // 14× DETAINED" },
      coverage: ["c", "l", "i"] as ("c" | "l" | "i")[],
      pinned: true,
      severity: "critical" as const,
    },
  ],
  euphemisms: {
    raid: { c: "security operation", l: "RAID", filter: "sourcing" as const, note: "State spokesperson is sole source. Verb erased: who breached whom?" },
  },
  story: {
    id: "WC-RAID-0104",
    tick: 104,
    location: "Dearborn, Wayne County, MI (FIPS 26163)",
    time_local: "Tue 03:47 EDT",
    continental: {
      brand: "CONTINENTAL",
      monogram: "C•N",
      kicker: "NATIONAL · LAW ENFORCEMENT",
      hed: "Federal Authorities Conduct Security Operation in Dearborn, Detain 14 for Questioning",
      dek: "Department of Homeland Security says the pre-dawn action targeted a Wayne County address tied to an ongoing public-safety inquiry.",
      byline: "By J. Halvorsen and M. Pereira · Updated 5h ago",
      paragraphs: [
        [
          "DEARBORN, Mich. — Federal authorities conducted a coordinated ",
          { euph: "raid", text: "security operation" },
          " early Tuesday morning at a Wayne County community center, detaining 14 individuals for questioning.",
          { sup: 1 },
        ],
      ],
      bibliography: [
        { n: 1, src: "DHS Office of Public Affairs", kind: "press release", id: "DHS-OPA-2026-0104-01", chunk: "chunk_corpus_dhs_pr_0104a", sim: 0.91 },
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
          body: ["AT 0347 TUESDAY, FEDS BROKE THE FRONT DOOR OF THE WCLF HALL ON SCHAEFER."],
          margin: { ref: "AFFIDAVIT-WCLF-0104", chunk: "chunk_corpus_aff_0104", note: "front-door cam timestamp 03:47:22" },
        },
      ],
    },
    intel: {
      classification: "TS//SI//NOFORN",
      cable_id: "0104-A",
      origin: "FBI/HSI JOINT TASKFORCE — ▮▮▮▮▮▮ FIELD OFFICE",
      routing: ["▮▮▮▮▮▮/CT", "DHS/I&A"],
      caveat: "HANDLE VIA COMINT CHANNELS ONLY",
      subj: "BREACH OPERATION · WCLF-DEARBORN · POST-ACTION",
      fields: [["EVENT", "BREACH / DETAIN / SEIZE"]] as [string, string][],
      assessment: ["Action precedes WCLF-CALLED REGIONAL STRIKE at T+71H. Timing assessed deliberate."],
      refs: [{ tag: "CHUNK", id: "chunk_corpus_sigint_0104", sim: 0.95, src: "SIGINT/88.7 capture" }],
      distribution: "▮▮▮▮▮▮ · NOFORN · 30D RETAIN",
    },
  },
  filters: [
    { id: "ownership" as const, label: "Ownership", desc: "", hits: 3, color: "var(--babylon-rent)" },
    { id: "sourcing" as const, label: "Sourcing", desc: "", hits: 5, color: "var(--babylon-cadre)" },
  ],
};

/** Mirrors `EMPTY_WIRE_FEED` (src/types/wire.ts) — a brand-new game before
 * the narrator has generated a first wire. Not importable from
 * "babylon-cockpit" (types aren't part of the DS export surface). */
const EMPTY_FEED = {
  meta: {
    tick: 0,
    session: "",
    operator: "RASKOVA-2",
    freq: "88.7 MHz",
    qth: "WAYNE CO / GRID EN82",
    classification: "TS//SI//NOFORN",
    cable_id: "0000-A",
    page_of: "001/001",
    timestamp_utc: "2026-07-06T00:00:00Z",
  },
  index: [],
  euphemisms: {},
  story: null,
  filters: [
    { id: "ownership" as const, label: "Ownership", desc: "", hits: 0, color: "var(--babylon-rent)" },
    { id: "advertising" as const, label: "Advertising", desc: "", hits: 0, color: "var(--babylon-heat)" },
    { id: "sourcing" as const, label: "Sourcing", desc: "", hits: 0, color: "var(--babylon-cadre)" },
    { id: "flak" as const, label: "Flak", desc: "", hits: 0, color: "var(--babylon-rupture)" },
    { id: "ideology" as const, label: "Anti-radical ideology", desc: "", hits: 0, color: "var(--babylon-laser)" },
  ],
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
  // `w-[1150px]` compiles to nothing and silently no-ops. 852x640 to stay
  // inside the capture pipeline's fixed 900x700 viewport.
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
      <WireTakeover gameId="g-preview-104" />
    </Frame>
  );
}

export function EmptyFeed() {
  seedWire({ data: EMPTY_FEED });
  return (
    <Frame>
      <WireTakeover gameId="g-preview-empty" />
    </Frame>
  );
}
