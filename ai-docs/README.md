# Babylon AI Documentation Context

Machine-readable documentation for LLM-assisted development.

This directory helps AI assistants understand context, use correct terminology, follow established patterns, avoid known pitfalls, and make decisions aligned with project philosophy.

---

## ACTIVE SPECS (The Truth)

| File | Purpose |
|------|---------|
| `epochs/overview.md` | **CANONICAL ROADMAP** - Four Epochs (Engine, Foundation, Game, Platform) |
| `epochs/epoch1-complete.md` | Epoch 1 completion record (13 Systems, 25 EventTypes, 4646 tests) |
| `epochs/epoch2/` | Epoch 2: The Foundation - data infrastructure, H3, PyQt |
| `epochs/epoch3/` | Epoch 3: The Game - game features (17 specs, renumbered from epoch2/) |
| `epochs/epoch4/` | Epoch 4: The Platform - DuckDB, RAG, API |
| `state.yaml` | Current project state, test counts, slice status |
| `architecture.yaml` | Technical Stack (Embedded Trinity: Ledger, Topology, Archive) |
| `tooling.yaml` | CI/CD, Testing, Parameter Tuning, Monte Carlo UQ |
| `formulas-spec.yaml` | All 31 mathematical formulas with signatures |
| `observer-layer.yaml` | Observer system, EventTypes, TopologyMonitor |

---

## THEORETICAL REFERENCE (YAML + RST)

| YAML | RST | Purpose |
|------|-----|---------|
| `theory.yaml` | `docs/concepts/theory.rst` | MLM-TW theoretical grounding |
| `carceral-equilibrium.yaml` | `docs/concepts/carceral-equilibrium.rst` | 70-year trajectory, revolution windows |
| `warlord-trajectory.yaml` | `docs/concepts/warlord-trajectory.rst` | Epoch 2 branching endgames |
| `terminal-crisis.yaml` | `docs/concepts/terminal-crisis.rst` | Crisis phases: plantation → death camp |
| `demographics.yaml` | `docs/reference/demographics.rst` | Mass Line: population blocks |
| `tuning-standard.yaml` | `docs/reference/tuning.rst` | 20-Year Entropy Standard |

---

## ARCHIVE (Do Not Read for Coding)

| Directory | Purpose |
|-----------|---------|
| `archive/pre_necropolis/` | Old specs from Phase-era nomenclature (pre-2025 pivot) |
| `archive/pre_necropolis/decisions_monolith.yaml` | Original monolithic ADR file (now split into decisions/) |

---

## Quick Reference by Epoch

### Epoch 1: The Engine - COMPLETE

See `epochs/epoch1-complete.md` for full completion record.

| Slice | Name | Status |
|-------|------|--------|
| 1.1 | Core Types | COMPLETE |
| 1.2 | Economic Flow | COMPLETE |
| 1.3 | Survival Calculus | COMPLETE |
| 1.4 | Consciousness Drift | COMPLETE |
| 1.5 | Synopticon Dashboard | COMPLETE |
| 1.6 | Endgame Resolution | COMPLETE |
| 1.7 | Graph Bridge | COMPLETE |
| 1.8 | Carceral Geography | COMPLETE |

### Epoch 2: The Foundation - IN PROGRESS

See `epochs/epoch2/overview.md` for specifications.

| Slice | Name | Status |
|-------|------|--------|
| 2.1 | 3NF Schema | COMPLETE |
| 2.2 | Census Loaders | COMPLETE |
| 2.3 | Economic Loaders | COMPLETE |
| 2.4 | Circulatory Loaders | COMPLETE |
| 2.5 | H3 Geographic System | PLANNED |
| 2.6 | PyQt Visualization | PLANNED |
| 2.7 | Schema Integration | PLANNED |

### Epoch 3: The Game - PLANNED

See `epochs/epoch3/overview.md` for specifications. All specs in `epochs/epoch3/`:

| Slice | File | Purpose |
|-------|------|---------|
| 3.1 | demographics-spec.yaml | Demographic Resolution |
| 3.2 | vanguard-economy.yaml | Cadre/Sympathizer/Reputation Resources |
| 3.3 | cohesion-mechanic.yaml | Internal Dynamics, Iron Law of Oligarchy |
| 3.4 | fog-of-war.yaml | Fish in Water Intel |
| 3.5 | gramscian-wire-vision.yaml | Narrative Warfare, Hegemony |
| 3.6 | repression-logic.yaml | State Repression Mechanics |
| 3.7 | state-attention-economy.yaml | State AI Threads |
| 3.8 | kinetic-warfare.yaml | Asymmetric Logistics, System Disruption |
| 3.9 | balkanization-spec.yaml | Territorial Fracture |
| 3.10 | doctrine-tree.yaml | Ideological Tech Tree, Line Struggle |
| 3.11 | strategy-layer.yaml | External Actions, Resource Traps |
| 3.12 | reactionary-subject.yaml | Class Basis of Fascism |

### Epoch 4: The Platform - VISION

See `epochs/epoch4/overview.md` for specifications.

---

## Architecture & Patterns

| File | Purpose |
|------|---------|
| `game-loop-architecture.yaml` | Engine/State separation, Systems, formulas |
| `entities.yaml` | 17 game entity types and relationships |
| `decisions/index.yaml` | Architecture Decision Records index (24 ADRs) |
| `ontology.yaml` | Domain terms (MLM-TW, architecture, game) |
| `patterns.yaml` | How to do things here |
| `anti-patterns.yaml` | What NOT to do |
| `mantras.yaml` | Guiding principles as memorable phrases |
| `pydantic-patterns.yaml` | Pydantic V2 models, validators, serialization |
| `documentation-standards.yaml` | Diataxis, RST format, docstrings |

**ADR Files:** Individual ADRs are in `decisions/` directory (e.g., `decisions/ADR001_embedded_trinity.yaml`)

---

## UI & Visualization

| File | Purpose |
|------|---------|
| `synopticon-spec.yaml` | Observer system architecture, Lens filter |
| `design-system.yaml` | Visual design: colors, typography, Bunker Constructivism |
| `ui-wireframes.yaml` | ASCII wireframes for complex systems |
| `echarts-patterns.yaml` | Apache ECharts chart configuration |
| `dpg-patterns.yaml` | DearPyGui patterns |

---

## Usage

When starting a session, an AI assistant should:
1. Read `ai-docs/epochs/overview.md` for current roadmap (Four Epochs)
2. Read `ai-docs/state.yaml` for current slice status and test counts
3. Reference `ai-docs/ontology.yaml` when encountering domain terms
4. Check `ai-docs/patterns.yaml` before implementing new features
5. Consult `ai-docs/decisions/index.yaml` to understand why things are the way they are

## Maintenance

Update these docs when:
- New domain concepts are introduced
- Architectural decisions are made
- Patterns emerge or change
- Mistakes are made (add to anti-patterns)
