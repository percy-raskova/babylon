# Babylon Project Management Directory

**Purpose**: the one-stop shop for ANY agent (Claude Sonnet/Opus/Fable, or a human)
to catch up on the project and pick up work mid-stream without the originating
session's context. This directory is about **project management** — plans, status,
assessments, owner decisions. Its sibling `ai-docs/` is about **documentation for
AI** — architecture, decisions (ADRs), tooling, machine-readable state.

**The goal (definition of done)**: `reports/aidocs-vs-code-audit-2026-05-16.md`
is implemented (the 27-spec Epoch-3 catalog, Waves 1–5) **and** the game works
locally (Django+React app playable end-to-end against the real engine).

## Catch up in five minutes

1. `execution/PROGRESS_REPORT-2026-07-08.md` — where the work stands right now.
2. `execution/REMEDIATION_PLAN.md` — the ratified plan currently being executed.
3. `programs/00-mission.md` — the mission and Percy's standing working agreements.
4. `programs/01-state-of-the-world.md` — environment facts and what is DONE (with
   commits); verify its "pending verification" items before building on them.

**Authority chain** (later documents supersede earlier ones where they conflict):
`programs/09-program-full-game.md` (scope) → `assessments/POST_ASSESSMENT.md` →
`assessments/HOLISTIC_REVIEW-2026-07-07.md` → `execution/REMEDIATION_PLAN.md` →
the newest `execution/PROGRESS_REPORT-*.md`.

## Directory map

| Directory | What lives here | Read when |
| --- | --- | --- |
| `programs/` | The numbered planning corpus `00`–`09`: mission, state of the world, engine truths, per-program plans (071, 098, catalog waves, dialectics, chat-corpus alignment, graph substrate, full-game build) | Planning any work; `00` + `01` always first |
| `assessments/` | Independent reviews and audits: the Jul-7 browser E2E (`E2E_SUMMARY.md`), the Program-09 post-merge review (`POST_ASSESSMENT.md`), the 15-agent whole-repo sweep (`HOLISTIC_REVIEW-2026-07-07.md`) | Before trusting any status claim made elsewhere |
| `execution/` | Active execution records: the remediation plan, progress reports, `briefs/` (verified scout implementation briefs, one per remaining branch), `phase7-inputs.md` (accumulated record-repair inputs), the historical `_PROGRESS.md` / `_HANDOFF.md` session records, the frozen `c17-test-migration-ledger.md` | Doing the work; catching up on how it went |
| `owner/` | `owner-queue.md` — decisions needing/holding Percy's rulings | Before making any call that smells like an owner decision |
| `reference/` | Source texts kept in-repo for the project record | As needed |

## Reading order for the planning corpus (`programs/`)

| File | What it holds | Read when |
| --- | --- | --- |
| `00-mission.md` | Goal, roadmap authority, sequencing, working agreements | Always, first |
| `01-state-of-the-world.md` | What is DONE (with commits), in-flight work, environment facts | Always, second |
| `02-engine-truths.md` | Engine architecture truths + gotchas + repro recipes (2026-07-02 forensics) | Before touching the engine or bridge |
| `03-next-spec-071.md` | Execution plan for spec-071 Reactionary Subject | When starting 071 |
| `04-data-program-098.md` | Reference-DB build pipeline program (spec-098) | Before loader work |
| `05-catalog-execution.md` | Waves 2–5 execution order, per-spec notes, local-play items | Everything after 071 |
| `06-lawverian-dialectics.md` | MASTER RECORD: dialectics refactor (ADR051), IMPLEMENTED | Before contradiction/opposition/regime code |
| `07-chat-corpus-alignment.md` | Owner rulings + uncatalogued mechanics (M1–M12) + experience layer (X1–X9) | Before scoping new features or UX |
| `08-graph-substrate.md` | BabylonGraph/rustworkx record (Amendment L, ADR052), gotchas | Before graph/engine internals |
| `09-program-full-game.md` | Program 09 full-game build — 4 lanes, spec catalog 090+ | Before any 090+ spec |

**Status note (2026-07-08):** Program 09 merged on Jul 6, but the first real E2E
(assessments/) found the product unplayable at merge. The active work is the
remediation program in `execution/REMEDIATION_PLAN.md`; `09-program-full-game.md`
remains the scope authority.

## How to use this directory

1. Read the catch-up list above. Do not skip `00`/`01`.
2. Follow the working agreements in `programs/00-mission.md` — they are Percy's
   standing rules, not suggestions.
3. Keep it accurate: when you complete a unit, update the newest progress report
   (or add one) and the relevant program file. Accuracy over comprehensiveness —
   five accurate documents beat fifty stale ones.
4. Where a document conflicts with the repo, **the repo wins** — and say so in the
   document you fix (see `assessments/` for the evidence standard).

## Reorganization note (2026-07-08)

This directory was flat until 2026-07-08; documents were moved (git mv, history
preserved) into the structure above. Older documents reference the flat paths —
map them as: `project/NN-*.md` → `project/programs/NN-*.md`; `project/POST_ASSESSMENT.md`,
`project/HOLISTIC_REVIEW-2026-07-07.md` → `project/assessments/`; repo-root
`E2E_SUMMARY.md` → `project/assessments/E2E_SUMMARY.md`; `project/REMEDIATION_PLAN.md`,
`project/_PROGRESS.md`, `project/_HANDOFF.md`, `project/c17-test-migration-ledger.md`
→ `project/execution/`; `project/owner-queue.md` → `project/owner/owner-queue.md`.

## Companion sources (do not duplicate, point into them)

- The catalog itself: `reports/aidocs-vs-code-audit-2026-05-16.md` (Part 3 =
  the 27-spec roadmap; Part 4 = dependency graph; Part 5 = doc hygiene).
- Live project state: `ai-docs/state.yaml` (its `truth_status` banner governs),
  `ai-docs/decisions/` (ADR index — ADR051 dialectics + ADR052 graph substrate),
  `ai-docs/tuning-standard.yaml` (20-Year Entropy Standard).
- Governance: `.specify/memory/constitution.md` **v2.7.0** (Amendment K =
  dialectics, Amendment L = rustworkx substrate; II.12 authoring-API and
  III.7 determinism-hash gates bind all engine work).
- Theory library (the economics the game must express): `grundrisse.pdf`,
  `Capital-Volume-{I,II,III}.pdf` in repo root; `/home/user/Downloads/babylon_books/`
  (Cope's *Divided World Divided Class*, Amin, Federici, econophysics);
  `/media/user/data/mim/` (MIM Theory, Cope, Amin).
