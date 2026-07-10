/**
 * CorpusPage preview — RAG retrieval browser tab. Pure props (`story`); the
 * component derives its own `chunks` list from
 * `story.continental.bibliography` + `story.liberated.paragraphs[].margin`
 * + `story.intel.refs` — Constitution VIII "Archive is observer-only" note
 * is a static footer, not a prop. Page-level width (~1100px).
 */
import { CorpusPage } from "babylon-cockpit";

const STORY = {
  id: "WC-RAID-0104",
  tick: 104,
  location: "Dearborn, Wayne County, MI (FIPS 26163)",
  time_local: "Tue 03:47 EDT",
  continental: {
    brand: "CONTINENTAL",
    monogram: "C•N",
    kicker: "NATIONAL",
    hed: "Federal Authorities Conduct Security Operation in Dearborn",
    dek: "",
    byline: "",
    paragraphs: [],
    bibliography: [
      {
        n: 1,
        src: "DHS Office of Public Affairs",
        kind: "press release",
        id: "DHS-OPA-2026-0104-01",
        chunk: "chunk_corpus_dhs_pr_0104a",
        sim: 0.91,
      },
      {
        n: 2,
        src: "DHS Office of Public Affairs",
        kind: "press release",
        id: "DHS-OPA-2026-0104-01",
        chunk: "chunk_corpus_dhs_pr_0104b",
        sim: 0.88,
      },
      {
        n: 3,
        src: "Senior DHS official",
        kind: "background, attributable on consent",
        id: "BG-0104-022",
        chunk: "chunk_corpus_bg_0104_022",
        sim: 0.74,
      },
      {
        n: 4,
        src: "Continental newsroom; standard-procedure boilerplate",
        kind: "house style",
        id: "CN-STYLE-7.4.2",
        chunk: "chunk_corpus_cn_style_742",
        sim: 0.99,
      },
    ],
  },
  liberated: {
    brand: "FREE SIGNAL",
    callsign: "WCLF-PIRATE-887",
    operator: "RASKOVA-2",
    hed: "",
    pre: "",
    post: "",
    paragraphs: [
      {
        body: ["AT 0347 TUESDAY, FEDS BROKE THE FRONT DOOR OF THE WCLF HALL ON SCHAEFER."],
        margin: {
          ref: "AFFIDAVIT-WCLF-0104",
          chunk: "chunk_corpus_aff_0104",
          note: "front-door cam timestamp 03:47:22",
        },
      },
      {
        body: ["BRO. J. KAMINSKI, 71, A LIFETIME UAW LOCAL 600 MAN, WAS KNELT ON FOR ELEVEN MINUTES."],
        margin: {
          ref: "ER-RECORD / BEAUMONT-0104-0521",
          chunk: "chunk_corpus_er_0104",
          note: "admit 04:21 // GCS 14 // chest CT pending",
        },
      },
      {
        body: ["THEY SEIZED OUR PRINTERS, OUR MEMBERSHIP ROLODEX, MUTUAL AID LEDGERS, STRIKE FUND BOOKS."],
        margin: {
          ref: "INVENTORY-WCLF-0103",
          chunk: "chunk_corpus_inv_0103",
          note: "complete asset list 18h prior",
        },
      },
    ],
  },
  intel: {
    classification: "TS//SI//NOFORN",
    cable_id: "0104-A",
    origin: "",
    routing: [],
    caveat: "",
    subj: "",
    fields: [],
    assessment: [],
    refs: [
      { tag: "CHUNK", id: "chunk_corpus_warrant_0103", sim: 0.92, src: "FISC docket 26-▮▮▮▮" },
      { tag: "CHUNK", id: "chunk_corpus_chs7_0102", sim: 0.81, src: "CHS-7 contact report" },
      { tag: "CHUNK", id: "chunk_corpus_strike_0103", sim: 0.77, src: "WCLF council minutes" },
      { tag: "CHUNK", id: "chunk_corpus_sigint_0104", sim: 0.95, src: "SIGINT/88.7 capture" },
    ],
    distribution: "",
  },
};

function Frame({ children }: { children?: unknown }) {
  // Inline style, not a Tailwind arbitrary-value class — see wire.md: the DS
  // package's Tailwind content-scan doesn't cover .design-sync/previews/, so
  // `w-[1100px]` compiles to nothing and silently no-ops. Sized to 840x640
  // to stay inside the capture pipeline's fixed 900x700 viewport.
  return (
    <div className="bg-void p-2" style={{ width: 840, height: 640 }}>
      {children as never}
    </div>
  );
}

export function Populated() {
  return (
    <Frame>
      <CorpusPage story={STORY} />
    </Frame>
  );
}

export function SparseRetrieval() {
  const story = {
    ...STORY,
    continental: { ...STORY.continental, bibliography: [] },
    liberated: {
      ...STORY.liberated,
      paragraphs: [{ body: ["NO CORROBORATING FIELD REPORTS FILED YET."], margin: null }],
    },
    intel: { ...STORY.intel, refs: [] },
  };
  return (
    <Frame>
      <CorpusPage story={story} />
    </Frame>
  );
}

export function NoActiveStory() {
  return (
    <Frame>
      <CorpusPage story={null} />
    </Frame>
  );
}
