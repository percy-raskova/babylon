# Babylon Onboarding & Product Layer — the door, the veil, and the timeline tree

Dated record, 2026-10-26. Status: APPROVED for design (user, 2026-10-26);
implementation explicitly NOT authorized (the PER-354 workhorse owns the
tree, and tutorial implementation remains parked until the core gameplay
surfaces land in Wave 5). This document is the authority the onboarding
and product-shell plan will argue from. Research briefings and specs it
rests on:
`docs/gameplay/2026-10-25-porch-01.md`, `docs/gameplay/2026-10-25-porch-02.md`,
`docs/gameplay/2026-10-26-combat-design.md`,
`docs/gameplay/2026-10-26-peacetime-economic-verbs-design.md`,
`docs/gameplay/2026-10-26-negotiation-and-party-life-design.md`,
`docs/superpowers/specs/2026-07-17-viable-game-design.md`,
`docs/superpowers/specs/2026-07-27-m3-tutorial-contracts.md`, and
`ai/epochs/epoch3/tutorial-design.yaml`.

## 1. Intent and the why

Babylon's six-screen interface (Topology, Electoral, Physical Map,
Ticker, Wiki, Line/Doctrine), two-stroke epistemic veil (*On Practice*),
and 28-day OODA loop are unlike anything else in strategy gaming.
Dropping a new player into all six screens, four monetary books, fifteen
state cells, and a party congress at Period 0 would drown them in chrome
before they ever felt the hook.

Conversely, a hand-holding pop-up tutorial that pauses the game to
lecture the player about surplus value violates the foundational law of
`Porch 01`: **"Babylon taught me Capital, but it was fun."**

The solution is that **the organizational scale and the epistemic veil
*are* the onboarding curve** (#4), wrapped inside a **Product Layer**
(#5) that lets the player pick their starting terrain, tendency, and
crisis bookmark at the door, branch and compare counterfactual histories
from any past period or Congress, and export their campaign's written
*Short Course* Chronicle and Wiki as clean local Markdown files.

## 2. Goals, non-goals, anti-goals

**Goals.**
- G1. **Progressive Screen & Veil Unlocks (#4):** Start the player at
  Period 0 as a five-person local circle with only the surfaces a local
  circle actually touches—**Ticker (`VeilTier::T0PricesOnly`)**, local
  **Topology**, **Physical Map**, and **Wiki**—and unlock deeper
  instruments (`T1ExploitationVisible`, `T2MarketScissors`,
  `StructuralStateView`, **Line/Doctrine**, **Electoral**, **Party
  Congresses**, and **Stage-2 Mesh Combat**) organically as the
  organization studies, investigates, and grows.
- G2. **Failure as a Safe Teacher:** Let early amateur errors (such as
  *The News Herald Tribune Gazette Drop* yielding `+0` contacts or a
  *Magical Power of Pancakes* kitchen failing to reproduce a single
  cadre) play out fast in the first 3–5 periods so the player feels why
  Lenin and Mao wrote what they wrote.
- G3. **Period-0 Campaign Setup ("The Door," #5):** Give the player a
  sharp, replayable campaign setup screen selecting **(a) Starting
  Region**, **(b) Founding Tendency Archetype**, and **(c) Crisis
  Bookmark** over a deterministically seeded perturbation of the
  `marxist-data-3NF.sqlite` world (`Porch 02` §7).
- G4. **The Counterfactual Timeline Tree & Ironman Toggle (#5):** Turn
  the embedded SQLite campaign store's period-by-period history (`PER-354`)
  into a first-class player toy: a visual **Timeline Tree** where the
  player can fork from any past Period or Party Congress (*"What if we
  had purged Kellerman at Period 24 instead of compromising?"*) and
  compare the two histories, alongside an optional **History Is Written
  in Ink (Ironman)** toggle.
- G5. **One-Click Local Markdown & Replay Export (#5):** Because the LLM
  narrator and Wiki write pure GFM Markdown (`ADR249`), let the player
  export their campaign's entire **Chronicle, Vigilance Case Files, and
  Endgame Reckoning** as a clean local Markdown directory on disk, paired
  with a compact `.babylon` seed-and-intent replay bundle.

**Non-goals.**
- Do not build or wire the tutorial overlay until Wave 5 (`Task 9`, the
  six gameplay screens) exists in `babylon-client` (standing rule from
  `porch-handoff.md`).
- No separate throwaway "tutorial map" with fake rules; onboarding runs
  on the real simulation engine.

**Anti-goals (what makes this a failure even if it works).**
- A1. **Walls of lecture text:** Explaining Marxist theory in modal popups
  before the player has stubbed their toe on the material contradiction
  in play.
- A2. **Hiding locked instruments without a breadcrumb:** Per `Porch 01`,
  locked instruments on the Ticker and Topology are rendered as
  **visible-but-veiled slots naming what unlocks them** (*"Veiled: Study
  Value Theory to reveal Surplus Extraction"*), never silently omitted.
- A3. **Save-scumming away the Long Tail:** Silent quick-load overwrites
  that erase a past mistake without showing the branch. In non-Ironman
  play, loading an earlier period creates a visible **Counterfactual
  Branch** in the campaign's Timeline Tree rather than deleting the
  original history.

## 3. Constraints (binding)

- C1. **Sequencing gate:** Onboarding (`#4`) is designed here so Wave 2
  and Wave 5 expose the right hooks, but its client overlay is scheduled
  strictly *after* the six gameplay screens are playable.
- C2. **Patches & the no-key-naming rule (`2026-07-27-m3-tutorial-contracts.md`):**
  Where the tutorial guide (`Patches` or the mentor voice) speaks, those
  lines are data-driven, never name raw keyboard bindings in prose, and
  never duplicate the `GIVEN / WHEN / THEN` step text.
- C3. **Seeded Period-0 bounds (`Porch 02` §7):** Campaign seeds
  perturb initial county and counterpart conditions strictly within the
  measured historical dispersion of `marxist-data-3NF.sqlite`—never
  producing negative populations, broken conservation identities, or
  un-winnable starts.
- C4. **Deterministic fork identity (`PER-60`, `PER-354`):** Forking a
  campaign at Period $t$ copies the committed SQLite snapshot up to $t$
  and starts a new branch lineage with its own `branch_id` and parent
  `(campaign_id, fork_period, parent_world_hash)`.

---

## 4. Part I (#4): Progressive Onboarding — The Veil Is the Tutorial

Instead of a separate tutorial mode, a new campaign in Babylon teaches
its 6 screens and 4 peacetime verbs in **four organic stages** driven by
the player's own *On Practice* progression (`Study` + `Practice`):

### Stage 1 — The Circle (Periods 1–4: Ticker `T0`, Local Topology, Physical Map)
You start at Period 0 as a five-person circle in your chosen region with
a small cash box and 672 hours per household.
- **What is open:** Only your local county on **Topology** and **Physical
  Map**, the **Ticker** at `VeilTier::T0PricesOnly` (wages, rent notices,
  grocery prices, the 168-hour household week strip, and the
  `Organization` cash book), and the **Wiki**.
- **What is veiled (visible as sealed slots):** The deeper economic
  meters (`T1` exploitation rate, `T2` imperial rent scissors $\Phi$),
  State attention threads $\Theta$ (hidden behind `PoliticalMaturityTier::LiberalFiction`:
  *"Police enforce the law neutrally"*), **Line/Doctrine (Screen #6)**,
  and **Electoral (Screen #2)**.
- **The First Safe Mistake:** The player's natural instinct in Period 1
  is to print 100 newspapers and drop them on doorsteps (*The News
  Herald Tribune Gazette Drop*) or open a soup kitchen staffed by their
  own cadres (*The Magical Power of Pancakes*).
  - At Period 1 Reckoning, the Seal prints `100 newspapers distributed!`
    and the Reckoning shows **`+0` Contacts, `+0` Cadre Labor** (*"The
    paper circulated; the politics did not"*), while a single cadre's
    sick mother triggers the 672-hour cliff (`"Rosa isn't coming"`).
  - The mentor note (`Patches` / *Liberated Signal* marginalia) points
    the player to **Verb 1 (Mass-Line Co-Governance)** and **Study**:
    you need relationships before distribution, and shared reproduction
    before spare hours.

### Stage 2 — Tearing the Veil (`Study` + First Social Investigation)
When the player allocates their first `Cadre Labor` to **Study** (*Value
Theory* & *State and Revolution*) and runs their first **`INVESTIGATE`**
on a local plant or union hall:
- **The Veil of Money lifts on the Ticker (`T0 -> T1 -> T2`):** The
  Ticker animates open to reveal that the gap between wages and prices
  is not "inflation"—it is surplus value ($s/v$) and the imperial rent
  scissors ($\Phi = W_c - V_c$).
- **The Liberal Fiction cracks on Topology (`LiberalFiction -> StructuralStateView`):**
  The neutral blue police badge peels back to reveal competing cellular
  automata (`CityPd`, `CountySheriff`, `FbiFieldOffice`) pricing targets
  from private dossiers $L_c$, unlocking **Verb 3 (Paying the Clandestine
  *Faux Frais*)** and **Verb 2 (Bookkeeping Stances)**.

### Stage 3 — The Room and the Floor (Unlocking Screen #6 `Line/Doctrine` & Screen #2 `Electoral`)
As soon as your circle touches its first external Union Local, tenant
coalition, or internal disagreement (typically Periods 5–10):
- **Screen #6 (`Line / Doctrine`)** unlocks as an active contest over the
  Three-Strand Line (Class, Nation, Gender), showing the live traps
  (*Imperialist Economism*, *Michael Scott Communism*, *KKKommunities of
  KKKare*) and the requirements for **Key A (`ConstituteParty` Congress)**.
- **Screen #2 (`Electoral`)** unlocks the first time a municipal election
  or DA/Sheriff race enters the calendar—immediately letting DSA-style
  players run candidates and discover the `Clout` vs. `Votes` exchange
  rate and the five material barriers first-hand.

### Stage 4 — The Vanguard & The Mesh (Post-Constitution & Dual Power)
Constituting the Party (`Key A + Key B`) starts the visible **260-Period
SPD Calcification Clock** on the Ticker and unlocks full **Party
Congresses** (`Ceremony 8`), while crossing the Dual Power QRF threshold
evolves the operation loadout from early firing-group catalog actions to
late-game **Zone Mesh & Corridor Interdiction** (`2026-10-26-combat-design.md` §4).

---

## 5. Part II (#5): The Product Layer — The Door, The Timeline Tree & Markdown Export

### 5.1 "The Door" — Period-0 Campaign Setup
Per `Porch 02` §7 (*The Law of the Boat*), at Period 0 your organization
is a dinghy: steering it into any strategy is easy now and costly later.
The **New Campaign** screen lets the player configure three choices
before Period 0 generates:

1. **Starting Regional Anchor (Where Your Dinghy Launches):**
   - **Wayne County / Detroit Rust Belt (Canonical Start):** Auto plants
     (Dearborn Assembly), entrenched UAW bureaucracy (Local 600), stark
     urban/suburban segregation, and 4 county jails + 1 prison.
   - **The Black Belt / New Afrika (Internal Semi-Colony):** Contiguous
     oppressed-nation majority, high mass receptivity $M_r$, intense
     comprador-NGO and Sheriff-Plantation (`captive_revenue > tax_revenue`)
     pressure.
   - **Border & Logistics Corridor / Aztlán:** Direct touch on the
     migration rent valve and FAF5 freight choke points; heavy federal
     border/ICE agency presence.
   - **The College & Military-Post Swamp:** High imperial rent $\Phi$,
     half the county employed on post or university payroll, teeming
     with `KKKommunities of KKKare` and `ProtestCircuitTrotskyist` nodes.
2. **Founding Tendency Archetype (Your Initial 5-Person Circle):**
   Remember `Porch 01`: *the DSA electoralist who downloads Babylon to
   prove the designer wrong is a first-class player.* Every archetype is
   playable, honest, and starts with distinct assets and blind spots:
   - **Mass-Line & Prison Ministry Circle (MIM(P) / MLM-TW):** Starts
     with `Study` progress on the Three-Strand Line and a prison-kite
     contact; zero legal cash book, zero electoral clout.
   - **Democratic Socialist / Electoral Chapter (DSA):** Starts with a
     `Legal Institution` book, dues roll, and a City Council ballot
     slot; starts at `PoliticalMaturityTier::LiberalFiction` with
     existing `salaried_staff` (`survival_interest > 0`) and open donor
     rolls visible to police.
   - **Revolutionary Shop-Floor Caucus (DRUM / Syndicalist):** Starts
     with shift stewards inside a productive plant and high strike
     leverage; must fight union payroll absorption and economism from
     Period 1.
   - **Urban Action Cell (Blanquist / Focoist):** Starts with an
     underground safe house (`c > 0`) and expropriated gear; zero mass
     receptivity $M_r$, zero kitchen/reproductive base, and an immediate
     *faux frais* cash burn.
3. **Crisis Bookmark & World Seed:**
   - Choose the starting macro-regime (**Baseline Late-Empire**,
     **Inflation / Super-Wage Squeeze**, or **Acute Imperial Boomerang**)
     plus a shareable **Campaign Seed** string that deterministically
     perturbs county conditions within `marxist-data-3NF.sqlite` bounds.

### 5.2 Save/Load as a Toy: The Counterfactual Timeline Tree & Ironman
Because Babylon's embedded SQLite store (`PER-354`) commits every
28-day period atomically with a `NominalWorldHash` and an immutable
journal, **Save/Load is designed around historical counterfactuals**
(`game-loop-architecture.yaml`: *"Load any state, modify parameter, run
forward, compare"*):

- **The Campaign Timeline Tree (Default Mode):**
  - The game autosaves at every `Seal` / `Reckoning` boundary.
  - Instead of a flat list of overwriteable save files, opening **The
    Archive** renders your campaign as a **branching Timeline Tree**
    marked by your major decisions (Congresses, Strikes, Splits, Wedge
    Offers).
  - At any point—especially after discovering in Period 60 that a compromise
    at Period 24's Second Congress or a fiery speech at Period 8 killed
    your operation—you can click **Fork Timeline at Period $t$**.
  - Forking creates a named child branch (e.g., `Branch B: Purged
    Kellerman at 2nd Congress`) while keeping `Branch A` intact, letting
    you compare the two timelines' Chronicles, wealth curves, and
    Topology graphs side by side!
- **History Is Written in Ink (Ironman Toggle):**
  - For players who want maximum gravity on every `Seal` click, toggling
    **Ironman** at Campaign Setup locks the Timeline Tree to a single
    forward tip until the campaign reaches one of the Four Endgames (or
    mid-campaign destruction)—at which point the full Timeline Tree
    unlocks alongside the Endgame Reckoning so you can inspect and fork
    the "what-ifs."

### 5.3 Exporting the Permanent Record (Local Markdown & Replay Bundle)
As established in `Porch 01`, the player writes the history of their
world as a political treatise, and the LLM's only write permission is
Markdown. At any time—and automatically on the Endgame Reckoning screen—the
player can click **Export Campaign Archive**, which writes a clean,
self-contained local folder to disk:

- `chronicle/` — Every period's chapter (`CH-01` through `CH-N`), titled
  by the period's dominant task in verb form (*Short Course* style),
  with all three narrator feeds (*Corporate Feed*, *Liberated Signal*,
  *Intel Stream*) and the `BRIEF SUMMARY` reckonings.
- `wiki/` — Every unlocked dossier, Vigilance Case File (*Michael Scott
  Communism*, *KKKommunities of KKKare*, *The Queer Qlux Qlan*, *The
  Magical Power of Pancakes*), Promise Register table, and leaked enemy
  SOP memo, linked with standard GFM relative links (`[text](path.md)`,
  `ADR249`).
- `reckoning.md` — Once the endgame is reached, the omniscient narrator's
  full causal-chain reveal (*"What killed you"* or *"What almost killed
  you"*), tracing how early-period speeches, unpurged moles, or skimped
  *faux frais* surfaced decades later.
- `replay.babylon` — The compact deterministic replay bundle (initial
  seed + scenario hash + per-period sealed intents) that any copy of
  Babylon can open to verify the `NominalWorldHash` chain or fork a
  counterfactual branch from any period.

## 6. What is left to the builder

- Exact Bevy layout of the **New Campaign ("The Door")** screen and the
  **Timeline Tree** branch selector.
- Exact directory template and frontmatter metadata for the exported
  local Markdown archive folder.
- Authoring the remaining `Patches` / marginalia lines for Stage 1–4
  progressive veil unlocks once Wave 5 (`Task 9`) lands the six screens.

## 7. Builder-check rulings (author calls, 2026-10-26)

A builder-check review (`deepseek/deepseek-flash#high`) returned ten
architectural questions; all ten are settled here from the Architecture
Reset (`docs/architecture-reset/06`–`07`) and existing canon:

- **R1. Replay-backed Timeline Forking (`07-history-replay-and-archive.md`):**
  Per Chapter 07's retention law (opening + current + latest 13-period
  checkpoints + full intent journal), forking at an arbitrary Period $t$
  copies the nearest retained checkpoint $\le t$ into a new `.sqlite`
  campaign file (whose `OpeningMetadata` records `(parent_campaign_id,
  fork_period, parent_world_hash)`) and deterministically replays the
  committed journal through $t - 1$, landing at the start of Period $t$'s
  **Decide** step with Period $t$'s original command unsealed so the
  player can make the counterfactual choice.
- **R2. Chronicle & Wiki Markdown retention vs. template fallback:**
  Earned dossiers and delivered chapter Markdown are stored as they are
  generated; if a campaign is played with LLM narration disabled, the
  deterministic template renderer (`Porch 01`) produces the exported
  Markdown chapters from the retained period summaries so `Export
  Campaign Archive` is always complete and offline-capable.
- **R3. Engine-owned `VeilTier` and locked-slot breadcrumbs:** Per Wave
  2 (`Task 3: epistemic_fence.rs`), `epistemic_fence::project_player_view`
  is the sole authority deciding whether an instrument is veiled and
  returns a typed `FieldState::VeiledInstrument { unlock_hint }` to
  `babylon-client`—never client-side hiding.
- **R4. Regional Anchors in Michigan (`P7a`) vs. National (`P6`):** In
  the Michigan campaign, the four anchors map to Michigan county
  clusters (Wayne/Dearborn auto-UAW; Washtenaw/Ingham college-payroll
  swamp; Detroit/Port Huron freight-border corridor; urban/rural
  prison-pipeline counties); in the National campaign (`P6`), they map
  to the multi-state regional clusters.
- **R5. Crisis Bookmarks are strictly Period-0 initial-condition presets:**
  Per the Constitutional compact ("executable shocks remain absent"), a
  Crisis Bookmark modifies only Period-0 starting stocks, price steps,
  and $\Phi$ / fiscal balances; the simulation runs identical governed
  rules thereafter with zero scripted shock schedules.
- **R6. Sum-preserving Period-0 seed perturbations:** Seeded
  perturbations apply sum-preserving integer pair-transfers within the
  measured historical IQR of `marxist-data-3NF.sqlite`, preserving
  wealth and $\Phi$ conservation by construction without generate-and-reject
  loops.
- **R7. `replay.babylon` format:** Contains the campaign seed,
  `OpeningMetadata` (`build_hash`, `content_hash`, parent branch link),
  and the ordered log of sealed per-period intents, verifiable against
  any matching build/content install.
- **R8. Ironman flag in `OpeningMetadata`:** Stored as an immutable
  `OpeningMetadata` attribute (no new SQLite table) and enforced by
  refusing `fork_at_period(t)` until `EndgameSummitState` (or
  mid-campaign destruction) is reached.
- **R9. Parameterized Archetype deltas over Regional Anchors:** The 4
  Founding Tendency Archetypes are parameterized opening deltas applied
  to the chosen Regional Anchor's primary plant, union hall, campus, or
  carceral edge (not 16 separate scenario copies).
- **R10. Statutory Election Calendar:** Municipal, DA/Sheriff, and
  federal elections run on fixed period intervals in `defines.toml`,
  with the first local municipal/DA race scheduled at Period 6 so DSA
  starts and Stage-3 circles encounter an early electoral contest
  deterministically.
