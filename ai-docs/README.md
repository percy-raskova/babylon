# AI Documentation

Machine-readable documentation for LLM-assisted development.

## Purpose

This directory helps AI assistants:
1. **Understand context** without re-reading the entire codebase
2. **Use correct terminology** specific to this project
3. **Follow established patterns** rather than inventing new ones
4. **Avoid known pitfalls** documented from past mistakes
5. **Make decisions** aligned with project philosophy

## Files

| File | Purpose | Format |
|------|---------|--------|
| **ROADMAP & STATUS** |||
| `epochs-overview.md` | **CANONICAL ROADMAP** - Epoch + Slice model | Markdown |
| `state.yaml` | Current project state, test counts, slice status | YAML |
| `roadmap.md` | ~~Old Phase-based roadmap~~ (DEPRECATED - see epochs-overview.md) | Markdown |
| **SPECIFICATIONS** |||
| `metabolic-slice.yaml` | Slice 1.4 spec - MetabolismSystem, biocapacity | YAML |
| `gramscian-wire-mvp.yaml` | Slice 1.5 spec - Dual narrative display (Epoch 1) | YAML |
| `demographics-spec.yaml` | Slice 2.1 spec - Demographic Resolution | YAML |
| `strategy-layer.yaml` | Slice 2.2a spec - External Actions, Resource Traps | YAML |
| `cohesion-mechanic.yaml` | Slice 2.2b spec - Internal Dynamics, Iron Law of Oligarchy | YAML |
| `gramscian-wire-vision.yaml` | Slice 2.4 spec - Narrative Warfare, Hegemony (Epoch 2) | YAML |
| `formulas-spec.yaml` | All 16 mathematical formulas with signatures | YAML |
| `observer-layer.yaml` | Observer system, EventTypes, TopologyMonitor | YAML |
| **ARCHITECTURE** |||
| `architecture.yaml` | System structure, directory map, data flow | YAML |
| `game-loop-architecture.yaml` | Engine/State separation, Systems, formulas | YAML |
| `entities.yaml` | 17 game entity types and relationships | YAML |
| `decisions.yaml` | Architecture Decision Records (ADR001-ADR028) | YAML |
| **PATTERNS & STANDARDS** |||
| `ontology.yaml` | Domain terms (MLM-TW, architecture, game) | YAML |
| `patterns.yaml` | How to do things here | YAML |
| `anti-patterns.yaml` | What NOT to do | YAML |
| `mantras.yaml` | Guiding principles as memorable phrases | YAML |
| `documentation-standards.yaml` | Diataxis, RST format, docstrings, accuracy rules | YAML |
| **TOOLING & CI** |||
| `tooling.yaml` | CI/CD, Sphinx, linting, mutation testing | YAML |
| `ci-workflow.yaml` | GitHub Actions, branch protection, contributor workflow | YAML |
| **DESIGN & THEORY** |||
| `design-system.yaml` | Visual design: colors, typography, Bunker Constructivism | YAML |
| `theory.md` | MLM-TW theoretical foundation | Markdown |
| `rag-architecture.yaml` | RAG as permission system, validation pipeline | YAML |
| **UI PATTERNS** |||
| `synopticon-spec.yaml` | Observer system architecture, Lens filter, SynopticView | YAML |
| `nicegui-patterns.yaml` | NiceGUI development patterns, gotchas, quick reference | YAML |
| `tailwind-patterns.yaml` | Tailwind CSS patterns, arbitrary values, flexbox, sizing | YAML |
| `echarts-patterns.yaml` | Apache ECharts chart configuration, dynamic updates, styling | YAML |
| `quasar-patterns.yaml` | Quasar Framework components, props, dark mode | YAML |
| `asyncio-patterns.yaml` | Python asyncio, to_thread, callback detection, timers | YAML |
| `jsoneditor-patterns.yaml` | JSON Editor (svelte-jsoneditor), run_editor_method API | YAML |
| `pydantic-patterns.yaml` | Pydantic V2 models, validators, serialization, constrained types | YAML |
| `game-data.yaml` | External data sources and CI/CD pipeline | YAML |

## Usage

When starting a session, an AI assistant should:
```
1. Read ai-docs/epochs-overview.md for current roadmap (Epoch + Slice model)
2. Read ai-docs/state.yaml for current slice status and test counts
3. Reference ai-docs/ontology.yaml when encountering domain terms
4. Check ai-docs/patterns.yaml before implementing new features
5. Consult ai-docs/decisions.yaml to understand why things are the way they are
```

For implementation work:
- **Slice 1.4** (The Rift): See `ai-docs/metabolic-slice.yaml`
- **Slice 1.5** (Gramscian Wire MVP): See `ai-docs/gramscian-wire-mvp.yaml`
- **Slice 2.1** (Demographics): See `ai-docs/demographics-spec.yaml`
- **Slice 2.2a** (Strategy Layer): See `ai-docs/strategy-layer.yaml`
- **Slice 2.2b** (The Vanguard): See `ai-docs/cohesion-mechanic.yaml`
- **Slice 2.4** (The Wire): See `ai-docs/gramscian-wire-vision.yaml`

## Maintenance

Update these docs when:
- New domain concepts are introduced
- Architectural decisions are made
- Patterns emerge or change
- Mistakes are made (add to anti-patterns)
