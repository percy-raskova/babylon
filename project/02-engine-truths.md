# 02 — Engine Truths (2026-07-02 forensics)

Hard-won knowledge from a full-day root-cause investigation. Read before
touching the engine, the bridge, or any canonical baseline. Every claim here
was verified empirically in-session; commits referenced are on
`fix/web-local-play-wireup`.

## 1. The bridged canonical world — what it actually is

`WorldStateBridge.hydrate_initial` (`src/babylon/engine/headless_runner/bridge.py`)
builds, per county in scope (sorted-FIPS index `i`):

- **Entities**: worker `C{i:03d}` (population 85) + bourgeoisie `C{i+500:03d}`
  (population 15). Since `23cfacc2` the worker is created by
  `create_labor_aristocracy` (`src/babylon/engine/factories.py`):
  role=LABOR_ARISTOCRACY, wealth 0.8 (> subsistence 0.3), organization 0.05,
  repression 0.3. Both classes get `BASELINE_IDEOLOGY`
  (cc=0.1, ni=0.5 → r=0.05, l=0.50, f=0.45 per ADR043).
- **Territory** `T{i:03d}` (since `b758a4fa`): model-default biocapacity
  100/100, regeneration 0.02 — the metabolic base.
- **Edges** (3 per county):
  - EXPLOITATION worker→bourgeois (tension 0.1) — ImperialRentSystem's path.
  - TENANCY worker→territory — ProductionSystem's precondition for ANY
    production/wages.
  - WAGES bourgeois→worker — `_find_employer` resolves the LA's employer
    through this; the wages phase pays productivity + super-wage bonus.
- Hex economics (v/c/s/k per hex) hydrate separately into Postgres and are
  **static per year by design** — entity dynamics do NOT feed back into hex v.

## 2. The closed-drain extinction (fixed; how it hid for 2 months)

Symptom: every real-systems canonical run since spec-066 suffered statewide
demographic extinction at tick ~68–70. Diagnosis chain (all verified):

- ProductionSystem pays ONLY workers holding a TENANCY edge; spec-065's
  hydration deliberately seeded no territories ("first cut"). With no income,
  both classes burned fixed endowments: worker dead ~t42, bourgeois
  (10.0 wealth − 0.15/tick vitality) dead ~t67–70.
- It hid because (a) no gate asserted survival, (b) trace consciousness
  columns silently go NULL when a county's population is 0 (the bridge only
  writes consciousness rows while population > 0), and (c) the only "healthy"
  520-tick comparator in Postgres (session `04b4e02c…`) was a **no-op-era
  run**: its p_acq/p_rev are 0 and ideology frozen at the same three values
  for all 520 ticks. Treat any comparator with frozen values as invalid.
- Spec-070 and spec-086 were both exonerated by controlled experiment:
  pre-070 code × post-086 data reproduced the identical extinction; pre-086
  data (restored from the `fact_qcew_annual__pre_086` backup into a temp
  SQLite via `VACUUM INTO` + table rename) reproduced identical trajectories.

**Guard now in place** (`02ad41b2`): `terminal_state.counties_with_population`
(counted via non-NULL ideology in the trace view at the terminal tick) must
equal `counties_alive`; `tools/regression_test.py compare-bundle` fails
otherwise. Never remove this check.

## 3. The tick-1 revolt (fixed; the class-character lesson)

After the income circuit landed, Φ still transferred exactly once: per-system
edge probes showed **StruggleSystem severing the EXPLOITATION edge at tick 1**.
Root cause: `struggle.py`'s Terminal-Crisis rule fires revolt when
P(S|R) > P(S|A) **for PERIPHERY_PROLETARIAT** — and the bridge hydrated US
county workers as periphery proletariat at starvation wealth. The engine
correctly executed periphery logic on the imperial core.

Fix (`23cfacc2`): core county workers are **LABOR_ARISTOCRACY** (per Cope/
Amin/Fundamental Theorem). This activates the already-built Amin/Wallerstein
machinery in `src/babylon/engine/systems/economic.py`: LA production routes
to the employer (ProductionSystem `_EMPLOYED_PRODUCER_ROLES`), the wages
phase pays back productivity + super-wage bonus from the rent pool, and
SUPERWAGE_CRISIS fires when the pool exhausts.

**Verified 80-tick vitals** (1-county probe): Φ flows every tick growing
0.008→0.78; bourgeois wealth 9.86→35.07; worker population stable at 72;
P(S|A) 0.061→0.995 while P(S|R) holds 0.167. Hegemony holds mathematically;
rupture is reserved for rent-pool exhaustion (~year 43, beyond the 10-year
canonical window).

## 4. Consciousness is crisis-gated — flat is CORRECT during hegemony

`ConsciousnessSystem` (`src/babylon/engine/systems/ideology.py`, pipeline
position 17) calls `compute_agitation_delta`
(`src/babylon/formulas/consciousness_routing.py`) with agitation generated
ONLY from: rising exploitation rate, FALLING Φ (wage/wealth decline), or
rising reproductive visibility. While the bribe grows, Δagitation = 0 and
consciousness stays at baseline 0.1. **Do not "fix" flat consciousness during
the pacified phase** — it is the Fundamental Theorem holding. Drift engages
on material crisis (TRPF decay of the rent pool, or struggle cutting wages).

## 5. Diagnostic playbook (reusable probes)

The single most effective tool from the forensics: a 1-county in-process
harness (~40 s hydration, then ~0.2 s/tick). Pattern:

```python
# poetry run python - <<'EOF' ... (full working example in session transcript;
# reconstruct from these calls — all signatures verified 2026-07-02)
from psycopg_pool import ConnectionPool
from babylon.config.defines import GameDefines
from babylon.persistence import PostgresRuntime
from babylon.persistence.postgres_initialization import initialize_session
from babylon.engine.headless_runner.bridge import WorldStateBridge
from babylon.engine.headless_runner.runner import EventCapture
from babylon.engine.event_bus import EventBus
from babylon.economics.boundary_flow_register import BoundaryFlowRegister
from babylon.persistence.conservation_audit import ConservationAuditor
from babylon.engine.simulation_engine import SimulationEngine, _DEFAULT_SYSTEMS
from babylon.engine.services import ServiceContainer
from babylon.engine.context import TickContext          # NOTE: engine.context
# pool = ConnectionPool(DSN); runtime = PostgresRuntime(pool=pool)
# initialize_session(session_id=uuid4(), sqlite_path=Path(...), runtime=...,
#     defines=GameDefines.load_default(), start_year=2010,
#     scenario_length_years=2, counties=["26163"], hex_hydration_counties={"26163"})
# world = WorldStateBridge(...).hydrate_initial(session_id=..., scope_fips={"26163"},
#     event_capture=EventCapture(), total_ticks=N, start_year=2010, sqlite_path=...)
# g = world.to_graph(); services = ServiceContainer.create(defines=defines)
# engine = SimulationEngine(list(_DEFAULT_SYSTEMS))
# for tick in range(1, N): engine.run_tick(g, services, TickContext(tick=tick))
```

Three probe variants that cracked the case — run systems ONE AT A TIME inside
a tick and diff state between `system.step(...)` calls:

1. **Per-system attribute diff** (who changes `population`/`wealth` on node X).
1. **Per-system edge diff** (who adds/removes/retypes edges) — caught the
   tick-1 severing.
1. **Trajectory print** every K ticks (population, wealth, Φ=edge value_flow,
   p_acq/p_rev, cc/agitation) — caught the closed drain and proved the fix.

Integration-test form of the same harness:
`tests/integration/test_bridge_income_circuit.py` (9 tests; module-scoped
fixture; skip-gated on Postgres + the live SQLite).

## 5b. Landmines found in claude-mem history (2026-07-02 review)

- **DecompositionSystem enforcer gap**: position 11 in the default pipeline
  implements the LA terminal arc (theory.yaml: when super-wages fail, LA
  decomposes ~30% CARCERAL_ENFORCER / ~70% internal proletariat via
  `defines.carceral.n_fraction`). It resolves the enforcer by role lookup
  (`_find_entity_by_role`, role CARCERAL_ENFORCER, include_inactive=True).
  **The bridge seeds no such entity**, so the enforcer branch no-ops
  (returns None) when decomposition fires. Harmless
  inside the 10-year canonical (rent exhaustion ≈ year 43) but MUST be fixed
  before any spec that induces SUPERWAGE_CRISIS (071's crisis tests, 074,
  081). Fix shape: seed an inactive carceral-enforcer entity per county, or
  teach the system to create one.
- **Dormant dialectics layer**: `src/babylon/engine/dialectics/` is a full
  parallel framework (24 Dialectic classes mapping Capital I–III, sublation
  rules, World.tick(), invariants) — NOT referenced by `simulation_engine`
  or the headless runner. It is a separate abstraction tier, currently
  unwired. Do not assume it runs; do not wire it casually (that's a spec).
- **Intended full arc length**: theory.yaml pins the TRPF multiplier floor
  at 10% after ~1,800 ticks (~35 years) — the 520-tick canonical is only the
  opening decade BY DESIGN. Long-arc behaviors (decomposition, superwage
  crisis, carceral equilibrium) need induced-crisis tests or longer runs.
- **SOLIDARITY transmits periphery→core** (proletarian internationalism) —
  and the bridged world has no periphery entities and no SOLIDARITY edges
  (player-verb-created per Constitution III.5). Consciousness routing to
  revolution therefore requires player action or spec-worked periphery
  presence; this is intended.

## 6. Misc engine facts that cost hours to learn

- `TickContext` lives in `babylon.engine.context`, kwarg is `tick=`.
- `PostgresRuntime` has no `from_env`; construct with
  `PostgresRuntime(pool=ConnectionPool(dsn))`.
- `initialize_session` requires `sqlite_path` as `Path`, not `str`.
- Entity ids must match `^C[0-9]{3}$`; territory ids `^T[0-9]{3}$` (or h3 hex).
- Factories: `create_proletariat` / `create_labor_aristocracy` /
  `create_bourgeoisie` in `src/babylon/engine/factories.py`; ID constants in
  `src/babylon/models/entity_registry.py`.
- Bundle `summary.json` events carry their type under `details.type`
  (top-level `event_type` is the literal string `Event`).
- `summary.terminal_state.total_v/c/s/k` come from HEX economics (static per
  year); entity wealth is not in them — so entity-dynamics changes do NOT
  shift the 5-tick gate's `total_v`.
- The extraction formula:
  `Φ/tick = (extraction_efficiency/52) × trpf_mult × worker_wealth × (1 − cc)`;
  defaults: extraction_efficiency 0.8, trpf_coefficient
  0.0005, floor 0.1.
- SUPERWAGE_CRISIS ≈ tick 2,236 (year ~43) at current constants — by design
  beyond the 520-tick canonical.
- 25 default systems run in materialist-causality order (list:
  `simulation_engine._DEFAULT_SYSTEMS`; docs in root `CLAUDE.md`).
- Systems mutate the graph in place; access via `graph.nodes[id][attr]`.
- `mise run test:summary` prints the latest test run one-screen summary.
