# National launcher contract implementation plan

> **For agentic workers:** Use `superpowers:subagent-driven-development` with
> GPT-6.1 Terra at extra-high reasoning. Record RED/GREEN and review evidence.

**Goal:** Repair the current national installation check and exercise the actual
Rust producer and Python consumer together through disposable Postgres.

**Architecture:** Retain the existing runtime/launcher ownership. Accept the
current economy-status v2 response and refuse unsupported versions. Extend the
existing session smoke rather than add another runtime API or qualification task.

**Tech Stack:** Pinned Python runner, Rust client/runtime, PostgreSQL 17 and the
existing `tools/run_rust_postgres.sh` owned disposable lifecycle.

**Spec:** The active thread Goal and
`reports/gameplay-delivery-audit-2026-10-29.md`, launch-check finding.
This plan is the first subproject of the full enemy-AI and next-gameplay Goal.

## Constraints and review focus

- Preserve unrelated patches, existing campaigns and source history.
- No compatibility adapter, game-law change, new runtime API or docs generation.
- Keep complete campaign/period/scope/hash checks and strict JSON value types.
- Keep the standard session smoke and disposable-resource cleanup.
- Serialize heavy checks and retain the existing phase budgets.

## Task 1: Fix the consumer and qualify the real producer

**Files:** `tools/run_observer_session.py`,
`tests/unit/tools/test_run_observer_session.py`,
`tools/run_rust_postgres.sh` and directly applicable existing runner contracts.

**Interfaces:** `_national_economy_status` keeps its current signature and
response shape. The current Rust producer emits integer `schema_version: 2`.
The session-progress smoke invokes the existing installation check with both
`standard` and `national-world` presets.

- [x] Make the unit fixture use v2 and observe the national smoke fail before
  changing the launcher. Preserve all identity and scope assertions.
- [x] Cover refusal of old v1, future v3, boolean and string schema values.
- [x] Change the launcher expectation to v2 and verify the affected unit tests.
- [x] Run standard and national installation checks serially in the existing
  disposable session-progress focus. Preserve exact-child and resource cleanup.
- [x] Run Python scope, shell/static checks and the required Python gate.
- [x] Build the unchanged Rust binaries, then run the real disposable focus.
- [x] Review the task, address findings and commit the verified repair.

## Later subprojects retained by the active Goal

Complete the finite Wayne playtest with explicit human evidence. Repair enemy
belief and budget-policy boundaries and integrate a deterministic opponent into
real campaigns. Deliver the bounded Wayne topology scene under PER-292 using
the current action authority. Their plans follow current source/tracker and
governance discovery, without counting design documents as implementation.
