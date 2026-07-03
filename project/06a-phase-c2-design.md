# 06a — Phase C2 design (composition + structure)

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
