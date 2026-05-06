# ADR-001: Mechanical splits — `defines.py`, `enums.py`, OODA helper dedup

**Status**: Proposed
**Date**: 2026-05-05
**Phase**: 1 of 6
**Tier**: T1
**Estimated effort**: 1.5 days
**Risk**: Low

## Context

Three of the most-imported files in the project are oversized barrel modules. Edits in any one trigger import-cascades across dozens of files and slow down `mypy --strict`.

Evidence (from `.understand-anything/knowledge-graph.json` and `wc -l`):

| File                                                     | Lines |             In-degree |                         Internal classes |
| -------------------------------------------------------- | ----: | --------------------: | ---------------------------------------: |
| `src/babylon/models/enums.py`                            |  1298 | 90 (#1 most-imported) |                                 25 enums |
| `src/babylon/config/defines.py`                          |  4157 | 65 (#2 most-imported) |                 42 `*Defines(BaseModel)` |
| `src/babylon/ooda/action_costs.py` + `action_effects.py` |     — |                     — | duplicates `_compute_membership_overlap` |

The internal classes inside `enums.py` and `defines.py` are independent — there is no circular reference, no shared base — so this is purely a packaging problem. The OODA duplication was flagged by the file-analyzer with the `duplication` tag during the knowledge-graph build.

`defines.py` houses domain-specific Pydantic categories: e.g. `OODADefines` is 441 lines, `StateApparatusAIDefines` is 480 lines. Either file alone exceeds CLAUDE.md's 100-line-per-function guidance for the file as a whole and forces every consumer of any single Defines category to depend on all 42.

## Decision

Convert each oversized barrel into a package with a backward-compatible `__init__.py` that re-exports every symbol. **No public import path changes.**

### `models/enums.py` → `models/enums/`

```
src/babylon/models/enums/
├── __init__.py             # `from .topology import *`, etc.; preserves `from babylon.models.enums import EdgeType`
├── topology.py             # EdgeType, EdgeMode, TopologyType
├── social.py               # SocialRole, ClassCharacter, MembershipRole, OrgType
├── consciousness.py        # ConsciousnessTendency, IntensityLevel, ContradictionCharacter, ContradictionType
├── territory.py            # TerritoryType, OperationalProfile, SectorType, DisplacementPriorityMode
├── events.py               # EventType, ResolutionType, GameOutcome
├── legal.py                # LegitimationClassification, LegalStatus, LegalStanding, DispossessionType, ExploitationMode
├── community.py            # CommunityType, HyperedgeCategory
└── _resolution.py          # resolve_edge_type() helper
```

### `config/defines.py` → `config/defines/`

Keep `GameDefines` as the assembler facade in `config/defines/__init__.py`. Each category becomes its own file:

```
src/babylon/config/defines/
├── __init__.py             # GameDefines + re-exports of every *Defines class
├── _assembler.py           # Composition / loading from pyproject.toml [tool.babylon]
├── crisis.py               # CrisisDefines
├── economy.py              # EconomyDefines
├── consciousness.py        # ConsciousnessDefines
├── struggle.py             # StruggleDefines, AidDefines, CarceralDefines
├── territory.py            # TerritoryDefines, InfraTerrainDefines, InfrastructureDefines
├── ooda.py                 # OODADefines (441 LOC)
├── state_apparatus.py      # StateApparatusAIDefines (480 LOC)
├── ...
└── tunables.py             # PrecisionDefines, ServicesDefines, TimescaleDefines, ExternalDataDefines
```

Group categories that already cross-reference each other in the same file. Co-locate `LifecycleDefines` + `OrganizationDefines` only if they share fields — otherwise keep separate.

### `_compute_membership_overlap` dedup

Move the function to `src/babylon/ooda/_helpers.py`. Update both `action_costs.py` and `action_effects.py` to import it. Single canonical implementation.

## Consequences

### Positive

- Editing `OODADefines` no longer invalidates the bytecode cache for 65 importers.
- Per-category test isolation: `from babylon.config.defines.economy import EconomyDefines` lets unit tests avoid loading the whole tree.
- Aligns with CLAUDE.md guidance on keeping logical units file-scoped.
- One canonical `_compute_membership_overlap` removes a future drift risk.

### Negative / tradeoffs

- Adds 25–35 new files. Mostly mechanical — git history preserves provenance via `git log --follow`.
- `defines/__init__.py` will be large (~50 lines of re-exports). Acceptable cost for the public API stability.

## Acceptance criteria

- [ ] `from babylon.models.enums import EdgeType` (and every other existing enum import) still works without change.
- [ ] `from babylon.config.defines import GameDefines` (and every existing `*Defines` import) still works.
- [ ] `mise run check` passes with zero new mypy/ruff findings.
- [ ] No file in the new packages exceeds 600 lines.
- [ ] `_compute_membership_overlap` exists in exactly one location; both old call sites import from `ooda._helpers`.
- [ ] `git grep -n "from babylon.models.enums"` and `git grep -n "from babylon.config.defines"` return identical line counts before and after.

## Rollout

Three commits, in order:

1. **`refactor(ooda): extract _compute_membership_overlap helper`**

   - Add `ooda/_helpers.py` with the function.
   - Update `action_costs.py` and `action_effects.py` to import from `_helpers`.
   - Delete the duplicate in `action_effects.py`.

1. **`refactor(models): split enums.py into enums/ package`**

   - Create `models/enums/` with category files + `__init__.py` re-export.
   - Delete `models/enums.py`.
   - Verify import equivalence with `git grep` diff.

1. **`refactor(config): split defines.py into defines/ package`**

   - Same shape as #2 but for `config/defines/`.
   - Keep `GameDefines` assembler in `__init__.py`.
   - Verify `pyproject.toml [tool.babylon]` loading still works.

## Test strategy

- `mise run test:unit` between each commit (fast feedback).
- `mise run check` (lint + format + typecheck + test:unit) before each push.
- Specific assertions:
  - `pytest tests/ -k "test_defines"` — passes unchanged.
  - `python -c "from babylon.config.defines import GameDefines; GameDefines()"` — succeeds.
  - `python -c "from babylon.models import enums; print(len([n for n in dir(enums) if not n.startswith('_')]))"` — same count as before.
- Optional: `pytest --collect-only` before/after — should yield identical test set.

## References

- Knowledge graph nodes:
  - `file:src/babylon/models/enums.py` (in-degree 90)
  - `file:src/babylon/config/defines.py` (in-degree 65)
  - `function:src/babylon/ooda/action_effects.py:_compute_membership_overlap` (tagged `duplication`)
- Related ADRs: ADR-002 will reference categories established here.
- CLAUDE.md sections: "Coding Standards" (Pydantic First, Strict Typing), "Common Gotchas" (Mypy misses Pydantic attribute errors).
