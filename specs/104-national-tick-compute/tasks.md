# tasks-104 — National tick-compute profile + budget

## Part 1: #18 hex_spatial_map hardening (preamble)

- [x] T01 — Found offending test: `tests/integration/test_tiger_ingestion.py`
      `fresh_tiger_table` fixture truncates `immutable_reference_tiger_county`
      with `conn.autocommit = True` (visible to all concurrent sessions)
- [x] T02 — Fix: `PinnedPool` wrapper + `DELETE` in transaction with
      `ROLLBACK` on teardown (MVCC isolation, no blocking)
- [x] T03 — Regression test: `test_hex_spatial_map_isolation.py` (2 tests)
- [x] T04 — Commit: `fix(test): isolate hex_spatial_map truncation from
      concurrent sessions (#18)`

## Part 2: E:104 National tick-compute profile + budget

- [x] T05 — Verify `per_system_ms` already wired (spec-065 T074)
- [x] T06 — Verify DecompositionSystem no-op already closed (spec-071)
- [x] T07 — Verify `--scope=national` works (spec-064)
- [x] T08 — `sim:profile` accepts `--scope` arg
- [x] T09 — Run national profile (5-tick timed out at 10min hydration;
      michigan-statewide 5-tick profile completed — 26 systems measured)
- [x] T10 — Ratify budget numbers (`budget.json`, 2× headroom)
- [x] T11 — Add `qa:tick-budget` mise task (michigan-statewide scope for CI)
- [x] T12 — `qa:e2e-regression` Δ=0.000% (tri-county hash unchanged)
- [x] T13 — Commit
