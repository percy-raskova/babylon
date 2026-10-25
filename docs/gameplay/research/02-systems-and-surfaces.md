# 02 — Systems and Surfaces (player-facing inventory)

Research briefing, read-only sweep, 2026-10-25. Question: **what does the player see and
touch?** Not engine internals. Sibling briefings own `ai/brainstorms/**` + vision docs
(01) and `project/**` + `reports/**` (03); overlaps below are cited, not re-derived.

**Files read in full or in the named sections:** `ai/game-loop-architecture.yaml`,
`ai/observer-layer.yaml`, `ai/epochs/epoch1/{synopticon-spec,gramscian-wire-mvp,agency-layer,imperial-circuit,territorial-schema,ui-wireframes}.yaml`,
`ai/epochs/epoch3/{fog-of-war,state-attention-economy,gramscian-wire-vision,overview}.yaml`,
all six `design/mockups/synopticon/*.jsx` + `synopticon.css`, `design/mockups/{manifest.json,PROVENANCE.md,README.md}`,
`specs/093-territory-org-detail/spec.md`, `specs/094-the-wire/spec.md`,
`specs/095-endgame-chronicle/spec.md`, `specs/096-observatory-foundation/{spec,data-model}.md`,
`docs/superpowers/specs/2026-07-27-wiki-content-architecture.md`,
`docs/superpowers/specs/2026-07-17-viable-game-design.md`,
plus `docs/gameplay/2026-10-25-porch-01.md` and `rust/crates/babylon-client/src/decision_surface.rs`
as the ground truth the older documents must be read against.

---

## 0. Ground truth first: what is actually on screen today

`rust/crates/babylon-client/src/decision_surface.rs` declares a closed manifest of
**five** surfaces — `TitleLockup` (admin), `CountyDossier` (gameplay),
`ObserverShell` (observer), `ObserverProduction` (observer), `OrganizerWorkspace`
(gameplay) — and refuses a gameplay surface that lacks any of: decision question,
visible signals, visible uncertainty, fog requirements, actions, expected receipts,
Archive subjects. Two facts fall out that the older design documents do not reflect:

- The **only live player verbs** are `inquiry`, `reinforce`, `hold`,
  `configure-standing-work` (organizer workspace). `investigate` is declared but
  **sealed with a player-visible reason** ("unavailable until Gate 5") on the dossier
  and both observer surfaces.
- Fog already ships in a minimal form: "uninvestigated place subjects render R6
  placeholder pages", "fog chips with zero label bytes", "missing knowledge is not
  zero", "Archive materialization lag: verified tick behind the durable tail".

Everything below from `ai/**`, `specs/**`, and `design/mockups/**` is **not** live
unless this section says it is. There is no `web/` tree; specs 093–096 were written
against a Django+React product that no longer exists in the repo.

---

## 1. Player-facing systems inventory

**A. Epistemic (what you are allowed to know)**

1. **Two-layer fog read-model** — material layer public (production, wages, rent,
   demographics, territory); political layer (consciousness, agitation, heat, stances)
   visible only within organizing reach. Unknown = honest unknown, never zero, never
   stale. `viable-game-design.md` §5a; porch-01 §147.
2. **Organizing reach as terra incognita** — solidarity edges drawn as literal lines;
   building/losing an edge is a visible territorial event (same §5a).
3. **Intel ledger** — session-scoped, event-sourced from INVESTIGATE resolutions,
   time-stamped, visibly aging; visibility is a pure function of (graph, ledger), so no
   engine or determinism cost (§5a).
4. **No fogged dead ends** — clicking an unknown yields a card naming the missing fact
   and the path to it, linking into the INVESTIGATE composer (§5a; matches the live
   "honestly-unavailable action slot" rule in `decision_surface.rs`).
5. **Veil of Money, T0/T1/T2** — conceptual axis orthogonal to the spatial one:
   T0 prices only → T1 wage-vs-value-produced → T2 the scissors. Locked instruments
   are *visible-but-veiled with a path* ("Study: Value Theory"), enforced at
   serialization so no client can peer through (§5d; porch-01 §163).
6. **Desert / Mud / Water vision tiers** — keyed to Mass Receptivity `M_r`
   (<0.2 / 0.2–0.8 / ≥0.8) with **Intel Confidence `I_c`** rendered as text grammar:
   solid → `~0.5` → `0.3?` → and, below `I_c` 0.2, **data that looks completely
   normal and is false** (the ambush trap). `ai/epochs/epoch3/fog-of-war.yaml`
   (`vision_states`, `ui_representation`).
7. **Decay by relationship** — intel goes stale at 0.2 / 0.05 / 0.01 per tick in
   Desert / Mud / Water; friendly territory is *cheaper to keep current*.
8. **Clarity degradation texture** — signal strength vs noise floor produce three
   renderings of the same view: sharp, `0.4█ ± 0.1█` ranges, and `████ █████`
   redaction. `ai/epochs/epoch1/synopticon-spec.yaml` (`degradation_model`).
9. **The Gloom / flashlight** — unobserved space lit by a focus point with falloff,
   ambient 0.05 (`synopticon-spec.yaml` `bunker_aesthetic_support.gloom_metrics`).

**B. The State apparatus (the adversary's machinery, and what leaks)**

10. **Attention Threads Θ** — the State's per-tick concurrency budget; Monitor 1,
    Investigate 2, Suppress 3, QRF strike *all remaining*. `state-attention-economy.yaml`.
11. **The blind tick** — a QRF strike consumes every thread; the rest of the map is
    unobserved for that tick. Named in-file as "THE PRIMARY EXPLOIT".
12. **Saturation / DDoS** — cheap high-visibility noise forces the State to spend
    attention; the player acts in the resulting blind spots (`overload_strategy`).
13. **Police-state spiral** — every capacity upgrade buys Θ with permanent legitimacy
    and an agitation floor; the player's win condition is to bait the upgrade
    (`expansion_mechanics`, `police_state_spiral_example`).
14. **Lavender risk score** — `clamp(centrality 0.40 + neighbor-risk 0.20 + velocity
    0.30 + geo 0.20)`, thresholds 0.4 monitor / 0.7 suppress / 0.9 eliminate
    (`design/mockups/synopticon/synopticon-data.jsx` `THRESHOLDS`, `DOCTRINE.lavender`).
15. **The Gospel queue** — strike priority by risk, then opportunity, then lower
    collateral; CDE policy ceiling filters; thread budget allocates; decoy probability
    is "informational only — not blocking" (`synopticon-data.jsx` `DOCTRINE.gospel`).
16. **Decoys and blowback** — engaging a decoy produces blowback that the State's own
    assess step attributes to the strike, i.e. **repression reads as efficacy**
    (`synopticon-gospel.jsx`, `DOCTRINE.gospel.notes`).
17. **Ghost nodes** — the map draws "what the State thinks exists": dashed,
    signal-loss inferences with `r: null` (`synopticon-data.jsx` `NETWORK.nodes` g01/g02).
18. **Legibility itself as the wound** — 78% coverage, names stripped to aliases
    (`ROSARY-7`), 18.47M observed vs 1,284 legible nodes (`META`).

**C. Political economy (what the meters mean)**

19. **Imperial rent flow (Φ)** — tribute from periphery to core; Φ = Wc − Vc gap; the
    Fundamental Theorem meter is the centerpiece of the circuit screen
    (`viable-game-design.md` §5b; `ai/epochs/epoch1/imperial-circuit.yaml`
    `game_dynamics.the_core_tension`).
20. **Falling rate of bribery** — super-wages shrink as periphery resistance rises; the
    four bourgeois responses (maintain / extract harder / austerity / fascism) are the
    game's strategic menu (`imperial-circuit.yaml`).
21. **Market scissors / MELT drift / corrections** — T2-only instruments, unlocked by
    theory (`§5d`; spec names `specs/115-market-scissors`).
22. **Metabolic rift / biocapacity gradient** — habitability as a map lens
    (`specs/093-territory-org-detail/spec.md` US3; `ai/epochs/epoch1/metabolic-slice.yaml`).
23. **Bifurcation** — agitation routes to class consciousness *or* national identity;
    the doctrine tree (Unit 6) is supposed to move this number (`§5c`).
24. **Survival calculus** — `P(S|A)` acquiescence vs `P(S|R)` revolution as the
    player-legible stakes of material collapse (`game-loop-architecture.yaml` systems 4).
25. **Heat / eviction / spillover** — territorial attention cost with adjacency
    spillover; the operative's exposure clock (`game-loop-architecture.yaml` system 7,
    `epochs/epoch1/agency-layer.yaml`).

**D. Agency and conflict**

26. **The George Floyd dynamic** — state violence (spark) × accumulated agitation
    (fuel) ⇒ uprising; the player can neither summon nor suppress it reliably
    (`agency-layer.yaml`).
27. **Mass-line actions** — `agitate_locally`, `social_investigation`,
    `establish_contact_network`; political work *precedes* intelligence
    (`fog-of-war.yaml` `actions`).
28. **Protracted war phases** — Defensive ↔ Equilibrium ↔ Offensive, bidirectional,
    condition-driven, never time-driven (`ai/epochs/epoch1/territorial-schema.yaml`
    `game_timeline`).
29. **Balkanization / CLAIMS / ColonialStance** — Blood upholds, Blue ignores, Phosphor
    abolishes; five map lenses plus a Collapse-Moment mode (`specs/093` US3).
30. **Endgame as recognized pattern, not verdict** — `REVOLUTIONARY_VICTORY`,
    `ECOLOGICAL_COLLAPSE`, `FASCIST_CONSOLIDATION`, `RED_OGV`,
    `FRAGMENTED_COLLAPSE`, with `UNRESOLVED` as the fixed-horizon terminal
    (`specs/095-endgame-chronicle/contracts/endgame.yaml`: six outcomes, spec-116).

**E. Narrative and record**

31. **Three authored feeds from one immutable journal** — Corporate (euphemism),
    Liberated Signal (samizdat, the book the player writes), Intel Stream (raw, no
    adjectives). Hegemony `H` decides which reads as mainstream; high H = Signal is
    "disinformation", H<0.3 = the official story collapses and the State substitutes
    coercion. `gramscian-wire-vision.yaml`; porch-01 §115.
32. **Euphemism sync-highlight** — hovering a flagged term in one column highlights its
    equivalent and shows a translation chip; five Herman/Chomsky filters + a consent
    score on a Patterns tab (`specs/094-the-wire/spec.md`, US1/US3).
33. **Dossier as the atomic knowledge object** — entity id + alias + status, risk
    anatomy, pattern-of-life radar, POL log, collateral estimate, decoy probability,
    neighbours, recommendation (`synopticon-dossiers.jsx`; live analogue:
    `CountyDossier` with signal atoms + provenance + place chips).
34. **Doctrine as a leaked SOP** — the algorithm printed as a state document, each
    formula beside a human-cost footnote ("penalizes informal-economy survival,
    mutual aid and remittance networks identically to illicit finance")
    (`synopticon-doctrine.jsx`).
35. **Chronicle** — the permanent, AI-narrated record, outside the tick hash; per-outcome
    epilogues (§6; `specs/095`; `wiki-content-architecture.md` §2.3).
36. **Wiki / glossary** — three namespaces: hand-written AI-forbidden Glossary,
    engine-templated State pages, AI-narrated Chronicle; infobox = `{statblock}`,
    what-links-here, no lead paragraph yet (`wiki-content-architecture.md` §2–4).
37. **Decision ceremony** — deliberation in the five screens, then a split-pane event
    popup where the click is the gavel and options are summarised by *meaning*, never
    by yield (porch-01 §60).

**F. Time**

38. **Periods, not ticks** — the world answers on its own schedule; receipt stub at the
    seal, story-first reckoning at period close, consequences in the long tail with
    `observed_period` vs `acquired_period` (porch-01 §70).
39. **100 in-game years** — 5,200 ticks at 52 weeks/year; endgame patterns may appear
    along the way but only the horizon terminates (spec-116 owner ruling).
40. **The five screens** (newest ruling): Topology · Electoral · Physical map · Ticker ·
    Wiki, information assembled *toward* the player, no dashboard to troll
    (porch-01 §41).

---

## 2. Best surfaces worth keeping (idea → source → why)

| Idea | Source | Why it matters |
|---|---|---|
| **Honestly-unavailable action slot with the reason in the button** | `rust/crates/babylon-client/src/decision_surface.rs` (`ActionAvailability::Unavailable`) | Turns "not built yet" into diegetic information; already shipped and contract-tested against the rendered card, so the surface cannot lie about its own state. |
| **Confidence grammar instead of numbers** — solid / `~0.5` / `0.3?` / normal-looking-but-false | `ai/epochs/epoch3/fog-of-war.yaml` `ui_representation.confidence_indicators` | Teaches the fog *pattern* rather than annotating each datum; the "masked looks normal" tier is the only design here that makes political work feel necessary instead of optional. |
| **Uncertainty per field, declared in the surface contract** | `decision_surface.rs` (`visible_uncertainty`) | Forces every screen to state what it cannot know at build time — a compile-time fog budget, not a UI afterthought. |
| **Risk-anatomy stacked bar with threshold ticks drawn behind it** | `design/mockups/synopticon/synopticon-dossiers.jsx` (total bar + MON 0.40 / SUP 0.70 / KILL 0.90 marks) | One bar explains an opaque score, its parts, and the decision boundaries without a table; ideal for the *dossier on yourself* as the State sees it. |
| **Doctrine-as-leaked-SOP with human-cost footnotes** | `synopticon-doctrine.jsx`, `synopticon-data.jsx` `DOCTRINE.lavender.features[].note` | Best available answer to "show the machine without turning it into a spreadsheet": the formula is an artifact of the enemy, and the footnote is the argument. |
| **Ghost nodes for signal loss** | `synopticon-data.jsx` (dashed `GHOST`, `r: null`) | Renders absence as a *shape* rather than a blank, which is exactly the "unknown ≠ zero" rule the live dossier already promises. |
| **Engage → decoy → blowback that the system misattributes** | `synopticon-gospel.jsx` (resolve modal; `DOCTRINE.gospel.notes`) | Makes the adversary's own metrics unreliable, so the player must read politics rather than the scoreboard — the mechanism that keeps a state dashboard from becoming a strategy solver. |
| **CDE policy slider as the moral dial** | `synopticon-gospel.jsx` controls | A single number with immediate queue consequences (collateral ceiling) is the cleanest "cost of repression" control in the corpus. |
| **Θ budget strip with threads available / total** | `synopticon-panopticon.jsx` `StatBox "THREADS AVAIL."`, `state-attention-economy.yaml` | Gives the player a visible enemy resource to exhaust; the blind-tick exploit only works if the budget is legible *at the moment of baiting*. |
| **Clarity-graded redaction texture** (`████`, `±`, static) | `ai/epochs/epoch1/synopticon-spec.yaml` `degradation_model` | Cheap, diegetic way to render three knowledge states of one view without new data — pairs with the cold-collapse palette already in `design/mockups/synopticon/synopticon.css`. |
| **Euphemism sync-highlight across feeds** | `specs/094-the-wire/spec.md` US1 | The thesis is demonstrated by *interaction* ("same event, two stories") rather than by copy; also the only surface that makes the three-author model usable side-by-side. |
| **Intel ledger with visible aging** | `viable-game-design.md` §5a | Converts knowledge into an object with a timestamp, so investment in relationships has a running cost and memory becomes a resource. |
| **Fogged-place placeholder page (R6) rather than an empty panel** | `decision_surface.rs` (`uninvestigated place subjects render R6 placeholder pages`) | Already-implemented precedent for "no fogged dead ends"; every new surface should copy it. |
| **Split-pane decision ceremony with meaning-not-yield summaries** | `docs/gameplay/2026-10-25-porch-01.md` §60 | The single best guard against the spreadsheet failure mode: outcomes are never previewed, only stakes and engaged mechanisms are named. |
| **Three-tempo answer: seal → reckoning → long tail** | porch-01 §70 | Supplies the pacing skeleton the surfaces must serve (receipt now, story at period close, discovery periods later); no mockup implements it yet. |
| **Leaked-document surfaces as the only place formulas appear** | `synopticon-doctrine.jsx` + porch-01 §94 (visibility rule) | Reconciles the corpus's biggest conflict: show the algorithm as an in-world artifact, never as the player's own readout. |

---

## 3. Contradictions (live, and unresolved)

1. **Legibility: "show why" vs "never explain why."** `viable-game-design.md` §6 makes
   `CausalChainObserver` frames canonical ("Wages fell below subsistence in 3 counties →
   agitation rising"), §5d unlocks instrument tiers, and `specs/093` requires a
   BreakdownTooltip on *every* displayed number. porch-01 §94 (newest, canonical) says
   the game "never explains *why* mechanistically" and calls visible math a failure
   mode. `Synopticon` splits the difference by making the math an enemy artifact.
   → Resolution direction: causal *narration* survives as story ("what happened, who did
   what, what it cost"), breakdown popovers do not survive as player-facing UI; keep the
   provenance machinery for god-mode/Wiki.
2. **Fog: honest unknown vs deliberate falsification.** `viable-game-design.md` §5a and
   porch-01 §147: "unknowns render as honest unknown — never zero, never stale." But
   `fog-of-war.yaml` `desert.mechanics.masking` requires masked attributes to "show a
   plausible but FALSE value" and `ui_representation` calls it "the trap." Both are
   defensible (unknown = epistemic honesty; false = counter-insurgency), but a UI cannot
   promise both. → Decide per layer: political values falsifiable only where an
   informant exists, otherwise unknown.
3. **Two attention economies.** `state-attention-economy.yaml` gives the *State* Θ;
   `synopticon-spec.yaml` `the_gloom` makes *player attention* scarce and history
   contingent on where the camera is. Player-attention scarcity contradicts fog being a
   pure function of (graph, intel ledger) and makes the record viewpoint-dependent.
   → Keep Θ (adversary resource); drop the flashlight as a *truth* mechanic, keep it as
   a *lighting* effect.
4. **Three screen sets.** porch-01 (2026-10-25) rules **five screens**: Topology,
   Electoral, Physical map, Ticker, Wiki. `viable-game-design.md` (2026-07-17) rules
   **three**: Organizer's Map, Circuit, Line. `design/mockups/ui_kits/webapp` implements
   **13 screens**; the `Wire` is a 4-tab window and the `Synopticon` a 4-tab window.
   Nothing reconciles them, and "Electoral" has no mechanical substrate anywhere in
   `specs/`. → Treat five screens as the target and map the rest as panels *within*
   them.
5. **Endings.** porch-01: "no prescribed outcomes, the game shows, never prescribes."
   `specs/095` ships a terminal end-screen with per-outcome headlines that make four of
   five endings the same "THE BUNKER FAILS" text; `contracts/endgame.yaml` has already
   moved to six outcomes including `UNRESOLVED` (spec-116). End-screen-as-verdict is
   incompatible with pattern-recognition-at-horizon. → Chronicle becomes an epilogue to
   a *run that stopped*, not a verdict on the player.
6. **Campaign length.** 520 ticks (`viable-game-design.md` D3, "the 520-tick campaign
   IS the game") vs 5,200 ticks (spec-116 owner ruling, 100 years at 52 weeks/tick).
   The 520 figure is superseded but still shapes the pacing targets in `§4a`.
7. **Hegemony is load-bearing and unwritten.** `specs/094` gates channel visibility on
   `spec-077`'s hegemony mechanic; `specs/077` does not exist. Today all three feeds are
   always visible (`visibility` is a no-op pass-through), so the Wire's central claim
   ("neutrality is hegemony") has no mechanical consequence.
8. **Lobby of five vs one surface.** `decision_surface.rs` declares 5 surfaces, of which
   2 are gameplay; the design corpus describes ~25 distinct readouts. The live contract
   is deliberately stricter (it rejects a surface with no decision question), which is
   the right rule — but it means most corpus surfaces must be folded into panels rather
   than shipped as pages.

---

## 4. Stale or superseded (do not cite as current)

- **Specs 077 / 078 / 079 / 081 have no directory under `specs/`.** They exist only as
  catalog rows (`project/programs/05-catalog-execution.md`) and audit prose
  (`reports/aidocs-vs-code-audit-2026-05-16.md`): 077 Gramscian Hegemony, 078 Repression
  Logic Full, 079 Panopticon Economy (Θ), 081 Warlord Trajectory. Consequences:
  `specs/094`'s hegemony hook and `specs/095`'s "chronicle content enrichment is
  spec-081's deliverable" both point at nothing — and 081 is *warlord branching*, not
  chronicle. The Θ and fog systems survive only as `ai/epochs/epoch3/*.yaml`.
- **`ai/epochs/epoch1/ui-wireframes.yaml` is self-declared DEPRECATED** (DearPyGui,
  removed in spec-010). Same era: `ai/epochs/epoch1/dpg-patterns.yaml`. Historical only.
- **`ai/game-loop-architecture.yaml`** is accurate about *mechanics ordering* (7 systems,
  5 turn phases) but its "location: src/babylon/engine/…" paths and test counts are from
  the Python engine, which is gone — `src/babylon/engine/` no longer exists. Cite it for
  system *semantics* only.
- **`ai/epochs/epoch1/synopticon-spec.yaml`** targets `src/babylon/engine/synopticon.py`
  as "future implementation" — never built, and the host package is removed.
- **`docs/superpowers/specs/2026-07-27-wiki-content-architecture.md`** documents
  `src/babylon/projection/vault/**` (`concept_cards.py`, `narrator_cache.py`,
  `tick_baker.py`) — the whole vault tree is absent from the current checkout. Its
  *architecture* (Glossary / State / Chronicle namespaces, AI-forbidden tier,
  fact-grounding validator) is still the best available content model; its *file
  citations* are stale.
- **`ai/epochs/epoch1/gramscian-wire-mvp.yaml`** proposes two LLM calls per event and a
  two-channel toggle, with green/blue palettes. Superseded three ways: R-NARR makes the
  Wire narrator deterministic templates (`specs/094` FR-094-02), the channel count is
  three, and the palette is Cold Collapse (`PROVENANCE.md` notes the palette itself
  conflicts with Constitution Art. VII's GOLD clause pending an amendment).
- **`ai/epochs/overview.md`** is marked historical (2026-07-02) and its slice numbering
  disagrees with the files (`fog-of-war.yaml` says slice 3.10, overview says 3.4;
  attention economy is 3.9 in-file, 3.7 in overview).
- **`specs/096-observatory-foundation`** is a *developer* debug dashboard over Postgres,
  disabled in production, explicitly not player-facing. Its name now collides with the
  player `observer` campaign surfaces in `babylon-client`; do not let the two merge.
- **`design/mockups/PROVENANCE.md`** stands: these are ratified *reference* artifacts
  (`--no-verify`, do not hand-edit), and the palette conflict with Article VII is still
  open. Their layouts are canon; their data models (`risk_score`, `CDE`, `threads`) are
  invented and do not correspond to engine fields.
- **`ai/epochs/epoch1/synopticon-spec.yaml`** references `ai/design-system.yaml` as the
  colour source of truth; that file does not exist. Live tokens are
  `design/mockups/colors_and_type.css` / `synopticon.css`.

---

## 5. Lane boundaries

Visions, brainstorms and the Gramscian full vision's *political* argument (hegemony as
war of position, channel registers) belong to briefing 01 — I cite
`gramscian-wire-vision.yaml` only for its thresholds (H 0.7/0.3) and channel set.
Program sequencing, gate readiness and spec status belong to briefing 03; I cite
`spec-116`'s owner ruling only because it changes two numbers players see (horizon,
outcomes). `design/mockups/{wire,themap,community,ui_kits}` were outside this sweep —
the Wire and Synopticon surfaces are the only two I inventoried in code.
