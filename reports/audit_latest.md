# Simulation Health Report

**Generated**: 2025-12-31T06:10:42+00:00
**Status**: HEALTHY

## Scenario Results

| Scenario | Expected | Actual | Status |
|----------|----------|--------|--------|
| A: Baseline | Survives ≥50 ticks | 52 ticks | ✓ PASS |
| B: Starvation | Comprador dies <40 ticks | Tick 30 | ✓ PASS |
| C: Glut | Overshoot >1.0 | 0.03 | ⊘ SKIP (no territories) |

## Baseline Metrics (Tick 52)

| Metric | Value |
|--------|-------|
| P_c Wealth (Comprador) | 0.01 |
| P_w Wealth (Periphery Worker) | 0.0832 |
| Rent Pool | 100.21 |
| Super Wage Rate | 0.35 |
| Metabolic Overshoot | 0.03 |

## Scenario Parameters

| Scenario | Parameters |
|----------|------------|
| Baseline | Default GameDefines |
| Starvation | extraction_efficiency=0.05 |
| Glut | extraction_efficiency=0.99, default_subsistence=0.0 |

## Interpretation

- **Baseline**: Tests that default parameters produce a stable simulation
- **Starvation**: Tests that low extraction causes Comprador collapse (validates economic circuit)
- **Glut**: Tests that unsustainable extraction causes metabolic overshoot (validates ecological limits)
