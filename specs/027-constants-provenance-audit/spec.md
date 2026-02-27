# Feature Specification: Magic Constants Provenance Audit

**Feature Branch**: `027-constants-provenance-audit`
**Created**: 2026-02-27
**Status**: Draft
**Priority**: HIGH
**Dependencies**: Feature 017 (Tick Dynamics), Feature 002 (Dialectical Field Topology), Feature 021 (Capital Volume I)
**Input**: User description: "Audit 136 centralized numerical constants for provenance; classify each into derivable/eliminable/calibration/engineering/game-design tiers; produce remediation plan"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Complete Constants Inventory (Priority: P1)

A simulation developer needs to understand every numerical constant in the codebase so they can assess which constants lack empirical grounding. They run the audit and receive a structured inventory (YAML) of every constant with its location, value, stated purpose, and downstream consumers.

**Why this priority**: Without a complete inventory, no classification or remediation is possible. This is the foundation for all subsequent analysis. The inventory must have zero omissions from the canonical `defines.py` and `defines.yaml` sources.

**Independent Test**: Can be fully tested by comparing the inventory against the actual `defines.py` class fields and verifying every field appears. Delivers immediate value as a reference document.

**Acceptance Scenarios**:

1. **Given** the codebase contains `defines.py` with 22 in-scope subsection models (25 total; ServicesDefines/ArcGISDefines/ExternalDataDefines excluded per scope), **When** the audit runs Phase 0, **Then** the resulting `constants-inventory.yaml` contains an entry for every in-scope numerical constant in `defines.py` and `defines.yaml` with zero omissions
1. **Given** constants also appear as inline literals throughout `src/babylon/`, **When** the audit searches using documented patterns (regex, AST grep), **Then** inline constants that implicitly define simulation parameters are captured in the inventory on a best-effort basis with a coverage log recording search patterns and directories searched
1. **Given** each constant entry must include location, value, purpose, and consumers, **When** the inventory is reviewed, **Then** every entry has all four fields populated (consumers may be "none found" for dead constants)

______________________________________________________________________

### User Story 2 - Five-Tier Classification (Priority: P1)

A project lead needs every constant classified into exactly one of five tiers so they can prioritize remediation work. The tiers are: (A) Tensor-Derivable, (B) Eliminable, (C) Calibration Parameters, (D) Engineering Constants, (E) Game Design Knobs.

**Why this priority**: Classification determines the entire remediation strategy. A Tier A constant needs a derivation formula; a Tier E constant needs honest labeling. Wrong classification wastes engineering effort.

**Independent Test**: Can be tested by verifying every constant from the inventory appears in exactly one tier, and each classification includes documented reasoning traceable to the tier criteria.

**Acceptance Scenarios**:

1. **Given** the complete inventory from Phase 0, **When** Phase 1 classification runs, **Then** every constant has exactly one tier assignment (A/B/C/D/E) with documented reasoning
1. **Given** a constant is classified as Tier A (Tensor-Derivable), **When** the classification is reviewed, **Then** it includes either a specific derivation formula using existing model fields or a documented infrastructure gap
1. **Given** a constant is classified as Tier C (Calibration Parameter), **When** the classification is reviewed, **Then** it includes the theoretical meaning, a calibration data source, and a recommended sweep range
1. **Given** a constant is classified as Tier E (Game Design Knob), **When** the classification is reviewed, **Then** it includes an explicit statement of why real data is infeasible or unnecessary

______________________________________________________________________

### User Story 3 - Data Source Cross-Reference (Priority: P2)

A data engineer needs to know which approved federal data sources (QCEW, BEA, Census, FRED, etc.) can replace or constrain each Tier A and Tier C constant, so they can plan data pipeline work.

**Why this priority**: Without data source mapping, Tier A constants cannot be replaced and Tier C constants cannot be calibrated. This bridges the gap between "this constant is wrong" and "here is the data to fix it."

**Independent Test**: Can be tested by verifying every Tier A and Tier C constant has a data source mapping (either a specific source with derivation path, or an explicit "no source available" with justification).

**Acceptance Scenarios**:

1. **Given** a Tier A constant with an approved data source match, **When** the cross-reference is reviewed, **Then** it specifies the exact data source, table/field, and derivation formula
1. **Given** a Tier A constant with no approved data source, **When** the cross-reference is reviewed, **Then** it documents that the constant is unconstrained and notes whether a new data source should be added to the approved list
1. **Given** the Constitution's Article III.4 approved data source table, **When** all Tier A and Tier C constants are cross-referenced, **Then** every mapping complies with the approved source list or explicitly proposes additions

______________________________________________________________________

### User Story 4 - Dependency Graph and Impact Analysis (Priority: P2)

A simulation architect needs to understand which systems consume each constant and which constants are coupled together, so they can plan remediation in the right order without breaking cascading dependencies.

**Why this priority**: Replacing a constant consumed by five systems is fundamentally different from replacing one consumed by a single system. The dependency graph prevents remediation work from accidentally breaking downstream systems.

**Independent Test**: Can be tested by verifying the dependency graph identifies the top 5 highest-impact replacement targets and that every consumer relationship is traceable to actual code references.

**Acceptance Scenarios**:

1. **Given** the complete inventory with consumer tracing, **When** the dependency analysis runs, **Then** it produces a Mermaid dependency graph showing constant-to-system relationships
1. **Given** the dependency graph, **When** reviewed for cascade risks, **Then** it identifies constants consumed by 3+ systems as high-impact targets
1. **Given** the dependency graph, **When** reviewed for easy wins, **Then** it identifies constants consumed by exactly one system as isolated targets

______________________________________________________________________

### User Story 5 - Phased Remediation Plan (Priority: P3)

A project lead needs a sequenced implementation plan that orders constant replacements by impact, difficulty, and data readiness, so they can scope follow-up features efficiently.

**Why this priority**: The remediation plan is the ultimate deliverable that translates analysis into action. Lower priority because it depends on all prior phases being complete.

**Independent Test**: Can be tested by verifying the plan provides a sequenced order that respects system dependencies (no constant is replaced before its upstream dependencies are resolved).

**Acceptance Scenarios**:

1. **Given** the classification, data source mapping, and dependency graph, **When** the remediation plan is produced, **Then** it orders constants by impact (simulation behavior change), difficulty (number of affected systems), and data readiness (pipeline availability)
1. **Given** the remediation plan, **When** a follow-up feature is scoped from it, **Then** the feature can be implemented without requiring out-of-order work on unaddressed dependencies

______________________________________________________________________

### Edge Cases

- What happens when a constant is consumed by both active and deprecated code paths? Classify based on active consumers only; note deprecated usage separately
- What happens when a constant appears to be Tier A (derivable) but the derivation requires infrastructure from an unimplemented feature? Document the infrastructure gap explicitly; do not reclassify as Tier E
- What happens when two constants serve the same purpose in different subsections? Flag as potential Tier B redundancy; verify both consumers before recommending elimination
- What happens when a Tier C constant has multiple plausible calibration sources that disagree? Document all sources with their disagreement range and recommend the most authoritative
- What happens when a constant mentioned in expected candidates does not exist in the current codebase? Skip it; only audit what actually exists in code

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The audit MUST produce a structured YAML inventory (`specs/027-constants-provenance-audit/reports/constants-inventory.yaml`) of every numerical constant in `defines.py`, `defines.yaml`, `formulas/constants.py`, and inline literals in simulation systems
- **FR-002**: Each inventory entry MUST include: file path with line number, current value, stated purpose (from docstring/comment/Field description), and list of consumer systems/functions
- **FR-003**: The audit MUST classify every inventoried constant into exactly one of five tiers (A: Tensor-Derivable, B: Eliminable, C: Calibration Parameter, D: Engineering/Precision, E: Game Design Knob)
- **FR-004**: Every Tier A classification MUST include either a specific derivation formula using existing model fields (ValueTensor4x3, CountyEconomicState, NetworkX graph) or a documented infrastructure gap specifying what is missing
- **FR-005**: Every Tier C classification MUST include: theoretical meaning, calibration data source, recommended sweep range, and whether existing parameter sweep tooling can calibrate it
- **FR-006**: Every Tier E classification MUST include an explicit statement of why deriving from real data is infeasible or unnecessary
- **FR-007**: The audit MUST cross-reference every Tier A and Tier C constant against the Constitution Article III.4 approved data source table (QCEW, BEA, Census/ACS, FRED, CDC WONDER, Piketty/WID, PWT, Eviction Lab, US Courts, ATTOM/CoreLogic, Fed SCF, Fed Z.1)
- **FR-008**: The audit MUST produce a dependency graph (Mermaid format) showing which constants are consumed by which systems, identifying cascade risks (3+ consumers), isolated constants (1 consumer), and coupled clusters
- **FR-009**: The audit MUST produce a remediation plan that sequences constant replacements by impact, difficulty, and data readiness
- **FR-010**: The audit MUST produce a standalone sub-report (`specs/027-constants-provenance-audit/reports/constants-bourgeoisie-cluster.md`) for the 10 bourgeoisie policy constants in `EconomyDefines` (5 policy deltas: bribery/austerity/iron-fist/crisis wage and repression deltas; 2 tension thresholds: bribery/iron-fist; 3 pool thresholds: high/low/critical) with architectural analysis assessing whether the entire subsection should be flagged for replacement via the Organization-as-Agent pattern
- **FR-011**: The audit MUST produce a standalone sub-report (`specs/027-constants-provenance-audit/reports/constants-territory-cluster.md`) for `TerritoryDefines` (~13 parameters) with architectural analysis assessing whether it can be substantially collapsed by wiring to Feature 002's dialectical field topology
- **FR-012**: The audit MUST NOT make code changes; it produces reports only
- **FR-013**: If replacing a magic constant would require introducing a different magic constant (e.g., normalization bound), the audit MUST flag this explicitly rather than hiding the problem
- **FR-014**: The audit MUST search for constants hidden in inline literals, default function arguments, and comments marked with STUB/TODO/PLACEHOLDER/MAGIC throughout `src/babylon/`

### Key Entities

- **Constant**: A numerical value in the simulation codebase (integer or float) that governs simulation behavior. Key attributes: location (file + line), value, purpose, list of consumers, tier classification
- **Tier Classification**: One of five categories (A through E) with tier-specific metadata. Tier A requires derivation formula or infrastructure gap. Tier C requires calibration source and sweep range. Tier E requires design rationale
- **Consumer**: A system, function, or formula that reads a constant's value. The consumer relationship forms a directed dependency graph from constant to system
- **Data Source**: A federal or academic data provider from the Constitution's approved list that can replace or constrain a constant's value. Each mapping specifies the source, specific dataset/table, and derivation path

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every in-scope constant in `defines.py` (22 in-scope subsection models, 136 numerical scalar fields) and `defines.yaml` appears in the inventory with zero omissions
- **SC-002**: Every inventoried constant has exactly one tier classification (A/B/C/D/E) with documented reasoning that references the tier criteria
- **SC-003**: Every Tier A constant has a specific derivation formula using existing model fields, or a documented infrastructure gap specifying what is missing
- **SC-004**: Every Tier C constant has a calibration source, recommended sweep range, and assessment of whether existing parameter sweep tooling can calibrate it
- **SC-005**: The dependency graph identifies at least the top 5 highest-impact replacement targets ranked by number of consuming systems
- **SC-006**: The remediation plan provides a sequenced implementation order that respects system dependencies (no constant is scheduled for replacement before its upstream dependencies)
- **SC-007**: Every Tier E constant is explicitly labeled as a game design choice with documentation of why real data is infeasible or unnecessary
- **SC-008**: The inline literal search includes a coverage log documenting search patterns used, directories searched, and any known gaps — enabling future audits to improve coverage incrementally

## Scope Boundaries

### In Scope

- All numerical constants in `src/babylon/config/defines.py` and `src/babylon/data/defines.yaml`
- Constants re-exported via `src/babylon/formulas/constants.py`
- Inline numerical literals throughout `src/babylon/` that implicitly define simulation parameters (per FR-014)
- Default arguments in function signatures throughout `src/babylon/` that encode parameter assumptions
- Comments marked with STUB, TODO, PLACEHOLDER, MAGIC or similar indicators

### Out of Scope

- Test-only engineering constants (tolerances, fixture sizes) in `tests/` unless they implicitly define simulation parameters
- String/enum constants (e.g., ArcGIS organization IDs, service names, displacement priority mode strings)
- External data source configuration (URLs, hosts, layer numbers) in `ExternalDataDefines` (0 numerical fields), `ArcGISDefines` (0 numerical fields), `ServicesDefines` (4 int layer-number fields — all excluded)
- Code changes of any kind; this feature produces reports only
- Constants in the legacy `babylon/` directory outside `src/babylon/`

## Constraints

- **Read-only investigation**: No code changes. Remediation is scoped as follow-up features from the plan
- **Constitution compliance**: Every recommendation must comply with Article III methodology constraints
- **No new magic**: Replacing a magic constant with a different magic constant must be flagged, not hidden
- **Honest fabrication over laundered fabrication**: If a constant genuinely cannot be derived, classifying it as Tier E (acknowledged game design) is better than providing a fake derivation

## Assumptions

- The Constitution Article III methodology constraints are authoritative and current
- The approved data source table in Article III.4 is the definitive list of permitted sources
- Existing parameter sweep infrastructure (`mise run tune:optuna`, `mise run tune:sobol`, `mise run tune:params`) is functional and available for Tier C calibration assessment
- The tensor pipeline (QCEW, ValueTensor4x3, CountyEconomicState) and graph topology (NetworkX solidarity/extraction edges) represent the current state of derivable infrastructure for Tier A assessment
- Feature 002 and Feature 021 specs represent planned architecture (not yet fully implemented) for field-based and production-based dynamics respectively

## Deliverables

1. `specs/027-constants-provenance-audit/reports/constants-inventory.yaml` -- Phase 0 exhaustive census (structured data)
2. `specs/027-constants-provenance-audit/reports/constants-classification.md` -- Phase 1 five-tier classification with reasoning
3. `specs/027-constants-provenance-audit/reports/constants-data-sources.md` -- Phase 2 cross-reference against approved data sources
4. `specs/027-constants-provenance-audit/reports/constants-dependency-graph.md` -- Phase 3 dependency analysis with Mermaid diagrams
5. `specs/027-constants-provenance-audit/reports/constants-remediation-plan.md` -- Phased remediation plan ordered by impact, difficulty, data readiness
6. `specs/027-constants-provenance-audit/reports/constants-bourgeoisie-cluster.md` -- Standalone deep-dive on EconomyDefines bourgeoisie policy delta cluster (FR-010)
7. `specs/027-constants-provenance-audit/reports/constants-territory-cluster.md` -- Standalone deep-dive on TerritoryDefines parameter collapse potential (FR-011)

## Clarifications

### Session 2026-02-27

- Q: What is the correct search scope for inline numerical literals? → A: Full `src/babylon/` (matches FR-014; Scope Boundaries updated to remove engine-only restriction)
- Q: What deliverable format should "special investigative attention" (FR-010, FR-011) produce? → A: Standalone sub-reports; deliverables list updated with two new files
- Q: Where should report deliverables be written? → A: `specs/027-constants-provenance-audit/reports/` (co-located with spec); all deliverable paths updated
- Q: How should inline literal audit completeness be verified? → A: Best-effort with coverage log; SC-001 zero-omission guarantee scoped to defines.py/defines.yaml only; SC-008 added for coverage log requirement
- Q: Are ServicesDefines layer numbers in scope? → A: No. All 4 ServicesDefines int fields are ArcGIS layer numbers, explicitly excluded per Out of Scope. In-scope count: 136 (140 total minus 4). Resolved during `/speckit.analyze` cross-artifact consistency check.
