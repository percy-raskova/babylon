# Specification Quality Checklist: Sovereign Topology + Faction Influence + Balkanization

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-05-17
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
  - The spec discusses domain concepts (entity names like `Sovereign`,
    `PoliticalFaction`; edge names like `CLAIMS`, `INFLUENCES`) and
    explicit code-reality references (where these will live in
    `src/babylon/`), but does not prescribe language features, ORM
    constructs, or API signatures. Code-reality references are
    grounded in observed file paths only, not invented APIs.
- [x] Focused on user value and business needs
  - User Stories 1–4 are framed around player-observable outcomes
    (habitability trajectories, faction competition, branching
    endgames, fracture mechanics). The Background and Theoretical
    Mandate sections explain *why* — the MLM-TW thesis that
    settler-colonialism is the load-bearing political axis.
- [x] Written for non-technical stakeholders
  - Theoretical Mandate, User Stories, and Endgame descriptions are
    in plain language. The Functional Requirements section uses
    enum / entity vocabulary that a stakeholder familiar with the
    project's theoretical framework will recognize from
    `ai-docs/epochs/epoch3/`.
- [x] All mandatory sections completed
  - User Scenarios & Testing (4 prioritized stories + Edge Cases),
    Requirements (46 FRs + Key Entities), Success Criteria (13 SCs)
    are all present. Optional sections (Background, Theoretical
    Mandate, Naming Disambiguation, Relationship to Existing
    GameOutcome, Assumptions, Out of Scope, Dependencies, Downstream
    Unblocks) are included where relevant.

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
  - No `[NEEDS CLARIFICATION]` markers were introduced; ambiguous
    choices (e.g., whether to add 4 new GameOutcome values vs
    extending the 3 existing ones) are explicitly framed as
    plan-phase decisions with success-criteria constraints
    (SC-001), not blocking clarifications.
- [x] Requirements are testable and unambiguous
  - Each FR is phrased in MUST / SHOULD / MAY terms. Enums (FR-002,
    FR-003, FR-006, FR-010, FR-011, FR-015) enumerate exact
    permitted values. Numeric thresholds (e.g., −0.02 / −0.005 /
    +0.01 metabolic_impact in FR-004; control_level=0.8 in FR-024;
    `control_level > 0.0` in FR-035) are explicit.
- [x] Success criteria are measurable
  - Each SC has either a counted observable (SC-002: "each of the
    four endgames is observed at least once across 100 runs"), a
    time bound (SC-003: "within 5 ticks"; SC-006: "within 10
    ticks"), a benchmark (SC-004: runtime flat across N ∈ {10, 100,
    1000}), or an equality (SC-011: "byte-identical sequences").
- [x] Success criteria are technology-agnostic (no implementation details)
  - SCs reference observable simulation behavior (endgames reached,
    events emitted, slope changes detectable). The one
    implementation-touching SC (SC-004: O(1) fracture cost) is
    phrased in terms of asymptotic-cost behavior, not specific
    graph-library calls.
- [x] All acceptance scenarios are defined
  - Each of US1–US4 has 3–7 Given/When/Then acceptance scenarios.
- [x] Edge cases are identified
  - 10 enumerated edge cases cover unclaimed territory, all-zero
    influence, orphaned Sovereign cleanup, concurrent collapse,
    endgame-already-fired, 100% secession, transient dual-power
    sum violations, Red Settler Trap, dissolved Sovereigns, and
    new mid-game Factions.
- [x] Scope is clearly bounded
  - "Out of Scope" section explicitly excludes ethnonational
    composition modeling, kinetic civil-war combat, faction-internal
    cohesion dynamics, faction action verbs, religious-institution
    field contribution, and higher-dimensional ideology manifolds —
    each with a pointer to the spec that owns that scope.
- [x] Dependencies and assumptions identified
  - Dependencies section lists spec-037, spec-061, spec-062,
    spec-066, spec-069, and ADR029 with REQUIRED / REFERENCE
    qualifiers. Assumptions section covers pipeline integration,
    GraphProtocol support, Detroit-tri-county MVP scope, proxy data
    availability, PostgreSQL bridge persistence, endgame detector
    extension, determinism preservation, multiplier overridability,
    tribal sovereignty schema-level support, greenfield-status, and
    FactionBalance-unrelated.

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
  - Every FR is either directly testable (enums, numeric thresholds,
    event emissions) or maps to one or more of the 13 SCs.
- [x] User scenarios cover primary flows
  - US1: extraction-policy-applies-to-territory (the smallest playable
    demo of the thesis).
    US2: factions-compete-and-install-sovereign (the political-
    competition layer).
    US3: collapse-triggers-branching-endgame (the strategic-stakes
    layer).
    US4: secession-as-O(1)-fracture (the mid-game-evolution layer).
- [x] Feature meets measurable outcomes defined in Success Criteria
  - Each US has a corresponding "Independent Test" that maps to one
    or more SCs. US1 → SC-003. US2 → SC-005, SC-008. US3 → SC-001,
    SC-002, SC-010, SC-012. US4 → SC-004, SC-009.
- [x] No implementation details leak into specification
  - The spec names existing files (e.g., `events.py`,
    `endgame_detector.py`) only to ground "extend this, don't
    create a parallel detector" guidance. It does not specify
    Python type signatures, SQL DDL, or NetworkX API calls. The
    System-position FRs (FR-041, FR-042) reference the spec-056
    partition assertion as a constraint the plan must honor, not as
    an implementation prescription.

## Code-Reality Verification

- [x] Greenfield entities confirmed
  - Verified at 2026-05-17 that `src/babylon/models/entities/` has
    no `sovereign.py` or political-coalition `faction.py`.
- [x] Edge-type additions confirmed greenfield
  - Verified that `src/babylon/models/enums/topology.py` `EdgeType`
    enum has no `CLAIMS` / `INFLUENCES` / `ADMINISTERS` values.
- [x] Naming-collision risk explicitly addressed
  - Existing `FactionBalance` + `StateFaction` (spec-039) are
    state-internal-factionalism, distinct from the
    political-coalition Faction in this spec. FR-045 mandates
    disambiguated naming.
- [x] GameOutcome existing-vs-new tension explicitly addressed
  - The "Relationship to Existing GameOutcome" section maps each of
    the four new pathways to the closest existing value and frames
    enum-extension-vs-sub-classification as a plan-phase decision.
- [x] Pipeline integration honors spec-056 partition assertion
  - FR-042 mandates classification into MATERIAL_BASE / ACTION_PHASE
    / CONSEQUENCE per spec-056's import-time assertion.

## Validation Result

- [x] All checklist items pass on first pass (no remediation iterations
  required). The spec is ready for `/speckit.clarify` (optional, since
  no ambiguities require user input) or directly for
  `/speckit.plan`.

## Notes

- Items marked incomplete require spec updates before `/speckit.clarify` or `/speckit.plan`.
- The spec deliberately leaves three plan-phase choices open rather
  than locking them in: (1) whether to add new `GameOutcome` enum
  values or extend existing ones (FR-030); (2) whether
  `FactionInfluenceSystem` belongs in ACTION_PHASE or CONSEQUENCE
  (FR-042); (3) the concrete schema for the chronicle/audit history
  layer (FR-046, audit table vs JSON column vs event stream).
- The user's project memory feedback ("No MVP scoping — full vision
  is the MVP") is honored: this spec covers the full Wave 1 scope
  (~140–180h per the audit estimate), not an MVP subset. The four
  User Stories are prioritized P1–P4 for risk/ordering purposes, not
  as a "ship P1 and defer the rest" plan.
