/**
 * Babylon Frontend v2 — Mock Data Fixtures
 *
 * Spec 061 US7 (T115): this file is preserved ONLY for v1-style
 * visualization placeholders (HexMapPlaceholder, TopologyGraphPlaceholder,
 * TopBarV2) and for the verb-target catalog in `lib/verb-config.ts`.
 *
 * None of the v2 pages (Briefing, Orgs, Verb, Intel, Results, Analysis)
 * import from this module any more — they read the live engine state
 * via `useGameState` + `useTimeseries`. The full deletion of this file
 * is deferred to a follow-up spec that replaces the verb-target catalog
 * with engine-sourced target endpoints (T091's full implementation).
 *
 * Original purpose:
 *   Port of ui_kits/webapp_v2/mock-data.jsx into typed TypeScript.
 *   Was the single source of truth for all v2 routes during development.
 */

import type {
  V2Org,
  V2Territory,
  V2Community,
  V2Edge,
  V2Event,
  V2Verb,
  V2Route,
  V2BreakdownEntry,
  V2ClassCharacter,
} from "@/types/v2-types";

// --- Tick / Session ---
export const TICK = 42;
export const SESSION_ID = "wayne-county-2026-001";
export const SCENARIO = { key: "wayne_county", name: "Wayne County Organizer", territories: 81 };

// --- Organizations ---
export const ORGS: V2Org[] = [
  {
    id: "ORG001",
    name: "Wayne County Labor Federation",
    short: "WCLF",
    player_controlled: true,
    org_type: "civil_society_org",
    class_character: "proletarian",
    hq_territory: "T-DEARBORN-E",
    ooda_phase: "DECIDE",
    cohesion: 0.71,
    legitimacy: 0.63,
    opacity: 0.58,
    vanguard: { cl: 8.4, cl_max: 12, sl: 24.1, sl_max: 44, rep: 0.63, budget: 142, heat: 0.71 },
    members: ["C-DEARBORN-PROLE", "C-HAMTRAMCK-IMM", "C-DETROIT-E-LUMP"],
    last_action: { tick: 41, verb: "educate", target: "C-DEARBORN-PROLE", outcome: "+0.04 CON" },
    badges: ["NEW_AFRIKAN_LED", "AUTONOMOUS"],
  },
  {
    id: "ORG002",
    name: "Detroit Tenants Coalition",
    short: "DTC",
    player_controlled: true,
    org_type: "tenants_union",
    class_character: "proletarian",
    hq_territory: "T-DETROIT-CENTRAL",
    ooda_phase: "OBSERVE",
    cohesion: 0.54,
    legitimacy: 0.71,
    opacity: 0.42,
    vanguard: { cl: 4.2, cl_max: 8, sl: 13.3, sl_max: 28, rep: 0.71, budget: 78, heat: 0.34 },
    members: ["C-DETROIT-C-PROLE", "C-DETROIT-E-LUMP"],
    last_action: { tick: 41, verb: "mobilize", target: "C-DETROIT-C-PROLE", outcome: "+0.07 SOL" },
    badges: ["WOMEN_LED", "PROTECTED"],
  },
  {
    id: "ORG-NPC-001",
    name: "Wayne County Sheriff's Department",
    short: "WCSD",
    player_controlled: false,
    org_type: "state_apparatus",
    class_character: "bourgeois",
    hq_territory: "T-DETROIT-CENTRAL",
    ooda_phase: "ACT",
    cohesion: 0.92,
    legitimacy: 0.41,
    opacity: 0.18,
    members: [],
    badges: [],
    last_observed_tick: 42,
    threat_level: "HIGH",
  },
  {
    id: "ORG-NPC-002",
    name: "Detroit Finance Bloc",
    short: "DFB",
    player_controlled: false,
    org_type: "capital_bloc",
    class_character: "comprador_bourgeois",
    hq_territory: "T-DETROIT-CENTRAL",
    ooda_phase: "DECIDE",
    cohesion: 0.81,
    legitimacy: 0.58,
    opacity: 0.74,
    members: [],
    badges: [],
    last_observed_tick: 39,
    threat_level: "MEDIUM",
  },
  {
    id: "ORG-NPC-003",
    name: "Settler Militia 'III%'",
    short: "S3",
    player_controlled: false,
    org_type: "reactionary_paramilitary",
    class_character: "labor_aristocrat",
    hq_territory: "T-DOWNRIVER",
    ooda_phase: "ORIENT",
    cohesion: 0.68,
    legitimacy: 0.22,
    opacity: 0.81,
    members: [],
    badges: [],
    last_observed_tick: 40,
    threat_level: "EMERGING",
  },
];

// --- Territories ---
export const TERRITORIES: V2Territory[] = [
  {
    id: "T-DEARBORN-E",
    name: "Dearborn East",
    county: "Wayne",
    pop: 41200,
    rent: 0.34,
    con: 0.42,
    sol: 0.61,
    heat: 0.71,
    wealth: 0.31,
    biocap: 0.42,
    dominant_community: "PROLE",
  },
  {
    id: "T-DETROIT-CENTRAL",
    name: "Detroit Central",
    county: "Wayne",
    pop: 88300,
    rent: 0.51,
    con: 0.38,
    sol: 0.44,
    heat: 0.84,
    wealth: 0.18,
    biocap: 0.31,
    dominant_community: "PROLE",
  },
  {
    id: "T-HAMTRAMCK",
    name: "Hamtramck",
    county: "Wayne",
    pop: 22100,
    rent: 0.28,
    con: 0.51,
    sol: 0.72,
    heat: 0.42,
    wealth: 0.39,
    biocap: 0.55,
    dominant_community: "IMM",
  },
  {
    id: "T-DOWNRIVER",
    name: "Downriver",
    county: "Wayne",
    pop: 51400,
    rent: 0.18,
    con: 0.21,
    sol: 0.31,
    heat: 0.34,
    wealth: 0.62,
    biocap: 0.71,
    dominant_community: "LABOR_ARISTO",
  },
  {
    id: "T-DETROIT-E",
    name: "Detroit East",
    county: "Wayne",
    pop: 64200,
    rent: 0.41,
    con: 0.32,
    sol: 0.38,
    heat: 0.61,
    wealth: 0.21,
    biocap: 0.34,
    dominant_community: "LUMP",
  },
];

// --- Communities (XGI hyperedges) ---
export const COMMUNITIES: V2Community[] = [
  {
    id: "C-DEARBORN-PROLE",
    name: "Dearborn Proletarian Workers",
    composition: ["NEW_AFRIKAN", "ARAB_AMERICAN", "WORKING_CLASS"],
    territories: ["T-DEARBORN-E"],
    members: 8400,
    con: 0.42,
    sol: 0.61,
    credibility_to: { ORG001: 0.72, ORG002: 0.31 },
    dominant_class: "proletarian",
  },
  {
    id: "C-DETROIT-E-LUMP",
    name: "Detroit East Lumpen Reserve",
    composition: ["NEW_AFRIKAN", "INCARCERATED", "UNDEREMPLOYED"],
    territories: ["T-DETROIT-E"],
    members: 11200,
    con: 0.28,
    sol: 0.34,
    credibility_to: { ORG001: 0.41, ORG002: 0.52 },
    dominant_class: "lumpen",
  },
  {
    id: "C-HAMTRAMCK-IMM",
    name: "Hamtramck Immigrant Communities",
    composition: ["BANGLADESHI", "YEMENI", "WORKING_CLASS"],
    territories: ["T-HAMTRAMCK"],
    members: 6300,
    con: 0.51,
    sol: 0.72,
    credibility_to: { ORG001: 0.68, ORG002: 0.44 },
    dominant_class: "proletarian",
  },
  {
    id: "C-DOWNRIVER-LA",
    name: "Downriver Labor Aristocracy",
    composition: ["SETTLER", "UNIONIZED", "HOMEOWNERS"],
    territories: ["T-DOWNRIVER"],
    members: 14800,
    con: 0.21,
    sol: 0.31,
    credibility_to: { ORG001: 0.55, ORG002: 0.18 },
    dominant_class: "labor_aristocracy",
  },
  {
    id: "C-DETROIT-C-PROLE",
    name: "Detroit Central Tenant Class",
    composition: ["NEW_AFRIKAN", "WOMEN", "RENTERS"],
    territories: ["T-DETROIT-CENTRAL"],
    members: 22100,
    con: 0.38,
    sol: 0.44,
    credibility_to: { ORG001: 0.39, ORG002: 0.78 },
    dominant_class: "proletarian",
  },
];

// --- Edges ---
export const EDGES: V2Edge[] = [
  {
    id: "E001",
    type: "EXPLOITATION",
    source: "ORG-NPC-002",
    target: "C-DEARBORN-PROLE",
    intensity: 0.72,
    rate_of_profit: 0.34,
  },
  {
    id: "E002",
    type: "SOLIDARITY",
    source: "ORG001",
    target: "ORG002",
    intensity: 0.61,
    age_ticks: 12,
  },
  {
    id: "E003",
    type: "REPRESSION",
    source: "ORG-NPC-001",
    target: "ORG001",
    intensity: 0.71,
    last_event: "informant detected",
  },
  {
    id: "E004",
    type: "TRIBUTE",
    source: "T-DEARBORN-E",
    target: "ORG-NPC-002",
    intensity: 0.42,
    value_flow_per_tick: 1.2,
  },
  {
    id: "E005",
    type: "TENANCY",
    source: "C-DETROIT-C-PROLE",
    target: "ORG-NPC-002",
    intensity: 0.81,
    rent_burden: 0.43,
  },
];

// --- Events ---
export const EVENTS: V2Event[] = [
  {
    id: "ev001",
    tick: 42,
    type: "REPRESSION_SPIKE",
    severity: "critical",
    title: "Informant detected in Wayne County Labor Federation",
    body: "Pattern-of-life analysis suggests an informant has been active for 6 ticks. Heat elevated +0.12.",
    actors: ["ORG-NPC-001", "ORG001"],
  },
  {
    id: "ev002",
    tick: 42,
    type: "CONSCIOUSNESS_SHIFT",
    severity: "info",
    title: "Class consciousness rising in Hamtramck Immigrant Communities",
    body: "Solidarity transmission from Dearborn organizing carried over. CON +0.07 this tick.",
    actors: ["C-HAMTRAMCK-IMM"],
  },
  {
    id: "ev003",
    tick: 41,
    type: "EXTRACTION",
    severity: "warning",
    title: "Imperial rent increased in Dearborn East",
    body: "Detroit Finance Bloc raised effective rents 4.2% — unequal exchange ratio now 1.34.",
    actors: ["ORG-NPC-002", "T-DEARBORN-E"],
  },
  {
    id: "ev004",
    tick: 41,
    type: "TURF_PRESSURE",
    severity: "warning",
    title: "Settler Militia 'III%' observed scouting Downriver",
    body: "Reactionary paramilitary OODA shift to ORIENT. May contest territory next 3 ticks.",
    actors: ["ORG-NPC-003", "T-DOWNRIVER"],
  },
  {
    id: "ev005",
    tick: 40,
    type: "SOLIDARITY_FORMED",
    severity: "good",
    title: "New solidarity edge: WCLF ↔ DTC",
    body: "Co-org assembly in Hamtramck produced a stable solidarity edge (intensity 0.61).",
    actors: ["ORG001", "ORG002"],
  },
];

// --- Time series ---
function makeSeries(base: number, drift: number, n = 24): number[] {
  const out: number[] = [];
  let v = base;
  for (let i = 0; i < n; i++) {
    // Mock fixture data only — not security-sensitive; deterministic seeding
    // would be an option but adds complexity for no gameplay benefit.
    // eslint-disable-next-line sonarjs/pseudo-random
    v = Math.max(0, Math.min(1, v + (Math.random() - 0.5) * 0.04 + drift * 0.005));
    out.push(v);
  }
  return out;
}

export const TIMESERIES = {
  imperial_rent: makeSeries(0.31, 0.5),
  consciousness: makeSeries(0.3, 0.8),
  solidarity: makeSeries(0.42, 0.6),
  heat: makeSeries(0.55, 0.4),
  wealth: makeSeries(0.32, -0.2),
  biocapacity: makeSeries(0.51, -0.3),
};

// --- Verbs ---
export const VERBS: V2Verb[] = [
  {
    verb: "educate",
    label: "Educate",
    glyph: "◐",
    target_type: "community",
    cost_label: "3 CL",
    desc: "Raise consciousness via political education in a target community.",
  },
  {
    verb: "aid",
    label: "Aid",
    glyph: "◇",
    target_type: "org_or_territory",
    cost_label: "$50",
    desc: "Transfer material resources to allied org or territory infrastructure.",
  },
  {
    verb: "attack",
    label: "Attack",
    glyph: "▲",
    target_type: "org_or_territory",
    cost_label: "8 CL",
    desc: "Targeted sabotage of bourgeois institution. Increases Heat.",
  },
  {
    verb: "mobilize",
    label: "Mobilize",
    glyph: "◈",
    target_type: "community",
    cost_label: "5 SL",
    desc: "Convert sympathizer labor into collective action in a community assembly.",
  },
  {
    verb: "campaign",
    label: "Campaign",
    glyph: "◢",
    target_type: "territory_or_community",
    cost_label: "4 CL",
    desc: "Sustained organizing campaign in a territory or community.",
  },
  {
    verb: "move",
    label: "Move",
    glyph: "→",
    target_type: "territory",
    cost_label: "1 CL",
    desc: "Relocate org HQ or cadre to a new territory.",
  },
  {
    verb: "investigate",
    label: "Investigate",
    glyph: "◉",
    target_type: "any",
    cost_label: "2 CL",
    desc: "Reduce opacity on a target — org, edge, territory, or community.",
  },
  {
    verb: "reproduce",
    label: "Reproduce",
    glyph: "⬡",
    target_type: "org",
    cost_label: "10 CL",
    desc: "Organizational reproduction — convert sympathizers to cadre, train successors.",
  },
  {
    verb: "negotiate",
    label: "Negotiate",
    glyph: "⇄",
    target_type: "org",
    cost_label: "1 CL",
    desc: "Open negotiation channel with another org. Risks legitimacy.",
  },
];

// --- Routes ---
export const ROUTES: V2Route[] = [
  { key: "login", path: "/login", label: "Login", group: "pre", icon: "◌" },
  { key: "games", path: "/games", label: "Games", group: "pre", icon: "▤" },
  { key: "briefing", path: "/games/:id", label: "Briefing", group: "core", icon: "◐" },
  { key: "orgs", path: "/games/:id/orgs", label: "Orgs", group: "core", icon: "◇" },
  { key: "intel", path: "/games/:id/intel/:type/:tid", label: "Intel", group: "core", icon: "◉" },
  { key: "results", path: "/games/:id/results", label: "Results", group: "core", icon: "▦" },
  {
    key: "v_educate",
    path: "/games/:id/actions/educate",
    label: "Educate",
    group: "verb",
    icon: "◐",
  },
  { key: "v_aid", path: "/games/:id/actions/aid", label: "Aid", group: "verb", icon: "◇" },
  { key: "v_attack", path: "/games/:id/actions/attack", label: "Attack", group: "verb", icon: "▲" },
  {
    key: "v_mobilize",
    path: "/games/:id/actions/mobilize",
    label: "Mobilize",
    group: "verb",
    icon: "◈",
  },
  {
    key: "v_campaign",
    path: "/games/:id/actions/campaign",
    label: "Campaign",
    group: "verb",
    icon: "◢",
  },
  { key: "v_move", path: "/games/:id/actions/move", label: "Move", group: "verb", icon: "→" },
  {
    key: "v_invest",
    path: "/games/:id/actions/investigate",
    label: "Investigate",
    group: "verb",
    icon: "◉",
  },
  {
    key: "v_reproduce",
    path: "/games/:id/actions/reproduce",
    label: "Reproduce",
    group: "verb",
    icon: "⬡",
  },
  {
    key: "v_negotiate",
    path: "/games/:id/actions/negotiate",
    label: "Negotiate",
    group: "verb",
    icon: "⇄",
  },
  { key: "analysis", path: "/games/:id/analysis", label: "Analysis", group: "post", icon: "◊" },
];

// --- Scope resolver ---
export const Scope = {
  getPlayer: () => ({
    scope: "Player",
    username: "percy",
    orgs: ORGS.filter((o) => o.player_controlled).map((o) => o.id),
  }),
  getOrg: (id: string) => ORGS.find((o) => o.id === id),
  getTerritory: (id: string) => TERRITORIES.find((t) => t.id === id),
  getCommunity: (id: string) => COMMUNITIES.find((c) => c.id === id),
  getEdge: (id: string) => EDGES.find((e) => e.id === id),
  getOrgsBy: (filter: (o: V2Org) => boolean) => ORGS.filter(filter),
  getCommunitiesIn: (terrId: string) => COMMUNITIES.filter((c) => c.territories.includes(terrId)),
  getEdgesOf: (id: string) => EDGES.filter((e) => e.source === id || e.target === id),
  getScriptValueBreakdown: (name: string): V2BreakdownEntry[] => {
    const breakdowns: Record<string, V2BreakdownEntry[]> = {
      heat: [
        { label: "Base", value: 0.2 },
        { label: "Recent attacks (×3)", value: 0.18 },
        { label: "Informant penalty", value: 0.12 },
        { label: "Adjacent state action", value: 0.21 },
      ],
      cohesion: [
        { label: "Base", value: 0.4 },
        { label: "Reproduction edge", value: 0.2 },
        { label: "Educate streak (4)", value: 0.11 },
        { label: "Heat penalty", value: -0.05 },
      ],
      consciousness: [
        { label: "Base", value: 0.2 },
        { label: "Educate spillover", value: 0.07 },
        { label: "Solidarity transmission", value: 0.05 },
        { label: "Material conditions", value: 0.1 },
      ],
    };
    return breakdowns[name] ?? [];
  },
};

// --- Color maps (Article VII: color encodes meaning) ---
export const CLASS_COLORS: Record<V2ClassCharacter, string> = {
  proletarian: "#e04040",
  bourgeois: "#c8a860",
  comprador_bourgeois: "#e0a030",
  labor_aristocracy: "#80b0e0",
  labor_aristocrat: "#80b0e0",
  lumpen: "#a070d0",
};

export const EDGE_COLORS: Record<string, string> = {
  EXPLOITATION: "#e04040",
  SOLIDARITY: "#40c040",
  REPRESSION: "#e0a030",
  TRIBUTE: "#c8a860",
  TENANCY: "#a070d0",
  WAGES: "#80b0e0",
  ADJACENCY: "#404040",
};
