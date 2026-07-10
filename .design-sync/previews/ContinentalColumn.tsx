/**
 * ContinentalColumn preview — pure-props corporate/continental press column,
 * one third of The Wire's triptych. Ported from design/mockups/wire/wire-data.jsx
 * (the WC-RAID story), re-ticked to 104 / Wayne County FIPS 26163 to match the
 * rest of the DS suite's shared fiction (see EventsFeed's rupture-in-Wayne-
 * County cell). No store — `story`/`activeEuph`/`activeSup` are direct props.
 */
import { ContinentalColumn } from "babylon-cockpit";

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
    // Trimmed to 2 paragraphs / 2 citations (not the full 4 from the source
    // mockup) so the References block — and CitationActive's highlighted
    // row, this component's whole reason for existing — stays inside the
    // 660px frame instead of scrolling out of view (see wire.md).
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
        src: "Senior DHS official",
        kind: "background, attributable on consent",
        id: "BG-0104-022",
        chunk: "chunk_corpus_bg_0104_022",
        sim: 0.74,
      },
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
          ". A SHOCK TEAM WENT IN BEFORE THE FIRST CALL TO COUNSEL WAS COMPLETE.",
        ],
        margin: {
          ref: "AFFIDAVIT-WCLF-0104",
          chunk: "chunk_corpus_aff_0104",
          note: "front-door cam timestamp 03:47:22",
        },
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
    fields: [["EVENT", "BREACH / DETAIN / SEIZE"]],
    assessment: [],
    refs: [],
    distribution: "▮▮▮▮▮▮ · NOFORN · 30D RETAIN",
  },
};

function Frame({ children }: { children?: unknown }) {
  // Inline style, not a Tailwind arbitrary-value class: .design-sync/previews/
  // is outside the DS package's Tailwind content-scan glob, so `w-[420px]`
  // compiles to nothing in _ds_bundle.css and silently no-ops (verified via
  // pixel-bounding-box + `rg` against the compiled CSS — see wire.md; this
  // also affects the w-[440px] exemplars, StatChip/EventsFeed/TimeControls).
  return (
    <div className="bg-void p-2" style={{ width: 420, height: 660 }}>
      {children as never}
    </div>
  );
}

export function Populated() {
  return (
    <Frame>
      <ContinentalColumn
        story={STORY}
        activeEuph={null}
        setActiveEuph={() => {}}
        activeSup={null}
        setActiveSup={() => {}}
        euphAlways={false}
      />
    </Frame>
  );
}

export function CitationActive() {
  return (
    <Frame>
      <ContinentalColumn
        story={STORY}
        activeEuph={null}
        setActiveEuph={() => {}}
        activeSup={2}
        setActiveSup={() => {}}
        euphAlways={false}
      />
    </Frame>
  );
}

export function NoBibliography() {
  const story = { ...STORY, continental: { ...STORY.continental, bibliography: [] } };
  return (
    <Frame>
      <ContinentalColumn
        story={story}
        activeEuph={null}
        setActiveEuph={() => {}}
        activeSup={null}
        setActiveSup={() => {}}
        euphAlways={false}
      />
    </Frame>
  );
}

export function NoActiveStory() {
  return (
    <Frame>
      <ContinentalColumn
        story={null}
        activeEuph={null}
        setActiveEuph={() => {}}
        activeSup={null}
        setActiveSup={() => {}}
        euphAlways={false}
      />
    </Frame>
  );
}
