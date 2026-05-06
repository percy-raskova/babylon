# Contract: Population Conservation Modulo Births and Deaths

**Invariant ID**: INV-004
**User Story**: 4 (P2)
**Test File**: `tests/property/invariants/test_population.py`

## Predicate

For any generated initial DPDState distribution `pre_dpd: Mapping[hex_id, DPDState]` and any single tick:

```text
let pre_pop  = sum(d.cohort_total for d in pre_dpd.values())
let world    = WorldState with pre_dpd installed
let world'   = SimulationEngine.run_tick(world)
let post_dpd = {h: world'.hexes[h].dpd_state for h in world'.hexes}
let post_pop = sum(d.cohort_total for d in post_dpd.values())
let births   = count(events for events in world'.events if event.type == BIRTH)
let deaths   = count(events for events in world'.events if event.type == DEATH)
assert post_pop == pre_pop + births − deaths   (exact, integer-valued)
```

For multi-tick:

```text
assert pop_T == pop_0 + Σ_{t<T} births_t − Σ_{t<T} deaths_t
```

## Inputs

| Input | Type | Strategy |
|-------|------|----------|
| `pre_dpd` | `Mapping[str, DPDState]` | `dpd_state_grid_strategy()` |
| `n_ticks` | `int` | `integers(min_value=1, max_value=10)` |

## Failure Mode

`pytest.fail(f"Population accounting violated at tick {t}: pre={pre_pop}, post={post_pop}, births={births}, deaths={deaths}, expected post={pre_pop + births - deaths}")`

## Acceptance

- Zero births / zero deaths tick: `pop` unchanged.
- Mortality > births: `pop` decreases by exactly `deaths − births`, no negative counts.
- Multi-tick accumulation matches.
