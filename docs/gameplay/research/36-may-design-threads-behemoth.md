# 36 — May 2026: the month the aesthetic was enforced, not invented

Read-only memory and repository research, 2026-10-26. Window: **2026-05-01 to 2026-05-31**.
Question: what did the Director establish in May about how the game should feel — especially the
topology graph as a living or behemoth thing, and any UI-as-art direction — and where does the
May record contradict the current two-tier exposure doctrine (Tier 1 public statistics as numbers,
Tier 2 engine internals as sensory cues)?

A sibling miner covers July (the Living Map / spec-113 cluster). This briefing stops at the edge
of that window and treats anything later as downstream evidence only. Every claim carries an ID.
Evidence class: **O** = read directly in the record; **D** = my mapping or inference; **A** =
claimed absence, with the method that established it.

---

## 0. Thesis

1. **May contains no new Director aesthetic doctrine.** Every May prompt that touches the frontend
   or its look is an engineering instruction. The one May prompt that touches the frontend directly
   is "Yeah let's commit frontend at a third unit" (#P3572, 2026-05-05). May is the month the
   March/April architecture was *enforced*, not the month a mood was set. (**O** for the prompt
   inventory; **D** for the framing.)
2. **"Behemoth" is not a May word.** No observation, prompt, session or tracked document in the
   May window contains *behemoth*, *shoggoth*, *monstrous* or *leviathan* (**A** — SQL scan of all
   May observations and prompts for those stems; `git grep` for the same stems over
   `docs/`, `ai-docs/`, `specs/` at the 2026-05-20 tree `266dfe948`). The metaphor belongs to a
   later stratum. Do not attribute it to May.
3. **The only "living" claim live in May is about the terminal, not the graph.** The design system
   in force says the UI should feel "Alive (flickering, breathing, not static)"
   (`ai-docs/design-system.yaml:29` @ `266dfe948`). It says nothing about the graph being alive.
   The graph is governed by the opposite document: "Node position, size, and connection density
   *are* the data. Decoration is prohibited" (`ai-docs/brainstorms/gui/babylon_ui_constitution.md`
   §3.1 @ `266dfe948`).
4. **May already contains the Tier-2 grammar the October doctrine wants — and suppresses it.**
   `docs/concepts/aesthetics.rst` @ `266dfe948` binds sensory cues to engine internals:
   flicker "increases during high system load (contradiction accumulation)", static rises with
   repression, and "Environmental factors visualized through signal quality, not graphics"
   (lines 240–410). That is engine-internals-as-sensory-cue, written down and shipped in the May
   tree. It is the doctrine's inheritance, not its invention.
5. **The live contradiction is agent-written, not directorial.** The Constitution's Article VII —
   quoted as binding in the May 5 reset — forbids "mood over meaning" and "decorative glow"
   (`docs/agents/babylon-frontend-reset-prompt.md:95-101` @ `273de9be9`). The Director's own
   aesthetic says the opposite: "grim, atmospheric, hardware-focused vibe" (#P364). An October
   research sweep has already compressed Bunker Constructivism into "palette-as-data, no
   decorative glow, no chartjunk" (`docs/gameplay/research/01-visions-and-brainstorms.md:96`),
   keeping the prohibition and losing the atmosphere. (**O** for all three texts; **D** for the
   compression claim.)

---

## 1. Method and its limits

- Primary retrieval was claude-mem smart search, filtered to the May window, for: topology graph
  feel, Living Map, corporate dashboard, Installer aesthetic, pulsating/behemoth/monster/alien/
  shoggoth, dissonance, soundtrack, UI/UX feel, sensual, exposure, fog/vibe.
- Semantic (Chroma) search was offline for most of the session, so results fell back to keyword
  search. To avoid a false negative I queried the memory store directly, read-only
  (`file:...claude-mem.db?immutable=1`): all `observations` and `user_prompts` rows dated
  2026-05-01…2026-05-31 matching the aesthetic stems. That is the basis for every **A** claim.
- Repository evidence comes from the 2026-05-20 tree `266dfe948` and the two May frontend commits
  `273de9be9` (2026-05-05) and `283f2e901` (2026-05-15). Files are cited as `path@commit`.
- I did not read the March 7 / April 2 / April 6 / April 10 design conversations that the May
  documents repeatedly invoke (`docs/agents/babylon-frontend-reset-prompt.md:5` @ `273de9be9`).
  They are outside the window. Where the May texts report them, I label that as reported, not
  observed.

---

## 2. What actually happened in May

The month is lopsided. Two days carry all the design work; the rest is engine, data and
specification.

| Date | Event | Evidence |
| --- | --- | --- |
| 2026-05-05 | Frontend pivots from single-page "war room" to a 16-route app in one commit; 1,249 LOC deleted, 40+ files added, 30+ new components, 5 legacy components removed; 310 tests across 44 files green | `273de9be9`; #34839, #34843, #34842 |
| 2026-05-05/06 | Design kit `ui_kits/webapp_v2/` lands: 16 artboards, "Bunker Constructivism" tokens, mock pages, static topology sketch | `273de9be9`; #34841 |
| 2026-05-10 | PyQt6 dashboard deleted with its dependent tests — the desktop dashboard is retired, the web app becomes the only player surface | #36076; `4fa0dea5f` |
| 2026-05-11/12 | Spec-061 "real backend wire-up": six routed pages move from fixtures to live API; visual redesign declared a non-goal | #S2747, #S2761; `specs/061-real-backend-wireup/spec.md` @ `7ff987ff7` |
| 2026-05-15 | Course-correction prompt lands: lean `GameShell`, no graph panel in Briefing, `GraphView` moved to a future `/games/:id/topology` route | `283f2e901`; `docs/agents/babylon-frontend-paradox-course-correction.md:666,677` |
| 2026-05-16 | Audit finds the music estate substantially implemented (crisis / revolutionary / fascist suites as MIDI generators) but unconnected to the running game | #37440 |
| 2026-05-20 | Project state: Epoch 1 complete, "Slice 1.5 — The Dashboard" in progress; goal is wiring the 4-node Imperial Circuit and adding a metabolic gauge | #38007 |
| 2026-05-20 | README/onboarding rewritten to point at the React+Django UI; DearPyGui demoted to legacy | #38025 |

(**O** for every row; the table's ordering is **D**.)

Everything else in the window is invariants, Leontief rent, circulation, data ingest, caching, the
headless runner, or balkanization. A full-month scan of `session_summaries` for UI, design, visual,
dashboard or topology requests returns engineering sessions only (**A**, same SQL pass).

---

## 3. Thread A — the topology graph in May: demoted, then made static

This is the closest May comes to the question, and the answer runs against the behemoth reading.

**May 5 — the graph loses its throne.** The pivot commit describes what was dismantled: "the
collapsed god-page that fused map, topology graph, action composer, time series, resource bar,
event log, and org list into one viewport" (`273de9be9`). The replacement gives the graph no page
of its own. It survives as a panel inside the org inspector, labelled "Edge Topology", plus a
second, smaller "Topological View · BubbleSets Hull" on the community inspector
(`ui_kits/webapp_v2/pages-core.jsx:416,572` @ `273de9be9`).

**May 5 — the graph is drawn as an instrument.** The prototype's `TopologyGraph` is a static SVG:
straight lines at 0.55 opacity, 16px circles at 18% fill, monospace 7px labels, and a dashed
ellipse for the hyperedge hull. No animation, no pulse, no state-reactive motion
(`ui_kits/webapp_v2/shell.jsx:219-260` @ `273de9be9`). The comment above it cites the Constitution,
not a mood: "Article VIII.9: hyperedges are NOT pairwise" (same). The kit's own status table is
candid: "Topology graph ⚠️ Sketched — not interactive. BubbleSets/Sigma is the production target"
(`ui_kits/webapp_v2/README.md` @ `273de9be9`).

**May 15 — the graph is moved off the main screen.** The course correction makes it explicit:
`GameShell` becomes "Map + sparkline strip + tick narrative + End Turn. No verb composer, no
full-size charts, no graph panel", and step 4 says "Remove `<GraphView>` from the left panel. Move
to a future `/games/:id/topology` route"
(`docs/agents/babylon-frontend-paradox-course-correction.md:666,677` @ `283f2e901`).

**D:** For one month in the middle of 2026, the project's answer to "how should the topology feel?"
was "less of it, on its own page, later". That is the opposite of a behemoth directive. Whoever
later gave the graph a living body was reacting to a graph that May had deliberately made small,
static and peripheral.

---

## 4. Thread B — two canons in force at once

May's real aesthetic event is not a new directive. It is that two incompatible documents were both
binding, and both shipped.

### 4.1 The atmospheric canon (Director lineage)

`docs/concepts/aesthetics.rst` — "Bunker Constructivism: Damp Basement Cyberinsurgency" — is the
Director's December pivot written up (#P364, "grim, atmospheric, hardware-focused vibe"; #P291,
"Expensive GPUs cooling in a damp basement… The hum of fans"). It is untouched between 2026-02-27
and July, so it is live all May (**O**: `git log -- docs/concepts/aesthetics.rst`). Its claims:

> Colors are not paint on surfaces. They are **light emissions** in a dark room. The UI is not a
> webpage. It is a **CRT monitor in a concrete room**.
> The walls sweat. Humidity is visible in the vignette effect.
> The screen flickers. Not broken—struggling against interference.
> Monumental scale suggested by the unseen infrastructure.
> — `docs/concepts/aesthetics.rst:36-44,74` @ `266dfe948`

`ai-docs/design-system.yaml` (created 2025-12-14, unchanged through May) states the feel list
plainly: "The UI should feel: Heavy (metal chassis, not floating cards), Old (CRT grain, not
retina-sharp), **Alive (flickering, breathing, not static)**, Underground (hidden, illicit,
insurgent)" (`ai-docs/design-system.yaml:26-30` @ `266dfe948`).

The May 5 kit carries this vocabulary into code: token names in `colors_and_type.css` are
`--babylon-wet-concrete`, `--babylon-soot`, `--babylon-chassis`, `--babylon-phosphor-green`, under
the header "BASE COLOR TOKENS — 'Light emissions in a dark room'" (**O**:
`ui_kits/webapp_v2/colors_and_type.css` @ `273de9be9`).

One detail in this canon matters for the exposure question more than any other line. Colour is
assigned by **speaker**, not by data domain: "The System speaks in green. Data. Facts. Metrics."
(`#39FF14`), "The AI speaks in purple. Life. Growth. The Signal." (`#9D00FF`), and "Red is Pain,
not Decoration. Use ONLY for critical states." (`#D40000`) — `ai-docs/design-system.yaml:64-86`
@ `266dfe948`. **D:** That is a primitive form of the two tiers: one channel for what the engine
counts, one channel for what the narrator says about it, one channel for what hurts. It also sits
outside Article VII's rule that CRIMSON means extraction and GOLD means solidarity regardless of
who is speaking, so the two schemes would collide as soon as AI narration or metrics appear on a
graph view.

### 4.2 The instrumental canon (agent lineage)

`ai-docs/brainstorms/gui/babylon_ui_constitution.md` @ `266dfe948` — the source text of
Constitution Article VII — says the opposite thing about the same screens:

> The aesthetic lineage is Constructivist information design — form follows function, art as tool
> for the movement. **We are closer to Bloomberg Terminal than to cyberpunk mood board.**

> The rebellion is in what the tool reveals, not in how it looks.

> Color encodes meaning. Decorative use is prohibited. […] Ambient glow is prohibited unless
> intensity maps to a quantitative variable.

> **Mood over meaning** — aesthetic choices MUST be semantically grounded. *(listed as prohibited)*

The May 5 reset prompt quotes Article VII as constitutional and non-negotiable: "Color encodes
meaning (class, extraction, edge type, state), not mood. Luminosity encodes magnitude. No
decorative glow, no chartjunk"
(`docs/agents/babylon-frontend-reset-prompt.md:95-101` @ `273de9be9`).

**D:** "Art as tool" and "no mood" are agent positions, not the Director's. The Director asked for
"grim, atmospheric, hardware-focused vibe" and, separately, for the state's voice to be a cold
machine (#P345: "Degree centrality > 0.4 … Probability of survival: 12%"). Agents turned the
second instruction into a global prohibition on atmosphere. That substitution is visible in May
and it is the root of today's confusion about whether sensory cues are legitimate.

### 4.3 The canons disagree inside one commit

`273de9be9` contains both the Article VII quotation ("no decorative glow") and a token file whose
palette includes bloom, phosphor and "wet concrete". The palette itself has drifted into at least
four versions, none reconciled:

| Source (all live in May) | Crimson | Gold | Note |
| --- | --- | --- | --- |
| Article VII / UI constitution (`266dfe948`) | `#dc143c` | `#ffd700` | "Bloomberg, not cyberpunk" |
| `docs/concepts/aesthetics.rst` (`266dfe948`) | `#d40000` | `#ffd700` | "Phosphor Burn", bloom is prescribed |
| `ai-docs/design-system.yaml` (`266dfe948`) | `#d40000` | `#ffd700` | "Digital Grow Room"; adds data-green `#39ff14` and signal-purple `#9d00ff` |
| `colors_and_type.css` (`273de9be9`) | `#e04040` / `#dc143c` | `#c8a860` | prototype ships its own values |

(**O** for each row; **D** for calling it drift rather than intentional per-surface palettes — no
document in the May tree states a rule for reconciling them, and the kit README says only
"reconcile" as a to-do.)

---

## 5. Thread C — the Tier-2 grammar already exists in the May tree

This is the most useful find in the window, and it is easy to miss because it sits in a
"concepts" page rather than in the Constitution.

`docs/concepts/aesthetics.rst` @ `266dfe948` binds visual behaviour to *unobservable engine state*:

> **Flicker** — Border opacity oscillates +/-5% at 0.5-2Hz. Applied to active panels and windows.
> Simulates unstable power or signal interference. **Increases during high system load
> (contradiction accumulation).** (lines 253-256)

> **Animation** — Flicker and pulse on state changes. **Screen tearing on heavy load
> (contradiction accumulation).** (line 377)

> **Sound Design** — Static and interference that rises with system stress. […] **High repression
> periods increase static and interference.** (lines 379-395)

> **Signal Conditions** — Weather/environmental effects manifest as signal degradation […]
> **Environmental factors visualized through signal quality, not graphics.** (lines 404-405)

> Scanlines "the eye should **feel** them more than see them". (line 231)

**D:** Read against the October doctrine (#198996: Tier 1 public stats as clean BI, Tier 2 internal
mechanics as cues and derivatives), May's aesthetics page is a Tier-2 specification written eight
months early. It even states the tier boundary — public/environmental reality enters the UI as
*signal quality*, not as extra chart series. The current doctrine is therefore not a departure from
May; it is a return to a document that Article VII had been quietly overriding.

---

## 6. Thread D — the wiring month: numbers must explain themselves

If May has a *positive* design philosophy, it is provenance, not sensation.

- Spec-061 opens by insisting the fixture era was deliberate: pages "were authored with hard-coded
  fixture data so that the UI could be designed in parallel with the simulation engine — an
  intentional choice" (`specs/061-real-backend-wireup/spec.md:10` @ `7ff987ff7`; the Director says
  the same in #P3730: "I used mocks when designing the UI so that is a very intentional choice").
- Its non-goals include "Redesigning the player-facing UI layout, navigation, or visual style"
  (same file, non-goals). **O:** May explicitly declined to change how the game looks.
- The Briefing page is defined as the player's first surface and as narrative: "the first page a
  player sees"; the May kit calls it a "newspaper landing" for the tick
  (`pages-core.jsx:8` @ `273de9be9`). Results is "post-tick feedback"; Intel is "surveillance over
  territories, orgs, edges, and communities" (spec-061 user stories 3 and 6).
- The May 15 course correction adds the mechanism that makes numbers answerable: a
  `BabylonScriptValue` plus a typed selector registry so every displayed number carries a
  contributor breakdown (`docs/agents/babylon-frontend-paradox-course-correction.md:1-60, 200-260`
  @ `283f2e901`). Its stated justification is constitutional: "the constitution requires every
  derived number to trace to primitives or `GameDefines`".
- The same prompt rejects configurable density: "Don't add a 'compact mode' toggle that brings
  everything back. The whole point is fewer surfaces, not configurable density"
  (`...:693` @ `283f2e901`).

**D:** May's UI-as-art direction, if it can be called that, is *legibility as aesthetics*: the
beauty is that a number can be opened. This is the direct ancestor of the October Tier 1 and of the
"each display must answer a decision question" rule.

---

## 7. Thread E — knowledge as relationship (the fog antecedent)

Live in the May tree, though authored 2025-12-26: `ai-docs/epochs/epoch3/fog-of-war.yaml`
("The Epistemic Horizon — The Fish in Water"). It defines intelligence as social, not sensory:

> Intelligence is not about PRESENCE but about RELATIONSHIP. You know what the masses tell you.
> You see through their eyes. […] The State can SEE everywhere (Panopticon) but cannot UNDERSTAND.
> The Revolution can UNDERSTAND but only where it has built relationships.

(**O**: `ai-docs/epochs/epoch3/fog-of-war.yaml:1-60` @ `266dfe948`.)

The May kit already renders a small piece of this: org inspector opacity prints "intel is partial;
further Investigate recommended" versus "intel is reliable enough to plan against"
(`ui_kits/webapp_v2/pages-core.jsx:405-408` @ `273de9be9`). **D:** That is a Tier-1 number carrying
an explicit epistemic qualifier — closer to the current two-tier intent than anything in the
Constitution.

---

## 8. Thread F — sound: estate without doctrine

May's audit found the music system substantially implemented and unconnected: three thematic
suites (crisis, revolutionary, fascist), 20+ files, MIDI generators and rendered assets, no player
hook (#37440, 2026-05-16). The Director's original instruction was explicitly about feel — "the
vibe, the aesthetic, the mood of the game. And how it feels. Translate that into music" (#P192) —
and the fascist suite was commissioned as "the vibe of the fascist enemy bad guys" (#P210).

**A:** no May record uses *dissonance* as a design concept, and no May document defines a
music-to-state mapping. The soundtrack exists in May as an asset estate, not as doctrine. Any
current claim that music carries dissonance for internal states is post-May.

---

## 9. Director's words versus agents' interpretations

| Claim in the May record | Whose words | Evidence |
| --- | --- | --- |
| "Bunker Constructivism" / "Damp Basement Cyberinsurgency"; "grim, atmospheric, hardware-focused vibe"; a machine overheating in a dark room | Director, Dec 2025, relayed into `aesthetics.rst` | #P364; #P291; `docs/concepts/aesthetics.rst` @ `266dfe948` |
| "the vibe, the aesthetic, the mood of the game. And how it feels" → music | Director | #P192 |
| State/narrator voice should be coldly numeric ("Degree centrality > 0.4 … survival: 12%") | Director | #P345 |
| "I used mocks when designing the UI … very intentional" | Director | #P3730 |
| "Commit frontend at a third unit" — the only May design-adjacent instruction | Director | #P3572 |
| UI is "closer to Bloomberg Terminal than to cyberpunk mood board"; "art as tool"; "Mood over meaning" prohibited; glow prohibited | Agent (UI constitution author), promoted to Constitution Article VII | `babylon_ui_constitution.md` @ `266dfe948`; `babylon-frontend-reset-prompt.md:95-101` @ `273de9be9` |
| The collapsed "War Room" is an anti-pattern; 16 routes; no density toggle | Agent, reporting March/April decisions it says the Director made | `babylon-frontend-reset-prompt.md:5,81` @ `273de9be9`; `...course-correction.md:693` @ `283f2e901` |
| "War Room" as the *goal* of composition (step 7) | Agent | `babylon-frontend-reset-prompt.md:130` @ `273de9be9` |
| Bunker Constructivism = "palette-as-data, no decorative glow, no chartjunk" | Agent, October 2026 sweep — the atmosphere has been dropped | `docs/gameplay/research/01-visions-and-brainstorms.md:96` |

**D:** The recurring failure mode is not disobedience. It is *reduction*: each agent generation keeps
the prohibitions (no glow, no chartjunk, no decoration) and discards the intention behind the
atmosphere (the machine should feel hot, damp, and watched). By October the reduction is complete
enough that a research sweep can define Bunker Constructivism as a list of things not to draw.

---

## 10. Contradictions with the current two-tier exposure doctrine

Each item names the May text, the current doctrine it collides with, and what would have to be
ruled on.

**C1 — Atmosphere is constitutionally forbidden, and the doctrine now wants it.**
Article VII prohibits "mood over meaning" and "decorative glow" and requires colour to encode
meaning "not mood" (`babylon_ui_constitution.md` @ `266dfe948`;
`babylon-frontend-reset-prompt.md:97` @ `273de9be9`). Tier 2 asks the UI to be "an aesthetic
expression of the underlying data" (#198996). These are compatible only if every sensory cue is
*also* a quantitative encoding — which is exactly the escape clause Article VII already provides
("unless intensity maps to a quantitative variable"). **Ruling needed:** state that sensation
must be a function of a named state variable, or amend Article VII's successor. **Severity: high**
— it decides whether Tier 2 is legal at all.

**C2 — "Hidden state is prohibited" versus fog.**
Article VII §8 and §10 forbid hidden critical state: "Hidden state — critical variables MUST be
persistently visible"; "These are NOT hidden in menus. They are persistent."
(`babylon_ui_constitution.md` @ `266dfe948`). Fog entered the Constitution only at v4.0.0
(2026-08-22, `c41257141`), and the May-live fog spec makes knowledge conditional on relationship
(`ai-docs/epochs/epoch3/fog-of-war.yaml` @ `266dfe948`). **D:** A Tier-2 cue is now *sometimes* the
only legitimate signal, which Article VII would call hidden state. **Severity: high** — needs an
explicit statement that fogged internals may be communicated by cue rather than withheld entirely.

**C3 — The two canons were never reconciled, so "Bunker Constructivism" means two things.**
`aesthetics.rst` prescribes bloom, grain, vignette, flicker and "the walls sweat"
(@ `266dfe948`); the UI constitution prohibits ambient glow and decorative animation
(@ `266dfe948`). Both were live in May, and the May 5 commit shipped the vocabulary of the first
under a citation of the second (`273de9be9`). **Severity: medium** — mostly a naming hazard, but it
means a citation of "Bunker Constructivism" proves nothing until the cited text is named.

**C4 — Four palettes, no reconciliation rule.**
See the table in §4.3. **Severity: medium** — semantic colour claims ("CRIMSON always means
extraction") are only checkable against one palette at a time.

**C5 — May's graph was deliberately inert; the behemoth reading inverts that decision.**
`GraphView` removed from the briefing, moved to a future route, drawn as a static SVG with no
motion (`...course-correction.md:677` @ `283f2e901`; `shell.jsx:219-260` @ `273de9be9`).
**Severity: medium** — not a contradiction of the doctrine, but a contradiction of the direction of
travel. Anyone proposing a pulsing graph today should say which May decision they are reversing,
and why the graph earned a body it was denied then.

**C6 — Music has no state binding, so "dissonance" cannot yet be a cue.**
Suites exist by political condition, not by engine variable (#37440). **Severity: low** — a
missing implementation, not a conflict.

---

## 11. What to carry forward, and what not to

**Carry:**
1. The Tier-2 grammar in `docs/concepts/aesthetics.rst` (lines 231-405 @ `266dfe948`) — flicker,
   static and signal quality as functions of contradiction, repression and environment — because it
   is the only *mechanical* sensory specification the project has produced.
2. The provenance requirement: every displayed number opens into contributors
   (`...course-correction.md:200-260` @ `283f2e901`). This is Tier 1 done properly.
3. The epistemic qualifier on intel ("partial" / "reliable enough") as the model for how a Tier-1
   number can carry Tier-2 doubt (`pages-core.jsx:405-408` @ `273de9be9`).
4. "Alive (flickering, breathing, not static)" as a *chassis* property
   (`ai-docs/design-system.yaml:29` @ `266dfe948`), not as a licence to animate data.

**Do not carry:**
1. Article VII's blanket "mood over meaning" prohibition as if it were the Director's position. It
   is an agent's drafting choice that the Director's own briefs contradict (#P364, #P291).
2. The claim that May established a behemoth aesthetic. It did not — and the July material
   inherits from a graph May had just demoted (**A** for absence; **D** for the inheritance claim).
3. Any of the four palettes as "the" palette without naming the document.

---

## 12. Open questions for the July miner and the parent session

1. When exactly does *behemoth* enter the record? It is absent from May and absent from the May
   tree; if it appears in July it is a new coinage, not a recovered one (**A** for May).
2. Who wrote the "living map" direction — and does it cite `aesthetics.rst`'s flicker/static
   grammar, or invent a fresh one?
3. Was Article VII ever amended in June before its July 9 de-particularization
   (`4bb8aa0b1`, "Article VII de-particularized … aesthetics are a design-system concern")? That
   commit is the moment the Constitution stopped being able to forbid glow, which may be the real
   permission event for the sensory turn.

---

## 13. Sources

| ID | Date | What it is |
| --- | --- | --- |
| #198996 | 2026-10-26 | Adoption of the two-tier UI exposure doctrine (Tier 1 clean BI, Tier 2 cues/derivatives) |
| #P192 | 2025-12-09 | Director: "the vibe, the aesthetic, the mood of the game… translate that into music" |
| #P210 | 2025-12-09 | Director: music capturing "the vibe of the fascist enemy bad guys" |
| #P291 | 2025-12-10 | Director: "Insurgent Operator" / "Hydroponic Cyber-Insurgency" aesthetic pivot |
| #P345 | 2025-12-11 | Director: the state's voice must be cold, mechanical, numeric |
| #P364 | 2025-12-11 | Director: pivot to "Bunker Constructivism", "grim, atmospheric, hardware-focused vibe" |
| #P3572 | 2026-05-05 | Director: "Yeah let's commit frontend at a third unit" |
| #P3730 | 2026-05-12 | Director: mocks were an intentional choice when designing the UI |
| #34839 / #34842 / #34843 | 2026-05-06 | Frontend reset scope, test count, staged components |
| #34841 | 2026-05-06 | Paradox UI patterns + design spec + router implementation examined |
| #36076 | 2026-05-10 | PyQt6 dashboard deletion confirmed |
| #37440 | 2026-05-16 | Music system implemented as suites; tutorial/data unimplemented |
| #38007 | 2026-05-20 | Epoch 1 complete; Slice 1.5 "The Dashboard" in progress (metabolic gauge) |
| #38025 | 2026-05-20 | README points at React+Django UI; DearPyGui legacy |
| #S2597–#S2604 | 2026-05-05/06 | Spring session cluster: codebase understanding, roadmap, frontend refactor |
| #S2747 / #S2761 | 2026-05-11/12 | Backend-to-frontend wiring assessment; Intel page wiring |
| `273de9be9` | 2026-05-05 | Commit: pivot from single-page war room to 16-route app; ships design kit |
| `283f2e901` | 2026-05-15 | Commit: adds `babylon-frontend-paradox-course-correction.md` |
| `7ff987ff7` | 2026-05-12 | Commit: spec-061 artifacts (real backend wire-up) |
| `266dfe948` | 2026-05-20 | Tree used for all `@266dfe948` quotations |
| `4bb8aa0b1` | 2026-07-09 | Constitution v2.8.0: Article VII de-particularized, annex deleted |
| `c41257141` | 2026-08-22 | Constitution v4.0.0: fog enters the governing text |
