# Contract: α-Smoothing Continuity (US4 — INV-009)

**Predicate ID**: INV-009
**User Story**: US4 (P3)
**Source**: [spec.md §US4](../spec.md#user-story-4--α-smoothing-continuity-in-steady-state-priority-p3)
**Tests**: `tests/property/invariants/test_alpha_smoothing.py`

## Predicate

For each α-smoothed coefficient `c` in
`AlphaCoefficientDiscovery.discover_alpha_coefficients()` and each
consecutive (steady-state, steady-state) tick pair `(s_t, s_{t+1})`:

```text
|c_{t+1} - c_t| <= alpha * |raw_{t+1} - c_t| + epsilon

where:
    epsilon = 1e-12  (float64 round-off floor)
    alpha   = c.default_alpha  (or override from defines.py per containing class)
    steady_state ⇔ CrisisStateInspector.is_steady_state(s_t)
                   AND CrisisStateInspector.is_steady_state(s_{t+1})
```

**Suspended** when either tick is in a crisis phase
(`CrisisPhase.{ONSET, EARLY, DEEP, RECOVERY}`).

## Inputs (Hypothesis strategies)

| Strategy | Source |
|----------|--------|
| `alpha_coefficient_triple_strategy()` | `tests/property/strategies/alpha_coefficient.py` |
| `worldstate_with_consecutive_ticks_strategy(n_ticks=5)` | `tests/property/strategies/worldstate.py` |

## Test predicates

### Predicate A — Synthesized formula sweep (Q3 clarification, layer 1)

```python
@pytest.mark.parametrize("coeff", AlphaCoefficientDiscovery.discover_alpha_coefficients(),
                         ids=lambda c: f"{c.containing_class.__name__}.{c.field_name}")
@given(triple=alpha_coefficient_triple_strategy())
@settings()
def test_alpha_inequality_synthesized(coeff, triple):
    prev, raw, override_alpha = triple
    alpha = override_alpha if override_alpha is not None else coeff.default_alpha
    smoother = CoefficientSmoother(alpha=alpha)
    new = smoother.smooth(raw=raw, previous=prev, is_initialized=True)
    drift = abs(new - prev)
    bound = alpha * abs(raw - prev) + 1e-12
    assert drift <= bound, (
        f"INV-009 (synth) {coeff.containing_class.__name__}.{coeff.field_name}: "
        f"drift={drift:.6e}, bound={bound:.6e}, alpha={alpha}, prev={prev}, raw={raw}"
    )
```

### Predicate B — Observed end-to-end smoke check (Q3 clarification, layer 2)

```python
@given(state=worldstate_with_consecutive_ticks_strategy(n_ticks=5))
@settings(max_examples=20, derandomize=True)
def test_gamma_ema_observed_end_to_end(state, service_container_fixture):
    """One canonical coefficient (gamma EMA) through real run_tick.
    Falsifies wiring, not the formula."""
    inspector = CrisisStateInspector()
    prev_state = state
    prev_gamma = _extract_gamma(prev_state)
    for tick_idx in range(5):
        ctx = TickContext(tick=tick_idx)
        post_graph = SimulationEngine.run_tick(prev_state.to_graph(), service_container_fixture, ctx)
        post_state = WorldState.from_graph(post_graph)
        if not (inspector.is_steady_state(prev_state) and inspector.is_steady_state(post_state)):
            prev_state, prev_gamma = post_state, _extract_gamma(post_state)
            continue  # crisis transition — suspended per US4.3
        new_gamma = _extract_gamma(post_state)
        raw_gamma = _extract_raw_gamma(post_state)
        drift = abs(new_gamma - prev_gamma)
        bound = GAMMA_ALPHA * abs(raw_gamma - prev_gamma) + 1e-12
        assert drift <= bound, (
            f"INV-009 (observed) tick {tick_idx}: gamma drift={drift:.6e}, bound={bound:.6e}"
        )
        prev_state, prev_gamma = post_state, new_gamma
```

### Predicate C — Crisis suspension honored (US4.3)

```python
@given(
    crisis_phase=st.sampled_from([CrisisPhase.ONSET, CrisisPhase.EARLY,
                                   CrisisPhase.DEEP, CrisisPhase.RECOVERY]),
    triple=alpha_coefficient_triple_strategy(),
)
@settings()
def test_inequality_suspended_in_crisis(crisis_phase, triple):
    """When either tick is in crisis, the harness MUST NOT assert the inequality
    even if the inequality would otherwise be violated."""
    prev_state = make_state(crisis_phase=CrisisPhase.NORMAL)
    post_state = make_state(crisis_phase=crisis_phase)
    inspector = CrisisStateInspector()
    assert not (
        inspector.is_steady_state(prev_state)
        and inspector.is_steady_state(post_state)
    ), "Suspension precondition not honored"
```

## Failure modes

| Cause | Symptom | Remediation |
|-------|---------|-------------|
| The EMA formula is implemented incorrectly (e.g., `prev + alpha * raw` instead of `prev + alpha * (raw - prev)`) | Predicate A fails on every coefficient | Fix `CoefficientSmoother.smooth` |
| A System bypasses the smoother and writes raw values directly | Predicate B fails (Predicate A passes) | Find the System, route writes through `CoefficientSmoother` |
| A non-EMA `*_alpha` field appears (e.g., a new power-law exponent) | Predicate A fails on a coefficient that is not actually EMA | Add the field to `_NOT_EMA_ALPHAS` in `harness/alpha_discovery.py` (research §4) |
| Crisis suspension wrong-side: a steady-state tick incorrectly triggers crisis suspension | Predicate B passes silently when it should fail | Audit `CrisisStateInspector.is_steady_state` against research §5 |

## Out of scope

- Coefficients smoothed by mechanisms other than EMA (e.g., median
  filter, Kalman filter) — none in current codebase.
- Higher-order continuity (smooth derivatives) — out of scope for v1.
- Crisis-detection logic itself — covered by tests in
  `src/babylon/economics/tick/crisis_detector.py`.
