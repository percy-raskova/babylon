# 01 — Visions and Brainstorms (familiarization sweep, part 1 of 3)

Scope read: `ai/brainstorms/**`, the epoch overviews and completion records,
`ai/epochs/epoch3/gramscian-wire-vision.yaml`, `ai/epochs/epoch4/vision.yaml`,
`ai/game-loop-architecture.yaml`, plus the epoch-3 slice specs that carry the
game vision (doctrine, tutorial, fog, attention, balkanization, vanguard
economy, strategy, music, RAG). `docs/gameplay/2026-10-25-porch-01.md` and
`docs/superpowers/specs/2026-07-17-viable-game-design.md` are cited as the
**current** authorities (owned by the sibling sweeps); everything in `ai/` is
upstream of them. No `ai/gramscian-wire-vision.yaml` exists at the path in the
brief — the file is `ai/epochs/epoch3/gramscian-wire-vision.yaml`.

## (a) The coherent vision

Babylon is a single-player political-economy strategy game about **running a
revolutionary organization in the contemporary United States**, at county and
hex resolution, on real federal data. The player is not a state and not a
class; they are the **Cadre Council** — the organization that acts while
classes are reservoirs to be organized, extracted from, or lost (percynotes2
makes this explicit: "Organizations ARE the agents"). The fantasy is
vicarious: run the experiments that would be irresponsible in life — the
commune, the electoral road, the Blanquist cell — inside a machine that feels
real without claiming to predict anything (porch:13-16).

The loop is period-based. The player allocates cadre labor, sympathizer labor,
and reputation across verbs (agitate, organize, educate, investigate, strike,
contest elections, later kinetic action); a deterministic material engine
adjudicates; the answer returns **as story first, numbers second**. Three
fronts each deserve their own room: the organizer's map (solidarity edges drawn
as literal lines over fog), the imperial-rent circuit (Φ, Wc vs Vc, the
scissors — the "scoreboard"), and the doctrine line (the organization's soul).
A fourth surface — the wiki/chronicle — is the permanent record.

What makes it a game rather than a simulator is **epistemics as progression**.
Two-layer fog: material facts (production, wages, rent, demographics) are public
record; political facts (consciousness, agitation, heat, faction stances) exist
only inside organizing reach, and unknowns render as honest unknown, never as
zero. Intel is a ledger of purchased, aging snapshots, not a vision cone. On top
of that sits the **Veil of Money**: the player sees only prices until theory
lets them see value — commodity fetishism as a UI gate, which doubles as
onboarding, because locked instruments are visible-but-veiled with a study path
rather than hidden.

Narrative is the other half of the epistemics. One immutable journal, three
tellings: a Corporate Feed that naturalizes (passive voice, euphemism), a
Liberated Signal that agitates (samizdat, active voice, names the owners), and
an Intel Stream that is raw engine data with no adjectives and no LLM. Hegemony
decides which telling reads as mainstream. "The player reads all three feeds and
writes one." A chronicle/wiki accumulates the record and the epilogues; an LLM
may re-prose a canonical frame but may never add a claim, and templates render
when no model is present.

Failure modes are the content, not the penalty screen. The liberal trap
(electoralism absorbs energy), the ultra-left trap (military victory, political
defeat), the rightist trap (raising the labor aristocracy out of revolutionary
need), the PatSoc pipeline (anti-imperial rhetoric degenerating into national
socialism), the False Summit (a red flag over continued extraction), the warlord
trajectory (prison-plantation as an emergent mode of production), and the
carceral equilibrium (no revolution in the core while Wc > Vc) are all authored
as live attractors. Doctrine is a map of ideological struggle with mutually
exclusive trunks, traps, and degeneration — not a tech tree, and with no optimal
path. The state is likewise a finite-attention machine: it sees everything and
understands nothing, so the player can saturate its threads and act in the blind
spots.

Endings are plural and honest: revolutionary victory, fascist consolidation,
ecological collapse, balkanization into successor states, and — only through
decolonization (ABOLISH, not UPHOLD or IGNORE) — a sustainable future. The bias
lives in the starting conditions, never in the endings.

The intended feel: eerie, weighty, contemplative — Disco Elysium's narrative
company over Victoria 3's systemic weight, presented as an intelligence briefing
rather than a dashboard, with "slow thinking, sharp choosing" and a decision
ceremony (seal → reckoning → long tail) instead of a spreadsheet dialog. The
designer's success line: *"Babylon taught me Capital, but it was fun."*

## (b) Best individual ideas

| Idea | Source | Why it matters |
|---|---|---|
| Three-channel narrator (Corporate / Liberated / Intel) generated from one immutable journal; hegemony decides which reads as mainstream | `ai/epochs/epoch3/gramscian-wire-vision.yaml:150-330`, restated `docs/gameplay/2026-10-25-porch-01.md:115-134` | The single strongest identity hook: mechanics, voice, and ideology in one object; falsification-proof because all three cite the same record |
| "The player reads all three feeds and writes one" | `docs/gameplay/2026-10-25-porch-01.md:134` | Names the player's authorial role — history-writing as the win condition of the interface |
| The Veil of Money — prices visible, value only through doctrine tiers | `docs/superpowers/specs/2026-07-17-viable-game-design.md:205-231` | Turns fetishism into a progression system and solves "full chrome at tick one" diegetically |
| Two-layer fog: material public, political only within organizing reach; intel as an aging ledger | same:166-183 | Makes knowledge the real resource and keeps determinism (fog is a serialization boundary, not a mechanic) |
| Doctrine tree as a map of ideological struggle: mutually exclusive trunks, traps, degeneration, no optimal path | `ai/epochs/epoch3/doctrine-tree.yaml:32-54`, trunks at `:314-554` | Refuses the tech-tree default; makes ideology a cost, not a bonus |
| The PatSoc Pipeline — "How to Accidentally Become a Fascist" as a worked degeneration path | `ai/epochs/epoch3/doctrine-tree.yaml:951-1050` | Best single piece of authored content in the corpus; teaches the trap by making each step reasonable |
| Party Congress: 500-1000 TL ceremonies — trunk shift, rectification, self-criticism as a trap escape | `ai/epochs/epoch3/doctrine-tree.yaml:899-950` | Gives ideology an internal politics and a dramatic, costly reset verb |
| State Attention economy: finite threads, repression costs money, "DDoS the state", act in blind spots | `ai/epochs/epoch3/state-attention-economy.yaml:1-16`, taught at `ai/epochs/epoch3/tutorial-design.yaml:279-283` | Inverts the usual omniscient-AI; produces a genuinely novel strategy layer |
| Fish-in-water intelligence: knowledge is relationship, not presence (Mass Receptivity; hostile masses deceive you) | `ai/epochs/epoch3/fog-of-war.yaml:1-20` | Corrects the scout-unit model and gives Mao's metaphor mechanical teeth |
| Balkanization three paths + the False Summit (RED_OGV keeps the pipelines running and still collapses) | `ai/epochs/epoch3/balkanization-spec.yaml:58-90` | A winning-but-losing ending — the most interesting ending shape proposed anywhere |
| Settler-colonial stance (UPHOLD / IGNORE / ABOLISH) as the fundamental political axis | `ai/epochs/epoch3/balkanization-spec.yaml:13-30, 87-90` | Gives the game a thesis that is not reducible to class alone, and a hard constraint on "true victory" |
| Terminal crisis cascade (SUPERWAGE → CLASS_DECOMPOSITION → CONTROL_RATIO → TERMINAL_DECISION) and three endgames | `ai/epochs/epoch1-complete.md:54-55` | A 100-year dramatic arc already computed by the engine; the drama existed before the presentation did |
| Interceptors that block an action *with a narrative reason* (`InterceptResult.block(reason)`) | `ai/game-loop-architecture.yaml:320-350, 482-490` | Mechanism for "every interception legible": refusal becomes prose, not a greyed button |
| Decision ceremony: seal (music sting + receipt stub, unknowns marked unknown) → reckoning (story first, numbers second) → long tail (backdated knowledge discovered later) | `docs/gameplay/2026-10-25-porch-01.md:60-88` | Solves consequence-preview-vs-mystery better than either previews or nothing |
| Backdated knowledge (`observed_period` vs `acquired_period`) used dramatically | `docs/gameplay/2026-10-25-porch-01.md:84-88` | Cheap, deterministic way to make betrayal and discovery arrive late |
| Bunker Constructivism: palette-as-data, no decorative glow, no chartjunk, CRIMSON always means extraction | `ai/brainstorms/gui/babylon_ui_constitution.md:13-76, 223-236`; prior art `ai/epochs/epoch1/ui-wireframes.yaml:37-60` | A rigorous visual grammar that survives any engine rewrite; the prohibitions are the valuable part |
| Organization as a *view* over a subgraph with an OODA metabolism and an org→institution life cycle | `ai/brainstorms/network/percynotes2.md:1-40` | The cleanest answer to "who acts?" — classes are substrate, organizations are agents |
| Religious institutions as captured field sources (gravitational capture of ideological bias) | `ai/brainstorms/superstructure/religious_capture_hypothesis.md:1-45` | A superstructure mechanic with a material grounding (who funds you, you drift toward) |
| Procedural soundtrack driven by game state (MIDI track generation, mood per phase) | `ai/epochs/epoch3/music-system.yaml:1-8` | Unusual and cheap differentiation; the *intent* survives even though the implementation is superseded |

## (c) Contradictions between docs

1. **Preview vs mystery.** "Outcomes are never previewed... the game never
   explains *why* mechanistically" (`docs/gameplay/2026-10-25-porch-01.md:77,90`)
   vs "`preview_action` costs/warnings rendered in ActionComposer before submit"
   and the acceptance gate "preview visible before every submit"
   (`docs/superpowers/specs/2026-07-17-viable-game-design.md:140,152`), and
   "Feedforward: before committing an action, show what will happen"
   (`ai/brainstorms/gui/babylon_ui_constitution.md:147-149`).
2. **Narrator as garnish vs narrator as storyteller.** D5 "deterministic canon,
   LLM garnish" (`viable-game-design.md:67`) vs "the LLM as storyteller rather
   than garnish" (`porch-01.md:37`) — and porch contradicts itself eight lines
   later: "It describes and never modifies" (`porch-01.md:139`). The same doc
   wants a bigger and a smaller LLM.
3. **Visible math.** "Rebellion is in what the tool reveals" and "luminosity
   encodes magnitude / data-ink maximization"
   (`babylon_ui_constitution.md:7-9, 69-76, 81-84`; §4.3 at `:147`) vs "Failure
   mode: spreadsheet popups. Visible math. Gameable multipliers... If they can
   see the formula, they'll play the formula" (`porch-01.md:110-113`, rule at
   `:94-108`). This is the deepest split in the corpus: analytics instrument vs
   fiction-first game.
4. **How many screens.** Five (Topology / Electoral / Physical map / Ticker /
   Wiki — `porch-01.md:41-54`) vs three (Organizer's Map / Circuit / Line —
   `viable-game-design.md:64,158-163`) vs the shipped top-bar takeovers (WIRE /
   DIALECTIC / CHRONICLE / NETWORK / DOCTRINE — `viable-game-design.md:160`) vs
   epoch-gated progressive reveal (`ai/epochs/epoch3/tutorial-design.yaml:350-365`).
5. **God view.** "God Mode MVP Panels" as the GUI starting point
   (`ai/brainstorms/gui/gui-guiding-star.md:155-178`) vs "multi-page app, no
   god-dashboard" (`viable-game-design.md:64`). The guiding star is a *developer*
   harness that was later read as a product spec.
6. **Who the player is.** Cadre Council with fogged political state
   (`viable-game-design.md:63`) vs an unnamed "leftist of some stripe" running
   experiments (`porch-01.md:5-16`) vs a party *line* with trunks that can
   degenerate into fascism (`doctrine-tree.yaml:32-54`) vs pure observer with no
   agency (`ai/epochs/epoch1/gramscian-wire-mvp.yaml:14-38`).
7. **Campaign length.** "The 520-tick nationwide campaign IS the game"
   (`viable-game-design.md:65`) vs "full 5,200-tick campaigns COMPLETE", "the
   100-year horizon" (`ai/loop-goal.md:19-22`). A 10× drift in the session shape
   with no doc reconciling it.
8. **Onboarding frame.** Tutorial as a 30-50 tick observation-only Epoch 1 with
   agency unlocked later (`tutorial-design.yaml:46-98, 350-365`) vs no-MVP,
   "onboarding lives inside the campaign's opening arc"
   (`viable-game-design.md:65,78`).
9. **Heat visibility vs fog.** "Heat must be visually apparent — the player
   should feel surveillance as a mechanic, not discover it through failure"
   (`babylon_ui_constitution.md:213-215`) vs heat as fogged political-layer data
   visible only within organizing reach (`viable-game-design.md:171-173`).
10. **Hegemony as a writable resource.** `gramscian-wire-vision.yaml:91-144`
    makes Hegemony a 0-1 resource with a fixed delta formula, and
    `:571-573` writes `consciousness_drift += effective_narrative *
    exposure` directly. That contradicts the compact in `AGENTS.md` ("an
    external-event rule can add only an allowed pressure, burden, or capacity
    effect... cannot write downstream results"; "a rule cannot impose a second
    fixed response curve") and the base-before-superstructure turn order in
    `ai/game-loop-architecture.yaml:546-565`. The three feeds are observer-layer
    prose; the resource is a mechanic that the current law would refuse.
11. **Engine shape.** "7 Systems, 704 tests" (`game-loop-architecture.yaml:15,158,799`)
    vs "13 Systems, 4,646 tests" (`ai/epochs/epoch1-complete.md:12-13,72-75`),
    and both describe a Python engine that `ai/loop-goal.md:14-16` says is
    retired. Status lines in these files are not trustworthy evidence.
12. **Two epoch schemes.** `ai/epochs/overview.md:11-16` numbers 1-4 (Engine,
    Foundation, Game, Platform), while the epoch-3 specs repeatedly call
    themselves "Epoch 2: The Game" (`gramscian-wire-vision.yaml:2`,
    `doctrine-tree.yaml:2`, `strategy-layer.yaml:2`) and
    `balkanization-spec.yaml:2` calls itself "Epoch 3: The Collapse". Every
    "Epoch N" sentence in `ai/epochs/**` needs re-reading against its own file
    header before it is cited.

## (d) Clearly stale or superseded

- **`ai/epochs/overview.md` (whole file).** Self-declares historical at
  `:3-7`; statuses frozen ~Jan 2026; its "living roadmap" pointer
  (`reports/aidocs-vs-code-audit-2026-05-16.md`, `ai/state.yaml`) is itself
  historical per `AGENTS.md`. Use `ai/loop-goal.md` +
  `docs/superpowers/specs/2026-07-29-game-design-standard-design.md` instead.
- **`ai/epochs/epoch4/vision.yaml`.** DuckDB + DuckPGQ, ChromaDB corpus, a
  `NarrativeDirector`/`BondiAlgorithm` that *generates* narrative, REST
  endpoints — every pillar has since moved: embedded SQLite (ADR287) not
  Postgres/DuckDB, deterministic frames not generated prose (D5), and the
  platform/API ambition is gone. Keep only as evidence that "dramatic arc
  generation" was once a design goal.
- **`gramscian-wire-vision.yaml` mechanics (not its concept).** References
  `src/babylon/models/world_state.py`, `src/babylon/config/defines.py`,
  `src/babylon/ai/director.py`, `src/babylon/rag/rag_pipeline.py` (`:588-625`);
  Python no longer owns simulation. Its "do not implement in Epoch 1, implement
  in Epoch 2" warning (`:27-37`) addresses an epoch scheme that no longer
  exists. Its `supersedes: brainstorm/narrative/gramscian-wire.md` (`:19`)
  points at a file that is not in the repo (`ai/brainstorms/narrative/` does not
  exist). The three channels, the euphemism tables, and the aesthetic contrast
  are live; the hegemony resource and the consciousness write are not.
- **`ai/epochs/epoch1/gramscian-wire-mvp.yaml`.** Dual-LLM-prompt MVP for a
  removed Python `NarrativeDirector`; superseded by deterministic
  `CausalChainObserver` frames + template fallback (D5), and its
  "APPROVED_MVP" status predates the no-MVP rule.
- **`ai/epochs/epoch1/ui-wireframes.yaml`.** Self-marked `DEPRECATED`
  (DearPyGui removed in Spec 010, 2026-02-01). Only "Bunker Constructivism" and
  its palette are worth keeping.
- **All epoch-3 slice specs as *implementation* documents.** Every one targets
  Python systems/paths (`src/babylon/...`); the Rust kernel/BSL/tick/client path
  owns material effects now. The mechanics are unbuilt vision, not current
  architecture — read them as design intent and re-derive the interface.
- **`ai/epochs/epoch3/tutorial-design.yaml` epoch gating.** The 1.0
  observation-only → 2a agency ladder conflicts with the no-MVP rule and the
  520/5,200-tick campaign; keep the failure-message craft (`:319-341`) and
  tooltip tiers (`:296-317`), drop the staging.
- **`ai/epochs/epoch3/music-system.yaml` (midiutil/mido procedural MIDI).**
  Superseded by the wired Wave-3 audio estate (39 SFX + 13 tracks,
  `ai/loop-goal.md:32`). Keep the state→mood mapping idea only.
- **`ai/game-loop-architecture.yaml`.** "status: implemented" refers to the
  retired Python engine. Live residue: the dialectic turn order (`:546-565`),
  the feedback-loop catalogue (`:591-627`), and the interceptor pattern
  (`:263-527`). Everything with a `src/babylon` path or a system count is
  historical.
- **`ai/brainstorms/tensor/**` and `ai/brainstorms/data/**`.** Theory and data
  hydrator design, not game vision (belongs to the architecture/theory sweep).
- **`ai/epochs/epoch3/warlord-trajectory.yaml`.** Explicitly `status: DEFERRED`
  (`:6`); a strong ending idea with no home yet.
