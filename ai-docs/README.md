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
| `decisions.yaml` | Architecture Decision Records (ADR001-ADR013) | YAML |
| `patterns.yaml` | How to do things here | YAML |
| `anti-patterns.yaml` | What NOT to do | YAML |
| `game-data.yaml` | External data sources and CI/CD pipeline | YAML |
| `theory.md` | MLM-TW theoretical foundation | Markdown |

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
