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
| `state.yaml` | Current project state, sprint history, test counts | YAML |
| `architecture.yaml` | System structure, directory map, data flow | YAML |
| `game-loop-architecture.yaml` | Engine/State separation, Systems, formulas | YAML |
| `formulas-spec.yaml` | All 12 mathematical formulas with signatures | YAML |
| `entities.yaml` | 17 game entity types and relationships | YAML |
| `ontology.yaml` | Domain terms (MLM-TW, architecture, game) | YAML |
| `decisions.yaml` | Architecture Decision Records (ADR001-ADR024) | YAML |
| `patterns.yaml` | How to do things here | YAML |
| `anti-patterns.yaml` | What NOT to do | YAML |
| `mantras.yaml` | Guiding principles as memorable phrases | YAML |
| `tooling.yaml` | CI/CD, Sphinx, linting configuration | YAML |
| `ci-workflow.yaml` | GitHub Actions, branch protection, contributor workflow | YAML |
| `documentation-standards.yaml` | Diataxis, RST format, docstrings, accuracy rules | YAML |
| `game-data.yaml` | External data sources and CI/CD pipeline | YAML |
| `theory.md` | MLM-TW theoretical foundation | Markdown |
| `rag-architecture.yaml` | RAG as permission system, validation pipeline | YAML |
| `design-system.yaml` | Visual design: colors, typography, Bunker Constructivism | YAML |
| `synopticon-spec.yaml` | Observer system architecture, Lens filter, SynopticView | YAML |
| `nicegui-patterns.yaml` | NiceGUI development patterns, gotchas, quick reference | YAML |
| `tailwind-patterns.yaml` | Tailwind CSS patterns, arbitrary values, flexbox, sizing | YAML |
| `echarts-patterns.yaml` | Apache ECharts chart configuration, dynamic updates, styling | YAML |
| `quasar-patterns.yaml` | Quasar Framework components, props, dark mode | YAML |
| `asyncio-patterns.yaml` | Python asyncio, to_thread, callback detection, timers | YAML |
| `jsoneditor-patterns.yaml` | JSON Editor (svelte-jsoneditor), run_editor_method API | YAML |
| `pydantic-patterns.yaml` | Pydantic V2 models, validators, serialization, constrained types | YAML |

## Usage

When starting a session, an AI assistant should:
```
1. Read ai-docs/state.yaml to understand current project state
2. Reference ai-docs/ontology.yaml when encountering domain terms
3. Check ai-docs/patterns.yaml before implementing new features
4. Consult ai-docs/decisions.yaml to understand why things are the way they are
```

## Maintenance

Update these docs when:
- New domain concepts are introduced
- Architectural decisions are made
- Patterns emerge or change
- Mistakes are made (add to anti-patterns)
