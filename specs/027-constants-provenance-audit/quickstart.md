# Quickstart: Magic Constants Provenance Audit

**Feature**: 027-constants-provenance-audit
**Branch**: `027-constants-provenance-audit`

## What This Feature Produces

This is a **research-only** feature. No code changes. It produces 7 structured reports analyzing every numerical constant in the simulation codebase.

## Report Deliverables

| # | File | Phase | Content |
|---|---|---|---|
| 1 | `reports/constants-inventory.yaml` | 0 | Exhaustive census of 136+ constants with location, value, purpose, consumers |
| 2 | `reports/constants-classification.md` | 1 | Five-tier classification (A-E) with documented reasoning per constant |
| 3 | `reports/constants-data-sources.md` | 2 | Cross-reference of Tier A/C constants against Constitution III.4 data sources |
| 4 | `reports/constants-dependency-graph.md` | 3 | Mermaid dependency graphs, cascade risks, coupled clusters |
| 5 | `reports/constants-remediation-plan.md` | 4 | Phased replacement plan ordered by impact, difficulty, data readiness |
| 6 | `reports/constants-bourgeoisie-cluster.md` | 1+ | Deep-dive: EconomyDefines policy delta cluster (9 constants) |
| 7 | `reports/constants-territory-cluster.md` | 1+ | Deep-dive: TerritoryDefines collapse potential (12 constants) |

All reports live under `specs/027-constants-provenance-audit/reports/`.

## Execution Order

```
Phase 0: Inventory     → reports/constants-inventory.yaml
Phase 1: Classify      → reports/constants-classification.md
                        → reports/constants-bourgeoisie-cluster.md
                        → reports/constants-territory-cluster.md
Phase 2: Data Sources  → reports/constants-data-sources.md
Phase 3: Dependencies  → reports/constants-dependency-graph.md
Phase 4: Remediation   → reports/constants-remediation-plan.md
```

Each phase depends on the previous phase's output.

## Key Source Files to Read

### Primary Targets
- `src/babylon/config/defines.py` — 25 subsection models (22 in-scope), 136 in-scope numerical constants
- `src/babylon/data/defines.yaml` — YAML overrides for 14 of 25 subsections
- `src/babylon/formulas/constants.py` — 2 re-exported constants

### Inline Literal Hotspots
- `src/babylon/formulas/class_dynamics.py` — FRED-fitted ODE coefficients
- `src/babylon/formulas/dynamic_balance.py` — bourgeoisie policy defaults
- `src/babylon/engine/systems/edge_transition.py` — 17+ transition thresholds
- `src/babylon/engine/factories.py` — entity creation defaults
- `src/babylon/engine/scenarios.py` — scenario preset values
- `src/babylon/engine/topology_monitor.py` — 7 deprecated module constants

### Infrastructure for Tier A Assessment
- `src/babylon/economics/tensor.py` — ValueTensor4x3 (derivable quantities)
- `src/babylon/economics/hydrator.py` — QCEW→tensor pipeline
- `src/babylon/economics/melt/` — MELT calculator, class position classifier
- `src/babylon/economics/gamma/` — gamma visibility tensor

### Constitution Reference
- `.specify/memory/constitution.md` — Article III.1 (No Magic Constants), III.4 (Approved Sources)

## Tier Definitions

| Tier | Name | Criteria | Required Metadata |
|---|---|---|---|
| A | Tensor-Derivable | Can be computed from existing tensor/graph infrastructure or planned features | Derivation formula OR infrastructure gap |
| B | Eliminable | Dead code, duplicate, or deprecated constant | Elimination reasoning + consumer verification |
| C | Calibration Parameter | Genuine tuning parameter with empirical constraints | Theoretical meaning + data source + sweep range |
| D | Engineering/Precision | Technical constant (epsilon, precision, capacity) | Purpose + constraint relationship |
| E | Game Design Knob | Intentional design choice where real data is infeasible | Rationale for why data derivation is impossible/unnecessary |

## Verification

- **SC-001**: Compare inventory against `defines.py` in-scope field count (expected: 136)
- **SC-002**: Every constant has exactly one tier (A/B/C/D/E)
- **SC-008**: Coverage log documents inline literal search methodology
