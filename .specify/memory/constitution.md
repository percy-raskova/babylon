<!--
================================================================================
SYNC IMPACT REPORT
================================================================================
Version Change: 2.0.0 → 2.1.0
Bump Rationale: MINOR — material expansion of Article IV test case scope.
  Ratifies Detroit→Michigan statewide expansion (83 counties, BEA EAs as
  aggregation tier) and Detroit-Windsor cross-border boundary condition.
  Tri-county Detroit sub-test preserved as backward-compat acceptance
  criterion. No primitive redefinitions.

Modified Principles:
  - IV. Test Case: Metro Detroit (2010-2025) → IV. Test Case: Michigan
    Statewide (2010-2025)
    - Expanded from Wayne/Oakland counties to all 83 Michigan counties
    - Added BEA Economic Areas as constitutional aggregation tier
    - Added Detroit-Windsor boundary condition (Canada required)
    - Tri-county Detroit preserved as backward-compat acceptance criterion

Added Principles: None

Added Sections: None

Removed Sections: None

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
    Decision required before v2.2.0.
  - AMENDMENT D: Hyperedge reconciliation spec (preserve Anti-Pattern
    VIII.9 under strictly-dyadic morphism constraint)
  - CODE: Update AGENTS.md Embedded Trinity description to distinguish
    runtime World from persistence layer
  - SPEC: All specs referencing II.1 "Four-Node Recursive" must update
    to II.1 "Partition Emergence"
  - SPEC: Spec 038 (unified-class-system) references "fractal
    consistency" — update per Amendment B
  - SPEC: Spec 040 (michigan-statewide-scope) constitutional
    ratification complete; implementation can proceed

Previous Version History:
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

Governing document for the political simulation engine testing MLM-TW political economy against empirical data. Full rationale, examples, and historical context for each article in `constitution/`.

## I. Theoretical Commitments

> Full article: `constitution/article-i-theory.md`

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

**16. Organization vs Institution** — Organization = voluntary coordination, can be destroyed. Institution = crystallized social relations, survives member turnover. Organizations become institutions through formalization. The player builds organizations; the state operates institutions. Destroying an organization kills it. Destroying an institution requires replacing the social relations it crystallizes. Organizations ARE the agents — they are the entities that take action via verbs. SocialClass, Territory, and Community are substrate, not agents.

**17. OODA Loop as Organizational Metabolism** — Every organization/institution has an OODA profile (Observe-Orient-Decide-Act) determining action capacity per turn. Trade-offs: speed vs coherence, autonomy vs coordination, democracy vs reaction time. Decentralized orgs observe fast but orient slowly. Hierarchical institutions decide fast but observe poorly. The profile constrains which verbs are available and how many per tick. [TRANSITION STATE — Pending Amendment C: OODA profiles are constitutional but their v2 architectural placement is unresolved. Candidate homes: (a) pole attribute on PartyDialectic, (b) morphism metadata, (c) independent agent registry. A spec with invariance proof must be ratified before v2.2.0.]

**18. Material-Ideological Distinction** — Every dialectic has two dimensions: material basis (objective structural position, exists regardless of consciousness) and ideological dimension (whether actors conceive of collective interests opposed to hegemonic order). The GAP between material position and ideological consciousness is the terrain of political struggle. This is class-in-itself vs class-for-itself, generalized across all contradiction axes. [TRANSITION STATE — Pending Amendment D: v1 implementation expressed this on hyperedges. v2 reimplementation must preserve the distinction without violating the dyadic morphism constraint or Anti-Pattern VIII.9.]

**19. Dialectic as Primitive** — The dialectic `D = (A, Ā, w, T, σ)` is the irreducible structural unit. `A` and `Ā` are typed poles; `w ∈ [-1, 1]` is the principal aspect weight; `T` is the motion operator (pure function `step`); `σ` is the sublation predicate. The ValueTensor4x3 is derived from dialectic structure, not primitive. All class partitions — including the {Core, Periphery} × {Bourgeoisie, Proletariat} schema — emerge from dialectic resolution patterns at specific scales. The engine enforces three universal invariants on every dialectic at every tick: weight ∈ [-1, 1], type stability across motion, and that `step` returns a Dialectic of the declared type.

## II. Architecture Principles

> Full article: `constitution/article-ii-architecture.md`

**1. Partition Emergence from Dialectic Structure** — The {Core, Periphery} × {Bourgeoisie, Proletariat} schema is a derived partition of the dialectic graph at a specific resolution, not a primitive fractal. It emerges when the dialectical field is coarse-grained along the imperial rent and class-contradiction axes. At finer resolutions, the same structure resolves into more specific contradictions. Amendment B MUST provide an invariance proof that the partition is recoverable under morphism-preserving coarse-graining without loss of predictive power.

**2. Primitives vs Derived** — Store: dialectic poles (typed frozen BaseModel), morphism graph (source, target, relation, weight), reproduction requirements. Compute: ValueTensor4x3, SNLT, value, c/v/s, Φ, r, s/v, OCC. NEVER store derived quantities. The Dialectic is primitive; the tensor is derived.

**3. NetworkX as Discretized Manifold** — Graph is the manifold. Tensors are field values. Connectivity determines information/value flow. [TRANSITION STATE — Pending Amendment D: In v2, the morphism graph is strictly dyadic (II.9). The NetworkX+XGI dual-graph commitment must be reconciled with this constraint without collapsing hyperedges into pairwise edges (Anti-Pattern VIII.9).]

**4. Quantities vs Coefficients** — Quantities flux per tick. Coefficients α-smooth. Crisis = discontinuous coefficient reset, not gradual drift.

**5. AI Observes, Never Controls** — State calculated then narrated. AI read-only. Reproducibility paramount. AI failure non-fatal. The AI layer consumes `observe()` projections, never invokes `step()` or mutates poles.

**6. State is Data, Engine is Transformation** — World: frozen Pydantic `World` model holding dialectics, morphisms, events. Engine: pure `tick(world, actions) → (new_world, events)`. The Embedded Trinity (SQLite Ledger, NetworkX Topology, ChromaDB Archive) provides persistence and serialization; the `World` is the single runtime structure for tick computation. No DB I/O during tick.

**7. Edges vs Hyperedges** — Dyadic flows between two entities → morphism graph (II.9). N-ary membership → XGI hyperedge. Two layers MUST remain separate. Hyperedge overlap = solidarity potential; morphism edge = actuality. Edges per tick; hyperedges α-smooth. [TRANSITION STATE — Pending Amendment D: The v2 morphism graph is strictly dyadic. Reconciliation required: either (a) hyperedges as higher-order structures with 1-skeleton in the morphism graph plus explicit consistency constraints, (b) simplicial representation, or (c) hyperedges migrate to pole structure. Anti-Pattern VIII.9 MUST be preserved.]

**8. Client as Presentation Layer** — The browser is a viewport into server-computed state, not a participant in computation. The frontend receives game state via `observe()` projections as JSON, renders them, and emits player intents as JSON. It never runs simulation logic, never hydrates graphs, never resolves ticks. The `observe()` output is the durable contract; the frontend framework is disposable and replaceable without affecting the engine, the API, or the database. JSON is the interchange format at every system boundary.

**9. Morphism as Dyadic Relation** — Morphisms are strictly dyadic: source dialectic → target dialectic with typed relation and coupling weight. Five canonical relations: `feeds`, `constrains`, `transforms`, `contains`, `antagonizes`. No N-ary morphisms at this layer. The morphism graph is the wiring diagram for tick-level data flow. `feeds` determines `TickInputs` for `step()`.

**10. World as Runtime Single Structure** — At runtime, the World holds all dialectics, their morphism wiring, and per-tick events. This is the single structure for tick computation. Persistence (SQLite, ChromaDB) is a serialization concern, not a runtime partition. The Embedded Trinity is the durability layer; the World is the execution layer.

## III. Methodological Constraints

> Full article: `constitution/article-iii-methodology.md`

**1. No Magic Constants** — Every number traces to primitives or data sources.

**2. Falsifiability Required** — Every formula defines: prediction, null hypothesis, distinguishing observable, falsifying data.

**3. Physics Cosplay Prohibition** — Tensor notation earns its keep through actual invariance. Reject formalism without transformation laws.

**4. Data Source Traceability** — Approved: QCEW, Census/ACS, BEA, FRED, HIFLD, BTS, FCC, ATUS, CDC WONDER, Piketty/WID, PWT, Census Trade, Eviction Lab, US Courts, ATTOM/CoreLogic, Fed SCF, Fed Z.1 Financial Accounts, Chetty Opportunity Atlas, Natural Earth, USDA ERS Commuting Zones (derived from Census JTW), BEA Economic Areas (BEA regional definitions), OMB Core-Based Statistical Areas/CBSAs (OMB metro area definitions). New sources require explicit addition.

**5. Empirical vs Strategic Separation** — Material conditions from data (nodes, constraints, extractive edges). Strategic intervention NOT from data (solidaristic edges, organizing, consciousness-raising).

## IV. Test Case: Michigan Statewide (2010-2025)

> Full article: `constitution/article-iv-michigan.md`

The canonical test case is the State of Michigan, all 83 counties, 2010–2025. BEA Economic Areas (EAs) are the constitutional aggregation tier for regional analysis. The model MUST reproduce observed class transitions and inter-regional inequality using only QCEW/Census data + theoretical mechanisms. Failure = theory or implementation wrong.

### IV.1 Detroit-Windsor Boundary Condition

The Detroit-Windsor corridor is a required boundary condition, not an optional foreign node. Cross-border labor markets, trade flows, and imperial rent circuits (automotive supply chain, logistics, water rights) MUST be modeled. Canada is a first-class territorial substrate. The boundary itself is a contradiction surface: same labor, different citizenship regimes, different repression budgets.

### IV.2 Tri-County Backward-Compat Acceptance Criterion

The original Wayne County vs Oakland County tri-county sub-test (Crisis → Devaluation → Recolonization → Displacement) is preserved as a mandatory backward-compatibility acceptance criterion. Any statewide model MUST reproduce the tri-county results when coarse-grained to that resolution. Regression = implementation wrong.

## V. Action Vocabulary

> Full article: `constitution/article-v-verbs.md`

### Player (9 verbs)

**Educate, Aid, Attack, Mobilize, Campaign, Move, Investigate, Reproduce, Negotiate**.

Player-facing (3x3): Build org | Project power | Manage resources. Engine-facing: Organization (node) | Population (org↔class edges) | Other actors (org↔org edges). Every verb maps to a graph operation. Atomic. All always available. Deterministic.

### State AI (6 verbs)

**Administer** (Fund, Staff, Audit, Legislate) — reproduce state apparatus. **Develop** (Rezone, Invest, Eminent Domain, Tax Incentives) — reshape territory layer; asymmetric verb player lacks; gentrification as verb. **Research** — advance tech; products potentially seizable by player. **Co-opt** (Bribe, Propagandize, Incorporate, Divide) — absorb opposition or destroy relationships; Divide targets edges not nodes. **Repress** (Surveil, Infiltrate, Raid, Prosecute, Liquidate) — escalation ladder; each step costs more legitimacy. **Withdraw** (Strategic / Tactical / Scorched Earth) — concede, reposition, or deny territory; player must read which mode.

No separate state Negotiate verb — negotiation is a mode of Withdraw (terms of concession) or Co-opt (terms of absorption). Asymmetry is structural: state has fewer verbs but Develop operates on substrate player cannot directly modify.

## VI. Scope Control

> Full article: `constitution/article-vi-scope.md`

1. **Material Base First** — Economic extraction → class formation → solidarity → THEN repression.
2. **Zoom Where Data Exists** — Resolution matches data availability.
3. **Flag Scope Creep** — Must trace to Detroit prediction or improve falsifiability. Otherwise DEFER.

## VII. Visual Design Principles

> Full article: `constitution/article-vii-visual.md`

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

> Full article: `constitution/article-viii-antipatterns.md`

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

> Full article: `constitution/article-ix-governance.md`

**1. Amendment Procedure** — Propose → demonstrate consistency → update artifacts → increment version.

**Versioning**: MAJOR (removal/redefinition of primitive or principle), MINOR (new principle/section or material expansion), PATCH (clarification, wording, non-semantic refinement).

**Compliance triggers**: New system, formula change, data source addition, scope expansion, UI implementation, infrastructure/deployment change, primitive redefinition.

**2. Staged Amendment Series** — When a primitive changes, downstream principles MUST be translated through a numbered amendment series with invariance proofs. Each amendment in the series must demonstrate that affected principles are at least as constrained as their predecessors. No amendment in the series may be skipped. The series is complete only when all downstream principles are either re-grounded or explicitly superseded.

**Amendment A — Dialectic Primitive** (ratified v2.0.0): Introduces `Dialectic[A, B]` as irreducible unit. Demotes Four-Node Recursive to derived partition. ValueTensor4x3 derived status.

**Amendment B — Partition Invariance** (pending): Four-node schema as derived partition. Requirement: invariance proof under morphism-preserving coarse-graining.

**Amendment C — OODA Placement** (pending): Architectural home for OODA profiles in v2. Requirement: spec with invariance proof before v2.2.0.

**Amendment D — Hyperedge Reconciliation** (pending): NetworkX+XGI and strictly-dyadic morphism constraint. Requirement: spec preserving Anti-Pattern VIII.9.

Additional amendments will be registered as they are identified during downstream translation.

## X. Deployment Infrastructure

> Full article: `constitution/article-x-infrastructure.md`

**1. Bare Metal, Ansible-Managed** — No Docker, no Nix, no containerization. Everything installs on the host OS via apt packages and is configured declaratively by Ansible playbooks. The entire server state is described in version-controlled roles. Nothing is installed by hand on the VPS.

**2. Terraform Provisions, cloud-init Bridges, Ansible Configures** — Terraform creates and destroys cloud resources (servers, firewalls, DNS records, object storage). cloud-init creates the deploy user on first boot — the only thing it does. Ansible configures everything after. These three tools have non-overlapping responsibilities.

**3. Postgres Bare Metal from PGDG** — PostgreSQL installs from the upstream PGDG apt repository directly on the host. Extensions (PostGIS, pgvector) install as apt packages. Ansible's `community.postgresql` collection manages database creation, roles, extensions, and pg_hba declaratively. Postgres listens on Unix socket only — never exposed to the network.

**4. systemd as Sole Supervisor** — All processes (Postgres, Gunicorn, Nginx, Woodpecker) run as systemd units. No additional supervisors. Service dependencies, restart policies, and cgroup resource limits are declared in unit files deployed by Ansible.

**5. Cloudflare Edge, Hetzner Compute** — Nothing computes on Cloudflare; nothing reaches users without Cloudflare first. Cloudflare handles DNS, SSL, DDoS, WAF, CDN, R2 storage, and Workers AI. Hetzner handles Django, Postgres, NetworkX, and CI/CD. Division of labor is strict — no function is shared between the two.

**6. Solo-Developer Constraint** — Every infrastructure component is filtered through: does this require a second full-time job to maintain? If yes, reject it. Kubernetes, Prometheus+Grafana, HashiCorp Vault, service meshes, and container orchestration are explicitly rejected until scale demands them.

______________________________________________________________________

**Version**: 2.1.0 | **Ratified**: 2026-01-30 | **Last Amended**: 2026-04-28
