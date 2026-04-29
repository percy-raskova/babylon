<!--
================================================================================
SYNC IMPACT REPORT
================================================================================
Version Change: 2.6.0 → 2.6.1
Bump Rationale: PATCH — agentic-AI consumption fixes. No new theoretical
  primitives or principle redefinitions. Fixes amendment registry
  inconsistency (F–J missing from IX.2), removes ghost article references,
  extracts III.4 tables to machine-readable YAML, adds cross-reference
  annotations, adds AI Decision Procedure (IX.3) and AI Context Budget
  (III.9) as clarifications for agentic consumption. Amendment C deadline
  deferred to v2.8.0.

Modified Principles:
  - I.16 — added See Also cross-reference to I.21 and V
  - I.18 — added See Also cross-reference to II.7 and VIII.9
  - I.21 — added See Also cross-reference to I.16 and II.5
  - II.3 — added See Also cross-reference to II.9 and VIII.9
  - II.5 — added See Also cross-reference to I.16 and I.21
  - II.7 — added See Also cross-reference to I.18 and VIII.9
  - III.4 — tables extracted to data-catalog.yaml; constitution now
    references canonical YAML file

Added Principles:
  - III.9 AI Context Budget (new)
    - P0 / P1 / P2 principle tiers for agent context windows
    - Mandatory retention rules per tier

Added Sections:
  - IX.3 AI Decision Procedure (new)
    - Read-and-Proceed, Read-and-Ask, Escalate, Transition-State
      escalation ladder for AI agents
  - IX.4 AI Context Budget Governance (new)
    - Session rules for P0/P1/P2 retention and escalation

Templates Requiring Updates:
  ✅ plan-template.md: No hardcoded principle numbers
  ✅ spec-template.md: No constitution references
  ✅ tasks-template.md: No constitution references
  ✅ checklist-template.md: No constitution references
  ✅ agent-file-template.md: No constitution references

Follow-up TODOs:
  - AMENDMENT B: Four-node partition invariance proof under
    morphism-preserving coarse-graining
  - AMENDMENT C: OODA profile placement spec (three candidate homes:
    PartyDialectic pole, morphism metadata, independent agent registry).
    Decision required before v2.8.0. **DEFERRED from v2.7.0.**
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

**17. OODA Loop as Organizational Metabolism** — Every organization/institution has an OODA profile (Observe-Orient-Decide-Act) determining action capacity per turn. Trade-offs: speed vs coherence, autonomy vs coordination, democracy vs reaction time. Decentralized orgs observe fast but orient slowly. Hierarchical institutions decide fast but observe poorly. The profile constrains which verbs are available and how many per tick. [TRANSITION STATE — Pending Amendment C: OODA profiles are constitutional but their v2 architectural placement is unresolved. Candidate homes: (a) pole attribute on PartyDialectic, (b) morphism metadata, (c) independent agent registry. A spec with invariance proof must be ratified before v2.7.0.]

**18. Material-Ideological Distinction** — Every dialectic has two dimensions: material basis (objective structural position, exists regardless of consciousness) and ideological dimension (whether actors conceive of collective interests opposed to hegemonic order). The GAP between material position and ideological consciousness is the terrain of political struggle. This is class-in-itself vs class-for-itself, generalized across all contradiction axes. [TRANSITION STATE — Pending Amendment D: v1 implementation expressed this on hyperedges. v2 reimplementation must preserve the distinction without violating the dyadic morphism constraint or Anti-Pattern VIII.9.] See Also: II.7 (dyadic morphism constraint), VIII.9 (anti-pattern preserving).

**19. Dialectic as Primitive** — The dialectic `D = (A, Ā, w, T, σ)` is the irreducible structural unit. `A` and `Ā` are typed poles; `w ∈ [-1, 1]` is the principal aspect weight; `T` is the motion operator (pure function `step`); `σ` is the sublation predicate. The ValueTensor4x3 is derived from dialectic structure, not primitive. All class partitions — including the {Core, Periphery} × {Bourgeoisie, Proletariat} schema — emerge from dialectic resolution patterns at specific scales. The engine enforces three universal invariants on every dialectic at every tick: weight ∈ [-1, 1], type stability across motion, and that `step` returns a Dialectic of the declared type.

**20. Spatial Substrate as Immutable Ground Truth, Political Claims as Overlay** — The H3 hex grid and federal county data are the immutable spatial substrate. Political claims — jurisdictions, contested territory, secession, autonomous zones — are overlays on this substrate, never mutations of it. The substrate preserves the empirical validation regime (QCEW/Census data maps to fixed geography). Political claims are first-class state: a hex or county can have multiple overlapping claims, zero claims, or claims that change without the substrate changing. The institutional layer and electoral mechanics operate on claims, not on substrate. Banned: substrate-mutating political operations (redrawing county lines, creating hexes, deleting territory).

**21. Sparrow Three-Targeting-Modes Framework** — State repression and player resistance both operate through three topological targeting modes: **centrality** (hubs and critical nodes — disrupt the network by removing its most connected elements), **singletons** (isolated targets — vulnerable because they lack solidarity edges, but also invisible because they lack network presence), and **cutsets** (bridges and bottlenecks — the minimal set of edges whose removal disconnects the graph). Repress sub-verbs (Surveil, Infiltrate, Raid, Prosecute, Liquidate) map to these modes: Surveil identifies singletons; Infiltrate targets cutsets; Raid hits centrality. Player verbs map to the inverse: Educate creates centrality; Aid strengthens cutsets; Attack exposes singletons. This is the topological grammar that gives both sides a combinatorial game to fight over. See Also: I.16 (Organizations are the agents that execute targeting-mode verbs), II.5 (AI narrates targeting outcomes via `observe()` projections).

## II. Architecture Principles

**1. Partition Emergence from Dialectic Structure** — The {Core, Periphery} × {Bourgeoisie, Proletariat} schema is a derived partition of the dialectic graph at a specific resolution, not a primitive fractal. It emerges when the dialectical field is coarse-grained along the imperial rent and class-contradiction axes. At finer resolutions, the same structure resolves into more specific contradictions. Amendment B MUST provide an invariance proof that the partition is recoverable under morphism-preserving coarse-graining without loss of predictive power.

**2. Primitives vs Derived** — Store: dialectic poles (typed frozen BaseModel), morphism graph (source, target, relation, weight), reproduction requirements. Compute: ValueTensor4x3, SNLT, value, c/v/s, Φ, r, s/v, OCC. NEVER store derived quantities. The Dialectic is primitive; the tensor is derived.

**3. NetworkX as Discretized Manifold** — Graph is the manifold. Tensors are field values. Connectivity determines information/value flow. [TRANSITION STATE — Pending Amendment D: In v2, the morphism graph is strictly dyadic (II.9). The NetworkX+XGI dual-graph commitment must be reconciled with this constraint without collapsing hyperedges into pairwise edges (Anti-Pattern VIII.9).] See Also: II.9 (strictly dyadic morphism layer), VIII.9 (anti-pattern preserving).

**4. Quantities vs Coefficients** — Quantities flux per tick. Coefficients α-smooth. Crisis = discontinuous coefficient reset, not gradual drift.

**5. AI Observes, Never Controls** — The AI is parser + narrator, never adjudicator. On the input path, the AI parses player prose into structured vectors (player intent → engine-compatible representation). On the output path, the AI narrates engine state into prose. In both directions the AI is a transformer of representation, not a source of truth. The engine adjudicates; the AI translates. AI failure is non-fatal: parsing fallback returns raw intent; narration fallback returns structured state. The AI layer consumes `observe()` projections, never invokes `step()` or mutates poles. See Also: I.16 (AI narrates org actions, never executes them), I.21 (targeting modes exposed through `observe()` if Org dialectic encodes them).

**6. State is Data, Engine is Transformation** — World: frozen Pydantic `World` model holding dialectics, morphisms, events. Engine: pure `tick(world, actions) → (new_world, events)`. The Embedded Trinity (SQLite Ledger, NetworkX Topology, ChromaDB Archive) provides persistence and serialization; the `World` is the single runtime structure for tick computation. No DB I/O during tick. Persistence access is constrained by II.11: no subsystem may read another subsystem's tables directly.

**7. Edges vs Hyperedges** — Dyadic flows between two entities → morphism graph (II.9). N-ary membership → XGI hyperedge. Two layers MUST remain separate. Hyperedge overlap = solidarity potential; morphism edge = actuality. Edges per tick; hyperedges α-smooth. [TRANSITION STATE — Pending Amendment D: The v2 morphism graph is strictly dyadic. Reconciliation required: either (a) hyperedges as higher-order structures with 1-skeleton in the morphism graph plus explicit consistency constraints, (b) simplicial representation, or (c) hyperedges migrate to pole structure. Anti-Pattern VIII.9 MUST be preserved.] See Also: I.18 (material-ideological distinction), VIII.9 (oppressor hyperedge).

**8. Client as Presentation Layer** — The browser is a viewport into server-computed state, not a participant in computation. The frontend receives game state via `observe()` projections as JSON, renders them, and emits player intents as JSON. It never runs simulation logic, never hydrates graphs, never resolves ticks. The `observe()` output is the durable contract; the frontend framework is disposable and replaceable without affecting the engine, the API, or the database. JSON is the interchange format at every system boundary.

**9. Morphism as Dyadic Relation** — Morphisms are strictly dyadic: source dialectic → target dialectic with typed relation and coupling weight. Five canonical relations: `feeds`, `constrains`, `transforms`, `contains`, `antagonizes`. No N-ary morphisms at this layer. The morphism graph is the wiring diagram for tick-level data flow. `feeds` determines `TickInputs` for `step()`.

**10. World as Runtime Single Structure** — At runtime, the World holds all dialectics, their morphism wiring, and per-tick events. This is the single structure for tick computation. Persistence (SQLite, ChromaDB) is a serialization concern, not a runtime partition. The Embedded Trinity is the durability layer; the World is the execution layer.

**11. Subsystem Table Ownership** — Each subsystem (consciousness, tensor, edge-mode state machine, dialectics, hex substrate, orgs) owns its persistence tables. Cross-subsystem reads MUST go through declared interfaces: SQL views with explicit contracts, RPC boundaries, or event streams. Direct table access from outside the owning subsystem is prohibited. If a monolithic deployment is chosen, the coupling must be explicitly documented per table with a federation migration plan. Unowned tables = undefined behavior. Epoch 3 federation requires this boundary discipline; its absence is a forward-blocking defect.

**12. Matrix Representation Layer** — NetworkX is the authoring API for graph construction and inspection. scipy.sparse is the computation layer for large-scale matrix operations. The actual mathematical structure is operator algebra on these matrices. The three-layer stack MUST remain separable: authoring → sparse matrix → operator expression. Never conflate NetworkX traversal with matrix computation, and never implement operator logic directly in NetworkX. The operator algebra is the source of truth; the other two are interfaces.

**13. Transport Substrate** — The movement of value, goods, and people is modeled as a transport substrate with two mechanisms: **min-cost flow** for deterministic routing (roads, rail, shipping lanes) and **slime-mold conductivity** for emergent routing (networks that optimize under pressure, like informal supply chains or migration routes). Transport edges have types: AIR_LINK (high speed, high visibility), SHIPPING_LANE (bulk, slow, regulated), ROAD (flexible, medium visibility), RAIL (capacity-constrained, infrastructure-dependent). The transport substrate is a Volume II/III mechanic: it mediates between production (Volume I) and realization (Volume III), and its topology determines where crises of disproportionality and realization propagate.

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

**7. Determinism Hash and Replayability** — Every tick MUST produce a deterministic hash of its inputs (World state + player actions + random seed if applicable). The same inputs MUST always produce the same outputs. This makes III.2 (Falsifiability Required) operational rather than aspirational: a prediction is a hash, and a falsifying observation is a hash mismatch. Replayability is not a feature — it is the mechanism by which falsifiability is enforced. The engine MUST support full replay from any tick given the initial state and action log. Non-determinism is a bug, not a design choice.

**8. Structural Provenance (Aleksandrov Test)** — Every formal construct — tensor, matrix, graph invariant, derived coefficient — MUST trace a chain of abstractions back to a material relation. This is a stricter version of III.1 (No Magic Constants) applied to formalism rather than scalars. The test: can you name the material process that this operator represents? If the chain breaks, the construct is invalid. Examples: the Laplacian represents diffusion of solidarity pressure; the adjacency matrix power represents multi-step exploitation chains; PageRank represents hierarchical command structure. Ungrounded operators are banned regardless of their mathematical elegance.

**9. AI Context Budget** — The constitution is consumed by AI agents with finite context windows. Principles are tiered by load-bearing status:

- **P0 (Never Drop)**: I.19 Dialectic Primitive, I.20 Spatial Substrate, II.9 Morphism Dyadic, III.7 Determinism Hash, III.8 Aleksandrov Test, V Verb Atomicity. These define the irreducible constraints of the system. An agent operating on any implementation task MUST retain these principles in context.

- **P1 (Load-Bearing)**: I.1 Settler-Colonial Frame, I.2 Imperial Rent, I.4 Bifurcation, I.6 Solidarity Edge Mode, I.7 Quantitative→Qualitative, I.12 Catastrophe Surface, I.16 Organization vs Institution, I.21 Sparrow, II.1 Partition Emergence, II.2 Primitives vs Derived, II.5 AI Scope, II.6 State is Data, II.11 Subsystem Ownership, II.12 Matrix Layer, II.13 Transport Substrate, III.1 No Magic Constants, III.2 Falsifiability, III.4 Data Catalog, III.6 Model Pinning, IV Michigan Test Case. These constrain specific domains. An agent MUST retain domain-relevant P1 principles for the file(s) it is editing.

- **P2 (Elaboration)**: I.3 TRPF, I.5 Department III, I.8 Tragedy of Inevitability, I.9 Metabolic Rift, I.10 Terminal Crisis, I.11 Emergent Pedagogy, I.13 Principal Contradiction, I.14 Contradiction Internals, I.15 Edge Mode Transitions, I.17 OODA, I.18 Material-Ideological, II.3 NetworkX Manifold, II.4 Quantities vs Coefficients, II.7 Edges vs Hyperedges, II.8 Client Layer, II.10 World Runtime, III.3 Physics Cosplay, III.5 Empirical vs Strategic, VI Scope Control, VII Visual Design, VIII Anti-Patterns, X Deployment. These provide context and guardrails but are not load-bearing for implementation. Agents MAY drop P2 principles when context-constrained, provided P0 and relevant P1 are retained.

An agent MUST report which tier it is operating from if it drops context.

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
2. **Zoom Where Data Exists** — Resolution matches data availability.
3. **Flag Scope Creep** — Must trace to Detroit prediction or improve falsifiability. Otherwise DEFER.

## VII. Visual Design Principles

1. **UI Observes, Never Controls** — Passive observer. Emits intents, never mutates state.
2. **Color as Data** — BLOOD_VOID, BLACK, CRIMSON (power), GOLD (action/solidarity), SILVER (mass), ASH (muted). Luminosity = magnitude. All via palette tokens.
3. **Data-Ink Maximization** — Every pixel encodes data or enables navigation. Small multiples over animation.
4. **Graph Is Primary** — Node position/size/density ARE data. Verbs over nouns. Topology visible.
5. **Signifier Legibility** — No hidden verbs. All interactive elements have visual affordance.
6. **Semantic Invariance** — Color meaning invariant across all views.
7. **Smallest Effective Difference** — Minimum visual distinction necessary.
8. **Feedback/Feedforward** — State changes confirmed visually. Preview consequences.
9. **Typography** — Monospace dominant. Max two typeface families.
10. **Prohibitions** — No decorative glow, hardcoded colors, chartjunk, hidden state, gratuitous animation, corner legends, context-dependent color, mood over meaning.

## VIII. Anti-Patterns

1. **Solidarity as Scalar** — Edge type transforms, not `+= x`.
2. **Union Density as Revolutionary** — US unions = labor aristocracy institutions.
3. **Determinism from Material Conditions** — Conditions constrain, not determine.
4. **Ungrounded Tensor Notation** — See III.3.
5. **Claims Without Falsifiability** — See III.2.
6. **Constants Without Data Sources** — See III.1, III.4.
7. **Superstructure Before Base** — See VI.1.
8. **Decorative Visualization** — See VII.10.
9. **Community as Pairwise Edge** — Community = XGI hyperedge, not combinatorial pairwise edges. See II.7.
10. **Oppressor Hyperedge for Institutional Exclusion** — Category 2 communities (DISABLED, QUEER, UNDOCUMENTED, INCARCERATED) have NO paired oppressor hyperedge. ABLED is absence of disability, not a political community. HETEROSEXUAL is unmarked default, not solidarity community. Contrast with Category 1 where BOTH sides exist (SETTLER has institutions, recruits, defends extraction). See II.7.

## IX. Governance

**1. Amendment Procedure** — Propose → demonstrate consistency → update artifacts → increment version.

**Versioning**: MAJOR (removal/redefinition of primitive or principle), MINOR (new principle/section or material expansion), PATCH (clarification, wording, non-semantic refinement).

**Compliance triggers**: New system, formula change, data source addition, scope expansion, UI implementation, infrastructure/deployment change, primitive redefinition.

**2. Staged Amendment Series** — When a primitive changes, downstream principles MUST be translated through a numbered amendment series with invariance proofs. Each amendment in the series must demonstrate that affected principles are at least as constrained as their predecessors. No amendment in the series may be skipped. The series is complete only when all downstream principles are either re-grounded or explicitly superseded.

**Amendment A — Dialectic Primitive** (ratified v2.0.0): Introduces `Dialectic[A, B]` as irreducible unit. Demotes Four-Node Recursive to derived partition. ValueTensor4x3 derived status.

**Amendment B — Partition Invariance** (pending): Four-node schema as derived partition. Requirement: invariance proof under morphism-preserving coarse-graining.

**Amendment C — OODA Placement** (pending): Architectural home for OODA profiles in v2. Requirement: spec with invariance proof before v2.7.0. **Deferred to v2.8.0** — no invariance proof ratified in this cycle.

**Amendment D — Hyperedge Reconciliation** (pending): NetworkX+XGI and strictly-dyadic morphism constraint. Requirement: spec preserving Anti-Pattern VIII.9.

**Amendment E — Michigan Statewide** (ratified v2.1.0): Expands canonical test case to 83 Michigan counties. Adds BEA EAs as aggregation tier. Detroit-Windsor boundary condition required. Tri-county preserved as acceptance criterion.

**Amendment F — Subsystem Table Ownership** (ratified v2.2.0): Each subsystem owns its persistence tables. Cross-subsystem reads via declared interfaces only (views, RPC, events). Direct table access prohibited. Federation boundary discipline.

**Amendment G — Spatial Substrate** (ratified v2.3.0): H3 hex grid and federal county data are immutable spatial substrate. Political claims are overlays, never mutations. Bans substrate-mutating political operations.

**Amendment H — Data Catalog Structure** (ratified v2.4.0): III.4 restructured from flat list to six-category catalog with provenance metadata. Fixture vs runtime distinction formalized.

**Amendment I — AI Parser Scope** (ratified v2.5.0): AI is parser + narrator, never adjudicator. Model pinning and parsed vector persistence required. Replayability across model deprecation.

**Amendment J — Determinism and Representation** (ratified v2.6.0): I.21 Sparrow targeting framework; II.12 matrix representation layer; II.13 transport substrate; III.7 determinism hash and replayability; III.8 structural provenance; V Investigate decomposed into three atomic sub-verbs.

Additional amendments will be registered as they are identified during downstream translation.

**3. AI Decision Procedure** — When an AI agent encounters ambiguity, it MUST follow this escalation ladder:

1. **Read and Proceed** — If the constitution provides an unambiguous constraint or prohibition that answers the question directly, the agent MUST apply it without asking for clarification. Examples: "Banned: infinite biocapacity" → reject any code producing it; "Every verb maps to a graph operation" → ensure `Investigate(Territory)` mutates the graph.

2. **Read and Ask** — If the constitution constrains the shape of the answer but not its content, the agent MUST consult the relevant spec before proceeding. Examples: II.13 defines transport edge types (AIR_LINK, SHIPPING_LANE, ROAD, RAIL) but does not define their cost functions → read the transport spec; I.21 defines three targeting modes but does not define the exact graph operation for Educate → read the verb spec.

3. **Escalate to Amendment** — If the question requires a choice between: adding a new primitive (new pole type, new morphism relation, new transport edge type not in II.13); redefining an existing primitive (changing the dialectic structure in I.19); relaxing a prohibition (allowing substrate mutation despite I.20); or introducing a formalism that fails the Aleksandrov Test (III.8) — then the agent MUST STOP and propose a constitutional amendment. It MUST NOT improvise a solution. The proposal MUST include: the problem, the proposed principle text, the principles it affects, and a draft invariance proof.

4. **Transition State Protocol** — If a principle is marked `[TRANSITION STATE]`, the agent MUST treat it as blocked. It MAY propose a spec to resolve the transition state, but it MUST NOT implement code that depends on the unresolved principle. Examples: II.7 (hyperedges) is transition state → do not implement hyperedge logic until Amendment D is ratified.

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

**5. Cloudflare Edge, Hetzner Compute** — Nothing computes on Cloudflare; nothing reaches users without Cloudflare first. Cloudflare handles DNS, SSL, DDoS, WAF, CDN, R2 storage, and Workers AI. Hetzner handles Django, Postgres, NetworkX, and CI/CD. Division of labor is strict — no function is shared between the two.

**6. Solo-Developer Constraint** — Every infrastructure component is filtered through: does this require a second full-time job to maintain? If yes, reject it. Kubernetes, Prometheus+Grafana, HashiCorp Vault, service meshes, and container orchestration are explicitly rejected until scale demands them.

______________________________________________________________________

**Version**: 2.6.1 | **Ratified**: 2026-01-30 | **Last Amended**: 2026-04-28
