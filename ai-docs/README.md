# Babylon AI Documentation Context

Machine-readable documentation for LLM-assisted development.

This directory helps AI assistants understand context, use correct terminology, follow established patterns, avoid known pitfalls, and make decisions aligned with project philosophy.

---

## ACTIVE SPECS (The Truth)

| File | Purpose |
|------|---------|
| `epochs-overview.md` | **CANONICAL ROADMAP** - Epoch + Slice model (Epoch 1-5) |
| `epoch1-mvp-complete.md` | Current System State & Physics (Material Reality) |
| `state.yaml` | Current project state, test counts, slice status |
| `architecture.yaml` | Technical Stack (Embedded Trinity: Ledger, Topology, Archive) |
| `tooling.yaml` | CI/CD, Testing, Parameter Tuning, Monte Carlo UQ |
| `formulas-spec.yaml` | All 16 mathematical formulas with signatures |
| `observer-layer.yaml` | Observer system, EventTypes, TopologyMonitor |

---

## THEORETICAL REFERENCE

| File | Purpose |
|------|---------|
| `theory.md` | MLM-TW / Necropolitics theoretical grounding |
| `carceral-equilibrium.md` | Default 70-year trajectory, revolution windows, necropolis equilibrium |
| `warlord-trajectory.md` | Epoch 2 branching: Classical Concentration vs Warlord Coup endgames |
| `terminal-crisis-dynamics.md` | Crisis phase mechanics: plantation -> prison -> concentration -> genocide |
| `demographics_and_mortality.md` | Mass Line Refactor: population blocks, grinding attrition |

---

## ARCHIVE (Do Not Read for Coding)

| Directory | Purpose |
|-----------|---------|
| `archive/pre_necropolis/` | Old specs from Phase-era nomenclature (pre-2025 pivot) |

---

## Quick Reference by Slice

### Epoch 1 (The Demonstration) - MVP COMPLETE

| Slice | File | Status |
|-------|------|--------|
| 1.4 The Rift | `metabolic-slice.yaml` | VALIDATED |
| 1.5 Gramscian Wire MVP | `gramscian-wire-mvp.yaml` | 90% |
| 1.6 Endgame Detector | (in epochs-overview.md) | PLANNED |
| 1.7 Graph Bridge | (in epochs-overview.md) | PLANNED |

### Epoch 2 (The Game) - PLANNED

| Slice | File | Purpose |
|-------|------|---------|
| 2.1 Demographics | `demographics-spec.yaml` | Demographic Resolution |
| 2.2a Strategy Layer | `strategy-layer.yaml` | External Actions, Resource Traps |
| 2.2b The Vanguard | `cohesion-mechanic.yaml` | Internal Dynamics, Iron Law of Oligarchy |
| 2.3 Reactionary Subject | `reactionary-subject.yaml` | Class Basis of Fascism |
| 2.5 The Wire | `gramscian-wire-vision.yaml` | Narrative Warfare, Hegemony |
| 2.6 Vanguard Economy | `vanguard-economy.yaml` | Cadre/Sympathizer/Reputation Resources |
| 2.7 Kinetic Warfare | `kinetic-warfare.yaml` | Asymmetric Logistics, System Disruption |
| 2.8 Doctrine System | `doctrine-tree.yaml` | Ideological Tech Tree, Line Struggle |
| 2.9 The Panopticon | `state-attention-economy.yaml` | State AI Threads |
| 2.10 Epistemic Horizon | `fog-of-war.yaml` | Fish in Water Intel |

---

## Architecture & Patterns

| File | Purpose |
|------|---------|
| `game-loop-architecture.yaml` | Engine/State separation, Systems, formulas |
| `entities.yaml` | 17 game entity types and relationships |
| `decisions.yaml` | Architecture Decision Records (ADR001-ADR039+) |
| `ontology.yaml` | Domain terms (MLM-TW, architecture, game) |
| `patterns.yaml` | How to do things here |
| `anti-patterns.yaml` | What NOT to do |
| `mantras.yaml` | Guiding principles as memorable phrases |
| `pydantic-patterns.yaml` | Pydantic V2 models, validators, serialization |
| `documentation-standards.yaml` | Diataxis, RST format, docstrings |

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
1. Read `ai-docs/epochs-overview.md` for current roadmap (Epoch + Slice model)
2. Read `ai-docs/state.yaml` for current slice status and test counts
3. Reference `ai-docs/ontology.yaml` when encountering domain terms
4. Check `ai-docs/patterns.yaml` before implementing new features
5. Consult `ai-docs/decisions.yaml` to understand why things are the way they are

## Maintenance

Update these docs when:
- New domain concepts are introduced
- Architectural decisions are made
- Patterns emerge or change
- Mistakes are made (add to anti-patterns)
