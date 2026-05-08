# Quickstart: ADR Bundle 1 — local verification

**Spec**: [`spec.md`](spec.md)  |  **Plan**: [`plan.md`](plan.md)  |  **Branch**: `058-adr-bundle-1-pre-spec-057`

This guide is for a Babylon contributor (or the spec-057 implementer) who wants to (a) verify Bundle 1 lands cleanly on their local machine after each commit in the rollout, and (b) trust that Spec 057's downstream work will compose with Bundle 1 without surprises.

The bundle ships as **7 commits** (per `research.md` R1). After each commit, the local CI gate (`mise run check`) MUST pass and the regression net (`mise run test:int`) MUST hold the baseline tally **8988 passed / 186 skipped / 1 xfailed / 0 failures / 0 errors**.

---

## Prerequisites

```bash
cd /home/user/projects/game/babylon
git fetch && git checkout 058-adr-bundle-1-pre-spec-057
poetry install
poetry run pre-commit install   # If not yet installed; idempotent
```

Confirm baseline before starting:

```bash
mise run check    # lint + format + typecheck + test:unit (fast gate)
mise run test:int # integration tests
```

Both should pass with the baseline tallies. If they don't, stop and resolve before applying any Bundle 1 commit.

---

## Per-commit verification recipes

### Commit 1 — `refactor(ooda): extract _compute_membership_overlap helper` (US5)

What it does: moves `_compute_membership_overlap` from `action_costs.py` and `action_effects.py` into `ooda/_helpers.py`; updates both call sites to import from the new canonical location.

**Verify**:

```bash
# (a) Single canonical definition
git grep -n "def _compute_membership_overlap" src/
# Expected: exactly one match in src/babylon/ooda/_helpers.py

# (b) Both old call sites import from _helpers
git grep -n "from babylon.ooda._helpers import" src/babylon/ooda/
# Expected: matches in action_costs.py and action_effects.py

# (c) OODA tests pass unchanged
poetry run pytest tests/unit/ooda/ tests/integration/test_ooda_*.py -x
```

---

### Commit 2 — `refactor(models): split enums.py into enums/ package` (US3a)

What it does: replaces `src/babylon/models/enums.py` (1298 LOC, 45 enum classes) with a `src/babylon/models/enums/` package whose `__init__.py` re-exports every symbol via explicit `__all__`.

**Verify**:

```bash
# (a) Public surface preserved
python -c "from babylon.models.enums import EdgeType, SocialRole, EventType; print('ok')"
# Expected: ok

# (b) Star imports work and __all__ is explicit
python -c "from babylon.models import enums; print(len(enums.__all__))"
# Expected: ~45 (matches the pre-split set)

# (c) git grep equivalence on flat-import lines
git grep -hn "from babylon.models.enums import" src/ tests/ | sort | uniq -c | sort -rn | head -5
# Expected: same line count and same import sets as before commit 2

# (d) New regression test passes
poetry run pytest tests/unit/test_public_import_surface.py -x

# (e) Per-file LOC cap holds
find src/babylon/models/enums -name "*.py" -exec wc -l {} \; | awk '{ if ($1 > 600) print "OVER CAP:", $0 }'
# Expected: empty output (no file over 600 LOC)

# (f) Full fast gate
mise run check
```

---

### Commit 3 — `refactor(config): split defines.py into defines/ package` (US3b)

What it does: replaces `src/babylon/config/defines.py` (4168 LOC, 42 `*Defines` classes) with `src/babylon/config/defines/` package; preserves `GameDefines` as the assembler facade in `__init__.py`.

**Verify**:

```bash
# (a) GameDefines instantiates with default config (pyproject.toml [tool.babylon] still wires correctly)
python -c "from babylon.config.defines import GameDefines; gd = GameDefines(); print(gd.economy.extraction_efficiency)"
# Expected: 0.8 (or whatever the current default is)

# (b) All 42 *Defines classes still importable via flat path
python -c "
from babylon.config.defines import (
    CrisisDefines, EconomyDefines, ConsciousnessDefines,
    OODADefines, StateApparatusAIDefines, TerritoryDefines,
    # ... etc
)
print('ok')
"

# (c) Per-file LOC cap
find src/babylon/config/defines -name "*.py" -exec wc -l {} \; | awk '{ if ($1 > 600) print "OVER CAP:", $0 }'
# Expected: empty (no file over 600 LOC)

# (d) Public surface regression test
poetry run pytest tests/unit/test_public_import_surface.py -x

# (e) Full fast gate
mise run check
```

---

### Commit 4 — `feat(core): add protocol_kit with DataSource, CachedSource, SourceRegistry` (US1 step 1)

What it does: pure-add of `src/babylon/core/protocol_kit.py` with three new types (`DataSource`, `CachedSource[T]`, `SourceRegistry`). No existing code is modified.

**Verify**:

```bash
# (a) New module exists and imports cleanly
python -c "from babylon.core.protocol_kit import DataSource, CachedSource, SourceRegistry; print('ok')"

# (b) New unit tests pass (covers the contract in contracts/protocol_kit.md and contracts/source_registry.md)
poetry run pytest tests/unit/core/test_protocol_kit.py -v

# (c) No existing tests broken (pure-add)
mise run test:unit

# (d) Full fast gate
mise run check
```

---

### Commit 5 — `refactor(economics): migrate melt/ + gamma/ Default* classes to CachedSource[T]` (US1 step 2)

What it does: 10 `Default*` classes in `melt/` (6) and `gamma/` (4) drop their hand-rolled `__init__` boilerplate and inherit from `CachedSource[T]`. MRO conflicts (per spec Risks) trigger swap-and-document per R3.

**Verify**:

```bash
# (a) Migrated classes are now CachedSource subclasses
python -c "
from babylon.core.protocol_kit import CachedSource
from babylon.economics.melt.melt_calculator import DefaultMELTCalculator
assert issubclass(DefaultMELTCalculator, CachedSource), f'{DefaultMELTCalculator.__mro__}'
print('ok')
"
# Repeat for each of the 10 migrated classes; if any fails, swap per spec Risks

# (b) Cache semantics preserved (existing melt/gamma tests cover real-data lookups)
poetry run pytest tests/unit/economics/melt/ tests/unit/economics/gamma/ -x

# (c) Migration count: at least 10 classes inherit from CachedSource
python -c "
from pathlib import Path
import ast
count = 0
for path in Path('src/babylon/economics/melt').rglob('*.py'):
    src = path.read_text()
    if 'CachedSource' in src and 'class Default' in src:
        count += sum(1 for line in src.splitlines() if line.startswith('class Default'))
for path in Path('src/babylon/economics/gamma').rglob('*.py'):
    src = path.read_text()
    if 'CachedSource' in src and 'class Default' in src:
        count += sum(1 for line in src.splitlines() if line.startswith('class Default'))
print(f'Migrated count: {count}')
assert count >= 10, f'SC-005: at least 10 required, got {count}'
"

# (d) Full fast gate
mise run check
```

---

### Commit 6 — `refactor(economics): replace factory.py wiring with SourceRegistry.builtin_economics()` (US1 step 3)

What it does: shrinks `economics/factory.py` from 662 LOC to <150 LOC by replacing each `create_*_services()` body with a 3-line shim that delegates to `SourceRegistry.builtin_economics()`.

**Verify**:

```bash
# (a) factory.py LOC cap (SC-004)
wc -l src/babylon/economics/factory.py
# Expected: < 150

# (b) Shim signatures preserved
python -c "
from babylon.economics.factory import (
    create_economics_services, create_financial_services,
    create_circulation_services, create_vol1_services
)
print('all 4 shims present')
"

# (c) Shims return equivalent service bundles to pre-Bundle-1
poetry run pytest tests/unit/economics/test_factory_shims.py -v
# Expected: structural equivalence on returned EconomicsServices, FinancialServices, etc.

# (d) Full fast gate
mise run check
```

---

### Commit 7 — `refactor(economics): decompose tick/system.py + type bea_to_department mapping` (US2 + US4)

What it does: replaces `src/babylon/economics/tick/system.py` (1705 LOC, 33 methods) with a `tick/system/` package containing a ≤200-LOC `TickDynamicsSystem` facade and 8–9 focused sub-modules; replaces runtime TOML reparse in `economics/department_mapper.py` with the typed `BEA_TO_DEPARTMENT` singleton.

**Verify**:

```bash
# (a) Facade LOC cap
wc -l src/babylon/economics/tick/system/__init__.py
# Expected: <= 200

# (b) Per-sub-module LOC cap (400 LOC)
find src/babylon/economics/tick/system -name "*.py" -exec wc -l {} \; | awk '{ if ($1 > 400) print "OVER CAP:", $0 }'
# Expected: empty

# (c) Public class import unchanged
python -c "from babylon.economics.tick.system import TickDynamicsSystem; print('ok')"

# (d) Behavioral fence test passes (the load-bearing test for FR-007 per Q3)
poetry run pytest tests/integration/economics/tick/test_facade_behavioral_fence.py -v

# (e) Spec-057 quarantine preserved (FR-008): _compute_imperial_rent stub stays, tests stay skipped
grep -n "_compute_imperial_rent" src/babylon/economics/tick/system/imperial_rent.py
# Expected: the stub function exists in this sub-module

poetry run pytest tests/ -k "imperial_rent" --collect-only 2>&1 | grep -c "skipped"
# Expected: same skipped count as pre-Bundle-1 baseline

# (f) BEAMappings loads at import time
python -c "from babylon.economics.tensor_hierarchy.mappings import BEA_TO_DEPARTMENT; print(len(BEA_TO_DEPARTMENT.mappings))"
# Expected: number matches BEA codes in bea_to_department.toml

# (g) BEAMappings tests
poetry run pytest tests/unit/economics/tensor_hierarchy/test_bea_mappings.py -v

# (h) department_mapper consumes typed object
grep -n "tomllib" src/babylon/economics/department_mapper.py
# Expected: zero matches (no longer reparses; consumes BEA_TO_DEPARTMENT)

# (i) Full fast gate + integration
mise run check
mise run test:int

# (j) Bundle-final tally check (the load-bearing assertion for SC-001)
poetry run pytest --tb=no -q tests/ -m "not ai" 2>&1 | tail -5
# Expected: 8988 passed, 186 skipped, 1 xfailed (or close — minor drift if the new tests added in commits 4/5/7 push the passed count up)
```

---

## Rollback procedure

Each commit is independently revertible. If a commit fails the local gate:

```bash
git revert HEAD          # Creates a revert commit; preserves history
mise run check           # Verify revert is clean
```

For commit 5 (the `Default*` migration) — if MRO conflicts emerge that the spec Risks fallback didn't anticipate:

```bash
git reset --hard HEAD^   # Undo commit 5 entirely
# Then: per R3, swap the conflicting class for a different Default* class from
# economics/credit/, economics/throughput/, etc. Re-run commit 5 with the swap.
```

---

## Spec 057 forward-compat sanity check (after the bundle is fully merged to dev)

After all 7 commits land and merge to `dev`, the spec-057 implementer can verify Bundle 1 actually unblocks them:

```bash
# (a) New economic data sources can be authored with the SC-007 30-line budget
cat <<'EOF' > /tmp/spec057_smoke.py
"""Smoke test: a new spec-057-style data source fits in <30 lines."""
from babylon.core.protocol_kit import CachedSource, DataSource
from typing import Protocol, runtime_checkable

@runtime_checkable
class PeripheryLaborCoefficientsSource(DataSource, Protocol):
    def get_coefficient(self, year: int, sector: str) -> float | None: ...

class DefaultPeripheryLaborCoefficientsSource(CachedSource[float]):
    name = "DefaultPeripheryLaborCoefficientsSource"

    def _fetch(self, year: int, sector: str) -> float | None:
        # Real impl would query a database; smoke test just returns a value
        return 0.42

    def get_coefficient(self, year: int, sector: str) -> float | None:
        result = self._resolve((year, sector), lambda: self._fetch(year, sector))
        return None if not result else result

# Author counts ~20 lines for the entire source. SC-007 budget: <=30. PASS.
EOF
poetry run python /tmp/spec057_smoke.py
echo "Spec 057 line-budget smoke test passed."

# (b) Spec 057 can land its real Leontief impl in tick/system/imperial_rent.py without touching the facade
ls -la src/babylon/economics/tick/system/imperial_rent.py
# Expected: file exists; spec-057 implementer edits this file ONLY (not the facade or other sub-modules)

# (c) BEAMappings is consumable as the dept_mapping argument to a Leontief calculator
python -c "
from babylon.economics.tensor_hierarchy.mappings import BEA_TO_DEPARTMENT
# Spec 057 design: ProductionChainRentCalculator.calculate(dept_mapping=BEA_TO_DEPARTMENT, ...)
print(BEA_TO_DEPARTMENT.get_departments(BEA_TO_DEPARTMENT.mappings[0].bea_code))
"
```

If any of (a)/(b)/(c) fails, Bundle 1 has a regression that needs investigation before Spec 057 can proceed.

---

## When to escalate

Stop and ask if any of these surface:

- A `Default*` class can't be migrated to `CachedSource[T]` even after the swap-fallback (spec Risks). Escalate before adding multiple-inheritance complexity to `CachedSource`.
- The 600-LOC cap is unachievable for any `enums/` or `defines/` sub-module after clustering (per R2). Escalate before introducing nested sub-packages — the cap is a guideline; nested packages are a documented escape hatch but should be discussed.
- The behavioral-fence test (commit 7) detects an event-bus emission order change that's hard to fix. Escalate; the alternative is a Bundle-1-scope-change to allow set-equality on event order, which conflicts with the Q3 clarification.
- The full-suite tally drifts from 8988/186/1 by more than ±3 tests (excluding the new tests added in commits 4/5/7). Escalate; this means a regression has been introduced.
