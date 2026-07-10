/**
 * PatternsPage preview — Manufacturing Consent dashboard (Herman & Chomsky's
 * five filters + euphemism map). Pure props (`euphemisms`, `filters`,
 * `story`). Filter `color` values use the real Cold Collapse `--babylon-*`
 * tokens (see wire.md: `EMPTY_WIRE_FEED` in src/types/wire.ts ships
 * unprefixed `var(--rent)` etc, which are undefined in index.css — a
 * pre-existing bug worth flagging, not reproduced here). Page-level width.
 */
import { PatternsPage } from "babylon-cockpit";

const FILTERS = [
  { id: "ownership" as const, label: "Ownership", desc: "Continental is owned by a holding group with auto/defense exposure.", hits: 3, color: "var(--babylon-rent)" },
  { id: "advertising" as const, label: "Advertising", desc: "Stellantis is Continental’s second-largest advertiser this quarter.", hits: 2, color: "var(--babylon-heat)" },
  { id: "sourcing" as const, label: "Sourcing", desc: "5 of 5 named sources in the Corporate piece are state/state-adjacent.", hits: 5, color: "var(--babylon-cadre)" },
  { id: "flak" as const, label: "Flak", desc: "Two prior WCLF-favorable pieces were retracted under advertiser pressure.", hits: 2, color: "var(--babylon-rupture)" },
  { id: "ideology" as const, label: "Anti-radical ideology", desc: "‘Public safety’ frame presupposes the legitimacy of state violence.", hits: 4, color: "var(--babylon-laser)" },
];

const EUPHEMISMS = {
  raid: { c: "security operation", l: "RAID", filter: "sourcing" as const, note: "State spokesperson is sole source. Verb erased: who breached whom?" },
  arrest: { c: "detain for questioning", l: "SNATCH / ABDUCT", filter: "sourcing" as const, note: "‘Detain’ implies temporary; 14 are still held without charge at +18h." },
  organizers: { c: "individuals", l: "COMRADES / ORGANIZERS", filter: "ideology" as const, note: "Subjecthood removed. Names withheld until family confirms." },
  hq: { c: "community center", l: "WCLF HALL / OUR HALL", filter: "ownership" as const, note: "Property classification scrubbed. 11-year-old federation HQ at 7100 Schaefer." },
  files: { c: "materials", l: "PRINTERS · ROLODEX · MUTUAL AID LEDGERS · STRIKE FUND BOOKS", filter: "sourcing" as const, note: "What was actually taken matters. ‘Materials’ permits any contraband framing." },
  violence: { c: "measured and proportionate", l: "BATTERING RAMS · FLASHBANGS · KNEE-ON-NECK", filter: "ideology" as const, note: "Worth-doing-ness assumed. The state grades its own paper." },
  civilian: { c: "concerned community members", l: "NEIGHBORS / FAMILIES / KIDS WATCHING", filter: "sourcing" as const, note: "Witnesses present, unnamed. Their account doesn’t lead." },
  rifles: { c: "an undisclosed quantity of firearms", l: "4× LEGALLY-REGISTERED HUNTING RIFLES", filter: "flak" as const, note: "Number hidden; legality omitted. ‘Stockpile’ framing preloaded." },
};

const STORY = {
  id: "WC-RAID-0104",
  tick: 104,
  location: "Dearborn, Wayne County, MI (FIPS 26163)",
  time_local: "Tue 03:47 EDT",
  continental: { brand: "CONTINENTAL", monogram: "C•N", kicker: "", hed: "", dek: "", byline: "", paragraphs: [], bibliography: [] },
  liberated: { brand: "FREE SIGNAL", callsign: "WCLF-PIRATE-887", operator: "RASKOVA-2", hed: "", pre: "", post: "", paragraphs: [] },
  intel: { classification: "TS//SI//NOFORN", cable_id: "0104-A", origin: "", routing: [], caveat: "", subj: "", fields: [], assessment: [], refs: [], distribution: "" },
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
      <PatternsPage euphemisms={EUPHEMISMS} filters={FILTERS} story={STORY} />
    </Frame>
  );
}

export function NoEuphemisms() {
  return (
    <Frame>
      <PatternsPage euphemisms={{}} filters={FILTERS} story={STORY} />
    </Frame>
  );
}

export function NoActiveStory() {
  const filters = FILTERS.map((f) => ({ ...f, hits: 0 }));
  return (
    <Frame>
      <PatternsPage euphemisms={{}} filters={filters} story={null} />
    </Frame>
  );
}
