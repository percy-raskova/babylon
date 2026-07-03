// mock-data.jsx — Babylon Web App UI Kit · Cold Collapse v8
// Single source of truth for the click-through prototype.

const MOCK = {
  scenario: { key: "wayne_county", name: "Wayne County Organizer", region: "Detroit Metro, MI", territories: 81, year: 2031, week: 14 },
  player_org: {
    id: "WCLF", name: "Wayne County Labor Federation", short: "WCLF",
    org_type: "civil_society_org", class_character: "proletarian",
    founded_tick: -240, members: 4820, ooda_phase: "decide",
    vanguard: { cl: 8.4, cl_max: 12, sl: 24.1, sl_max: 44, rep: 0.63, budget: 142, heat: 0.71 },
    history_cl:  [6.2, 6.8, 7.1, 7.4, 7.0, 7.6, 8.1, 8.4],
    history_sl:  [18.0, 19.2, 20.1, 22.4, 23.0, 23.5, 23.9, 24.1],
    history_rep: [0.51, 0.54, 0.56, 0.58, 0.60, 0.61, 0.62, 0.63],
    history_heat:[0.40, 0.45, 0.50, 0.58, 0.61, 0.64, 0.69, 0.71],
  },
  orgs_other: [
    { id: "DTC",  name: "Detroit Tenants Council",        type: "civil",  class: "proletarian",        rel: "ally",      strength: 0.62 },
    { id: "DFB",  name: "Detroit Food Not Bombs",         type: "mutual", class: "proletarian",        rel: "ally",      strength: 0.41 },
    { id: "WCSD", name: "Wayne County Sheriff's Dept",    type: "state",  class: "state_apparatus",   rel: "hostile",   strength: 0.82 },
    { id: "FORD", name: "Ford Motor Company",             type: "corp",   class: "bourgeois",          rel: "exploiter", strength: 0.93 },
    { id: "FCA",  name: "Fiat-Chrysler Detroit Plant",    type: "corp",   class: "bourgeois",          rel: "exploiter", strength: 0.78 },
    { id: "UAW",  name: "UAW Local 600",                  type: "union",  class: "labor_aristocracy",  rel: "ambivalent",strength: 0.55 },
    { id: "DEAR", name: "Dearborn Community Defense",     type: "mutual", class: "proletarian",        rel: "ally",      strength: 0.34 },
  ],
  territories: [
    { id: "T01", name: "Dearborn",          class: "proletarian",        pop: 109_976, heat: 0.51, rent: 0.42, consciousness: 0.61, wealth: 0.32, biocap: 0.58, controlling_org: "WCLF" },
    { id: "T02", name: "Detroit East",      class: "lumpenproletariat",  pop: 142_300, heat: 0.78, rent: 0.71, consciousness: 0.34, wealth: 0.18, biocap: 0.41, controlling_org: null },
    { id: "T03", name: "Hamtramck",         class: "proletarian",        pop: 22_400,  heat: 0.44, rent: 0.39, consciousness: 0.58, wealth: 0.29, biocap: 0.62, controlling_org: "DTC" },
    { id: "T04", name: "Downriver",         class: "labor_aristocracy",  pop: 198_500, heat: 0.31, rent: 0.28, consciousness: 0.41, wealth: 0.55, biocap: 0.72, controlling_org: "UAW" },
    { id: "T05", name: "Grosse Pointe",     class: "bourgeois",          pop: 45_200,  heat: 0.18, rent: 0.12, consciousness: 0.08, wealth: 0.91, biocap: 0.81, controlling_org: "FORD" },
    { id: "T06", name: "Detroit West",      class: "proletarian",        pop: 88_400,  heat: 0.62, rent: 0.55, consciousness: 0.49, wealth: 0.22, biocap: 0.48, controlling_org: null },
  ],
  events: [
    { id: "e1", tick: 41, type: "EXTRACTION",    severity: "warning",  text: "Imperial rent +0.042 in Dearborn — Ford Motor land lease enforcement" },
    { id: "e2", tick: 42, type: "CONSCIOUSNESS", severity: "info",     text: "Class consciousness rising in Wayne County periphery (+0.018)" },
    { id: "e3", tick: 42, type: "HEAT_SPIKE",    severity: "critical", text: "State heat elevated — informant detected in organizing network" },
    { id: "e4", tick: 40, type: "SOLIDARITY",    severity: "info",     text: "Solidarity edge formed: WCLF ↔ Detroit Tenants Council" },
    { id: "e5", tick: 39, type: "RUPTURE",       severity: "rupture",  text: "Wildcat strike at Fiat-Chrysler Detroit — 480 workers walk out" },
    { id: "e6", tick: 38, type: "REPRESSION",    severity: "warning",  text: "WCSD raid on Hamtramck Tenants Union meeting — 4 arrested" },
    { id: "e7", tick: 37, type: "AID",           severity: "info",     text: "$50 transferred from WCLF to Detroit Food Not Bombs" },
  ],
  verbs: [
    { id: "educate",   label: "Educate",   cost: "3 CL",  desc: "Raise consciousness in target community",       icon: "◎", color: "var(--cadre)" },
    { id: "mobilize",  label: "Mobilize",  cost: "5 SL",  desc: "Activate sympathizers for direct action",       icon: "◈", color: "var(--solidarity)" },
    { id: "attack",    label: "Attack",    cost: "8 CL",  desc: "Targeted sabotage of bourgeois institution",    icon: "▲", color: "var(--laser)" },
    { id: "aid",       label: "Aid",       cost: "$50",   desc: "Transfer material resources to allied org",     icon: "◆", color: "var(--rupture)" },
    { id: "recruit",   label: "Recruit",   cost: "2 CL",  desc: "Convert sympathizer labor into cadre labor",    icon: "✚", color: "var(--spire)" },
    { id: "propaganda",label: "Propaganda",cost: "4 CL",  desc: "Region-wide consciousness/reputation boost",    icon: "◐", color: "var(--population)" },
  ],
  notifications: [
    { id: "n1", text: "WCLF cadre labor regenerated (+1.2)", read: false },
    { id: "n2", text: "Heat threshold approaching critical (0.71/0.80)", read: false },
    { id: "n3", text: "New scenario event: Auto strike rumors", read: false },
  ],
};

window.MOCK = MOCK;
