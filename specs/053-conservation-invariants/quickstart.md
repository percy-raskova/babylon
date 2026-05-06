# Quickstart: Conservation Invariant Property Tests

**Audience**: Babylon maintainers running or interpreting the new property tests.
**Prerequisites**: `poetry install` complete; `mise run check` passes on a clean checkout.

## Run the property tests

The five new property tests are part of the unit gate.

```bash
mise run test:unit                                   # runs everything tagged @unit, including these
poetry run pytest tests/property/invariants/        # runs only the property tests
poetry run pytest tests/property/invariants/test_value_conservation.py  # one invariant
```

## Run a single invariant against a specific system

```bash
poetry run pytest "tests/property/invariants/test_value_conservation.py::test_per_system[ImperialRentSystem]"
```

The `parametrize` id is the system's class name. Use this when you suspect a specific system is the culprit for a regression.

## Run with the slow profile (more examples, longer run)

```bash
HYPOTHESIS_PROFILE=slow poetry run pytest tests/property/invariants/
```

`slow` draws 500 examples per `@given` instead of 100 and disables `derandomize`, letting the example database grow with new failures.

## Replay a saved counterexample

Hypothesis automatically replays anything in `.hypothesis/examples/` at the start of every run. After a regression is fixed, the test should pass on the next run *without* re-shrinking — that is the regression-prevention guarantee. The example database is preserved by the CI cache.

To delete the cache (e.g., after a constitutional change to the invariant tolerance):

```bash
rm -rf .hypothesis/
```

## Interpret a failure

A failed property test prints:

1. The Hypothesis-shrunk minimal input (visible in the pytest output between `Falsifying example:` lines).
2. The pytest parametrize id (for per-system tests, this names the responsible system).
3. The custom failure message (drift, tolerance, pre/post sums).

Example:

```text
FAILED tests/property/invariants/test_value_conservation.py::test_per_system[StruggleSystem]
   Falsifying example: pre=WorldState(hexes={'872830899ffffff': HexEconomicState(c=0.0, v=0.0, s=1.0)})
   System StruggleSystem mutated sum(c+v+s) by -0.5 > tol=1e-10; pre=1.0, post=0.5
```

The fix workflow is:

1. Read the failing input — Hypothesis already minimized it.
2. Run the test in a debugger with that exact input.
3. Identify the violating mutation in the system's `step()`.
4. Either fix the system OR (if the mutation is intentional) declare `creates_value: ClassVar[bool] = True` on the system class.

## Adding a new invariant

To add an invariant beyond the five in this spec:

1. Add a contract document under `specs/053-conservation-invariants/contracts/<name>.md` (or in a successor spec).
2. Add a strategy under `tests/property/strategies/<name>.py` if existing strategies don't cover the new input type.
3. Add a test file under `tests/property/invariants/test_<name>.py` following the conventions established in `test_value_conservation.py`.
4. Wire the new test into the unit gate by ensuring it carries `@pytest.mark.unit` (or relies on the default unit collection).

## Adding a new system to the engine

When adding a new `System` class under `src/babylon/engine/systems/`:

1. Decide whether the system mutates `sum(c+v+s)` (or, more loosely, `wealth`). Consult `research.md` R1/R2.
2. Set `creates_value: ClassVar[bool] = True` on the class if so; `False` otherwise.
3. Run `mise run test:unit`. If the per-system test catches an unexpected violation, your `creates_value=False` is wrong (or the system has a bug).

The default-deny policy (FR-004a) means a system **without** any marker is treated as `creates_value=False` and will be tested. This is intentional — it forces every new system to make an explicit conservation declaration.
