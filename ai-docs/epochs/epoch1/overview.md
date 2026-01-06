# Epoch 1: The Engine

**Status**: COMPLETE
**Theme**: "Validate the Thesis Through Simulation"

## Summary

Epoch 1 delivered the core simulation engine that validates MLM-TW theory through deterministic mechanics. The 70-year Carceral Equilibrium trajectory demonstrates that revolution in the Imperial Core is impossible when W_c > V_c (wages exceed value produced).

## Completion Record

See `epoch1-complete.md` for the full completion record including:
- 13 Systems (ImperialRent, Solidarity, Consciousness, Survival, Struggle, Contradiction, Territory, Metabolism, etc.)
- 25 EventTypes
- 4646 tests passing
- Carceral Equilibrium validation (70-year trajectory)

## Slices

| Slice | Name | Status | Description |
|-------|------|--------|-------------|
| 1.1 | Core Types | COMPLETE | Pydantic models, constrained types |
| 1.2 | Economic Flow | COMPLETE | ImperialRentSystem, 4-node circuit |
| 1.3 | Survival Calculus | COMPLETE | P(S|A), P(S|R) calculations |
| 1.4 | Consciousness Drift | COMPLETE | Ideology bifurcation |
| 1.5 | Synopticon Dashboard | COMPLETE | DearPyGui Observer UI |
| 1.6 | Endgame Resolution | COMPLETE | Terminal crisis detection |
| 1.7 | Graph Bridge | COMPLETE | WorldState.to_graph()/from_graph() |
| 1.8 | Carceral Geography | COMPLETE | TerritorySystem, heat dynamics |

## Spec Files in This Directory

| File | Purpose |
|------|---------|
| `agency-layer.yaml` | George Floyd Dynamic (Slice 1.2) |
| `balance-targets.yaml` | Numerical success criteria |
| `balance-tuning.yaml` | Empirical balance findings |
| `carceral-geography.yaml` | TerritorySystem necropolitics |
| `demographics.yaml` | Mass Line Refactor (ADR033) |
| `dpg-patterns.yaml` | DearPyGui implementation patterns |
| `gramscian-wire-mvp.yaml` | Slice 1.5 passive narrative observation |
| `imperial-circuit.yaml` | 4-node Imperial Circuit model |
| `metabolic-slice.yaml` | MetabolismSystem (Slice 1.4) |
| `parameter-analysis.yaml` | Epoch 1 parameter tuning results |
| `synopticon-spec.yaml` | Observer system (Mass Line + Kino-Eye) |
| `territorial-schema.yaml` | Territory enums/types |
| `ui-wireframes.yaml` | Dashboard layout specification |

## Key Achievements

1. **Fundamental Theorem Validated**: Simulation demonstrates that imperial rent (Phi) prevents revolutionary consciousness in the core as long as W_c > V_c.

2. **George Floyd Dynamic**: The agency layer shows how excessive force events can trigger mass mobilization when P(S|R) exceeds threshold.

3. **Carceral Equilibrium**: 70-year trajectory shows stable extraction followed by crisis phases:
   - SUPERWAGE_CRISIS at ~42.9 years
   - CLASS_DECOMPOSITION at ~43.3 years
   - CONTROL_RATIO_CRISIS at ~44.1 years
   - TERMINAL_DECISION at ~44.9 years

4. **Metabolic Rift**: Ecological limits integrated via biocapacity depletion and overshoot ratio.

## Epoch 1 to Epoch 2 Bridge

Epoch 1 uses abstract territories (T001, T002...) and hardcoded parameters. Epoch 2 replaces these with:
- Real data from federal APIs (Census, FRED, BLS)
- Real geography via H3 hexagonal coordinates
- Scalable visualization via PyQt + deck.gl

The GraphProtocol interface (Slice 2.7) enables this transition without rewriting Epoch 1 Systems.
