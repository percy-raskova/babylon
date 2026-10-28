# Babylon Combat Design — the insurgent route

Dated record, 2026-10-26. Status: APPROVED for design (user, 2026-10-26);
implementation explicitly NOT authorized. This document is the authority
the implementation plan will argue from. Research briefings it rests on:
`research/16` (PPW and dual power), `26` (RAND COIN doctrine), `27`
(endings and violence logic), `30` (people's-war operational grammar),
plus the kinetic-warfare doctrine (`ai/epochs/epoch3/kinetic-warfare.yaml`)
as superseded-where-noted. Briefings 28, 29, 31 folded 2026-10-26;
briefing 32 (Lawvere) landed 2026-10-26 with a refutation, recorded
in O1; briefings 28, 29, 31 folded 2026-10-26.

## 1. Intent and the why

Babylon is a political simulator with an insurgent route, not a war game.
No existing game does insurgent warfare justice: all assume
conventional-on-conventional forces, resolve combat as body-count dice,
and treat loss as numbers ticking down. Babylon's combat must be the
route of the sergeant, the rebel, the people's army — realistic, gritty,
never glorified: entertainment that makes the player think, where the
weight of every operation is political before it is military. War is
diplomacy by other means, and the engine must price the diplomacy.

The design veteran-grades the problem: it was seven years of someone's
life, and getting it right is a requirement, not flavor.

## 2. Goals, non-goals, anti-goals

**Goals.**
- G1. Two-stage dialectical combat: squad-scale direct action early,
  zone-scale network warfare late, with the interface evolving because
  the commanded object evolves.
- G2. Every operation carries a political invoice — consciousness,
  legitimacy, base, cadre — itemized where the player cannot look away.
- G3. The fed trap as the core skill: telling your moment from the
  state's setup, through provenance, not labels.
- G4. Long memory: early decisions resurface dozens of turns later
  through the state's evidence pool, with an LLM-rendered endgame
  reckoning of the causal chain.
- G5. Winnable without ever being fair: the state is terrifying but
  never one thing, and its contradictions are terrain.

**Non-goals.**
- No base-building, no unit production, no research trees, no division
  designer, no map-painting. Ground is costly to hold and cheap to
  deny; the engine must make the player feel that.
- No symmetric Red-vs-Blue balance. Asymmetry is the subject.
- No new engine primitive is anticipated; quantities already exist
  (Heat, legitimacy, cadre labour, organization, knowledge_seq,
  journal). Thresholds are discrete; no sigmoid, no second fixed
  response curve.

**Anti-goals (what makes this a failure even if it works).**
- A1. Glorification: body counts without political cost, war as
  spectacle, violence without invoices.
- A2. The decisive-battle instinct: any mechanic that rewards storming
  the palace over destroying effective strength.
- A3. An invincible state: anything that teaches the player resistance
  is futile demoralizes instead of engaging.
- A4. A fair fight: symmetric mechanics with different skins.

## 3. Constraints (binding)

- C1. The engine judges mechanics; the LLM narrates only, in markdown,
  with god-mode reads. The endgame reveal is rendered from actual
  engine records (journal, state diagrams, archives), never invented.
- C2. Visibility rule: show only what a history-book participant could
  learn — except the endgame screen, where the narrator is explicitly
  granted the full view.
- C3. Fog that lies: intel in unorganized terrain is masked, not
  uncertain. Receptivity-gated truth from the ambush-trap mechanic
  applies to targeting: you cannot know terrain you have not organized.
- C4. Stage is derived, never stored. No screen shows a stage number;
  no designer writes `stage += 1`.
- C5. Armed action without a base is focoism and must be selectable,
  look brave, and carry the historical consequence (a flash of fury plus
  a legitimacy transfer to the state).
- C6. The ten principles are not purchasable by the state; loss is
  payable in cadre and legitimacy, never only units.

## 4. The two stages and the transition

**Early: the catalog.** Marighella's mission list, executed under
discipline: ambush, sabotage, raids and penetrations, expropriation
(funding), liberation of prisoners, armed propaganda, war of nerves.
Unit scale is the firing group; cadres are personified slots —
representations of aggregates, classes, organizations — never
simulation individuals (Director ruling, 2026-10-26; capabilities live
on organization pools, names generate at the loss receipt). Operations fund the movement (capture is the production function:
no rebel quartermaster — equipment comes from the enemy, so every
advance requires contact) and draw on a six-commodity support
portfolio (manpower, funding, materiel, intelligence, sanctuary,
tolerance) whose sources the state can see and price. Denial shifts the
mix; substitution costs legitimacy and visibility.

**Late: the mesh.** The player commands Giáp's three troop categories
across zones — ubiquitous militia, elite regulars — through a
network-integrity layer: 21st-century distributed comms (burners, cloud
dead drops, couriers where it is dark), no headquarters with antennas.
Operations are possible only where lines of communication reach; the
state hunts the relays. Coordination where the mesh holds is swarming:
simultaneous action without a center — but a swarm has no standing
capability, only a duty cycle (dormant, coalescing, pulse, dispersal),
and coalescing is the leak: gathering is when the state sees you.
Action further requires a mandate slower than the pulse (the assembly
authorizes what the fighters execute), and connection has an optimum,
not a maximum — over-connected units oscillate between zones and act
in neither, while a severed mesh gets picked off in detail. The asymmetry is the texture —
satellites and fusion centers against a network built to be expendable.

**Interdiction economics (material layer).** Corridors obey the
min-edge rule: one fully damaged segment on a trunk removes the great
majority of its throughput — interdiction is cheap, repair is not, so
target selection matters more than force committed. Starvation is
conserved, never broadcast: a cut feeds nothing downstream, and the
decisive cut is the last edge before a subtree. Distance penalties are
discrete authored steps, never a fitted curve — the compiled sigmoid
is the exact primitive the constitution refuses.

**Transition.** The player authors it through constrained allocation —
pointing, clicking, scales, a planning mini-game with anchors — and the
engine recognizes the material conditions underneath (liberated
administration that survives a repression cycle, a replacement rate that
holds). Structure for the artwork: the player writes the plan, but only
inside a structure the engine enforces. Neuberg's fourteen-element town
plan is the model: planned element by element, unfilled elements become
the failure script, and the commander's own location is on the map.
pointing, clicking, scales, a planning mini-game with anchors — and the
engine recognizes the material conditions underneath (liberated
administration that survives a repression cycle, a replacement rate that
holds). Structure for the artwork: the player writes the plan, but only
inside a structure the engine enforces. Neuberg's fourteen-element town
plan is the model: planned element by element, unfilled elements become
the failure script, and the commander's own location is on the map.

## 5. The fed trap (core loop)

Every operation — genuine or planted — arrives through the identical
offer UI with a visible provenance trail: who brought the target,
through which channel, what the player's own investigation confirms.
The engine never labels the setup. The difference lives in the
provenance details and whether the organized base confirms the intel.
Restraint is always on the menu and sometimes the only correct move.
The trap works because the door opens: off-menu violence is attemptable
and priced in cadre and legitimacy rather than refused. The state's
deeper weapon is classification: deciding who is reconcilable
(moderate, buyable, splittable) and who is irreconcilable, and making
the decision true by offering just enough to split the organization.
The player answers from an Offer/Split ledger — preempt the buyout,
negotiate the split, double the bought asset, or refuse and wear the
consequence.

## 6. Violence menu and control

County control is a gradient, and the gradient dictates the violence
menu: selective where held or contested, indiscriminate only where
there is nothing to lose. What is unavailable is not greyed out — it is
absent, because the population will not do it or the terrain will not
hold it. Two corrections from the research ride along: making a county
illegible does not shield it, it relocates the state's efficient
violence onto the neighboring county (illegibility has a blast radius);
and discipline is a boolean latched by the first unpunished atrocity.

## 7. Loss, gravity, invoices (all three surfaces — decided)

When the encryption capability is destroyed, it blinks out — and the
player discovers it when they reach for it and it isn't there. The
human face is minted at the loss receipt: the slot generates its name
at the moment of loss (never a simulation individual before that), and
the three surfaces carry it from there:
- the named cadre who doesn't come back;
- the civilian cost printed on the Ticker next to the price of bread;
- the Wiki writing down what happened where the Corporate Feed lies.
Giáp's rule is the doctrine: losses avoided even at the cost of ground;
Neuberg's counter-pole (the defensive is death) stands as the live
contradiction the player must resolve in play, not in a tooltip.

## 8. Long memory and the reckoning

The permanent journal is already immutable history, so the Palantir is
the state's view over the player's own journal: the fiery speech drains
Cadre Labor, raises the risk score, and feeds militia recruitment now —
and writes camera footage plus a decade-old arrest into the evidence
pool, where they wait until an identification check kills an operation
years later for reasons predating it. The QRF ring thickens exactly
where the player has operated; the crossfire family stays in the
front's composition. At the endgame, the narrator — granted the full
view once, and only once — renders the chain on both screens: "what
almost killed you" in victory, "what killed you" in defeat.

## 9. Winnability

The state is terrifying but beatable because it is never one thing:
collection is not fusion (fifteen competing cells hoard and refuse to
share); the mobile reserve is finite (anywhere expensively, never
everywhere); repression has a legitimacy price — and the enemy's
internal contradictions work against it (rival incentives, turf war as
terrain, assets that can be turned, factions set against each other).
And invisibility defunds the analyst: the state's circularity trap
(unknown prevalence, no budget, no discovery) means what it cannot
count, it cannot fund watching — until the player forces it to evidence
prevention at the late, countable, near-disaster point.
The player never defeats the machine; they make one component late
every period while the machine's contradictions do the rest.

## 10. Open items (left to the builder unless marked Director)

- O1. Lawverean formalization (briefing 32 — VERDICT: refuted as
  stated, confirmed in the object). Composition integrates the middle
  out, so the composite remembers its factors only up to "has the same
  law" — composition does NOT remember, and the §8 long-memory claim
  must not rest on it. What the text actually gives: memory is a
  place — the process arrow's domain contains the full history
  (turn 5 is literally in turn 50's domain), and forgetting is an
  explicit arrow (Markov projection). Design rule: long memory lives
  in OBJECTS (the journal, the evidence pools — the domains), never
  in composed scalar updates; any scalar heat/suspicion that claims to
  remember is a declared Markov assumption and must be audited as
  such. Implementer warning: the paper's composition symbol is
  diagrammatic (left-then-right), reversed from modern convention —
  any implementation from it must flip the order.
- O2. Inputs still to fold: briefing 32 (Lawvere formalization) and
  the Palestine / Russian and Chinese civil war / South Africa case
  studies. Briefings 28, 29, 31 are folded above.
- O3. Director rulings banked: `ControlRatioSystem` name collision
  (prisoner control vs county control); `territory.bsl` legibility
  override (accumulated Heat vs local-guide predicate).
- O4. Leak-surface framing ("you fear the meeting") — proposed,
  awaiting veteran confirmation.
- O5. Whether victory redacts any of the file in the endgame reveal.

## 13. Gameplay loop, atomic operation, endgame (author proposal,
2026-10-26 — Director: the loop answers Q1, the endgame is delegated)

The cybernetic loop, one 28-day period per turn, riding the existing
Decision Ceremony. It is the OODA loop, instantiated: Read is Observe;
Verify and Allocate are Orient; Load out and Seal are Decide; Reckoning
is Act; the Long Tail is the feedback that re-opens Observe. (Director,
2026-10-26: "the basic gameplay loop is OODA" — approved as the
loop's identity.) This instantiates the pre-existing formalism
(`ai/THE_FORMALISM.md`): OODA is the rate limiter (I.17) — capacity
per tick paces every verb program, chains sequenced across ticks,
never burst, which is what the Seal rule enforces; verbs are atomic
(no macro-verbs, no scripted combos), which is what the atomic
operation enforces; and Attack already raises the acting org's heat,
which is precisely what the state AI's observability/escalation
machinery reads — the invoice coupling predates this document.

1. **Read.** Ticker (what changed, what relief costs now), Topology
   (where the second administration grew or shrank), Map (QRF rings —
   what the state can still enter cheaply), Wiki (what happened,
   including backdated discovery), dossiers (fog-bound, as earned).
2. **Verify.** Spend finite cadre-hours confirming intel
   (receptivity-gated truth) and checking provenance on offers. Every
   hour here is an hour not spent elsewhere — the 168-hour metabolism
   is the master scarcity. Verification runs on three Standing Asks:
   questions whose answers would change an action this week, each
   naming its decision, its answerer, the price the answerer pays,
   and the answer-by time — carried in heads, never written down.
   Ground truth lives in the County Book: four ledgers kept in four
   different heads, never in one place, decaying, seizable. Its
   accuracy is an asset and its existence a liability — a captured
   cadre compromises exactly one ledger.
3. **Allocate (the plan UI).** Distribute cadre-hours across mass work,
   institution goods, intel/counterintel, op preparation, and rest.
   Constrained sliders and scales, not freeform: structure for the art.
4. **Load out.** For each committed operation: offer, staffing drawn
   from organization capability pools (personified slots, §4),
   expropriated equipment, approach (surgical vs blind), extraction
   plan, diversion, timing. This loadout screen is the FFT texture —
   squad composition as the tactical game, played before the fact.
5. **Seal.** Lock the period. No player input after this point:
   preparation is meaningful because it is the last word.
6. **Reckoning.** The engine resolves: tick phases run, ops resolve
   under fog to named outcomes, invoices post (consciousness,
   legitimacy, heat, casualties, evidence into the journal and the
   state's pools).
7. **Long Tail.** Ripples: prices move, Wiki entries land, front
   composition shifts, QRF rings thicken where you operated, dossiers
   publish. The narrator renders; the next Read begins.

The atomic operation falls out of the loop: a single committed
decision — offer plus staffing plus preparation plus timing — sealed in
step 5, resolved once in step 6, invoiced in step 7. Concurrency is
bounded by cadre-hours and leak surface, not by slots: every additional
op in a period costs preparation depth and widens the meeting the
player should fear. There are no tactical choices inside an operation;
all tactics live in steps 2–4, which is what makes them matter.

Endgame mapping: armed victory is TrueLiberation via the crossover —
the QRF calculus failed in more than one region at once with the goods
clause holding. Defeat can strike mid-campaign: annihilation below
critical mass with the line unwritten is destruction (the record
survives on the Wiki; the run ends); with the line preserved it is
strategic retreat (regression, play continues from the defensive).
Survival to the horizon with the reckoning is the "you endured"
variant. The reckoning names the minted names, reads the file, and
renders the what-ifs from actual records.

## 11. Builder handoff

Build from this document plus the cited briefings; do not go back to
the user except through the review below. Calls made here by the author:
off-menu violence attemptable-not-refused (§6); discover-loss-when-
reached-for (§7); full chain on both endgame screens (§8); plan UI as
constrained allocation with Neuberg elements (§4).

## 12. Builder-check rulings (author calls, 2026-10-26)

A builder review returned nine questions; six are settled here, three
go to the user (asked alongside this document).

- R1. "No new primitive" bans new mathematics, not new stored state.
  No sigmoid, no second response curve, no new formalism — but new
  state must be expressed through existing machinery (graph nodes,
  journal records, knowledge_grant/Dossier/service_state patterns).
  New tables only if typed and governed like the existing nine.
- R2. Fed-trap offers are generated from the state agencies' own
  dossiers and deception capacity (existing graph machinery: Dossier,
  Capacity, false-flag concepts), never from an independent random
  table; genuine allies can also source offers, each with its own
  agenda. Always observable: channel, vouch chain, and the cost of
  independent confirmation.
- R3. Killed stay dead; captured enter the existing carceral pipeline
  (arrest, county jail, prison, organizing, release) and a recovered
  specialist's capability returns with the person. The loss receipt
  has two branches.
- R4. One contested legitimacy quantity per county. "The player pays"
  and "the state gains" are the same write; focoism's transfer, the
  discipline latch, and the risk score all move it.
- R5. Canonical period is 28 days (`DAYS_PER_TICK = 28`). A
  "decade-old arrest" is ~130 ticks; "dozens of turns" is one to three
  years; long memory is observable inside a normal campaign. (The
  "7-day" figure in the review is a negative test vector, not live
  config.)
- R6. The sealed-with-honest-reason contract stands (ADR249 R9):
  unavailable operations render as sealed rows whose reason states the
  population/terrain refusal. "Absent" in §6 means absent as an
  executable action; the sealed row is what makes the menu a map of
  what the population will actually do.
