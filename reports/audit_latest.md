# Simulation Health Report

**Generated**: 2026-01-01T01:02:20+00:00
**Status**: UNHEALTHY

## Scenario Results

| Scenario | Expected | Actual | Status |
|----------|----------|--------|--------|
| A: Baseline | Survives ≥50 ticks | 52 ticks | ✓ PASS |
| B: Starvation | Comprador dies <40 ticks | Tick 15 | ✓ PASS |
| C: Glut | Overshoot >1.0 | 0.00 | ✗ FAIL |

## Baseline Metrics (Tick 52)

| Metric | Value |
|--------|-------|
| P_c Wealth (Comprador) | 0.01 |
| P_w Wealth (Periphery Worker) | 1.0396 |
| Rent Pool | 90.23 |
| Super Wage Rate | 0.35 |
| Metabolic Overshoot | 0.00 |

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
