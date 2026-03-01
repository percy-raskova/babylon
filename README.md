# Babylon - The Fall of America

A geopolitical simulation engine modeling the collapse of American hegemony through Marxist-Leninist-Maoist Third Worldist (MLM-TW) theory.

**Mantra:** *Graph + Math = History*

## What Is This?

Babylon models class struggle as a deterministic output of material conditions within a compact topological phase space. It simulates imperial rent extraction, consciousness drift, solidarity transmission, and revolutionary rupture using NetworkX graphs and Pydantic-validated state.

The simulation runs locally without external servers, using the **Embedded Trinity** architecture:

- **The Ledger** (SQLite/Pydantic) — Rigid material state: 17 JSON entity collections validated against JSON Schema Draft 2020-12
- **The Topology** (NetworkX/GraphProtocol) — Fluid relational state; `to_graph()`/`from_graph()` bridge Pydantic ↔ DiGraph
- **The Archive** (ChromaDB) — Semantic history for AI narrative; AI observes state, never controls mechanics

**Architecture Principle:** State is pure data. Engine is pure transformation. They never mix.

## Quick Start

```bash
# Install dependencies
poetry install
poetry run pre-commit install

# Run tests (9,100+ tests)
mise run test:all

# Run simulation
mise run sim:run
```

**Requirements:** Python 3.12+, Poetry, mise

## Project Structure

```
src/babylon/
├── engine/              # Simulation engine (step function, systems, event bus, observers)
│   ├── systems/         # 23 modular Systems (economic, ideology, survival, territory, ...)
│   └── formula_registry.py  # Hot-swappable formula dispatch
├── formulas/            # Mathematical formulas (15 modules covering all MLM-TW theory)
├── models/              # Pydantic entities (SocialClass, Territory, WorldState)
├── rag/                 # ChromaDB integration for semantic history
├── config/              # GameDefines, logging configuration
└── data/game/           # JSON entity definitions (17 collections)

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

The simulation engine runs modular Systems with strict dependency injection:

```
step(WorldState, SimulationConfig) -> WorldState
     |
     v
SimulationEngine.run_tick(graph, services, context)
     |
     +-- 1. ImperialRentSystem   (economic.py)      - Wealth extraction via imperial rent
     +-- 2. SolidaritySystem     (solidarity.py)    - Consciousness transmission
     +-- 3. ConsciousnessSystem  (ideology.py)      - Ideology drift & bifurcation
     +-- 4. SurvivalSystem       (survival.py)      - P(S|A), P(S|R) calculations
     +-- 5. StruggleSystem       (struggle.py)      - Agency Layer (George Floyd Dynamic)
     +-- 6. ContradictionSystem  (contradiction.py) - Tension/rupture dynamics
     +-- 7. TerritorySystem      (territory.py)     - Heat, eviction, carceral geography
     +-- 8. MetabolismSystem     (metabolism.py)    - Biocapacity depletion, ecological overshoot
```

Additional specialized systems (23 total): `VitalitySystem`, `ReserveArmySystem`, `CommunitySystem`,
`ProductionSystem`, `OODASystem`, `ContradictionFieldSystem`, `EdgeTransitionSystem`, `LifecycleSystem`, and others.

**Key components:**

| File                                      | Purpose                                                    |
| ----------------------------------------- | ---------------------------------------------------------- |
| `src/babylon/engine/simulation_engine.py` | Orchestrates all Systems                                   |
| `src/babylon/engine/services.py`          | ServiceContainer (dependency injection)                    |
| `src/babylon/engine/event_bus.py`         | Publish/subscribe events (12 EventTypes)                   |
| `src/babylon/engine/formula_registry.py`  | Hot-swappable formula dispatch                             |
| `src/babylon/engine/topology_monitor.py`  | Phase transition detection via percolation                 |
| `src/babylon/engine/observer.py`          | `SimulationObserver`, `SessionRecorder`, `EndgameDetector` |
| `src/babylon/config/defines.py`           | `GameDefines` — all tunable coefficients                   |

## Formula System

15 formula modules in `src/babylon/formulas/`:

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
mise run test:all           # All non-AI tests (9,100+)
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
mise run ui                               # DearPyGui Synopticon dashboard
```

## Testing Standards

Pytest markers:

```
@pytest.mark.math        # Deterministic formulas (fast, pure)
@pytest.mark.ledger      # Economic/political state
@pytest.mark.topology    # Graph/network operations
@pytest.mark.integration # Database/ChromaDB (I/O bound)
@pytest.mark.ai          # AI/RAG evaluation (slow, non-deterministic)
@pytest.mark.red_phase   # TDD RED phase (intentionally failing)
```

Test constants are centralized in `tests/constants.py` (see ADR031). All code follows strict TDD: Red → Green → Refactor.

## Current State

**Epoch 1: "The Demonstration" — COMPLETE**
**Current: Slice 1.5 "The Dashboard" — IN PROGRESS**

Completed systems:

- Imperial Rent extraction (EXPLOITATION edges) — 4-phase extraction
- Solidarity transmission (SOLIDARITY edges)
- Consciousness drift and bifurcation
- Survival calculus (P(S|A), P(S|R))
- George Floyd Dynamic (EXCESSIVE_FORCE → UPRISING)
- Territory heat, eviction, and displacement pipeline
- Topology monitoring (percolation, resilience, phase transitions)
- Metabolic Rift (biocapacity depletion, ecological overshoot)
- OODA Loop system (organization decision cycles)
- Community hyperedge layer (XGI hypergraph)
- DPD lifecycle circuit (legitimation crisis modeling)

In progress:

- Slice 1.5: Wire 4-node circuit metrics to DearPyGui Synopticon dashboard
- Feature 033: Bifurcation Topology Analysis (George Jackson model extended with community consciousness weighting)

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

| Location                                           | Content                                                         |
| -------------------------------------------------- | --------------------------------------------------------------- |
| [`ai-docs/`](ai-docs/)                             | Machine-readable YAML specs (architecture, ADRs, current state) |
| [`ai-docs/state.yaml`](ai-docs/state.yaml)         | Canonical project status, test counts, sprint state             |
| [`ai-docs/decisions.yaml`](ai-docs/decisions.yaml) | Architecture Decision Records (ADR001–ADR036+)                  |
| [`specs/`](specs/)                                 | Per-feature specifications                                      |
| [`docs/`](docs/)                                   | Sphinx API documentation (`mise run docs:live`)                 |

## License

MIT License — see [LICENSE](LICENSE).

______________________________________________________________________

**Built With**

```
Claude Opus 4.5 🤝 Autistic Trans Woman = Coherent MLM-TW Simulation
```
