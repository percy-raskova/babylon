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
