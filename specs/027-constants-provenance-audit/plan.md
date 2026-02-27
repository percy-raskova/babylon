# Implementation Plan: Magic Constants Provenance Audit

**Branch**: `027-constants-provenance-audit` | **Date**: 2026-02-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/027-constants-provenance-audit/spec.md`

## Summary

Audit all 136 in-scope centralized numerical constants in `GameDefines` (22 in-scope subsection models) plus ~50+ inline simulation-behavior literals throughout `src/babylon/`. Classify each into one of five tiers (A: Tensor-Derivable, B: Eliminable, C: Calibration, D: Engineering, E: Game Design), cross-reference against Constitution III.4 approved data sources, trace consumer dependencies, and produce a phased remediation plan. This is a research-only feature — no code changes. The investigation produces 7 structured report deliverables.

## Technical Context

**Language/Version**: Python 3.12+ (read-only analysis of existing codebase)
**Primary Dependencies**: None added. Analysis reads `defines.py` (Pydantic 2.x models), `defines.yaml`, formula modules, and engine systems.
**Storage**: N/A (produces Markdown and YAML report files only)
**Testing**: N/A (research-only; verification is via inventory completeness checks against `defines.py` field counts)
**Target Platform**: N/A (report artifacts consumed by humans and downstream feature specs)
**Project Type**: Research investigation — report generation only
**Performance Goals**: N/A
**Constraints**: Read-only. No code changes. Constitution III.1/III.4 compliance on all recommendations.
**Scale/Scope**: 136 in-scope GameDefines constants (140 total minus 4 ServicesDefines layer numbers excluded per spec scope) + ~50 inline literals = ~186 total items to audit. 7 report deliverables across 5 investigation phases.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| III.1 No Magic Constants | **ALIGNED** | This feature IS the enforcement mechanism for III.1. The audit identifies every violation. |
| III.4 Data Source Traceability | **ALIGNED** | FR-007 requires cross-referencing against the approved source table. |
| VIII.6 Constants Without Data Sources | **ALIGNED** | This anti-pattern is what the audit detects and classifies. |
| II.2 Primitives vs Derived | **ALIGNED** | Tier A classification identifies which constants should be derived rather than stored. |
| III.2 Falsifiability Required | **INFORMATIONAL** | The audit itself doesn't add formulas, but Tier A derivation paths must reference falsifiable relationships. |
| VI.3 Flag Scope Creep | **ALIGNED** | FR-012 explicitly constrains to reports only — no remediation code. |

**Pre-design gate**: PASS (no violations)

**Post-design re-check**: PASS (report-only feature introduces no architectural patterns that could violate constitution)

## Project Structure

### Documentation (this feature)

```text
specs/027-constants-provenance-audit/
├── spec.md              # Feature specification (clarified)
├── plan.md              # This file
├── research.md          # Phase 0: codebase research findings
├── data-model.md        # Report schema definitions
├── quickstart.md        # Execution guide
├── checklists/
│   └── requirements.md  # Spec validation checklist
├── reports/             # Investigation deliverables (Phase 0-4 output)
│   ├── constants-inventory.yaml
│   ├── constants-classification.md
│   ├── constants-data-sources.md
│   ├── constants-dependency-graph.md
│   ├── constants-remediation-plan.md
│   ├── constants-bourgeoisie-cluster.md
│   └── constants-territory-cluster.md
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

N/A — This is a research-only feature. No source code files are created or modified.

**Structure Decision**: No source code structure needed. All output goes to `specs/027-constants-provenance-audit/reports/`. This decision was clarified during the `/speckit.clarify` session (see spec.md Clarifications section).

## Investigation Phases

### Phase 0: Exhaustive Constants Inventory

**Goal**: Produce `reports/constants-inventory.yaml` with zero omissions from `defines.py`/`defines.yaml`.

**Approach**:
1. Enumerate all 22 in-scope subsection models in `defines.py` (25 total minus ArcGISDefines, ExternalDataDefines with 0 numerical fields, and ServicesDefines excluded per spec scope), extracting every `int`/`float` `Field()` definition
2. Cross-reference against `defines.yaml` to note which constants have YAML overrides vs Python-only defaults
3. Capture `formulas/constants.py` re-exports (2 constants: `LOSS_AVERSION_COEFFICIENT`, `EPSILON`)
4. Search `src/babylon/` for inline literals using documented regex patterns and AST-level inspection
5. For each constant: trace consumers by grepping for field access patterns (e.g., `defines.economy.extraction_efficiency`, `self._defines.*)

**Verification**: Inventory count for in-scope GameDefines scalars must equal 136 (verified by research R-001; 140 total minus 4 ServicesDefines layer numbers excluded per spec scope). Coverage log documents inline literal search methodology (SC-008).

**Key search patterns for inline literals**:
- STUB/TODO/PLACEHOLDER/MAGIC comments (8 known locations)
- Module-level `_CONSTANT = value` declarations outside `defines.py`
- Function signature `param: float = value` defaults that duplicate GameDefines
- `attrs.get("field", fallback_value)` patterns in system implementations
- `ClassDynamicsParams`/`SecondOrderParams` frozen dataclass defaults
- `PredicateCondition(threshold=value)` in edge transition tables

### Phase 1: Five-Tier Classification

**Goal**: Classify every inventoried constant into exactly one tier (A/B/C/D/E).

**Approach**:
1. For each constant, evaluate against tier criteria in order: A → B → D → E → C (this order minimizes misclassification — check derivability first, then eliminability, then engineering, then design, leaving calibration as the catch-all for genuine parameters)
2. **Tier A**: Cross-reference against existing tensor infrastructure (ValueTensor4x3, MELT, gamma, hydrator) and planned Features 002/021. If a derivation path exists (even if infrastructure isn't built yet), classify as A with infrastructure gap noted.
3. **Tier B**: Check consumer count = 0 (dead code) or duplicate of another constant. Verify deprecated constants (topology_monitor.py, endgame_detector.py) with active runtime paths.
4. **Tier D**: Engineering constants (epsilon, decimal_places, capacity ratios) identified by their relationship to precision/infrastructure rather than simulation theory.
5. **Tier E**: Constants where the concept is inherently non-empirical (consciousness sensitivity, narrative pacing). Must have explicit rationale.
6. **Tier C**: Everything else — genuine calibration parameters with theoretical meaning but no derivation path. Must have sweep range and data source assessment.

**Sub-reports** (parallel with classification):
- `reports/constants-bourgeoisie-cluster.md` — Deep analysis of 10 EconomyDefines policy constants + `calculate_bourgeoisie_decision()` formula defaults. Assess Organization-as-Agent replacement path.
- `reports/constants-territory-cluster.md` — Deep analysis of 12 TerritoryDefines parameters. Assess Feature 002 dialectical field collapse potential.

### Phase 2: Data Source Cross-Reference

**Goal**: Map every Tier A and Tier C constant to an approved federal data source (or document its absence).

**Approach**:
1. For each Tier A constant: identify the specific dataset, table/field, and derivation formula from existing adapters (SQLiteBEA*, SQLiteQCEW*, QCEWCareAdapter, FredAPIClient)
2. For each Tier C constant: identify the best calibration data source and recommended sweep range
3. Cross-reference all mappings against Constitution Article III.4 approved list
4. Flag any constants that would require data sources NOT on the approved list

**Known data source coverage**:
| Source | Adapter Exists | Constants Addressable |
|---|---|---|
| QCEW | Yes (SQLiteQCEWSource) | extraction_efficiency, wage rates, employment-based derivations |
| BEA | Yes (SQLiteBEA*Source) | GDP-based derivations, industry ratios, sv_ratio |
| FRED | Partial (FredAPIClient) | Unemployment decomposition, interest rates |
| Census/ACS | Planned | Population demographics, housing tenure |
| Fed SCF | Yes (wealth_proxy) | Wealth percentile thresholds |
| ATUS | Yes (MVPUnpaidCareHoursSource) | Unpaid care hours, gamma visibility |
| Eviction Lab | Planned | Dispossession weights |
| ATTOM/CoreLogic | Planned | Foreclosure rates |
| Piketty/WID | Planned | Historical inequality ratios |

### Phase 3: Dependency Graph and Impact Analysis

**Goal**: Produce Mermaid dependency graphs showing constant→system relationships.

**Approach**:
1. Build directed graph: constants as source nodes, systems/formulas as target nodes
2. Weight edges by usage type (direct=1.0, fallback=0.5, deprecated=0.1)
3. Identify cascade risks: constants with 3+ consuming systems
4. Identify isolated constants: exactly 1 consumer (easy replacement targets)
5. Identify coupled clusters: groups of constants consumed by the same system (bundled replacement candidates)
6. Rank top 5 highest-impact replacement targets by weighted consumer count

**Expected high-impact clusters** (from research):
- `EconomyDefines` policy deltas → consumed by `ImperialRentSystem` + `calculate_bourgeoisie_decision`
- `SurvivalDefines` → consumed by `SurvivalSystem` + `StruggleSystem` + factories
- `TerritoryDefines` → consumed by `TerritorySystem` + potentially `ContradictionFieldSystem`
- `StruggleDefines` → consumed by `StruggleSystem` + `ConsciousnessSystem`

### Phase 4: Remediation Plan

**Goal**: Sequence constant replacements by impact, difficulty, and data readiness.

**Approach**: Order remediation into 5 phases:

1. **Quick Wins** — Isolated Tier B (eliminable) + Tier A with existing infrastructure (data pipeline ready). Estimated: 10-15 constants.
2. **High-Impact Data-Ready** — Tier A constants with cascade risk but existing adapter coverage. Requires careful system-level testing. Estimated: 15-20 constants.
3. **Infrastructure-Gated** — Tier A constants requiring Feature 002/021 completion. Cannot proceed until planned infrastructure is built. Estimated: 20-30 constants.
4. **Calibration-Only** — Tier C constants requiring parameter sweep optimization. Can proceed independently using existing Optuna/SALib tooling. Estimated: 15-25 constants.
5. **Acknowledged Design** — Tier E constants requiring honest relabeling in `GameDefines` Field descriptions. Estimated: 5-10 constants.

Each remediation item maps to a potential follow-up feature with estimated scope.

## Key Risk: Inline Literal Completeness

The zero-omission guarantee (SC-001) applies only to `defines.py`/`defines.yaml` constants (verifiable by field enumeration). Inline literal search is best-effort with a coverage log (SC-008). The coverage log must document:
- Regex patterns used
- AST-level search patterns (if any)
- Directories searched
- Known gaps or files skipped

This was clarified during `/speckit.clarify` to prevent false completeness claims.

## Complexity Tracking

No constitution violations to justify. This is a research-only feature that directly serves Constitution Article III.1.
