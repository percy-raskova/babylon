# 06 — Lawverian Dialectics Refactor (design doc + delegation contract)

**Status**: Phase A in progress (2026-07-02). Owner decisions: direct refactor
(no speckit), re-ground in place, executable + law-tested category theory,
Fable designs/reviews + delegated implementation. Branch:
`refactor/lawverian-dialectics` (off `fix/web-local-play-wireup`).
Approved plan archived at `.claude/plans/glimmering-tumbling-hinton.md`
(session-scoped) — THIS file is the durable contract.

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
