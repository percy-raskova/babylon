# Babylon Wiki Log

Chronological record of wiki ingests and maintenance operations.

## [2026-04-28] ingest | Initial wiki creation

**Source**: AGENTS.md refactor (commit e8301106)
**Pages Created**: architecture.md, coding-standards.md, testing.md, commands.md, gotchas.md, governance.md, index.md
**Pages Updated**: AGENTS.md (rewritten as index/schema)
**Cross-references Added**: All wiki pages linked from index.md; AGENTS.md links to all wiki pages
**Open Questions**: None

## [2026-04-28] ingest | Constitution v2.6.1 + Specification skills

**Source**: Constitution amendment cycle + specification skill framework (commit 81004ac1)
**Pages Created**: N/A (specs live in .specify/)
**Pages Updated**: .specify/memory/constitution.md, .specify/memory/data-catalog.yaml
**Cross-references Added**: See Also annotations between I.21↔II.5↔I.16, I.18↔II.7↔VIII.9
**Open Questions**: Amendment C deferred to v2.8.0; Amendments B and D still pending

## [2026-04-29] ingest | Branch merge + Wiki lint + Skill documentation

**Source**: feature/045-mvp-mock-progression merged into dev; main force-overwritten by dev; wiki lint pass
**Pages Created**: `.opencode/skills/wiki-maintain/SKILL.md`
**Pages Updated**:

- `docs/agents/architecture.md` — added MetabolismSystem (8th system), fixed system count
- `docs/agents/index.md` — added Agent Skills section with all 7 OpenCode skills; linked log.md properly
- `docs/agents/log.md` — appended this entry
  **Cross-references Added**:
- index.md → log.md (proper link)
- index.md → all 7 specification + wiki skills
  **Lint Findings Resolved**:
- Fixed contradiction: architecture.md now lists 8 systems (was 7)
- Fixed orphan: log.md now properly linked from index.md
- Added missing skill documentation to index
  **Open Questions**: Should we add a dedicated `docs/agents/skills.md` page with detailed skill usage examples?

## [2026-05-05] ingest | ADR sequence from knowledge-graph analysis

**Source**: `/understand-anything:understand` knowledge-graph build (commit `7710461b`, 1685 nodes, 3733 edges) + `/understand-anything:understand-chat` architectural review.
**Pages Created**:

- `docs/agents/adrs/README.md` — ADR index, format template, provenance.
- `docs/agents/adrs/ADR-001-mechanical-file-splits.md` — split `defines.py` (4157 LOC) + `enums.py` (1298 LOC); dedup `_compute_membership_overlap`.
- `docs/agents/adrs/ADR-002-protocol-kit-and-source-registry.md` — generic `CachedSource` ABC + `SourceRegistry` to replace 7 hand-rolled `create_*_services()` and 61 `Default*` boilerplates.
- `docs/agents/adrs/ADR-003-system-abc.md` — `SystemBase` ABC for the 23 engine Systems with shared `_read`/`_write`/`_publish` helpers.
- `docs/agents/adrs/ADR-004-discriminated-event-union.md` — Pydantic 2 discriminated union over the 22 Event variants; remove `deserialize_event`.
- `docs/agents/adrs/ADR-005-god-class-decomposition.md` — composition decomposition of `postgres_runtime.py` (1955 LOC, 1 class, 53 methods) and `engine/simulation.py` (1048 LOC).
- `docs/agents/adrs/ADR-006-cleanup-batch.md` — `Scenario` ABC, remaining splits (`circulation/types.py`, `tick/system.py`, `edge_transition.py`), typed BEA mapping, orphan-schema audit.
  **Pages Updated**:
- `docs/agents/index.md` — added "Architecture Decision Records" section linking the ADR index + all six ADRs.
- `docs/agents/log.md` — appended this entry.
  **Cross-references Added**:
- ADRs 002–006 each cite ADR-001's package-split shape; ADR-005 + ADR-006 cite ADR-003's `SystemBase`.
- Each ADR cross-references CLAUDE.md "Common Gotchas" and "Coding Standards" sections relevant to the change.
- Each ADR cites specific knowledge-graph node IDs (file paths + LOC + in-degree) so the evidence is auditable.
  **Open Questions**:
- Should accepted/implemented ADRs eventually mirror into `ai-docs/decisions.yaml` (the immutable history file), or stay in markdown?
- Recommended capture flow when an ADR ships: append `ai-docs/decisions.yaml` entry + flip ADR status header to `Implemented`.
- ADRs are meant to be picked up by spec-kit (`/speckit.specify` → `.../implement`) one phase at a time; first candidate is ADR-001.
