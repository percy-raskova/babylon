/**
 * Spec 094: The Wire — TypeScript types matching the WireFeed contract.
 *
 * Mirrors `specs/094-the-wire/contracts/wire.yaml` and the data shape
 * from `design/mockups/wire/wire-data.jsx`. The WireFeed is produced by
 * the backend's DeterministicNarrator and served at
 * `GET /api/games/:id/wire/`.
 */

export interface WireMeta {
  tick: number;
  session: string;
  operator: string;
  freq: string;
  qth: string;
  classification: string;
  cable_id: string;
  page_of: string;
  timestamp_utc: string;
}

export type WireSeverity = "critical" | "warning" | "info";

export interface WireStoryIndex {
  id: string;
  tick: number;
  slug: string;
  hed: { c: string; l: string; i: string };
  coverage: ("c" | "l" | "i")[];
  pinned?: boolean;
  severity: WireSeverity;
}

export type WireFilterId = "ownership" | "advertising" | "sourcing" | "flak" | "ideology";

export interface EuphemismEntry {
  c: string;
  l: string;
  filter: WireFilterId;
  note: string;
}

export interface ManufacturingConsentFilter {
  id: WireFilterId;
  label: string;
  desc: string;
  hits: number;
  color: string;
}

/** A run within a paragraph — string, euphemism span, or superscript citation. */
export type WireRun = string | { euph: string; text: string } | { sup: number };

export interface BibliographyEntry {
  n: number;
  src: string;
  kind: string;
  id: string;
  chunk: string;
  sim: number;
}

export interface ContinentalStory {
  brand: string;
  monogram: string;
  kicker: string;
  hed: string;
  dek: string;
  byline: string;
  paragraphs: WireRun[][];
  bibliography: BibliographyEntry[];
}

export interface LiberatedMarginNote {
  ref: string;
  chunk: string;
  note: string;
}

export interface LiberatedParagraph {
  body: WireRun[];
  margin?: LiberatedMarginNote | null;
}

export interface LiberatedStory {
  brand: string;
  callsign: string;
  operator: string;
  hed: string;
  pre: string;
  post: string;
  paragraphs: LiberatedParagraph[];
}

export interface IntelField {
  key: string;
  value: string;
}

export interface IntelRef {
  tag: string;
  id: string;
  sim: number;
  src: string;
}

export interface IntelStory {
  classification: string;
  cable_id: string;
  origin: string;
  routing: string[];
  caveat: string;
  subj: string;
  fields: [string, string][];
  assessment: string[];
  refs: IntelRef[];
  distribution: string;
}

export interface WireStory {
  id: string;
  tick: number;
  location: string;
  time_local: string;
  continental: ContinentalStory;
  liberated: LiberatedStory;
  intel: IntelStory;
}

export interface WireFeed {
  meta: WireMeta;
  index: WireStoryIndex[];
  euphemisms: Record<string, EuphemismEntry>;
  story: WireStory | null;
  filters: ManufacturingConsentFilter[];
}

/** MSW contract-faithful fixture for testing. */
export const EMPTY_WIRE_FEED: WireFeed = {
  meta: {
    tick: 0,
    session: "",
    operator: "RASKOVA-2",
    freq: "88.7 MHz",
    qth: "WAYNE CO / GRID EN82",
    classification: "TS//SI//NOFORN",
    cable_id: "0000-A",
    page_of: "001/001",
    timestamp_utc: "2026-01-01T00:00:00Z",
  },
  index: [],
  euphemisms: {},
  story: null,
  filters: [
    { id: "ownership", label: "Ownership", desc: "", hits: 0, color: "var(--rent)" },
    { id: "advertising", label: "Advertising", desc: "", hits: 0, color: "var(--heat)" },
    { id: "sourcing", label: "Sourcing", desc: "", hits: 0, color: "var(--cadre)" },
    { id: "flak", label: "Flak", desc: "", hits: 0, color: "var(--thermal)" },
    { id: "ideology", label: "Anti-radical ideology", desc: "", hits: 0, color: "var(--laser)" },
  ],
};
