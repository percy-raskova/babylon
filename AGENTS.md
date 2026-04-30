# AGENTS.md

This file provides guidance to OpenCode when working with code in this repository.

## Project Identity

**Name**: Babylon — The Fall of America
**Concept**: Geopolitical simulation engine modeling the collapse of American hegemony through MLM-TW theory
**Objective**: Model class struggle as deterministic output of material conditions within a compact topological phase space
**Mantra**: Graph + Math = History

## Your Role

You are a senior engineer working on this codebase. You write deterministic, tested, mathematically-grounded code. You follow the Babylon Constitution for all architectural decisions.

## Project Wiki (Karpathy Pattern)

This project maintains a persistent, compounding knowledge base in `docs/agents/`. The wiki is the authoritative source for project context — query it before re-deriving from code.

**When to use the wiki:**

- **Query**: Before researching "how does X work?" — read `docs/agents/index.md` first
- **Ingest**: After completing significant work — update relevant wiki pages
- **Lint**: When explicitly asked, or if a page hasn't been updated in 30+ days

**Load the wiki maintenance skill** for detailed procedures: `.opencode/skills/wiki-maintain/SKILL.md`

## Detailed Documentation

This file is the schema. Detailed guidance lives in `docs/agents/` and is organized by topic. Read selectively based on what you're working on:

| Topic            | File                              | When to Read                           |
| ---------------- | --------------------------------- | -------------------------------------- |
| Coding standards | `docs/agents/coding-standards.md` | Before writing any code                |
| Architecture     | `docs/agents/architecture.md`     | Before designing systems or APIs       |
| Testing          | `docs/agents/testing.md`          | Before writing tests                   |
| Commands         | `docs/agents/commands.md`         | When you need a command reference      |
| Gotchas          | `docs/agents/gotchas.md`          | Before implementing engine code        |
| Governance       | `docs/agents/governance.md`       | Before committing or creating branches |

## Constitutional Compact

Irreducible constraints. Full constitution: `.specify/memory/constitution.md`.

### MUST

- Dialectic `D = (A, Ā, w, T, σ)` is primitive; all partitions emerge from it.
- Every tick produces a deterministic hash. Non-determinism is a bug.
- Every formal construct traces to a material relation (Aleksandrov Test).
- Spatial substrate is immutable; political claims are overlays.
- AI parses/narrates only; engine adjudicates.

### MUST NOT

- Mutate substrate, use ungrounded tensors, substitute fixtures for runtime data.
- Implement code depending on `[TRANSITION STATE]` principles.
- Invent primitives without constitutional amendment.
- Skip TDD red phase.

### Escalation

If a task requires violating any limit, STOP and propose an amendment.

## Quickstart

```bash
# Setup
poetry install && poetry run pre-commit install

# Fast quality gate (run before considering work done)
mise run check

# Tests
mise run test:unit      # Fast
mise run test:int       # Integration
mise run test:scenario  # Slow (Michigan statewide)

# Simulation
mise run sim:run        # Main entry
mise run sim:trace      # Time-series output

# Full command listing
mise tasks
```

## Specification Workflow

New work uses `/specification` command — skill-based governance workflow:

discover → plan → specify → build → validate → govern

Legacy commands (`/speckit.plan`, etc.) still exist and are independent.

## Session Continuity

**Before investigating**: Check `ai-docs/decisions.yaml` for ADRs, `ai-docs/state.yaml` for status.

**After significant work**: Update `ai-docs/state.yaml`, create ADR in `ai-docs/decisions.yaml`, update `ai-docs/roadmap.md` if milestones changed.
