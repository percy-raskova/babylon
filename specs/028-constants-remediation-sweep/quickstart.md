# Quickstart: Constants Remediation Sweep

**Feature**: 028-constants-remediation-sweep
**Prerequisites**: Feature 027 audit complete, on branch `028-constants-remediation-sweep`

## Execution Order

The remediation MUST proceed in this exact order (FR-001):

1. **Generate regression baselines** (before any changes)
2. **US2: Tier B Elimination** (zero behavioral change)
3. **Regenerate baselines** (captures clean GameDefines hash)
4. **US1: Tier A Wiring** (data-derived values replace hardcoded)
5. **US3: Tier C Centralization** (inline → GameDefines with bounds)
6. **US4: Triage & Documentation** (remaining 138 constants)

## Step 1: Establish Regression Baselines

```bash
# Generate fresh baselines from current state
mise run qa:regression-generate

# Verify they pass
mise run qa:regression
```

## Step 2: Tier B Elimination (US2)

Work through elimination groups in order:

### Group A — Pure Delete (7 constants)
Delete deprecated module constants where GameDefines fields already exist:
- `src/babylon/engine/observers/endgame_detector.py` lines 53-61
- `src/babylon/engine/topology_monitor.py` lines 55-56

### Group B — Extract + Delete (~21 constants)
For each: add GameDefines field → update callers → delete inline default:
- `src/babylon/formulas/dynamic_balance.py` — 10 function params → `economy.*`
- `src/babylon/engine/topology_monitor.py` lines 57-65 — 5 constants → `topology.*`
- `src/babylon/engine/observers/metrics.py` line 41 — DEATH_THRESHOLD → `precision.death_threshold`
- `src/babylon/formulas/solidarity.py`, `metabolic_rift.py`, `curvature.py`, `trpf.py` — 5 defaults → various subsections

### Group C — Redirect Callers (2 constants)
- Update importers of `formulas.constants.LOSS_AVERSION_COEFFICIENT` → use GameDefines.behavioral directly
- Update importers of `formulas.constants.EPSILON` → use GameDefines.precision directly

### After Each Group
```bash
mise run check           # lint + format + typecheck + test:unit
mise run qa:regression   # verify no behavioral change
```

## Step 3: Regenerate Baselines

```bash
# GameDefines hash changed (new fields added). Regenerate baselines.
mise run qa:regression-generate
```

## Step 4: Tier A Wiring (US1)

Wire 12 pipeline-ready constants to their data sources. For each:
1. Add hydration call at initialization
2. Keep GameDefines default as fallback
3. Document falsifiability statement
4. Run regression (expect deviations — document each)

**Key files to modify:**
- `src/babylon/economics/tick/system.py` — class share constants (lines 320-342)
- `src/babylon/data/reference/hydrator.py` — extend with new hydration functions
- `src/babylon/config/defines.py` — no changes (values override at runtime)

## Step 5: Tier C Centralization (US3)

Move 28 inline constants to GameDefines with `Field(ge=, le=)` bounds:
- 12 non-edge-transition constants across formula modules
- 16 edge transition thresholds from `src/babylon/engine/systems/edge_transition.py`

```bash
# After centralization, verify sweep infrastructure
mise run tune:morris 20   # Should include all 63+ Tier C constants
```

## Step 6: Triage & Documentation (US4)

Generate triage report and update GameDefines field descriptions:
- 25 deferred Tier A → document blocking feature + required adapter
- 14 Tier D → add engineering constraint rationale to `description=`
- 99 Tier E → add "Game design: [rationale]. Not data-derived." to `description=`

## Verification

```bash
# Final verification
mise run check                    # All quality gates
mise run qa:regression            # Baseline comparison
mise run test:all                 # Full non-AI test suite
```

## Key References

| Artifact | Purpose |
|----------|---------|
| `specs/027-constants-provenance-audit/reports/constants-inventory.yaml` | Canonical 247-constant inventory |
| `specs/027-constants-provenance-audit/reports/constants-classification.md` | 5-tier taxonomy |
| `specs/027-constants-provenance-audit/reports/constants-remediation-plan.md` | 5-phase remediation plan |
| `specs/027-constants-provenance-audit/reports/constants-data-sources.md` | Data source mappings |
| `src/babylon/config/defines.py` | GameDefines (primary modification target) |
| `src/babylon/data/reference/hydrator.py` | Hydrator pattern reference |
| `tools/regression_test.py` | Regression gate infrastructure |
