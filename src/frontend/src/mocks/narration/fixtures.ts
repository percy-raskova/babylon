/**
 * Fixture narration beats — Program 16 Lane N.
 *
 * Shares the preview-suite fiction documented in `.design-sync/NOTES.md`:
 * tick 104, Wayne County FIPS 26163, the Wayne County Labor Federation
 * (WCLF) hall raid on Schaefer Avenue, and `org-uaw-local-600` (UAW Local
 * 600 — labor-aristocratic, "ambivalent" toward WCLF per
 * `design/mockups/ui_kits/webapp/mock-data.jsx`). Grounded further in the
 * raid narrative from `design/mockups/wire/wire-data.jsx` and the
 * `.design-sync/previews/WireApp.tsx` exemplar (14 detained, T+71H called
 * strike, DHS "security operation" euphemism).
 *
 * Voice register (Design Bible §7): `"wire"` beats are newspaper
 * declaratives — actor + action lead, tick named in the second clause,
 * scare-quoted state euphemisms, no ALL-CAPS. `"analysis"` beats are the
 * longer theory register — periodic sentences naming the driving
 * contradiction explicitly.
 */

import type { NarrationBeat } from "@/types/narration";

export const NARRATION_FIXTURE_BEATS: NarrationBeat[] = [
  {
    id: "beat-wclf-strike-call",
    tick: 103,
    scope: "event",
    subjectRef: "evt-wclf-strike-call",
    headline: "Wayne County Labor Federation called a regional strike, tick 103.",
    body: "WCLF leadership set a seventy-one-hour strike window from the Schaefer Avenue hall floor, tick 103. The federal action against that same hall followed within three days.",
    register: "wire",
  },
  {
    id: "beat-wclf-raid",
    tick: 104,
    scope: "event",
    subjectRef: "evt-wclf-raid-0104",
    headline: "Federal agents raided the WCLF hall on Schaefer, tick 104.",
    body: 'Agents broke the front door at 0347 Tuesday, tick 104, detaining fourteen members of the Wayne County Labor Federation. The Department of Homeland Security called it a "security operation."',
    register: "wire",
  },
  {
    id: "beat-kaminski-injured",
    tick: 104,
    scope: "event",
    subjectRef: "evt-wclf-raid-0104",
    headline: 'Deputies "restrained" a seventy-one-year-old UAW man during the raid, tick 104.',
    body: "Deputies knelt on J. Kaminski, a lifetime UAW Local 600 member, for eleven minutes outside the hall, tick 104. He is listed at Beaumont Hospital with bruised ribs and a fractured orbital.",
    register: "wire",
  },
  {
    id: "beat-raid-timing-analysis",
    tick: 104,
    scope: "event",
    subjectRef: "evt-wclf-raid-0104",
    headline: "The raid's timing names its target.",
    body: "The federal action against the WCLF hall lands seventy-one hours before the union's own called strike deadline, tick 104. Read against the wage-hierarchy account of state timing as class discipline, the sequence is not coincidence: repression escalates precisely where organization threatens continuity of the extraction relation, not where disorder alone would justify it.",
    register: "analysis",
  },
  {
    id: "beat-heat-countywide",
    tick: 104,
    scope: "tick",
    subjectRef: null,
    headline: "Heat climbed across Wayne County, tick 104.",
    body: 'State pressure — what the wire still calls "security operations" — intensified county-wide, tick 104, in the hours after the Schaefer hall raid.',
    register: "wire",
  },
  {
    id: "beat-dtc-solidarity",
    tick: 105,
    scope: "event",
    subjectRef: "evt-dtc-solidarity-call",
    headline: "Detroit Tenants Council answered with a solidarity call, tick 105.",
    body: "DTC leadership announced a solidarity action for the fourteen detained WCLF members, tick 105, the first cross-org response of the week.",
    register: "wire",
  },
  {
    id: "beat-uaw-silence-analysis",
    tick: 105,
    scope: "tick",
    subjectRef: null,
    headline: "UAW Local 600 stayed on the sideline, tick 105.",
    body: "Local 600's leadership issued no statement on the raid, tick 105. The union's labor-aristocratic position — a Downriver wage premium financed by rent the Core extracts from the periphery — makes ambivalence, not solidarity, the materially rational choice for its leadership; the wage-hierarchy account predicts exactly this silence rather than treating it as a failure of nerve.",
    register: "analysis",
  },
  {
    id: "beat-county-rent-104",
    tick: 104,
    scope: "county",
    subjectRef: "26163",
    headline: "Wayne County's contradiction sharpened, tick 104.",
    body: "Imperial rent extraction in the county rose against an already-strained wage floor, tick 104, per the county's own extraction gauge.",
    register: "wire",
  },
  {
    id: "beat-county-wage-line-analysis",
    tick: 106,
    scope: "county",
    subjectRef: "26163",
    headline: "Wayne County splits along the wage line, tick 106.",
    body: "Downriver's labor-aristocratic wage premium, financed by rent extracted through the county's auto operations, continues to separate its material interest from Dearborn's and Detroit East's, tick 106. The county's consciousness gradient tracks this split more reliably than any single organizing campaign tracks it.",
    register: "analysis",
  },
  {
    id: "beat-ford-lease-enforcement",
    tick: 107,
    scope: "county",
    subjectRef: "26163",
    headline: 'Ford "enforced" its Dearborn land lease, tick 107.',
    body: "Imperial rent in Dearborn rose four hundredths as Ford Motor enforced lease terms on county land, tick 107. The company called the increase routine.",
    register: "wire",
  },
  {
    id: "beat-fca-wildcat",
    tick: 108,
    scope: "event",
    subjectRef: "evt-fca-wildcat",
    headline: "Workers walked out at the Fiat-Chrysler plant, tick 108.",
    body: 'Four hundred eighty workers left the line without a permit, tick 108. Management called it "unauthorized absence."',
    register: "wire",
  },
  {
    id: "beat-wclf-informant",
    tick: 110,
    scope: "event",
    subjectRef: "evt-wclf-informant",
    headline: "WCLF found an informant in its ranks, tick 110.",
    body: "Cadre discipline flagged a leak inside the organizing network, tick 110, days after county heat had spiked with no obvious external cause.",
    register: "wire",
  },
  {
    id: "beat-endgame-dual-power",
    tick: 312,
    scope: "endgame",
    subjectRef: null,
    headline: "Revolutionary councils across Wayne County declared dual power, tick 312.",
    body: 'The county\'s organized core crossed the threshold state media would not name outright, tick 312. History records what the wire called "unrest."',
    register: "wire",
  },
  {
    id: "beat-endgame-analysis",
    tick: 312,
    scope: "endgame",
    subjectRef: null,
    headline: "The fall of the wage hierarchy.",
    body: "What began as a raid on a Schaefer Avenue hall closed as the unmaking of the wage hierarchy that hall's members were raided for threatening, tick 312. Imperial rent, unable to buy acquiescence once its price exceeded what accumulation could bear, gave way to the organization the wage-hierarchy account predicted it eventually would.",
    register: "analysis",
  },
];
