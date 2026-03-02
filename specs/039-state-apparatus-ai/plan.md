# Implementation Plan: State Apparatus AI

**Branch**: `039-state-apparatus-ai` | **Date**: 2026-03-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/039-state-apparatus-ai/spec.md`

## Summary

This feature implements the state as a strategic adversary — a factional coalition of Finance-Capital, Security-State, and Settler-Populist interests whose behavior shifts based on which faction dominates. It unifies three subsystems (attention threads, NPC faction AI, organization-territory integration) with a six-verb action taxonomy, factional politics model, and Sparrow-grounded intelligence system.

Technical approach: extend existing Organization entity with StateFaction/FactionBalance models, extend OODA loop with StateActionType verbs, implement attention threads as intelligence resources with observation gap mechanics, and add DEVELOP/WITHDRAW territory effects — all using frozen Pydantic models, GraphProtocol, and the Protocol+Default implementation pattern established across specs 031-038.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: Pydantic 2.x (frozen models, discriminated unions), NetworkX 3.x (GraphProtocol via NetworkXAdapter), XGI 0.10 (hypergraph community memberships)
**Storage**: In-memory via GraphProtocol. No new database tables. State apparatus AI state persists via WorldState serialization. AttentionThread and FactionBalance stored as graph node attributes or context persistent data.
**Testing**: pytest with markers (`@pytest.mark.math`, `.ledger`, `.topology`, `.integration`, `.unit`). TestConstants pattern for domain values. DomainFactory for test entities.
**Target Platform**: Linux server (local simulation engine, deterministic given RNG seed)
**Project Type**: Single project — extends existing `src/babylon/` module tree
**Performance Goals**: Deterministic simulation. 500-action cap per tick (existing). State AI decision function must complete within tick budget. No external AI service calls in stub.
**Constraints**: Frozen Pydantic immutability (`model_copy(update={})`). Protocol+Default impl pattern. Computation not storage (topology computed from COMMAND edges, never stored). Per-tick event semantics (fresh list each tick). Consciousness delta clamped to 0.05 per tick. GraphProtocol 18-method interface.
**Scale/Scope**: Detroit Metro 2010 test case. ~5-8 attention threads. 3 factions. 6 top-level verbs with ~24 sub-verbs. Budget-constrained finite actions per tick.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Post-design re-check (2026-03-02): ALL PASS. Data model (14 entities), contracts (24 BCs), and protocols verified against all articles. No violations introduced.*

| Article | Principle | Status | Notes |
|---------|-----------|--------|-------|
| I.1 | Settler-Colonial Frame | PASS | Three factions include Settler-Populist with imperial rent material base; DEVELOP verb models gentrification/displacement along colonial lines |
| I.2 | Imperial Rent (Φ) | PASS | StateBudget derives partly from imperial rent pool; Settler-Populist faction's material base IS imperial rent distribution; BRIBE distributes imperial rent to labor aristocracy |
| I.4 | George Jackson Bifurcation | PASS | Fascist convergence detection directly implements bifurcation (SS>0.4, settler CI>0.6, FC<0.25); near-absorbing state models the attractor |
| I.6 | Solidarity as Edge Mode | PASS | DIVIDE targets edges, not nodes; CO_OPT degrades SOLIDARISTIC→TRANSACTIONAL→ANTAGONISTIC; mode transforms, not scalar weights |
| I.7 | Quantitative → Qualitative | PASS | Faction weights are floats (quantities); fascist convergence is enum transition (quality); thread phases are discrete states |
| I.12 | Catastrophe Surface | PASS | Fascist convergence is a fold crossing on the catastrophe surface; faction balance shifts are continuous until convergence threshold |
| I.15 | Edge Mode Transitions | PASS | DIVIDE follows SOLIDARISTIC→TRANSACTIONAL→ANTAGONISTIC state machine; no prohibited direct EXTRACTIVE→SOLIDARISTIC jumps |
| I.16 | Organization vs Institution | PASS | StateApparatus models institutions (survive member turnover); player builds organizations; AUDIT detects institutional decay |
| I.17 | OODA Loop as Org Metabolism | PASS | State AI uses OODA decision flow per tick; thread-level OODA for intelligence; meta-OODA for thread allocation |
| I.18 | Material-Ideological Distinction | PASS | CO_OPT targets ideological dimension (consciousness); DEVELOP targets material basis (territory); gap between material and ideological is the strategic terrain |
| II.2 | Primitives vs Derived | PASS | FactionBalance weights are primitive (stored); dominant_faction is computed (derived). Thread intel_completeness is primitive; Sparrow analysis results are computed. |
| II.3 | NetworkX as Discretized Manifold | PASS | All state apparatus operations go through GraphProtocol; PRESENCE edges, attention threads modeled as graph constructs |
| II.5 | AI Observes, Never Controls | PASS | State AI is deterministic rule-based stub; no external AI service; strategy pattern allows future LLM hot-swap without violating reproducibility |
| II.6 | State is Data, Engine is Transformation | PASS | FactionBalance, StateBudget, AttentionThread are frozen Pydantic models; state AI decision function is pure transformation |
| II.7 | Edges vs Hyperedges | PASS | PRESENCE is a dyadic edge (org↔territory); community consciousness is XGI hyperedge; thread targets can be either. Two layers remain separate. |
| III.1 | No Magic Constants | PASS | All thresholds (fascist convergence, effect floors, observation ceilings) are GameDefines parameters with documented sources or flagged as SYNTHETIC |
| III.2 | Falsifiability Required | PASS | SC-002 through SC-010 define specific predictions with null hypotheses testable via seeded runs |
| III.4 | Data Source Traceability | PASS | Detroit 2010 initialization values flagged as SYNTHETIC defaults; QCEW-derived budget revenue; no new data sources required |
| III.5 | Empirical vs Strategic Separation | PASS | Material conditions (budget, profit rate, imperial rent pool) from data; strategic behavior (verb selection, escalation) from factional logic |
| V | Action Vocabulary | PASS | All 6 state verbs with sub-verbs are constitutional (Article V, added v1.7.0). Verb taxonomy matches constitution exactly. |
| VI.1 | Material Base First | PASS | Implementation order: budget/factions first, then verbs, then intelligence, then territory effects. Economic extraction drives state capacity. |
| VIII.1 | Anti-Pattern: Solidarity as Scalar | PASS | DIVIDE transforms edge types (SOLIDARISTIC→TRANSACTIONAL→ANTAGONISTIC), not scalar weights |
| VIII.9 | Anti-Pattern: Community as Pairwise Edge | PASS | Community consciousness tracked via XGI hyperedge, not pairwise edges |

**Gate Result**: ALL PASS. No constitution violations. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/039-state-apparatus-ai/
├── plan.md              # This file
├── spec.md              # Feature specification (completed)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── state-ai-decision.md
│   ├── attention-thread.md
│   ├── faction-balance.md
│   └── territory-effects.md
├── checklists/
│   └── requirements.md  # Spec quality checklist (completed)
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/babylon/
├── models/
│   ├── enums.py                    # EXTEND: StateActionType, StateFaction, ThreadPhase, etc.
│   └── entities/
│       ├── organization.py         # EXTEND: factional_alignment on StateApparatus
│       ├── state_apparatus_ai.py   # NEW: FactionBalance, StateBudget, StateAction, LegalFramework
│       └── attention_thread.py     # NEW: AttentionThread, ObservationModel, SparrowAnalysis
├── ooda/
│   ├── npc_stub.py                 # EXTEND: six-verb decision function (primary integration)
│   ├── state_ai/                   # NEW: state AI decision architecture
│   │   ├── __init__.py
│   │   ├── decision.py             # Factional objective function, verb scoring
│   │   ├── escalation.py           # Escalation/de-escalation logic
│   │   ├── faction_dynamics.py     # Faction balance shift calculations
│   │   └── protocols.py            # NPCDecisionStrategy protocol
│   └── attention/                  # NEW: attention thread system
│       ├── __init__.py
│       ├── thread_manager.py       # Thread allocation, meta-OODA
│       ├── sparrow.py              # Network analysis on G_observed
│       ├── observation.py          # Observation gap, surveillance methods
│       └── thread_ooda.py          # Per-thread OODA cycle
├── engine/
│   └── systems/
│       └── ooda.py                 # EXTEND: state action resolution in Layer 1
├── formulas/
│   └── state_ai.py                 # NEW: faction shift formulas, consciousness effects
├── config/
│   └── defines.py                  # EXTEND: StateApparatusAIDefines sub-section

tests/
├── unit/
│   ├── state_ai/                   # NEW: unit tests
│   │   ├── test_faction_balance.py
│   │   ├── test_state_verbs.py
│   │   ├── test_escalation.py
│   │   ├── test_attention_threads.py
│   │   ├── test_sparrow.py
│   │   └── test_territory_effects.py
│   └── ooda/
│       └── test_npc_stub.py        # EXTEND: state AI verb selection tests
├── contract/
│   └── state_ai/                   # NEW: behavioral contract tests
│       ├── test_decision_contract.py
│       ├── test_thread_contract.py
│       ├── test_faction_contract.py
│       └── test_territory_contract.py
└── integration/
    └── test_state_ai_integration.py # NEW: 52-tick integration tests
```

**Structure Decision**: Single project extending existing module tree. State AI logic goes in `src/babylon/ooda/state_ai/` (adjacent to existing `npc_stub.py`). Attention threads go in `src/babylon/ooda/attention/`. New entity models go in `src/babylon/models/entities/`. This follows the established pattern where OODA-related decision logic lives in `src/babylon/ooda/` and entity definitions live in `src/babylon/models/entities/`.

## Complexity Tracking

> No constitution violations found. No complexity justifications needed.
