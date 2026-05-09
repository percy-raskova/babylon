# Contract: `CalibrationWarning` event family

**Spec**: 057 / FR-002, FR-004, FR-008
**Location**: `src/babylon/models/events.py` (additions to existing file per research.md §R6)
**Pattern**: Typed `EconomicEvent` subclasses + EventBus discriminator strings

## Three event types

### `AxiomViolationEvent` — periphery-wage `ratio < 1.0`

**Discriminator**: `"calibration_warning.axiom_violation"`
**Emitted from**: `DefaultPeripheryLaborCoefficientsSource._fetch`
**FR**: FR-002 + Clarifications 2026-05-08

| Field | Type | Constraint | Meaning |
|---|---|---|---|
| `industry` | `str` | non-empty | BEA industry code where violation occurred |
| `year` | `int` | `[1900, 2100]` | The data year |
| `ratio` | `float` | finite | The violating wage ratio (< threshold) |
| `threshold` | `float` | default `1.0` | The expected lower bound (axiom) |

### `QcewCarryForwardEvent` — QCEW gap, employment shares carried forward

**Discriminator**: `"calibration_warning.qcew_carry_forward"`
**Emitted from**: `DefaultIndustryToCountyAllocator.allocate` (and the `imperial_rent.compute()` "pipeline not wired" sentinel case)
**FR**: FR-004 + Clarifications 2026-05-08

| Field | Type | Constraint | Meaning |
|---|---|---|---|
| `county_fips` | `str` | 5-char numeric (or `"*"` for "all counties" sentinel) | County identifier |
| `year` | `int` | `[1900, 2100]` | The tick year (gap year) |
| `look_back_year` | `int` | `[1900, 2100]` | The year carried forward from |
| `look_back_distance` | `int` | `[0, 20]` | `year - look_back_year` (use `-1` as sentinel for "Spec 057 pipeline not wired" pattern) |

### `PhiHourOutlierEvent` — per-county `phi_hour` outside plausible range

**Discriminator**: `"calibration_warning.phi_hour_outlier"`
**Emitted from**: `DefaultIndustryToCountyAllocator.allocate`
**FR**: FR-008 + Clarifications 2026-05-08

| Field | Type | Constraint | Meaning |
|---|---|---|---|
| `county_fips` | `str` | 5-char numeric | County identifier |
| `phi_hour` | `float` | finite | The outlier value |
| `threshold_low` | `float` | default `-1000.0` | Plausibility lower bound (from `LeontiefRentDefines`) |
| `threshold_high` | `float` | default `1000.0` | Plausibility upper bound (from `LeontiefRentDefines`) |

## Publishing pattern

Per research.md §R6, all three events are published via the existing `EventBus.publish(Event(...))` adapter:

```python
typed_event = AxiomViolationEvent(
    tick=current_tick, industry=industry, year=year, ratio=float(ratio)
)
self._bus.publish(Event(
    type="calibration_warning.axiom_violation",
    tick=current_tick,
    payload=typed_event.model_dump(),
))
```

## Subscriber pattern

```python
def calibration_handler(event: Event) -> None:
    typed = AxiomViolationEvent.model_validate(event.payload)
    # ... handle ...

bus.subscribe("calibration_warning.axiom_violation", calibration_handler)
```

For wildcard subscription (e.g., dashboard observer): if the existing `EventBus` does not support glob-pattern subscriptions, register three explicit handlers (one per discriminator string). A shared base handler factored into a single function with type dispatch:

```python
def all_calibration_handler(event: Event) -> None:
    if event.type == "calibration_warning.axiom_violation":
        typed = AxiomViolationEvent.model_validate(event.payload)
    elif event.type == "calibration_warning.qcew_carry_forward":
        typed = QcewCarryForwardEvent.model_validate(event.payload)
    elif event.type == "calibration_warning.phi_hour_outlier":
        typed = PhiHourOutlierEvent.model_validate(event.payload)
    else:
        return
    # ... unified handling ...

for t in ["calibration_warning.axiom_violation",
          "calibration_warning.qcew_carry_forward",
          "calibration_warning.phi_hour_outlier"]:
    bus.subscribe(t, all_calibration_handler)
```

## Test assertion pattern

```python
def test_axiom_violation_emitted(bus: EventBus, source: DefaultPeripheryLaborCoefficientsSource) -> None:
    source.get_coefficients(year=2015)  # Triggers fetch with mock data containing ratio=0.95
    history = bus.get_history()
    axiom_events = [e for e in history if e.type == "calibration_warning.axiom_violation"]
    assert len(axiom_events) == 1
    typed = AxiomViolationEvent.model_validate(axiom_events[0].payload)
    assert typed.industry == "INDUSTRY_X"
    assert typed.ratio == 0.95
    assert typed.threshold == 1.0
```

## Acceptance criteria

| ID | Test | Method |
|---|------|--------|
| AC1 | `AxiomViolationEvent` round-trips through EventBus | `test_axiom_event_roundtrip` — publish, get_history, model_validate, assert field equality |
| AC2 | `QcewCarryForwardEvent` round-trips with `look_back_distance=0` (no carry — should not normally be emitted) and `look_back_distance=5` (max) | `test_qcew_event_boundary_values` — assert validation accepts both bounds |
| AC3 | `PhiHourOutlierEvent` round-trips with default thresholds | `test_outlier_event_default_thresholds` — assert `threshold_low=-1000.0`, `threshold_high=1000.0` if not provided |
| AC4 | Validation rejects out-of-range `look_back_distance` | `test_qcew_event_distance_too_large` — `pytest.raises(pydantic.ValidationError)` for `look_back_distance=21` |
| AC5 | Discriminator strings match expected format `"calibration_warning.<subtype>"` | `test_event_type_strings` — assert `EventType.CALIBRATION_AXIOM_VIOLATION.value == "calibration_warning.axiom_violation"` etc. |
