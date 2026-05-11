# Quickstart: Verifying ADR Bundle 2 Acceptance

**Bundle**: 059-adr-bundle-2-post-spec-057 · **Phase**: 1
**Reference**: spec.md SC-001 through SC-010; contracts/

This quickstart guides an implementer or reviewer through verifying that
Bundle 2 has landed correctly. It is structured as a pre-flight checklist
(run once before Bundle 2 work begins) plus per-ADR acceptance gates and a
final merge gate.

Total time to run all gates: ≈ 15 minutes (test suite dominated).

## 0. Pre-flight (one-time, run once before any Bundle 2 commit)

```bash
# 0.1 — Confirm assumptions: Bundle 1 (Spec 058) and Spec 057 are merged
git log --oneline | head -10 | grep -E "spec-057|058-adr-bundle-1"
# Expected: at least one commit from each is in history

# 0.2 — Tag the baseline so byte-equality checks have an anchor
git checkout 059-adr-bundle-2-post-spec-057
git tag pre-bundle-2-baseline

# 0.3 — Capture the baseline test tally
mise run test:unit 2>&1 | tail -5  # save the "X passed, Y skipped, Z xfailed" line
mise run test:int 2>&1 | tail -5

# 0.4 — Capture the baseline sim:trace CSV (200 ticks)
poetry run python tools/parameter_analysis.py trace \
  --csv reports/sim-trace-baseline-200.csv --ticks 200
sha256sum reports/sim-trace-baseline-200.csv

# 0.5 — Verify byte-determinism of `imperial_circuit` (already verified in
#       research.md D8, but re-confirm against current data)
poetry run python tools/parameter_analysis.py trace --csv /tmp/det-1.csv --ticks 50
poetry run python tools/parameter_analysis.py trace --csv /tmp/det-2.csv --ticks 50
cmp -s /tmp/det-1.csv /tmp/det-2.csv && echo "byte-deterministic ✓" \
  || echo "non-deterministic — adjust SC-007"

# 0.6 — Pull the knowledge graph (currently a 132-byte LFS pointer)
git lfs pull -- .understand-anything/knowledge-graph.json
# OR rebuild it:
# /understand-anything:understand

# 0.7 — Snapshot the orphan-schema list from the graph
python -c "
import json
g = json.loads(open('.understand-anything/knowledge-graph.json').read())
orphans = [n['id'] for n in g.get('nodes', [])
           if n.get('type') == 'schema' and not n.get('inboundRefs')]
print(f'Orphan count: {len(orphans)}')
for o in orphans: print(f'  - {o}')
"
# Expected: 8 (or whatever the current rebuild produces)
```

## 1. ADR-005 Part A — `postgres_runtime` decomposition

```bash
# After every ADR-005A commit:
poetry run pytest tests/unit/persistence/ tests/contract/persistence/ -q

# Per-file LOC budget (FR-001 / SC-002):
find src/babylon/persistence/postgres_runtime -name "*.py" -exec wc -l {} +
# Expected: facade __init__.py ≤200; every other file ≤400

# Protocol satisfaction (contracts/protocol-satisfaction.md P1):
poetry run python -c "
from babylon.persistence import PostgresRuntime
from babylon.persistence.protocols import RuntimePersistence, PostgresRuntimeExtensions
from psycopg_pool import AsyncConnectionPool
# Stub pool for isinstance check; real I/O is in integration tests
class _NullPool:
    pass
runtime = PostgresRuntime.__new__(PostgresRuntime)  # bypass __init__
assert isinstance(runtime, RuntimePersistence)
assert isinstance(runtime, PostgresRuntimeExtensions)
print('P1 ✓')
"
```

## 2. ADR-005 Part B — `simulation` decomposition

```bash
# After every ADR-005B commit:
poetry run pytest tests/unit/engine/ tests/integration/ -q

# Per-file LOC budget (FR-002 / SC-002):
find src/babylon/engine/simulation -name "*.py" -exec wc -l {} +
# Expected: facade __init__.py ≤200; every other file ≤400

# End-to-end smoke (US1 acceptance scenario 2):
mise run sim:run    # must exit 0
mise run sim:trace  # must exit 0 and produce reports/trace.csv

# Byte-equality check (contracts/byte-equality.md B1):
poetry run python tools/parameter_analysis.py trace \
  --csv /tmp/sim-trace-post.csv --ticks 200
cmp -s reports/sim-trace-baseline-200.csv /tmp/sim-trace-post.csv \
  && echo "ADR-005B byte-equality ✓"
```

## 3. ADR-004 — `TickEvent` discriminated union

```bash
# After step 1 (kind: Literal added to all 19 leaf variants):
poetry run pytest tests/ -k "event" -q

# After step 2 (events.py → events/ package):
git grep -h "from babylon.models.events import" -- 'src/' 'tests/' \
  | sort -u > /tmp/events-imports-after.txt
diff /tmp/events-imports-before.txt /tmp/events-imports-after.txt
# Expected: empty diff (FR-007 / contracts/import-equivalence.md C3)

# After step 3 (observers consume TickEvent with assert_never):
poetry run mypy --strict src/babylon/engine/observers/ 2>&1 | grep -E "error|warning"
# Expected: zero new errors (SC-004 / FR-008)

# After step 4 (deserialize_event removed):
git grep -n "def deserialize_event" src/
# Expected: zero matches (FR-006 / SC-003)

# Discriminator validation (contracts/protocol-satisfaction.md P5):
poetry run pytest tests/unit/models/test_tick_event_discriminator.py -v
```

## 4. ADR-003 — `SystemBase` ABC

```bash
# After step 1 (SystemBase added):
poetry run pytest tests/unit/engine/systems/test_system_base.py -v

# After steps 2 + 3 (all 22 Systems migrated):
poetry run python -c "
from babylon.engine.systems.base import SystemBase
SYSTEMS = [
    ('babylon.engine.systems.survival', 'SurvivalSystem'),
    ('babylon.engine.systems.territory', 'TerritorySystem'),
    # … 20 more from contracts/protocol-satisfaction.md P3
]
for mod_path, cls_name in SYSTEMS:
    mod = __import__(mod_path, fromlist=[cls_name])
    cls = getattr(mod, cls_name)
    assert issubclass(cls, SystemBase), f'{cls_name} not subclass of SystemBase'
print('SC-005 ✓ (all 22 Systems inherit from SystemBase)')
"

# After step 4 (data.get → _read(required=True) conversions):
git log -p --grep="_read(required=True)" | grep "^+.*_read.*required=True" | wc -l
# Expected: ≥5 conversions (FR-011 / SC-006)
```

## 5. ADR-006.1 — `Scenario` ABC

```bash
# After Scenario migration:
poetry run pytest tests/unit/engine/scenarios/ -v

# Backward-compat shims still resolve (FR-012):
poetry run python -c "
from babylon.engine.scenarios import (
    create_two_node_scenario, create_high_tension_scenario,
    create_labor_aristocracy_scenario, create_imperial_circuit_scenario,
    create_us_scenario, get_multiverse_scenarios, apply_scenario,
)
from babylon.engine.scenarios_wayne_county import create_wayne_county_scenario
print('All 6 backward-compat shims resolve ✓')
"

# Byte-equality of imperial_circuit (SC-007):
poetry run python tools/parameter_analysis.py trace \
  --csv /tmp/scenario-post.csv --ticks 200
cmp -s reports/sim-trace-baseline-200.csv /tmp/scenario-post.csv \
  && echo "ADR-006.1 byte-equality ✓ (imperial_circuit)"

# Per-other-scenario byte-equality (run once after Scenario migration; for
# each scenario that pre-flight 0.5 marked deterministic, expect byte-equal;
# for the others, run the relaxed numeric-tolerance check from
# contracts/byte-equality.md B2)
```

## 6. ADR-006.2 + 6.4 — package splits

```bash
# After 6.2 (circulation/types/):
git grep -h "from babylon.economics.circulation.types import" -- 'src/' 'tests/' \
  | sort -u > /tmp/circ-imports-after.txt
diff /tmp/circ-imports-before.txt /tmp/circ-imports-after.txt
# Expected: empty diff (FR-013 / contracts/import-equivalence.md C6)
find src/babylon/economics/circulation/types -name "*.py" -exec wc -l {} +
# Expected: every file ≤400

# After 6.4 (edge_transition/):
git grep -h "from babylon.engine.systems.edge_transition" -- 'src/' 'tests/' \
  | sort -u > /tmp/edge-imports-after.txt
diff /tmp/edge-imports-before.txt /tmp/edge-imports-after.txt
# Expected: empty diff (FR-014 / contracts/import-equivalence.md C7)
poetry run python -c "
from babylon.engine.systems.base import SystemBase
from babylon.engine.systems.edge_transition import EdgeTransitionSystem
assert issubclass(EdgeTransitionSystem, SystemBase), \
    'ADR-006.4 system.py must inherit from SystemBase (research.md D5)'
print('ADR-006.4 SystemBase inheritance ✓')
"
```

## 7. ADR-006.6 — orphan schema audit

```bash
# Step 1 — distinguish graph-orphan vs runtime-unused (research.md D6):
for s in culture ideology institution persona sentiment narrative_frame slice-spec; do
  echo "=== $s ==="
  echo "  Pydantic refs: $(git grep -l "$s" -- 'src/babylon/models/' | wc -l)"
  echo "  Loader refs:   $(git grep -l "${s}.schema" -- 'src/babylon/' | wc -l)"
  echo "  Tool/test refs: $(git grep -l "${s}.schema" -- 'tools/' 'tests/' | wc -l)"
done

# Step 2 — for each schema, the disposition (kept-with-description / standalone-by-design /
# deleted-with-rationale) is recorded as an entry in ai-docs/decisions.yaml.

# Verification (SC-008):
grep -A 5 "ADR059_orphan_schema_audit" ai-docs/decisions.yaml | head -50
# Expected: 8 (or current count) sub-entries with disposition fields
```

## 8. Final merge gate

```bash
# Tally check (FR-016 / SC-001):
mise run test:unit 2>&1 | tail -1     # diff against baseline tally
mise run test:int 2>&1 | tail -1      # diff against baseline tally

# Linter / typecheck (SC-009):
mise run check                         # zero new findings vs. baseline

# Byte-equality (SC-007 / contracts/byte-equality.md B1):
poetry run python tools/parameter_analysis.py trace \
  --csv /tmp/sim-trace-merge.csv --ticks 200
cmp -s reports/sim-trace-baseline-200.csv /tmp/sim-trace-merge.csv \
  && echo "Final merge gate: byte-equality ✓" \
  || (echo "DRIFT — block merge"; exit 1)

# All success criteria green:
echo "
SC-001 (test tally): see above
SC-002 (LOC budgets): see sections 1, 2, 6
SC-003 (deserialize_event removed): $(git grep -c 'def deserialize_event' src/ || echo 0)
SC-004 (assert_never in observers): see section 3
SC-005 (22 Systems inherit SystemBase): see section 4
SC-006 (≥5 _read conversions): see section 4
SC-007 (sim:trace byte-equality): see above
SC-008 (orphan schemas resolved): see section 7
SC-009 (mise run check passes): $(mise run check >/dev/null 2>&1 && echo PASS || echo FAIL)
SC-010 (new variant forces mypy update): manual sanity check
"
```

## Troubleshooting

**Drift in `sim:trace` CSV after ADR-005**: bisect the ADR-005 commits.
The most likely cause is sub-component initialization order — the facade
must instantiate IO components in the same order as the monolith's
constructor (per ADR-005 Part A step 1: "Add empty IO module files" before
extracting any methods).

**Test tally regression after ADR-003**: a `_read(..., required=True)`
conversion exposed a real bug per FR-011. This is the **intended** outcome
(spec.md Risks bullet 4). The fix is to provide the missing field in the
test fixture or to document why the field is genuinely optional and revert
to `required=False` for that read.

**Mypy errors in observers after ADR-004**: per research.md D7, the
observer migration introduces `match event:` dispatch where it doesn't
currently exist. The error is "match-case is not exhaustive" — add the
`case _: assert_never(event)` clause or convert the match to an
`isinstance` chain that explicitly handles every variant.

**Knowledge graph orphan count != 8**: `git lfs pull` may not have run.
If the rebuild reports a different number, update `tasks.md` to reflect the
actual orphan list before US6 begins.
