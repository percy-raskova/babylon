# Separate native timing and memory qualification

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development. Execute the tasks below with independent task reviews and a final whole-branch review.

**Goal:** Qualify native Wayne only when ordinary-play timing and a separate complete memory run both pass against the same build, captured inputs and decisions.

**Architecture:** Retain one native workload and select an explicit measurement mode. Each member independently authenticates its actions, committed state, recovery and custody. A versioned pair join is the only native qualification authority; neither member can qualify alone.

**Tech stack:** Existing Python operator tools and frozen Pydantic records; locked Rust/Bevy game; existing PostgreSQL ownership, backup and qualification paths.

**Spec:** Director's 9 November 2026 approval in this chat, “Separate timing and memory runs; require both.” Preserve the canonical Wayne design at `docs/superpowers/specs/2026-11-03-wayne-map-and-relationships-design.md`. This is a bounded execution supplement to the solidarity-loop plan, not another design authority.

## Global Constraints

- Keep the numeric policy `contracts/national_storage_qualification_v6.json` byte-identical. Normal play must satisfy cold open/reopen <180 seconds, advances <=120 seconds, Archive <=180 seconds, production reads <=180 seconds, focused controls <=60 seconds and the existing two-period smoke <=900 seconds. The longer walkthrough is timed separately.
- The memory member retains the full current scope, creation/period coverage, immutable source and executable admission, exact process/backend identity, ownership/authority checks, restoration, RSS plus hugetlb <=10,000,000,000 bytes and maximum unsampled gap <=5 seconds. Its raw phase durations are diagnostic. Use the existing finite 900-second operation watchdog where ordinary performance deadlines are intentionally absent. Preserve existing control/cleanup watchdogs. Never subtract freezes or invent zero-memory evidence.
- Run members serially in distinct newly owned databases and private XDG directories under the existing single common lease. Give the pair one newly declared canonical campaign UUID, used only in its two empty databases. Preserve all original P7/Michigan/personal state and every prior test artifact, source and binary. Never query protected campaigns or operate shared services.
- Require equal source closure, actual role-to-binary digests, captured input manifest, policy, workload, requested horizon and ordered actual decision semantics. Ordinary command nonces differ legitimately: preserve and validate exact raw command -> commitment -> receipt -> marker joins inside each member; compare period, actor/target/partner, practice and exact selected allocations across members. Do not normalize arbitrary fields, demand equality of nonce-bearing raw hashes, or trust a caller-supplied decision hash without deriving it from authenticated evidence.
- Reuse the same controls, decisions, Play/Pause, reports/Archive, ordinary reopens and all three process-cold Wayne walk segments in both modes. A valid normal member cannot substitute for missing/failed memory. Preserve within-member functional-state equality across restart and custody.
- Version changed evidence/report formats and reject unsupported old input before writes. Keep one current implementation. Never retain a compatibility path that can publish the old single-run native qualification.
- Native measurement mode is orthogonal to `smoke-01`/`walk-01` workload identity. Use a fresh `qualification-10` namespace and one canonical mode-aware path resolver throughout runner, storage and backup. Never alias or overwrite old namespaces or manufacture owner records.
- Source work is on the existing isolated `codex/PER-364-wayne-solidarity-loop` lane, based on `50e2b5281cb95c82e01bb2ee2246627702ffd2d3`, which includes refreshed `origin/dev` `40a4f4d999f8655c5b1a6d550d2c25c5e7a07ad8`. PR1052 stays unchanged. No merge is authorized.
- Follow RED/GREEN for meaningful regressions, explicit strict immutable types and specific errors. Use existing mise tasks, BLAS=1, media storage and serial heavy jobs; no documentation generation or blanket cleanup. Preserve prior binaries before any build can replace them.
- Research informs the implementation without expanding it into a telemetry platform. Retain raw measurements and explicit mode/identity context. No new game mechanic, tracing backend, dependency, profiler installation or build-profile change is needed for this split.

## Review Focus

- A valid timing run paired with missing, failed, copied or wrongly scoped memory evidence must fail qualification.
- Matching names with different inputs, binaries, campaign declaration, horizon, target or allocation must fail the authenticated join.
- Different legitimate nonces must be accepted only when each member's exact receipts and committed markers validate and the selected decisions agree.
- Every startup/restart/Archive phase must retain its own evidence; capture durations cannot enter the normal timing verdict or be silently discarded.
- A completed member must be safely backed up and retired without issuing final native qualification or weakening failed-fixture retention.

---

### Task 1: Implement mandatory paired qualification end to end

**Ownership:** `tools/devtools/national_native_evidence.py`, `national_storage_qualification.py`, `national_native_runner.py`, `national_windowed_qualification.py`, `wayne_qualification_storage.py`, `wayne_qualification_backup.py`, the exact consuming operator/shell entrypoints including `tools/postgres_national_lifecycle.sh` and `tools/run_rust_postgres.sh`, and directly covering unit/contract tests. Add `tools/devtools/national_native_pair.py` and its focused test file if this keeps the pair join separate from existing large validators. No gameplay or numeric-policy changes; no Rust change is necessary for elapsed ceilings, which Rust records rather than enforces. You are not alone; preserve unrelated work. Do not spawn subagents.

**Interfaces:** Introduce strict `MeasurementMode = Literal["normal_play", "memory_capture"]`. Extend the current native leaf manifest to version 5 with explicit measurement purpose and authenticated input binding. Add `NativePairEvidence` version 1 with scope `native_timing_and_memory_pair_v1`, binding exactly one member of each purpose to a frozen declaration and retained artifact references. Bump the final qualification report from version 7 to 8. Keep unmodified Rust leaf receipt schemas and the numeric policy v6. Final concrete producer/parser signatures must be reported for Task 3.

- [ ] Add meaningful RED cases using existing valid qualification fixture builders: normal-only, missing/failed memory, duplicate mode, reused actual owner/process incarnation, substituted bundle, changed inputs/build/policy/horizon/campaign/decision target/allocation, old format and tampered per-run receipt. Add a positive case with different legitimate nonces and exact within-member joins.
- [ ] Implement the typed join over independently validated member bundles. Derive the actual decision projection from authenticated commands and receipts. Verify each member's own clocks, scope, source, material, recovery and complete evidence roster before joining. Distinct owners and actual process incarnations are required; opaque final world/receipt hashes are not cross-run equality keys.
- [ ] Add explicit mode to the ordinary runner and operator admission. Normal mode never constructs a sampler or writes a memory certificate; memory mode retains the existing complete sampler. Authenticate P0/foundation independently of capture in both. Keep all workload callbacks and three Wayne process-cold segments on the same path. Apply ordinary performance ceilings only to normal mode; enforce resource coverage and finite operation/control watchdogs in memory mode. Retain raw durations and explicit mode in both.
- [ ] Bind both new fixtures to one admitted pair declaration and new campaign UUID. Centralize `qualification-10/<workload>/<mode>` resolution for source release, ownership, portable inventory, custody and backup. Preserve the existing exclusive lease and independent restore verification before each retirement.
- [ ] Publish a narrowly scoped completed-member receipt sufficient for successful-member backup/retirement. It is not final native qualification. Publish final `qualification.json` only after both authenticated member bundles qualify. Wire the real operator entrypoint/evaluator/export roster to this final gate; do not leave an optional helper or a single-run success path.
- [ ] Run focused Python RED/GREEN, affected runner/socket/storage/backup/contracts, shell syntax and applicable static checks, then one `mise run check` before commit. No live fixture or Cargo job in this task. Record actual commands, output, versions, complete changed files, concrete operator invocation and limits in the report. Commit through `mise run commit` with Part of PER-364 and the required coauthor.

**Deliverable:** The actual operator -> native member -> independent evidence -> retirement -> pair evaluation path works through consuming tests and fails closed on incomplete or mismatched pairs. Test evidence and source review are not native acceptance.

### Task 2: Finish the two already reviewed presentation regressions

**Ownership:** `rust/crates/babylon-client/src/organizer/presentation.rs` and its existing inline tests only. Use the prepared patches under the prior solidarity ledger's `task-4-final-branch-review-09/` as context, not an unreviewed replacement. You are not alone; preserve Task 1 and unrelated edits. Do not spawn subagents.

- [ ] Prove RED for food refusal being described as whole-gift refusal when cash remains accepted, and pantry food-only support being described as cash-constrained.
- [ ] Correct only the inaccurate text and its meaningful assertions. Preserve actual practice availability, selected amounts, authored costs, independent material paths and accounting.
- [ ] Run scoped client tests, format and applicable strict Clippy serially with exclusive build storage. Commit normally and report exact covering results. No live native game or full repeated gate in this task.

### Task 3: Record the approved method and research in canonical documentation

**Ownership:** one new `ai/decisions/ADR294_native_timing_and_memory_qualification.yaml` and its index entry; the existing Wayne design; relevant qualification paragraphs in `docs/concepts/architecture.rst`; Task 4 of `docs/superpowers/plans/2026-11-06-wayne-solidarity-loop.md`; one short dated research note if needed. Preserve all historical ADRs/reports and the October 26 research briefing. You are not alone; preserve earlier code. Do not spawn subagents.

- [ ] Record the Director-approved separation, both-required gate, unchanged numeric caps, actual mode-aware producer/parser/entrypoint interfaces and independent member custody. Distinguish normal timing from captured diagnostics and retained within-member identities from cross-run decision semantics.
- [ ] Record the observed same-build 130.587-second opening without capture versus 180-second failure with at least 41.719 seconds of imposed freezes. Label this one serial diagnostic pair, not historical sole-cause proof, a timing distribution or native qualification.
- [ ] Summarize only verified relevant primary-source guidance from Tavily and the actual local shelf search. The book was not found or read; do not attribute chapter/page advice to it. Separate cited guidance from Babylon design choices. Keep proposed broad telemetry features outside this delivery.
- [ ] Run targeted prose/YAML checks and normal commit hooks without documentation generation. Report the exact canonical updates and remaining actual acceptance.

### Task 4: Qualify the final source and resume the Wayne delivery

- [ ] Obtain independent task reviews and one final whole-branch review. Resolve findings through the owning worker with scoped retests. Preserve reviewed artifacts and all old products before rebuilding.
- [ ] Run the applicable serial final formatting, scoped tests, strict Clippy, decision-surface contracts, BSL, Python/publishing checks and the required no-docs Rust gate after the final changes. Build/export the actual final native programs with current source and input receipts; retain prior binaries.
- [ ] Exercise the real operator in fresh disposable national fixtures: normal smoke then verified backup/retirement; matching full memory smoke then verified backup/retirement; authenticate and evaluate the required pair. Capture real cold opens, two decisions, Archive catch-up and ordinary restart. No time subtraction, Michigan substitution, cap changes or fabricated certificates.
- [ ] Perform both required members of the ten-period authored walkthrough: collect -> local food-only -> remote mixed -> explicitly manage routine during arrival -> cash-only -> subsequent purchasing close, using actual route timing. Retain pending and completed process-cold restarts and raw evidence. Inspect the existing four resolution/scale variants and required native frames, then publish comparison evidence without claiming unobserved behavior.
- [ ] Prepare the follow-up PR to `dev`, preserving PR1052 and bounded Linear scope. Complete heavy checks before preparing the already-authorized separate fresh human game. Record comprehension, hesitation, chosen follow-up and desire to continue when the user plays. Leave human acceptance explicitly open until that session occurs. No merge.
