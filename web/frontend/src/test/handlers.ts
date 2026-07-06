/**
 * MSW request handlers — stateful mock of the Django API endpoints and Babylon engine.
 */

import { http, HttpResponse } from "msw";
import {
  makeWayneCountySnapshot,
  makeAvailableAction,
  makeGameSummary,
  makeActionResult,
} from "./fixtures";
import { GameSnapshot, GameEvent } from "../types/game";
import orgsFixture from "../mocks/organizations.json";
import educateTargetsFixture from "../mocks/educate_targets.json";

// In-memory state machine for the mock game loop
let mockState: GameSnapshot = makeWayneCountySnapshot();
let queuedActions: { verb: string; targets?: string[] }[] = [];

// Spec 092: journal/alerts fixture — a mix of severities across ticks so
// the Event Log filter buttons and the Tick Resolution alert feed both
// have something real to render against.
//
// Spec-092 review fix (Defect D): types use the REAL engine's lowercase
// snake_case `EventType` casing (verified against
// `src/babylon/models/enums/events.py`), and severities match the
// backend's `_EVENT_SEVERITY` classification table
// (`web/game/engine_bridge.py`) rather than `lib/eventClassifier.ts`'s
// UPPERCASE-keyed map — EventLogPage/TickResolutionPage no longer consult
// that classifier (they read `event.severity` directly), so a green test
// suite against these fixtures now means something on real production data.
const mockJournalEvents: GameEvent[] = [
  {
    id: "journal-1",
    type: "uprising",
    tick: 5,
    severity: "critical",
    title: "Uprising",
    body: "Workers rose up in Hamtramck",
    data: { org_id: "ORG001" },
  },
  {
    id: "journal-2",
    type: "eviction_pipeline",
    tick: 4,
    severity: "warning",
    title: "Eviction Pipeline",
    body: "Eviction pipeline triggered against striking tenants in Dearborn",
    data: {},
  },
  {
    id: "journal-3",
    type: "wage_payment",
    tick: 3,
    severity: "informational",
    title: "Wage Payment",
    body: "Wages paid to proletariat",
    data: {},
  },
];

// Reset state function for testing
export const resetMockState = () => {
  mockState = makeWayneCountySnapshot();
  queuedActions = [];
};

// Spec 094: WireFeed fixture — a single uprising story with all 3 channels.
const mockWireFeed = {
  meta: {
    tick: 5,
    session: "wayne-county-001",
    operator: "RASKOVA-2",
    freq: "88.7 MHz",
    qth: "WAYNE CO / GRID EN82",
    classification: "TS//SI//NOFORN",
    cable_id: "0005-A",
    page_of: "001/001",
    timestamp_utc: "2026-05-12T08:47:22Z",
  },
  index: [
    {
      id: "journal-1",
      tick: 5,
      slug: "UPRISING \u00b7 HAMTRAMCK",
      hed: {
        c: "Authorities Report Civil Disturbance in Hamtramck",
        l: "WORKERS ROSE UP IN HAMTRAMCK // THE STREET HOLDS",
        i: "CIVIL DISTURBANCE // HAMTRAMCK // RESPONSE ACTIVE",
      },
      coverage: ["c", "l", "i"],
      severity: "critical",
    },
  ],
  euphemisms: {
    disturbance: {
      c: "civil disturbance",
      l: "UPRISING",
      filter: "ideology",
      note: "Framing a political act as a public-order issue erases the grievance.",
    },
    authorities: {
      c: "authorities",
      l: "COPS / PIGS",
      filter: "sourcing",
      note: "State spokesperson is sole source.",
    },
  },
  story: {
    id: "journal-1",
    tick: 5,
    location: "Hamtramck",
    time_local: "",
    continental: {
      brand: "CONTINENTAL",
      monogram: "C\u2022N",
      kicker: "NATIONAL \u00b7 LAW ENFORCEMENT",
      hed: "Authorities Report Civil Disturbance in Hamtramck",
      dek: "Law enforcement officials say a civil disturbance was brought under control.",
      byline: "By Continental Staff \u00b7 Updated 2h ago",
      paragraphs: [
        [
          "Hamtramck \u2014 ",
          { euph: "authorities", text: "authorities" },
          " responded to reports of a ",
          { euph: "disturbance", text: "civil disturbance" },
          " in the area early Tuesday.",
          { sup: 1 },
        ],
      ],
      bibliography: [
        {
          n: 1,
          src: "DHS Office of Public Affairs",
          kind: "press release",
          id: "DHS-OPA-001",
          chunk: "chunk_dhs_pr_001",
          sim: 0.91,
        },
      ],
    },
    liberated: {
      brand: "FREE SIGNAL",
      callsign: "WCLF-PIRATE-887",
      operator: "RASKOVA-2",
      hed: "WORKERS ROSE UP IN HAMTRAMCK // THE STREET HOLDS",
      pre: "[ BEGIN TRANSMISSION \u00b7 CIPHER: NONE \u00b7 BROADCAST IN THE CLEAR ]",
      post: "[ END TRANSMISSION \u00b7 TUNE NEXT HOUR \u00b7 WE HOLD THE LINE ]",
      paragraphs: [
        {
          body: [
            "THE STREET HELD IN HAMTRAMCK. WORKERS DROPPED THEIR TOOLS AND THE ",
            { euph: "authorities", text: "COPS / PIGS" },
            " SENT THE SHOCK TEAMS.",
          ],
          margin: {
            ref: "WITNESS-001",
            chunk: "chunk_wit_001",
            note: "front-line timestamp confirmed",
          },
        },
      ],
    },
    intel: {
      classification: "TS//SI//NOFORN",
      cable_id: "0005-A",
      origin: "FBI/HSI JOINT TASKFORCE \u2014 DETROIT FIELD OFFICE",
      routing: ["\u25ae\u25ae\u25ae\u25ae\u25ae\u25ae/CT", "DHS/I&A", "DOJ/NSD"],
      caveat: "HANDLE VIA COMINT CHANNELS ONLY",
      subj: "CIVIL DISTURBANCE \u00b7 HAMTRAMCK \u00b7 POST-ACTION",
      fields: [
        ["EVENT", "DISTURBANCE / DETAIN"],
        ["LOCATION", "Hamtramck"],
        ["DETAINEES", "8\u00d7 PROCESSED"],
        ["CONFIDENCE", "HIGH \u00b7 0.82"],
      ],
      assessment: ["Action timed to suppress labor coordination."],
      refs: [{ tag: "CHUNK", id: "chunk_sigint_001", sim: 0.95, src: "SIGINT capture" }],
      distribution: "\u25ae\u25ae\u25ae\u25ae\u25ae\u25ae \u00b7 NOFORN \u00b7 30D RETAIN",
    },
  },
  filters: [
    {
      id: "ownership",
      label: "Ownership",
      desc: "Continental is owned by a holding group with auto/defense exposure.",
      hits: 1,
      color: "var(--rent)",
    },
    {
      id: "advertising",
      label: "Advertising",
      desc: "Advertiser pressure shapes coverage of implicated industries.",
      hits: 0,
      color: "var(--heat)",
    },
    {
      id: "sourcing",
      label: "Sourcing",
      desc: "Named sources are state or state-adjacent.",
      hits: 2,
      color: "var(--cadre)",
    },
    {
      id: "flak",
      label: "Flak",
      desc: "Prior favorable coverage was retracted under pressure.",
      hits: 0,
      color: "var(--thermal)",
    },
    {
      id: "ideology",
      label: "Anti-radical ideology",
      desc: "The frame presupposes the legitimacy of the existing order.",
      hits: 2,
      color: "var(--laser)",
    },
  ],
};

export const handlers = [
  // Auth endpoints
  http.get("/accounts/whoami/", () =>
    HttpResponse.json({
      status: "ok",
      data: { is_authenticated: true, id: 1, username: "testuser" },
    }),
  ),

  http.post("/accounts/login/", () =>
    HttpResponse.json({
      status: "ok",
      data: { username: "testuser" },
    }),
  ),

  http.get("/accounts/login/", () =>
    HttpResponse.text("<html><body>login</body></html>", {
      headers: {
        "Content-Type": "text/html",
      },
    }),
  ),

  http.post("/accounts/logout/", () => HttpResponse.json({ status: "ok", data: null })),

  // Scenario catalog
  http.get("/api/scenarios/", () =>
    HttpResponse.json({
      status: "ok",
      data: [
        {
          key: "wayne_county",
          name: "Wayne County Organizer",
          description: "Organize in Wayne County, Michigan.",
          territory_count: 81,
        },
        {
          key: "us_nationwide",
          name: "United States — Nationwide",
          description: "Full CONUS simulation",
          territory_count: 1100,
        },
      ],
    }),
  ),

  // Game list
  http.get("/api/games/", () =>
    HttpResponse.json({
      status: "ok",
      data: [
        makeGameSummary({
          id: "wayne-county-001",
          scenario: "wayne_county",
          current_tick: mockState.tick,
          status: "active",
        }),
      ],
    }),
  ),

  // Create game
  http.post("/api/games/", () => {
    resetMockState(); // Reset for a new game
    return HttpResponse.json({
      status: "ok",
      data: { session_id: "wayne-county-001" },
    });
  }),

  // Game state
  http.get("/api/games/:id/state/", () =>
    HttpResponse.json({
      status: "ok",
      data: mockState,
    }),
  ),

  // Organizations
  http.get("/api/games/:id/organizations/", ({ request }) => {
    const url = new URL(request.url);
    const playerOnly = url.searchParams.get("player_only") === "true";
    let orgs = orgsFixture.organizations;
    if (playerOnly) {
      orgs = orgs.filter((o) => o.vanguard !== null && o.vanguard !== undefined);
    }
    return HttpResponse.json({
      status: "ok",
      data: { organizations: orgs },
    });
  }),

  // Available actions
  http.get("/api/games/:id/actions/available/", () =>
    HttpResponse.json({
      status: "ok",
      data: [
        makeAvailableAction({ verb: "educate", targets: ["C001", "C004"], cost: 0 }),
        makeAvailableAction({ verb: "attack", targets: ["C003"], cost: 0 }),
        makeAvailableAction({ verb: "mobilize", targets: ["C001"], cost: 0 }),
      ],
    }),
  ),

  // Educate Targets
  http.get("/api/games/:id/actions/educate/targets/", () =>
    HttpResponse.json(educateTargetsFixture),
  ),

  // Submit action — per-verb endpoints (Spec 040)
  http.post("/api/games/:id/actions/:verb/", async ({ params, request }) => {
    const data = (await request.json()) as Record<string, unknown>;
    const verb = params.verb as string;

    // Affordability Check Contract
    let canAfford = true;
    let reason = "";

    const playerOrg = mockState.organizations[0]; // Assuming Wayne County Player Org is first
    if (playerOrg && playerOrg.vanguard) {
      if (verb === "attack") {
        if (playerOrg.vanguard.cadre_labor < 2) {
          canAfford = false;
          reason = "Insufficient Cadre Labor (need 2)";
        }
      } else if (verb === "educate") {
        if (playerOrg.vanguard.budget < 50) {
          canAfford = false;
          reason = "Insufficient Budget (need $50)";
        }
      }
    }

    if (!canAfford) {
      return HttpResponse.json(
        {
          status: "error",
          message: reason,
        },
        { status: 400 },
      );
    }

    // Deduct cost and queue action
    if (playerOrg && playerOrg.vanguard) {
      if (verb === "attack") playerOrg.vanguard.cadre_labor -= 2;
      if (verb === "educate") playerOrg.vanguard.budget -= 50;
    }

    queuedActions.push({ verb, ...data });

    return HttpResponse.json({
      status: "ok",
      data: { id: queuedActions.length, status: "pending", verb },
    });
  }),

  // Resolve tick
  http.post("/api/games/:id/resolve/", () => {
    mockState.tick += 1;

    // Simulate Trap Escalation Contract
    if (mockState.traps) {
      const attackCount = queuedActions.filter((a) => a.verb === "attack").length;
      const educateCount = queuedActions.filter((a) => a.verb === "educate").length;

      if (attackCount > 0) {
        mockState.traps.ultra_left.score += 0.3 * attackCount;
        if (mockState.traps.ultra_left.score >= 0.5) {
          mockState.traps.ultra_left.severity = "moderate";
          mockState.traps.active_trap = "ultra_left";
        }
      }

      if (educateCount > 0) {
        mockState.traps.liberal.score += 0.3 * educateCount;
        if (mockState.traps.liberal.score >= 0.5) {
          mockState.traps.liberal.severity = "moderate";
          mockState.traps.active_trap = "liberal";
        }
      }
    }

    queuedActions = []; // Flush actions

    return HttpResponse.json({
      status: "ok",
      data: { resolved: true },
      tick: mockState.tick,
    });
  }),

  // Action results
  http.get("/api/games/:id/results/:tick/", () =>
    HttpResponse.json({
      status: "ok",
      data: [makeActionResult()],
    }),
  ),

  // Journal — full cross-tick event history (spec 092)
  http.get("/api/games/:id/journal/", () =>
    HttpResponse.json({
      status: "ok",
      data: { events: mockJournalEvents },
    }),
  ),

  // Alerts — critical/warning events from the latest tick (spec 092)
  http.get("/api/games/:id/alerts/", () =>
    HttpResponse.json({
      status: "ok",
      data: { alerts: mockJournalEvents.filter((e) => e.severity !== "informational") },
    }),
  ),

  // The Wire — WireFeed from DeterministicNarrator (spec 094)
  http.get("/api/games/:id/wire/", () =>
    HttpResponse.json({
      status: "ok",
      data: mockWireFeed,
    }),
  ),

  // Spec 095: Contradiction snapshot — the Dialectic screen feed
  http.get("/api/games/:id/contradiction/", () =>
    HttpResponse.json({
      status: "ok",
      data: {
        tick: 5,
        regime: "crisis",
        oppositions: [
          {
            key: "capital_labor",
            gap: 0.71,
            rate: 0.03,
            is_principal: true,
            leading_pole: "b",
          },
          {
            key: "imperial",
            gap: 0.42,
            rate: -0.01,
            is_principal: false,
            leading_pole: "a",
          },
        ],
        principal_key: "capital_labor",
        frame: {
          principal: {
            id: "capital_labor",
            aspect_a: "Labor",
            aspect_b: "Capital",
            principal_aspect: "b",
            intensity: 0.71,
            aspect_balance: 0.03,
            is_antagonistic: true,
          },
          secondary: {
            id: "imperial",
            aspect_a: "Core",
            aspect_b: "Periphery",
            principal_aspect: "a",
            intensity: 0.42,
            aspect_balance: -0.01,
            is_antagonistic: true,
          },
        },
      },
    }),
  ),

  // Spec 095: Endgame state — terminal outcome + chronicle stat cards
  http.get("/api/games/:id/endgame/", () =>
    HttpResponse.json({
      status: "ok",
      data: {
        tick: 5,
        outcome: null,
        headline: "",
        summary: "",
        stats: {
          final_tick: 5,
          consciousness: 0.42,
          solidarity_edges: 3,
          heat: 0.31,
        },
      },
    }),
  ),

  // Spec 095: Journal objectives — Vic3-style objectives tracker
  http.get("/api/games/:id/objectives/", () =>
    HttpResponse.json({
      status: "ok",
      data: {
        tick: 5,
        objectives: [
          {
            id: "revolution",
            title: "Revolutionary Victory",
            description:
              "Build mass class consciousness and solidarity edges to overthrow the empire.",
            progress: 0.42,
            status: "active",
            category: "revolution",
          },
          {
            id: "ecological_collapse",
            title: "Ecological Collapse",
            description: "Biocapacity depletion forces a terminal retreat from extraction.",
            progress: 0.31,
            status: "active",
            category: "collapse",
          },
          {
            id: "fascist_consolidation",
            title: "Fascist Consolidation",
            description: "False-consciousness bloc achieves a sovereign grip on the state.",
            progress: 0.71,
            status: "active",
            category: "fascist",
          },
          {
            id: "red_ogv",
            title: "Red OGV Trap",
            description:
              "Settler-socialist formation captures the movement without abolishing empire.",
            progress: 0.36,
            status: "active",
            category: "red_ogv",
          },
          {
            id: "fragmented_collapse",
            title: "Fragmented Collapse",
            description: "Balkanization — sovereign fragmentation outpaces solidarity.",
            progress: 0.22,
            status: "active",
            category: "fragmented",
          },
        ],
      },
    }),
  ),

  // Economy — per-territory economic summary (spec 093 US5)
  http.get("/api/games/:id/economy/", ({ request }) => {
    const url = new URL(request.url);
    const territoryId = url.searchParams.get("territory_id");
    if (!territoryId || territoryId === "unknown-territory") {
      return HttpResponse.json({
        status: "ok",
        data: {
          territory_id: territoryId,
          has_data: false,
          value_produced: 0,
          wage_share: null,
          rent_extracted: 0,
          exploitation_rate: null,
          extraction_intensity: 0,
        },
      });
    }
    return HttpResponse.json({
      status: "ok",
      data: {
        territory_id: territoryId,
        has_data: true,
        value_produced: 812.4,
        wage_share: null,
        rent_extracted: 118.9,
        exploitation_rate: 0.1464,
        extraction_intensity: 0.41,
      },
    });
  }),

  // Map snapshot — GeoJSON + balkanization metadata (spec 093 US3)
  http.get("/api/games/:id/map/", () =>
    HttpResponse.json({
      status: "ok",
      data: {
        type: "FeatureCollection",
        features: [],
        metadata: {
          balkanization: {
            factions: [
              { id: "FAC_A", colonial_stance: "uphold", is_settler_formation: true },
              { id: "FAC_B", colonial_stance: "ignore", is_settler_formation: true },
              { id: "FAC_C", colonial_stance: "abolish", is_settler_formation: false },
            ],
            sovereigns: [
              {
                id: "SOV_A",
                ruling_faction_id: "FAC_A",
                extraction_policy: "intensify",
                legitimacy: 0.58,
                claimed_territory_ids: ["t2", "t3"],
              },
            ],
            territory_influence: [
              {
                territory_id: "t1",
                influences: [
                  { faction_id: "FAC_A", influence_level: 0.47, support_type: "ideological" },
                  { faction_id: "FAC_B", influence_level: 0.41, support_type: "material" },
                ],
                dominant_faction_id: "FAC_A",
                current_sovereign_id: null,
                contested: true,
                habitability: 0.4,
              },
              {
                territory_id: "t2",
                influences: [
                  { faction_id: "FAC_A", influence_level: 0.71, support_type: "ideological" },
                ],
                dominant_faction_id: "FAC_A",
                current_sovereign_id: "SOV_A",
                contested: false,
                habitability: 0.9,
              },
            ],
          },
        },
      },
    }),
  ),

  // Spec 103: Trade flows — per-bloc price/flow lines for Wire INDEX
  http.get("/api/games/:id/trade-flows/", () =>
    HttpResponse.json({
      status: "ok",
      data: {
        tick: 5,
        has_data: true,
        blocs: [
          {
            node_id: "canada",
            label: "Canada",
            kind: "international",
            latest: {
              phi_year_inflow: 5200.0,
              bilateral_trade_value: 8_000_000,
              bilateral_trade_tons: 12_000,
              erdi_ratio: 1.18,
            },
            phi_series: [
              { tick: 1, magnitude: 100.0 },
              { tick: 2, magnitude: 105.0 },
              { tick: 3, magnitude: 98.0 },
            ],
            trade_series: [
              { tick: 1, magnitude: 50.0 },
              { tick: 2, magnitude: 55.0 },
            ],
          },
          {
            node_id: "china",
            label: "China",
            kind: "international",
            latest: {
              phi_year_inflow: 13_000.0,
              bilateral_trade_value: 20_000_000,
              bilateral_trade_tons: 30_000,
              erdi_ratio: 1.42,
            },
            phi_series: [
              { tick: 1, magnitude: 250.0 },
              { tick: 2, magnitude: 260.0 },
              { tick: 3, magnitude: 270.0 },
            ],
            trade_series: [],
          },
        ],
      },
    }),
  ),

  // Spec 103: County import-exposure provenance breakdown
  http.get("/api/games/:id/exposure/", ({ request }) => {
    const url = new URL(request.url);
    const countyFips = url.searchParams.get("county_fips");
    if (!countyFips || countyFips === "99999") {
      return HttpResponse.json({
        status: "ok",
        data: {
          county_fips: countyFips ?? "",
          has_data: false,
          total_exposure: 0,
          breakdown: { total: 0, contributors: [] },
          citations: [],
        },
      });
    }
    return HttpResponse.json({
      status: "ok",
      data: {
        county_fips: countyFips,
        has_data: true,
        total_exposure: 189.2,
        breakdown: {
          total: 189.2,
          contributors: [
            {
              label: "Canada",
              value: 60.8,
              share: 0.32,
              source: { kind: "derived", path: `exposure[${countyFips}][canada]` },
              children: [
                {
                  label: "spec-100 exposure weight",
                  value: 0.32,
                  share: 1.0,
                  source: {
                    kind: "reference_table",
                    path: `county_exposure_by_external[canada][${countyFips}]`,
                  },
                  children: [],
                },
                {
                  label: "live flow (drain_edge)",
                  value: 190.0,
                  share: 1.0,
                  source: {
                    kind: "dynamic_table",
                    path: `boundary_flow_register[canada→${countyFips}]`,
                  },
                  children: [],
                },
              ],
            },
            {
              label: "China",
              value: 128.4,
              share: 0.68,
              source: { kind: "derived", path: `exposure[${countyFips}][china]` },
              children: [
                {
                  label: "spec-100 exposure weight",
                  value: 0.55,
                  share: 1.0,
                  source: {
                    kind: "reference_table",
                    path: `county_exposure_by_external[china][${countyFips}]`,
                  },
                  children: [],
                },
                {
                  label: "live flow (drain_edge)",
                  value: 233.5,
                  share: 1.0,
                  source: {
                    kind: "dynamic_table",
                    path: `boundary_flow_register[china→${countyFips}]`,
                  },
                  children: [],
                },
              ],
            },
          ],
        },
        citations: [
          {
            id: "bea-io-2023",
            source: "BEA I-O imports",
            table: "fact_bea_io_coefficient",
            year: 2023,
            notes: "Import coefficients per industry.",
          },
          {
            id: "qcew-2023q2",
            source: "QCEW county industry shares",
            table: "fact_qcew",
            year: "2023Q2",
            notes: "County-level industry employment shares.",
          },
          {
            id: "hickel-drain",
            source: "Hickel drain",
            table: "immutable_reference_hickel_drain",
            notes: "Annual Φ inflow per external bloc.",
          },
        ],
      },
    });
  }),

  // Spec 103: Trade panel — aggregate trade panel for Analysis page
  http.get("/api/games/:id/trade-panel/", () =>
    HttpResponse.json({
      status: "ok",
      data: {
        tick: 5,
        has_data: true,
        total_phi_inflow: 715.0,
        total_trade: 105.0,
        blocs: [
          {
            node_id: "canada",
            label: "Canada",
            phi_inflow: 205.0,
            trade: 105.0,
            erdi_ratio: 1.18,
          },
          {
            node_id: "china",
            label: "China",
            phi_inflow: 510.0,
            trade: 0.0,
            erdi_ratio: 1.42,
          },
        ],
        flow_types: [
          { flow_type: "drain_edge", total: 715.0, tick_count: 2 },
          { flow_type: "trade_inbound", total: 105.0, tick_count: 2 },
        ],
      },
    }),
  ),
];
