<!--
================================================================================
SYNC IMPACT REPORT
================================================================================
Version Change: 2.9.0 → 2.9.1 (2026-07-09, same evening)
Bump Rationale: PATCH — status-marker flip only: III.12 corollary (a)
  [PENDING CODE] → [IMPLEMENTED] (program 13 landed both items the same day:
  docs/reference/determinism-contract.rst with the hand-computation gate
  satisfied, and dense full-trace goldens for the 5 regression scenarios
  byte-compared in qa:regression with a double-generation determinism proof).
  No principle text changed.

--- prior report (v2.8.0 → 2.9.0) ---
Version Change: 2.8.0 → 2.9.0 (2026-07-09)
Bump Rationale: MINOR — Amendment Q (Behavioral Contracts / Durable Spec).
  New III.12: the system's observable behavior must be pinned in
  implementation-agnostic artifacts (checkpoint baselines, full-trace goldens,
  defines.yaml, seed data, the Postgres schema, observe()/HTTP contracts,
  written predicate specs) — the durable spec any reimplementation is
  validated against (the "rewrite test"); constitutional hashes require a
  language-agnostic canonical-serialization reference [PENDING CODE,
  program 13]; cross-implementation float validation is tolerance-bounded per
  III.7; verification stays redundant (replay + property + scenario +
  contract + mutation). New VIII.13 (Spec Trapped in Implementation). III.9
  P1 tier gains III.12. Prompted by the 2026-07-09 test-suite rewrite audit
  (project/assessments/TEST_SUITE_REWRITE_AUDIT-2026-07-09.md); doctrinal
  sources Fowler ("evaluations as behavioral contracts that outlive any
  particular implementation") and Majors ("code as a materialized view of
  understanding"). Owner-ratified 2026-07-09.

--- prior report (v2.7.0 → 2.8.0) ---
Version Change: 2.7.0 → 2.8.0 (2026-07-09)
Bump Rationale: MINOR — Amendments M (superseded), N (Spectrum of Unequal
  Exchange → I.2a), O (Transport Substrate extension → II.13), P (Loud Failure
  III.11 + VIII.12 + III.7 determinism honesty). Amendment C RESOLVED (OODA home
  = organization graph-node metadata). Article VII de-particularized (no
  constitutional palette / type stack / texture — supersedes the drafted M;
  aesthetics are a design-system concern). Factual drift fixed (II.6/II.10 →
  Postgres runtime + pgvector; SQLite = read-only fixture). Dialectic sublation
  glyph σ → s (I.19) to free σ for the I.2a spectrum coordinate. Governing
  document relocated: .specify/memory/constitution.md → repo-root CONSTITUTION.md
  (data-catalog.yaml likewise); the 10 stale constitution/article-*.md annex
  fragments retired (the monolith is the single source of truth).

--- prior report (v2.6.1 → 2.7.0) ---
Version Change: 2.6.1 → 2.7.0
Bump Rationale: MINOR — Amendments K and L registered in one cycle. K
  records the executable implementation of the dialectic primitive
  (Lawverian refactor, ADR051) and adds two principles (III.10
  Earn-Its-Keep, VIII.11 Tension-as-Accumulator anti-pattern). L rebinds
  the graph substrate implementation from NetworkX to rustworkx. No
  primitive is removed or redefined: II.3's manifold commitment is
  library-independent — only the implementation binding changes.
  Amendment C is RESOLVED in v2.8.0 (OODA home = organization graph-node metadata).

Modified Principles:
  - II.3 — retitled "Graph as Discretized Manifold"; implementation
    binding now rustworkx; [TRANSITION STATE — Amendment D] marker
    preserved with the dual-graph commitment renamed to rustworkx+XGI
  - II.6 — Embedded Trinity: "NetworkX Topology" → "rustworkx Topology";
    "ChromaDB Archive" → "pgvector Archive" (factual drift fix per
    spec-037, rider on Amendment L)
  - II.12 — rustworkx is the authoring API (three-layer stack unchanged)
  - III.9 — P2 tier label "II.3 NetworkX Manifold" → "II.3 Graph
    Manifold"; III.10 added to the P1 tier
  - X.5 — Hetzner compute list: NetworkX → rustworkx

Added Principles:
  - III.10 Earn-Its-Keep (Categorical Constructs) — a categorical
    construct ships only with a law, a prediction, or a running
    computation (Amendment K)
  - VIII.11 Tension as Accumulator — contradiction intensity is a fresh
    per-tick measured gap, never an add-only ratchet (Amendment K)

Added Sections:
  - IX.2 Amendment K — Lawverian Dialectics Implementation (ratified
    v2.7.0; source ai-docs/decisions/ADR051)
  - IX.2 Amendment L — Graph Substrate: NetworkX → rustworkx (ratified
    v2.7.0; implementation on branch refactor/networkx-to-rustworkx,
    ADR052 forthcoming)

Templates Requiring Updates:
  ✅ plan-template.md: No hardcoded principle numbers
  ✅ spec-template.md: No constitution references
  ✅ tasks-template.md: No constitution references
  ✅ checklist-template.md: No constitution references
  ✅ agent-file-template.md: No constitution references

Follow-up TODOs:
  - AMENDMENT B: Four-node partition invariance proof under
    morphism-preserving coarse-graining
  - AMENDMENT C: RESOLVED in v2.8.0 — OODA profile home ratified as
    organization graph-node metadata (`ooda_profile` on the org node),
    the shipped implementation. No longer blocks the amendment cycle.
  - CODE: Amendment L implementation (BabylonGraph substrate swap +
    ADR052) lands on branch refactor/networkx-to-rustworkx; constitution
    ratified ahead of code per IX.1 compliance triggers.
  - ANNEX: RETIRED in v2.8.0 — the constitution/article-*.md fragment files
    (which lagged the monolith) were deleted; this monolith is the single
    source of truth.
  - AMENDMENT D: Hyperedge reconciliation spec (preserve Anti-Pattern
    VIII.9 under strictly-dyadic morphism constraint)
  - CODE: Audit all Postgres schema definitions for subsystem table
    ownership violations. Document coupling where found.
  - CODE: Update AGENTS.md Embedded Trinity description to distinguish
    runtime World from persistence layer
  - SPEC: All specs referencing II.1 "Four-Node Recursive" must update
    to II.1 "Partition Emergence"
  - SPEC: Spec 038 (unified-class-system) references "fractal
    consistency" — update per Amendment B
  - SPEC: Spec 040 (michigan-statewide-scope) constitutional
    ratification complete; implementation can proceed
  - SPEC: New spec required for II.11 — subsystem boundary interface
    contracts (views, RPC, events) and table ownership registry
  - SPEC: New spec required for I.20 — political claim overlay model,
    claim-substrate composition rules, contested territory state machine
  - SPEC: New spec required for III.4 — data source ingestion pipeline
    per category, fixture pinning mechanism, provenance tracking schema

Previous Version History:
  2.6.1 (2026-04-28): PATCH — agentic-AI consumption fixes: amendment
    registry consistency (F–J), III.4 tables → data-catalog.yaml, III.9
    AI Context Budget, IX.3 AI Decision Procedure, cross-references
  2.6.0 (2026-04-28): Amendment J — Sparrow targeting, matrix layer,
    transport substrate, determinism hash, structural provenance,
    Investigate sub-verb decomposition
  2.5.0 (2026-04-28): Amendment I — AI parser scope expanded, model
    pinning, parsed vector persistence
  2.4.0 (2026-04-28): Amendment H — Structured data source catalog,
    provenance metadata, fixture vs runtime distinction
  2.3.0 (2026-04-28): Amendment G — Spatial substrate as immutable ground
    truth, political claims as overlay, unblocks institutional layer
  2.2.0 (2026-04-28): Amendment F — Subsystem table ownership,
    cross-subsystem interface discipline, Epoch 3 federation boundary
  2.1.0 (2026-04-28): Amendment E — Michigan statewide test case,
    Detroit-Windsor boundary condition, tri-county backward-compat
  2.0.0 (2026-04-28): Amendment A — Dialectic as primitive, staged
    amendment series framework, ValueTensor4x3 derived status
  1.10.1 (2026-04-14): Added USDA ERS CZs, BEA EAs, OMB CBSAs to III.4
  1.10.0 (2026-04-14): Added II.8 Client as Presentation Layer,
    X Deployment Infrastructure
  1.8.2 (2026-03-01): Added Natural Earth SQLite to III.4
  1.8.1 (2026-02-27): Added Chetty Opportunity Atlas to III.4
  1.8.0 (2026-02-26): Added I.16-I.18, expanded II.7, added VIII.10
  1.7.0 (2026-02-25): Added V. State AI Verbs
  1.6.1 (2026-02-25): Structural reorganization
  1.6.0 (2026-02-25): Added II.7 Edges vs Hyperedges, VIII.9
  1.5.0 (2026-02-24): Added I.12-I.15
  1.4.0 (2026-02-24): Added V. Player Action Vocabulary
  1.3.2 (2026-02-05): Added dispossession data sources to III.4
  1.3.1 (2026-02-05): Added PWT and Census Trade to III.4
  1.3.0 (2026-01-31): Added VIII. Visual Design Principles
  1.2.0 (2026-01-30): Added I.8-I.11, II.5-II.6
  1.1.0 (2026-01-30): Added I.7
  1.0.0 (2026-01-30): Initial ratification
================================================================================
-->

# Babylon Constitution

Governing document for the political simulation engine testing MLM-TW political economy against empirical data.

## I. Theoretical Commitments

**1. Settler-Colonial Frame** — Principal contradiction: imperialism vs oppressed nations, NOT capital vs labor.

**2. Imperial Rent (Φ)** — Φ = unequal exchange + externalized reproduction + domestic shadow labor. W_c > V_c → imperial rent. Explains core working class pacification.

**2a. Spectrum of Unequal Exchange (σ)** — `[RATIFIED · PENDING CODE]` Unequal exchange is not binary (core vs periphery) but a continuous gradient. Every production node carries a **spectrum coordinate σ** — its position on a single global unequal-exchange axis, computed from data only (organic composition of capital, capital intensity), never assigned. Target wages align to σ (`ŵ(σ)` monotone in σ, calibrated per sim-year from the wage cross-section); actual wages gravitate toward `ŵ(σ)` each tick, composing with — not replacing — reserve-army pressure; consciousness anti-correlates with σ (the labor aristocracy emerges at high σ). σ is a per-node scalar field; its edge gradient `σ(target) − σ(source)` is the measured direction of value transfer. This **refines, does not replace, I.2**: Φ's "unequal exchange" channel is the coarse-graining of the σ gradient — σ is **not** a fourth Φ channel (Φ remains I.2's three channels). This σ (spectrum coordinate) is distinct from the dialectic sublation predicate `s` (I.19). Owner-ratified 2026-07-08 (program 10 / spec-107). See Also: I.2 (Φ), III.4 (σ is data-computed).

**3. TRPF with Counter-Tendencies** — Model tendency AND counter-tendencies separately. Stable r MUST emerge from interaction, not be assumed.

**4. George Jackson Bifurcation** — Crisis → fascism (no solidarity edges) or revolution (solidarity across colonial divide). Warsaw Ghetto corollary: P(S|A) → 0 triggers revolt regardless of organization. Hegemony prevents this realization.

**5. Department III** — Reproduction tensor MUST include Dept III. g₃₃ → 0 (invisible). Rising visibility compresses profits independent of TRPF.

**6. Solidarity as Edge Mode** — Four modes: EXTRACTIVE, TRANSACTIONAL, SOLIDARISTIC, ANTAGONISTIC. Organizing transforms types, not weights. Qualitative, not scalar.

**7. Quantitative → Qualitative** — Quantities accumulate (resilience, pressure, crisis, consciousness). Qualities transform discretely (edge modes, class position, system phase). Thresholds explicit. No continuous quality gradients. Enums for qualities, floats for quantities.

**8. Tragedy of Inevitability** — Collapse is default. Player shapes character, not outcome. Existence costs calories (`base_subsistence > 0`). Earth remembers wounds. Death is real. Banned: infinite biocapacity, equilibrium stability, player "victory."

**9. Metabolic Rift** — ΔB = R - (E × η), η > 1.0. Overshoot O = C/B. Extraction permanently reduces max biocapacity. Independent collapse vector alongside TRPF.

**10. Terminal Crisis Arc** — Plantation → Prison → Camp → Death Camp. Each transition when previous stage unprofitable. Carceral turn responds to Φ exhaustion.

**11. Emergent Pedagogy** — All strategies playable. Consequences modeled, not punished. Theory follows experience. No hidden win conditions. Decolonial victory is emergent, not enforced.

**12. Catastrophe Surface** — Control parameters continuous (floats per tick). State variables discrete (enums at fold crossings). Catastrophe surface explicit per phase transition. I.7 is the what; I.12 is the geometry.

**13. Principal Contradiction** — One contradiction leads per tick. Selection: intensity × structural position. Shifts are discrete events. Primary dynamics full effect; secondary dampened.

**14. Contradiction Internals** — Aspect (dominant/subordinate — reversal is phase transition). Character (antagonistic/non-antagonistic, independent of edge mode). Trajectory (1st + 2nd derivatives per tick). Edges MUST be directed.

**15. Edge Mode Transitions** — State machine governs permissible transitions. Prohibited: EXTRACTIVE → SOLIDARISTIC (requires TRANSACTIONAL intermediate). Conditions reference contradiction internals. Topology versioned as constitutional amendment.

**16. Organization vs Institution** — Organization = voluntary coordination, can be destroyed. Institution = crystallized social relations, survives member turnover. Organizations become institutions through formalization. The player builds organizations; the state operates institutions. Destroying an organization kills it. Destroying an institution requires replacing the social relations it crystallizes. Organizations ARE the agents — they are the entities that take action via verbs. SocialClass, Territory, and Community are substrate, not agents. See Also: I.21 (verbs operate through orgs via targeting modes), V (atomic verb mapping to graph operations).

**17. OODA Loop as Organizational Metabolism** — Every organization/institution has an OODA profile (Observe-Orient-Decide-Act) determining action capacity per turn. Trade-offs: speed vs coherence, autonomy vs coordination, democracy vs reaction time. Decentralized orgs observe fast but orient slowly. Hierarchical institutions decide fast but observe poorly. The profile constrains which verbs are available and how many per tick. \[RATIFIED · IMPLEMENTED — Amendment C (v2.8.0): the OODA profile lives as **organization graph-node metadata** (the `ooda_profile` attribute on each org node, read at tick time by the OODASystem). The three v1 candidate homes (PartyDialectic pole, morphism metadata, independent agent registry) are superseded by the shipped implementation.\]

**18. Material-Ideological Distinction** — Every dialectic has two dimensions: material basis (objective structural position, exists regardless of consciousness) and ideological dimension (whether actors conceive of collective interests opposed to hegemonic order). The GAP between material position and ideological consciousness is the terrain of political struggle. This is class-in-itself vs class-for-itself, generalized across all contradiction axes. [TRANSITION STATE — Pending Amendment D: v1 implementation expressed this on hyperedges. v2 reimplementation must preserve the distinction without violating the dyadic morphism constraint or Anti-Pattern VIII.9.] See Also: II.7 (dyadic morphism constraint), VIII.9 (anti-pattern preserving).

**19. Dialectic as Primitive** — The dialectic `D = (A, Ā, w, T, s)` is the irreducible structural unit. `A` and `Ā` are typed poles; `w ∈ [-1, 1]` is the principal aspect weight; `T` is the motion operator (pure function `step`); `s` is the sublation predicate (written `σ` before v2.8.0; renamed to free the glyph σ for the I.2a spectrum coordinate — the code identifier is `sublation`, unaffected). The ValueTensor4x3 is derived from dialectic structure, not primitive. All class partitions — including the {Core, Periphery} × {Bourgeoisie, Proletariat} schema — emerge from dialectic resolution patterns at specific scales. The engine enforces three universal invariants on every dialectic at every tick: weight ∈ [-1, 1], type stability across motion, and that `step` returns a Dialectic of the declared type.

**20. Spatial Substrate as Immutable Ground Truth, Political Claims as Overlay** — The H3 hex grid and federal county data are the immutable spatial substrate. Political claims — jurisdictions, contested territory, secession, autonomous zones — are overlays on this substrate, never mutations of it. The substrate preserves the empirical validation regime (QCEW/Census data maps to fixed geography). Political claims are first-class state: a hex or county can have multiple overlapping claims, zero claims, or claims that change without the substrate changing. The institutional layer and electoral mechanics operate on claims, not on substrate. Banned: substrate-mutating political operations (redrawing county lines, creating hexes, deleting territory).

**21. Sparrow Three-Targeting-Modes Framework** — State repression and player resistance both operate through three topological targeting modes: **centrality** (hubs and critical nodes — disrupt the network by removing its most connected elements), **singletons** (isolated targets — vulnerable because they lack solidarity edges, but also invisible because they lack network presence), and **cutsets** (bridges and bottlenecks — the minimal set of edges whose removal disconnects the graph). Repress sub-verbs (Surveil, Infiltrate, Raid, Prosecute, Liquidate) map to these modes: Surveil identifies singletons; Infiltrate targets cutsets; Raid hits centrality. Player verbs map to the inverse: Educate creates centrality; Aid strengthens cutsets; Attack exposes singletons. This is the topological grammar that gives both sides a combinatorial game to fight over. `[RATIFIED · PENDING CODE — the three modes and the Repress sub-verbs exist in code (`ooda/attention/sparrow.py`, `StateActionType`), but the mode↔verb correspondence (Surveil→singleton, Infiltrate→cutset, Raid→centrality, and the player inverse) is not yet wired into the tick path.]` See Also: I.16 (Organizations are the agents that execute targeting-mode verbs), II.5 (AI narrates targeting outcomes via `observe()` projections).

## II. Architecture Principles

**1. Partition Emergence from Dialectic Structure** — The {Core, Periphery} × {Bourgeoisie, Proletariat} schema is a derived partition of the dialectic graph at a specific resolution, not a primitive fractal. It emerges when the dialectical field is coarse-grained along the imperial rent and class-contradiction axes. At finer resolutions, the same structure resolves into more specific contradictions. Amendment B MUST provide an invariance proof that the partition is recoverable under morphism-preserving coarse-graining without loss of predictive power.

**2. Primitives vs Derived** — Store: dialectic poles (typed frozen BaseModel), morphism graph (source, target, relation, weight), reproduction requirements. Compute: ValueTensor4x3, SNLT, value, c/v/s, Φ, r, s/v, OCC. NEVER store derived quantities. The Dialectic is primitive; the tensor is derived.

**3. Graph as Discretized Manifold** — Graph is the manifold. Tensors are field values. Connectivity determines information/value flow. Implementation binding: rustworkx (Amendment L; NetworkX retired). [TRANSITION STATE — Pending Amendment D: In v2, the morphism graph is strictly dyadic (II.9). The rustworkx+XGI dual-graph commitment must be reconciled with this constraint without collapsing hyperedges into pairwise edges (Anti-Pattern VIII.9).] See Also: II.9 (strictly dyadic morphism layer), VIII.9 (anti-pattern preserving).

**4. Quantities vs Coefficients** — Quantities flux per tick. Coefficients α-smooth. Crisis = discontinuous coefficient reset, not gradual drift.

**5. AI Observes, Never Controls** — The AI is parser + narrator, never adjudicator. On the input path, the AI parses player prose into structured vectors (player intent → engine-compatible representation). On the output path, the AI narrates engine state into prose. In both directions the AI is a transformer of representation, not a source of truth. The engine adjudicates; the AI translates. AI failure is non-fatal: parsing fallback returns raw intent; narration fallback returns structured state. The AI layer consumes `observe()` projections, never invokes `step()` or mutates poles. See Also: I.16 (AI narrates org actions, never executes them), I.21 (targeting modes exposed through `observe()` if Org dialectic encodes them).

**6. State is Data, Engine is Transformation** — World: frozen Pydantic `World` model holding dialectics, morphisms, events. Engine: pure `tick(world, actions) → (new_world, events)`. The Embedded Trinity (Postgres runtime Ledger, rustworkx Topology, pgvector Archive — with a read-only SQLite reference fixture as initialization input) provides persistence and serialization; the `World` is the single runtime structure for tick computation. No DB I/O during tick. Persistence access is constrained by II.11: no subsystem may read another subsystem's tables directly.

**7. Edges vs Hyperedges** — Dyadic flows between two entities → morphism graph (II.9). N-ary membership → XGI hyperedge. Two layers MUST remain separate. Hyperedge overlap = solidarity potential; morphism edge = actuality. Edges per tick; hyperedges α-smooth. [TRANSITION STATE — Pending Amendment D: The v2 morphism graph is strictly dyadic. Reconciliation required: either (a) hyperedges as higher-order structures with 1-skeleton in the morphism graph plus explicit consistency constraints, (b) simplicial representation, or (c) hyperedges migrate to pole structure. Anti-Pattern VIII.9 MUST be preserved.] See Also: I.18 (material-ideological distinction), VIII.9 (oppressor hyperedge).

**8. Client as Presentation Layer** — The browser is a viewport into server-computed state, not a participant in computation. The frontend receives game state via `observe()` projections as JSON, renders them, and emits player intents as JSON. It never runs simulation logic, never hydrates graphs, never resolves ticks. The `observe()` output is the durable contract; the frontend framework is disposable and replaceable without affecting the engine, the API, or the database. JSON is the interchange format at every system boundary.

**9. Morphism as Dyadic Relation** — Morphisms are strictly dyadic: source dialectic → target dialectic with typed relation and coupling weight. Five canonical relations: `feeds`, `constrains`, `transforms`, `contains`, `antagonizes`. No N-ary morphisms at this layer. The morphism graph is the wiring diagram for tick-level data flow. `feeds` determines `TickInputs` for `step()`.

**10. World as Runtime Single Structure** — At runtime, the World holds all dialectics, their morphism wiring, and per-tick events. This is the single structure for tick computation. Persistence (Postgres runtime + pgvector Archive; SQLite only as a read-only reference fixture) is a serialization concern, not a runtime partition. The Embedded Trinity is the durability layer; the World is the execution layer. (Runtime writes go to Postgres — the web DB on port 5432, the headless-runner DB on 5433; SQLite is `mode=ro` hydration input, never a runtime ledger; ChromaDB was replaced by pgvector in Feature 037.)

**11. Subsystem Table Ownership** — Each subsystem (consciousness, tensor, edge-mode state machine, dialectics, hex substrate, orgs) owns its persistence tables. Cross-subsystem reads MUST go through declared interfaces: SQL views with explicit contracts, RPC boundaries, or event streams. Direct table access from outside the owning subsystem is prohibited. If a monolithic deployment is chosen, the coupling must be explicitly documented per table with a federation migration plan. Unowned tables = undefined behavior. Epoch 3 federation requires this boundary discipline; its absence is a forward-blocking defect.

**12. Matrix Representation Layer** — rustworkx is the authoring API for graph construction and inspection. scipy.sparse is the computation layer for large-scale matrix operations. The actual mathematical structure is operator algebra on these matrices. The three-layer stack MUST remain separable: authoring → sparse matrix → operator expression. Never conflate rustworkx traversal with matrix computation, and never implement operator logic directly in rustworkx. The operator algebra is the source of truth; the other two are interfaces.

**13. Transport Substrate** — The movement of value, goods, and people is modeled as a transport substrate with two mechanisms: **min-cost flow** for deterministic routing `[RATIFIED · IMPLEMENTED]` (roads, rail, shipping lanes) and **slime-mold conductivity** for emergent routing `[RATIFIED · PENDING CODE]` (networks that optimize under pressure, like informal supply chains or migration routes). Transport edges have types: AIR_LINK (high speed, high visibility), SHIPPING_LANE (bulk, slow, regulated), the **road tier** (HIGHWAY / ARTERIAL / LOCAL_ROAD — flexible, medium visibility), RAIL (capacity-constrained, infrastructure-dependent), and **INFORMAL** (slime-mold-only routing, no built infrastructure). The transport substrate is a Volume II/III mechanic: it mediates between production (Volume I) and realization (Volume III), and its topology determines where crises of disproportionality and realization propagate. **Extension** `[RATIFIED · PENDING CODE]` (owner-ratified 2026-07-08): corridors are state-owned; edges carry a **condition** that **degrades** with use and neglect; agents **build and repair** them through the existing `BUILD_INFRASTRUCTURE` verb (no new verb); the implementing spec is not yet authored. See Also: V (BUILD_INFRASTRUCTURE), III.11 (a missing transport input fails loud, never silently no-ops).

## III. Methodological Constraints

**1. No Magic Constants** — Every number traces to primitives or data sources.

**2. Falsifiability Required** — Every formula defines: prediction, null hypothesis, distinguishing observable, falsifying data.

**3. Physics Cosplay Prohibition** — Tensor notation earns its keep through actual invariance. Reject formalism without transformation laws.

**4. Data Source Traceability** — All data sources are organized in a categorized catalog with provenance metadata. New sources require explicit constitutional addition with full provenance record. Two classes of data exist: runtime data sources (fetched/updated during operation) and validation fixtures (pinned snapshots used for reproducible tests). Fixture data is NEVER a runtime dependency.

**4.1 Catalog Reference** — The canonical machine-readable catalog is `data-catalog.yaml` in this directory. It defines six categories (Federal Economic, Federal Demographic, Federal Infrastructure, International Trade, Land Cover/Spatial, Legal/Judicial/Housing) with provenance metadata per source: `id`, `agency`, `dataset`, `vintage`, `granularity`, `cadence`, and `class` (Runtime or Fixture). New sources require explicit constitutional addition to both the YAML catalog and the amendment registry.

**4.2 Validation Fixture vs Runtime Data Source** — **Validation fixtures** are pinned snapshots of data used for reproducible test cases. They are versioned, hashed, and stored in the repository or artifact store. Fixtures are NEVER fetched at runtime and NEVER substituted for runtime data. Examples: assessor parcel snapshots for test counties, Natural Earth boundaries, Chetty Opportunity Atlas tract-level data.

**Runtime data sources** are fetched or updated during operation. They have live APIs, changing vintages, and require update pipelines. Runtime data MAY be cached but MUST be refreshable. Examples: QCEW wages, Census ACS estimates, FRED series, CDC WONDER mortality.

The distinction is load-bearing for reproducibility: a test using a fixture must produce the same result in 2026 as in 2028. A test using runtime data is an integration test against live infrastructure, not a reproducible validation.

**5. Empirical vs Strategic Separation** — Material conditions from data (nodes, constraints, extractive edges). Strategic intervention NOT from data (solidaristic edges, organizing, consciousness-raising).

**6. Model Pinning and Parsed Vector Persistence** — Every AI parsing operation MUST pin the model version (model identifier, weights version, tokenizer version). The parsed vector MUST be stored alongside the source prose. Replayability across model deprecation is a constitutional requirement, not an optimization: if the model is deprecated, the stored vector MUST remain sufficient to reproduce the engine state that the prose produced. No retroactive re-parsing with new models. A parsed vector without its model pin is undefined behavior.

**7. Determinism and Replayability** — Every tick MUST produce a deterministic SHA-256 hash of its inputs (World state + player actions + random seed). The same inputs MUST always produce the same outputs; non-determinism is a bug, not a design choice. The engine MUST support full replay from any tick given the initial state and action log — the per-tick hash is the **replay-integrity** mechanism (a replayed tick whose hash differs from the recorded one has diverged). **Falsifiability** (III.2) is enforced not by hash equality but by **tolerance-bounded value comparison** of recorded checkpoints (the `qa:regression` gate): a prediction is a checkpointed value, a falsifying observation is a value that drifts beyond tolerance. Distinguish two kinds of drift: **input-hash drift** — the `defines_hash` (the hash of the tunable coefficients) changed because a coefficient moved — is *expected and benign* (regenerate the baselines and say so); **behavioral drift** — a checkpoint value or an outcome changed — is *the bug the gate exists to catch*. Conflating the two (treating a benign defines change as a failure, or a behavioral change as a mere warning) defeats the gate.

**8. Structural Provenance (Aleksandrov Test)** — Every formal construct — tensor, matrix, graph invariant, derived coefficient — MUST trace a chain of abstractions back to a material relation. This is a stricter version of III.1 (No Magic Constants) applied to formalism rather than scalars. The test: can you name the material process that this operator represents? If the chain breaks, the construct is invalid. Examples: the Laplacian represents diffusion of solidarity pressure; the adjacency matrix power represents multi-step exploitation chains; PageRank represents hierarchical command structure. Ungrounded operators are banned regardless of their mathematical elegance.

**9. AI Context Budget** — The constitution is consumed by AI agents with finite context windows. Principles are tiered by load-bearing status:

- **P0 (Never Drop)**: I.19 Dialectic Primitive, I.20 Spatial Substrate, II.9 Morphism Dyadic, III.7 Determinism, III.8 Aleksandrov Test, III.11 Loud Failure, V Verb Atomicity. These define the irreducible constraints of the system. An agent operating on any implementation task MUST retain these principles in context.

- **P1 (Load-Bearing)**: I.1 Settler-Colonial Frame, I.2 Imperial Rent, I.2a Spectrum of Unequal Exchange, I.4 Bifurcation, I.6 Solidarity Edge Mode, I.7 Quantitative→Qualitative, I.12 Catastrophe Surface, I.16 Organization vs Institution, I.21 Sparrow, II.1 Partition Emergence, II.2 Primitives vs Derived, II.5 AI Scope, II.6 State is Data, II.11 Subsystem Ownership, II.12 Matrix Layer, II.13 Transport Substrate, III.1 No Magic Constants, III.2 Falsifiability, III.4 Data Catalog, III.6 Model Pinning, III.10 Earn-Its-Keep, III.12 Behavioral Contracts, IV Michigan Test Case. These constrain specific domains. An agent MUST retain domain-relevant P1 principles for the file(s) it is editing.

- **P2 (Elaboration)**: I.3 TRPF, I.5 Department III, I.8 Tragedy of Inevitability, I.9 Metabolic Rift, I.10 Terminal Crisis, I.11 Emergent Pedagogy, I.13 Principal Contradiction, I.14 Contradiction Internals, I.15 Edge Mode Transitions, I.17 OODA, I.18 Material-Ideological, II.3 Graph Manifold, II.4 Quantities vs Coefficients, II.7 Edges vs Hyperedges, II.8 Client Layer, II.10 World Runtime, III.3 Physics Cosplay, III.5 Empirical vs Strategic, VI Scope Control, VII Visual Design, VIII Anti-Patterns, X Deployment. These provide context and guardrails but are not load-bearing for implementation. Agents MAY drop P2 principles when context-constrained, provided P0 and relevant P1 are retained.

An agent MUST report which tier it is operating from if it drops context.

**10. Earn-Its-Keep (Categorical Constructs)** — A categorical construct (adjunction, cylinder, level lattice, functor, operator) ships only if it yields a LAW (a testable invariant), a PREDICTION (a falsifiable claim), or a COMPUTATION that runs in production — never as vocabulary. This is III.3 and III.8 applied to category theory: name the law, the prediction, or the running computation, or the construct is banned regardless of its elegance. (Amendment K; governing rule of the Lawverian dialectics refactor, ADR051.)

**11. Loud Failure (No Silent Degradation)** — A subsystem that cannot do its job MUST fail loud — raise, or emit an alarm-severity signal — never silently no-op, skip, or return a plausible default. Guardrails, gates, test markers, and canaries MUST be armed and enforced; a disarmed guard, an unregistered handler that silently drops work, or a system that early-returns when its required inputs are absent is a constitutional **defect**, not graceful degradation. This is the operational lesson of the "Loud Machine" remediation: systemic *silent* failures (no-op engine systems, disarmed strict-markers, skipped canaries, a case-mismatched node filter) are more dangerous than crashes because they pass every green check while producing wrong or empty results. The good pattern: an unregistered verb resolver raises rather than no-ops. The banned pattern: a system that silently no-ops when a context key is missing. See Also: VIII.12 (Silent No-Op anti-pattern), III.7 (determinism), III.2 (falsifiability).

**12. Behavioral Contracts (Durable Spec)** — The system's observable behavior MUST be pinned in implementation-agnostic artifacts: checkpoint baselines and full-trace goldens (`tests/baselines/`), the `defines.yaml` coefficient space, seed data, the Postgres schema, the `observe()`/HTTP contracts (II.8), and written predicate specs. These artifacts are the durable specification; any particular implementation — and its implementation-coupled tests (model shape, mock choreography) — is a disposable materialization that must be regenerable from them. The acceptance question is the **rewrite test**: could a reimplementation in another language be validated against the surviving artifacts alone? Three corollaries: **(a) Canonical serialization** — every constitutional hash (the III.7 tick hash, `defines_hash`, the `tick_commit` chain) MUST have its byte-level serialization specified in a language-agnostic reference document; a hash whose byte layout is defined only by the code that computes it is implementation-defined behavior. `[RATIFIED · IMPLEMENTED — docs/reference/determinism-contract.rst (program 13 item 1) + dense full-trace goldens byte-compared in qa:regression (item 2); program 13 complete 2026-07-09]` **(b) Float honesty** — byte-identical replay is guaranteed only within a single implementation and libm; cross-implementation validation is tolerance-bounded checkpoint comparison (III.7) with written tolerance derivations. **(c) Redundant verification** — behavior is verified by multiple independent strategies (replay baselines, property laws, scenario emergence, boundary contracts, mutation baselines); a single strategy has blind spots. Every new system boundary ships with a contract test and its behavioral artifact, not only unit tests. Implementation-coupled tests remain legitimate scaffolding but MUST NOT be the only home of load-bearing behavioral knowledge. See Also: III.7 (determinism and tolerance), III.2 (falsifiability), II.8 (client contract), VIII.13.

## IV. Test Case: Michigan Statewide (2010-2025)

The canonical test case is the State of Michigan, all 83 counties, 2010–2025. BEA Economic Areas (EAs) are the constitutional aggregation tier for regional analysis. The model MUST reproduce observed class transitions and inter-regional inequality using only QCEW/Census data + theoretical mechanisms. Failure = theory or implementation wrong.

### IV.1 Detroit-Windsor Boundary Condition

The Detroit-Windsor corridor is a required boundary condition, not an optional foreign node. Cross-border labor markets, trade flows, and imperial rent circuits (automotive supply chain, logistics, water rights) MUST be modeled. Canada is a first-class territorial substrate. The boundary itself is a contradiction surface: same labor, different citizenship regimes, different repression budgets.

### IV.2 Tri-County Backward-Compat Acceptance Criterion

The original Wayne County vs Oakland County tri-county sub-test (Crisis → Devaluation → Recolonization → Displacement) is preserved as a mandatory backward-compatibility acceptance criterion. Any statewide model MUST reproduce the tri-county results when coarse-grained to that resolution. Regression = implementation wrong.

## V. Action Vocabulary

### Player (9 verbs)

**Educate, Aid, Attack, Mobilize, Campaign, Move, Investigate, Reproduce, Negotiate**.

Player-facing (3x3): Build org | Project power | Manage resources. Engine-facing: Organization (node) | Population (org↔class edges) | Other actors (org↔org edges). Every verb maps to a graph operation. Atomic per target instance. All always available. Deterministic.

**Investigate Sub-Verbs** — Investigate has three target types, each a distinct sub-verb preserving atomicity:

- **Investigate(Territory)** — Reveals hidden substrate state (concealed exploitation, informal economy, unregistered claims). One territory node per tick.
- **Investigate(Org)** — Reveals org internals (cadre quality, funding sources, OODA profile). One org node per tick.
- **Investigate(Edge)** — Reveals edge properties (relation type, weight, history). One edge per tick.

Each sub-verb is atomic. The player selects the target type; the engine resolves the appropriate sub-verb.

### State AI (6 verbs)

**Administer** (Fund, Staff, Audit, Legislate) — reproduce state apparatus. **Develop** (Rezone, Invest, Eminent Domain, Tax Incentives) — reshape territory layer; asymmetric verb player lacks; gentrification as verb. **Research** — advance tech; products potentially seizable by player. **Co-opt** (Bribe, Propagandize, Incorporate, Divide) — absorb opposition or destroy relationships; Divide targets edges not nodes. **Repress** (Surveil, Infiltrate, Raid, Prosecute, Liquidate) — escalation ladder; each step costs more legitimacy. **Withdraw** (Strategic / Tactical / Scorched Earth) — concede, reposition, or deny territory; player must read which mode.

No separate state Negotiate verb — negotiation is a mode of Withdraw (terms of concession) or Co-opt (terms of absorption). Asymmetry is structural: state has fewer verbs but Develop operates on substrate player cannot directly modify.

## VI. Scope Control

1. **Material Base First** — Economic extraction → class formation → solidarity → THEN repression.
1. **Zoom Where Data Exists** — Resolution matches data availability.
1. **Flag Scope Creep** — Must trace to Detroit prediction or improve falsifiability. Otherwise DEFER.

## VII. Visual Design Principles

1. **UI Observes, Never Controls** — Passive observer. Emits intents, never mutates state.
1. **Color as Data** — Color encodes semantic meaning (a verb, not a vibe); luminosity encodes magnitude; every color is a named palette token, never hardcoded in a component. The **concrete palette is a design-system artifact, not constitutional** — the specific token set lives in the design system (e.g. `design/mockups/colors_and_type.css`) and may evolve without amendment, provided these principles hold. (This de-particularization supersedes the drafted Amendment M: with no constitutional palette, there is none to violate.)
1. **Data-Ink Maximization** — Every pixel encodes data or enables navigation. Small multiples over animation.
1. **Graph Is Primary** — Node position/size/density ARE data. Verbs over nouns. Topology visible.
1. **Signifier Legibility** — No hidden verbs. All interactive elements have visual affordance.
1. **Semantic Invariance** — Color meaning invariant across all views.
1. **Smallest Effective Difference** — Minimum visual distinction necessary.
1. **Feedback/Feedforward** — State changes confirmed visually. Preview consequences.
1. **Typography** — Monospace-dominant for data. Typography is disciplined by **function, not decoration**: each typeface family must serve one distinct role (data, chrome, display), and none may be introduced for ornament. The specific families are a design-system artifact, not constitutional.
1. **Prohibitions** — No decoration on data-encoding surfaces (no chartjunk, no ornament where color or luminance carries meaning), no hardcoded colors, no hidden state, no gratuitous animation, no context-dependent color, no mood over meaning. Diegetic chrome/texture on non-data surfaces is a design-system choice, not a constitutional matter.

## VIII. Anti-Patterns

1. **Solidarity as Scalar** — Edge type transforms, not `+= x`.
1. **Union Density as Revolutionary** — US unions = labor aristocracy institutions.
1. **Determinism from Material Conditions** — Conditions constrain, not determine.
1. **Ungrounded Tensor Notation** — See III.3.
1. **Claims Without Falsifiability** — See III.2.
1. **Constants Without Data Sources** — See III.1, III.4.
1. **Superstructure Before Base** — See VI.1.
1. **Decorative Visualization** — See VII.10.
1. **Community as Pairwise Edge** — Community = XGI hyperedge, not combinatorial pairwise edges. See II.7.
1. **Oppressor Hyperedge for Institutional Exclusion** — Category 2 communities (DISABLED, QUEER, UNDOCUMENTED, INCARCERATED) have NO paired oppressor hyperedge. ABLED is absence of disability, not a political community. HETEROSEXUAL is unmarked default, not solidarity community. Contrast with Category 1 where BOTH sides exist (SETTLER has institutions, recruits, defends extraction). See II.7.
1. **Tension as Accumulator** — Contradiction intensity MUST be a fresh per-tick measured gap (an adjunction defect per I.19), never an add-only `+=` ratchet. Saturating accumulators pin at their bound and carry no information (the pre-Amendment-K inertness bug: edge tension pinned at exactly 1.0 by ~t100). See III.10, Amendment K.
1. **Silent No-Op / Disarmed Guardrail** — A subsystem that skips its work when inputs are missing, a guardrail present but not enforced (a strict-marker set to no-op, a canary that always skips, an `ai`-marked test that selects zero tests), or a handler that silently drops unrecognized work. The failure passes every green check while producing wrong or empty state. See III.11 (Loud Failure).
1. **Spec Trapped in Implementation** — Load-bearing behavioral knowledge whose ONLY home is implementation-coupled: a mock call-sequence test, a model-shape assertion, a hash whose byte layout exists only in the code that computes it. The knowledge dies with the materialization it describes. If it matters, it belongs in a durable artifact — a baseline, a golden trace, a schema, a predicate spec, a property law. See III.12 (Behavioral Contracts).

## IX. Governance

**1. Amendment Procedure** — Propose → demonstrate consistency → update artifacts → increment version.

**Versioning**: MAJOR (removal/redefinition of primitive or principle), MINOR (new principle/section or material expansion), PATCH (clarification, wording, non-semantic refinement).

**Compliance triggers**: New system, formula change, data source addition, scope expansion, UI implementation, infrastructure/deployment change, primitive redefinition.

**2. Staged Amendment Series** — When a primitive changes, downstream principles MUST be translated through a numbered amendment series with invariance proofs. Each amendment in the series must demonstrate that affected principles are at least as constrained as their predecessors. No amendment in the series may be skipped. The series is complete only when all downstream principles are either re-grounded or explicitly superseded.

**Amendment A — Dialectic Primitive** (ratified v2.0.0): Introduces `Dialectic[A, B]` as irreducible unit. Demotes Four-Node Recursive to derived partition. ValueTensor4x3 derived status.

**Amendment B — Partition Invariance** (pending): Four-node schema as derived partition. Requirement: invariance proof under morphism-preserving coarse-graining.

**Amendment C — OODA Placement** (ratified v2.8.0): The OODA profile's architectural home is **organization graph-node metadata** (`ooda_profile` on the org node, read by the OODASystem at tick time) — the shipped implementation, ratified behind code. Supersedes the three v1 candidates (PartyDialectic pole, morphism metadata, agent registry). Resolves the item that formerly blocked v2.8.0.

**Amendment D — Hyperedge Reconciliation** (pending): rustworkx+XGI dual-graph commitment and strictly-dyadic morphism constraint (dual-graph binding renamed from NetworkX+XGI by Amendment L; the reconciliation requirement is unchanged). Requirement: spec preserving Anti-Pattern VIII.9.

**Amendment E — Michigan Statewide** (ratified v2.1.0): Expands canonical test case to 83 Michigan counties. Adds BEA EAs as aggregation tier. Detroit-Windsor boundary condition required. Tri-county preserved as acceptance criterion.

**Amendment F — Subsystem Table Ownership** (ratified v2.2.0): Each subsystem owns its persistence tables. Cross-subsystem reads via declared interfaces only (views, RPC, events). Direct table access prohibited. Federation boundary discipline.

**Amendment G — Spatial Substrate** (ratified v2.3.0): H3 hex grid and federal county data are immutable spatial substrate. Political claims are overlays, never mutations. Bans substrate-mutating political operations.

**Amendment H — Data Catalog Structure** (ratified v2.4.0): III.4 restructured from flat list to six-category catalog with provenance metadata. Fixture vs runtime distinction formalized.

**Amendment I — AI Parser Scope** (ratified v2.5.0): AI is parser + narrator, never adjudicator. Model pinning and parsed vector persistence required. Replayability across model deprecation.

**Amendment J — Determinism and Representation** (ratified v2.6.0): I.21 Sparrow targeting framework; II.12 matrix representation layer; II.13 transport substrate; III.7 determinism hash and replayability; III.8 structural provenance; V Investigate decomposed into three atomic sub-verbs.

**Amendment K — Lawverian Dialectics Implementation** (ratified v2.7.0): I.19's dialectic primitive is executable. OppositionRegistry of measured adjunction defects (gap, balance ∈ [-1, 1], rate — fresh per tick, never accumulated); principal contradiction ranked by gap × (1 + rate_weight × |rate|), implementing I.13. Adjunction instances: connectivity (atomization), scale (allocate ⊣ aggregate; H3 aggregation as sheaf), value-form (wage⇄value counit defect Φ). Level lattices (spatial hex < county < state < nation; social individual < community < class < bloc) with Aufhebung operator. Fixed-point regime classifier: reproduction / crisis / sublation — RUPTURE is the crisis regime's boiling point; EventType.LEVEL_TRANSITION is the production Aufhebung signal. Composition algebra (product/sum/nesting), typed coupling graph (feeds/constrains/transforms/contains/antagonizes), sublation lineage. Anti-Pattern VIII.9 n-ary protection preserved. Adds III.10 and VIII.11. Source: ADR051.

**Amendment L — Graph Substrate: NetworkX → rustworkx** (ratified v2.7.0): The manifold commitment (II.3) is library-independent; the implementation binding moves from NetworkX to rustworkx (Rust core) for runtime performance and memory behavior. II.3 retitled "Graph as Discretized Manifold"; II.6 Trinity updated (rustworkx Topology; pgvector Archive — ChromaDB drift fix per spec-037); II.12 authoring API; X.5 compute list. Determinism (III.7) MUST be preserved across the swap via insertion-ordered iteration surfaces; regression baselines regenerate only with written proof of an unavoidable order shift. Amendment D's pending reconciliation is unaffected: the dual-graph commitment becomes rustworkx+XGI.

**Amendment M — Cold Collapse Visual Canon** (superseded, not ratified): The drafted palette/typography/texture amendment (`specs/090-cold-collapse/article-vii-amendment.md`) is **superseded by de-particularization** (v2.8.0): Article VII no longer binds a concrete palette, type stack, or texture, so there is no constitutional palette for the Cold Collapse canon to conflict with. The concrete canon lives in the design system.

**Amendment N — Spectrum of Unequal Exchange** (ratified v2.8.0, `[PENDING CODE]`): Adds I.2a — the σ spectrum coordinate, a data-computed per-node position on a global unequal-exchange gradient; wages align to `ŵ(σ)`, consciousness anti-correlates. Refines I.2 without adding a fourth Φ channel. Frees the glyph σ by renaming the I.19 sublation predicate to `s`. Owner-ratified 2026-07-08 (program 10 / spec-107).

**Amendment O — Transport Substrate Extension** (ratified v2.8.0, `[PENDING CODE]`): Extends II.13 — state-owned corridors, an INFORMAL edge type, edge condition/degradation, and BUILD/REPAIR via the existing `BUILD_INFRASTRUCTURE` verb. Fixes the `ROAD` → road-tier (HIGHWAY/ARTERIAL/LOCAL_ROAD) naming. Owner-ratified 2026-07-08.

**Amendment P — Loud Failure and Determinism Honesty** (ratified v2.8.0): Adds III.11 (Loud Failure / No Silent Degradation) and VIII.12 (Silent No-Op anti-pattern); reconciles III.7 (the hash is replay-integrity; falsifiability is tolerance-bounded value comparison; input-hash drift ≠ behavioral drift). Corrects factual drift in II.6/II.10 (Postgres runtime + pgvector; SQLite = read-only fixture). The operational lesson of the Loud Machine remediation.

**Amendment Q — Behavioral Contracts / Durable Spec** (ratified v2.9.0; corollary (a) `[IMPLEMENTED]` as of v2.9.1 — program 13 delivered both work items the same day): Adds III.12 — behavior pinned in implementation-agnostic artifacts (the rewrite test), canonical hash-serialization requirement, float-tolerance honesty, redundant verification, contract-test-per-boundary — and VIII.13 (Spec Trapped in Implementation). Registers program 13 (`project/programs/13-behavioral-contracts.md`): the determinism-contract reference doc + dense full-trace goldens for the five regression scenarios. Doctrinal sources: Fowler (evaluations as behavioral contracts that outlive implementations; redundant verification layers) and Majors (code as a materialized view of understanding; AI demands more discipline). Prompted by the 2026-07-09 test-suite rewrite audit (`project/assessments/TEST_SUITE_REWRITE_AUDIT-2026-07-09.md`). Owner-ratified 2026-07-09.

Additional amendments will be registered as they are identified during downstream translation.

**3. AI Decision Procedure** — When an AI agent encounters ambiguity, it MUST follow this escalation ladder:

1. **Read and Proceed** — If the constitution provides an unambiguous constraint or prohibition that answers the question directly, the agent MUST apply it without asking for clarification. Examples: "Banned: infinite biocapacity" → reject any code producing it; "Every verb maps to a graph operation" → ensure `Investigate(Territory)` mutates the graph.

1. **Read and Ask** — If the constitution constrains the shape of the answer but not its content, the agent MUST consult the relevant spec before proceeding. Examples: II.13 defines transport edge types (AIR_LINK, SHIPPING_LANE, ROAD, RAIL) but does not define their cost functions → read the transport spec; I.21 defines three targeting modes but does not define the exact graph operation for Educate → read the verb spec.

1. **Escalate to Amendment** — If the question requires a choice between: adding a new primitive (new pole type, new morphism relation, new transport edge type not in II.13); redefining an existing primitive (changing the dialectic structure in I.19); relaxing a prohibition (allowing substrate mutation despite I.20); or introducing a formalism that fails the Aleksandrov Test (III.8) — then the agent MUST STOP and propose a constitutional amendment. It MUST NOT improvise a solution. The proposal MUST include: the problem, the proposed principle text, the principles it affects, and a draft invariance proof.

1. **Transition State Protocol** — If a principle is marked `[TRANSITION STATE]`, the agent MUST treat it as blocked. It MAY propose a spec to resolve the transition state, but it MUST NOT implement code that depends on the unresolved principle. Examples: II.7 (hyperedges) is transition state → do not implement hyperedge logic until Amendment D is ratified.

**4. AI Context Budget** — See III.9 for the canonical principle priority tiers. This section records governance rules for the budget:

- P0 principles are immutable across all agent sessions. No implementation task may proceed without them.
- P1 principles are domain-mandatory. An agent editing `engine/systems/territory.py` MUST retain II.13 and III.4; an agent editing `engine/systems/solidarity.py` MUST retain I.6 and I.21.
- P2 principles MAY be dropped when context-constrained, but the agent MUST report which P2 principles were dropped in its session summary.
- If an agent cannot fit P0 + relevant P1 into context, it MUST escalate — it MUST NOT drop P0 or P1 silently.

## X. Deployment Infrastructure

**1. Bare Metal, Ansible-Managed** — No Docker, no Nix, no containerization. Everything installs on the host OS via apt packages and is configured declaratively by Ansible playbooks. The entire server state is described in version-controlled roles. Nothing is installed by hand on the VPS.

**2. Terraform Provisions, cloud-init Bridges, Ansible Configures** — Terraform creates and destroys cloud resources (servers, firewalls, DNS records, object storage). cloud-init creates the deploy user on first boot — the only thing it does. Ansible configures everything after. These three tools have non-overlapping responsibilities.

**3. Postgres Bare Metal from PGDG** — PostgreSQL installs from the upstream PGDG apt repository directly on the host. Extensions (PostGIS, pgvector) install as apt packages. Ansible's `community.postgresql` collection manages database creation, roles, extensions, and pg_hba declaratively. Postgres listens on Unix socket only — never exposed to the network.

**4. systemd as Sole Supervisor** — All processes (Postgres, Gunicorn, Nginx, Woodpecker) run as systemd units. No additional supervisors. Service dependencies, restart policies, and cgroup resource limits are declared in unit files deployed by Ansible.

**5. Cloudflare Edge, Hetzner Compute** — Nothing computes on Cloudflare; nothing reaches users without Cloudflare first. Cloudflare handles DNS, SSL, DDoS, WAF, CDN, R2 storage, and Workers AI. Hetzner handles Django, Postgres, rustworkx, and CI/CD. Division of labor is strict — no function is shared between the two.

**6. Solo-Developer Constraint** — Every infrastructure component is filtered through: does this require a second full-time job to maintain? If yes, reject it. Kubernetes, Prometheus+Grafana, HashiCorp Vault, service meshes, and container orchestration are explicitly rejected until scale demands them.

______________________________________________________________________

**Version**: 2.9.1 | **Ratified**: 2026-01-30 | **Last Amended**: 2026-07-09
