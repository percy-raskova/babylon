---
name: wiki-maintain
description: Maintain the Babylon project wiki following the Karpathy LLM Wiki pattern. Use when ingesting new knowledge, updating cross-references, linting for contradictions, or keeping agent documentation current with code changes.
---

# Wiki Maintenance Skill

## Purpose

Maintain a persistent, compounding knowledge base for the Babylon project. The wiki lives in `docs/agents/`, `ai-docs/`, and `.specify/`. This skill ensures knowledge accumulates rather than being re-derived every session.

## Architecture (Karpathy Pattern)

**Three layers:**

1. **Raw Sources** (immutable) — Code, specs, constitution, data catalog
1. **Wiki** (LLM-maintained) — `docs/agents/*.md`, `ai-docs/*.yaml`, `.specify/plans/`, `.specify/specs/`
1. **Schema** (this skill + AGENTS.md) — Tells the LLM how to structure and maintain the wiki

## Operations

### 1. Ingest

When new information enters the project, integrate it into the wiki.

**Trigger:** After completing any significant work — new code, ratified specs, architectural decisions, data source additions.

**Procedure:**

1. **Identify what changed** — New/modified files, new concepts, new dependencies
1. **Update relevant wiki pages** — Read existing pages, update them with new information
1. **Create new pages if needed** — When a concept lacks its own page
1. **Update cross-references** — Link new pages to related existing pages
1. **Update the index** — Regenerate `docs/agents/index.md`
1. **Append to the log** — Record the ingest in `docs/agents/log.md`

**Babylon-specific pages to maintain:**

| Page                              | When to Update                                         |
| --------------------------------- | ------------------------------------------------------ |
| `docs/agents/architecture.md`     | New systems, API changes, formula additions            |
| `docs/agents/coding-standards.md` | New patterns, tool changes, convention updates         |
| `docs/agents/testing.md`          | New test patterns, fixture changes, marker additions   |
| `docs/agents/commands.md`         | New mise tasks, changed CLI interfaces                 |
| `docs/agents/gotchas.md`          | New debugging lessons, common pitfalls discovered      |
| `docs/agents/governance.md`       | Workflow changes, branch policy updates                |
| `ai-docs/decisions.yaml`          | New ADRs ratified                                      |
| `ai-docs/state.yaml`              | Test counts, component status changes                  |
| `.specify/memory/constitution.md` | Only via `specification-govern` skill — never directly |

**Ingest Log Format** (`docs/agents/log.md`):

```markdown
## [YYYY-MM-DD] ingest | Brief Description

**Source**: What changed (PR, commit, spec ratification)
**Pages Updated**: List of wiki pages modified
**Pages Created**: List of new wiki pages
**Cross-references Added**: What now links to what
**Open Questions**: Anything unresolved
```

### 2. Query

Answer questions by reading the wiki, not by re-deriving from code.

**Trigger:** When asked about project structure, patterns, history, or "how does X work?"

**Procedure:**

1. **Read the index** — `docs/agents/index.md` to find relevant pages
1. **Read relevant pages** — Load 2-5 most relevant wiki files
1. **Synthesize with citations** — Quote specific files, don't hallucinate
1. **If answer is incomplete** — Flag gaps in the wiki for future ingest

**Never** answer from memory when the wiki contains the authoritative information.

### 3. Lint

Health-check the wiki for consistency.

**Trigger:** When explicitly asked, or when a page hasn't been updated in 30+ days.

**Procedure:**

1. **Read the index** — `docs/agents/index.md`
1. **Check for contradictions** — Scan pages for conflicting claims
1. **Find orphan pages** — Pages with no inbound links from other wiki pages
1. **Identify stale claims** — Claims that newer code/sources have superseded
1. **Find missing cross-references** — Concepts mentioned but not linked
1. **Check index completeness** — Every wiki page listed in index?
1. **Report findings** — List issues with recommended fixes

**Lint Report Format:**

```markdown
## Wiki Lint Report — YYYY-MM-DD

### Contradictions
- [ ] Page A claims X, Page B claims not-X (lines N, M)

### Orphan Pages
- [ ] `docs/agents/foo.md` — no inbound links

### Stale Claims
- [ ] `docs/agents/bar.md` says System Y does Z, but code shows it does W

### Missing Cross-references
- [ ] Page C mentions "Dialectic Primitive" but doesn't link to constitution

### Recommended Actions
1. Fix contradiction by...
2. Link orphan page from...
```

## Index Maintenance

`docs/agents/index.md` is the content-oriented catalog. Regenerate it after every ingest.

**Format:**

```markdown
# Babylon Wiki Index

## Architecture
- [Architecture Overview](architecture.md) — Trinity, engine systems, formulas
- [Coding Standards](coding-standards.md) — Pydantic, TDD, commits, docstrings

## Operations
- [Testing](testing.md) — Test constants, factories, fixtures, markers
- [Commands](commands.md) — mise tasks reference
- [Gotchas](gotchas.md) — Common pitfalls and debugging lessons

## Governance
- [Governance](governance.md) — Git workflow, session continuity

## Specifications
- Plans: `.specify/plans/`
- Specs: `.specify/specs/`
- Constitution: `.specify/memory/constitution.md`
- Data Catalog: `.specify/memory/data-catalog.yaml`

## AI State
- Decisions: `ai-docs/decisions.yaml`
- Roadmap: `ai-docs/roadmap.md`
- State: `ai-docs/state.yaml`
```

## Rules

- **Never modify the constitution** (`.specify/memory/constitution.md`) through this skill. Use `specification-govern` for constitutional changes.
- **Never delete wiki pages** without user approval. Orphan pages should be linked, not removed.
- **Always update the index** after creating or significantly modifying any wiki page.
- **Always append to the log** after every ingest operation.
- **Prefer updating existing pages** over creating new ones. The wiki should be dense, not sprawling.
- **Cross-reference aggressively** — Every concept should link to its authoritative definition.
