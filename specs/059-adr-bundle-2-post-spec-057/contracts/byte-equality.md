# Contract: Byte-Equality of Simulation Output

**Bundle**: 059-adr-bundle-2-post-spec-057 · **Phase**: 1
**Reference**: spec.md SC-007, US1 acceptance scenario 2, US4 acceptance
scenario 3, ADR-005 test strategy

The decomposition (ADR-005) and Scenario migration (ADR-006.1) MUST preserve
deterministic simulation output bit-for-bit. This contract specifies the
fixed-seed runs that gate the merge.

## B1 — `sim:trace` byte-equality (ADR-005)

**Contract**: Two `mise run sim:trace 200` invocations on the post-Bundle-2
branch produce identical CSVs to the same invocations on the
`pre-bundle-2-baseline` tag.

**Pre-flight (research.md D8 verified, 50 ticks)**:
```bash
poetry run python tools/parameter_analysis.py trace \
  --csv /tmp/baseline-50.csv --ticks 50
poetry run python tools/parameter_analysis.py trace \
  --csv /tmp/repeat-50.csv --ticks 50
cmp -s /tmp/baseline-50.csv /tmp/repeat-50.csv && echo "DETERMINISTIC"
# Expected: "DETERMINISTIC"
```

**Pre-Bundle-2 baseline capture** (run before any Bundle 2 commit):
```bash
git checkout pre-bundle-2-baseline
poetry run python tools/parameter_analysis.py trace \
  --csv /tmp/sim-trace-200-baseline.csv --ticks 200
sha256sum /tmp/sim-trace-200-baseline.csv > /tmp/sim-trace-200-baseline.sha256
```

**Post-Bundle-2 verification** (run before merge):
```bash
git checkout 059-adr-bundle-2-post-spec-057
poetry run python tools/parameter_analysis.py trace \
  --csv /tmp/sim-trace-200-post.csv --ticks 200
cmp -s /tmp/sim-trace-200-baseline.csv /tmp/sim-trace-200-post.csv \
  && echo "BYTE-IDENTICAL — ADR-005 acceptance ✓" \
  || (echo "DRIFT — investigate"; diff <(head -20 /tmp/sim-trace-200-baseline.csv) \
                                         <(head -20 /tmp/sim-trace-200-post.csv))
```

**Acceptance threshold**: byte-identical. If the post-merge CSV differs from
baseline, the merge is blocked. The differ-investigator MUST identify which
ADR-005 commit introduced the drift and either revert or document the
intentional change with a new baseline tag.

**Default scenario**: `create_imperial_circuit_scenario` (the
`parameter_analysis.py trace` default). Verified byte-deterministic across
two 50-tick runs (research.md D8).

## B2 — Per-scenario byte-equality (ADR-006.1)

**Contract**: After ADR-006.1's `Scenario` ABC migration, each of the 6
ported scenarios produces byte-identical output to its pre-migration free
function counterpart, run with the same fixed seed.

**Pre-flight check** (run once before US4 begins, identifies any
non-deterministic scenarios up-front):

```bash
SCENARIOS=(
  "two_node"
  "high_tension"
  "labor_aristocracy"
  "imperial_circuit"
  "us"
  "wayne_county"
)

mkdir -p /tmp/scenario-determinism
git checkout pre-bundle-2-baseline

for s in "${SCENARIOS[@]}"; do
  for run in 1 2; do
    poetry run python tools/parameter_analysis.py trace \
      --csv "/tmp/scenario-determinism/${s}-baseline-run${run}.csv" \
      --ticks 50
    # NOTE: parameter_analysis.py currently always uses imperial_circuit;
    # tasks.md will add a --scenario flag during the Scenario migration.
  done

  if cmp -s "/tmp/scenario-determinism/${s}-baseline-run1.csv" \
            "/tmp/scenario-determinism/${s}-baseline-run2.csv"; then
    echo "${s}: DETERMINISTIC ✓"
  else
    echo "${s}: NON-DETERMINISTIC — SC-007 must relax to numeric tolerance"
    diff "/tmp/scenario-determinism/${s}-baseline-run1.csv" \
         "/tmp/scenario-determinism/${s}-baseline-run2.csv" | head -10
  fi
done
```

**Per-scenario acceptance**:
- If a scenario is byte-deterministic on the baseline tag, the post-migration
  port MUST also produce a byte-identical CSV. SC-007 holds as written.
- If a scenario is NOT byte-deterministic on the baseline (e.g., depends on
  dict ordering, filesystem walk order, or `time.time()`), SC-007 is relaxed
  for that scenario to **numeric equality with epsilon = 1e-9** for floating
  point columns and exact equality for integer/string columns. The relaxation
  is recorded in tasks.md per-scenario.

**Default-tightest case**: at minimum, `imperial_circuit` MUST be
byte-identical (verified pre-flight in D8); the other 5 scenarios may relax
to numeric tolerance if pre-flight reveals non-determinism.

## B3 — Event roundtrip equality (ADR-004)

**Contract**: For every leaf `TickEvent` variant `V` and every legal instance
`v: V`, the JSON roundtrip via `TypeAdapter(TickEvent)` produces a value
equal to `v`.

```python
from pydantic import TypeAdapter
from babylon.models.events import TickEvent
import json

adapter = TypeAdapter(TickEvent)

def assert_event_roundtrip(event):
    # Pydantic dict roundtrip
    dumped = event.model_dump()
    reloaded = adapter.validate_python(dumped)
    assert reloaded == event, f"Pydantic roundtrip failed for {type(event).__name__}"

    # JSON roundtrip (tighter — exercises the serializer)
    json_str = event.model_dump_json()
    reloaded_from_json = adapter.validate_json(json_str)
    assert reloaded_from_json == event, \
        f"JSON roundtrip failed for {type(event).__name__}"
```

**Test location**: `tests/unit/models/test_tick_event_roundtrip.py` (new;
introduced by ADR-004 step 1, parametrized over all 19 leaf variants).

## B4 — `WorldState` graph roundtrip preserves event semantics

**Contract**: `WorldState.from_graph(state.to_graph()) == state` for any
`state` containing a non-empty `events: list[TickEvent]`.

This is the integration-level version of B3 — it exercises both the
`to_graph` serializer (which writes events into graph node attributes) and
the `from_graph` deserializer (which now uses `TypeAdapter(TickEvent)`
instead of the deleted `deserialize_event` shim).

**Test location**: `tests/integration/test_worldstate_event_roundtrip.py`
(existing; should pass unchanged after ADR-004 lands, and the test must
exercise at least 5 different variant types to cover the discriminator).

## Acceptance gate

This contract is satisfied when:

1. B1's `sim:trace 200` CSV is byte-identical between baseline and merge
   commit.
2. B2's pre-flight pass identifies which scenarios qualify for byte-equality
   vs. numeric-tolerance; each scenario meets its declared bar post-migration.
3. B3's per-variant roundtrip test passes for all 19 leaf variants.
4. B4's integration roundtrip test passes.
