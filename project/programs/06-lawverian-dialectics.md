# 06 — Lawverian Dialectics Refactor (MASTER RECORD)

**Status**: **IMPLEMENTED — Phases A–E COMPLETE (2026-07-03, ADR051)**.
Constitution Amendment K (v2.7.0). Canonical re-baseline accepted
(`ea0e3661`): contradiction_field rows flow, max_tension non-saturating,
liveness 83/83. Implemented on the **BabylonGraph** substrate — the
NetworkX→rustworkx migration (Amendment L, ADR052, `08-graph-substrate.md`)
post-dates this design; its `nx.*` sketches now run through BabylonGraph's
nx-compat surface.

This is the consolidated master: the former phase-design docs `06a`
(Phase C2), `06b` (Phase D), and `06c` (Phase E) are folded in below as
Parts II–IV (owner ruling, 2026-07-03) and their files deleted. Citations
of the form "06a §5" resolve to "Part II §5" here, "06c E8" to
"Part IV §E8", etc. Part I is the original design+delegation contract,
kept verbatim as the semantic record behind ADR051.

Owner decisions: direct refactor (no speckit), re-ground in place,
executable + law-tested category theory, Fable designs/reviews +
delegated implementation. Branch: `refactor/lawverian-dialectics`
(off `fix/web-local-play-wireup`); continued by
`refactor/networkx-to-rustworkx`.

______________________________________________________________________

## Part I — Design doc + delegation contract (original 06)

## 1. Mission

Make Lawvere's category-theoretic dialectics the rigorous representation that
powers the engine. Contradiction stops being a saturating scalar and becomes
a structured object: two poles, a unity, a **measured gap** (how far the
opposition is from closure), a **rate** (its direction of development), a
**principal aspect** (which pole leads), a **level** (where in the
spatial/social hierarchy it lives), and an **Aufhebung condition** (when it
resolves upward). The economy joins the same machinery: imperial rent Φ is
the measured defect of the wage⇄value adjunction.

Theory anchors (all verified sources, 2026-07-02):

- Lawvere 1970 "Quantifiers and Sheaves": "the main pairs of opposing
  tendencies in mathematics take the form of adjoint functors."
- Adjoint cylinder (UIAO): adjoint string i\_! ⊣ i^\* ⊣ i\_\* with both outer
  functors fully faithful; skeleton comonad □ = i\_! ∘ i^*, sheaf monad
  ○ = i\_* ∘ i^*. Laws: □□=□, ○○=○, □○=□, ○□=○, and i^* ∘ i\_! = id =
  i^\* ∘ i\_\* (full faithfulness of the embeddings).
- Aufhebung of level i = least level j > i with ○_j □_i = □_i
  (the lower opposition is resolved-and-preserved above) — computable
  negation-of-negation.
- Cohesion quadruple Π₀ ⊣ Δ ⊣ Γ ⊣ ∇ (pieces/discrete/points/codiscrete).
  ⚠ Vocabulary: this repo already uses "cohesion" for organizational
  cohesion — the package says "connectivity cylinder" / "atomization".
- Laclau & Mouffe ch. 3 (PDF in `project/`): antagonism = failure of full
  identity-constitution, distinct from logical contradiction and real
  opposition; maps to `is_antagonistic` = gap that cannot close at its
  current level.

## 2. The four inertness bugs (now requirements)

Forensics 2026-07-02 (canonical session `6104efc2`, Postgres-verified):
tension exactly 1.0 on all edges by ~t100 with zero cross-county variance;
`contradiction_field` table 0 rows ever; solidarity 0.0 everywhere.

1. **Formula**: `engine/systems/contradiction.py:99-171` feeds raw
   dollar-scale `wealth_gap` into a [0,1] clamp → delta ≈ 1.0/tick,
   add-only (no reachable decay: bridge edges carry no `edge_mode`).
   → REQUIREMENT: gaps are normalized, can fall, and are computed from
   adjunction defects.
1. **Wiring**: systems 19–21 gate on `services.field_registry` which is
   `None` in every production path (`services.py:73`).
   → REQUIREMENT: `ServiceContainer.create` wires a populated
   OppositionRegistry by default.
1. **Persistence**: `persist_contradiction_fields`
   (`postgres_runtime/_legacy.py:682-716`) has zero production callers.
   → REQUIREMENT: bridge `persist_tick` snapshots the registry every tick.
1. **Consumption**: `principal_contradiction` attr read by nobody; the one
   tension consumer (bourgeois decision, `economic.py:762-790`) is
   degenerate at saturation.
   → REQUIREMENT: every phase that adds a producer adds a consumer.

## 3. Phase A — the core (`src/babylon/dialectics/`) — Fable, this session

Pure package: **no engine imports** (imports from `babylon.models` types
only). House patterns: state = frozen Pydantic; behavior = Protocol +
concrete classes; mypy strict; RST docstrings; bounded loops.

### `core/galois.py` — poset adjunctions (fully executable)

```python
class GaloisConnection(Generic[P, Q]):
    def __init__(self, lower: Callable[[P], Q], upper: Callable[[Q], P],
                 leq_p: Callable[[P, P], bool], leq_q: Callable[[Q, Q], bool]) -> None
    def holds(self, p: P, q: Q) -> bool      # lower(p) ≤q q  ⟺  p ≤p upper(q)
    def closure(self, p: P) -> P             # upper(lower(p)) — monad on P
    def interior(self, q: Q) -> Q            # lower(upper(q)) — comonad on Q
```

Laws (Hypothesis, `tests/property/dialectics/test_galois_laws.py`):
`holds` is an iff for the fixture connections; closure is inflationary,
idempotent, monotone; interior is deflationary, idempotent, monotone.

### `core/cylinder.py` — the UIAO / adjoint cylinder

```python
class AdjointCylinder(Generic[S, X]):
    def __init__(self, embed_left: Callable[[S], X], project: Callable[[X], S],
                 embed_right: Callable[[S], X], metric: Callable[[X, X], float],
                 eq_base: Callable[[S, S], bool] = operator.eq) -> None
    def skeleton(self, x: X) -> X            # □x = embed_left(project(x))
    def sheaf(self, x: X) -> X               # ○x = embed_right(project(x))
    def span(self, x: X) -> float            # d(□x, ○x)
    def balance(self, x: X) -> float         # d(□x, x)/span ∈ [0,1]; 0.5 if span=0
    def retracts(self, s: S) -> bool         # project∘embed_left == id == project∘embed_right
```

Laws (`test_cylinder_laws.py`, fixture = connectivity cylinder over small
nx graphs: embed_left=edgeless, embed_right=complete, project=node set,
metric=|edge symmetric difference|): retraction; □/○ idempotent; □○=□,
○□=○; balance∈[0,1]; balance(□x)=0 and balance(○x)=1 when span>0.

### `core/level.py` — levels + Aufhebung

```python
class Level(BaseModel):            # frozen: index >= 0, name
class LevelOperators(Generic[X]):  # frozen dataclass: skeleton, sheaf callables
class LevelLattice(Generic[X]):
    def __init__(self, levels: Sequence[Level],
                 operators: Mapping[int, LevelOperators[X]],
                 eq: Callable[[X, X], bool]) -> None   # strictly increasing indices
    def is_resolved_at(self, x: X, lower: int, higher: int) -> bool
        # Lawvere resolution: sheaf_higher(skeleton_lower(x)) == skeleton_lower(x)
    def aufhebung_of(self, lower: int, probes: Sequence[X]) -> Level | None
        # least higher level resolving on ALL probes; None if none does
```

Tests (`tests/unit/dialectics/test_level_lattice.py`): known-answer chain
where the resolving level is hand-computable; None when unresolvable;
validation errors on bad lattices.

### `core/opposition.py` — the contradiction registry

```python
class GapReading(BaseModel):       # frozen: gap: Intensity, balance: float [-1,1]
class GapMeasure(Protocol[I]):     # __call__(inputs: I) -> GapReading
class OppositionSpec(BaseModel):   # frozen: key, pole_a, pole_b, unity,
                                   #   level_name, antagonistic: bool = False
class BoundOpposition(Generic[I]): # frozen dataclass: spec + measure
class OppositionState(BaseModel):  # frozen: key, tick, gap, balance, rate,
                                   #   leading_pole: Literal["a","b"], is_principal
class OppositionRegistry(Generic[I]):
    def __init__(self, bindings: Sequence[BoundOpposition[I]],
                 rate_weight: float = 10.0) -> None      # unique keys enforced
    def step(self, inputs: I, tick: int,
             previous: Mapping[str, OppositionState] | None = None,
             ) -> tuple[OppositionState, ...]
    # rate = gap - prev.gap; leading pole: sign of balance, with INERTIA at 0
    # (holds previous pole — the principal aspect persists until overturned);
    # principal = argmax gap*(1 + rate_weight*|rate|), ties → lexicographic key.
```

Semantics contract with the EXISTING model
(`models/entities/contradiction.py` — do NOT duplicate it): registry state
maps onto `Contradiction` fields in Phase C as intensity ← gap,
aspect_balance ← rate, principal_aspect ← leading_pole, identity ← unity
strength. `Balance ∈ [-1,1]` = signed dominance of pole_b over pole_a.

Tests (`tests/unit/dialectics/test_opposition_registry.py`): rate
computation, principal selection + determinism of ties, pole inertia at
balance=0, unique-key validation, purity (same inputs → same states).

## 4. Phase B — connectivity cylinder instance (delegate)

- NEW `src/babylon/dialectics/instances/connectivity.py`: the cylinder over
  the SOLIDARITY subgraph. REUSE
  `engine/topology_monitor.py:extract_solidarity_subgraph:53` (don't
  reimplement). Π₀ via `nx.connected_components`. Atomization index
  = (|Π₀(X)|−1)/(|Γ(X)|−1), guard n≤1 → 0.0.
- TopologyMonitor keeps its public API; its percolation metrics
  (`calculate_component_metrics:106`) become derived from the cylinder
  (same numbers — behavior-compatible; assert equality against the old
  computation in tests before deleting the old path).
- SolidaritySystem: document + test the operator reading (transmission
  moves toward ○, repression toward □); no behavior change in B.
- Gate: `mise run check` + income-circuit suite + qa:e2e-regression green;
  new unit tests for the instance; NO baseline changes expected.

## 5. Phase C — Opposition registry rewires systems 18–21 (delegate; biggest)

1. `formulas/contradiction.py`: new normalized gap formula (relative wealth
   ratio via sigmoid or ratio-normalization — NOT raw dollars), explicit
   decay term, doctests. Old `calculate_contradiction_intensity` retired
   (update the 3 callers + formula registry if listed).

1. Registry content: the 24-opposition catalog lifted from dormant
   `engine/dialectics/` (its `registry.py:118-149` lists them; its
   `crises.py:6-11` maps crisis producers; its motion laws name the
   economics kernels each opposition reads). Phase C binds AT LEAST:
   capital_labor (EXPLOITATION edges), wage (WAGES), tenancy (TENANCY),
   atomization (Phase B cylinder), plus the frame-level
   imperial (core↔periphery) — full 24 as data allows; unbound specs may
   register with a null measure that reads 0 (documented).

1. `ServiceContainer.create` wires the registry by default (replaces
   `field_registry=None`); ContradictionSystem computes registry.step per
   tick and writes states into `contradiction_frames` (existing
   `Contradiction` model, field mapping per §3); FieldDerivativeSystem's
   derivative machinery repoints at gap trajectories; EdgeTransitionSystem
   predicates read gaps (Aufhebung conditions arrive in Phase E).

1. Bridge `persist_tick` calls `persist_contradiction_fields` with the
   per-tick registry snapshot → `contradiction_field` rows flow.

1. Consumers (same phase, non-negotiable): bourgeois decision takes the
   EXPLOITATION opposition's gap instead of degenerate aggregate tension
   (`economic.py:762-790`); StruggleSystem's rupture check reads that gap;
   ConsciousnessSystem agitation reads gap rates (keep crisis-gating:
   only DETERIORATION generates agitation).

1. Retire dormant `engine/dialectics/` (delete package + shim imports);
   migrate its ~224 tests' behavioral intents into the new instances'
   suites (the Grundrisse 10-tick cycle becomes a registry integration
   test); document in the ADR.

   **Done (C1.7, 2026-07-03).** Deleted the dormant package (31 modules) and
   its only non-test consumer — the `/v2` dialectic web surface
   (`web/game/repositories.py`; the `/v2/world/` + `/v2/dialectics/<id>/`
   routes in `web/game/api.py`; their `web/game/urls.py` registrations;
   `web/frontend/src/types/dialectic.ts` + `components/DialecticCard.tsx`).
   Postgres tables and migrations 0004/0005 kept — no migration written or
   deleted; no web test exercised the routes. All 224 dormant tests are
   catalogued in `project/c17-test-migration-ledger.md` — **17 covered / 20
   migrated / 187 obsolete-by-design**. The 20 migrated intents became **22
   new tests**: 15 in `tests/unit/economics/test_value.py` (the surviving
   `economics.value` poles, otherwise uncovered) and 7 in
   `tests/integration/test_grundrisse_cycle.py` (the Grundrisse arc:
   multi-tick step, gap/rate evolution, principal selection, rupture gating).
   The ADR is deferred to Phase E per §7 — this note plus the ledger stand in.
   Now-orphaned dead code flagged for the owner (not deleted, out of scope):
   `babylon.economics.value` and three unused v2 serializers in
   `web/game/serializers.py`.

1. Margins: update `tests/assertions.py` tolerances only where semantics
   changed; `tests/constants.py` tension bands → gap bands; regenerate the
   5 small baselines (`mise run qa:regression-generate`); fix exact-number
   pins (`test_timeseries_endpoint.py:63` 0.43,
   `test_territory_edge_serialization.py:71-72` 0.45/0.62,
   `test_simulation_engine.py:665` accumulation-rate).

- Gate: full standing loop + a NEW integration test: 50-tick bridged run
  where stddev(gap) across counties > 0 and gap is not pinned at 1.0.

## 6. Phase D — economy as adjunction instance (delegate)

- `instances/value_form.py`: adjunction labor-time ⇄ money via
  `melt_calculator.py` τ and `monetary/converter.py` (reuse, don't wrap
  trivially); **Φ = counit defect**, per-class signed (W_c − V_c)/V_c;
  law tests: numeraire invariance (extend spec-060 suite), τ round-trip.
- `instances/scale.py`: allocate ⊣ aggregate
  (`industry_to_county_allocator.py` ⊣ `geographic_flow.py:225`);
  property test: aggregate∘allocate ≈ id within documented tolerance;
  conservation invariants (`conservation_audit.py:158-180`) referenced as
  naturality squares in docstrings + one law test per square family.
- ImperialRentSystem reports flows through the instance (computation
  unchanged where already correct — accounting becomes categorical).
- Gate: standing loop + economics suites + conservation property tests.

## 7. Phase E — levels + Aufhebung + re-baseline (delegate)

**STATUS: COMPLETE (2026-07-03, ADR051).** Six commit units shipped — E0 field-stack
repoint, E1 spatial+social level lattices, E2 fixed-point regimes +
LEVEL_TRANSITION, E3 edge-mode category laws, E4 fractal check (expressed, not
xfailed), E5 induced-crisis + E6 grundrisse fixed-point integration tests, E8
canonical michigan re-baseline. Two resolutions flagged for review (see ADR051):
the regime classifies the capital_labor opposition rather than the abstract
Maoist principal; E3's "every EXTRACTIVE→SOLIDARISTIC path transits
TRANSACTIONAL" universal is false against the 17 (united-front routes exist) so
the TRUE law was tested instead. E7 rulings honored: TopologyMonitor stays a
test/facade observer (LEVEL_TRANSITION is the production Aufhebung signal); RLF
simplex constraints deferred to spec-071. Re-baseline acceptance: a/b/d PASS
(83/83 liveness, 2595 contradiction_field rows, max_tension 0.667305 vs the
old pinned 1.0); criterion (c) spatial stddev FAILS AS WRITTEN and was
accepted RE-SCOPED by Fable review — hydration seeds identical synthetic
wealth per county, so spatial spread is structurally zero regardless of the
dialectics layer; the criterion's intent (non-degenerate, non-saturating
tension) is met on the temporal axis, and hydration heterogeneity (per-county
wealth from QCEW) is the recorded open item (ADR051 `rebaseline_acceptance`).

- Level lattices: spatial hex≺county≺state≺nation (operators from scale
  maps); social individual≺community≺class≺bloc (communities via XGI
  membership span; NoCommunityFanOut-compatible).
- Aufhebung condition (`LevelLattice.is_resolved_at`) drives
  EdgeTransitionSystem qualitative transitions + TopologyMonitor phase
  changes; new LEVEL_TRANSITION event (extend EventType enum).
- Induced-crisis integration test: wage cut / rent-pool drain → assert
  gap growth, principal-contradiction shift, and at least one
  RUPTURE-or-LEVEL_TRANSITION fires (the crisis-gated pathway proves out).
- Full 520-tick canonical re-baseline: 83/83 liveness AND
  contradiction_field populated AND stddev(gap) across counties > 0 at
  t300 AND gaps non-saturating.
- ADR in `ai-docs/decisions/` + index; `ai-docs/state.yaml` bump; root
  `CLAUDE.md` pipeline-table note; update `project/01` + this file.

## 8. Delegation protocol

- One session per phase (Sonnet/Opus). Read THIS file + `project/01` +
  `project/02` first. TDD; commit per unit (conventional commits,
  Co-Authored-By trailer); never commit the 72 pre-existing modified test
  files; pre-commit formatters may abort a commit — re-add and re-commit,
  then verify with `git log --oneline -1`.
- Phase gate (run before declaring a phase done):

```bash
mise run check
poetry run pytest tests/integration/test_bridge_income_circuit.py -q
mise run qa:e2e-regression
poetry run pytest tests/property/ -q        # Phase C onward
```

- Fable reviews at each boundary before the next phase starts. Anything
  ambiguous: STOP and leave a question in the commit/PR body rather than
  guessing — especially around StruggleSystem (it severs EXPLOITATION
  edges; the hegemony test must stay green) and the crisis-gating of
  consciousness (flat during a growing bribe is CORRECT).

## 9. Chat-corpus requirements (added 2026-07-03 — see `07-chat-corpus-alignment.md`)

A full mine of Percy's claude.ai history surfaced endorsed design this
contract must absorb. The Lawverian foundation itself is owner-ordered
(2026-07-02 directive) — but the corpus adds constraints and content.

### 9.1 The earn-its-keep discipline (governs every phase)

Percy's own 2026-04-26 "Category theory meme" chat mocks duality-chasing;
the standing rule: **a categorical construct ships only if it yields a
law, a prediction, or a computation we run** — never as vocabulary. The
three CT structures that chat DID endorse become explicit targets:

- **H3 aggregation as a sheaf**: gluing = conservation; functoriality
  `A_{6->5} . A_{7->6} = A_{7->5}`; extensive quantities sum, intensive
  weighted-mean; aggregate primitives, recompute derived. NO cohomology.
  (Phase D `instances/scale.py` — name the sheaf condition in the tests.)
- **Edge modes as a presented category**: objects {EXTRACTIVE,
  TRANSACTIONAL, SOLIDARISTIC, ANTAGONISTIC, CO-OPTIVE}, hom-sets =
  legal transitions only (EXTRACTIVE->SOLIDARISTIC must transit
  TRANSACTIONAL). (Phase E EdgeTransition rework.)
- **Material/ideological as a fibration**: "class-for-itself is the
  failure of the canonical lift to exist." (Exploratory; earns its keep
  only if it produces the lift-existence check as code — else drop.)

### 9.2 Amendments to Phase C2 (composition + structure)

Beyond retiring the dormant package, C2 MUST re-express what the dormant
design carried and Percy ratified:

- **Composition algebra**: product (D1 ⊗ D2), sum (D1 ⊕ D2), and NESTING
  (a pole may itself be an opposition — the fractal four-node recursion,
  her original architecture). Registry gains composite bindings whose
  gap/balance derive from components; laws: composition respects gap
  bounds; nesting depth bounded (static loop bound).
- **Typed coupling graph**: oppositions relate via typed morphisms —
  feeds / constrains / transforms / contains / antagonizes — replacing
  "coupled only through shared inputs". Player verbs act as MORPHISM
  MUTATIONS (stance = signed intervention on a target opposition's
  balance); events = pull-based hooks over opposition states.
- **Sublation lineage**: `parent_id -> successor_id` first-class on
  opposition states (the dormant `Dialectic.parent_id` semantics);
  sublation-containment: successor GOVERNS predecessor's motion (the
  Class->Party handoff pattern), not mere replacement.
- **Observation-relativity** (deferred OK, record now): `observe()` is
  frame-dependent — Commodity through Transformation yields
  price-of-production; through Imperial yields unequal-exchange-distorted
  realization. Design the measure signature so frames can be added.
- **VIII.9 n-ary protection**: `OppositionSpec(pole_a, pole_b)` is
  dyadic; internal nations are NOT one pole. Rule: a pole may reference a
  COMMUNITY (XGI hyperedge id) — the dyadic reduction of an n-ary
  formation is FORBIDDEN as a pole; and opposition-to-APPARATUS
  (institutional exclusion, no oppressor community) is a distinct
  spec flavor from contradiction-pairs. Encode as validation + docs.

### 9.3 Amendments to Phase D (economy)

- **Φ tri-decomposition is mandatory**: Φ = three separately-measured
  defects — unequal exchange (Emmanuel/Amin), externalized reproduction
  (Meillassoux), domestic shadow labor (Fortunati) — the scalar is their
  SUM, never the primitive. "A single scalar weight cannot carry Φ's
  three components" (2026-04-12). Three adjunction instances, one report.
- **Conservation identity as THE law test**:
  `ΣL_performed = ΣV_visible + ΣΦ_shadow`, each Φ component independently
  traceable.
- **γ's three mechanisms are non-interchangeable**: γ_basket = τa/τb
  (international), γ_III = L_paid/(L_paid+L_unpaid) (reproductive
  visibility), π = τ_through/τ_national (throughput, NOT a visibility
  mechanism). Keep them distinct in the value-form instance.
- **Class-position sorting**: Φ_hour = W − τ_eff (τ_eff = τ·γ_basket);
  Φ_hour ≥ 0 → labor aristocracy; Φ_hour < 0 ∧ W ≥ V_repro → proletariat;
  W < V_repro → subproletariat; Φ_hour conserved across the divide
  ("Oakland's labor-aristocrat hour IS Wayne's super-exploited hour").

### 9.4 Amendments to Phase E (+ handoff to spec-071)

- **Fixed-point tick ontology** (Percy: "the unification"): a tick is one
  iteration of a self-consistency search — convergence = reproduction,
  non-convergence = crisis, bifurcation-at-higher-order = sublation.
  Phase E's Aufhebung wiring must implement rupture as the THIRD REGIME
  of the same operator, not a separate mechanism. The Grundrisse 4-cycle
  (Production→Circulation→Distribution→Consumption reading previous-tick
  state) is the canonical cyclical instance; port its 10-tick
  no-violation test as a FIXED-POINT test, not a flat registry test.
- **Rupture gate = condition AND level** (Mao's bomb): threshold-crossing
  needs a state predicate in addition to accumulator level — never fire
  on magnitude alone. (C1 already gates on "exceeds threshold AND
  rising"; keep the predicate extensible.)
- **Fractal check**: the level lattice must reproduce the 4-node
  recursion — {Core,Periphery}×{Bourgeoisie,Proletariat} reappearing at
  each zoom, lumpen appearing only on zoom-in. If Aufhebung-between-
  levels can't express this, say so explicitly rather than fake it.
- **RLF simplex constraints (071 consumes these)**: r+l+f=1, liberal
  tie-break default; `ideological_contestation = H(r,l,f)/log 3` is a
  DIAGNOSTIC ONLY (entropy is permutation-symmetric — it cannot carry the
  Jackson asymmetry); the asymmetry lives in the directed flow field:
  **f→r forbidden or ε-gated** (proletarianization ∧ adjacent-r ∧
  solidarity edge) — this breaks detailed balance (Kolmogorov) so NO
  potential function / free-energy formulation exists (rejected
  explicitly); r→f carries a CAPACITY transfer.
  - Also endorsed: `assimilation_ratio = f/(l+f)`.
  - Rejected: (c,v,s) ↦ (r,l,f) direct maps (vulgar economism), and
    the F = E − T·S MaxEnt framing.
- **Weight convention**: balance ∈ [−1,1] with 0 = equilibrium is the
  ratified convention (running code beat the spec's [0,1]) — already
  honored; principal-aspect flip semantics: ω(A)+ω(Ā)=1, flip at 0.5,
  with inertia.

______________________________________________________________________

## Part II — Phase C2 design (composition + structure) — formerly 06a

**IMPLEMENTED** (Phase C2 commit series; see ADR051). The
`StanceIntervention`/`opposition_interventions` hook in §5 is spec-071's
OODA entry point.

Fable's design for `project/06` §9.2, written 2026-07-03 while C1.7 ran.
Delegate: read `project/06` §8 (protocol) + §9.1 (earn-its-keep) first.
Everything here extends the NEW package (`src/babylon/dialectics/`); the
dormant `engine/dialectics/` is gone after C1.7 — its ratified semantics
are quoted here so you never need to resurrect it.

## Design rulings (Fable, binding for this phase)

### 1. Composition algebra — `core/composition.py`

Composition operates at the **binding** level: combinators take
`BoundOpposition[I]` components and return a new `BoundOpposition[I]`
whose measure is a pure function of the component measures re-run on the
same inputs. The registry itself DOES NOT CHANGE — composites are
ordinary bindings; their states are ordinary `OppositionState` rows.
(No post-step reading of component states: measures are pure, re-measure
is idempotent, and this keeps zero ordering dependency.)

- `product(spec, d1, d2)` — D1 ⊗ D2, "sharp only if BOTH are sharp":
  `gap = gap1 * gap2`, `balance = gap-weighted mean of balances`
  (0 if both gaps 0). **Law: gap(⊗) ≤ min(gap1, gap2).**
- `sum_(spec, d1, d2)` — D1 ⊕ D2, "either develops":
  `gap = g1 + g2 − g1·g2` (probabilistic OR), balance as above.
  **Law: gap(⊕) ≥ max(gap1, gap2).**
- Both stay in [0,1] by construction — Hypothesis property test over
  arbitrary component readings, not just examples.
- Composite specs carry provenance: `OppositionSpec` gains
  `component_keys: tuple[str, ...] = ()` and
  `composition: Literal["", "product", "sum"] = ""` (defaults keep every
  existing constructor valid).

### 2. Nesting (the fractal four-node recursion) — pole bindings

A pole may itself BE an opposition, or reference a community. New frozen
model in `core/opposition.py`:

```python
class PoleBinding(BaseModel):
    label: str                  # display name, required
    opposition_key: str = ""    # nesting: this pole IS that opposition
    community_id: str = ""      # n-ary formation via XGI hyperedge id
    # model_validator: opposition_key and community_id are mutually exclusive
```

`OppositionSpec` gains `binding_a: PoleBinding | None = None`,
`binding_b: PoleBinding | None = None` (None = plain named pole; fully
backward compatible). Registry `__init__` validates the nesting graph:

- every `opposition_key` referenced is registered (KeyError names it);
- the reference graph is acyclic (ValueError lists the cycle);
- depth ≤ `MAX_NESTING_DEPTH = 4` (module constant — the static loop
  bound; DFS is bounded by len(bindings), itself bounded at build time).

The four-node recursion `{Core,Periphery} × {Bourgeoisie,Proletariat}`
ships as a **test-fixture registry** (nested capital_labor per zone),
NOT as a production catalog change — composites enter the catalog when
Phase D gives the imperial opposition real periphery data. The test must
assert the recursion actually computes (outer gap responds to inner-pair
wealth changes), not just constructs.

### 3. VIII.9 n-ary protection + apparatus flavor

- `community_id` on `PoleBinding` is the ONLY way a pole references a
  collective formation; docs state the rule: reducing an n-ary formation
  (internal nation) to a plain dyadic pole string is FORBIDDEN.
- `OppositionSpec` gains
  `flavor: Literal["contradiction", "apparatus"] = "contradiction"`.
  Apparatus = institutional exclusion; there is NO oppressor community —
  validator: `flavor="apparatus"` ⇒ `binding_b` (the apparatus pole) has
  empty `community_id`. One law test per validator.

### 4. Typed coupling graph — `core/coupling.py`

Ratified vocabulary (verbatim from dormant `world.py`):
`feeds` (target's step reads source's observe), `constrains` (source
limits target's state space), `transforms` (source's output becomes
target's input prices), `contains` (source is one of target's poles —
nesting), `antagonizes` (mutual).

```python
CouplingKind = Literal["feeds", "constrains", "transforms", "contains", "antagonizes"]
class Coupling(BaseModel):      # frozen: source, target, kind
class CouplingGraph:            # constructed against a registry's keys
    def upstream_for(self, key) -> tuple[Coupling, ...]
    def downstream_of(self, key) -> tuple[Coupling, ...]
```

Validation laws (each a test): endpoints must be registered keys;
`antagonizes` edges are stored symmetric (adding one direction implies
the reverse on query); `contains` edges are AUTO-DERIVED from
`PoleBinding.opposition_key` and may not be added manually (consistency:
nesting ⇔ contains edge, exactly).

Catalog data: `build_default_coupling_graph()` in `instances/catalog.py`
encoding the ratified crisis-producer map as `transforms` couplings —
Realization←Circulation, Disproportionality←Reproduction,
DebtSpiral←SurplusDistribution, Financial←Credit — plus
`capital_labor antagonizes imperial` (both antagonistic specs) and
`wage feeds capital_labor` (the consciousness crisis signal reads wage's
rate; capital_labor's development presupposes the wage relation). These
edges reference keys that enter the registry across C2/D/E; the builder
takes the registry and SKIPS (with a logged, tested list) couplings
whose endpoints are not yet bound — never invents null bindings for
them. Phase E's sublation rules consume this graph; in C2 the tests
assert the topology matches this map exactly.

### 5. Player verbs as morphism mutations — interventions

```python
class StanceIntervention(BaseModel):   # frozen
    target_key: str
    delta_balance: float               # signed
    source: str                        # verb / organization id, for audit
```

`core/coupling.py` ships `apply_interventions(states, interventions)`:
returns new states with `balance = clamp(balance + Σ delta, -1, 1)` per
target, recomputing `leading_pole` under the same zero-inertia rule the
registry uses (interventions can flip the leading pole — that is their
POINT: stance is a signed intervention on the target's balance).
Unknown `target_key` → ValueError (logic layer fails loud, per repo
error-handling rules). Laws: clamp holds under Hypothesis-generated
intervention streams; unknown key raises; empty stream is identity.

Engine wiring (same phase, non-negotiable): `ContradictionSystem` reads
graph attr `opposition_interventions` (list of StanceIntervention dumps,
written by verb/OODA systems), applies them AFTER `registry.step`,
BEFORE `_write_frames`/`_maybe_rupture`/snapshot-stash, then CLEARS the
attr (consumed-once semantics; a test pins that two ticks don't
double-apply). No verb system writes it yet — a unit test writes it
directly; the OODA hookup is spec-071's, not ours.

### 6. Sublation lineage — governed states

`OppositionState` gains `governed_by: str = ""` and
`successor_key: str = ""` (defaults; frozen model, no migration needed —
snapshot round-trips through `model_dump` automatically).
`OppositionRegistry.__init__` gains `governance: Mapping[str, str] = {}`
(predecessor key → successor key; both must be registered, no chains
deeper than MAX_NESTING_DEPTH, no cycles — same bounded validation).

The one dynamic C2 implements (the Class→Party pattern's invariant):
**a governed opposition is EXCLUDED from principal selection** — the
successor's development leads. Law test: with governance
{"capital_labor": "party"} (test fixture), capital_labor can carry the
largest score and still never be `is_principal`; its state carries
`governed_by="party"`. WHO becomes governed WHEN (the Aufhebung
condition) is Phase E's — C2 ships the mechanism inert-but-lawful.

### 7. Observation-relativity — record only, no code

Ruling: deferred per §9.2 ("deferred OK, record now"). The measure
protocol stays `(inputs: I) -> GapReading`. The recorded design: frames
enter as a keyword-only `frame: str = "transformation"` parameter on
Phase D's value-form measures (frame-dependent observe: Commodity
through Transformation = price-of-production; through Imperial =
unequal-exchange-distorted realization). Write this into the C2 ADR's
"deferred" section and the `core/opposition.py` module docstring —
nothing else. A frame abstraction with one frame is vocabulary (§9.1).

### 8. Events = pull-based hooks — codify, don't build

The `opposition_states` graph attr IS the hook surface (consumers pull;
RUPTURE on the EventBus stays the only push). Document in the module
docstring + ADR. Do NOT add a hook/subscriber abstraction — nothing
computes with it today (§9.1).

## File plan

| File                                                     | Change                                                                                                                                                                                                 |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `src/babylon/dialectics/core/composition.py`             | NEW — product/sum combinators                                                                                                                                                                          |
| `src/babylon/dialectics/core/coupling.py`                | NEW — Coupling, CouplingGraph, StanceIntervention, apply_interventions                                                                                                                                 |
| `src/babylon/dialectics/core/opposition.py`              | PoleBinding; spec fields (component_keys, composition, binding_a/b, flavor); state fields (governed_by, successor_key); registry nesting+governance validation; governed-exclusion in `_principal_key` |
| `src/babylon/dialectics/instances/catalog.py`            | `build_default_coupling_graph()`                                                                                                                                                                       |
| `src/babylon/engine/systems/contradiction.py`            | interventions attr: read → apply → clear                                                                                                                                                               |
| `tests/unit/dialectics/test_composition.py`              | NEW — bounds laws (Hypothesis), provenance                                                                                                                                                             |
| `tests/unit/dialectics/test_coupling.py`                 | NEW — validation laws, intervention laws, producer-map topology                                                                                                                                        |
| `tests/unit/dialectics/test_opposition.py`               | EXTEND — nesting validation, governance exclusion, four-node recursion fixture                                                                                                                         |
| `tests/unit/engine/systems/test_contradiction_system.py` | EXTEND — intervention consume-once + pole flip through the system                                                                                                                                      |

Commit units: (1) composition, (2) pole bindings + n-ary/apparatus
validation, (3) coupling graph + catalog data, (4) interventions +
engine wiring, (5) governance. TDD each; mutation-probe at least the
governed-exclusion and the intervention clamp (earn-its-keep §9.1 —
plant the mutant, watch the suite, keep the killing test).

## Gate

Standing loop (`project/06` §8) + every law test above green + the
four-node recursion fixture computing. Then STOP for Fable review
before Phase D.

______________________________________________________________________

## Part III — Phase D design (economy as adjunction) — formerly 06b

**IMPLEMENTED** (commits `e3564efb`, `0dc7d419`, `aa2cfab0`, `0130caa1`; see
ADR051). The D5 transient-attr `from_graph` precedent (`w_paid`/`v_produced`)
is the pattern for spec-071's new fields.

Fable's binding design for `project/06` §6 + §9.3, written 2026-07-03
after a full kernel recon. Delegate: read `project/06` §8 + §9.1 first,
then this file. The prime directive of this phase is **reuse**: every
arithmetic quantity below already has a tested kernel (cited by file);
the adjunction instances are the STRUCTURE that binds them plus the NEW
laws. If a kernel's actual formula contradicts an identity stated here,
STOP and report — do not bend the law test to fit.

## D0. Ground truth corrections (recon findings, binding)

- The contract's shorthand "γ_basket = τa/τb" is a gloss. The tested
  code formula is the harmonic mean `γ_basket = 1/(α/γ_import + (1−α))`
  (`economics/melt/basket_visibility.py` and `economics/gamma/gamma_basket.py`
  agree). Cite and use the code formula everywhere.
- π (throughput) lives in `economics/throughput/calculator.py`
  (`π = τ_through/τ_national`) and is NOT a visibility mechanism — it
  never enters τ_eff. One law test pins this: rescaling π must not
  change τ_eff or any Φ component.
- Meillassoux externalized reproduction has NO kernel (zero repo hits).
  Its honest computable proxy is `formulas/lifecycle.py::compute_shadow_subsidy`
  (intergenerational: value of next-generation labor-power minus wages
  paid for its rearing). Phase D adopts that proxy as Φ_repro and says
  so in the docstring — no invented economics.
- `economics/shadow_labor.py` (config-lens Fortunati duplicate) is NOT
  touched — the data-driven `economics/gamma/` package is the kernel of
  record for Φ_domestic. Flag the duplication in the module docstring of
  value_form.py; reconciling it is out of scope.

## D1. `instances/value_form.py` — the labor-time ⇄ money adjunction

Typed poles REUSE the C1.7-orphaned `babylon.economics.value` models:
`AbstractLabor` (pole A, hours) ⇄ `ExchangeValue` (pole B, dollars).
This re-consumes the orphan — record that in the module docstring.

```python
class ValueFormAdjunction(BaseModel):   # frozen
    tau: float                # τ from MELTCalculator (DI — protocol, not Default hardwired)
    gamma_basket: float       # from BasketVisibilityCalculator
    # tau_effective = tau * gamma_basket   (computed_field; must equal
    # NationalParameters.tau_effective semantics — parameters.py:232-236)

    def to_labor_hours(self, dollars: float) -> float   # dollars / tau
    def to_money(self, hours: float) -> float           # hours * tau
```

- **τ round-trip law**: `to_money(to_labor_hours(x)) == x` and the
  reverse, Hypothesis over x ∈ [1e-6, 1e12], rel tol 1e-12. The pure
  numeraire map has ZERO defect — Φ is not conversion error.
- **Φ is the wage-form counit defect** — the gap between what the wage
  commands and what the labor produced:
  - `phi_class(w_c: float, v_c: float) -> float` = `(w_c − v_c)/v_c`,
    per-class, signed, dimensionless (the §6 contract form; ValueError
    on v_c \<= 0 — logic fails loud).
  - `phi_hour(wage_hourly: float, tau_effective: float) -> float` =
    `wage_hourly − tau_effective` (dollars/hour; the §9.3 sorting form).
- **Class sorting** (§9.3):
  `class_position_by_phi_hour(wage_hourly, tau_effective, v_reproduction)`
  returns `ClassPosition` — Φ_hour ≥ 0 →
  LABOR_ARISTOCRACY; Φ_hour < 0 ∧ W ≥ V_repro → PROLETARIAT; W < V_repro
  → LUMPENPROLETARIAT (use the existing enum + SUBPROLETARIAT alias,
  `economics/melt/types.py`). This is the FLOW axis; do NOT touch the
  canonical wealth-percentile classifier (stock axis — the two are
  deliberately decoupled, melt/types.py:9-18). Docstring must say both
  axes exist and why.
- **Numeraire invariance laws** (extend the spec-060 suite's style, new
  module `tests/property/dialectics/test_value_form_invariance.py`):
  `phi_class` invariant under uniform currency rescale k (w,v both
  scale); `class_position_by_phi_hour` invariant when wage, τ_eff, and
  V_repro all rescale by k. Hypothesis k ∈ [1e-3, 1e6].

## D2. Φ tri-decomposition (§9.3 — mandatory)

```python
class PhiDecomposition(BaseModel):      # frozen
    phi_unequal_exchange: float   # Emmanuel/Amin — kernel: gamma package
    phi_reproduction: float       # Meillassoux — kernel: lifecycle.compute_shadow_subsidy
    phi_domestic: float           # Fortunati — kernel: gamma_iii + shadow_subsidy
    # total: computed_field = sum of the three. NEVER a stored primitive.
```

Component kernels (reuse, cite in docstrings):

- Φ_UE := `DefaultShadowSubsidyCalculator.compute_phi_imperial`
  (`(1−γ_basket) × Consumption`, gamma/shadow_subsidy.py). The
  `formulas/unequal_exchange.py` four (exchange_ratio → value_transfer)
  are the flow-level cross-check: one law test computes a two-zone
  fixture both ways and asserts the same sign and order of magnitude.
- Φ_repro := aggregated `compute_shadow_subsidy` (per D0).
- Φ_domestic := the value of unpaid care hours, `τ × L_unpaid`.
  **Verify the kernel first**: if `compute_phi_iii` returns
  `(1−γ_III) × L_total × τ` it algebraically equals `τ × L_unpaid`
  (since 1−γ_III = L_unpaid/L_total) — use it directly. If it actually
  returns `(1−γ_III) × L_unpaid × τ` (quadratic in L_unpaid), that is a
  narrower "invisible-fraction" quantity: then Φ_domestic is computed as
  `τ × L_unpaid` in the instance and Φ_III is carried as a separate
  derived report field, NOT the conservation term. Determine which by
  reading the code; record the finding in the docstring.
- **THE conservation law** (§9.3): over a closed fixture,
  `Σ L_performed × τ = Σ V_visible + Σ Φ_shadow` where
  `L_performed = L_paid + L_unpaid`, `V_visible = τ × L_paid`,
  `Φ_shadow = Φ_domestic (+ Φ_repro where the fixture models generations)`. Exact within float tolerance; each component
  independently asserted (kill the "one big sum hides a broken term"
  failure mode). Name: `test_conservation_labor_equals_visible_plus_shadow`.

## D3. `instances/scale.py` — allocate ⊣ aggregate

The recon confirmed the two cited kernels operate on unrelated domains
today (industry-rent→county vs CFS-flow-matrix). The adjunction is the
GENERIC structure both instantiate:

```python
class ScaleAdjunction(BaseModel):       # frozen
    mapping: Mapping[str, str]          # child -> parent (total function)
    shares: Mapping[str, float]         # child -> share of its parent (per-parent sum == 1, validated)

    def allocate(self, by_parent: Mapping[str, float]) -> dict[str, float]
    def aggregate(self, by_child: Mapping[str, float]) -> dict[str, float]
```

- **Adjunction laws** (Hypothesis over random partitions + values):
  `aggregate(allocate(x)) == x` exactly (unit is identity — shares sum
  to 1); `allocate(aggregate(y))` is idempotent (the closure — applying
  it twice equals once). Extensive quantities SUM on aggregate;
  intensive quantities take the share-weighted mean (`aggregate_intensive`
  helper; one law test each).
- **H3 sheaf laws** (§9.1 — name the sheaf condition in the tests):
  `test_sheaf_gluing_conservation` (gluing = conservation: child sums
  equal parent totals) and `test_sheaf_functoriality_h3`
  (`A_{6→5} ∘ A_{7→6} == A_{7→5}` using real `h3` lib parentage over a
  small res-7 cell set — build the two mappings from `h3.cell_to_parent`;
  the composite of the two aggregations equals the direct one). NO
  cohomology, no sheaf class — the tests ARE the sheaf condition.
- **Naturality squares**: docstrings map the audit invariant names
  (`persistence/conservation_audit.py:158-180`) onto squares —
  hex→county, county→state, state→national sums for c/v/s/k are three
  square FAMILIES; one parametrized law test per family using
  ScaleAdjunction over fixture data. (The auditor's 21 names are a
  contract with no-op evaluators today — Phase D does NOT wire
  register_invariant; that is spec-062's program. Say so in the
  docstring.)
- Bind, don't rewrite: a thin test demonstrates
  `DefaultGeographicAggregator.aggregate` (geographic_flow.py:225)
  agrees with `ScaleAdjunction.aggregate` on a shared fixture (the
  existing kernel keeps its API; the instance names its law).

## D4. Accounting becomes categorical — ImperialRentSystem exposure

Computation UNCHANGED. The wages phase of
`engine/systems/economic.py::ImperialRentSystem` (whose per-edge
`value_flow` already exists) additionally writes per-tick node attrs on
each worker class it pays: `w_paid` (total wages incl. super-wage
bonus) and `v_produced` (productivity_value). Extraction phase already
records `value_flow` — leave it. That is the WHOLE change to economic.py;
its tests extend, none change.

`ContradictionSystem._build_graph_inputs` gains
`wage_value_pairs: tuple[tuple[float, float], ...] = ()` on
`GraphInputs` — one `(w_paid, v_produced)` pair per class node carrying
both attrs (skip nodes missing either; inactive-node guard as the other
extractors).

## D5. Catalog rebind — `wage` and `imperial` get true measures

Per the catalog's own docstrings ("Phase D replaces it" / "Phase D
rebinds this"):

- `wage` measure: from WAGES-edge endpoint wealth-asymmetry → the true
  defect over `wage_value_pairs`: gap = mean |w−v|/(w+v), balance =
  mean signed (w−v)/(w+v) (REUSE
  `formulas/contradiction.calculate_wealth_asymmetry_gap/_balance` on
  (v, w) ordered so positive balance = wage exceeds value = the bribe).
  Empty pairs → (0,0) with the old endpoint proxy as documented
  fallback REMOVED (no silent dual path — empty means no data). Update
  the spec poles to the true names: pole_a="value-produced",
  pole_b="price-of-labor-power"; keep key="wage".
- `imperial` measure: from NULL → per-class signed counit defect over
  the same pairs: gap = mean |phi_class| clamped [0,1] via the
  asymmetry form |w−v|/(w+v); balance = mean signed form (positive =
  wages exceed value = imperial-rent inflow = core pole dominant).
  Poles stay core/periphery; unity string updated to cite value_form.
  (wage reads the RELATION per class; imperial reads the same defect as
  the core↔periphery frame — document that they share inputs but carry
  different poles/levels, which C2's coupling graph already encodes as
  `wage feeds capital_labor`; add `wage feeds imperial` to the default
  coupling graph.)
- Consumers to re-verify (do not change semantics): consciousness reads
  wage's rate (crisis-gating — flat during a growing bribe stays
  CORRECT); `ImperialRentSystem._calculate_aggregate_tension` reads
  capital_labor (untouched).
- **Bridged integration test** (new, gated like
  test_bridge_income_circuit.py): 30-tick bridged run — assert the
  imperial opposition's gap becomes NON-ZERO once Φ flows (the
  income-circuit world pays super-wages every tick), its balance sign
  is stable-positive (pacification), and `wage`'s state matches the
  (w, v) accounting rather than endpoint wealth.

## D6. Out of scope (fence — do not wander)

- The four dormant spec-060 "arm" integration tests
  (`test_aggregate_equalities.py` etc.) stay gated: they await a
  transformation-weight instance (Volume III equalization), which is
  NOT Phase D (contract §6/§9.3 silence). Record in value_form.py's
  docstring that the transformation problem lands in a later phase.
- `economics/tick/system/imperial_rent.py` (county Leontief pipeline)
  and its `phi_hour` (production-chain rent per hour — a DIFFERENT
  quantity from D1's wage-defect Φ_hour): read-only. Name the collision
  in the value_form docstring so nobody conflates them.
- `economics/shadow_labor.py` duplication: flag only (D0).
- No GameDefines changes; no new tunables (all inputs are data or DI).

## File plan (Phase D)

| File                                                      | Change                                                                      |
| --------------------------------------------------------- | --------------------------------------------------------------------------- |
| `src/babylon/dialectics/instances/value_form.py`          | NEW — adjunction, phi_class/phi_hour, sorting, PhiDecomposition             |
| `src/babylon/dialectics/instances/scale.py`               | NEW — ScaleAdjunction + intensive/extensive helpers                         |
| `src/babylon/engine/systems/economic.py`                  | wages phase writes w_paid/v_produced node attrs                             |
| `src/babylon/engine/systems/contradiction.py`             | GraphInputs extraction: wage_value_pairs                                    |
| `src/babylon/dialectics/instances/catalog.py`             | wage + imperial measure rebind; `wage feeds imperial` coupling              |
| `tests/unit/dialectics/test_value_form.py`                | NEW — round-trip, phi laws, sorting, tri-decomposition, conservation        |
| `tests/unit/dialectics/test_scale.py`                     | NEW — adjunction laws, sheaf gluing/functoriality (h3), naturality families |
| `tests/property/dialectics/test_value_form_invariance.py` | NEW — numeraire invariance (Hypothesis)                                     |
| `tests/unit/engine/systems/test_economic_accounting.py`   | NEW — w_paid/v_produced exposure                                            |
| `tests/unit/engine/systems/test_contradiction_system.py`  | EXTEND — wage_value_pairs extraction                                        |
| `tests/integration/test_value_form_bridged.py`            | NEW — imperial gap live in the income-circuit world                         |

Commit units: (1) value_form + laws, (2) scale + sheaf laws,
(3) accounting exposure, (4) catalog rebind + bridged test, (5) docs +
margins. TDD each. Mutation probes required on: the tri-decomposition
sum (drop a component), the conservation identity (swap L_paid for
L_total), and aggregate∘allocate identity (skip share normalization).

## Gate (Phase D)

Standing loop (§8) + economics suites
(`poetry run pytest tests/unit/economics tests/integration/economics -q`)

- the new law tests + property suite. All-green bar. Then STOP for
  Fable review before Phase E.

______________________________________________________________________

## Part IV — Phase E design (formerly 06c)

**IMPLEMENTED** (commits `3c5055ff`→`ea0e3661`; see ADR051 for the accepted
re-baseline + the spatial-stddev open item). §E7's RLF simplex constraints
are DEFERRED TO SPEC-071. Storage note (updated 2026-07-03, ADR053): the
§E8-era 7 GB/run problem is solved — canonical runs now delta-persist
(~455k hex rows) and finished sessions are archived+purged via
`mise run sim:archive` — see `08-graph-substrate.md` RESOLVED block.

Fable's binding design for `project/06` §7 + §9.4 (+ §9.1 edge-modes),
written 2026-07-03 from a full surface recon. Delegate: read `project/06`
§8 + §9.1 first, then this file. Two recon corrections that OVERRIDE
anything older you read: (1) the bridge persist wiring EXISTS —
`bridge.py:561` calls `persist_contradiction_fields` (C1.4, hasattr-
guarded to the Postgres runtime); (2) the canonical 520-tick run is
Postgres-backed (`runner.py` opens `BABYLON_PG_DSN`), so
`contradiction_field` rows flow on the re-baseline run and the §7
criterion is checked by querying the table.

## E0. Repoint the dormant field stack (the §5.3 leftover, prerequisite)

Three Feature-002 systems run every tick as no-ops because they
early-return on `services.field_registry is None`
(`contradiction_field.py:71-73`, `field_derivative.py:68-69`,
`edge_transition/_legacy.py:571-573`). The Lawverian rewire makes the
opposition layer their source. Rulings:

- `ContradictionFieldSystem` (@19): drop the `field_registry` gate.
  Per-node `contradiction_fields` are now sourced LOCALLY: for each
  social_class node, field `"exploitation"` = mean fresh `tension` over
  its incident EXPLOITATION/WAGES/TENANCY edges (the per-edge gaps
  ContradictionSystem @18 just wrote), field `"atomization"` = the
  registry's atomization gap (global, uniform per node this phase).
  Keep the 3-tick rolling history machinery unchanged. `field_registry`
  keeps working when present (tests use it); the gate becomes
  "registry OR opposition source", not an early return.
- `FieldDerivativeSystem` (@20): NO source changes needed — it reads
  `contradiction_fields` node attrs + history, which E0 now populates.
  Delete only the `field_registry is None` early-return (its math needs
  no registry). Its `principal_contradiction` graph attr +
  PRINCIPAL_CONTRADICTION_SHIFT event now fire for real; they must NOT
  fight the registry's principal: rename its output attr to
  `principal_field` (grep consumers first — if any consumer reads
  `principal_contradiction` expecting the field-stack semantics, STOP
  and report).
- `EdgeTransitionSystem` (@21): delete the `field_registry` early-return
  (predicates read node attrs, which now exist). The 17-transition
  table is UNCHANGED.
- Fix the position-drift docstrings while there ("Execution Order:
  14/15/16" → 19/20/21 actual).
- Gate for E0 alone: the C1.6 bridged 50-tick integration test still
  green; a new unit test per system proving it acts without a
  field_registry (edge mode actually transitions under a forced
  predicate; derivatives non-zero after two ticks).

## E1. Level instances — `instances/levels.py`

Spatial chain `hex ≺ county ≺ state ≺ nation` and social chain
`individual ≺ community ≺ class ≺ bloc`, as `LevelLattice` instances
(`core/level.py` — `is_resolved_at` = `sheaf_higher(skeleton_lower(x)) == skeleton_lower(x)`).

The ambient object X for BOTH chains is a **keyed field**
`Mapping[str, float]` (entity id → value, e.g. county fips → capital\_
labor edge tension). Operators come from Phase D's `ScaleAdjunction`:

- `skeleton_at(level)` = `allocate(aggregate(x))` with that level's
  mapping/shares — smooths within-parent variation (the closure);
- `sheaf_at(level)` = the same closure at the NEXT level up. Equality
  (`eq`) is elementwise within 1e-9.
- **Resolution semantics (the earn-its-keep computation)**: a field is
  resolved at level L iff smoothing at L+1 no longer changes the
  L-smoothed field — i.e. within-(L+1)-region variance of the
  L-aggregates is zero: the contradiction now LIVES at or above L+1.
  This is a variance decomposition computed by adjunction operators.
  Law test: a field constant within states but differing between states
  is resolved at county, NOT resolved at hex; a uniform field resolves
  everywhere.
- Spatial mappings: hex→county from node `county_fips`; county→state =
  `fips[:2]`; state→nation = constant. Shares: population-weighted
  where populations exist, else uniform (document).
- Social mappings: individual→community from the XGI membership span
  (`H.nodes.memberships(agent_id)` — an agent in multiple communities
  contributes via NORMALIZED shares, 1/k each, keeping allocate
  stochastic); community→class from dominant `SocialRole` of members;
  class→bloc = {core, periphery} assignment. NoCommunityFanOut is
  untouched — the lattice reads the XGI layer, never adds MEMBERSHIP
  edges (Constitution II.7 / VIII.9).
- The `unity`-free `OppositionSpec.level_name` field (Phase A) now gets
  values in the catalog: capital_labor/wage/tenancy = "county",
  atomization = "class", imperial = "bloc". Pure data, one test.

## E2. Fixed-point regimes — one operator, three outcomes (§9.4)

A tick is one Picard iteration `W_{n+1} = T(W_n)`. Phase E ships the
REGIME CLASSIFIER over the opposition trajectory — no engine loop
changes, no convergence iteration inside a tick (the dormant package
never had one either; recon item 10):

```python
# dialectics/core/regime.py
Regime = Literal["reproduction", "crisis", "sublation"]
def classify_regime(
    states: Sequence[OppositionState],          # this tick, principal marked
    lattice: LevelLattice[Mapping[str, float]] | None,
    field: Mapping[str, float],                 # principal's per-entity gaps
    level_index: int,                           # principal's declared level
    *, rate_epsilon: float,                     # |rate| below = converged
) -> Regime
```

- **reproduction**: principal `|rate| <= rate_epsilon` — the
  self-consistency search converged; the social form reproduces.
- **crisis**: principal `rate > rate_epsilon` (gap developing) and the
  field NOT resolved at the next level — divergence within the level.
  The existing RUPTURE gate (`gap > threshold AND rate > 0`) stays
  byte-identical as the crisis THRESHOLD event: rupture is this regime's
  boiling point, not a separate mechanism.
- **sublation**: gap developing AND `lattice.aufhebung_of` (at
  `level_index`, probing `[field]`) returns a level — the contradiction
  has moved up: it is resolved-at-a-higher-level while diverging below. Publish the NEW
  `EventType.LEVEL_TRANSITION` (add to the enum — 70 → 71 members)
  with payload {opposition, from_level, to_level, gap, rate}.

Wiring: `ContradictionSystem._step_registry` computes the regime after
`_maybe_rupture` (it already has states; build `field` from per-county
capital_labor edge tensions — the same extraction the C1.6 bridged test
uses), stashes `graph attr "dialectical_regime"`, and publishes
LEVEL_TRANSITION on the sublation branch. `rate_epsilon` and the
lattice wiring ship via `services` defaults (`defines.tension. regime_rate_epsilon`, default 1e-4 — ONE new define, documented).
EdgeTransitionSystem's Aufhebung hook: a new `PredicateCondition`
metric `"regime"` usable in transitions (data only — no new transition
added to the 17 this phase; one unit test proves the predicate
evaluates).

## E3. Edge modes as a presented category (§9.1)

The 17 `EdgeModeTransition`s + the ANTAGONISTIC self-loop ARE the
presented category's generating morphisms. No new class. Law tests over
`_TRANSITION_MAP`/`_VALID_TRANSITIONS` as data:

- `test_no_direct_extractive_to_solidaristic` — absent from the 17;
- `test_extractive_reaches_solidaristic_through_transactional` — a path
  exists and every such path transits TRANSACTIONAL (BFS over the
  transition graph, bounded by 5 nodes);
- `test_all_transitions_endpoints_are_edge_modes` (closure of the
  presentation).

## E4. The fractal check (§9.4 — honesty clause)

Test fixture (extends C2's four-node recursion): nation-level imperial
opposition nests {Core,Periphery}; each zone nests its own
capital_labor. Assert: (a) the SAME {Core,Periphery}×{B,P} structure is
expressible at state zoom by rebinding the same specs over a state's
field slice (the lattice's allocate gives the slice); (b) lumpen
appears only on zoom-in: at class level the social lattice's aggregate
folds LUMPENPROLETARIAT into the proletariat pole (population-weighted),
at individual/community zoom the distinct pole is visible. If (b) is
NOT cleanly expressible with the current operators, the test documents
the failure with `pytest.mark.xfail(reason=...)` and the ADR says so
explicitly — per the contract: "say so explicitly rather than fake it."

## E5. Induced-crisis integration test

`tests/integration/test_induced_crisis.py`, gated like the income-
circuit suite. In the bridged income-circuit world: run ~20 ticks of
pacified hegemony (regime == reproduction), then force the crisis —
drain the rent pool / cut the wage flow (set the economy's rent pool to
~0 via the graph metadata the wages phase reads; if there is no clean
lever, use the SUPERWAGE_CRISIS path by exhausting the pool with a tiny
`extraction_efficiency`) — then assert over the following ticks:
(a) wage/capital_labor gap grows (rate > 0 sustained); (b) principal
contradiction SHIFTS (the fast-developing one takes over — assert the
registry's principal key changes); (c) at least one RUPTURE or
LEVEL_TRANSITION event fires. STOP-condition applies: if inducing the
crisis requires touching StruggleSystem's severing logic or the
consciousness gating, stop and report.

## E6. Grundrisse fixed-point test (§9.4 port)

Extend `tests/integration/test_grundrisse_cycle.py` (do not rewrite)
with `TestFixedPointReading`: the 4-moment cycle driven to its
repeating orbit is a fixed point of the COMPOSITE map T⁴ — assert
regime == "reproduction" on the orbit (gaps repeat within epsilon
tick-over-tick at the same moment across turns); a wage-cut
perturbation breaks the orbit → regime == "crisis". (The dormant
package's only fixed-point content was the previous-tick read pattern —
already carried by the graph-attr snapshot; the regime classifier is
the NEW machinery §9.4 demands.)

## E7. TopologyMonitor + consumers (honesty rulings)

- TopologyMonitor has ZERO production call sites (recon) — the headless
  runner has no observer path. Ruling: the PRODUCTION Aufhebung signal
  is the engine-side LEVEL_TRANSITION event (E2), persisted through the
  normal event pipeline. The monitor gains one small hook —
  `classify_phase` may take an optional `lattice_resolved: bool` that
  promotes transitional→solid when the social field resolves at class
  level — exercised in its existing test suites only. Wiring the
  monitor into the runner is OUT of scope; the ADR records this
  honestly ("TopologyMonitor remains a facade/test observer").
- RLF simplex constraints (§9.4): NOT implemented here — they are
  spec-071's. Record them in the ADR's handoff section verbatim from
  §9.4 (f→r ε-gate breaking detailed balance; entropy diagnostic-only;
  assimilation_ratio; balance∈[−1,1] convention already honored).

## E8. Re-baseline + closing docs

1. All gates green FIRST (below).
1. Launch the canonical run **nohup-detached** (harness background
   tasks die on compaction):
   `nohup mise run sim:e2e-michigan > reports/sim-runs/phase-e-rebaseline.log 2>&1 &`
   — expect ~52 min. Poll the log; on completion verify and RECORD:
   (a) `terminal_state.counties_alive == 83 == counties_with_population`;
   (b) `contradiction_field` rows > 0 for the run's session (psql on
   port 5433, `babylon_test`);
   (c) stddev of per-county capital_labor edge tension > 0 at t300
   (from the trace/baseline artifacts);
   (d) `max_tension < 1.0` in the new baseline (non-saturating gaps —
   the OLD baseline's pinned 1.0 is the artifact we are killing).
   Commit the refreshed `tests/baselines/michigan-e2e.json` with these
   four numbers in the commit body. If ANY criterion fails, STOP —
   report with the numbers; do not commit a failing baseline.
1. ADR `ai-docs/decisions/ADR051_lawverian_dialectics_refactor.yaml`
   (+ index.yaml entry, meta.version bump): the whole refactor A→E —
   registry replaces field_registry+tension ratchet; C2 composition/
   coupling/lineage; D adjunctions + Φ tri-decomposition; E levels/
   regimes/LEVEL_TRANSITION; deferrals (observation-relativity frames,
   RLF→071, TopologyMonitor unwired, transformation problem).
1. `ai-docs/state.yaml`: meta.version bump + sprint note.
1. Root `CLAUDE.md`: pipeline-table note — position 18's description
   already updated in C1; add a one-line note that 19-21 are live
   (no longer field_registry-gated) and events gained LEVEL_TRANSITION.
1. `project/01` + `project/06`: completion notes (§7 checked off).

## File plan (Phase E)

| File                                                    | Change                                    |
| ------------------------------------------------------- | ----------------------------------------- |
| `src/babylon/engine/systems/contradiction_field.py`     | E0 repoint (edge-tension source)          |
| `src/babylon/engine/systems/field_derivative.py`        | E0 gate removal + principal_field rename  |
| `src/babylon/engine/systems/edge_transition/_legacy.py` | E0 gate removal + regime predicate metric |
| `src/babylon/dialectics/instances/levels.py`            | NEW — spatial + social lattices           |
| `src/babylon/dialectics/core/regime.py`                 | NEW — classify_regime                     |
| `src/babylon/engine/systems/contradiction.py`           | E2 wiring (regime + LEVEL_TRANSITION)     |
| `src/babylon/models/enums/events.py`                    | +LEVEL_TRANSITION                         |
| `src/babylon/config/defines/...`                        | +tension.regime_rate_epsilon              |
| `src/babylon/dialectics/instances/catalog.py`           | level_name values                         |
| tests                                                   | per E0-E6; extend, never rewrite          |

Commit units: (1) E0 repoint, (2) E1 levels, (3) E2 regimes +
LEVEL_TRANSITION, (4) E3+E4 category laws + fractal, (5) E5+E6
crisis/fixed-point tests, (6) E8 re-baseline + ADR + docs. Mutation
probes required on: the resolution equality (mutant: sheaf==sheaf
instead of sheaf(skeleton)==skeleton), the crisis/sublation branch
order (mutant: sublation checked first unconditionally), and the E0
edge-tension mean (mutant: max instead of mean).

## Gate (Phase E)

Standing four (§8) + `tests/integration/test_grundrisse_cycle.py`,
`test_induced_crisis.py`, income-circuit — all green BEFORE the
re-baseline step. The re-baseline is the LAST act. Then STOP: Fable
review, then the owner's break.
