<!-- vale off -->
<!-- Research briefing: dated evidence with literal identifiers preserved. Not governed prose. -->

# 17 — Serge, Sparrow, RAND, and the Bonapartist Cellular Automaton

Read-only briefing, 2026-10-25. Question: **if every non-player agent is a cellular automaton climbing
its own local maximum, what is the State Machine State, and how does a Caesarist / Bonapartist
competition among factions and agencies produce it — emergently, deterministically, with fractures the
player can actually work?**

**Ruling under study (verbatim):** "All non-player agents should be treated like cellular automata
optimizing some sort of local maximum function, and that is what determines the State Machine State. The
state is like a Caesarist Bonapartist competition among Factions and Agencies and their interactions. The
state is not an eternal monolith; it is a bunch of actors pursuing maximal budgets, political power,
lobbying for expansion, protecting their institutional interests, all optimizing individual things."

**Sources.** Serge, *What Everyone Should Know About Repression* (1926),
`/media/user/data/old-hdd/old-hdd/www.marxists.org/archive/serge/1926/repression/{preface,ch2,ch3}.htm`,
read verbatim today. `/home/user/Downloads/babylon_books/`: Sparrow, *Beyond 911* (1990), *The Character
of Harms* (2008), "Informing enforcement" (1992), *Social Networks* 13 (1991), *IJIC* 5:3 (1992), Jerry
Lee lecture, *Crime Science* 7:14 (2018); Long, *On "Other War"* MG-482 (2006); Davis & Cragin, *Social
Science for Counterterrorism* (2009); Paul/Clarke/Grill, *Victory Has a Thousand Fathers* (2010); Jones
& Libicki, *How Terrorist Groups End* (2008). Repo: `ai/state-ai-algorithm.yaml`,
`ai/carceral-equilibrium.yaml`, `ai/epochs/epoch3/{repression-logic,state-attention-economy}.yaml`,
`ai/spec-prompts/enemy-ai/{coin.md,036-state-verb-system.md}`,
`ai/spec-prompts/{org_topology_speckit_prompts_v4_final.md,institution_speckit_prompts_v1.md}`,
`ai/_inbox/adversary-train-design.md`, `ai/decisions/{ADR172,ADR178,ADR180,ADR183,ADR184}`,
`ai/state.yaml:550-600`, `docs/concepts/{state-apparatus-ai,institution-model}.rst`,
`docs/reference/{state-apparatus-ai,organizations}.rst`, `reports/heat-system-dossier.md`,
`docs/gameplay/research/08`, and `rust/crates/babylon-graph/src/{capacity,dossier,exposure,backfire,induced}.rs`.

**Limits.** The 1992 *IJIC* paper is image-only here; it reaches this briefing through the 1991 paper and
`coin.md`'s quotations. Serge's Okhrana chapters (`ch1a/ch1b/ch4`) are **absent from this host**, so every
Okhrana-specific number below (Savinkov chart, Riga plan, 250 volumes) is cited from
`reports/heat-system-dossier.md`'s record of a primary fetch on 2026-07-30, not re-verified today. Azef,
the Security Sections and February 1917 are **standard historiography, flagged where used**, and are not
in the corpus.

**Guardrail.** MIM(P) / MLM-TW. Serge is read **only** as the 1926 archival anatomy of police files and
provocation mechanics; his later politics are excluded and nothing here depends on them. Nothing below
licenses Trotskyism, insurrectionism, or the ultra-left inference that a divided state is a weak one.

---

## 0. Thesis

**Babylon already models the state as three factions sharing one objective function. The ruling changes
the unit of computation: not three factions over one budget, but a dozen agencies over a dozen budgets,
each ranking priced options against its own partial dossier. The State Machine State is then not a choice
the state makes — it is the fixed point of their competition, and the competition has a fiscal shape, so
it can be computed rather than narrated.**

1. **The local maximum is already in the code.** `Capacity::allocate` ranks candidates by yield per unit
   spent on the actor's own `Dossier` and funds down the list until the instrument is empty. That is a
   local maximizer over a finite priced set, evaluated on belief. Nothing is missing but a second
   `Capacity` per agency and a rule for who gets replenished.
2. **Bonapartism is a fiscal outcome, not a mood.** An agency becomes autonomous when its replenishment
   stops depending on any ruling fraction's discretionary transfer and starts depending on threat
   demonstration. In crisis, that is the only revenue line that grows.
3. **February 1917 is structural, not stochastic.** If the candidate set is drawn from the dossier, an
   unindexed mass cannot be ranked — not because the state rolled badly, but because no candidate exists.

---

## 1. What already exists

### 1.1 Four layers, and a budget with an owner

`docs/concepts/institution-model.rst` fixes the layering, and it matches ADR184's ontology: **substrate**
(class, territory, community) → **institution** (the crystallized social relation: `RSA_POLICE`,
`ISA_EDUCATIONAL`, `ECONOMIC_EXTRACTIVE`) → **organization** (what acts, and holds a budget) → **key
figure**. The FBI is an organization inside the DOJ institution; a parish is one inside a church. ADR184
R1 then removes the last place "the state" could hide as a force of nature: `Capacity` carries `owner:
NodeId` and has no `Default`, and `Candidate.actor` names who pays.

That one type change is the precondition for the ruling. A budget owned by "the state" cannot compete
with itself. A budget owned by twelve organizations can.

### 1.2 The factional coalition (the current State AI)

`ai/spec-prompts/enemy-ai/036-state-verb-system.md` and `docs/concepts/state-apparatus-ai.rst` define
three fractions whose objective functions are blended by weight:

| Fraction | Material base | Preferred verbs | Tell |
|---|---|---|---|
| Finance-Capital | profit rate, accumulation, rent capture | `CO_OPT`, `DEVELOP` | panics to `REPRESS` only when extraction is hit |
| Security-State | the repressive apparatus itself | `REPRESS`, `ADMINISTER` | incentive to *maintain* threat perception |
| Settler-Populist | imperial rent to the settler nation | `DEVELOP` (displacement), `CO_OPT` (bribe base) | radicalizes when the rent pool contracts |

The claim is already the right one and it is MLM-TW, not pluralist: *which fraction dominates is
emergent, and the player's actions shift which version of the state is being fought.* Fascist
convergence is a conjunction (`SS > 0.4`, settler `collective_identity > 0.6` with
`ASSIMILATIONIST_FASCIST`, `FC < 0.25`) with entry thresholds easier than exit — hysteresis, not a
script. **The ruling adds the missing middle.** Three fractions over one budget is a single actor having
an internal argument; a dozen agencies over a dozen budgets is a *market*, and a market has prices,
losers and defection.

### 1.3 The verb system

Six verbs, **twenty-two** sub-verbs as `036` enumerates them:

| Verb | Sub-verbs | Writes to |
|---|---|---|
| `ADMINISTER` | `FUND`, `STAFF`, `LEGISLATE`, `AUDIT` | the apparatus itself |
| `DEVELOP` | `INVEST`, `REZONE`, `DISPLACE`, `NEGLECT` | territory, property, population |
| `RESEARCH` | `PURSUE_TECH`, `DEPLOY_TECH` | the state's own action space |
| `CO-OPT` | `BRIBE`, `PROPAGANDIZE`, `INCORPORATE`, `DIVIDE` | civil society, and *edges* |
| `REPRESS` | `SURVEIL`, `INFILTRATE`, `RAID`, `PROSECUTE`, `LIQUIDATE` | organizational topology |
| `WITHDRAW` | `STRATEGIC_WITHDRAWAL`, `TACTICAL_RETREAT`, `SCORCHED_EARTH` | commitment, then ground |

The "25" in circulation adds `EMERGENCY_POWERS`, `MASS_RAID` and the fascist pair
`POGROM`/`VIGILANTISM`, which live in the escalation narrative and the fascist-verb resolver rather than
under a parent verb. Worth pinning: a CA rule table needs an exact arity.

Two sub-verbs carry this briefing. `DIVIDE` targets **edges, not nodes**, and requires prior `SURVEIL` to
know which edges exist. `INFILTRATE` inserts a node that does not merely report but *degrades coherence
from inside*; `repression-logic.yaml` §3 makes it the **Malinovsky Paradox** — at cell discipline ≈ 0.8,
`spy_labor_output = discipline × competence × cover_factor` exceeds `intel_leak = (1 − discipline) ×
competence × extraction_efficiency`, so the spy becomes a net contributor and the state must choose
between paying and burning the asset.

### 1.4 Observation ceilings and the Sparrow selectors

`docs/reference/organizations.rst` defines `IntelMethodology` as four booleans plus a ceiling, and its
three presets already *are* the inter-agency fracture:

| Preset | Centrality | Equivalence | Template | Temporal | Ceiling |
|---|---|---|---|---|---|
| `local_pd()` | yes | no | no | no | **0.2** |
| `fusion_center()` | yes | no | no | yes | **0.5** |
| `fbi()` | yes | yes | yes | yes | **0.4** |

The Fusion Center sees the most and can *do* the least; the FBI can do the most and sees less than the
Fusion Center; the Local PD sees least and is the only one standing on the block. That is not a tuning
table. It is three different local maxima.

`org_topology_speckit_prompts_v4_final.md` §Phase 3 and `ai/_inbox/adversary-train-design.md` §W3 pin
the selector grammar: **`SURVEIL` → singleton, `INFILTRATE` → cutset, `RAID` → centrality.** A *singleton*
has no structural equivalent (Sparrow's role-uniqueness — arrest them and there is no substitute); a
*cutset* is a set whose removal fragments the graph (Menger); centrality is the general bridge hunt.
`KeyFigure.is_singleton` and `structural_importance` already exist.

### 1.5 The live Rust estate — built, uncalled

| Module | What it is | Status |
|---|---|---|
| `capacity.rs` | `Capacity{owner, budgets}`, `Candidate{actor, instrument, mode, target, expected_yield, cost}`, `allocate` → `AllocationOutcome{funded, declined}` | live, zero callers |
| `dossier.rs` | `Dossier{owner}`, `resolve_node/edge`, `knows_*`, `scope`, `stale_nodes`, `reconcile` | live, zero callers |
| `exposure.rs` | `components`, `removal_differential`, `degree_signature`, `signature_class_size`, `decapitation_value` | pure reads, zero callers |
| `backfire.rs` | `Backfire{protected_fraction, interpreted_fraction}` + `total()` | a measure, no curve |
| `induced.rs` | `co_projected_peers` — org↔org adjacency induced from shared `MEMBERSHIP`/`PRESENCE` | the missing edge producer |

Three properties are load-bearing and should not be re-litigated:

- **`allocate` is the escalation mechanic in full.** It funds in descending yield-per-unit until the
  instrument is dry; a candidate that no longer fits is *declined with its shortfall*, and cheaper
  candidates behind it still get funded. "Wanted the raid, could only afford the wiretap" is a typed
  return, not a narrative flourish (ADR184 R9).
- **Yield is computed on `L`, never on truth.** `exposure.rs` says it plainly: passing the true graph asks
  *what would a strike yield*; passing `L` asks *what the state believes a strike would yield*. Same
  arithmetic, different question — and keeping it one function is what stops the engine granting
  omniscience.
- **No threshold constant exists in `capacity.rs` and none may be added** (ADR172 r5, no imposed
  functional forms). That indicts the frozen reference's `heat_escalation_threshold: 0.6` and
  `thread_escalation_thresholds`: the *old* idiom, retained in `canonical_defines.json` as contract, not
  as a model to reproduce. And because `decapitation_value = Δφ(v) / |signature-class(v)|` is a quotient,
  the failure of decapitation against a distributed organization is not a coded exception — a redundant
  structure divides its own yield and the allocator declines.

**The ruling is nearly free in the Rust idiom and expensive in the frozen one.** In Rust, a second agency
is a second `Capacity` with a different `owner` and replenishment source; in the frozen idiom it is
another faction-weight vector and another threshold ladder. Build in Rust.

---

## 2. Victor Serge: the card index and the blind spot

### 2.1 The map precedes the arrest

"the immediate aim of the police is more to know than to repress. To know in order to repress at the
appointed hour, to the extent desired" (`ch2.htm`, verbatim). The instrument was a **typed, tiered ego
network**: the "Connections of Boris Savinkov," *two feet deep and three feet wide*, subject at the centre,
**red** circles for combat connections (groups of nine, eight, six), **green** for direct contact (37),
**nine yellow** for relatives, **brown** for friends-of-acquaintances. Two hops, typed edges,
role-differentiated tiers, drawn by hand in the 1910s, arcs timestamped — "Ivanov called on Pavel. Another
arrow links him to Marfa, who visited him at mid-day on the 27th."

That is `degree_signature` plus role classes in coloured pencil sixty years before the algorithm, and it
reproduces the 1991 paper's warning: *who you know most about* is not *who is central*.

Three mechanics follow. **Repression waits on map completeness**: the "Plan for the liquidation of the
Social-Democratic organisation of Riga" enumerates the CC (4 names), the propaganda committee (2), the
Riga Committee, 5 groups, 26 sub-groups — "**76 names in some 30 units. The only thing left to do is to
seize them all in one fell swoop.**" Nobody on that chart was arrested for an act. **It fires as one
simultaneous sweep**, denying the organization the chance to regrow around a partial cut. **The unit is a
structure, never an offence** — which is why `heat ≈ illegality` was refuted and L/K/X replaced it.

The map could be **better than the movement's own**: the archives held "a Plan of the Organisation of the
Socialist-Revolutionary Party, such as not even the members of its own Central Committee possessed." The
state's map is *biased*, not *dimmer*; on the structural question it was sometimes the better cartographer.

The apparatus was a **produced good with a labour cost**: 250 thick volumes on SD organizations for 1912
alone; the Paris station chief at 1,000 francs a month; a double execution itemized at 76 roubles, the
hangman taking 50 — "All in all, not very dear." Informant rates ran 3–200 roubles a month against a
student's 25-rouble cost of living, and **the premium was paid for centrality**: Malinovsky entered
Okhrana service in 1907, reached a "princely" 100 roubles/month by 1910, was elected to the Bolshevik CC at
Prague in 1912, and chaired the Bolshevik Duma fraction by 1913.

### 2.2 The provocateur must build the party

To remain worth 100 roubles a month, Malinovsky had to be *believable* — organizing strikes, speaking
well, building the organization he reported on. `repression-logic.yaml` formalizes the net value of that
labour against the intelligence leaked, crossing over near discipline 0.75–0.8; above the crossover the
state is **subsidizing the movement**, and its options reduce to keep paying or burn the asset.

**Azef is the same structure at the top.** Yevno Azef ran the SR Combat Organization while on the Okhrana
payroll; protecting the asset meant letting operations proceed — Plehve 1904, Grand Duke Sergei 1905 — so
asset protection cost the state the lives the asset existed to prevent. He was exposed in 1908 by
journalism (Burtsev) and an SR internal inquiry, not by police error.

**The sharpest reading available: an informant is a cell with its own local maximum.** Its value is
positional access; access requires real work; real work produces real capability for the target; and the
agency owning the asset will protect the target from *other agencies* to protect the asset. The handler
competes with his own colleagues, not only with the movement.

### 2.3 The bureaus hoard, and hoarding is material

Serge's Okhrana is not one organization. The Security Sections and the Department of Police's Special
Section competed with the Corps of Gendarmes and with provincial governors; the Paris station at 1,000
francs/month was a *foreign* station whose product was a claim on the centre's budget. Files were hoarded
because **a file is a title deed to jurisdiction**: whoever holds the informant holds the case, and
whoever holds the case holds the appropriation. Azef's file was Rachkovsky's power base before it was the
Okhrana's.

The carry-over is not psychological. **Information is property, and property generates turf.** A bureau
that shares its map gives away its budget.

### 2.4 February 1917

The Okhrana had files on every revolutionary committee in Petrograd. It did not have a file on the bread
queue.

Rationing was announced; the International Women's Day demonstration on 23 February (O.S.) was *not* an
organizational event and had no committee to infiltrate; the garrison — the repressive reserve — was
itself materially aggrieved (rotation, food, casualties) and began to mutiny on 26 February; the Volynsky
Regiment's refusal turned a crowd into an armed force; the Okhrana and the Corps of Gendarmes were
abolished within weeks.

Serge's conclusion is not "the police were stupid": "the revolution was the outcome of economic,
psychological and moral causes outside their reach," and "Nothing great is achieved without
disinterestedness. And the autocracy had no disinterested supporters." Three separable mechanisms sit in
that sentence, and only the first is a fog problem:

- **No candidate for the unindexed.** The crowd was not a node. If candidates are drawn from the dossier,
  the crowd cannot be ranked, funded or swept.
- **The reserve has its own grievance.** The garrison is a cell; its local maximum was not the
  autocracy's survival.
- **No disinterested defenders.** Legitimacy is not a scalar the state spends; it is the number of people
  who will defend the institution when it costs them something.

The cruel symmetry: **the archive that made the Okhrana formidable is the archive that convicted it.**
Serge read the police's own svodki to write the book. A captured dossier is worth more than a captured
rifle — and the game already has a home for it in the Archive.

---

## 3. RAND and Sparrow: why the agency optimizes its own KPI

### 3.1 Organizational repertoire (Long)

RAND's COIN-organisation research, Long says, "can most accurately be summed up as understanding how to
prevent bureaucracy from 'doing its thing.'" Komer's *Bureaucracy Does Its Thing* (1972) supplies the
mechanism: the U.S. military "carried out its institutional repertoire through firepower-intensive
'search-and-destroy' missions"; State treated Saigon "as if it were any other government"; USAID used "its
normal, peacetime methods"; and "below Presidential level everybody and nobody was responsible." Jenkins'
*The Unchangeable War* (1970) names it from inside: the Army was built for total war in central Europe
and was "unwilling, and to some extent unable, to adapt." Long's prescription — a unified civil-military
council under one senior official — is resisted for a stated reason: "Resistance will be… from
bureaucracies, civilian and military, that have no interest in performing for COIN in a way inconsistent
with their values and practices."

**The agency does not optimize "saving capitalism." It optimizes the reproduction of its own repertoire:**
mission set, training pipeline, promotion ladder, line item. That is how a state loses a war while every
agency performs well. In game terms, an agency's utility must be its **budget renewal**, and renewal must
be a function of the output its repertoire can actually produce. Then "the army does search-and-destroy in
a counterinsurgency" is not a scripted blunder — it is the argmax.

### 3.2 Program-centric machines and the measurement trap (Sparrow)

The 2018 Jerry Lee lecture gives the organizational form. A general class of harm appears; society invents
an agency with a **"general theory of operations"** — "this is how, in general, we will deal with this
broad class" — and builds **"big machines"** that are programmatic, functional or process based. The
alternative is problem-centric: disaggregate the class, study the particular structure, invent a tailored
intervention, "spotting knots, and then unpicking them." The bridge is a **"vigilance mechanism"**: the
methods "you use to discover problems or potential problems that you might not have known about if you
hadn't deliberately looked for them."

*The Character of Harms* explains why the machine cannot report honestly. Overseers want tables that are
aggregate, numerical, comparable over time, "objective," and unambiguously one agency's own contribution.
Agencies can produce that for **outputs**, not **outcomes**, because three questions are unanswerable in
that form: can you prove causality, can you assign credit across functions, can you measure prevention?
*Beyond 911* supplies the case: LAPD Wilshire's crime was falling and response times were excellent —
"these routine accounting measures were the LAPD's — and almost every other major police department's —
key indexes for the performance of its patrol force" — while the captain and his staff "didn't feel nearly
so good." The historical root: the Uniform Crime Reports were "readily adopted, by both police and public,
as the single most important measure of police performance," producing "one of the most distinctive
characteristics of the reform model: its tendency to be incident driven and reactive." **The metric became
the repertoire.**

Two rules follow. (1) The agency reports outputs; only the engine knows outcomes — and the gap must be
*visible to the player as a gap*, never smoothed into a score. (2) It must be possible to raise the metric
without reducing the harm, or the player's correct play is always "make the numbers."

*Informing Enforcement* adds the production side: legibility is manufactured through routine
record-generating interactions — permits, complaints, filings, GIS integration — by "information
craftsmen." *Beyond 911* adds the counter-channel: centralized dispatch severed "the old links of foot
patrol officers to their beats," and with them "the informal networks of friends, acquaintances, and
informers." **Two channels, and the policing mode trades one against the other** — the
Local-PD-versus-Fusion-Center fracture in material form.

### 3.3 Boundary-spanning risk, and why fragmentation is not weakness

Sparrow names the thing the ruling needs: **"boundary-spanning risks — if the responsibility for
controlling a risk sits across multiple agencies,"** with a coordination tax around 0.8× effectiveness
(`coin.md` §3). But the same fragmentation is why the apparatus survives losing any one agency. RAND's
numbers make the point from the other side: of 648 groups ending 1968–2006, **43% politics, 40% policing,
10% victory, 7% military**; in high-income states, 92 of 96 fully-ended groups ended via policing or
politics. The default repertoire is collection, prosecution and co-optation, distributed across agencies
that each own a slice. No single agency can be decapitated into victory.

**The razor: the turf war is simultaneously the exploit and the resilience.** A player who reads the
fractures as "the state is weak" builds on a false premise and loses to the redundancy. A player who reads
them as "the state is *expensive*" can make the competition cost more than the coordination saves. The
object is not to break the state but to raise the price of its own internal settlement.

### 3.4 Local knowledge cannot be centralized (Davis & Cragin)

Root causes are "many, complicated, and subtle. However, they are not the key to either the sustainment of
terrorism or to short- and mid-term counterterrorism"; the actionable factors are proximate — perceived
legitimacy, state repression, lack of opportunity, humiliation, kinship, intimidation, group services.
"Ascent and decline are different": decline tracks the group's own decision calculus, not the resolution
of root causes. On the state's instrument: discriminate force "is difficult when a significant portion of
the population sympathizes… the terrorists can blend in with the population and **good intelligence is
hard to come by**." And on communications, messages should be "built by people with a close understanding
of those particular audiences," which "argues against highly centralized message construction, especially
when driven by American headquarters intuition rather than local knowledge."

**The Fusion Center's higher ceiling is real and insufficient**, because what it collects is
*transmittable* and what the beat officer has is not. That asymmetry is already ADR184 R10: "The state buys
a wide, shallow, standardized view; the movement gets a narrow, deep, untransferable one." The wide view's
product can brief the Mayor and cannot find a safe house.

---

## 4. The design: a Caesarist cellular automaton

### 4.1 What this is not

**Not pluralism.** The agencies do not compete on equal terms in a neutral arena; they compete inside a
constraint set fixed by accumulation. Finance-Capital's decisive power is not its coalition weight, it is
its ability to *withhold* — investment strike, capital flight, bond market — and that is what ends
Bonapartist adventures which threaten accumulation. The competition is real and bounded.

**Not weakness.** Redundancy is the apparatus's resilience (§3.3). The object is cost, not collapse.

**Not a new primitive.** Every quantity below composes from what exists: `Capacity`, `Dossier`,
`exposure`, `Backfire`, `reproduction_capacity`, faction weights. ADR172 r5 and the constitutional compact
forbid adding a mathematical primitive, and nothing here needs one.

### 4.2 The cell

A **cell** is one `ORGANIZATION` or `INSTITUTION` node carrying five declared things:

| Field | Type | Authored? | Meaning |
|---|---|---|---|
| `mandate` | finite set of `(instrument, target_kind)` | content (BSL) | what the cell may legally price |
| `capacity` | `Capacity{owner}` | derived from appropriation | what it can pay for |
| `dossier` | `Dossier{owner}` | derived from resolution channels | what it believes |
| `jurisdiction` | territory nodes via `PRESENCE` | authored | the CA neighbourhood |
| `appropriation` | `{pool_id, share, basis}` | derived from last settlement | why it exists next period |

`mandate` is the **rule-table row** — content, not code. Heterogeneous cells sharing one update rule is
still a cellular automaton in the strict sense: finite state set, local rule, synchronous update,
deterministic. Heterogeneity lives in the transition table, which is exactly where BSL belongs. The
neighbourhood is graph-defined, not metric: `N(c) = PRESENCE territories(c) ∪ agencies sharing ≥1 of those
territories ∪ the institution housing c`. No radius parameter to tune.

### 4.3 The finite state alphabet

Six states, which is what makes this a CA rather than a queue of independent planners:

`DORMANT → WATCHING → CONTESTING → ACTING → OVERSTRETCHED → BURNED`

Transitions read only `(budget_ratio, dossier_novelty, rival_claim_on_same_territory)`. `CONTESTING` means
two cells hold funded candidates on one target; `OVERSTRETCHED` means obligations exceed the appropriation;
`BURNED` means an asset was extracted or an operation failed publicly. The alphabet is small on purpose: a
player must be able to read a cell's state off its behaviour, per the "predictable enough to be exploitable"
goal in `ai/state-ai-algorithm.yaml`.

### 4.4 The local rule (one synchronous update)

```
OBSERVE   L' = reconcile(L, scope) ∪ resolve(N(c), channel set)   // capped by ceiling
PRICE     candidates = { (m, t) ∈ mandate × scope(L') }           // NOTE: drawn FROM L'
          yield(m,t) = decapitation_value(L', scope, edge, t)     // computed on belief
          cost(m,t)  = instrument price from content
RANK      allocate(candidates) → funded[], declined[]             // yield/cost, total order
CLAIM     demonstrated = realized effects of funded[]             // OUTPUTS, not outcomes
```

- **The candidate set is a subset of `L`.** Not "the state probably misses things." Not a probability. A
  structural inclusion. This is February 1917 as a type constraint (§4.6).
- **Yield is a quotient, so distribution is self-defending.** A redundant structure divides its own yield
  and loses the ranking. No "if distributed, skip" rule anywhere.
- **Cheap modes win at equal damage.** `DIVIDE` and `PROPAGANDIZE` are cheapest by state capacity and among
  the most expensive by movement cost, which is why they dominate the record. Arithmetic, not a thumb.
- **Declines are visible.** `AllocationOutcome.declined` carries the shortfall; "wanted the raid, could
  only afford the wiretap" is the pedagogy.

### 4.5 The settlement — where Caesarism comes from

Steps 1–4 are local and synchronous. The **appropriation settlement** is the outer loop, once per fiscal
period, and it is what turns a set of optimizers into a state. Nest the pools to preserve locality:

| Pool | Contenders | Funded by |
|---|---|---|
| Municipal general fund | City PD, Mayor's office, code enforcement, public defender | property + sales tax |
| County levy | Sheriff, jail, prosecutor, court | county levy + state transfers |
| State general fund | State Police, Guard, prison system | state tax + federal pass-through |
| Federal appropriation | FBI field office, Fusion Center grant, task forces | federal budget |
| Corporate | contract security, landlord's agents | profit |

Cross-pool competition (FBI versus City PD) is then a **boundary interaction**, not a global auction —
Sparrow's boundary-spanning risk and Long's interagency problem, recovered as a consequence of fiscal
geography rather than asserted.

Each cell submits `demonstrated`; the pool holder allocates by demonstrated output discounted by a
**verification factor** it cannot fully compute. That discount is the measurement puzzle, and it is where
inflation lives: an agency whose output is unverifiable is paid on its *claim*. Then two derived
quantities:

```
threat_keyed_share(c) = share of c's appropriation whose basis is threat level,
                        not service delivered
autonomy(c)           = threat_keyed_share(c)
                      × reproduction_capacity(c)        // institution-model.rst formula
                      × (1 − max_faction_transfer_share(c))
```

`reproduction_capacity` is already defined (four boolean mechanisms at 70%, budget independence at 30%).
When `autonomy` clears the authored `institution/bonapartist_threshold` (0.4) while no faction weight
clears `bonapartist_exclusion_threshold` (0.35), the cell enters **Bonapartist mode** — the existing
`BonapartistModeEvent` contract in `institution_speckit_prompts_v1.md`, now materially derived instead of a
free-floating float.

**Why crisis produces Bonapartism, derived rather than asserted.** In crisis the pool shrinks (tax base
falls, imperial rent contracts). Service-keyed lines are cut proportionally; threat-keyed lines are not,
because demand for threat rises exactly when the pool falls. `threat_keyed_share` rises mechanically,
`autonomy` rises with it, and the cell whose repertoire is threat production becomes the only solvent one.
**The Caesar is the agency the depression did not defund.** And the discipline that ends it:
Finance-Capital's withholding is a pool-level shock an autonomous security apparatus cannot answer,
because it has no accumulation of its own. Bonapartism is a *form of capitalist rule*, not an escape from
it. A player who helps an agency become autonomous is not breaking the state; they are making it expensive
and brittle, and the brittleness cuts both ways.

### 4.6 February 1917 as a type constraint

```
candidates ⊆ L
```

No agency can price a target it has not resolved. Resolution channels are typed against the node kinds the
apparatus can enumerate — `ORGANIZATION`, `TERRITORY`, `SOCIAL_CLASS`. A mass with no organization node, no
permit, no filing, no denunciation and no territory-level signal above the resolution floor **cannot enter
`L`**, therefore cannot become a candidate, therefore consumes no budget — and the apparatus spends the
period sweeping the chart it already drew.

This gives the player a real strategic resource without magic:

- **Organize in forms the state's categories cannot hold.** A tenant association that is legally a mailing
  list; a congregation; a mutual-aid fund; a workplace committee whose only trace is a shift roster. The
  induced co-projection (`induced.rs`) does not form, so no org↔org adjacency exists to hunt.
- **But the state has one blunt instrument needing no dossier: the garrison.** A territory-level cell can
  act on density alone — expensive, indiscriminate, and **itself a cell with its own grievance**. In
  February the reserve's material condition was worse than the crowd's. Model the Guard with an
  appropriation and a morale term; never as a state attribute.
- **The mirror risk.** Legibility is not monotone in concealment: the Yugoslav CP at 120,000 members with a
  legal-only posture "disappeared from the political scene" in 1921; the Italian CP, semi-legal, survived
  4,000 arrests in a week and grew 10,000 → 30,000; the German CP with a standing illegal apparatus came out
  of von Seeckt's ban "with its forces hardly impaired." Going underground destroys reach.
  **Compartmentalization is a purchase, not a stat.**

### 4.7 The cells

| Cell | Mandate (instruments) | Appropriation basis | Its own local maximum | Failure mode produced |
|---|---|---|---|---|
| **City PD** | patrol, `SURVEIL`, `RAID(TARGETED)`, cite | municipal fund: service + clearance | call volume, clearance rate | incident-driven reactivity; ignores problems that generate no calls |
| **County Sheriff** | warrant service, jail, unincorporated patrol | county levy + per-diem bed revenue | **beds occupied** | prefers custody to resolution; feeds the carceral circuit |
| **State Police** | traffic, task forces, civil disturbance | state fund + federal grants | grant capture, task-force seats | jurisdiction-shopping: appears where the grant is, not the harm |
| **Fusion Center** | analysis, `SURVEIL`, referral brokerage | federal grant | **products produced, referrals brokered** | no arrest authority, so it optimizes for being *read*; inflates threat to renew |
| **FBI field office** | federal `RAID`, `INFILTRATE`, `PROSECUTE`, task forces | federal appropriation | cases **made**; assets protected | protects the informant over the case (Azef); withholds from locals |
| **Prosecutor / Court** | `PROSECUTE`, charge, adjudicate | county/state, conviction-driven | conviction rate, docket clearance | plea pressure; charges chosen for winnability, not harm |
| **Mayor / Council** | `LEGISLATE`, `FUND`, appoint | tax base, re-election | **no agency becomes autonomous** | underfunds coordination precisely because coordination strengthens a rival |
| **Guard** | civil disturbance, disaster | state + federal | its own material condition | unreliable reserve; mutiny is a budget event before a political one |
| **Prison administration** | custody, classification | per-diem + state | bed-days, classification throughput | administrative reclassification replaces legal process (the STG channel) |
| **Corporation** | private police, eviction, hiring | profit | cost minimization | substitutes public police; exports its risk onto the fund |
| **Media / Chamber** | none; influence | advertising / dues | the threat frame | sets what the pool holder believes a threat is |
| **Union local** | the same `allocate`, different replenishment | dues, expropriation | member capacity | included to prove symmetry (ADR184 R3) |

Two features are the whole point. **No cell's local maximum is "public safety."** And **the Mayor's local
maximum is preventing any other cell from becoming autonomous** — so the coordinating actor is structurally
incentivized *not* to coordinate. Long's "everybody and nobody was responsible" is not a bug in the table.
It is the fixed point.

### 4.8 The fractures the player works

| Fracture | Mechanism | Player move |
|---|---|---|
| **Referral dependency** | Fusion Center cannot act; PD owns the street | make the PD's numbers adequate so it has no reason to refer upward |
| **Budget substitution** | a federal case removes the Mayor's need to fund a local task force | hand the feds a case the locals wanted; watch the local unit defund |
| **Asset protection** | an informant's value is positional; burning it ends a career | feed a *known* informant a plausible false plot aimed at a rival's jurisdiction |
| **Metric capture** | outputs are verifiable, outcomes are not | force a public accounting that makes inflation costly for one cell |
| **Jurisdiction overlap** | two cells funding candidates on one target | concentrate visible activity in the overlap: over-policed there, under-policed elsewhere |
| **Repertoire mismatch** | each cell can price only what its mandate holds | hand the state a problem only an agency it distrusts can address |
| **Reserve unreliability** | the Guard is a cell with a grievance | make the reserve's material condition worse than the crowd's |
| **Dossier capture** | a captured `L` is a map of what the state knew *and didn't* | steal the file, learn the blank spaces, organize there |

The last is the Archive's actual use and the proof of §2.4: the svodki that made the Okhrana formidable are
the documents that convicted it.

### 4.9 Determinism, classification, hash

- **Synchronous, single pass, total order.** `allocate` already ranks by `(ratio desc, instrument, mode,
  target, cost, expected_yield)`, so equal inputs give equal funding order. The cell pass must iterate a
  `BTreeMap`-ordered set, never a `HashMap`.
- **Seeded, not sampled.** Resolution rolls take `rng_seed` from the tick; decisions fold into
  `NominalWorldHash` after the detached tick succeeds, per `MaterialReplaySession`. No LLM in the decision
  path (Amendment V/Y).
- **Classification (ADR178 C1).** `mandate`, thresholds and instrument prices are **Designed** or
  **Calibrated**; observation ceilings are **Calibrated** against the literature, never Observed. Any
  historical number — 76 names, 250 volumes, 100 roubles — is a **§6 validation target, never a define.**
- **Loud rejections.** Foreign `actor`, non-positive cost, non-finite yield: hard `GraphError`.
  Unaffordability is the only decline path.

### 4.10 Build order and the failing test

1. **Second owner.** Two `Capacity` instances (PD, FBI) over one `MemoryGraph`, each resolving a different
   subset. Assert the two disagree about which target is worth striking. *ADR184 R10's pinned test extended
   to three actors — the whole design in miniature.*
2. **The pool.** A two-cell settlement with one shrinking pool. Assert `threat_keyed_share` rises with no
   rule saying "raise it."
3. **Bonapartist mode.** Assert `autonomy` crosses 0.4 in a fiscal contraction with no faction weight
   crossing 0.35 — the event fires from arithmetic, not script.
4. **The unindexed mass.** Assert a territory-level spontaneous action generates *no candidate* for any
   agency whose `L` lacks an organization node there, and that the garrison is the only cell that can price
   it.
5. **Only then** the twelve-cell table and the fracture mechanics.

**RED for step 1:** *the PD and the FBI, given different dossiers over the same true graph, rank the same
target first.* If they do, `decapitation_value` is being computed on truth somewhere and the fog is
decorative.

### 4.11 What would falsify this design

- If inter-agency competition produces **no** measurable rise in the cost of a given repression outcome, the
  fracture set is cosmetic and the table should be cut to three cells.
- If Bonapartist mode is reachable **without** a fiscal contraction, there is a hidden coefficient and
  ADR172 r5 has been violated.
- If the player's best response to every fracture is the same move, there is one fracture, not eight.
- If an unindexed mass is never viable — territory-level resolution always catches it first — the February
  mechanism is dead and spontaneity should be deleted rather than faked.

### 4.12 Open questions for the Director

1. **Is the pool the right coupling?** Nested fiscal pools preserve CA locality and recover the
   literature's boundary problem. One global auction is simpler and makes every cell everyone's rival — the
   exchange theory of bureaucracy rather than the fiscal one.
2. **Does the Guard get a morale term, or is that already `Backfire`?** A mutinous reserve is a *loyalty*
   fact; `Backfire` measures the affected population's structure. Different quantities; probably not one
   name.
3. **Can the player hold a `Dossier`?** Dossier capture is the Archive's best use and the sharpest
   expression of §2.4. It also hands the player a model of the state's blind spots — a very strong object.
   Library or weapon?
4. **What is the unit of settlement?** A tick is a week; appropriations are annual. The fiscal period must be
   a declared multiple or the competition runs at the wrong tempo.

---

## 5. Summary

The state is not a monolith and never was. It is a set of cells, each ranking a finite set of priced actions
against a partial file, each paid for what it can show, each competing for a pool that shrinks in exactly
the crisis when threat is the only growth market. Bonapartism is what that arithmetic produces when no
fraction can pay for the state out of its own share. February 1917 is what it produces when the crowd has
no file.

None of this is asserted. The candidate set is drawn from the dossier, so the blind spot is a type
constraint. Yield is a quotient, so distributed organization defends itself. Appropriation is threat-keyed
or service-keyed, so autonomy is a fiscal derivative. The player's object is not to break the state but to
make its internal settlement expensive — and the state's answer is not unity but redundancy, which is why
it survives losing any one agency and why the price is the only lever that works.

The Okhrana drew the best network chart in Russia and lost to a bread queue. That is not a story about
police incompetence. It is the specification for the enemy.

---

## Sources

Serge (1926), preface and ch. 2–3 verbatim; ch. 1a/1b/4 via `reports/heat-system-dossier.md` §1.1, §4
(primary-verified 2026-07-30). Sparrow, *Beyond 911* (1990) ch. 1, 4–5; *The Character of Harms* (2008)
ch. 2, 5–6; *Informatization and the Public Sector* 2 (1992); *Social Networks* 13 (1991) 251–274; *IJIC*
5:3 (1992) 259–273 (scanned); *Crime Science* 7:14 (2018). Long, MG-482 (2006) ch. 3–5, citing Komer
(1972) and Jenkins (1970). Davis & Cragin (2009) summary and the decline and communications chapters.
Paul, Clarke & Grill (2010) summary. Jones & Libicki (2008) summary, ch. 2. Repo:
`ai/decisions/{ADR172,ADR178,ADR184}`, `ai/spec-prompts/enemy-ai/036-state-verb-system.md`,
`ai/spec-prompts/institution_speckit_prompts_v1.md`, `ai/epochs/epoch3/repression-logic.yaml` §3,
`docs/concepts/institution-model.rst`, `docs/reference/organizations.rst`,
`reports/heat-system-dossier.md`, `rust/crates/babylon-graph/src/{capacity,dossier,exposure,backfire,induced}.rs`.
