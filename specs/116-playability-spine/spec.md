# Spec 116 — The Playability Spine (Program 24, sub-project 1)

**Status:** PLANNED 2026-07-17 (owner approved the parent design and authorized
implementation the same day) · **Branch:** `feature/116-playability-spine`
**Parent design:** `docs/superpowers/specs/2026-07-17-viable-game-design.md` (§4)
**ADR:** ADR079 (authored with this program's first commit batch)

## Thesis

Babylon's engine already computes drama that never reaches the player. Before any screen
track (fog, circuit, doctrine) can matter, the base loop must be playable under **any**
information model: a campaign that holds tension across hundreds of ticks, an event rail
that is signal rather than wallpaper, a first session that explains itself, and the nine
evidence-backed wirings that connect existing engine riches to existing UI surfaces.
This is connection-and-framing work — no new dynamical systems.

## Owner ruling 2026-07-17 (post-design, supersedes the design's "520-tick" framing)

> "The endgame: it's **100 years of in-game time**, not a specific condition. The game
> ends when it ends; the scenario it's in is up to player actions and the economy."

At 1 tick = 1 week (defines `tunables.weeks_per_year: 52`), the campaign horizon is
**5200 ticks**. The five outcomes (REVOLUTIONARY_VICTORY, ECOLOGICAL_COLLAPSE,
FASCIST_CONSOLIDATION, RED_OGV, FRAGMENTED_COLLAPSE) become **recognized patterns** the
world is in along the way — never terminators. This executes the 2026-07-14
emergent-endgames ruling (fixed horizon + recognized patterns) which the live app had
not yet implemented ("Endgame Reached — tick 18"). Termination = horizon only, or the
player's own fast-forward-to-epilogue once a pattern locks (FR-116-5).

## Scope (from the parent design, verbatim commitments)

- **FR-116-1 · Campaign pacing (declared baseline ceremony #1).** Deterministic pacing
  instrument first (headless nationwide run; tick-of-first-recognition per outcome
  pattern + per-axis progress curves), then a single defines-level recalibration until
  the null-play arc holds tension across the 100-year horizon. Convert EndgameDetector
  from adjudicator to pattern recognizer; the campaign horizon (100 years → 5200 ticks)
  lives in defines. Fix the tick-0 "Sovereign Collapse" threshold bug. One ceremony,
  instrument-first-tune-once, per-scenario drift declared (Market Scissors promotion
  pattern).
- **FR-116-2 · Event salience.** (i) Consecutive same-type/same-subject events collapse
  into one card with count and age. (ii) Severity tiers: crimson reserved for genuine
  rupture/endgame proximity; political churn drops to gold/muted. (iii) Autopause fires
  once per distinct critical event — first occurrence or escalation, never repeats.
  Extends the existing `event-tray-mutes` machinery.
- **FR-116-3 · Lobby & briefing.** Generated operation codenames, dates, tick/status,
  delete/archive in the lobby. Game creation lands on a Scenario Briefing: who you are
  (the Cadre Council), the stakes, the five terminal outcomes in plain language with the
  win condition named (`get_journal_objectives` derives these). Curated difficulty/config
  exposure via the existing `CreateGameSerializer` overrides (never raw defines).
- **FR-116-4 · Quick-win wiring set** (each evidence-backed, see §9 of the parent
  design): (1) CausalChainObserver → bridge → wire/journal; (2) five distinct endgame
  epilogues; (3) `preview_action` costs/warnings rendered before submit;
  (4) per-target expected deltas in TargetPicker; (5) serialize the dead `tick_*`
  attributes into CrisisTimeline / BifurcationGauge / Economy surfaces;
  (6) EconomyDashboard phantom chips fixed against real fields; (7) event whitelist
  widened past 44/79 with POGROM/LOCKOUT/VIGILANTISM first-class (own EventType,
  severity, title, geographic anchor); (8) verb dead-ends become disabled-with-reason;
  (9) the permanent "PROFIT no data" chip wired or removed.
- **FR-116-5 · Fast-forward-to-epilogue** (owner box-tick, taken YES): when an outcome
  pattern is locked in, the player may fast-forward to the horizon epilogue instead of
  clicking through doomed ticks.

## Acceptance gates (parent design §4, restated under the fixed-horizon ruling)

1. Null-play nationwide run recognizes no outcome pattern before a calibrated tick
   floor, and the game terminates only at the 100-year horizon (no tick-0 events, no
   early "Endgame Reached").
2. No two consecutive identical event cards.
3. Autopause ≤ 1 per distinct event.
4. Every recognized outcome renders a distinct epilogue at the horizon (or on
   player-accepted fast-forward).
5. Preview visible before every submit.
6. A fresh player reaches their first submitted action unaided (scripted e2e trunk test).

## Constraints

- Engine determinism untouched: every change either observes (serialization boundary)
  or is a defines-level recalibration executed as the one declared ceremony.
- `mise run check` green per unit of work; `qa:regression` byte-identical **except** the
  ceremony commit, which regenerates baselines with per-scenario drift declared.
- No MVP scoping — the numbered items above are dependency-ordered, not severable.
- Coefficients live in `GameDefines`/`defines.yaml`; copy lives in data, not conditionals.

## Implementation plan

`docs/superpowers/plans/2026-07-17-playability-spine.md` (authored from the 10-scout
recon workflow `wf_cde8ea09-ac8`; task-by-task TDD).
