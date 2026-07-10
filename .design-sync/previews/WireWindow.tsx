/**
 * WireWindow preview — app chrome for The Wire (title bar + tab bar).
 * Pure props (`tabs`/`activeId`/`onTab`/`badge`/`children`), no store. The
 * primary variant axis is which tab is active — each cell nests a REAL
 * Wire page as `children` (per the task brief's own example: "a Wire page
 * inside WireWindow"), matching what WireApp actually composes, rather
 * than placeholder text. IndexPage's cell passes `gameId={null}` so its
 * nested BlocFlowLines never touches the store (see IndexPage.tsx/wire.md).
 * Page-level width (~1150px).
 */
import {
  WireWindow,
  ContinentalColumn,
  LiberatedColumn,
  IntelColumn,
  IndexPage,
  PatternsPage,
  CorpusPage,
} from "babylon-cockpit";

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
    dek: "Department of Homeland Security says the pre-dawn action targeted a Wayne County address tied to an ongoing public-safety inquiry.",
    byline: "By J. Halvorsen and M. Pereira · Updated 5h ago",
    paragraphs: [
      [
        "DEARBORN, Mich. — Federal authorities conducted a coordinated ",
        { euph: "raid", text: "security operation" },
        " early Tuesday morning at a Wayne County ",
        { euph: "hq", text: "community center" },
        ", detaining 14 individuals for questioning.",
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
        body: [
          "AT 0347 TUESDAY, FEDS WITH ",
          { euph: "violence", text: "BATTERING RAMS AND FLASHBANGS" },
          " BROKE THE FRONT DOOR OF THE ",
          { euph: "hq", text: "WCLF HALL ON SCHAEFER" },
          ".",
        ],
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
};

const FILTERS = [
  { id: "ownership" as const, label: "Ownership", desc: "", hits: 3, color: "var(--babylon-rent)" },
  { id: "sourcing" as const, label: "Sourcing", desc: "", hits: 5, color: "var(--babylon-cadre)" },
  { id: "ideology" as const, label: "Anti-radical ideology", desc: "", hits: 4, color: "var(--babylon-laser)" },
];

function tabs(activeExtra?: { patternsDot?: boolean }) {
  return [
    { id: "wire", label: "The Wire", count: 3, dot: "var(--babylon-spire)" },
    { id: "index", label: "Wire Index", count: INDEX.length },
    {
      id: "patterns",
      label: "Patterns",
      count: Object.keys(EUPHEMISMS).length,
      dot: activeExtra?.patternsDot === false ? undefined : "var(--babylon-laser)",
    },
    { id: "corpus", label: "Corpus" },
  ];
}

const badge = (
  <>
    <span className="wire-label">TICK</span>
    <span
      className="text-[16px] font-bold"
      style={{
        fontFamily: "var(--font-mono)",
        color: "var(--babylon-spire)",
        textShadow: "0 0 10px rgba(77,217,230,0.4)",
        letterSpacing: "0.04em",
      }}
    >
      0104
    </span>
    <span style={{ width: 1, height: 16, background: "var(--babylon-rebar)", margin: "0 8px" }} />
    <span
      className="text-[9px]"
      style={{ fontFamily: "var(--font-mono)", color: "var(--babylon-fog)", letterSpacing: "0.16em" }}
    >
      OP - RASKOVA-2
    </span>
  </>
);

function Frame({ children }: { children?: unknown }) {
  // Inline style, not a Tailwind arbitrary-value class — see wire.md: the DS
  // package's Tailwind content-scan doesn't cover .design-sync/previews/, so
  // `w-[1150px]` compiles to nothing and silently no-ops. 852x640 to stay
  // inside the capture pipeline's fixed 900x700 viewport — this compresses
  // the nested triptych's 3 columns noticeably tighter than their own
  // dedicated 420px-wide previews; graded on its own terms (see wire.md).
  return (
    <div className="bg-void p-2" style={{ width: 852, height: 640 }}>
      {children as never}
    </div>
  );
}

export function WireTabActive() {
  // Each column wrapped with explicit flex:1/minWidth:0 — WireApp's own
  // triptych row (`<div className="flex min-h-0 flex-1 overflow-hidden">`)
  // gives its 3 columns NO flex-basis at all, so they only ever claim their
  // own content's natural width and leave the remainder of the row as bare
  // void background (confirmed at any viewport width — see wire.md, a real
  // WireApp.tsx/wire.css finding, most visible when story=null and worst
  // when content is short). WireWindow's own job is chrome, not triptych
  // layout, so this preview supplies well-proportioned demo children rather
  // than reproducing that squeeze here too.
  return (
    <Frame>
      <WireWindow tabs={tabs()} activeId="wire" onTab={() => {}} badge={badge}>
        <div className="flex h-full min-h-0 overflow-hidden">
          <div style={{ flex: 1, minWidth: 0 }}>
            <ContinentalColumn
              story={STORY}
              activeEuph={null}
              setActiveEuph={() => {}}
              activeSup={null}
              setActiveSup={() => {}}
              euphAlways={false}
            />
          </div>
          <div className="drift" />
          <div style={{ flex: 1, minWidth: 0 }}>
            <LiberatedColumn story={STORY} activeEuph={null} setActiveEuph={() => {}} euphAlways={false} />
          </div>
          <div className="drift" />
          <div style={{ flex: 1, minWidth: 0 }}>
            <IntelColumn story={STORY} />
          </div>
        </div>
      </WireWindow>
    </Frame>
  );
}

export function IndexTabActive() {
  return (
    <Frame>
      <WireWindow tabs={tabs()} activeId="index" onTab={() => {}} badge={badge}>
        <IndexPage index={INDEX} activeId="WC-RAID-0104" onOpen={() => {}} gameId={null} />
      </WireWindow>
    </Frame>
  );
}

export function PatternsTabActive() {
  return (
    <Frame>
      <WireWindow tabs={tabs()} activeId="patterns" onTab={() => {}} badge={badge}>
        <PatternsPage euphemisms={EUPHEMISMS} filters={FILTERS} story={STORY} />
      </WireWindow>
    </Frame>
  );
}

export function CorpusTabActive() {
  return (
    <Frame>
      <WireWindow tabs={tabs()} activeId="corpus" onTab={() => {}} badge={badge}>
        <CorpusPage story={STORY} />
      </WireWindow>
    </Frame>
  );
}
