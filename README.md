# Babylon - The Fall of America

A geopolitical simulation engine — and now a playable web game being hardened —
modeling the collapse of American hegemony through Marxist-Leninist-Maoist
Third Worldist (MLM-TW) theory.

**Mantra:** *Graph + Math = History*

## What Is This?

Babylon models class struggle as a deterministic output of material conditions
within a compact topological phase space. It simulates imperial rent extraction,
consciousness drift, solidarity transmission, and revolutionary rupture — from a
two-node teaching scenario up to county-scale national runs — and exposes it as
a Django + React web game where the player acts through an organization inside
the simulation.

The simulation runs locally without external servers, using the **Embedded
Trinity** architecture:

- **The Ledger** (PostgreSQL runtime + Pydantic) — Rigid material state. Runtime
  simulation state lives in PostgreSQL (spec-037); a read-only SQLite reference
  database (`marxist-data-3NF.sqlite`) supplies QCEW/BEA/Census/TIGER source data
- **The Topology** (rustworkx via `BabylonGraph`) — Fluid relational state;
  `to_graph()`/`from_graph()` bridge Pydantic ↔ graph (Amendment L, ADR052 —
  byte-identical determinism; NetworkX was removed)
- **The Archive** (pgvector) — Semantic history for AI narrative; AI observes
  state, never controls mechanics

**Architecture Principle:** State is pure data. Engine is pure transformation.
They never mix.

## Where the project is right now (July 2026)

The full game surface exists: the 26-system engine, a React/Django web app (map,
verbs, intel, wire, chronicle, objectives), an Observatory debug dashboard, trade
blocs, and county-scale national runs. **Program 09** (specs 071–105) built that
surface and merged to `dev` on 2026-07-06.

The first real end-to-end playtest (2026-07-07) then found the core loop broken
at several junctions, and a whole-repo review found silent failures behind it.
The active work is the **Loud Machine remediation program**: fix everything
found, and wire the system so failures are loud instead of silent. Several of
the blockers are already fixed and merged (map projection, live verb pipeline,
loud scenario seeding, re-armed test guardrails); the rest is in flight.

**Catch up in five minutes:** [`project/`](project/) is the project-management
one-stop shop — start at
[`project/execution/PROGRESS_REPORT-2026-07-08.md`](project/execution/PROGRESS_REPORT-2026-07-08.md)
(where things stand) and
[`project/execution/REMEDIATION_PLAN.md`](project/execution/REMEDIATION_PLAN.md)
(the ratified plan). The authority chain and reading order live in
[`project/README.md`](project/README.md).

## Quick Start

```bash
# One-shot fresh-clone bootstrap: toolchain + deps + hooks + tuned Postgres 16 + schema
mise trust
mise run setup

# Verify your install with the self-contained smoke test
mise run sim:run

# Run the fast CI gate (lint + format + typecheck + unit tests)
mise run check

# Start the web game (Django :8000 + Vite :5173 as background daemons)
mise run web:dev
```

**Requirements:** [mise](https://mise.jdx.dev) (it provisions Python 3.12 and
Poetry for you) and Docker (for the tuned Postgres 16 compose stack). New to the
project? See [SETUP_GUIDE.md](SETUP_GUIDE.md) for a beginner-friendly,
OS-by-OS walkthrough.

## Project Structure

```
src/babylon/
├── engine/              # Simulation engine (step function, 26 systems, event bus, observers)
│   ├── systems/         # Modular Systems (production, ideology, survival, territory, sovereignty, ...)
│   ├── headless_runner/ # Postgres-backed full-scale runs (Michigan / national)
│   └── formula_registry.py  # Hot-swappable formula dispatch
├── formulas/            # 19 formula modules covering the MLM-TW mathematical core
├── models/              # Pydantic entities (SocialClass, Territory, Sovereign, WorldState)
├── economics/           # Imperial-rent tensor + Leontief pipeline, gamma visibility, circulation
├── persistence/         # PostgreSQL runtime, migrations, pgvector store, Parquet archival
├── dialectics/          # Executable contradiction layer (ADR051: oppositions, levels, regime)
├── ooda/                # Organization decision layer (actions, costs, effects)
├── config/              # GameDefines — every tunable coefficient
└── data/game/           # JSON entity/seed definitions (factions, sovereigns, personas)

web/                     # The game itself
├── game/                # Django app: API, engine bridge, session persistence
├── frontend/            # React 19 + Zustand + deck.gl map UI (Vite)
├── observatory/         # Read-only debug/analysis dashboard
└── babylon_web/         # Django project settings

project/                 # Project management one-stop shop (plans, assessments, progress)
ai/                 # Machine-readable YAML docs for AI agents (architecture, ADRs, state)
specs/                   # Feature specifications per branch (001-105+)
tests/                   # unit / integration / scenarios / property / contract
tools/                   # Simulation lab: traces, sweeps, tuning, QA gates
docs/                    # Sphinx API documentation
```

## Engine Systems

The simulation engine runs **26 modular Systems** in strict materialist-causality
order each tick (source of truth: `_DEFAULT_SYSTEMS` in
[`simulation_engine.py`](src/babylon/engine/simulation_engine.py)). They fall
into three phases:

```
step(WorldState, SimulationConfig) -> WorldState  ──►  SimulationEngine.run_tick(graph, services, context)

Material Base   Vitality · Territory · Substrate · Production · TickDynamics ·
                ReserveArmy · Community · Lifecycle · Solidarity · ImperialRent ·
                Dispossession · Decomposition · ControlRatio · Metabolism
Action Phase    OODA
Consequences    FactionInfluence · Survival · Struggle · Consciousness ·
                FascistFaction · Sovereignty · Contradiction · ContradictionField ·
                FieldDerivative · CollapseTransition · EdgeTransition
```

The base produces material conditions, organizations observe and act, and the
consequences (survival calculus, consciousness drift, contradiction fields,
sovereign collapse) follow. See [`CLAUDE.md`](CLAUDE.md) for per-system
annotations.

**Key components:**

| File                                      | Purpose                                                    |
| ----------------------------------------- | ---------------------------------------------------------- |
| `src/babylon/engine/simulation_engine.py` | Orchestrates all Systems                                   |
| `src/babylon/engine/services.py`          | ServiceContainer (dependency injection)                    |
| `src/babylon/engine/event_bus.py`         | Publish/subscribe events (82 EventTypes)                   |
| `src/babylon/engine/formula_registry.py`  | Hot-swappable formula dispatch                             |
| `src/babylon/engine/topology_monitor.py`  | Phase transition detection via percolation                 |
| `src/babylon/engine/observers/`           | `SessionRecorder`, `EndgameDetector` (5 terminal outcomes) |
| `src/babylon/config/defines/`             | `GameDefines` — all tunable coefficients                   |
| `web/game/engine_bridge.py`               | The web game's bridge into the engine                      |

## Formula System

19 formula modules in `src/babylon/formulas/` (selected highlights below; see
the directory for the full set, including `balkanization.py`, `reactionary.py`,
`consciousness_routing.py`, and `state_ai.py`):

| Module                   | Theory                                                     |
| ------------------------ | ---------------------------------------------------------- |
| `fundamental_theorem.py` | Imperial rent, labor aristocracy, consciousness drift      |
| `survival_calculus.py`   | P(S\|A), P(S\|R), crossover threshold, loss aversion       |
| `unequal_exchange.py`    | Exchange ratios, exploitation rate, Prebisch-Singer effect |
| `solidarity.py`          | Solidarity transmission                                    |
| `consciousness.py`       | Ternary consciousness (r/l/f simplex)                      |
| `balkanization.py`       | Sovereign collapse, secession, red-settler trap            |
| `reactionary.py`         | Fascist pull, defection, spontaneous riot risk             |
| `metabolic_rift.py`      | Biocapacity delta (ΔB = R − E×η), overshoot ratio          |
| `class_dynamics.py`      | Wealth flow, class-dynamics derivatives                    |
| `community.py`           | Community-level consciousness and solidarity               |
| `curvature.py`           | Topological curvature (Ollivier-Ricci / Wasserstein-1)     |
| `trpf.py`                | Tendency of the rate of profit to fall                     |
| `lifecycle.py`           | D–P–D′ lifecycle circuit, legitimation index               |

The imperial-rent tensor mathematics (value tensors, Leontief pipeline, gamma
visibility) lives in `src/babylon/domain/economics/`.

## Mathematical Core

**Fundamental Theorem:** Revolution in Core impossible if W_c > V_c (core wages > value produced). The difference is Imperial Rent (Φ).

**Survival Calculus:**

- P(S|A) = Sigmoid(Wealth − Subsistence) — survival by acquiescence
- P(S|R) = Organization / Repression — survival by revolution
- Rupture occurs when P(S|R) > P(S|A)

**Bifurcation:** When wages fall, agitation energy routes to Fascism (+1 ideology) or Revolution (−1) based on SOLIDARITY edge presence.

**Metabolic Rift:** ΔB = R − (E × η); Overshoot = C/B; O > 1 triggers `ECOLOGICAL_OVERSHOOT` event.

## Development Commands

```bash
# Setup
mise run setup              # Fresh clone: everything
poetry install && poetry run pre-commit install   # Piecemeal alternative

# CI gate (lint + format + typecheck + unit tests)
mise run check

# Testing (all test:* tasks write machine-readable reports to reports/test-results/)
mise run test:unit          # Fast unit tests only
mise run test:int           # Integration tests
mise run test:scenario      # Full scenario arcs (slow)
mise run test:all           # All non-AI tests (10,700+ collected)
mise run test:cov           # With coverage report

# Quality
mise run lint               # Ruff linter
mise run typecheck          # MyPy strict mode
mise run qa:audit           # Simulation health check (3 scenarios)
mise run qa:verify          # Formula correctness verification
mise run qa:storage-budget  # Storage regression gate (rows/tick vs baseline)

# Web game
mise run web:dev            # Django + Vite as background daemons
mise run web:status         # Server status
mise run web:test           # Frontend tests (Vitest)
mise run web:check          # Frontend quality gate (tsc + eslint + prettier + vitest)

# Agent/dev ergonomics
mise run commit -- "type(scope): msg"   # Hook-safe commit
mise run sim:status                     # Canonical-run status (tick, DB size, liveness)
```

For specific tests:

```bash
poetry run pytest tests/unit/test_foo.py::test_specific
poetry run pytest -k "test_name_pattern"
poetry run pytest -m "math or ledger"     # by marker
```

## Simulation Lab

The `tools/` directory provides analysis, optimization, and QA tooling:

```bash
# Trace and sweep
mise run sim:trace                        # Time-series CSV + JSON
mise run sim:sweep                        # 1D parameter sweep
mise run sim:monte-carlo 1000 42          # Monte Carlo uncertainty quantification

# Parameter tuning
mise run tune:morris 20                   # Fast sensitivity screening
mise run tune:sobol 512                   # Sobol variance decomposition
mise run tune:optuna 200                  # Bayesian optimization (TPE)
mise run tune:landscape p1 r1 p2 r2       # 2D grid search

# QA
mise run qa:regression                    # Baseline comparison (CI)
mise run qa:regression-generate           # New baselines after intentional changes
mise run qa:schemas                       # JSON schema validation
mise run qa:security                      # Dependency security audit

# Full-scale runs (Postgres-backed)
mise run sim:e2e-bg                       # Daemonized 520-tick canonical run
mise run sim:archive -- list              # Parquet archival lifecycle (spec-088)
```

## Testing Standards

Pytest markers (enforced — unknown markers are a collection error):

```
@pytest.mark.math        # Deterministic formulas (fast, pure)
@pytest.mark.ledger      # Economic/political state
@pytest.mark.topology    # Graph/network operations
@pytest.mark.integration # Database/Postgres (I/O bound)
@pytest.mark.ai          # AI/RAG evaluation (slow, non-deterministic; auto-applied to tests/unit/ai/)
@pytest.mark.contract    # Contract tests pinning cross-boundary interfaces
@pytest.mark.red_phase   # TDD RED phase (reserved; no active red_phase tests — retired 2026-07-08)
```

Test constants are centralized in `tests/constants.py` (see ADR031). All code
follows strict TDD: Red → Green → Refactor. Determinism is constitutional
(III.7): seeded RNG and tick-derived timestamps, verified by an in-process
determinism gate.

## Contributing

This project uses the [Benevolent Dictator](https://producingoss.com/en/benevolent-dictator.html) governance model. Persephone Raskova (@percy-raskova) has final authority on merges to `main`.

| Resource                           | Description                             |
| ---------------------------------- | --------------------------------------- |
| [SETUP_GUIDE.md](SETUP_GUIDE.md)   | Step-by-step setup for new contributors |
| [CONTRIBUTORS.md](CONTRIBUTORS.md) | Governance model and git workflow       |
| [CLAUDE.md](CLAUDE.md)             | Coding standards, architecture, gotchas |

```bash
git checkout dev
git checkout -b feature/your-feature
# Make changes, PR to dev
```

## Documentation

| Location                         | Content                                                               |
| -------------------------------- | --------------------------------------------------------------------- |
| [`project/`](project/)           | Project management: plans, progress reports, assessments, owner queue |
| [`ai/`](ai/)                     | Machine-readable YAML docs for AI agents (architecture, ADRs)         |
| [`ai/state.yaml`](ai/state.yaml) | Project status — read its `truth_status` banner first                 |
| [`ai/decisions/`](ai/decisions/) | Architecture Decision Records (one YAML per ADR)                      |
| [`specs/`](specs/)               | Per-feature specifications with verified task ledgers                 |
| [`docs/`](docs/)                 | Sphinx API documentation (`mise run docs:live`)                       |

## License

MIT License — see [LICENSE](LICENSE).

______________________________________________________________________

**Built With**

```
Claude (Opus 4.5 → Fable 5) 🤝 Autistic Trans Woman = Coherent MLM-TW Simulation
```
