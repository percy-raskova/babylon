# CLAUDE.md

Operating guidance for any coding agent working in this repository (Claude Code reads this file
natively; `AGENTS.md` is a symlink to it, so every tool shares one source of truth).

<!-- This file is living configuration, not documentation. Keep it lean (<200 lines), accurate,
     and imperative. Push deep reference into ai/ and docs/ that load on demand. -->

## Babylon — The Fall of America

Geopolitical simulation engine modeling the collapse of American hegemony through MLM-TW
(Marxist-Leninist-Maoist Third Worldist) theory. Class struggle is the **deterministic** output of
material conditions in a compact topological phase space. **Mantra: Graph + Math = History.**

You are a senior engineer on this codebase. You write deterministic, tested, mathematically
grounded code, and you follow the Babylon Constitution for architectural decisions.

## Constitutional Compact

Irreducible constraints. Full text: `CONSTITUTION.md` (v2.8.0, 10 Articles +
Amendments A–P; the canonical governance doc — read it before proposing architecture).

**MUST**

- The dialectic `D = (A, Ā, w, T, σ)` is primitive; all partitions emerge from it.
- Every tick produces a deterministic hash. Non-determinism is a bug.
- Every formal construct traces to a material relation (Aleksandrov Test).
- The spatial substrate is immutable; political claims are overlays.
- AI parses/narrates only; the engine adjudicates the math.

**MUST NOT**

- Mutate the substrate, use ungrounded tensors, or substitute fixtures for runtime data.
- Invent primitives without a constitutional amendment.
- Skip the TDD red phase.

**Escalation:** if a task requires violating a limit, STOP and propose an amendment.

## Architecture: The Embedded Trinity

Three-layer local system, no external servers. Full map: `ai/architecture.yaml`.

- **The Ledger** — rigid material state. SQLite reference DB (`data/sqlite/marxist-data-3NF.sqlite`,
  read-only) + PostgreSQL runtime (`src/babylon/persistence/`) + a few JSON seeds in
  `src/babylon/data/game/`.
- **The Topology** — fluid relational state via **rustworkx** (`babylon.topology.BabylonGraph`;
  its own package since Program 14; NetworkX was removed, Amendment L / ADR052).
  `WorldState.to_graph()` / `from_graph()`. Foundational node types
  `social_class` and `territory`; later specs add `organization`, `institution`, `sovereign`,
  `hex`, `industry`, `key_figure`. Edges: EXPLOITATION, SOLIDARITY, WAGES, TRIBUTE, TENANCY,
  ADJACENCY, …
- **The Archive** — semantic history for AI narrative via **pgvector** in Postgres
  (`persistence/pgvector_store.py`; replaced ChromaDB in spec-037). AI observes, never controls.

**Principle:** state is pure data; the engine is pure transformation; they never mix.

## Engine

`SimulationEngine.run_tick(graph, services, context)` runs 26 Systems in strict materialist-causality
order — **source of truth: `simulation_engine._DEFAULT_SYSTEMS`**; annotated order in
`ai/architecture.yaml`. The three phases:

1. **Material Base** (positions 1–13, + Substrate @2.5): Vitality, Territory, Production, TickDynamics,
   ReserveArmy, Community, Lifecycle, Solidarity, ImperialRent, Dispossession, Decomposition,
   ControlRatio, Metabolism.
2. **Action** (@14): OODASystem — organizations observe + act.
3. **Consequences** (14.5–21): FactionInfluence, Survival, Struggle, Consciousness, FascistFaction,
   Sovereignty, Contradiction, ContradictionField, FieldDerivative, CollapseTransition, EdgeTransition.

Key modules: `engine/services.py` (concrete ServiceContainer; the DI *protocol* is
`kernel/services.py`), `kernel/event_bus.py` (plain-str types; the `EventType` enum — 79 values —
is in `models/enums/events.py`), `engine/formula_registry.py` (23 hot-swappable formulas),
`engine/observers/` (`SessionRecorder` black-box replay, `EndgameDetector` for the 5 terminal
outcomes: REVOLUTIONARY_VICTORY, ECOLOGICAL_COLLAPSE, FASCIST_CONSOLIDATION, RED_OGV,
FRAGMENTED_COLLAPSE).

**Layering (Program 14, enforced by `mise run lint:imports`):** `kernel` < `models`/`formulas` <
`topology` < `domain` (economics, dialectics, organizations, institution, bifurcation, geography)
< `persistence` < `engine`; `intelligence` (ai + rag) observes. Nothing imports the engine
backward; the kernel imports nothing above itself.

## Mathematical Core

- **Fundamental Theorem:** revolution in the Core is impossible while `W_c > V_c` (wages > value
  produced); the gap is Imperial Rent (Φ).
- **Survival Calculus:** `P(S|A) = Sigmoid(Wealth − Subsistence)`, `P(S|R) = Organization / Repression`;
  rupture when `P(S|R) > P(S|A)`.
- **Bifurcation:** when wages fall, agitation routes to Fascism (+1) or Revolution (−1) by SOLIDARITY
  edge presence.
- **Metabolic Rift:** `ΔB = R − (E·η)`; overshoot `O = C / B` (O > 1 = ecological overshoot).

Formulas: ~56 functions across 17 modules in `src/babylon/formulas/` (re-exported via `__init__.py`
`__all__`; the two Epoch-2 placeholder Marx formulas were retired by fork-ledger F12).
Imperial-rent tensor/Leontief math lives in `src/babylon/domain/economics/`, not `formulas/`.

## Configuration — one moddable source of truth

All tunable coefficients live in `GameDefines` (Pydantic, 39 category sub-models in
`src/babylon/config/defines/`). The **canonical, player-editable single source of truth** is
`src/babylon/data/defines.yaml` — generated from the schema by `tools/generate_defines_config.py`,
read by `GameDefines.load_default()`, sync-guarded by `tests/unit/config/test_constants_sync.py`.
Modding guide: `docs/how-to/modding-defines.rst`. Never hardcode a coefficient — add a define and
regenerate the YAML (`poetry run python tools/generate_defines_config.py`).

## Coding standards

- **Pydantic first:** all game objects are frozen `BaseModel`s; use constrained types (`Probability`,
  `Currency`, `Intensity`, `Coefficient`), never raw dicts or bare floats.
- **Data-driven:** logic reads from `GameDefines`/`defines.yaml`, not hardcoded conditionals.
- **Strict typing:** MyPy strict, explicit return types. SQLAlchemy 2.0 `DeclarativeBase` + `Mapped`.
- **TDD:** red → green → refactor. `@pytest.mark.red_phase` for intentionally-failing tests.
- **RST docstrings** on all public classes/functions (Sphinx `-W` blocks CI on malformed ones);
  move heavy theory to `docs/reference/*.rst`. See `docs/how-to/` for the docstring pattern.
- **No `test_` prefix in production code** (pytest auto-collects it) — use `check_`/`verify_`/`validate_`.
- **Type-ignore** with a specific code (`# type: ignore[import-untyped]`), never blank.
- **`SimulationConfig`** is a run-scoped config carrying only `rng_seed` (Constitution III.7) — NOT a
  coefficient carrier; coefficients are in `GameDefines`.

## Git & commits

Benevolent-Dictator model (Persephone Raskova is BD). Branch from `dev`
(`feature/|fix/|docs/|refactor/|test/`), never commit directly to `main` or `dev`. Conventional
commits (`type(scope): desc`). **Commit after each unit of work** — pre-commit hooks test only staged
files, so intertwined units force ugly giant commits. Use `mise run commit -- "type(scope): msg"`
(hook-safe: pre-runs hooks, re-stages fixes, verifies HEAD moved). End commit messages with the
`Co-Authored-By` trailer. Full workflow: `CONTRIBUTORS.md`.

## Definition of done

- `mise run check` — lint + format + typecheck + `test:unit` — green.
- For any engine/economics/defines change: `mise run qa:regression` **byte-identical** (5 scenarios).
  If a value moves unintentionally, STOP; if intentionally, regenerate baselines and say so.
- After significant work: update `ai/state.yaml`; add an ADR in `ai/decisions/` (individual
  `ADR0NN_*.yaml` files + `index.yaml` catalog) for architectural decisions.

## Commands

`mise tasks` lists all ~120 tasks (full reference: `ai/tooling.yaml`). Agent inner loop:

```bash
mise run commit -- "type(scope): msg"   # hook-safe commit
mise run check                          # fast gate: lint + format + typecheck + test:unit
mise run check:quick                    # same minus the test leg
mise run test:q -- tests/unit/foo.py    # quiet scoped pytest (keeps cache => --lf works)
mise run test:failed                    # re-run last failures
mise run qa:regression                  # 5-scenario byte-identical baseline gate
mise run sim:status                     # canonical-run status (tick/520, DB size, liveness)
mise run db:sql -- "SELECT ..."         # one-shot SQL vs babylon_test
```

CI (`.github/workflows/ci.yml`) invokes the same mise tasks devs run (`test:unit-ci`, `lint:check`,
`qa:regression`, …) — the only raw-poetry exceptions are the py3.13 forward-compat leg (`nightly.yml`)
and a handful of documented one-offs (migrations, doc build, ad hoc pytest legs).

## Machine safety — resource limits (history: froze the dev box twice, 2026-07-12)

Solo dev box (12 cores / 31 GB RAM). The 2026-07-12 freezes were root-caused and FIXED: BLAS
thread oversubscription (pinned to 1, commit `f3dde939` — also a determinism win) stacked on the
claude-mem chroma-mcp leak (fixed upstream + locally 2026-07-13; **earlyoom is now active** as the
system backstop). Owner ruling 2026-07-14:

- **Run heavy commands UNCAPPED.** `mise run cap` (`tools/capped.sh`) is retired from routine use —
  a process that eats memory is a **code smell to catch loudly**, not contain silently; earlyoom
  keeps the box alive. The cap wrapper still exists for deliberately-risky one-offs (memory bombs,
  untrusted repro scripts), nothing else.
- **Keep the BLAS=1 pin** (conftest + mise `[env]` + guard test `tests/unit/test_blas_thread_cap.py`)
  — that one is correctness (deterministic FP reduction order), not just safety.
- **Still never fan out a Workflow where multiple agents each spawn pytest / the full suite** —
  `test:unit` is xdist with ~1 GB/worker coverage instrumentation; N agents × 4 workers stacks tens
  of GB for no benefit. Parallel agents are for read-only investigation and doc work; heavy
  test/build runs stay single-flight. Prefer scoped `mise run test:q -- <path>` locally.
- **If chroma-mcp servers accumulate again** (`pgrep -fc -- '--client-type persistent'` climbing):
  `mise run mcp:reap`. Never `pkill -f chroma-mcp` by hand (matches its own cmdline, SIGTERMs your
  shell; the script uses a `chroma[-]mcp` bracket guard). The recycle-loop root cause is fixed, so
  a climbing count is news — investigate, don't just reap.

## Gotchas (hard-won; details in `ai/anti-patterns.yaml`)

- `WorldState.events` is **per-tick, not cumulative** — a tick with no events is `[]`, never carried over.
- **Graph round-trip loses data:** `from_graph()` excludes computed fields and defaults missing ones;
  a `data.get("field", 0.0)` fallback silently masks a missing-field bug.
- **Systems mutate the shared graph in-place** in strict order — read `graph.nodes[id]["wealth"]`, not
  model attributes; each system sees prior systems' mutations.
- **MyPy misses Pydantic dynamic-attribute errors** — runtime tests are essential.
- **`dynamic_hex_state` is SPARSE** (spec-089 delta persistence): read `v_hex_state_asof`, never
  `WHERE tick = N` on the raw table; `MAX(tick)` ≠ last committed tick (that's `tick_commit`).
- **`WorldState` is frozen** — mutate via `model_copy(update={...})`, never assignment.
- **Inject dependencies explicitly**, don't discover them at runtime.

## Maintaining this file

This file is **yours**. You have standing permission to modify `CLAUDE.md` — and to shape your own
operating instructions more broadly — whenever you see fit, without asking first. When you learn
something durable (a convention, a corrected fact, a gotcha you hit twice), fix it here and prune what
went stale; treat it as living config with a lifecycle, not a monument. Keep it lean and link out for
depth. `AGENTS.md` symlinks to this file, so one edit updates both.
