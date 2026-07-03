# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Identity

**Name**: Babylon - The Fall of America
**Concept**: Geopolitical simulation engine modeling the collapse of American hegemony through MLM-TW (Marxist-Leninist-Maoist Third Worldist) theory
**Objective**: Model class struggle as deterministic output of material conditions within a compact topological phase space
**Mantra**: Graph + Math = History

## Governance & Git Workflow

This project uses the **Benevolent Dictator** model. Persephone Raskova ([@percy-raskova](https://github.com/percy-raskova)) has final authority on all merges to `main`.

### Branch Structure

```
main ────► stable releases (BD merges only)
  │              ▲
  ▼              │
dev ─────► integration (PRs welcome here)
  │    ▲
  ▼    │
feature/*, fix/*, docs/*, refactor/*
```

### Key Rules

- **Contributors** branch from `dev`, PR to `dev`
- **BD only** merges `dev` → `main` for releases
- **Hotfixes** go `fix/*` → `main` (BD only), then backport to `dev`
- **Never** commit directly to `main` or `dev`

### Branch Naming

| Prefix | Purpose |
|--------|---------|
| `feature/` | New functionality |
| `fix/` | Bug fixes |
| `docs/` | Documentation |
| `refactor/` | Code improvements |
| `test/` | Test changes |

### For Claude Instances

When making commits:
1. Use conventional commit format: `type(scope): description`
2. **Commit after each unit of work** - Don't let multiple logical changes accumulate
3. If working on a feature, ensure you're on a feature branch, not `main` or `dev`
4. See [CONTRIBUTORS.md](CONTRIBUTORS.md) and [SETUP_GUIDE.md](SETUP_GUIDE.md) for full workflow

**Commit Early, Commit Often**: Each logical unit of work should be its own commit. This means:
- After completing a bug fix → commit immediately
- After adding a new feature → commit immediately
- After refactoring → commit immediately
- After adding tests for a feature → commit with the feature (same unit)

**Why This Matters**: Pre-commit hooks test only staged files. If you accumulate multiple units of work (e.g., Bug A fix + Bug B fix), and Bug B's tests depend on Bug A's code changes, you cannot commit them separately - the hooks will fail. This forces large, intertwined commits that are hard to revert and review.

**Anti-Pattern**:
```
# BAD: Multiple units of work in one session without commits
1. Fix Genesis bug (scenarios.py, test_scenario_initialization.py)
2. Fix Zombie bug (economic.py, social_class.py, defines.py, test_subsistence.py)
3. Try to commit Genesis fix alone → FAILS (tests need Zombie fix code)
4. Forced to make one giant commit with both fixes
```

**Correct Pattern**:
```
# GOOD: Commit after each unit
1. Fix Genesis bug → commit immediately
2. Fix Zombie bug → commit immediately
3. Each fix is independently revertable
```

### Documentation Maintenance (ai-docs/)

**IMPORTANT**: After completing significant work, update `ai-docs/` to reflect the new state.

**When to Update:**
- After implementing a new System or feature
- After fixing bugs that affect documented behavior
- After refactoring that changes architecture
- When discovering issues or edge cases worth noting
- When completing a sprint or phase milestone

**Files to Consider:**

| File | Update When... |
|------|----------------|
| `state.yaml` | Test counts change, sprint status changes, new components added |
| `roadmap.md` | Phase/sprint milestones reached, new planned work identified |
| `tooling.yaml` | New tools added, configuration changes, testing infrastructure updates |
| `observer-layer.yaml` | Observer system changes, event types added |
| `architecture.yaml` | System architecture changes, new Systems added |
| `decisions.yaml` | Architectural decisions made (ADRs) |

**Update Guidelines:**
1. Keep status markers accurate (COMPLETE, IN PROGRESS, PLANNED)
2. Update test counts when they significantly change
3. Add new issues/TODOs discovered during work
4. Break large changes into discrete, trackable items
5. Reference file paths for implemented features
6. Add cross-references between related documents

**Anti-Pattern**: Do NOT mark features as implemented without verifying the code exists.

## Commands

```bash
# Setup
poetry install
poetry run pre-commit install

# Task Runner (namespace-driven - see ADR035)
mise tasks                                        # List all available tasks

# CI & Quality (fast gate)
mise run check                                    # lint + format + typecheck + test:unit
mise run ci                                       # Same as check
mise run lint                                     # Run ruff linter
mise run format                                   # Run ruff formatter
mise run typecheck                                # MyPy strict mode
mise run clean                                    # Clean build artifacts

# Testing (test:* namespace)
# Every test:* task writes verbose machine-readable artifacts to
# reports/test-results/<task>/{junit.xml,report.json,report.html}.
# See "Test Reports for AI Agents" section below for the JSON schema.
mise run test:unit                                # Unit tests (fast) → reports/test-results/unit/
mise run test:int                                 # Integration tests → reports/test-results/int/
mise run test:scenario                            # Scenario tests (slow, full arcs) → reports/test-results/scenario/
mise run test:all                                 # All non-AI tests → reports/test-results/all/
mise run test:cov                                 # Tests + coverage (XML+JSON+HTML) → reports/test-results/cov/
mise run test:doctest                             # Doctest examples in formulas → reports/test-results/doctest/

# Test report helpers
mise run test:clean                               # Wipe reports + .pytest_cache + htmlcov + .coverage* + __pycache__
mise run test:show                                # Open the most recent HTML report in a browser
mise run test:summary                             # Print one-screen summary of the most recent JSON report

# Simulation (sim:* namespace)
mise run sim:run                                  # Main simulation entry point
mise run sim:trace                                # Time-series CSV + JSON output
mise run sim:sweep                                # Parameter sweep analysis
mise run sim:profile                              # cProfile performance analysis

# Tuning (tune:* namespace)
mise run tune:optuna                              # Bayesian optimization (Optuna TPE)
mise run tune:landscape                           # 2D parameter grid search
mise run tune:params                              # 1D sensitivity sweep
mise run tune:dashboard                           # Optuna Dashboard visualization

# QA (qa:* namespace)
mise run qa:audit                                 # Simulation health check
mise run qa:verify                                # Formula correctness verification
mise run qa:schemas                               # JSON schema validation
mise run qa:security                              # Dependency security audit

# Demo (demo:* namespace)
mise run demo:slice                               # Full pipeline demo (Engine->RAG->LLM)
mise run demo:persona                             # Persephone persona voice test
mise run demo:narrative                           # Narrative U-curve sweep

# Data (data:* namespace)
mise run data:query                               # Open SQLite CLI for 3NF reference database
mise run data:db-init                             # Initialize SQLite database schema
mise run data:bea-load                            # Ingest BEA national I-O tables (spec-068)
mise run data:lodes-od                            # Download LODES OD commuter flow data
mise run data:tiger-counties                      # Ingest TIGER county geometry into Postgres
mise run data:tiger-sqlite                        # Bootstrap SQLite reference DB with TIGER + H3 res-7

# Documentation (docs:* namespace)
mise run docs:build                               # Build Sphinx documentation
mise run docs:live                                # Live-reload documentation server
mise run docs:strict                              # Build with warnings as errors

# Web App (web:* namespace)
mise run web:dev                                  # Start Django + Vite as background daemons
mise run web:stop                                 # Graceful shutdown (SIGTERM → SIGKILL after 5s)
mise run web:status                               # Show server running/stopped status
mise run web:logs                                 # Tail both server log files
mise run web:backend                              # Django in foreground (port 8000)
mise run web:frontend                             # Vite in foreground (port 5173)
mise run web:install                              # Install Python + Node deps
mise run web:migrate                              # Django database migrations
mise run web:test                                 # Frontend tests (Vitest)
mise run web:check                                # Frontend quality (tsc + eslint + prettier + vitest)
mise run web:build                                # Production frontend build

# Direct pytest (for specific tests)
poetry run pytest tests/unit/test_foo.py::test_specific    # Single test
poetry run pytest -k "test_name_pattern"                   # Pattern matching
```

## Architecture: The Embedded Trinity

Three-layer local system (no external servers):

1. **The Ledger** (SQLite/Pydantic) - `src/babylon/data/game/`
   - Rigid material state: 17 JSON entity collections
   - Validated against JSON Schema Draft 2020-12

2. **The Topology** (NetworkX) - `src/babylon/models/world_state.py`
   - Fluid relational state via `to_graph()`/`from_graph()`
   - Two node types: `SocialClass` (entities) and `Territory` (spatial)
   - Edges: EXPLOITATION, SOLIDARITY, WAGES, TRIBUTE, TENANCY, ADJACENCY, etc.

3. **The Archive** (pgvector) - `src/babylon/persistence/pgvector_store.py`
   - Semantic history for AI narrative generation (ChromaDB removed in spec-037; pgvector in Postgres replaced it)
   - AI observes state changes, never controls mechanics

## Engine Architecture

The simulation engine uses modular Systems with dependency injection.
Per spec-066 ADR044, the bridged headless runner now actually invokes
`SimulationEngine.run_tick(graph, services, context)` on every tick;
the engine runs the 25 default systems in this materialist-causality
order (source: `simulation_engine._DEFAULT_SYSTEMS`; spec-070 added the
three x.5 balkanization systems marked below):

```
SimulationEngine.run_tick(graph, services, context)
     |
     v
Material Base (positions 1-13, plus Substrate at 2.5):
   1.  VitalitySystem              - Biological cost + death
   2.  TerritorySystem             - Land state updates, heat dynamics, eviction pipeline
   2.5 SubstrateSystem             - Substrate stocks (spec 062 US7 FR-050)
   3.  ProductionSystem            - Value creation (v, c, s, k per hex)
   4.  TickDynamicsSystem          - Tick dynamics (Feature 017)
   5.  ReserveArmySystem           - Reserve-army wage pressure (Feature 021)
   6.  CommunitySystem             - Community hypergraph layer (Feature 022)
   7.  LifecycleSystem             - D-P-D' lifecycle circuit (Feature 030)
   8.  SolidaritySystem            - Consciousness transmission (organization calculation)
   9.  ImperialRentSystem          - Value extraction (Phi flows along EXPLOITATION edges)
  10.  DispossessionEventSystem    - Dispossession events (Feature 021)
  11.  DecompositionSystem         - Labor-aristocracy decomposition (Terminal Crisis)
  12.  ControlRatioSystem          - Guard:prisoner ratio + terminal decision
  13.  MetabolismSystem            - Ecological residue of production
Action Phase (position 14 — Spec 056 F6=alpha reorder):
  14.  OODASystem                  - Organizations observe + act (Feature 032)
Consequences (positions 14.5-21, incl. spec-070 x.5 systems):
  14.5 FactionInfluenceSystem      - Faction influence propagation (spec-070; classified CONSEQUENCE per FR-042 despite post-OODA position)
  15.  SurvivalSystem              - Risk assessment (P(S|A), P(S|R))
  16.  StruggleSystem              - Agency layer (George Floyd dynamic, EXCESSIVE_FORCE / UPRISING)
  17.  ConsciousnessSystem         - Ideology drift + bifurcation
  17.5 SovereigntySystem           - Sovereign legitimacy + secession dynamics (spec-070)
  18.  ContradictionSystem         - Systemic tension accounting
  19.  ContradictionFieldSystem    - Field computation (Feature 002)
  20.  FieldDerivativeSystem       - Spatial/temporal derivatives + principal_field (Feature 002)
  20.5 CollapseTransitionSystem    - Collapse partition + territory transition (spec-070)
  21.  EdgeTransitionSystem        - Compound predicates + edge mode transitions (Feature 002)
```

Phase E note: positions 19-21 (the Feature-002 field stack) are now LIVE in
production — they no longer early-return on `field_registry is None`. With no
registry wired, System 19 sources its per-node fields from the opposition layer
(exploitation = mean incident edge tension; atomization = the global gap),
System 20 emits `principal_field` (renamed from `principal_contradiction` to
avoid colliding with @18's Maoist principal), and System 21's predicates run.
ContradictionSystem @18 also classifies the fixed-point regime each tick
(`dialectical_regime` graph attr) and the EventType enum gained
`LEVEL_TRANSITION` (the Aufhebung signal, published on the sublation branch).

See `ai-docs/decisions/ADR044_engine_integration_into_bridged_runner.yaml`
for the spec-066 wiring history; the 7-system list previously documented
here was the early MVP cut from spec-001 (now historical).

**Key Components**:
- `src/babylon/engine/simulation_engine.py` - Orchestrates Systems
- `src/babylon/engine/services.py` - ServiceContainer (DI container)
- `src/babylon/engine/event_bus.py` - Publish/subscribe event bus (plain-str event types; the EventType enum — 71 values — lives in `src/babylon/models/enums/events.py`)
- `src/babylon/engine/formula_registry.py` - 12 hot-swappable formulas
- `src/babylon/engine/simulation.py` - Stateful facade for multi-tick runs
- `src/babylon/engine/factories.py` - `create_proletariat()`, `create_bourgeoisie()`
- `src/babylon/engine/observer.py` - `SimulationObserver` protocol for state change notifications
- `src/babylon/engine/topology_monitor.py` - Phase transition detection via percolation theory
- `src/babylon/engine/systems/struggle.py` - George Floyd Dynamic (EXCESSIVE_FORCE, UPRISING events)
- `src/babylon/engine/systems/territory.py` - Carceral geography, heat dynamics, eviction pipeline
- `src/babylon/config/defines/` - GameDefines (all tunable game coefficients)

**Observer System**:
- `SimulationObserver` - Protocol for state change notifications (`src/babylon/engine/observer.py` — the protocol only; implementations live in `engine/observers/`)
- `SessionRecorder` - Black box recording for debugging/replay (`engine/observers/`)
- `EndgameDetector` - Detects the 5 terminal GameOutcomes: REVOLUTIONARY_VICTORY, ECOLOGICAL_COLLAPSE, FASCIST_CONSOLIDATION, RED_OGV, FRAGMENTED_COLLAPSE (`engine/observers/endgame_detector.py`)
- `TopologyMonitor` - Phase transition detection via percolation theory (`src/babylon/engine/topology_monitor.py`)

## Type System

All game entities use Pydantic models with constrained types:

```python
# Constrained numeric types
from babylon.models import Probability, Currency, Intensity, Ideology, Coefficient

# Enums
from babylon.models import SocialRole, EdgeType, IntensityLevel, ResolutionType
from babylon.models import OperationalProfile, SectorType  # Territory system

# Core entities
from babylon.models import SocialClass, Territory, Relationship, WorldState, SimulationConfig
```

## Formula System

55 public formula functions across 17 modules in `src/babylon/formulas/`:

| Module | Formulas |
|--------|----------|
| `fundamental_theorem` | `calculate_labor_aristocracy_ratio`, `is_labor_aristocracy`, `calculate_consciousness_drift` |
| `survival_calculus` | `calculate_acquiescence_probability`, `calculate_revolution_probability`, `calculate_crossover_threshold`, `apply_loss_aversion` |
| `unequal_exchange` | `calculate_exchange_ratio`, `calculate_exploitation_rate`, `calculate_value_transfer`, `prebisch_singer_effect` |
| `solidarity` | `calculate_solidarity_transmission` |
| `dynamic_balance` | `calculate_bourgeoisie_decision` |
| `metabolic_rift` | `calculate_biocapacity_delta`, `calculate_overshoot_ratio` |
| `trpf` | `calculate_trpf_multiplier`, `calculate_rent_pool_decay`, `calculate_rate_of_profit`, `calculate_organic_composition` |
| `consciousness` / `consciousness_routing` | `compute_ternary_consciousness`, `compute_agitation_delta`, `compute_exploitation_visibility`, `compute_reification_buffer`, `route_agitation_to_ternary`, `normalize_to_simplex` |
| `state_ai` | `calculate_faction_shift`, `is_fascist_convergence`, `check_fascist_reversion` |
| `community` | `calculate_solidarity_potential`, `calculate_threat_score`, `calculate_infrastructure_decay`, `calculate_solidarity_amplification`, `compute_community_cost_modifier` |
| `class_dynamics` | `calculate_wealth_flow`, `calculate_class_dynamics_derivative`, `calculate_wealth_acceleration`, `calculate_full_dynamics`, `calculate_equilibrium_deviation`, `invert_wealth_to_population` |
| `lifecycle` | `compute_population_flow`, `compute_dependency_ratio`, `compute_legitimation_index`, `compute_pareto_gini`, `compute_ideology_transmission`, `compute_shadow_subsidy` |
| `balkanization` (spec-070) | `calculate_metabolic_impact`, `derive_extraction_policy_from_stance`, `derive_default_multipliers_from_stance`, `winning_faction_for_territory`, `detect_red_settler_trap`, `contiguous_influence_majority_subregion`, `extrapolate_habitability` |
| `contradiction` / `vitality` / `curvature` | `calculate_contradiction_intensity`, `calculate_mortality_rate`, `compute_ollivier_ricci` |

Note: imperial-rent math lives in `src/babylon/economics/` (tensor + Leontief pipeline, specs 011/057), not in `formulas/`.

## Pytest Markers

```python
@pytest.mark.math        # Deterministic formulas (fast, pure)
@pytest.mark.ledger      # Economic/political state
@pytest.mark.topology    # Graph/network operations
@pytest.mark.integration # Database/Postgres (I/O bound)
@pytest.mark.ai          # AI/RAG evaluation (slow, non-deterministic)
@pytest.mark.unit        # Unit tests (default)
@pytest.mark.red_phase   # TDD RED phase (intentionally failing until GREEN)
```

## Test Reports for AI Agents

Every `mise run test:*` task writes verbose machine-readable artifacts to
`reports/test-results/<task>/` (gitignored). Three formats per run, every time:

- **`junit.xml`** — JUnit XML, `xunit2` schema. Includes captured stdout, stderr,
  AND log records per `<testcase>` (via `junit_logging = "all"`). Compatible with
  GitHub Actions test-reporter, IDE integrations, most CI tooling.
- **`report.json`** — `pytest-json-report` output, indented for diff-readability.
  **Best format for AI parsing** — see schema below.
- **`report.html`** — `pytest-html`, self-contained (single file, viewable
  offline). Open via `mise run test:show`.

`test:cov` additionally writes `coverage.xml` (Cobertura), `coverage.json`
(machine-readable), and `htmlcov/` (interactive HTML) into the same directory.

### Verbose flags applied to every test:* task

`-vv --tb=long --showlocals --show-capture=all --capture=tee-sys -r aR --durations=25`

Per the pytest docs (max standard expressiveness), this produces:

- Full assertion diffs (no truncation)
- Long tracebacks with **local variables** at each frame
- Captured stdout/stderr/logs for every test (passing AND failing)
- Live console output passes through (via `tee-sys`) AND is captured
- All-outcome summary including `xfailed`/`xpassed`/`skipped` reasons
- Top 25 slowest tests reported per run

### JUnit ini settings (`pyproject.toml [tool.pytest.ini_options]`)

| Setting | Value | Effect |
|---|---|---|
| `junit_family` | `"xunit2"` | Modern schema with richer per-testcase metadata |
| `junit_logging` | `"all"` | Embeds stdout, stderr, AND log records into the XML |
| `junit_log_passing_tests` | `true` | Logs captured even for passing tests |
| `junit_duration_report` | `"call"` | Test-call duration only (excludes setup/teardown) |
| `junit_suite_name` | `"babylon"` | Suite name for multi-project test aggregators |

These are no-ops unless `--junit-xml` is passed (so raw `poetry run pytest`
behaves identically to today; CI is unaffected).

### Reading reports in a future session — recommended pattern

```python
import json
from pathlib import Path

# Load a specific task's most recent JSON report
report = json.loads(Path("reports/test-results/unit/report.json").read_text())

# Top-level fields
report["created"]    # ISO timestamp (UTC) when the run started
report["duration"]   # total wall time (seconds, float)
report["summary"]    # {"passed": N, "failed": N, "skipped": N, "error": N,
                     #  "xfailed": N, "xpassed": N, "total": N, "collected": N}
report["exitcode"]   # 0=all pass, 1=tests failed, 2=collection error, ...

# Per-test details
for test in report["tests"]:
    test["nodeid"]     # e.g., "tests/unit/test_foo.py::TestBar::test_baz"
    test["outcome"]    # "passed" | "failed" | "skipped" | "error" | "xfailed" | "xpassed"
    test["duration"]   # call duration (seconds)
    if test["outcome"] in ("failed", "error"):
        test["call"]["longrepr"]  # full traceback w/ locals (--tb=long --showlocals)
        test["call"]["stdout"]    # captured stdout (--capture=tee-sys)
        test["call"]["stderr"]
        test["call"]["log"]       # captured log records (level, message, ...)
```

### Quick checks

- `mise run test:summary` — one-screen text summary of the most recent run
  (counts, exit code, list of failures)
- `mise run test:show` — open most recent HTML report in a browser
- `mise run test:clean` — wipe `reports/test-results/`, `.pytest_cache/`,
  `htmlcov/`, `.coverage*`, and project `__pycache__/` directories (preserves
  `.hypothesis/` counterexample DB, `.venv/`, and `node_modules/`)

### CI is unaffected

`.github/workflows/ci.yml` uses raw `poetry run pytest -q --tb=short`, never
`mise run`. The mise tasks are dev/AI-agent ergonomics only — no CI changes.

## Coding Standards

- **Pydantic First**: All game objects as `pydantic.BaseModel`, no raw dicts
- **Constrained Types**: Use `Probability`, `Currency`, `Intensity` instead of raw floats
- **Data-Driven**: Game logic in JSON data files, not hardcoded conditionals
- **Strict Typing**: MyPy strict mode, explicit return types
- **TDD**: Red-Green-Refactor cycle mandatory
- **Conventional Commits**: Use `feat:`, `fix:`, `docs:`, `refactor:` prefixes
- **SQLAlchemy 2.0**: Use `DeclarativeBase` with `Mapped` types for ORM models
- **Sphinx-Compatible Docstrings**: All public classes/functions require RST-formatted docstrings
- **No `test_` Prefix in Production Code**: Pytest auto-collects functions starting with `test_`. Use `check_`, `verify_`, or `validate_` instead for production functions that "test" something (e.g., `check_resilience`, not `test_resilience`).

## Test Constants Architecture

Test values are centralized in `tests/constants.py` using frozen dataclasses. See **ADR031** for full rationale.

**Pattern**:
```python
from tests.constants import TestConstants
TC = TestConstants

def test_worker_wealth(self) -> None:
    worker = create_worker(wealth=TC.Wealth.WORKER_BASELINE)
    assert worker.wealth == TC.Wealth.WORKER_BASELINE  # Semantic!
```

**Categories**: `Wealth`, `Probability`, `Ideology`, `Consciousness`, `Thresholds`, `Vitality`, `Organization`, `EconomicFlow`, `RevolutionaryFinance`, `MetabolicRift`, `TRPF`, `MarxCapitalExamples`

**Key Distinction - What to Extract vs Keep Inline**:

| Extract to Constants | Keep Inline |
|---------------------|-------------|
| Domain defaults (`DEFAULT_WEALTH = 10.0`) | Type boundaries (`0.0`, `1.0` for Probability) |
| Thresholds (`AWAKENING = 0.7`) | Edge cases (`-0.001` for "just below zero") |
| Scenario values (`PERIPHERY_WORKER = 20.0`) | Precision tests (`0.123456789` for quantization) |
| Theoretical values (`LOSS_AVERSION = 2.25`) | Computed results in assertions |

**Rationale**: Type boundary tests verify the TYPE DEFINITION itself. The values 0.0 and 1.0 ARE the Probability contract. Extracting them reduces clarity.

**Anti-Pattern**: Don't extract boundary values to constants:
```python
# BAD: Obscures what's being tested
assert Probability(TC.Probability.LOWER_BOUND) is valid

# GOOD: Boundary is self-documenting
assert Probability(0.0) is valid  # Lower bound of [0, 1]
```

## Test Infrastructure

**Factories** (`tests/factories/`):
- `DomainFactory`: Creates test entities with sensible defaults
- Pattern: Override only what matters for the test

**Fixtures** (`conftest.py` hierarchy):
- Root: Session-scoped infrastructure
- Per-domain: Domain-specific fixtures
- Avoid fixture duplication across conftest files

**TDD Markers**:
```python
@pytest.mark.red_phase  # Intentionally failing until GREEN phase
```

## Docstring Standards

**IMPORTANT**: All public classes, functions, and modules MUST have Sphinx-compatible docstrings.

**Format**: RST (reStructuredText) - Sphinx's native format

```python
def calculate_imperial_rent(wages: Currency, value: Currency) -> Currency:
    """Calculate imperial rent extracted via unequal exchange.

    The fundamental theorem of MLM-TW: when wages exceed value produced,
    the difference represents imperial rent transferred from periphery.

    Args:
        wages: Currency amount paid to workers in core.
        value: Currency amount of value actually produced.

    Returns:
        Imperial rent (Phi) extracted from periphery workers.

    Raises:
        ValueError: If wages or value are negative.

    Example:
        >>> calculate_imperial_rent(wages=Currency(100.0), value=Currency(80.0))
        Currency(20.0)

    See Also:
        :func:`calculate_exploitation_rate`: Related exploitation metric.
        :class:`ImperialRentSystem`: System that applies this formula.
    """
```

**RST Rules**:
- Use `::` for code blocks (not markdown triple backticks)
- Use `:param name:` or `Args:` section for parameters
- Use `:returns:` or `Returns:` section for return values
- Use `:raises ExceptionType:` or `Raises:` section for exceptions
- Use `:class:`ClassName`` for cross-references to classes
- Use `:func:`function_name`` for cross-references to functions
- Use `:mod:`module.path`` for cross-references to modules
- Blank line required before and after code blocks
- Examples should pass `pytest --doctest-modules`

**Maintainability Refactoring Pattern**:
When refactoring to improve Maintainability Index (MI), move rich theory from function docstrings to RST files:

1. **Module docstring**: Keep theory summary, See Also cross-references
2. **Function docstring**: One-line summary + Args + Returns + minimal Example
3. **RST file** (`docs/reference/*.rst`): Full LaTeX formulas, historical context, code examples

This preserves rich documentation in Sphinx output while reducing LOC that penalizes MI scores.
The `ln(LOC)` term in MI formula treats docstrings and code equally.

**Why This Matters**: Sphinx autodoc generates API documentation from docstrings. Malformed docstrings produce warnings that block CI (we use `-W` flag). See `ai-docs/tooling.yaml` for configuration details.

## Mathematical Core

**Fundamental Theorem**: Revolution in Core impossible if W_c > V_c (wages > value produced). The difference is Imperial Rent (Phi).

**Survival Calculus**:
- P(S|A) = Sigmoid(Wealth - Subsistence) - survival by acquiescence
- P(S|R) = Organization / Repression - survival by revolution
- Rupture occurs when P(S|R) > P(S|A)

**Bifurcation Formula**: When wages fall, agitation energy routes to either Fascism (+1 ideology) or Revolution (-1 ideology) based on SOLIDARITY edge presence.

**Heat Dynamics**: HIGH_PROFILE territories gain heat (state attention), LOW_PROFILE decays heat. Heat >=0.8 triggers eviction pipeline.

**Metabolic Rift**: Ecological limits on capital accumulation:
- Biocapacity Delta: ΔB = R - (E × η) where R=regeneration, E=extraction, η=entropy
- Overshoot Ratio: O = C / B where C=consumption, B=biocapacity (O>1 = ecological overshoot)

## Configuration: GameDefines

All tunable game coefficients are centralized in `GameDefines` (Pydantic model):

```python
from babylon.config.defines import GameDefines

defines = GameDefines()  # Dataclass defaults; GameDefines.load_default() applies the optional src/babylon/data/defines.yaml override if present
defines.economy.extraction_efficiency  # 0.8 default
defines.consciousness.drift_sensitivity_k  # Consciousness drift rate
```

Categories: `economy`, `consciousness`, `solidarity`, `survival`, `territory`

## Simulation Lab (Complete Task Reference)

The `tools/` directory contains a comprehensive suite for simulation analysis, parameter optimization, and quality assurance. All tools import from `tools/shared.py` (ADR036).

### sim:* - Simulation Execution

| Task | Description | Output |
|------|-------------|--------|
| `mise run sim:run` | Main simulation entry point | Console |
| `mise run sim:trace` | Time-series CSV + JSON | results/trace.csv |
| `mise run sim:sweep` | 1D parameter sweep | results/sweep.csv |
| `mise run sim:profile` | cProfile performance analysis | Console + .prof |
| `mise run sim:monte-carlo` | Monte Carlo UQ (N-sample) | results/monte_carlo.csv |

### tune:* - Parameter Optimization

| Task | Description | Output |
|------|-------------|--------|
| `mise run tune:optuna` | Bayesian optimization (TPE) | optuna.db |
| `mise run tune:landscape` | 2D parameter grid search | results/landscape.csv |
| `mise run tune:params` | 1D sensitivity sweep | Console |
| `mise run tune:sensitivity` | Morris + Sobol SA (both) | results/*.json |
| `mise run tune:morris` | Morris screening (fast) | results/morris.json |
| `mise run tune:sobol` | Sobol variance decomposition | results/sobol.json |
| `mise run tune:dashboard` | Optuna web UI | Browser |

### qa:* - Quality Assurance

| Task | Description | Output |
|------|-------------|--------|
| `mise run qa:audit` | Health check (3 scenarios) | reports/audit_latest.md |
| `mise run qa:verify` | Formula correctness verification | Console |
| `mise run qa:schemas` | JSON schema validation | Console |
| `mise run qa:security` | Dependency security audit | Console |
| `mise run qa:regression` | Baseline comparison (CI) | Console |
| `mise run qa:regression-generate` | Create regression baselines | tests/baselines/*.json |

### Recommended Workflows

**Parameter Discovery (Which parameters matter?)**:
```bash
mise run tune:morris 20              # Fast screening by importance (mu*)
mise run tune:landscape p1 r1 p2 r2  # Visualize 2D interactions
mise run tune:sobol 512              # Quantify variance decomposition
mise run tune:optuna 200             # Optimize important parameters
```

**Uncertainty Quantification (How much variance?)**:
```bash
mise run sim:monte-carlo 1000 42     # 1000 replications, seed=42
# Review 95% CI for ticks_survived
```

**Regression Testing (CI protection)**:
```bash
# After intentional formula changes:
mise run qa:regression-generate      # Create new baselines
# Commit baselines with code changes

# In CI pipeline:
mise run qa:regression               # Compare against baselines
```

**Sensitivity Analysis Interpretation**:
- **Morris mu***: Mean absolute effect (higher = more important)
- **Morris sigma/mu***: Non-linearity indicator (>1 = interactive)
- **Sobol S1**: First-order variance (main effect alone)
- **Sobol ST**: Total-order variance (main + interactions)

Results are stored in `results/` (CSV, JSON), `reports/` (Markdown), `tests/baselines/` (regression), and `optuna.db` (SQLite).

## Documentation

- Sphinx docs: `mise run docs-live` for development, `mise run docs` to build
- AI-readable specs in `ai-docs/` (YAML format) - **read `ai-docs/README.md` for catalog**
- Anti-patterns documented in `ai-docs/anti-patterns.yaml`

**Architecture Principle**: State is pure data. Engine is pure transformation. They never mix.

## Common Gotchas (from claude-mem)

These lessons emerged from debugging sessions and are preserved to prevent re-learning:

### WorldState.events is Per-Tick, NOT Cumulative

```python
# WRONG: Accumulating events across ticks
accumulated_events = accumulated_events + new_events
new_state = state.model_copy(update={"events": accumulated_events})

# RIGHT: Each tick gets fresh events
new_state = state.model_copy(update={"events": tick_events})
```

The simulation engine creates fresh WorldState each tick. `events` contains ONLY that tick's events. "No events this tick" = empty list `[]`, not duplicate events from previous tick.

### Graph Round-Trip Can Lose Mutations

`WorldState.to_graph()` → Systems mutate graph → `WorldState.from_graph()`

**Gotcha**: `from_graph()` excludes computed fields and uses model defaults for missing fields:
```python
# In from_graph(), these are excluded:
social_class_computed = {"consumption_needs"}
territory_excluded = {"p_acquiescence", "p_revolution"}
```

If you add a field to SocialClass, ensure `to_graph()` serializes it via `model_dump()` AND `from_graph()` doesn't exclude it.

**Gotcha**: Using `data.get("field", 0.0)` fallback masks missing field bugs:
```python
# This silently uses 0.0 if s_bio missing from graph node
consumption = data.get("s_bio", 0.0) + data.get("s_class", 0.0)
```

### Systems Mutate Shared Graph In-Place

Systems execute in strict order, each seeing previous systems' mutations:
```
ImperialRent → Solidarity → Consciousness → Survival → Struggle → Contradiction → Territory → Metabolism
```

Access node data via `graph.nodes[node_id]["wealth"]`, not model attributes.

### Mypy Misses Pydantic Attribute Errors

```python
# This passes mypy but fails at runtime:
snapshot: TopologySnapshot = monitor.history[-1]
phase = snapshot.phase  # AttributeError: 'TopologySnapshot' has no attribute 'phase'
```

Pydantic models use dynamic attributes that bypass static analysis. **Runtime tests are essential.**

### Immutability via model_copy()

WorldState is frozen. ALL mutations return new instances:
```python
# WRONG: Trying to mutate
state.tick = state.tick + 1  # Raises ValidationError

# RIGHT: Copy with updates
new_state = state.model_copy(update={"tick": state.tick + 1})
```

### Dependency Injection Over Discovery

```python
# WRONG: Discovering dependencies at runtime
def __init__(self):
    self.metrics = self._find_observer(MetricsCollector)  # Couples to internals

# RIGHT: Explicit injection
def __init__(self, metrics_collector: MetricsCollector):
    self.metrics = metrics_collector  # Testable, explicit
```

## CI Hygiene

**Fix Unrelated Issues When Encountered**: If CI reveals lint/type errors in files you didn't modify, fix them. Don't leave broken windows.

**Import Order Matters**:
```python
# Correct order to avoid E402 (module level import not at top)
from __future__ import annotations

import pytest                          # stdlib first
from pydantic import ValidationError   # third-party second

from babylon.models import SocialClass # local imports third
from tests.constants import TestConstants
TC = TestConstants                      # alias AFTER all imports
```

**Maintain `__all__` Exports**: When adding public functions to a package, update `__init__.py`:
```python
__all__ = [
    "existing_function",
    "new_function",  # Add new exports here
]
```

**Type Ignore Comments**: Use specific error codes, not blanket ignores:
```python
# GOOD: Specific error code
import dearpygui.dearpygui as dpg  # type: ignore[import-untyped]

# BAD: Blanket ignore
import something  # type: ignore
```

## Session Continuity

**claude-mem Integration**: This project uses claude-mem for cross-session memory. Discoveries, decisions, and features are automatically recorded.

**Before Re-investigating**:
- Search claude-mem for prior work on the topic
- Check ai-docs/decisions.yaml for relevant ADRs
- Review ai-docs/state.yaml for current project status

**After Completing Significant Work**:
1. Update `ai-docs/state.yaml` with new status/test counts
2. Create ADR in `ai-docs/decisions.yaml` for architectural patterns
3. Update `ai-docs/roadmap.md` if milestones changed

**ADR Format** (in decisions.yaml):
```yaml
ADR0XX_descriptive_name:
  status: "accepted"
  date: "YYYY-MM-DD"
  title: "Short descriptive title"
  context: |
    What problem were we solving?
  decision: |
    What did we decide?
  rationale:
    key_point: "Why this approach?"
  consequences:
    positive:
      - "Benefit 1"
    negative:
      - "Tradeoff 1"
```

## Active Technologies
- Python 3.12+ + NetworkX 3.x, Pydantic 2.x, SQLAlchemy 2.x (001-mvp-sim-engine)
- SQLite (data/sqlite/marxist-data-3NF.sqlite for reference; in-memory for simulation state) (001-mvp-sim-engine)
- Python 3.12+ + Pydantic 2.x (frozen models), NetworkX 3.x (graph), h3 4.2 (spatial indexing) (006-gui-protocol-extension)
- N/A (in-memory protocols, no persistence changes) (006-gui-protocol-extension)
- Python 3.12+ + Pydantic 2.x, NetworkX 3.x, SQLAlchemy 2.x (existing stack) (008-infrastructure-hardening)
- In-memory (MetricsCollector stores data in dicts, no persistence layer used currently) (008-infrastructure-hardening)
- Python 3.12+ + Pydantic 2.x (validation), SQLAlchemy 2.x (ORM), typer (CLI), tqdm (progress) (009-data-preflight)
- SQLite (marxist-data-3NF.sqlite for reference data) (009-data-preflight)
- Python 3.12+ + NetworkX 3.x, Pydantic 2.x (no new dependencies) (010-cleanup-tech-debt)
- N/A (no storage changes) (010-cleanup-tech-debt)
- Python 3.12+ (existing stack) + Pydantic 2.x (validation), NumPy (tensor ops), SQLAlchemy 2.x (ORM) (011-fundamental-tensor-primitive)
- SQLite (`marxist-data-3NF.sqlite` for source data; in-memory tensor cache) (011-fundamental-tensor-primitive)
- Python 3.11+ + TensorRegistry, ValueTensor4x3, NoDataSentinel from spec 011; CapitalStockCalculator from spec 012; BEA GDP data, QCEW employment data (013-melt-basket-visibility)
- In-memory cache (follows TensorRegistry pattern); no new database tables (013-melt-basket-visibility)
- Python 3.12+ (existing stack) + Pydantic 2.x, SQLAlchemy 2.x (existing), ATUS infrastructure (Feature 005) (015-gamma-visibility-tensor)
- In-memory computation; reads from existing ATUS/QCEW data sources (015-gamma-visibility-tensor)
- Python 3.12+ (existing stack) + Pydantic 2.x (frozen models, validation), existing economics module infrastructure (Feature 013 ClassPosition, NoDataSentinel from tensor.py) (016-class-dynamics-engine)
- In-memory computation; no new database tables. Reads from existing data sources via protocol pattern. (016-class-dynamics-engine)
- Python 3.12+ (existing stack) + Pydantic 2.x (frozen models, validation), existing economics module infrastructure (Features 011-016) (017-simulation-tick-dynamics)
- In-memory computation; no new database tables. Reads from existing data sources via protocol pattern during initialization. (017-simulation-tick-dynamics)
- Python 3.12+ + Pydantic 2.x (frozen models), NetworkX 3.x (solidarity graph), existing economics module (Features 011-017) (018-crisis-devaluation-mechanics)
- In-memory computation; no new database tables. CrisisState persists via CountyEconomicState in the graph bridge. (018-crisis-devaluation-mechanics)
- Python 3.12+ + Pydantic 2.x, NetworkX 3.x, SQLAlchemy 2.x (all existing) (020-detroit-vertical-slice)
- SQLite (marxist-data-3NF.sqlite) — read-only during simulation (020-detroit-vertical-slice)
- Python 3.12+ + NetworkX 3.x (graph), Pydantic 2.x (models), scipy (Wasserstein-1 LP for curvature) (002-dialectical-field-topology)
- In-memory via GraphProtocol (`update_node`, `update_edge`) + `context.persistent_data` for cross-tick history (002-dialectical-field-topology)
- Python 3.12+ (existing stack) + Pydantic 2.x (frozen models), NetworkX 3.x (graph), SQLAlchemy 2.x (ORM), SciPy (sigmoid optimization) (021-capital-volume-i)
- SQLite (marxist-data-3NF.sqlite for reference data); in-memory via GraphProtocol for simulation state (021-capital-volume-i)
- Python 3.12+ (existing stack) + Pydantic 2.x (frozen models, validation), NetworkX 3.x (existing flow graph), XGI 0.10 (hypergraph — already in pyproject.toml) (022-hypergraph-community-layer)
- In-memory via GraphProtocol + XGI Hypergraph. No new database tables. Community state persists via WorldState serialization. (022-hypergraph-community-layer)
- Python 3.12+ (existing stack) + Pydantic 2.x (frozen models, validation), existing economics module infrastructure (Features 011-018) (023-capital-volume-ii)
- In-memory via GraphProtocol. No new database tables. Circulation state persists via CountyEconomicState in the graph bridge. (023-capital-volume-ii)
- Python 3.12+ (existing stack) + Pydantic 2.x (frozen models, validation), existing economics module infrastructure (Features 011-023), httpx (FRED API via existing FredAPIClient) (024-capital-volume-iii)
- In-memory via GraphProtocol. No new database tables. National financial state persists via `NationalTickParameters` extension. County-level distribution persists via `CountyEconomicState` in the graph bridge. FRED/Z.1/Census data loaded via existing `FredAPIClient` + SQLite 3NF schema. (024-capital-volume-iii)
- Python 3.12+ + Pydantic 2.x (frozen models), NumPy (matrix ops), SciPy (sparse matrices, eigendecomposition), SQLAlchemy 2.x (ORM), NetworkX 3.x (graph) (025-tensor-hierarchy)
- SQLite (`data/sqlite/marxist-data-3NF.sqlite` via `NormalizedBase` ORM) (025-tensor-hierarchy)
- Python 3.12+ (read-only analysis of existing codebase) + None added. Analysis reads `defines.py` (Pydantic 2.x models), `defines.yaml`, formula modules, and engine systems. (027-constants-provenance-audit)
- N/A (produces Markdown and YAML report files only) (027-constants-provenance-audit)
- Python 3.12+ (existing stack) + Pydantic 2.x (GameDefines frozen models), SQLAlchemy 2.x (hydrator ORM), NetworkX 3.x (graph bridge) (028-constants-remediation-sweep)
- SQLite (`marxist-data-3NF.sqlite` read-only for data hydration; in-memory for simulation) (028-constants-remediation-sweep)
- Python 3.12+ + Pydantic 2.x (frozen models, validation), XGI 0.10 (hypergraph), NetworkX 3.x (graph protocol) (029-community-hyperedge-upgrade)
- In-memory via XGI Hypergraph + GraphProtocol. CommunityConsciousness serialized to JSON via Pydantic. No new database tables. (029-community-hyperedge-upgrade)
- Python 3.12+ (existing stack) + Pydantic 2.x (frozen models, validation), NetworkX 3.x (GraphProtocol), XGI 0.10 (hypergraph — existing via Feature 022/029) (030-dpd-lifecycle-circuit)
- In-memory via GraphProtocol. No new database tables. DPDState persists via CountyEconomicState extension in the graph bridge. Mobility Atlas CSVs read once during parameter derivation (development-time, not runtime). (030-dpd-lifecycle-circuit)
- Python 3.12+ (existing stack) + Pydantic 2.x (frozen models, discriminated unions), NetworkX 3.x (GraphProtocol), XGI 0.10 (hypergraph — existing via Feature 022/029) (031-organization-base-model)
- In-memory via GraphProtocol. No new database tables. Organization state persists via WorldState serialization (`_node_type="organization"`). Key Figures as separate nodes (`_node_type="key_figure"`). (031-organization-base-model)
- Python 3.12+ (existing project standard) + Pydantic 2.x (frozen models, validation), NetworkX 3.x (GraphProtocol via NetworkXAdapter), XGI 0.10 (hypergraph, existing via Feature 022/029) (032-ooda-loop-system)
- In-memory via GraphProtocol. No new database tables. Organization OODA profiles stored as graph node attributes. Action results as tick events. (032-ooda-loop-system)
- Python 3.12+ + NetworkX 3.x (graph analysis), XGI 0.10 (hypergraph), Pydantic 2.x (frozen models) (033-bifurcation-topology)
- In-memory via GraphProtocol. No new database tables. BifurcationSnapshot stored in monitor history list. (033-bifurcation-topology)
- Python 3.12+ (existing project standard) + Pydantic 2.x (frozen models, validation), NetworkX 3.x (GraphProtocol via NetworkXAdapter), h3 4.2 (spatial indexing), Shapely 2.x (spatial intersection for NE snapping), SciPy (weighted curvature LP) (036-infrastructure-topology)
- In-memory via GraphProtocol. No new database tables. Infrastructure entities stored separately from WorldState.relationships. Natural Earth SQLite (423MB) read-only external data source. FCC broadband data via existing FCCBroadbandLoader. (036-infrastructure-topology)
- Python 3.12+ + psycopg 3.x + psycopg_pool (bulk simulation writes), Django 5.x (game management ORM), PostGIS (spatial queries on hex geometries), pgvector (semantic search replacing ChromaDB), PyArrow (Parquet export), boto3/s3fs (R2 upload), DuckDB (cross-game analytics over archived Parquet) (037-postgres-runtime-db)
- PostgreSQL 16+ (runtime state), SQLite (read-only reference `marxist-data-3NF.sqlite`), Cloudflare R2 (archived Parquet files) (037-postgres-runtime-db)
- Python 3.12+ (existing project stack) + Pydantic 2.x (frozen models, validators), NetworkX 3.x (graph queries), XGI 0.10 (hypergraph memberships) (034-ternary-consciousness)
- In-memory via GraphProtocol. Postgres schema migration for persistence (r, l, f columns). No new database tables. (034-ternary-consciousness)
- Python 3.12+ + Pydantic 2.x (frozen models, validators), NetworkX 3.x (GraphProtocol), XGI 0.10 (hypergraph memberships — existing via Features 022/029) (038-unified-class-system)
- In-memory via GraphProtocol. No new database tables. ClassSystemDefines persisted in `defines.yaml`. (038-unified-class-system)
- Python 3.12+ + Pydantic 2.x (frozen models, discriminated unions), NetworkX 3.x (GraphProtocol via NetworkXAdapter), XGI 0.10 (hypergraph community memberships) (039-state-apparatus-ai)
- In-memory via GraphProtocol. No new database tables. State apparatus AI state persists via WorldState serialization. AttentionThread and FactionBalance stored as graph node attributes or context persistent data. (039-state-apparatus-ai)
- Python 3.12+ + Pydantic 2.x (frozen models, validators), NetworkX 3.x (GraphProtocol), XGI 0.10 (community embeddedness queries) (040-institution-base-model)
- In-memory via GraphProtocol. No new database tables. Institution state persists via WorldState serialization (`_node_type="institution"`). (040-institution-base-model)
- Python 3.12+ (backend), TypeScript 5.x (frontend) + Django 5.x, Pydantic 2.x, NetworkX 3.x, psycopg 3.x, React 19, Zustand 5, Vite 6, deck.gl 9, react-router-dom 7 (installed, unused) (041-mvp-nationwide-sim)
- PostgreSQL 16+ (runtime state via `postgres_runtime.py`), SQLite (reference data) (041-mvp-nationwide-sim)
- TypeScript 5.7 (frontend), Python 3.12+ (backend — minimal changes) + React 19, Zustand 5, deck.gl 9, MapLibre GL 5, Recharts 2, Sigma.js 3, Tailwind CSS v4, Vite 6, lucide-react, react-router-dom 7 (042-game-ui-overhaul)
- PostgreSQL 16+ (runtime state via Django), localStorage (UI preferences) (042-game-ui-overhaul)
- Python 3.12+ + Hypothesis ^6.149.0 (already in `[tool.poetry.group.dev.dependencies]`), pytest 8.x, NetworkX 3.x, SciPy (sparse matrices for OD), Pydantic 2.x (frozen models). XGI 0.10 is available but not required for this work. (053-conservation-invariants)
- N/A at runtime. The Hypothesis example database persists generated counterexamples under `.hypothesis/` (already in `.gitignore` via `[tool.pytest.ini_options]` `cache_dir` settings). (053-conservation-invariants)
- Python 3.12+ (existing project standard) + Hypothesis ^6.149.0 (in `[tool.poetry.group.dev.dependencies]` since Spec 053), pytest 8.x, Pydantic 2.x (frozen models), NetworkX 3.x (graph protocol) (054-bound-invariants)
- N/A — `.hypothesis/` example DB persists generated counterexamples (already in `.gitignore`) (054-bound-invariants)
- Python 3.12+ (existing project standard) + Hypothesis ^6.149.0 (in `[tool.poetry.group.dev.dependencies]` since Spec 053), pytest 8.x, Pydantic 2.x (frozen models), NetworkX 3.x (graph protocol). XGI 0.10 is available but not required for the chosen US2 detector (`_node_type == "community"` graph attribute, per the 2026-05-06 clarification). (055-topology-invariants)
- Python 3.12+ (existing project standard) + Hypothesis ^6.149.0 (in `[tool.poetry.group.dev.dependencies]` since Spec 053), pytest 8.x, Pydantic 2.x (frozen models). For US4's PostgresRuntime branch (gated under `mise run test:integration`): psycopg 3.x + psycopg_pool (already in `pyproject.toml` since Spec 037). No new third-party dependencies are required for the default fast gate. (056-causal-invariants)
- For US4: in-memory `RuntimeDatabase` (default fast gate) + `PostgresRuntime` against a transient test database (`mise run test:integration` only). For US1 / US2 / US3: N/A — pure in-memory `WorldState` exercised by the engine. (056-causal-invariants)
- Python 3.12+ (project standard) (058-adr-bundle-1-pre-spec-057)
- N/A — this is a refactor; no schema changes, no new persistence (058-adr-bundle-1-pre-spec-057)
- Python 3.12+ (existing project standard) + Pydantic 2.x (frozen models, discriminated unions), (059-adr-bundle-2-post-spec-057)
- PostgreSQL 16+ for runtime state (unchanged); SQLite for (059-adr-bundle-2-post-spec-057)
- N/A — fully in-memory. Tests use existing `WorldState` and (060-value-form-invariants)
- Python 3.12+ (backend, engine, persistence); TypeScript 5.7 (frontend) (061-real-backend-wireup)
- PostgreSQL 16+ with PostGIS, pgvector, uuid-ossp extensions; SQLite for reference data only (`marxist-data-3NF.sqlite`) (061-real-backend-wireup)
- Python 3.12+ + Pydantic 2.x (frozen models), NetworkX 3.x (graph), SQLAlchemy 2.x (reference DB ORM), psycopg 3.x + psycopg_pool (Postgres runtime), XGI 0.10 (hypergraph — not new in this spec but referenced via existing community/ subsystem) (066-marx-coherence-fixes)
- PostgreSQL 16+ for runtime state (existing `dynamic_consciousness_state`, `dynamic_relationship_state` etc. from spec-062/065); SQLite for read-only reference data (`marxist-data-3NF.sqlite` for QCEW, BEA, FCC, Census, Hickel/Ricci); no new tables required (migrations 0020-0024 already shipped) (066-marx-coherence-fixes)
- Python 3.12+ (per project standard) + SQLAlchemy 2.x (`DeclarativeBase` + `Mapped[]` ORM in `src/babylon/reference/schema.py`), `sqlite3` (stdlib, atomic transaction wrapper), Pydantic 2.x (audit-report schema), no new deps (067-qcew-ownership-normalization)
- SQLite reference DB at `data/sqlite/marxist-data-3NF.sqlite`; affected tables: `fact_qcew_annual` (DELETE), `dim_industry` (read), `dim_ownership` (read), `dim_time` (read for vintage classification in audit report) (067-qcew-ownership-normalization)
- Python 3.12+ (existing project standard). + `sqlite3` stdlib (existing); Pydantic 2.x for (069-sqlite-cache-optimization)
- Reads from existing `marxist-data-3NF.sqlite` via the (069-sqlite-cache-optimization)
- Python 3.12+ (project standard) + Pydantic 2.x (frozen models per II.6 + I.19), (070-balkanization)
- PostgreSQL 16+ via existing graph bridge (spec-037 + (070-balkanization)
- Python 3.12 (babylon venv; babylon-data code must avoid >3.12-only syntax it doesn't already use) + SQLAlchemy 2.x (canonical ORM `src/babylon/reference/schema.py` + sessions via `babylon.reference.database`), pandas (chunked singlefile streaming, existing pattern), Pydantic 2.x (audit-report models), jsonschema (audit contract validation), stdlib sqlite3/argparse (086-qcew-loader-imputation)
- SQLite reference DB `/media/user/data/babylon-data/sqlite/marxist-data-3NF.sqlite` (canonical, reached via the repo's `data/sqlite` directory symlink — exactly one DB file); source: staged BLS annual singlefile CSVs 2010–2024 at `/media/user/data/babylon-data/qcew/` (8.3 GB, complete) (086-qcew-loader-imputation)

## Recent Changes
- 062-cross-scale-integration: Two-phase persistence boundary, per-tick transactional atomicity (FR-008a), weekly tick + year-scoped coefficient interpolation, hex-as-source-of-truth aggregation views, 5-flow-type pipeline ordering, Canada boundary node, conservation audit log with determinism hash
- 013-melt-basket-visibility: Added MELT calculator, basket visibility, class position classifier, imperial rent calculator (TVT formulas)
- 001-mvp-sim-engine: Added Python 3.12+ + NetworkX 3.x, Pydantic 2.x, SQLAlchemy 2.x
