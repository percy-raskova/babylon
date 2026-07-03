// map-data.jsx — mock data for spec-070 Balkanization "The Map"
// All hex positions / influence values / sovereign claims are seeded mock data.

// ─────────────────────────────────────────────────────────────
// STANCE PALETTE — answer was option 4: blood / royal blue / phosphor
// ─────────────────────────────────────────────────────────────
const STANCE = {
  UPHOLD:  { id: "UPHOLD",  label: "Uphold",  color: "#ff3344", glow: "rgba(255,51,68,.55)",  short: "U" }, // laser
  IGNORE:  { id: "IGNORE",  label: "Ignore",  color: "#6b8fb5", glow: "rgba(107,143,181,.55)", short: "I" }, // cadre blue
  ABOLISH: { id: "ABOLISH", label: "Abolish", color: "#5fbf7a", glow: "rgba(95,191,122,.55)",  short: "A" }, // solidarity phosphor
};

// ─────────────────────────────────────────────────────────────
// FACTIONS — three starter factions per spec-070
// ─────────────────────────────────────────────────────────────
const FACTIONS = [
  {
    id: "FAC_RESTORATIONIST", name: "Restorationist Front",
    ideology: "FASCISM", stance: "UPHOLD", is_settler_formation: true,
    extraction_modifier: 1.5, violence_modifier: 2.0,
    class_reduction: 0.0, metabolic_reduction: -0.5,
    base: "Rural settlers · militia · police",
    blurb: "Explicit white-settler restoration. Camps, accelerated extraction, quick collapse.",
  },
  {
    id: "FAC_WORKERS_CONGRESS", name: "Workers' Congress",
    ideology: "SETTLER SOCIALISM", stance: "IGNORE", is_settler_formation: true,
    extraction_modifier: 0.8, violence_modifier: 0.5,
    class_reduction: 0.7, metabolic_reduction: 0.0,
    base: "Industrial unions · settler proletariat",
    blurb: "The trap. Universal healthcare, fair wages — but the pipelines still flow. Red flags over stolen land.",
  },
  {
    id: "FAC_DECOLONIAL", name: "Decolonial Front",
    ideology: "ANTI-COLONIAL COMMUNISM", stance: "ABOLISH", is_settler_formation: false,
    extraction_modifier: 0.0, violence_modifier: 0.3,
    class_reduction: 0.5, metabolic_reduction: 0.8,
    base: "Indigenous · Black national liberation · anti-colonial cadre",
    blurb: "Land Back. The only coalition that ceases extraction. The only path that does not end in ecological collapse.",
  },
];
const FAC_BY_ID = Object.fromEntries(FACTIONS.map(f => [f.id, f]));

// ─────────────────────────────────────────────────────────────
// CONTINENTAL US — stylized macro-regions in a 940×500 viewBox.
// Each region is a polygon string for SVG <polygon>.
// They tile together to form a recognizable abstracted continental US.
// ─────────────────────────────────────────────────────────────
const US_REGIONS = [
  // NW corner
  { id: "PACNW", name: "Pacific NW", poly: "78,68 200,70 232,158 90,162 62,128 60,90" },
  { id: "CAL",   name: "California", poly: "90,162 232,158 222,278 138,288 110,290 84,260 72,212" },
  { id: "MTNW",  name: "Northern Plains", poly: "200,70 380,76 372,170 232,158" },
  { id: "MTNS",  name: "Mountain West", poly: "232,158 372,170 360,290 222,278" },
  { id: "SW",    name: "Southwest", poly: "222,278 360,290 320,372 148,372 138,288" },
  { id: "TX",    name: "Texas", poly: "320,372 480,388 466,418 408,432 348,408" },
  { id: "PLNS",  name: "Plains", poly: "380,76 540,82 528,212 372,170" },
  { id: "MWST",  name: "Midwest", poly: "540,82 668,90 654,202 660,232 528,212" },
  { id: "DEEP",  name: "Deep South", poly: "528,212 660,232 660,328 480,388 360,290 372,170" },
  { id: "SE",    name: "Southeast", poly: "660,328 766,318 780,358 738,372 692,388" },
  { id: "FL",    name: "Florida", poly: "738,372 798,372 822,398 836,442 802,438 770,408" },
  { id: "MIDATL",name: "Mid-Atlantic", poly: "660,232 770,222 800,272 766,318 660,328" },
  { id: "NE",    name: "Great Lakes", poly: "654,202 770,158 770,222 660,232 660,232" },
  { id: "NEAST", name: "New England", poly: "668,90 810,98 838,142 770,158 654,202 668,90" },
];

// ─────────────────────────────────────────────────────────────
// MAJOR CITY MARKERS — for context labels
// ─────────────────────────────────────────────────────────────
const CITIES = [
  { name: "Seattle",     x: 100, y: 100 },
  { name: "Portland",    x: 96,  y: 130 },
  { name: "Los Angeles", x: 130, y: 270 },
  { name: "Phoenix",     x: 220, y: 320 },
  { name: "Denver",      x: 320, y: 220 },
  { name: "Houston",     x: 430, y: 405 },
  { name: "New Orleans", x: 555, y: 395 },
  { name: "Atlanta",     x: 680, y: 340 },
  { name: "Miami",       x: 820, y: 422 },
  { name: "Detroit",     x: 678, y: 168 },
  { name: "Chicago",     x: 615, y: 192 },
  { name: "DC",          x: 780, y: 252 },
  { name: "New York",    x: 815, y: 178 },
  { name: "Boston",      x: 830, y: 142 },
  { name: "Minneapolis", x: 540, y: 130 },
];

// ─────────────────────────────────────────────────────────────
// HEX GRID — pointy-top, generated to cover continental US bbox.
// Only hexes whose centroid is inside any region polygon are kept.
// Each hex gets influence values, dominant faction, contested flag,
// habitability, heat, population, sovereign_id, label.
// ─────────────────────────────────────────────────────────────

const HEX_RADIUS = 17;
const HEX_W = Math.sqrt(3) * HEX_RADIUS;       // ~29.4
const HEX_H = 2 * HEX_RADIUS;                  // 34
const HEX_ROW_STEP = 0.75 * HEX_H;             // 25.5

function hexPoints(cx, cy, r = HEX_RADIUS) {
  const pts = [];
  for (let i = 0; i < 6; i++) {
    const a = Math.PI / 180 * (60 * i - 90); // pointy-top
    pts.push(`${(cx + r * Math.cos(a)).toFixed(2)},${(cy + r * Math.sin(a)).toFixed(2)}`);
  }
  return pts.join(" ");
}

function pointInPolygon(x, y, polyStr) {
  const pts = polyStr.split(" ").map(p => p.split(",").map(Number));
  let inside = false;
  for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
    const [xi, yi] = pts[i], [xj, yj] = pts[j];
    const intersect = ((yi > y) !== (yj > y)) &&
      (x < (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi);
    if (intersect) inside = !inside;
  }
  return inside;
}

function whichRegion(x, y) {
  for (const r of US_REGIONS) if (pointInPolygon(x, y, r.poly)) return r;
  return null;
}

// Deterministic PRNG so the map is stable across renders
function mulberry32(seed) {
  return function () {
    seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Per-region archetype: this seeds the influence distribution.
// Captures the political geography we want to MAKE LEGIBLE:
//   - The interior settler heartland is Restorationist-dominant (UPHOLD).
//   - Industrial belts + the West Coast urban core are Workers' Congress (IGNORE).
//   - Indigenous + Black Belt + decolonial pockets are Decolonial Front (ABOLISH).
// Numbers represent base influence (0-1) per faction, before noise.
const REGION_ARCHETYPE = {
  PACNW: { FAC_RESTORATIONIST: 0.30, FAC_WORKERS_CONGRESS: 0.42, FAC_DECOLONIAL: 0.28 },
  CAL:   { FAC_RESTORATIONIST: 0.18, FAC_WORKERS_CONGRESS: 0.48, FAC_DECOLONIAL: 0.34 },
  MTNW:  { FAC_RESTORATIONIST: 0.62, FAC_WORKERS_CONGRESS: 0.14, FAC_DECOLONIAL: 0.24 }, // strong indigenous presence
  MTNS:  { FAC_RESTORATIONIST: 0.55, FAC_WORKERS_CONGRESS: 0.16, FAC_DECOLONIAL: 0.29 },
  SW:    { FAC_RESTORATIONIST: 0.42, FAC_WORKERS_CONGRESS: 0.18, FAC_DECOLONIAL: 0.40 }, // Diné, Tohono O'odham, Pueblos
  TX:    { FAC_RESTORATIONIST: 0.58, FAC_WORKERS_CONGRESS: 0.22, FAC_DECOLONIAL: 0.20 },
  PLNS:  { FAC_RESTORATIONIST: 0.68, FAC_WORKERS_CONGRESS: 0.10, FAC_DECOLONIAL: 0.22 }, // settler heartland + Lakota/Dakota
  MWST:  { FAC_RESTORATIONIST: 0.38, FAC_WORKERS_CONGRESS: 0.46, FAC_DECOLONIAL: 0.16 }, // industrial union belt
  DEEP:  { FAC_RESTORATIONIST: 0.50, FAC_WORKERS_CONGRESS: 0.18, FAC_DECOLONIAL: 0.32 }, // Black Belt
  SE:    { FAC_RESTORATIONIST: 0.46, FAC_WORKERS_CONGRESS: 0.22, FAC_DECOLONIAL: 0.32 },
  FL:    { FAC_RESTORATIONIST: 0.54, FAC_WORKERS_CONGRESS: 0.20, FAC_DECOLONIAL: 0.26 },
  MIDATL:{ FAC_RESTORATIONIST: 0.34, FAC_WORKERS_CONGRESS: 0.40, FAC_DECOLONIAL: 0.26 },
  NE:    { FAC_RESTORATIONIST: 0.30, FAC_WORKERS_CONGRESS: 0.48, FAC_DECOLONIAL: 0.22 },
  NEAST: { FAC_RESTORATIONIST: 0.22, FAC_WORKERS_CONGRESS: 0.54, FAC_DECOLONIAL: 0.24 },
};

const rng = mulberry32(20251226); // epoch 3 start date as seed

// Helper: normalize influence triple to sum to 1
function normalize(inf) {
  const s = inf.FAC_RESTORATIONIST + inf.FAC_WORKERS_CONGRESS + inf.FAC_DECOLONIAL;
  return {
    FAC_RESTORATIONIST: inf.FAC_RESTORATIONIST / s,
    FAC_WORKERS_CONGRESS: inf.FAC_WORKERS_CONGRESS / s,
    FAC_DECOLONIAL: inf.FAC_DECOLONIAL / s,
  };
}

// Build the hex set
function buildHexes() {
  const hexes = [];
  const xmin = 40, xmax = 870, ymin = 50, ymax = 460;
  let id = 0;
  for (let row = 0; ; row++) {
    const cy = ymin + row * HEX_ROW_STEP;
    if (cy > ymax) break;
    const offset = (row % 2) ? HEX_W / 2 : 0;
    for (let col = 0; ; col++) {
      const cx = xmin + offset + col * HEX_W;
      if (cx > xmax) break;
      const region = whichRegion(cx, cy);
      if (!region) continue;
      const arch = REGION_ARCHETYPE[region.id];
      // Apply per-hex noise (mild) so the map has texture without flipping dominance often
      const noise = 0.18;
      const raw = {
        FAC_RESTORATIONIST: Math.max(0, arch.FAC_RESTORATIONIST + (rng() - 0.5) * noise * 2),
        FAC_WORKERS_CONGRESS: Math.max(0, arch.FAC_WORKERS_CONGRESS + (rng() - 0.5) * noise * 2),
        FAC_DECOLONIAL: Math.max(0, arch.FAC_DECOLONIAL + (rng() - 0.5) * noise * 2),
      };
      const inf = normalize(raw);
      // Determine dominant + contested
      const entries = Object.entries(inf).sort((a, b) => b[1] - a[1]);
      const dominant_faction_id = entries[0][0];
      const dominant_share = entries[0][1];
      const second_share = entries[1][1];
      const contested = (dominant_share - second_share) < 0.12 || dominant_share < 0.45;
      // Habitability inversely correlates with extraction → higher in ABOLISH zones
      const stance = FAC_BY_ID[dominant_faction_id].stance;
      const habBase = stance === "ABOLISH" ? 0.78 : stance === "IGNORE" ? 0.42 : 0.22;
      const habitability = Math.max(0.05, Math.min(0.95, habBase + (rng() - 0.5) * 0.18));
      // Heat: state attention. High in cities, high in contested zones, high in Decolonial strongholds.
      const heatBase = stance === "ABOLISH" ? 0.62 : stance === "UPHOLD" ? 0.28 : 0.40;
      const heat = Math.max(0.05, Math.min(0.95, heatBase + (rng() - 0.5) * 0.32 + (contested ? 0.18 : 0)));
      // Population: mostly low, spike near major cities
      const cityProx = Math.min(...CITIES.map(c => Math.hypot(c.x - cx, c.y - cy)));
      const population = Math.max(0.06, Math.min(1, 0.18 + Math.exp(-cityProx / 28) * 0.85));
      hexes.push({
        id: `H${String(id++).padStart(3, "0")}`,
        cx, cy, region_id: region.id, region_name: region.name,
        influences: inf,
        dominant_faction_id, dominant_share, second_share, contested,
        habitability, heat, population,
        // Sovereign assignment: clusters of hexes claimed by the dominant faction's sovereign.
        // Per spec, when a Sovereign collapses, sovereigns are recreated per winning faction.
        // We model post-collapse state: 3 emerging sovereigns + ungoverned contested zones.
        sovereign_id: contested ? null : `SOV_${dominant_faction_id.replace("FAC_", "")}`,
      });
    }
  }
  return hexes;
}

const HEXES = buildHexes();

// ─────────────────────────────────────────────────────────────
// SOVEREIGNS — 3 emerging, derived from controlled hex clusters
// ─────────────────────────────────────────────────────────────
const SOVEREIGNS = [
  {
    id: "SOV_RESTORATIONIST",
    name: "American Restorationist Authority",
    short_name: "A.R.A.",
    ruling_faction_id: "FAC_RESTORATIONIST",
    extraction_policy: "INTENSIFY",
    metabolic_impact: -0.02,
    legitimacy: 0.58,
    capital: "Dallas (de facto)",
    color: "#ff3344",
  },
  {
    id: "SOV_WORKERS_CONGRESS",
    name: "United Workers' Republic",
    short_name: "U.W.R.",
    ruling_faction_id: "FAC_WORKERS_CONGRESS",
    extraction_policy: "CONTINUE",
    metabolic_impact: -0.005,
    legitimacy: 0.47,
    capital: "Chicago",
    color: "#6b8fb5",
  },
  {
    id: "SOV_DECOLONIAL",
    name: "Coalition of Free Peoples",
    short_name: "C.F.P.",
    ruling_faction_id: "FAC_DECOLONIAL",
    extraction_policy: "CEASE",
    metabolic_impact: 0.01,
    legitimacy: 0.34,
    capital: "Diné Bikéyah (provisional)",
    color: "#5fbf7a",
  },
];
const SOV_BY_ID = Object.fromEntries(SOVEREIGNS.map(s => [s.id, s]));

// ─────────────────────────────────────────────────────────────
// SOVEREIGN BOUNDARY POLYGON — derived from controlled hex clusters
// Returns SVG polygon "x,y x,y …" for the convex(-ish) outline of each
// sovereign's claimed hexes. We do a simple alpha-shape approximation:
// for each sovereign, find the convex hull of its claimed hexes' centers.
// ─────────────────────────────────────────────────────────────
function convexHull(points) {
  if (points.length < 3) return points;
  const sorted = [...points].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const cross = (O, A, B) => (A[0] - O[0]) * (B[1] - O[1]) - (A[1] - O[1]) * (B[0] - O[0]);
  const lower = [];
  for (const p of sorted) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) lower.pop();
    lower.push(p);
  }
  const upper = [];
  for (let i = sorted.length - 1; i >= 0; i--) {
    const p = sorted[i];
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) upper.pop();
    upper.push(p);
  }
  return lower.slice(0, -1).concat(upper.slice(0, -1));
}

function sovereignClaimsPath(sovereignId) {
  const pts = HEXES.filter(h => h.sovereign_id === sovereignId).map(h => [h.cx, h.cy]);
  if (pts.length < 3) return null;
  const hull = convexHull(pts);
  return hull.map(p => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
}

// ─────────────────────────────────────────────────────────────
// COLLAPSE EVENTS — for variation 4
// ─────────────────────────────────────────────────────────────
const COLLAPSE_EVENTS = [
  { tick: 287, type: "SOVEREIGN_COLLAPSE",   sovereign: "United States Federal Government", target: null, severity: "critical", msg: "Federal Government legitimacy → 0.00. Sovereignty fractured." },
  { tick: 288, type: "TERRITORY_TRANSITION", sovereign: null, target: "Northern Plains",  severity: "critical", msg: "Northern Plains transitions: A.R.A. claims (influence 0.69)" },
  { tick: 288, type: "TERRITORY_TRANSITION", sovereign: null, target: "Mountain West",    severity: "critical", msg: "Mountain West contested: C.F.P. ↔ A.R.A. (Δ = 0.04)" },
  { tick: 289, type: "TERRITORY_TRANSITION", sovereign: null, target: "Midwest",          severity: "warning",  msg: "Midwest transitions: U.W.R. claims (influence 0.46)" },
  { tick: 289, type: "TERRITORY_TRANSITION", sovereign: null, target: "Southwest",        severity: "warning",  msg: "Southwest transitions: C.F.P. claims (influence 0.41)" },
  { tick: 290, type: "FACTION_VICTORY",      sovereign: null, target: "Workers' Congress",severity: "info",     msg: "Workers' Congress holds 7/14 macro-regions. False summit threshold reached." },
  { tick: 290, type: "WARN",                 sovereign: null, target: null,               severity: "warning",  msg: "Habitability: 0.42 → 0.395 (Δ −0.025). Metabolic rift accelerating." },
];

// ─────────────────────────────────────────────────────────────
// Exports
// ─────────────────────────────────────────────────────────────
Object.assign(window, {
  STANCE, FACTIONS, FAC_BY_ID,
  US_REGIONS, CITIES, HEXES,
  SOVEREIGNS, SOV_BY_ID,
  HEX_RADIUS, hexPoints, sovereignClaimsPath,
  COLLAPSE_EVENTS,
});
