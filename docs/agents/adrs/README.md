# Architecture Decision Records

Markdown ADRs for the Babylon refactoring sequence. Each ADR is one "phase" — a single conventional commit unit per CLAUDE.md, sized to be picked up by spec-kit (`/speckit.specify` → `/speckit.plan` → `/speckit.tasks` → `/speckit.implement`).

## Why ADRs here, not in `ai-docs/decisions.yaml`?

The YAML file in `ai-docs/decisions.yaml` records *accepted* architectural decisions as immutable history. The ADRs here are **proposed** refactors awaiting implementation. Once implemented, each ADR's outcome is summarized into a YAML entry in `ai-docs/decisions.yaml`; the markdown stays as the in-flight design document.

## Index

| #                                                  | Tier  | Title                                                              | Status   | Effort | Risk   |
| -------------------------------------------------- | ----- | ------------------------------------------------------------------ | -------- | ------ | ------ |
| [001](ADR-001-mechanical-file-splits.md)           | T1    | Mechanical splits — `defines.py`, `enums.py`, OODA helper dedup    | Proposed | 1.5 d  | Low    |
| [002](ADR-002-protocol-kit-and-source-registry.md) | T1    | `protocol_kit` + `SourceRegistry` for the Protocol+Default pattern | Proposed | 2 d    | Low    |
| [003](ADR-003-system-abc.md)                       | T2    | Lift `System` Protocol into a true ABC with shared scaffolding     | Proposed | 1 d    | Low    |
| [004](ADR-004-discriminated-event-union.md)        | T2    | Discriminated `TickEvent` union replaces `deserialize_event`       | Proposed | 2 d    | Medium |
| [005](ADR-005-god-class-decomposition.md)          | T1+T2 | Decompose `postgres_runtime.py` and `engine/simulation.py`         | Proposed | 5 d    | Medium |
| [006](ADR-006-cleanup-batch.md)                    | T3    | Scenario ABC + remaining splits + orphan schemas                   | Proposed | 3 d    | Low    |

## Format

Each ADR follows this template — keep them tight, evidence-driven, and grounded in `.understand-anything/knowledge-graph.json`:

```markdown
# ADR-NNN: Title

**Status**: Proposed | Accepted | Implemented | Superseded by ADR-XXX
**Date**: YYYY-MM-DD
**Phase**: N of 6
**Tier**: T1 | T2 | T3
**Estimated effort**: X days
**Risk**: Low | Medium | High

## Context
What's broken; cite files + line counts.

## Decision
Concrete approach: directory layout, class shapes, code sketches.

## Consequences
### Positive
### Negative / tradeoffs

## Acceptance criteria
- [ ] checklist

## Rollout
Sequenced commit boundaries.

## Test strategy
How to verify each step preserves behavior.

## References
Knowledge graph nodes, related ADRs, CLAUDE.md sections.
```

## Provenance

This refactoring sequence emerged from analysis of the knowledge graph at `.understand-anything/knowledge-graph.json` (1685 nodes, 3733 edges) generated 2026-05-05 from commit `7710461b`. The graph identified the high-leverage splits (god-class files, repeated `Protocol+Default` patterns, hub nodes by import in-degree) with concrete LOC and dependency counts.

To re-derive: run `/understand-anything:understand` and inspect:

- Top in-degree nodes via `nodes`/`edges` joins (most-imported files)
- Class-suffix histograms (`Calculator`, `Source`, `Computer`, etc.)
- File-level node `summary` and `tags` for refactor signals
