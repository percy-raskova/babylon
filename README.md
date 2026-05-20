# Babylon - The Fall of America

A geopolitical simulation engine modeling the collapse of American hegemony through Marxist-Leninist-Maoist Third Worldist (MLM-TW) theory.

**Mantra:** *Graph + Math = History*

## What Is This?

Babylon models class struggle as a deterministic output of material conditions within a compact topological phase space. It simulates imperial rent extraction, consciousness drift, solidarity transmission, and revolutionary rupture using NetworkX graphs and Pydantic-validated state.

The simulation runs locally without external servers, using the **Embedded Trinity** architecture:

- **The Ledger** (PostgreSQL runtime + Pydantic) — Rigid material state. Runtime simulation state lives in PostgreSQL (spec-037); a read-only SQLite reference database (`marxist-data-3NF.sqlite`) supplies QCEW/BEA/Census source data
- **The Topology** (NetworkX/GraphProtocol) — Fluid relational state; `to_graph()`/`from_graph()` bridge Pydantic ↔ DiGraph
- **The Archive** (pgvector) — Semantic history for AI narrative; AI observes state, never controls mechanics (ChromaDB was replaced by pgvector in spec-037)

**Architecture Principle:** State is pure data. Engine is pure transformation. They never mix.

## Quick Start

```bash
# Install the toolchain (Python 3.12 + Poetry) and dependencies
mise trust
mise install
mise run install

# Verify your install with the self-contained smoke test
mise run sim:run

# Run the full test suite (9,500+ tests)
mise run test:all
```

**Requirements:** [mise](https://mise.jdx.dev) (it provisions Python 3.12 and
Poetry for you). New to the project? See [SETUP_GUIDE.md](SETUP_GUIDE.md) for a
beginner-friendly, OS-by-OS walkthrough.

## Project Structure

```
src/babylon/
├── engine/              # Simulation engine (step function, systems, event bus, observers)
│   ├── systems/         # 25 modular Systems (economic, ideology, survival, territory, sovereignty, ...)
│   ├── headless_runner/ # Postgres-backed full-scale run (sim:e2e-michigan)
│   └── formula_registry.py  # Hot-swappable formula dispatch
├── formulas/            # Mathematical formulas (18 modules covering all MLM-TW theory)
├── models/              # Pydantic entities (SocialClass, Territory, WorldState)
├── persistence/         # PostgreSQL runtime + pgvector store
├── rag/                 # Retrieval pipeline over pgvector (semantic history)
├── config/              # GameDefines, logging configuration
└── data/game/           # JSON entity/seed definitions (factions, sovereigns, personas)

tests/
├── unit/                # Fast deterministic tests
├── integration/         # Full simulation tests
└── constants.py         # Centralized test constants (ADR031)

tools/                   # Simulation lab: traces, sweeps, tuning, QA
specs/                   # Feature specifications per branch
ai-docs/                 # Machine-readable YAML specs (architecture, ADRs, state)
docs/                    # Sphinx API documentation
```

## Engine Systems

The simulation engine runs **25 modular Systems** in strict materialist-causality
order each tick (source of truth: `_DEFAULT_SYSTEMS` in
[`simulation_engine.py`](src/babylon/engine/simulation_engine.py)). They fall
into three phases:

```
step(WorldState, SimulationConfig) -> WorldState  ──►  SimulationEngine.run_tick(graph, services, context)

Material Base   Vitality · Territory · Substrate · Production · TickDynamics ·
                ReserveArmy · Community · Lifecycle · Solidarity · ImperialRent ·
                Dispossession · Decomposition · ControlRatio · Metabolism
Action Phase    OODA · FactionInfluence
Consequences    Survival · Struggle · Consciousness · Sovereignty · Contradiction ·
                ContradictionField · FieldDerivative · CollapseTransition · EdgeTransition
```

The base produces material conditions, organizations observe and act, and the
consequences (survival calculus, consciousness drift, contradiction fields,
sovereign collapse) follow. See `CLAUDE.md` for the per-system annotations.

**Key components:**

| File                                      | Purpose                                                    |
| ----------------------------------------- | ---------------------------------------------------------- |
| `src/babylon/engine/simulation_engine.py` | Orchestrates all Systems                                   |
| `src/babylon/engine/services.py`          | ServiceContainer (dependency injection)                    |
| `src/babylon/engine/event_bus.py`         | Publish/subscribe events (70 EventTypes)                   |
| `src/babylon/engine/formula_registry.py`  | Hot-swappable formula dispatch                             |
| `src/babylon/engine/topology_monitor.py`  | Phase transition detection via percolation                 |
| `src/babylon/engine/observer.py`          | `SimulationObserver`, `SessionRecorder`, `EndgameDetector` |
| `src/babylon/config/defines.py`           | `GameDefines` — all tunable coefficients                   |

## Formula System

18 formula modules in `src/babylon/formulas/` (selected highlights below; see the
directory for the full set, including `balkanization.py`, `consciousness_routing.py`,
and `state_ai.py`):

| Module                   | Theory                                                     |
| ------------------------ | ---------------------------------------------------------- |
| `fundamental_theorem.py` | Imperial rent, labor aristocracy, consciousness drift      |
| `survival_calculus.py`   | P(S\|A), P(S\|R), crossover threshold, loss aversion       |
| `unequal_exchange.py`    | Exchange ratios, exploitation rate, Prebisch-Singer effect |
| `solidarity.py`          | Solidarity transmission                                    |
| `ideological_routing.py` | Bifurcation: fascist vs revolutionary routing              |
| `dynamic_balance.py`     | Bourgeoisie decision dynamics                              |
| `metabolic_rift.py`      | Biocapacity delta (ΔB = R − E×η), overshoot ratio          |
| `class_dynamics.py`      | Class composition analysis                                 |
| `community.py`           | Community-level consciousness                              |
| `curvature.py`           | Topological curvature (Wasserstein-1)                      |
| `trpf.py`                | Tendency of rate of profit to fall                         |
| `vitality.py`            | Population dynamics                                        |
| `lifecycle.py`           | Organization lifecycle                                     |

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
poetry install && poetry run pre-commit install

# CI gate (lint + format + typecheck + unit tests)
mise run ci

# Testing
mise run test:unit          # Fast unit tests only
mise run test:int           # Integration tests
mise run test:scenario      # Full scenario arcs (slow)
mise run test:all           # All non-AI tests (9,500+)
mise run test:cov           # With coverage report

# Quality
mise run lint               # Ruff linter
mise run typecheck          # MyPy strict mode
mise run qa:audit           # Simulation health check (3 scenarios)
mise run qa:verify          # Formula correctness verification
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
mise run qa:regression-generate           # Generate new baselines after intentional changes
mise run qa:schemas                       # JSON schema validation
mise run qa:security                      # Dependency security audit

# UI
mise run web:dev                          # React + Django map UI (current; needs Node — run web:install first)
mise run ui                               # DearPyGui Synopticon dashboard (legacy desktop dashboard)
```

## Testing Standards

Pytest markers:

```
@pytest.mark.math        # Deterministic formulas (fast, pure)
@pytest.mark.ledger      # Economic/political state
@pytest.mark.topology    # Graph/network operations
@pytest.mark.integration # Database/pgvector (I/O bound)
@pytest.mark.ai          # AI/RAG evaluation (slow, non-deterministic)
@pytest.mark.red_phase   # TDD RED phase (intentionally failing)
```

Test constants are centralized in `tests/constants.py` (see ADR031). All code follows strict TDD: Red → Green → Refactor.

## Current State

**Most recent sprint: spec-070 "Balkanization" (Sovereign Topology + Faction
Influence) — complete.** For canonical, always-current status (test counts,
sprint state, per-feature detail) see [`ai-docs/state.yaml`](ai-docs/state.yaml).

Features 001–070 have shipped, including:

- Imperial Rent extraction, unequal exchange, and the D–P–D′ lifecycle circuit
- Solidarity transmission, consciousness drift, and ternary-consciousness routing
- Survival calculus (P(S|A), P(S|R)) and the George Floyd Dynamic (EXCESSIVE_FORCE → UPRISING)
- Territory heat, eviction, and the carceral-geography pipeline
- Metabolic Rift (biocapacity depletion, ecological overshoot)
- OODA-loop organizations, the community hyperedge layer (XGI), and state-apparatus AI
- Dialectical field topology (contradiction fields, curvature, principal-contradiction tracking)
- Cross-scale integration with a PostgreSQL runtime and county-scale headless runs
- **Sovereign topology + faction influence + balkanization** (secession, civil war,
  sovereign collapse, and endgame detection)

Active development happens on the `dev` branch.

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

| Location                                   | Content                                                         |
| ------------------------------------------ | --------------------------------------------------------------- |
| [`ai-docs/`](ai-docs/)                     | Machine-readable YAML specs (architecture, ADRs, current state) |
| [`ai-docs/state.yaml`](ai-docs/state.yaml) | Canonical project status, test counts, sprint state             |
| [`ai-docs/decisions/`](ai-docs/decisions/) | Architecture Decision Records (one YAML per ADR)                |
| [`specs/`](specs/)                         | Per-feature specifications                                      |
| [`docs/`](docs/)                           | Sphinx API documentation (`mise run docs:live`)                 |

## License

MIT License — see [LICENSE](LICENSE).

______________________________________________________________________

**Built With**

```
Claude Opus 4.5 🤝 Autistic Trans Woman = Coherent MLM-TW Simulation
```
