/**
 * LiberatedColumn preview — pure-props Free Signal pirate-radio phosphor
 * terminal, one third of The Wire's triptych. Same WC-RAID-0104 fiction as
 * ContinentalColumn.tsx (tick 104, Wayne County FIPS 26163). No store —
 * `story`/`activeEuph` are direct props; `activeEuph` set directly (not via
 * hover) demonstrates the phosphor "active" highlight statically.
 */
import { LiberatedColumn } from "babylon-cockpit";

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
    bibliography: [],
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
      {
        body: [
          "THEY DRAGGED ",
          { euph: "arrest", text: "14 OF OUR COMRADES" },
          " INTO THE COLD IN ZIP TIES. ",
          { euph: "civilian", text: "NEIGHBORS WATCHED FROM PORCHES" },
          ". KIDS WATCHED. PHOTOS WERE TAKEN. WE HAVE THEM. WE WILL PUBLISH THEM.",
        ],
        margin: {
          ref: "WITNESS-CHAVEZ / WITNESS-OKONKWO",
          chunk: "chunk_corpus_wit_0104_a",
          note: "two unrelated witnesses, distinct apts",
        },
      },
      {
        body: [
          "BRO. J. KAMINSKI, 71, A LIFETIME UAW LOCAL 600 MAN, WAS KNELT ON FOR ELEVEN MINUTES. HE IS AT BEAUMONT NOW WITH BRUISED RIBS AND A FRACTURED ORBITAL. HE WAS BRINGING COFFEE FROM THE BACK ROOM. HE WAS NOT RESISTING.",
        ],
        margin: {
          ref: "ER-RECORD / BEAUMONT-0104-0521",
          chunk: "chunk_corpus_er_0104",
          note: "admit 04:21 // GCS 14 // chest CT pending",
        },
      },
      {
        body: [
          "THEY SEIZED OUR ",
          { euph: "files", text: "PRINTERS, OUR MEMBERSHIP ROLODEX, MUTUAL AID LEDGERS, STRIKE FUND BOOKS" },
          ", AND A CABINET CONTAINING ",
          { euph: "rifles", text: "FOUR LEGALLY-REGISTERED HUNTING RIFLES" },
          " THAT BELONG TO THE WCLF RIFLE CLUB. THE SIGN-OUT SHEET IS ALSO GONE.",
        ],
        margin: {
          ref: "INVENTORY-WCLF-0103",
          chunk: "chunk_corpus_inv_0103",
          note: "complete asset list 18h prior",
        },
      },
      {
        body: [
          "THE STATE CALLS THIS ",
          { euph: "raid", text: "‘PUBLIC SAFETY’" },
          ". WE CALL IT WHAT IT IS: TERROR TIMED TO BREAK THE STRIKE WAVE BEFORE IT CRESTS. THE STERLING WALKOUT IS IN 71 HOURS. THIS IS NOT A COINCIDENCE.",
        ],
        margin: {
          ref: "STERLING WALKOUT CALL · WCLF COUNCIL · 0103",
          chunk: "chunk_corpus_swc_0103",
          note: "raid timed -71h from strike T0",
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
    refs: [],
    distribution: "",
  },
};

function Frame({ children }: { children?: unknown }) {
  // Inline style, not a Tailwind arbitrary-value class — see wire.md: the DS
  // package's Tailwind content-scan doesn't cover .design-sync/previews/, so
  // `w-[420px]` compiles to nothing and silently no-ops.
  return (
    <div className="bg-void p-2" style={{ width: 420, height: 660 }}>
      {children as never}
    </div>
  );
}

export function Populated() {
  return (
    <Frame>
      <LiberatedColumn story={STORY} activeEuph={null} setActiveEuph={() => {}} euphAlways={false} />
    </Frame>
  );
}

export function EuphActive() {
  // "hq" (not "raid") — "raid" only appears in paragraph 5, which scrolls
  // out of the 660px frame; "hq" is in paragraph 1, which is always visible,
  // so the active phosphor highlight this cell exists to demonstrate is
  // actually visible in the capture (see wire.md).
  return (
    <Frame>
      <LiberatedColumn story={STORY} activeEuph="hq" setActiveEuph={() => {}} euphAlways={false} />
    </Frame>
  );
}

export function NoActiveStory() {
  return (
    <Frame>
      <LiberatedColumn story={null} activeEuph={null} setActiveEuph={() => {}} euphAlways={false} />
    </Frame>
  );
}
