// community-data.jsx — mock data for the community hypergraph
// Article VIII.9: community membership is a hyperedge. Rendered here as:
//   (a) intersection analysis (UpSet)  (b) choropleth on hexes (dominant composition)
//   (c) inspector badges (per-territory shares)  (d) verb target picker (Educate)

// ─────────────────────────────────────────────────────────────
// COMMUNITIES — the 9 hyperedges we model in this scenario
// Ordered top-down as they will appear in the UpSet matrix (heaviest first)
// ─────────────────────────────────────────────────────────────
const COMMUNITIES = [
  { id: "SETTLER",      label: "Settler",            short: "SET",
    count: 1840000, color: "#8a93a0",
    desc: "White American national identity. The base of every settler formation." },
  { id: "WORKING",      label: "Working Class",      short: "WRK",
    count: 1560000, color: "#ff3344",
    desc: "Wage-labor dependent. Cross-cuts every national community." },
  { id: "WOMEN",        label: "Women",              short: "WMN",
    count: 1620000, color: "#a070d0",
    desc: "Gendered reproductive labor; super-exploited within each national community." },
  { id: "LABOR_ARIST",  label: "Labor Aristocracy",  short: "LAR",
    count: 720000,  color: "#d4a02c",
    desc: "Imperial-rent-extracting strata. The trap of settler socialism." },
  { id: "NEW_AFRIKAN",  label: "New Afrikan",        short: "NAF",
    count: 480000,  color: "#5fbf7a",
    desc: "Black national identity. Internal colony." },
  { id: "CHICANO",      label: "Chicano",            short: "CHI",
    count: 320000,  color: "#d97a2c",
    desc: "Mexican-descended national. Aztlán." },
  { id: "QUEER",        label: "Queer",              short: "QER",
    count: 240000,  color: "#4dd9e6",
    desc: "Non-heteronormative gender / sexuality." },
  { id: "INDIGENOUS",   label: "Indigenous",         short: "IND",
    count: 68000,   color: "#e0a030",
    desc: "First Nations of Turtle Island. Original sovereignty." },
  { id: "INCARCERATED", label: "Incarcerated",       short: "INC",
    count: 38000,   color: "#b8321f",
    desc: "Carceral subjection. Disproportionately NAF, CHI, IND." },
];
const COMM_BY_ID = Object.fromEntries(COMMUNITIES.map(c => [c.id, c]));

// ─────────────────────────────────────────────────────────────
// INTERSECTIONS — the actual hyperedge cardinalities that matter politically.
// Sorted descending by count, top ~16 shown in UpSet. `ids` arrays MUST be
// sorted in COMMUNITIES order so matrix lookup is direct.
// `note` only on politically-salient intersections — surfaces as annotation.
// ─────────────────────────────────────────────────────────────
const INTERSECTIONS = [
  { ids: ["SETTLER","WORKING","WOMEN"],            count: 412000 },
  { ids: ["SETTLER","WORKING"],                    count: 388000 },
  { ids: ["SETTLER","WOMEN","LABOR_ARIST"],        count: 296000,
    note: "The labor-aristocracy 'middle' — the constituency settler socialism captures." },
  { ids: ["SETTLER","LABOR_ARIST"],                count: 268000 },
  { ids: ["WORKING","WOMEN","NEW_AFRIKAN"],        count: 182000,
    note: "Triple-burdened: race, gender, class. Highest mobilization potential per cost." },
  { ids: ["WORKING","WOMEN"],                      count: 174000 },
  { ids: ["SETTLER","LABOR_ARIST","WORKING"],      count: 142000 },
  { ids: ["WORKING","WOMEN","CHICANO"],            count: 124000 },
  { ids: ["WORKING","NEW_AFRIKAN"],                count: 108000 },
  { ids: ["WORKING","CHICANO"],                    count:  92000 },
  { ids: ["WORKING","WOMEN","QUEER"],              count:  58000 },
  { ids: ["SETTLER","WORKING","QUEER"],            count:  46000 },
  { ids: ["WORKING","NEW_AFRIKAN","INCARCERATED"], count:  22000,
    note: "Disproportionate carceral concentration. Central to Article VIII.9 example." },
  { ids: ["WOMEN","INDIGENOUS"],                   count:  21000 },
  { ids: ["WORKING","NEW_AFRIKAN","QUEER"],        count:  17000 },
  { ids: ["INDIGENOUS","INCARCERATED"],            count:   4200,
    note: "Smallest visible intersection — outsize political weight." },
];

// ─────────────────────────────────────────────────────────────
// PER-REGION COMMUNITY COMPOSITION
// For each US region (defined in map-data), declare the dominant + share of
// each community in that region. Numbers are mock; what matters is the pattern.
// We'll project these onto hexes to build the choropleth.
// ─────────────────────────────────────────────────────────────
const REGION_COMPOSITION = {
  // [region_id]: { dominant: id, mix: { id: share } } — shares need not sum to 1
  // (a person is in many communities)
  PACNW:  { dominant: "SETTLER",     mix: { SETTLER:.62, WORKING:.48, WOMEN:.51, LABOR_ARIST:.32, QUEER:.10, INDIGENOUS:.04 } },
  CAL:    { dominant: "CHICANO",     mix: { SETTLER:.34, WORKING:.58, WOMEN:.50, CHICANO:.39, NEW_AFRIKAN:.06, QUEER:.11 } },
  MTNW:   { dominant: "SETTLER",     mix: { SETTLER:.70, WORKING:.41, WOMEN:.49, INDIGENOUS:.12, LABOR_ARIST:.18 } },
  MTNS:   { dominant: "INDIGENOUS",  mix: { SETTLER:.41, INDIGENOUS:.36, CHICANO:.18, WORKING:.49, WOMEN:.50 } },
  SW:     { dominant: "INDIGENOUS",  mix: { SETTLER:.32, INDIGENOUS:.31, CHICANO:.27, WORKING:.54, WOMEN:.50 } },
  TX:     { dominant: "CHICANO",     mix: { SETTLER:.41, CHICANO:.34, NEW_AFRIKAN:.13, WORKING:.55, WOMEN:.50, INCARCERATED:.02 } },
  PLNS:   { dominant: "SETTLER",     mix: { SETTLER:.78, WORKING:.39, WOMEN:.49, INDIGENOUS:.08 } },
  MWST:   { dominant: "WORKING",     mix: { SETTLER:.52, NEW_AFRIKAN:.21, WORKING:.61, WOMEN:.51, LABOR_ARIST:.28, INCARCERATED:.014 } },
  DEEP:   { dominant: "NEW_AFRIKAN", mix: { SETTLER:.42, NEW_AFRIKAN:.41, WORKING:.59, WOMEN:.52, INCARCERATED:.022 } },
  SE:     { dominant: "NEW_AFRIKAN", mix: { SETTLER:.48, NEW_AFRIKAN:.35, WORKING:.56, WOMEN:.52, INCARCERATED:.018 } },
  FL:     { dominant: "SETTLER",     mix: { SETTLER:.49, NEW_AFRIKAN:.21, CHICANO:.18, WORKING:.52, WOMEN:.52, QUEER:.08 } },
  MIDATL: { dominant: "WORKING",     mix: { SETTLER:.46, NEW_AFRIKAN:.26, WORKING:.58, WOMEN:.52, LABOR_ARIST:.30, QUEER:.09 } },
  NE:     { dominant: "WORKING",     mix: { SETTLER:.51, NEW_AFRIKAN:.18, WORKING:.62, WOMEN:.51, LABOR_ARIST:.31 } },
  NEAST:  { dominant: "LABOR_ARIST", mix: { SETTLER:.46, NEW_AFRIKAN:.16, WORKING:.46, WOMEN:.52, LABOR_ARIST:.41, QUEER:.12 } },
};

// ─────────────────────────────────────────────────────────────
// PLAYER ORG — for verb page context
// ─────────────────────────────────────────────────────────────
const PLAYER_ORG = {
  id: "ORG_DET_REVOLUTIONARY_ASSEMBLY",
  short: "DRA",
  name: "Detroit Revolutionary Assembly",
  ideology: "ANTI-COLONIAL COMMUNISM",
  cohesion: 0.62, budget: 184, ooda: "ACT",
  // which communities the org currently operates in (overlap → cheaper)
  reach: { NEW_AFRIKAN: 0.41, WORKING: 0.28, WOMEN: 0.22, INCARCERATED: 0.18, CHICANO: 0.04 },
};

// ─────────────────────────────────────────────────────────────
// EDUCATE TARGETS — what the verb page shows.
// For each candidate community hyperedge: cost, predicted shift, overlap.
// Sorted by predicted_shift / cost (best ROI first).
// ─────────────────────────────────────────────────────────────
const EDUCATE_TARGETS = [
  { community_id: "NEW_AFRIKAN",
    cost: 12, members_reached: 197000, predicted_consciousness_shift: +0.041,
    overlap: 0.41, baseline_consciousness: 0.48, predicted_after: 0.521,
    notes: "DRA holds 41% reach. Cadre density highest. Lowest cost-per-shift." },
  { community_id: "INCARCERATED",
    cost: 28, members_reached: 6900, predicted_consciousness_shift: +0.083,
    overlap: 0.18, baseline_consciousness: 0.62, predicted_after: 0.703,
    notes: "Smallest community but highest per-capita shift. Carceral isolation amplifies effect." },
  { community_id: "WORKING",
    cost: 18, members_reached: 437000, predicted_consciousness_shift: +0.018,
    overlap: 0.28, baseline_consciousness: 0.34, predicted_after: 0.358,
    notes: "Largest community by absolute reach. Cross-cuts all national communities." },
  { community_id: "WOMEN",
    cost: 22, members_reached: 356000, predicted_consciousness_shift: +0.014,
    overlap: 0.22, baseline_consciousness: 0.39, predicted_after: 0.404,
    notes: "Gendered reproductive cadre needed. Effective with WORKING co-targeting." },
  { community_id: "CHICANO",
    cost: 34, members_reached: 12000, predicted_consciousness_shift: +0.008,
    overlap: 0.04, baseline_consciousness: 0.51, predicted_after: 0.518,
    notes: "Sparse reach. Pre-requisite: Move action into TX or SW first." },
  { community_id: "LABOR_ARIST",
    cost: 48, members_reached: 86000, predicted_consciousness_shift: -0.003,
    overlap: 0.0,  baseline_consciousness: 0.18, predicted_after: 0.177,
    warning: "Negative expected shift. Imperial rent renders this community resistant.",
    notes: "Article XII.4: do not educate the labor aristocracy. Their material interests bind them to empire." },
];

// ─────────────────────────────────────────────────────────────
// EVENTS — recent membership-flux events for the side panel
// ─────────────────────────────────────────────────────────────
const COMMUNITY_EVENTS = [
  { tick: 42, t: "−0 ticks", id: "EV1", kind: "RUPTURE",
    text: "NEW_AFRIKAN ∩ INCARCERATED bifurcated: +12% revolutionary consciousness post-uprising at Stateville." },
  { tick: 41, t: "−1 tick",  id: "EV2", kind: "TRANSMISSION",
    text: "Solidarity transmitted SETTLER∩WORKING ← NEW_AFRIKAN∩WORKING via auto-strike Detroit." },
  { tick: 40, t: "−2 ticks", id: "EV3", kind: "WARNING",
    text: "LABOR_ARIST ∩ SETTLER hardening. Imperial rent share rose +3.1% nationally." },
  { tick: 38, t: "−4 ticks", id: "EV4", kind: "FLUX",
    text: "WOMEN ∩ WORKING ∩ NEW_AFRIKAN gained +18,200 members; reproductive-labor strike spreading." },
];
