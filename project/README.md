# Babylon Continuation Kit

**Purpose**: This directory is the durable, agent-agnostic execution program for
finishing Babylon — written so that ANY agent (Claude Sonnet/Opus/Fable, or a
human) can pick up the work mid-stream without the originating session's
context. It captures the master plan ratified by Percy Raskova (BD) on
2026-07-02 and the hard-won engine knowledge from that session's forensics.

**The goal (definition of done)**: `reports/aidocs-vs-code-audit-2026-05-16.md`
is implemented (the 27-spec Epoch-3 catalog, Waves 1–5) **and** the game works
locally (Django+React app playable end-to-end against the real engine).

## Reading order

| File                       | What it holds                                                                       | Read when                            |
| -------------------------- | ----------------------------------------------------------------------------------- | ------------------------------------ |
| `00-mission.md`            | Goal, roadmap authority, sequencing, working agreements                             | Always, first                        |
| `01-state-of-the-world.md` | What is DONE (with commits), what is in flight, environment facts                   | Always, second                       |
| `02-engine-truths.md`      | Engine architecture truths + gotchas + repro recipes from the 2026-07-02 forensics  | Before touching the engine or bridge |
| `03-next-spec-071.md`      | Concrete execution plan for spec-071 Reactionary Subject (the next unit)            | When starting 071                    |
| `04-data-program-098.md`   | Reference-DB build pipeline program (spec-098)                                      | When starting 098 or any loader work |
| `05-catalog-execution.md`  | Waves 2–5 execution order, per-spec notes, local-play completion items, doc hygiene | For everything after 071             |

## How to use this kit

1. Read `00` and `01` completely. Do not skip.
1. Verify the "pending verification" items in `01` before building on them.
1. Follow the working agreements in `00` — they are Percy's standing rules,
   not suggestions.
1. Keep this kit accurate: when you complete a unit, update `01` (status) and
   the relevant program file. Accuracy over comprehensiveness — five accurate
   documents beat fifty stale ones.

## Companion sources (do not duplicate, point into them)

- The catalog itself: `reports/aidocs-vs-code-audit-2026-05-16.md` (Part 3 =
  the 27-spec roadmap; Part 4 = dependency graph; Part 5 = doc hygiene).
- Live project state: `ai-docs/state.yaml` (v2.14.0+), `ai-docs/decisions/`
  (ADR index), `ai-docs/tuning-standard.yaml` (20-Year Entropy Standard).
- Theory library (the economics the game must express): `grundrisse.pdf`,
  `Capital-Volume-{I,II,III}.pdf` in repo root; `/home/user/Downloads/babylon_books/`
  (Cope's *Divided World Divided Class*, Amin, Federici, econophysics);
  `/media/user/data/mim/` (MIM Theory, Cope, Amin).
