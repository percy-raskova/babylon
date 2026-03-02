# Research: Institution Base Model

**Date**: 2026-03-02
**Feature**: 040-institution-base-model

## R1: Entity Storage Pattern (GraphProtocol Integration)

**Decision**: Institutions will be stored as graph nodes with `_node_type="institution"`, following the established pattern for organizations and key figures.

**Rationale**: The codebase has a consistent pattern for entity storage:
1. Define frozen Pydantic model in `src/babylon/models/entities/`
2. Add `dict[str, InstitutionType]` field to `WorldState`
3. Serialize via `model_dump()` in `WorldState.to_graph()` with `_node_type="institution"`
4. Reconstruct in `WorldState.from_graph()` with type dispatch
5. Query via `graph.query_nodes(node_type="institution")`

This is how `organization` (Feature 031) and `key_figure` nodes were added.

**Alternatives considered**:
- Separate data structure outside graph: Rejected — breaks graph traversal and query patterns
- Embedded as Organization attributes: Rejected — spec requires distinct third layer

## R2: Existing Organization Model Fields to Deprecate

**Decision**: `Organization.is_institution` (bool, default=False) and `Organization.institutional_persistence` (float|None) will be deprecated in favor of the new Institution entity.

**Rationale**: Research found:
- `is_institution` is used in `ooda/action_eligibility.py:142-143` to gate ASSIMILATE action
- `institutional_persistence` is cross-validated: must be None when `is_institution=False`
- Both fields exist on the base Organization class at `models/entities/organization.py:113-209`

Deprecation approach: Keep fields on Organization with `DeprecationWarning`, add migration path where `is_institution=True` orgs should reference an Institution entity instead.

## R3: Feature 039 Model Pattern

**Decision**: Follow Feature 039's exact model pattern for Institution entities.

**Rationale**: Feature 039 (State Apparatus AI) provides the most recent and relevant precedent:
- Enums as `StrEnum` in `models/enums.py` with feature comment headers
- Entity models in `models/entities/<name>.py` with `ConfigDict(frozen=True)`
- Module-level `frozenset` constants for valid string literals
- `@model_validator(mode="after")` for cross-field invariants (e.g., weights sum to 1.0)
- `@computed_field` for derived state (e.g., `dominant_faction`)
- New `EventType` values appended to existing enum

Key files from 039:
- `models/entities/state_apparatus_ai.py` — FactionBalance (sum-to-1.0 pattern), StateBudget, StateAction
- `models/entities/attention_thread.py` — AttentionThread, SparrowAnalysis

## R4: FactionBalance vs InternalBalanceOfForces

**Decision**: Reuse the sum-to-1.0 pattern from Feature 039's `FactionBalance` but create a new `InternalBalanceOfForces` model with different faction types.

**Rationale**: Feature 039's `FactionBalance` has three fractions (finance_capital, security_state, settler_populist) with a `@model_validator` enforcing sum=1.0 and a `@computed_field` for `dominant_faction`. The Institution spec requires three different fractions (Liberal-Technocratic, Revanchist-Fascist, Institutionalist-Bonapartist). Same mathematical pattern, different semantic domain. No code reuse possible — the fractions represent different things.

**Alternatives considered**:
- Generic weighted-fraction base class: Over-engineering for two uses. Rejected per "no abstractions for single-use code."

## R5: Structural Selectivity Data File Format

**Decision**: Use a YAML file in `src/babylon/data/game/` defining default action modifiers per ApparatusType, loaded through a new `InstitutionDefines` section in `GameDefines`.

**Rationale**: The project uses `GameDefines` (Pydantic model loaded from `defines.yaml`) for all tunable coefficients. Structural selectivity defaults per apparatus type fit this pattern. The data file maps each `ApparatusType` to a dict of `ActionType -> float` modifiers.

**Alternatives considered**:
- Separate JSON file: Inconsistent with existing YAML-based defines pattern
- Hardcoded in model: Violates Paradox Pattern ("game logic in data files, not hardcoded")

## R6: EventBus Integration Pattern

**Decision**: Institution functions return event data objects. New `EventType` values added to the enum. No direct EventBus dependency in the institution module.

**Rationale**: The existing EventBus has 43 EventType values. Feature 039 added 6 (STATE_ACTION_EXECUTED, FASCIST_CONVERGENCE, FACTION_SHIFT, THREAD_ESCALATION, LEGAL_FRAMEWORK_ENACTED, LEGAL_FRAMEWORK_REVOKED). Institution events should follow the same pattern:
- `INSTITUTION_FACTION_SHIFT` — hegemonic fraction changed
- `INSTITUTION_REPRODUCTION` — replacement org spawned
- `INSTITUTION_BONAPARTIST_MODE` — Bonapartist threshold crossed

Events are frozen dataclass instances returned from pure functions; calling code (Phase 4 system) publishes them.

## R7: Community Embeddedness Pattern

**Decision**: Implement `community_embeddedness()` as a query function following `compute_community_embeddedness()` from `ooda/initiative.py`.

**Rationale**: The existing pattern in `ooda/initiative.py:82-124` computes overlap between org communities and territory communities using MEMBERSHIP edges. Institution embeddedness follows the same pattern but queries institution territory_ids against community hyperedge membership. The XGI hypergraph is transient (built per-tick in CommunitySystem.step()), so embeddedness queries operate on graph data, not XGI directly.

## R8: OODA Modulation Pattern

**Decision**: Provide a `hegemonic_fraction_effect()` function that returns OODA profile modifier data, not an actual OODAProfile mutation.

**Rationale**: OODAProfile is stored as a plain dict on organization graph nodes, not as a Pydantic field. The institution module should return a dict of modifier hints (e.g., `{"preferred_action": ActionType.ASSIMILATE, "escalation_speed": 0.3}`) that the OODA system interprets during its cycle. This keeps the institution module decoupled from OODA internals.

## R9: Spawning Blueprint Structure

**Decision**: SpawningBlueprint is a frozen Pydantic model stored as a field on Institution, containing org_type, default class_character, and base attribute overrides.

**Rationale**: When an institution needs to spawn a replacement Organization, the blueprint provides the template. The spawned org inherits blueprint defaults, modified by current institutional state (e.g., hegemonic fraction influences the new org's `factional_alignment` for StateApparatus, or `consciousness_tendency` for CivilSocietyOrg). The blueprint does NOT store a full Organization instance — just the minimum needed to construct one.
