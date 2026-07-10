/**
 * IntelColumn preview — pure-props SIGINT cable column with structured
 * fields + redactions, one third of The Wire's triptych. Same WC-RAID-0104
 * fiction (tick 104, Wayne County FIPS 26163). No store — `story` is a
 * direct prop. Redaction blocks (▮) exercise `renderRedacted`.
 */
import { IntelColumn } from "babylon-cockpit";

const STORY = {
  id: "WC-RAID-0104",
  tick: 104,
  location: "Dearborn, Wayne County, MI (FIPS 26163)",
  time_local: "Tue 03:47 EDT",
  continental: {
    brand: "CONTINENTAL",
    monogram: "C•N",
    kicker: "NATIONAL",
    hed: "",
    dek: "",
    byline: "",
    paragraphs: [],
    bibliography: [],
  },
  liberated: {
    brand: "FREE SIGNAL",
    callsign: "WCLF-PIRATE-887",
    operator: "RASKOVA-2",
    hed: "",
    pre: "",
    post: "",
    paragraphs: [],
  },
  intel: {
    classification: "TS//SI//NOFORN",
    cable_id: "0104-A",
    origin: "FBI/HSI JOINT TASKFORCE — ▮▮▮▮▮▮ FIELD OFFICE",
    routing: ["▮▮▮▮▮▮/CT", "DHS/I&A", "DOJ/NSD", "WHITE-HOUSE/SITROOM"],
    caveat: "HANDLE VIA COMINT CHANNELS ONLY",
    subj: "BREACH OPERATION · WCLF-DEARBORN · POST-ACTION",
    // Trimmed from the source mockup's 9 fields / 4 assessments / 4 refs so
    // the Populated cell's full cable — assessment, refs, DIST, and the
    // closing classification bar — stays inside the 660px frame instead of
    // scrolling out of view (see wire.md; same fix as ContinentalColumn).
    fields: [
      ["EVENT", "BREACH / DETAIN / SEIZE"],
      ["LOCAL TIME", "03:47 EDT · TICK 0104"],
      ["DETAINEES", "14× PROCESSED · 0× CHARGED AT +18H"],
      ["MEDICAL", "1× HOSPITAL (SUBJ-7 · AGE 71 · ▮▮▮▮▮▮▮▮▮▮)"],
      ["CONFIDENCE", "HIGH · 0.84"],
    ] as [string, string][],
    assessment: [
      "Action precedes WCLF-CALLED REGIONAL STRIKE at T+71H. Timing assessed deliberate.",
    ],
    refs: [{ tag: "CHUNK", id: "chunk_corpus_sigint_0104", sim: 0.95, src: "SIGINT/88.7 capture" }],
    distribution: "▮▮▮▮▮▮ / ▮▮▮▮▮▮ / ▮▮▮▮▮▮ · NOFORN · 30D RETAIN",
  },
};

function Frame({ children }: { children?: unknown }) {
  // Inline style, not a Tailwind arbitrary-value class — see wire.md: the DS
  // package's Tailwind content-scan doesn't cover .design-sync/previews/, so
  // `w-[420px]` compiles to nothing and silently no-ops. Height capped at 660
  // (not the component's full natural height) to stay inside the capture
  // pipeline's fixed 900x700 viewport — col-body's own overflow-y:auto
  // handles the rest, same as it would in a real, viewport-bounded window.
  return (
    <div className="bg-void p-2" style={{ width: 420, height: 660 }}>
      {children as never}
    </div>
  );
}

export function Populated() {
  return (
    <Frame>
      <IntelColumn story={STORY} />
    </Frame>
  );
}

export function MinimalCable() {
  const story = { ...STORY, intel: { ...STORY.intel, assessment: [], refs: [] } };
  return (
    <Frame>
      <IntelColumn story={story} />
    </Frame>
  );
}

export function NoActiveStory() {
  return (
    <Frame>
      <IntelColumn story={null} />
    </Frame>
  );
}
