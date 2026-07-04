# 00 — Mission, Authority, Working Agreements

As of 2026-07-02. Owner: Persephone Raskova (BD, @percy-raskova).

## The goal

> `reports/aidocs-vs-code-audit-2026-05-16.md` is implemented and the game
> works locally.

Two legs, both required:

1. **The catalog**: the audit's Part-3 roadmap — 27 specs across 7 waves
   (est. 1,883–2,591 h), critical path `spec-070 → 071 → 075 → 081`
   (Balkanization → Reactionary Subject → Kinetic Warfare → Warlord).
1. **Local play**: the Django+React web app playable end-to-end against the
   real engine (not stubs), on Percy's machine.

**Completeness check (2026-07-03)**: Percy's full claude.ai chat corpus was
mined and reconciled against this kit — `07-chat-corpus-alignment.md` is the
master record. It adds endorsed-but-uncatalogued mechanics (commodity-flow
routing, prose→stance verbs, chronicle/Journal, resource substrate, modding,
deployment track, international layer), the experience layer (Wire, wiki
tooltips, narrator voice, visual identity, audio, accessibility), five OWNER
DECISIONS — **all five ruled by Percy 2026-07-03** (palette=AI discretion,
delivery=web app, narrator=Workers-AI/LoRA, victory-UX=chronicle+Journal,
scale=single Postgres; rulings verbatim in `07` §1) — and chat-sourced
requirements folded into the dialectics contract (`06` §9). "The game works locally" remains the near goal; 07
defines what "a complete game" adds beyond it.

**Full-game directive (2026-07-03, evening)**: Percy: "the desired end
state is a full game, with all of the features — and that's what we're
trying to build." The COMPLETE GAME (catalog Waves 2–7 + 07's M1–M12
mechanics + X1–X9 experience layer) is the destination; "works locally"
is a milestone on the way. The ratified execution program for the four
new tracks — React/Django UI build-out per the design canon, the
Observatory debug dashboard, the trade-bloc international layer, and
nationwide scope — is **`09-program-full-game.md`** (four parallel
agent lanes; owner decisions P1–P4 recorded there).

## Roadmap authority (ratified 2026-07-02)

- The **living roadmap** = the audit report + `ai-docs/state.yaml`.
- `ai-docs/epochs/` is **historical vision**, not authority (banners added).
- **Spec numbers are first-come**; the audit's numbers are advisory. 086 and
  097 were consumed by the QCEW data-quality track — when starting a catalog
  spec, take the next free number in `specs/` and note the audit's advisory
  number in the spec header.

## Ratified sequencing

1. ~~spec-086 QCEW loader + imputation~~ **DONE 2026-07-02** (data correctness
   underpins v/exploitation/imperial-rent everywhere).
1. ~~Lawverian dialectics refactor~~ **DONE 2026-07-03** (ADR051, Amendment K;
   master record `06-lawverian-dialectics.md`) and ~~graph-substrate
   migration~~ **DONE 2026-07-03** (ADR052, Amendment L,
   `08-graph-substrate.md`) — the two foundations 071 consumes.
1. **spec-071 Reactionary Subject** — next catalog spec (see `03-next-spec-071.md`).
1. **Program 09 (ratified 2026-07-03)**: four parallel lanes kick off
   alongside 071 — `[E: 071] [W: 090→091] [D: 100 ∥ 098-LODES] [O: 096]`
   — see `09-program-full-game.md` §3. 071 remains the engine lane's
   next unit; the web/data/observatory lanes touch disjoint files.
1. **spec-098 reference-DB build pipeline** — interleaved with catalog work
   (see `04-data-program-098.md`); its LODES OD slice is prioritized
   first (Lane D of program 09).
1. Waves 2 → 5 per the audit (see `05-catalog-execution.md`).

## Working agreements (Percy's standing rules — non-negotiable)

- **No MVP scoping.** The full Epoch-3 feature surface IS the minimum viable
  plan. Never propose MVP/Phase-1 splits of features that already have a full
  spec. (Memory: `feedback_full_vision_no_mvps`.) *Clarified 2026-07-03
  (`09` §1 R-MVP): the rule bars splitting SPECCED features;
  owner-directed scoping of an unspecced horizon item (e.g. M9 trade
  blocs) is the act of writing its first spec, not an MVP split — and
  those specs never self-describe as "phase 1".*
- **TDD mandatory**: Red → Green → Refactor. Intentionally-failing tests get
  `@pytest.mark.red_phase`. Write the failing test FIRST and run it to observe
  RED before implementing.
- **Commit after each unit of work**, conventional-commit format
  (`type(scope): description`). Commit messages end with the line:
  `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` (adjust the model
  name to yourself).
- **Pre-commit hooks** frequently reformat staged files and ABORT the commit:
  after every `git commit`, check `git log --oneline -1`; if the commit didn't
  land, `git add` the reformatted files and commit again. Large canonical
  artifacts (sim-run bundles) are committed `--no-verify` per precedent
  (635d234e).
- **Branching**: contributors branch from `dev`, PR to `dev`. Only the BD
  merges `dev → main`. Never commit directly to `main` or `dev`.
- **Never use `git -C <path>`** — `cd` to the repo root instead.
- **Ripgrep (`rg`) over grep.** `pipx` for non-project Python tools;
  `poetry run` / `mise run` for project tasks.
- **Speckit lifecycle for specs**: `specify → plan → tasks → implement`, with
  Constitution gates (v2.7.0 — Amendments K dialectics + L rustworkx
  substrate; II.12 authoring-API and the III.7 determinism-hash contract now
  bind engine work too. Original list: III.1 no-magic-numbers, III.7 frozen models,
  III.8 data-grounding, II.11, I.20, IV) checked in plan.md.
- **Docs**: demand-driven, verifiable claims only, never document unbuilt
  features (a "Future Enhancements" doc is the only place for plans).
- **After significant work**: update `ai-docs/state.yaml`, add ADRs to
  `ai-docs/decisions/` (+ index), and update THIS kit's `01-state-of-the-world.md`.
- **Owner review items** go to Percy; do not merge to dev/main yourself.

## Theory grounding (why the economics look the way they do)

The game models MLM-TW (Third-Worldist) political economy. When an engine
behavior looks wrong, check the theory before "fixing" it:

- **Fundamental Theorem**: revolution in the core is impossible while
  W_c > V_c (core wages exceed value produced). The difference is imperial
  rent (Φ). Core county workers are **LABOR ARISTOCRACY** — super-waged,
  pacified — not periphery proletariat. (This mis-assignment caused the
  tick-1 revolt bug; see `02-engine-truths.md` §3.)
- **Survival calculus**: P(S|A) = sigmoid(wealth − subsistence);
  P(S|R) = organization/repression. Rupture when P(S|R) > P(S|A).
- **Agitation is crisis-gated**: `compute_agitation_delta` generates agitation
  ONLY from rising exploitation, FALLING Φ, or rising care-work visibility.
  Flat consciousness during a growing-bribe phase is CORRECT (hegemony), not
  a missing wire.
- Canonical texts for intent questions: Cope *Divided World Divided Class*,
  Amin *The Law of Worldwide Value*, MIM Theory (locations in `README.md`).
