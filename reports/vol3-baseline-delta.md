# Vol III Money — Baseline Delta

**Status:** DRAFT — pending owner approval (see U8.3's "Owner Approval Gate" section,
not yet authored).
**Design:** `docs/superpowers/specs/2026-07-18-vol3-money-scissors-design.md`

This file's full structure (Owner Approval Gate, per-scenario delta tables, named
mechanisms) is authored by Task U8.3. Task U4.8 creates this skeleton early only to
record the U4 monetary-anchor gate sweep, per its own instructions.

## Verification evidence

| Check | Command | Result | Evidence |
|---|---|---|---|
| U4 gate sweep | `mise run lint:imports`; `mise run check:quick`; `mise run test:q -- tests/unit/economics/monetary/test_anchor.py tests/property/invariants/test_monetary_anchor_absence.py`; `mise run qa:regression` | `lint:imports`: PASS — "Contracts: 6 kept, 0 broken." `check:quick`: PASS — Ruff "All checks passed!", format "1727 files left unchanged", MyPy "Success: no issues found in 639 source files". Anchor tests: PASS — "35 passed in 2.26s" (28 in `test_anchor.py` + 7 property tests; the brief's documented count of 29 is stale against what U4.1-U4.7 actually landed — a benign count drift, not a failure). `qa:regression`: PASS — "Results: 5 passed, 0 failed" — all 5 scenarios (`imperial_circuit`, `two_node`, `starvation`, `glut`, `fascist_bifurcation`) byte-identical to the pre-U4 baseline. | `.superpowers/sdd/task-U4.8-report.md` |

## U5 acceptance evidence

Task U5.9 closes the unit (bind four Volume III oppositions + activate CouplingGraph).
Dialectics + engine suite (314 tests) and `check:quick` both PASS; no test asserted a
specific principal-contradiction key, so no ranking-consequence observation to carry
forward. §5 hazard 3 (no new shadow accumulator) is clear — `rg -n
'persistent_data\[|context\.persistent'` over `contradiction.py` and
`market_scissors.py` returns only a pre-existing docstring mention, identical to what
`dev` already has.

**Registry key tuple** (`build_default_registry().keys`, catalog 6 → 10):

```
10 ('atomization', 'capital_labor', 'credit', 'debt_spiral', 'financial', 'imperial', 'price_value', 'surplus_distribution', 'tenancy', 'wage')
```

**Reserved `transforms` edges surviving `build_default_coupling_graph`**, with the two
`Skipping coupling` INFO lines (both naming Volume II endpoints not yet registered):

```
INFO:babylon.domain.dialectics.instances.catalog:Skipping coupling circulation -> realization (transforms): endpoint(s) not yet registered
INFO:babylon.domain.dialectics.instances.catalog:Skipping coupling reproduction -> disproportionality (transforms): endpoint(s) not yet registered
[('credit', 'financial', 'transforms'), ('surplus_distribution', 'debt_spiral', 'transforms')]
```

Both `surplus_distribution -> debt_spiral` and `credit -> financial` survive the
builder; only the two Volume II circulation edges (`realization`, `disproportionality`)
are still skipped, matching spec §7's prediction that binding the four endpoints
activates exactly these two dormant crisis-producer couplings.

Evidence: `.superpowers/sdd/task-U5.9-report.md`.
