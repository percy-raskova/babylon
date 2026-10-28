<!-- vale off -->
<!-- Research briefing: dated evidence with literal identifiers preserved. Not governed prose. Same disposition as project/README.md. -->

# 22 — Gap 3: The Carceral Pipeline, Prison Organizing, the Yard Hazards, and Prison Solidarity

Read-only design and theory briefing, 2026-10-25. **Gap 3** of the porch series.

The question: when City PD, the County Sheriff or the FBI takes your cadres, what
happens on the board? The inherited answer is a decrement — `CL -= 1`, the unit
leaves the map. The Director's answer is the opposite:

> "Prison isn't a death sentence. You can organize in the prisons! You can also
> get merked by Nazi gangs or fall into drugs etc. or breed traitors. Prison
> solidarity is key."

Both halves of that sentence are mechanics, and they are the *same* mechanic seen
from two sides. A prison removes a person from your street roster and deposits him
in the densest concentration of lumpenproletariat in the county, under the total
administrative control of an agency whose budget rises when the yard is violent.
It is simultaneously the safest place to be a revolutionary (you cannot be
arrested twice) and the cheapest place to kill one (a yard stabbing is an
"inmate-on-inmate incident"; nobody files a report).

This briefing grounds the pipeline and the yard in George Jackson, MIM(Prisons) and
the UFPP, Victor Serge's *What Everyone Should Know About Repression*, the Attica
and Pelican Bay peace initiatives, and the corpus's own account of Lenin in
Siberian exile; specifies the deterministic state machine against the shipped Rust
surfaces (`territory.bsl`, `control-ratio.bsl`, `babylon-graph::capacity`,
`babylon-graph::exposure`, the 34-slot phase registry, the practice-intent
allowlist); prices the four yard hazards as `PrisonAdmin`'s funded candidates
rather than as dice; and derives the prison solidarity pact as five attacks on five
revenue lines.

Everything below is game design. No Rust, no Python, no commits.

---

## 0. The one-page answer

1. **Arrest is not a decrement, it is a move.** A person transfers between rosters.
   The conserved object is the person; the changed object is *where he is and who
   administers him*. The corpus already has this exact idiom shipped:
   `decomposition/p04-enforcer-intake` and `p05-ip-intake` move population and
   wealth between class nodes instead of deleting it. **Arrest is decomposition at
   household granularity.**

2. **The pipeline has five named custody states and four gates, and each gate is
   somebody's budget.** `STREET → LOCKUP → CHARGED → PRISON → RELEASE`. Bail is a
   money gate. Charging is an electoral gate. Intake assignment is an
   administrative gate. Parole is an electoral gate. The player never fights "the
   carceral state"; the player fights *a specific agency's line item*.

3. **Confinement is a relation, not a role.** There is no `PRISONER` member in
   `SocialRole` and there must never be one. A confined person keeps
   `INTERNAL_PROLETARIAT` or `LUMPENPROLETARIAT`; he acquires a `TENANCY` edge to a
   `PRISON` node. Class position is not suspended by a lock.

4. **A `PRISON` node is a facility with a custody register, not a `PENAL_COLONY`
   sink.** The ported `territory/p4-penal-suppression` ("every class tenant of a
   penal colony has its organization zeroed") is the *displacement-sink* mechanic
   and stays exactly as written. Reusing it for a named prison would make
   organization a per-tick flow and blind `control-ratio/c04-terminal`. The prison
   gets its own node kind and its own atomization *events*.

5. **The four hazards are one identity.** `PrisonAdmin`'s budget is
   $\pi N_{\text{occupied}} + \gamma A + \omega W$ — per-diem times beds, plus a
   control-unit increment that rises with measured yard violence, plus the
   appropriation that pays the guard local. Therefore
   $\partial B/\partial A = \gamma > 0$: **the prison's business model is the race
   war.** Every hazard below is that partial derivative wearing a different mask,
   and a prisoner's own 2006 account of the failed Pelican Bay peace talks says so
   in plain words.

6. **The hazards are `Capacity::allocate` calls, not random events.** A gang stabs
   the cadre with the highest `decapitation_value` it can afford at
   `cost = p_shiv` until its budget runs out. Assaults per period is
   $\min(\lfloor B_{\text{gang}}/p_{\text{shiv}} \rfloor, \#\text{unprotected
   cadre})$. No sigmoid, no heat score, no saving throw.

7. **Defence is a count of people, not a modifier.** An attack on cadre $c$
   succeeds iff $\text{force}(A,c) \ge \text{defence}(c)$ where
   $\text{defence}(c)$ is the number of pact-covered prisoners standing in the same
   yard. Nothing happens to a man with forty friends. This is the whole of "prison
   solidarity is key," and it is arithmetic rather than sentiment.

8. **The pact is five planks, each earned by a world-fact, never purchased.**
   PEACE (a period with zero yard homicides across two previously hostile
   contingents), UNITY (a verified exposure of a planted rumour or snitch), GROWTH
   (a study cell that produced cadre while honouring the right to leave),
   INTERNATIONALISM (two national contingents in one study cell), INDEPENDENCE (a
   period with zero goods received from the administration). No tech tree. No cost.

9. **The pact is a floor, not a ceiling.** It buys *peace*, which is a commons, and
   the player needs *cadre*, which is not. Converting one into the other requires
   the study cell, and the study cell requires your line — at which point the
   united front's other contingents may lawfully leave (GROWTH plank), and the
   prison splits along the oldest line in the corpus: peace-and-education versus
   politics.

10. **The pact fails without an outside line, and the corpus documents the
    failure.** In 2006 Pelican Bay prisoners initiated peace talks and lost, in the
    initiator's own words, because "we did not have any grassroots community
    support, which remains to be a critical component." In 2011–2013 the same
    demand held, because by then there was an outside movement. **That difference
    is a variable in the model: `prison/legal-line`.**

11. **Time is the resource prison actually consumes.** A sentence is 40–260
    periods; the SPD calcification clock is 260 periods. A cadre sentenced in
    period 40 and released in period 300 outlives the Party. Prison is where the
    strategic clock becomes visible on one man's face.

12. **The player never sees a probability.** He sees a kite in a bad hand, a legal
    visit report with two sentences redacted, a Corporate Feed headline about a
    bed expansion "following a disturbance," and twelve hours taken out of a
    household's week for a bus to Chippewa.

---

## 1. Theoretical and historical grounding

### 1.1 George Jackson: the prison is the front, and the lumpen is the base

The corpus carries a prisoner's own essay on Jackson
(`/media/user/data/mim/textonly/agitation/prisons/essays/the.dragon.html`,
August 2005), and it states the material facts the design needs:

- Jackson was **eighteen** at sentencing, on "a gas station robbery in which
  seventy dollars was stolen," and got **one year to life** — the indeterminate
  sentence. He served "nearly half of his life" and "seven years in solitary
  confinement."
- "In 1971 more than 50 percent of prisoners were black; that was five times the
  population ratio of Afro-Amerikans in this country at that time."
- "He showed them how Amerika's prisons were full of poor minorities… He
  organized and educated them around demands for prison reform. He simultaneously
  showed them that in the end prisons could not be changed. Change could only come
  from a full-scale revolution."

The same corpus preserves Jackson's line, quoted by a New York prisoner in *Under
Lock & Key*: "a person that takes the civil exam today can kill me tomorrow and a
person that took the civil exam yesterday can kill me today"
(`ulk/ulk/ulk105.html`). That is `PrisonAdmin`'s staffing model in one sentence:
**the guard is not a villain, he is a shift-worker with a grievance and a
truncheon**, and the same man is your neighbour on Tuesday. It is also why the
guard local is a legitimate target of division tactics and not a monolith.

MIM(Prisons)' `FPLmimp.pdf` states the strategic claim directly: "the U.$. prison
system is a major part of the imperialist state used to prevent the
self-determination of oppressed nations… we see prisoners in this country as being
at the forefront of any anti-imperialist and revolutionary movement," and the
one-liner that governs this whole feature: **"all prisoners are political
prisoners because all imprisonment under imperialism is political."**

**Design consequence.** The lumpen is the base and is not romanticised. MIM's own
formulation is that the First World lumpen is "parasitic on the petty bourgeoisie"
and available because "nothing to lose," and that "You can't sell dope forever" is
a *structural* argument, not a moral one. So the prison is not a recruitment
bonanza. It is the one place where the parasitic stratum is (a) physically
assembled, (b) unable to leave, and (c) has no wage relation to defend. That is
precisely the condition under which the "parasitic" character can be *transformed
by institution* rather than exhorted away.

### 1.2 MIM(Prisons) and the UFPP: peace as a product with five enforceable planks

`FPLmimp.pdf` prints the **United Front for Peace in Prisons — Statement of
Principles** in full, and the framing sentence is the mechanic:

> "The basis of any real unity comes from an agreement on certain key ideas. This
> statement does not grant authority to any party over any other party. We are
> mutually accountable to each other to uphold these points in order to remain
> active participants in this united front."

The five planks, verbatim in substance:

1. **PEACE** — "organize to end the needless conflicts and violence within the
   U.$. prison environment. The oppressors use divide-and-conquer strategies so
   that we fight each other instead of them."
2. **UNITY** — "keep an open line of networking and communication, and ensure we
   address any situation with true facts… because of how the pigs utilize tactics
   such as rumours, snitches and fake communications."
3. **GROWTH** — "education and freedom to grow… We support members within our
   organization who leave and embrace other political organizations… Similarly, we
   recognize the right of comrades to leave."
4. **INTERNATIONALISM** — "We cannot liberate ourselves when participating in the
   oppression of other nations."
5. **INDEPENDENCE** — "We build our own institutions and programs independent of
   the United $tates government and all its branches, right down to the local
   police."

And the membership test, which is the sharpest implementable sentence in the
corpus (research/06 §7(iii)): **"Members don't have to agree with MIM(Prisons)'s
cardinal points… but they can't consciously disagree with any of them."**

**Design consequence.** Each plank names a *specific enemy tactic* in its own text.
PEACE names divide-and-conquer. UNITY names rumours and snitches. GROWTH names
immobility and the closed cadre. INTERNATIONALISM names chauvinism. INDEPENDENCE
names dependency on the administration. That is not a value list; it is a
**counter-table**, and it maps one-to-one onto the four hazards in §4. The corpus
wrote the tech tree; the designer's job is only to price it.

### 1.3 Victor Serge: the arrest is an epistemic event, and "say nothing" is a rule

`archive/serge/1926/repression/` has the author's preface and chapters 2 and 3 of
*What Everyone Should Know About Repression* (1926). It is the corpus's best
statement of what the *player* loses at the moment of arrest — not men, but
**information about his own organization.**

Chapter 3, "Simple advice to revolutionaries," is a procedure:

- "As a matter of principle: **say nothing**." "Explaining yourself is dangerous;
  you are in the hands of professionals able to get something out of your every
  word." And the old rule the papers printed in large type: "Comrades, make no
  statements! Say nothing!"
- "Lying is extremely dangerous: it is difficult to construct a story without its
  defects being too obvious."
- "Don't let yourself be surprised or disconcerted by the classic: 'We know
  everything!' **This is never the case.** It is a barefaced trick."
- "Don't believe a word of another classic ploy: 'We know everything because your
  Comrade So and So has talked!'… Even if So and So did 'tell all', this is a
  further reason to be doubly circumspect."
- Correspondence: "take into account that your mail will be opened… Don't say, for
  example: 'Comrade Peter has been arrested,' but 'Uncle P. has suddenly fallen
  ill.'" And on prisons: "Old jailbirds write this strong recommendation on prison
  walls, for the revolutionary to learn from: **'Never confess!'**"

And the strategic frame from the preface: "the immediate aim of the police is more
to **know** than to repress. To know in order to repress at the appointed hour, to
the extent desired." Plus Serge's own warning against the opposite error — a
"disdain for legal action" born of "a kind of tendency to make the least political
effort (it is easier to conspire than to lead mass action)."

**Design consequences, three.**

(a) The thing an arrest removes is *knowledge security*, and the thing a confession
buys the state is a *case*. A cadre who says nothing is not merely brave; he is
**worthless to buy**, because there is nothing to purchase. That converts Hazard C
from a loyalty check into a price.

(b) The mail is opened. Every kite is a document the admin may read, so prison
communication has a *censorship cost per route*, and the routes are countable
(legal mail, family visit, books programme, lawyer, released comrade).

(c) Serge's anti-legalist warning is the guardrail on the whole feature. The prison
is not a legal mini-game and "jailbreak" is not a verb. The corpus position is
unambiguous: MIM(P) explicitly refuses premature armed struggle in the core, and the
`research/06` fiche calls the alternative "never more than a flash of fury."

### 1.4 Attica 1971: the pact and its price

The local corpus gives Attica as a *fact in the background* rather than a history:
`aa/articles/prisonboom.txt` (MIM, 1999) says that "this contradiction between
oppressed nationals from the cities and their white captors was part of the
background to the Attica rebellion in upper NY State in 1971," and the MIM archive
preserves a flyer for **Big Black (Frank Smith)**, "an inmate at Attica
Correctional Facility… during the early 1970s. He was a leader of prisoners and
worked to raise the political consciousness of prisoners both before and during the
Attica rebellion" (`atticatalk.html`, `aa/old/januaryevents.html`).

The standard historiography (from recall, not from this corpus — flagged in §10):
September 9–13, 1971; roughly 1,300 prisoners hold the yard and 42 hostages;
the demands include amnesty for the uprising and safe passage; Rockefeller orders
the retake; 39 die, 29 of them prisoners, and the autopsy record shows the dead were
killed by state fire, not by the hostages' captors.

**Design consequence.** Attica is the design's ceiling and its warning. It proves
that a united yard can take a prison in an afternoon, and that the state will kill
the united yard rather than negotiate with it. Therefore:

- A yard takeover is legal as an `OCCUPATION` intent on a `FACILITY`/`TERRITORY`
  (already in the allowlist) and it has a **political shock value that is the
  highest in the game and an exterior line value of zero** — porch-02's own
  characterisation: "Prisons (Attica / MIM(P) UFPP): Highest political shock, zero
  exterior line — crushable by one all-out assault."
- It is never a win condition. It is a *forced move* that the player uses when the
  alternative is worse, and its price is paid in dead cadre that no hash can
  restore.

### 1.5 Pelican Bay 2006 → 2011–2013: why one peace failed and one held

This is the single most important empirical pair for the design, and the corpus
holds the *failure* in a participant's own voice.

`agitation/prisons/campaigns/ca/history.peace.summit.html` — a California prisoner,
October 2006, on the Pelican Bay Peace Summit initiative:

> "Back in the year 2000, we the progressive class of Black prisoners had initiated
> efforts through these prison bureaucrats, in order to initiate some peace/resolve
> to the social conflict that had materialized out in general population, i.e.
> 'race war.' But as to be expected, these prison bureaucrats launched an aggressive
> 'armed propaganda' campaign, in order to sabotage and disrupt our efforts."
> The bureaucrats told Sacramento that the peace delegates "were manipulating this
> opportunity to organize and conspire in criminal and violent activities, which is
> completely false and unfounded!"
> "But by the time that we got around to challenging this nonsense, our efforts had
> proven to be futile, as we did not have any grassroots community support, which
> remains to be a critical component."

And the economic motive, stated by the prisoner without any theoretical vocabulary:

> "these fascist pigs in here also had a vested economic interest in seeing that the
> cycle of violence remained a material factor… if our collective goal towards peace
> had been materialized into a reality, then the fascist pigs would no longer been
> able to prey on the fears of the public, under the premise of violence being a out
> of control issue, and **the justification for the continued existence of these
> super-maximum slave kamps would have also been negated**."

That paragraph is $\partial B/\partial A > 0$ written by a man in a cell. It is the
design's licence to make the admin's budget a function of yard violence without
inventing a villain.

The 2011–2013 counterpart (standard published history, flagged in §10): the
*Agreement to End Hostilities*, negotiated among the recognized leaders of the
major California prison organizations while all of them were held in Pelican Bay's
SHU; the 2011 and 2013 mass hunger strikes against the gang-validation/SHU regime,
with the 2013 action reported as the largest in California history; and the
*Ashker v. Governor* settlement of 2015 ending indeterminate SHU. The accepted
reading of the pair is that the 2006 attempt had no outside line and the 2011–2013
attempt did.

**Design consequence, and it is the load-bearing variable of this whole feature.**
The difference between a peace that dies and a peace that holds is **not** the
sincerity of the prisoners, the size of the yard, or the eloquence of the appeal. It
is whether an outside organization existed to (1) make the reprisal expensive, and
(2) replace an isolated initiator. The model therefore needs `prison/legal-line` as
a first-class quantity, and the player's prison strategy is fundamentally a
*logistics* strategy: **you are not organizing the yard, you are keeping a line
open to it.**

### 1.6 Lenin in Shushenskoye: exile as cadre school, from the corpus's own file

`archive/krupskaya/works/rol/rol02.htm` ("Reminiscences of Lenin — In Exile")
contains the exact mechanic, in a domestic register:

- Lenin arrives at Shushenskoye; the cottage is small and spotless; he is out
  hunting when Krupskaya arrives.
- A deported worker, **Oscar**, "a young man, who had been deported for taking part
  in a strike and behaving violently in the course of it. He had read a lot of
  all-sorts, but had only the faintest of ideas about socialism." He returns from
  the volost saying "A new clerk has arrived — he and I have the same convictions."
  "Meaning?" — "**We are both against revolution.**"
  "Vladimir Ilyich and I were just flabbergasted. The next day I sat down with him
  to study *The Communist Manifesto* (I had to translate it from the German), and
  when that was mastered, we passed on to…"

That is a study cell in a prison node, run by two cadre, with one receptive lumpen,
and a book that had to be translated because there was no supply chain. It is also
the answer to "why does the player's line matter inside the wire": Oscar was not
won by sympathy; he was won by a curriculum.

The same chapter supplies the attrition baseline: Kurnatovsky, "exile after exile,
prison after prison… after a month or two of freedom he would be snatched back
again for long terms. He never had any real life." And the two Decembrists "soon
put out of action — Zaporozhets, who went mad in prison, and Vaneyev, who died from
an illness contracted there."

**Design consequence.** Three inputs, one output: teachers, material, receptive
students. And a fourth, silent input: **survival**, because the admin can simply
hold a man until he is no longer the man you sent in.

### 1.7 What the state believes: the frozen `carceral-geography.yaml` is the guard's model, not the physics

`ai/epochs/epoch1/carceral-geography.yaml` (v1.1.0, "status: implemented", sprint
3.7.1) defines `TerritoryType.PENAL_COLONY` with
`organization_effect: "set to 0.0 for connected SocialClass nodes"`, and
`_suppress_organization` operating over `TENANCY` edges. That specification is now
executable Rust, verbatim:

```
(rule territory/p4-penal-suppression
  :role mechanic
  :evidence derived
  :material-basis "atomization via incarceration: every class tenant of a penal
    colony has its organization zeroed (territory.py:349-378)"
  (when (= ttype TerritoryType/PENAL_COLONY))
  (effects
    (for-each (neighbors self EdgeType/TENANCY :in NodeType/SOCIAL_CLASS)
      (update-node it social-class/organization (set 0)))))
```

Note what this rule *is*. It encodes the prison's **claim about itself** — "we
atomize them" — as a law of physics. Under it, prison solidarity is not merely
difficult; it is *unrepresentable*. The organization number is zero by fiat and
there is nothing to contest.

The design move of this briefing is therefore not an addition but a **relocation of
the same claim from the physics to the antagonist**:

> Atomization is what the administration *achieves*, at intake and at each
> disciplinary shock. It is not what a prison *is*. The delta between the
> administration's suppression and the collective's reconstitution is the game.

This is dialectically correct (the guard's model is one-sided; the yard is a
contradiction), and it is mechanically necessary (a zeroed stock cannot be
organized, and the control-ratio terminal branch already reads that stock).

**And it costs nothing in receremony.** `territory/p4-penal-suppression` stays
exactly as shipped, because a `PRISON` facility is not a `PENAL_COLONY` sink (see
§3.1). The ported rule keeps its meaning for the displacement pipeline; the prison
gets new rules in a later slot.

---

## 2. The board: one conserved flow of persons through five custody states

### 2.1 The state machine

```
                       ┌──────────────────────────── GATE 1: arrest (CUSTODY budget)
                       │                            ┌── County Sheriff (jail beds, per-diem)
   STREET ─────────────┤                            ├── City PD (clearance rate)
   (class node,        │                            └── FBI (dossier, high-value target)
    ORGANIZATION)      ▼
                     LOCKUP ────────── GATE 2a: bail (Money, player) ──────────────► STREET
                     (county jail)  ── GATE 2b: charge/dismiss (DA, electoral) ───► RELEASED
                          │
                          │ GATE 3: sentencing (judge; DA's charging policy)
                          ▼
                      PRISON ──┬── GENERAL POP ◄──► SHU (isolation shock)
                     (facility)│
                          │    ├── GATE 4a: release (parole board, electoral) ──► STREET
                          │    ├── GATE 4b: transfer out (DOC contract) ────────► ANOTHER PRISON
                          │    ├── GATE 4c: death (yard, medical neglect, age)
                          │    └── GATE 4d: liberation (terminal branch only)
                          ▼
                       (person is conserved across every arrow except death)
```

Named states, not hit-point bars (Debord's rule, porch-02 §3). Each arrow is owned
by an agency with a budget, and each agency's budget is legible in the Ticker.

### 2.2 Gate 1 — arrest is a mini-decomposition

The shipped decomposition pack already contains the exact transfer idiom:

```
p04-enforcer-intake   SOCIAL_CLASS  reads fire-tick, gain fields  → population/wealth ADD, active:=1
p05-ip-intake         SOCIAL_CLASS  reads fire-tick, ip fields    → population/wealth SET, active:=1
p06-la-deactivate     SOCIAL_CLASS  reads fire-tick, amounts       → active := 0
```

Three rules, one class split into two fractions and deactivated. **Arrest has the
same shape at a different granularity**: a slice of a street class node's population
`active := 0` on the street node and an additive intake on a new confined node.

**Which slice?** Not a rate. The state arrests where `decapitation_value` is
highest, because that is what `babylon-graph::capacity` computes: a `Candidate`'s
`expected_yield` is "normally `decapitation_value` over a dossier scope," and the
allocator funds down the list by yield per unit spent until the money runs out.
`decapitation_value(target) = removal_differential(target) / signature_class_size(target, hops)`.

Two consequences fall out for free, and both are already documented in
`capacity.rs`/`exposure.rs`:

- **A distributed organization resists arrest without a "resist arrest" mechanic.**
  A ring has a low removal differential, so a raid on any one node ranks low, so
  the agency funds something else. The player does not buy a modifier; he changes
  the shape of his graph.
- **The bureau arrests the organizer before the member.** The organizer has the
  high differential. This is the correct, cruel result, and it means the *first*
  arrest of a campaign is usually the most expensive one.

**Arrest count, deterministically:**
$$A_t = \min\left(\left\lfloor \frac{B_{\text{custody},t}}{c_{\text{arrest}}}\right\rfloor,\ \text{street cadre at the targeted node}\right)$$
funded in descending `decapitation_value` within the agency's dossier $L_c$. The
agency's dossier is partial and sometimes wrong (porch-02 §3: "the dossier lies
with a straight face"), so an arrest can land on the wrong node, or on a member
rather than the organizer, or on nobody.

**And the arrest is where knowledge is lost.** The player learns the shape of the
raid only from what did *not* happen afterward (Serge: the police "know in order to
repress at the appointed hour"). This is the knowledge system's `observed_period`
vs `acquired_period` distinction used as drama, not bookkeeping (porch-01).

### 2.3 Gate 2 — lockup, bail, and the DA

**Lockup** is the county jail, and the county jail is a *revenue* institution
before it is a punitive one: porch-02 §3 gives the Sheriff's local objective as
"optimizes occupied jail beds (per-diem revenue)." The Michigan reference data
(§2.4) confirms the shape: 109 local jail facilities across 79 counties, 16,686
beds — the lockup is *everywhere*, within driving distance of every family.

**Bail is a receivable, not an expense.** This matters and it is a real design
distinction:

- Cash bail is a deposit. The org's cash moves to the court's account as a
  *refundable claim*, and returns on appearance. `babylon-material-circuit` already
  has the payable/receivable pair shape (`WageAccrualReceipt` is "a
  payable/receivable pair, without a cash movement or a claim about new value").
- The **non-refundable** cost is the bond premium (the 10% to the bondsman) and,
  catastrophically, **forfeiture** if the cadre absconds. Forfeiture is the only
  way bail becomes an expense, and it happens exactly when the cadre is *guilty of
  the thing the state alleged* — or when the org has lost control of him.

The mechanic: **posting bail is cheap if you are right and ruinous if you are
wrong.** That is a Decision Ceremony (§7.4), not a purchase.

The bail bondsman is an `ORGANIZATION` node with a `FISCAL` instrument, and it is a
target of division tactics like any other: he is also the man who profits from the
county's pretrial detention rate.

**Charging is the electoral gate.** The porch already approved the office verb:
`Bail/Pardon/Charging` [DA/Sheriff races]. A captured DA's office can decline to
charge, divert, or set bail at zero; it cannot free the already-sentenced. The
asymmetry is the point: **electoral power reaches the front of the pipeline and not
the back**, which is exactly the lesson the DSA character must learn the hard way
(porch-02 §4, the five material barriers).

### 2.4 Gate 3 — the rural prison node, with the real numbers

The user's mandate names the geography: "extracting urban captive nations to fund
rural white prison-guard towns." That is not a rhetorical flourish; it is in the
reference database, county by county.

`/media/user/data/babylon-data/sqlite/marxist-data-3NF.sqlite`, table
`fact_coercive_infrastructure` (3,867 rows; keys `county_id`, `coercive_type_id`,
`source_id`, with `facility_count` and `total_capacity`), joined to
`dim_coercive_type` (`prison_federal`, `prison_state`, `prison_local`,
`prison_private`, `prison_tribal`, `prison_other`, plus eight `military_*`). For
Michigan:

| Carceral type | Facilities | Counties | Capacity |
|---|---|---|---|
| Local Jail/Detention | 109 | **79** | 16,686 |
| State Prison | 31 | **21** | 12,376 |
| Other Correctional | 4 | 4 | 1,030 |
| Federal Prison | 1 | 1 | — |

The state-prison counties, by capacity:

| County | Facilities | Capacity |
|---|---|---|
| Chippewa | 2 | 3,870 |
| Gratiot | 2 | 2,560 |
| Montcalm | 1 | 2,256 |
| Muskegon | 2 | 1,853 |
| Jackson | 4 | 1,752 |
| Ionia | 3 | — |
| Washtenaw | 3 | — |
| … 14 more, incl. Alger, Baraga, Crawford, Delta, Luce, Manistee, Marquette | 1 each | — |

And Wayne County — Detroit, the Black Belt node, the arrest engine — holds
**4 local jails with 1,860 beds and exactly one state prison**.

Read the two tables together and the pipeline is not a metaphor:

- **The lockup is distributed to 79 of 83 counties.** Every family can reach a
  jail.
- **The sentence is concentrated in 21 counties, and the three largest of them
  have no city in them at all.** Chippewa, Gratiot and Montcalm hold 8,686 beds
  between them; Muskegon and Jackson are small industrial towns with their own
  prison histories, not Detroit. A Detroit cadre sentenced to Chippewa is 400 miles
  and roughly six hours by road from his mother, one way. A visit is a twelve-hour
  round trip that consumes a household's week (§6.3).
- **The beds flow toward the empty counties.** Chippewa holds 3,870 prison beds;
  Wayne holds 1,860 jail beds for a population two orders of magnitude larger.

That is the "two-sided map event" of `research/06` P7 (−oppressed-nation safety,
+local white employment, +budget, from the same hex), and it is measurable from the
repo's own database rather than asserted.

**Limits of the data, stated plainly.** `fact_coercive_infrastructure` contains no
police agencies at all — `dim_coercive_type` has zero rows with
`category = 'enforcement'`, so City PD, Sheriff patrol and the FBI are *not* in
this table. The carceral half of the coercive apparatus is empirical here; the
enforcement half is not. Any PRISON node's `beds` is Observed; any PD's `sworn` is
not, and must be labelled Designed or Calibrated until a source lands.

### 2.5 Gate 4 — the yard: what the node is made of

A `PRISON` node holds, as graph structure:

```
                 ┌──────────────────────────────┐
                 │  PRISON (NodeType/PRISON)    │  facility + custody register
                 │  seats in a county (H3)      │
                 └───┬────────┬────────┬────────┘
        TENANCY :in  │        │        │  TENANCY :in
        ┌────────────┘        │        └──────────────┐
        ▼                     ▼                       ▼
  SOCIAL_CLASS          SOCIAL_CLASS            SOCIAL_CLASS
  role=LUMPEN           role=INTERNAL_          role=CARCERAL_
  population=N₁         PROLETARIAT             ENFORCER
  organization=o₁       population=N₂           population=G
                        organization=o₂

  edges out of the prison node:
    COORDINATION → PRISON_ADMIN      (ORGANIZATION, OrgKind/STATE_APPARATUS)
    COORDINATION → GUARD_LOCAL       (ORGANIZATION, the union: a CIVIL_SOCIETY org)
    COORDINATION → COUNTY_SHERIFF    (ORGANIZATION; the division target)
    MEMBERSHIP   → PRISON_CHAPTER    (ORGANIZATION: your people, or the UFPP chapter)
    ADJACENCY    → PRISON_TOWN       (TERRITORY: the county seat that lives off the wage bill)
```

Why this shape and not "prison is an INSTITUTION carrier":

- `control-ratio/c01` already computes per-`SOCIAL_CLASS` census contributions and
  `c02` folds them onto a single carrier. That works for a *global* guard:prisoner
  ratio. It cannot tell you *which* yard is a powder keg.
- A `PRISON` node with `TENANCY` in-neighbours lets the same fold run **locally**:
  one prison's census is a fold over its own tenants. That is the same query form
  (`(neighbors self EdgeType/TENANCY :in NodeType/SOCIAL_CLASS)`) that
  `territory/p4-penal-suppression` already uses, so it is proven syntax.
- And it gives the prison its own `ORGANIZATION` members, which is where the
  chapter, the pact and the informant live.

### 2.6 Gate 5 — four exits, and one of them is a lie

| Exit | Condition | Graph effect | What the player sees |
|---|---|---|---|
| **Release** | `prison/sentence-remaining = 0`, parole granted | population ADD to the home street class node, `active := 1` | a bus ticket, a name on a roster, a period-late letter |
| **Transfer out** | admin funds a `TRANSFER` mode (cheaper than a control unit) | population moves to another `PRISON` node, chapter edges severed | mail starts bouncing; the kite stops |
| **Death** | hazard resolution (§4) or age/medical | the only true decrement | a Corporate Feed line: "pronounced dead at 4:12 a.m." |
| **Liberation** | the reserved terminal branch only | `TERMINAL_DECISION` = REVOLUTION | the gate opens, once, at the end of the world |

The transfer deserves emphasis because it is the corpus's own current event:
`aa/articles/prisonboom.txt` documents Michigan shipping prisoners to a CCA
facility in Oklahoma and to West Virginia, "under threat of being messed up with the
parole board," and a state law (MCL 791.211.83) requiring volunteer transfers being
quietly rewritten to make it legal. **A transfer is a cheaper control unit**: it
severs the chapter, punishes the organizer, and books per-diem revenue in another
county. It is `PrisonAdmin`'s second-cheapest mode after censorship.

The player's counter is already designed as an office verb: `NON_COOPERATION`
[sanctuary/**carceral freeze**] on the Electoral screen. That is the only verb in
the game that attacks a transfer contract, and it is exactly the kind of thing a
county commission can actually do.

---

## 3. The prison node's internal register

### 3.1 Vocabulary: what is new, and what is not

**New, and vocabulary only (no amendment; Article IX: "New governed content
vocabulary does not need an amendment when it uses the current mathematics"):**

- `NodeType` member `PRISON` — added through the normal scenario/vocabulary path,
  i.e. `(defvocabulary NodeType (SOCIAL_CLASS TERRITORY ORGANIZATION … PRISON))`,
  following `content/scenarios/organization-practice-contract.bscn`'s existing form.
  Requires the ADR + schema + conformance ceremony that any new governed vocabulary
  takes, and nothing more.
- `defenum PrisonSecurity (MINIMUM MEDIUM CLOSE MAXIMUM)`.
- `defenum CustodyState (STREET LOCKUP CHARGED PRISON RELEASED TRANSFERRED DEAD LIBERATED)`.
- New `deffield`s, listed in §3.2.

**Not new, and must not be invented:**

- No `PRISONER` member of `SocialRole`. Confinement is a relation.
- No `PRISON_ORGANIZE` practice. The contract's `practice_ids` is a closed u8 set of
  nine verbs, `target_allowlists` are exact, and `other_practices: empty_only`. The
  existing verbs already reach a prison (§3.4).
- No `jailbreak` verb, and no plan to add one. It is not on the allowlist, and the
  refusal is the design (Serge's warning; `research/06`'s "flash of fury").
- No new intrinsic. The kernel table is `floor`, `{exp, log}`, and the ADR219
  sextet `sqrt`/`round-half-even`/`min`/`max`/`abs`/`clamp`. Every quantity below is
  composed from `fold sum`/`count`/`min`/`max` over node fields and the four
  arithmetic operators.

### 3.2 Fields, with provenance

**On the `PRISON` node (facility register):**

| Field | Type | Written by | Class |
|---|---|---|---|
| `prison/beds` | int extensive | scenario seed (from `fact_coercive_infrastructure.total_capacity`) | **Observed** |
| `prison/operator` | enum `{STATE, FEDERAL, PRIVATE, COUNTY}` | scenario seed (`dim_coercive_type.code`) | **Observed** |
| `prison/security` | enum `PrisonSecurity` | scenario seed | **Observed** |
| `prison/occupied` | int extensive | `p02` | **Derived** |
| `prison/cadre-held` | int extensive | `p02` | **Derived** |
| `prison/pact-covered` | int extensive | `p02` | **Derived** |
| `prison/captive-org-weighted` | int extensive | `p02` (population × organization, pre-multiplied — the `c01` idiom) | **Derived** |
| `prison/contraband-flow` | int extensive | `p05` | **Derived** |
| `prison/yard-homicides` | int extensive | `p04` | **Derived** |
| `prison/assaults` | int extensive | `p04` | **Derived** |
| `prison/shu-held` | int extensive | `p06` | **Derived** |
| `prison/pact-planks` | int intensive, `[0,5]` | `p09` | **Designed** (a rule count, not a measurement) |
| `prison/legal-line` | int extensive (routes open) | `p07` | **Derived** |
| `prison/lockdown` | int (periods remaining) | `p07` | **Derived** |
| `prison/hunger-strike` | int extensive (participants) | `p08` | **Derived** |
| `prison/transfers-out` | int extensive | `p11` | **Derived** |
| `prison/visits` | int extensive (per period) | `p07` | **Derived** |

**On each confined `SOCIAL_CLASS` node:**

| Field | Type | Class | Note |
|---|---|---|---|
| `social-class/population` | int extensive | existing | conserved |
| `social-class/organization` | probability | existing | **the contested quantity** |
| `social-class/cadre` | int extensive | derived | not `organization/cadre-level` — that is a *ratio on an org*; a prison needs a headcount |
| `social-class/study-cell` | int extensive | derived | seats in the school |
| `social-class/dependent` | int extensive | derived | in debt to the contraband market |
| `social-class/flipped` | int extensive | derived | **written but not readable by the player** (see §4.4) |
| `social-class/hardened` | int extensive | derived | long-custody cadre who held |
| `social-class/broken` | int extensive | derived | long-custody cadre who did not |

**Calibrated constants (each needs a declared operating range and a play purpose):**

| Const | Meaning | Range anchor |
|---|---|---|
| `carceral/per-diem` | county payment per occupied bed per period | Michigan's out-of-state bed contracts are public; range must bracket them |
| `carceral/control-unit-increment` | budget increment per recorded assault | the 2006 letter's mechanism; **Designed**, with the letter as the qualitative anchor |
| `carceral/smuggle-capacity` | contraband units a guard corps can move per period | the 1995 NY report (guards selling dope, several officers arrested) is the qualitative anchor |
| `carceral/dose-lethality` | deaths per unit of contraband flow | fentanyl-era; must state the era explicitly, because the 1995 anchor and the 2020s anchor differ by an order of magnitude |
| `carceral/charge-cost` | currency per arrest | county booking data is not in the DB; **Designed** |

The rule: a constant is legal only if it has a `:const` row in the world's `.bscn`,
a declared range, and a named play purpose. No constant hides in a rule body
(that is exactly what the decomposition/control-ratio headers call "an
underivable coefficient ADR172 r5 forbids").

### 3.3 The rule roster and the exact same-tick order

`babylon-tick/src/phase_order.rs` resolves a rule's slot from **the id prefix before
`/`** (`execution_key`: `rule_id.split('/').next()`), and refuses an unknown prefix
with `registered system "X" has no governed slot`. It also refuses an explicit
`(anchor :after control-ratio)` inside the Material Base partition —
`is_material_base_interior` raises "mods may target the boundary before vitality or
after metabolism, but cannot splice incidental order into the governed material
causal spine."

Two workable placements follow, and the report recommends the first:

**(A) No schedule change (recommended for v1).** Ship the pack in its own file
`content/rules/prison.bsl`, with rule ids prefixed by an *existing* system so they
resolve into slot 13 (`control-ratio`), after the ported rules by D16 ascending
byte order:

```
control-ratio/c01 … c04    (shipped, unchanged)
control-ratio/p01 … p11    (this pack)     'p' = 0x70 > 'c' = 0x63
```

This is legal today: the prefix selects the slot, the *file* is irrelevant to
ordering, and `phase_order.rs` refuses only unknown prefixes and interior anchors.
Cost: zero. `schedule_digest` is unchanged. No pinned baseline moves.

**(B) The clean long-term home (needs ceremony).** Insert a governed `carceral`
slot at ordinal 14 (Material Base), pushing `metabolism` to 15 and every
Consequence ordinal up by one: `SYSTEM_COUNT` 34 → 35, `MATERIAL_BASE_COUNT` 15 →
16, `schedule_digest` changes, and **every pinned schedule digest and replay
identity must be receremonied**. That is a Director-gated change, and it should not
ride a gameplay feature.

Every new rule additionally needs a `GOVERNED_RULE_ATTRIBUTIONS` row (ADR224:
`rule_id`, `role`, `evidence`, `owner: Director`, `date`, `adr`) — governance pins
the role, not the content file.

**The pack, in byte order, with same-tick reads declared (D116 discipline):**

| Rule | Subject | Reads | Writes |
|---|---|---|---|
| `control-ratio/p01-custody-census` | `SOCIAL_CLASS` | `role`, `active`, `population`, `organization`, `cadre`, `pact-covered` | `prison-*` contribution fields on the class node |
| `control-ratio/p02-custody-publish` | `PRISON` | p01 (same tick) via a `TENANCY` fold | `occupied`, `cadre-held`, `pact-covered`, `captive-org-weighted` |
| `control-ratio/p03-admin-replenishment` | `ORGANIZATION` (`PrisonAdmin`) | p02 census, `carceral/per-diem`, prior `assaults`, guard wage bill | the admin's per-instrument budgets |
| `control-ratio/p04-yard-violence` | `PRISON` | p02, p03, gang budgets, `decapitation`-ranked targets | `assaults`, `yard-homicides`, class `cadre` decrements |
| `control-ratio/p05-contraband` | `PRISON` | p03 `ADMIN` budget, `smuggle-capacity`, `pact-planks` | `contraband-flow`, class `dependent` increments |
| `control-ratio/p06-shu-flip` | `SOCIAL_CLASS` | `shu-held`, ties, `sentence-remaining`, `security-discipline` | `flipped`, `broken`, `hardened` |
| `control-ratio/p07-lockdown-mail` | `PRISON` | route table, admin `CUSTODY` budget, `legal-line` | `lockdown`, `legal-line`, `visits` |
| `control-ratio/p08-study-cell` | `SOCIAL_CLASS` | `cadre`, `legal-line`, receptive count | `study-cell`, `cadre` ADD, `organization` (bounded) |
| `control-ratio/p09-pact-planks` | `ORGANIZATION` (chapter) | five world-facts (§5.2) | `pact-planks` |
| `control-ratio/p10-intake-atomize` | `SOCIAL_CLASS` | arrival flag | `organization` (set to the intake value) |
| `control-ratio/p11-release` | `SOCIAL_CLASS` | `sentence-remaining`, exit condition | population move, `active`, `flipped` handoff |

`p01` and `p02` are deliberately the same shape as `control-ratio/c01`/`c02` — a
per-node contribution then a carrier fold — because that shape is already proven,
already conformance-tested, and already documented as the "push idiom" that avoids
the N-times-write bug. `p01` publishes its three per-node contributions
(`prison/census-occupied`, `prison/census-cadre`, `prison/census-pact`) exactly as
`c01` publishes `social-class/prisoner-census-*`; `p02` folds them over the
`TENANCY` in-neighbours and is the only writer of the prison-node aggregates.

**One same-tick dependency that must be called out explicitly.** `c01` reads
`social-class/organization` *before* `p08` writes it in the same slot, because `c` <
`p`. That is correct here and only here: the terminal branch wants the
*beginning-of-period* organization, and `p08`'s rebuild lands for next period. If
this is ever "fixed" by renaming `p08` to sort before `c01`, the terminal branch
starts reading a value produced by a rule that has not run — a silent, hash-stable
wrong answer. That is a D-record, and it is exactly the class of bug the
control-ratio header's "DELIBERATE reliance" language exists to prevent.

### 3.4 The player's verbs already reach a prison

This is the pleasant surprise of the audit: **no practice-contract change is
needed.**

| Player intent | Contract | Prison use |
|---|---|---|
| `ORGANIZE` | ids 1; targets `SOCIAL_CLASS`, `ORGANIZATION` | send a study package to the confined class; run the chapter; build the pact |
| `AGITATE` | 2; `SOCIAL_CLASS` | the yard meeting, the chow-line speech |
| `MUTUAL_AID` | 3; `SOCIAL_CLASS` | commissary fund, family travel fund, books |
| `STRIKE` | 4; **`LABOR_PROCESS`** | the convict-labour stoppage — the prison *is* a labour process |
| `OCCUPATION` | 6; `FACILITY`, `TERRITORY`, `ACCESS_POINT` | the yard takeover (Attica) |
| `INVESTIGATE` | 9; **`FACILITY`** | the SHU exposé, the mail-censorship audit, the smuggling inquiry |
| `BLOCKADE` | 5; routes | the transport van, the transfer bus |
| `DAMAGE` | 7; `FACILITY`, `STOCK` | refuse, and be told why |
| `CAPITAL_STRIKE` | 8; commitments | — |

Two of these are the design's best accidents:

- **`STRIKE` targets a `LABOR_PROCESS`, and convict labour is a labour process.**
  The hunger strike and the work stoppage are the *same verb*, which is historically
  right: the CA prisoner's account (`campaigns/ca/ca.strike.html`) moves from the
  DA referral to "I deny my first meal. The pigs actions, laughing and bets of how
  long the hunger strike will last… After three meals passed the pigs started to
  take me serious. Their first plan of action: a medical staff brings a weight scale
  and takes a weigh-in — 184 pounds… May 11, 168… 158." That is a *measured*
  labour process with a published escalation curve, and it is the corpus's own
  account of how the strike weapon works from inside.
- **`INVESTIGATE` targets a `FACILITY` with exactly one parameter, valued
  `{work_lost: 1, maintenance_received: 2}`.** The prison exposé is a facility
  investigation, and its output is the thing MIM(P) actually produced: a published
  finding. Note the parameter vocabulary — *work lost* and *maintenance received* —
  is already the material ledger of a facility, which is what a prison is.

And the `ORGANIZE` organizer-command parameter set is `{reinforce, hold,
pause_standing, resume_standing, saved_standing_contact}`. **`pause_standing` and
`resume_standing` are lockdown discipline.** The contract already knows that
standing organization sometimes has to be laid down and picked up, which is exactly
what a lockdown forces. No new parameter is needed to model "go quiet until the
shakedown passes."

`practice execution remains unwired` (per `practice_budget_topology.yaml`), as with
every practice. This briefing specifies the target, not a claim that it runs.

---

## 4. The four macabre hazards, priced

### 4.1 The identity that makes all four rational

`PrisonAdmin` is an `ORGANIZATION` (`OrgKind/STATE_APPARATUS`) with `Capacity`
budgets per instrument (ADR184: "**Capacity belongs to organizations. 'The state' is
not a node type.**"). Its replenishment, per period:

$$B_{\text{admin}} = \underbrace{\pi\, N_{\text{occupied}}}_{\text{per-diem}} \;+\; \underbrace{\gamma\, A_{\text{prior}}}_{\text{control-unit line}} \;+\; \underbrace{\omega\, W_{\text{guard}}}_{\text{appropriation}}$$

and the gang cells' replenishment:

$$B_{\text{gang}} = \underbrace{\mu\, V_{\text{contraband}}}_{\text{market share}} \;+\; \underbrace{\rho\, U_{\text{unprotected}}}_{\text{protection rents}}$$

Three statements follow, and they are the entire political economy of the yard:

1. $\partial B_{\text{admin}} / \partial A = \gamma > 0$. **Violence is revenue.** The
   warden is not sadistic; he is defending a line item, and the 2006 prisoner said
   so without being told.
2. $\partial B_{\text{gang}} / \partial U = \rho > 0$. **Fear is a product.**
   Protection is the only commodity a prison gang actually sells, and it is sold to
   the *unaffiliated*, which is to say to the mass of lumpen who have not joined
   anything.
3. $\partial B_{\text{gang}} / \partial V = \mu > 0$, and $V$ requires unmet demand,
   which requires pain, boredom and debt — i.e. requires the absence of a study
   cell.

So a prison solidarity pact that (a) protects the unprotected, (b) shuts the market,
and (c) fills the hours, **cuts three of the five revenue lines at once**. That is
why it is fought, and it is why it works.

### 4.2 Hazard A — getting merked: the decapitation market

**The mechanism, in shipped primitives.** The gang cells and the admin both fund
`ARMED` candidates. Each candidate is
`Candidate { actor, instrument: "ARMED", mode: "GANG_ASSASSINATION", target,
expected_yield, cost }` where:

- `expected_yield` = `decapitation_value(target)` in the **attacker's dossier** — the
  Sparrow quotient, already implemented: a ring scores low, a hub scores high. The
  organizer in a star-shaped chapter is the highest-yield target on the yard, and
  the arithmetic says so without anyone deciding to target organizers.
- `cost` = the price of a manufactured weapon plus the disciplinary exposure of the
  act (a recoverable `carceral/shiv` constant plus the admin's *tolerance*, which is
  the real variable: a stabbing that the admin wants to record is cheap).

`Capacity::allocate` funds down the ranking until the `ARMED` budget is exhausted.
Thus **assaults are a min of two counts, and both counts are visible in the world**:

$$A_t = \min\left(\left\lfloor \frac{B_{\text{gang},t}}{p_{\text{shiv}}}\right\rfloor,\; \#\{\,c : \text{uncovered}(c) \,\}\right)$$

with the targets taken in descending `decapitation_value`.

**The defence, in the same currency.** An attack on $c$ succeeds iff

$$\text{force}(A, c) \;\ge\; \text{defence}(c), \qquad \text{defence}(c) = \#\{\, j \;:\; \text{pact-covered}(j) \,\wedge\, \text{same yard}(j) \,\wedge\, j \ne c \,\}$$

`defence` is a **headcount**, not a probability and not a multiplier. Consequences,
all derived:

- A cadre in a yard with 40 pact brothers is not a candidate at all, because the
  gang's `expected_yield` is discounted by the certainty of reprisal, which is
  itself a count. The allocator declines him and stabs somebody else — and the
  somebody else is exactly the man who did not join.
- **The pact's PEACE plank is what turns a crowd into a defence**, because a crowd
  that will not act together is `defence = 0` even at 400 men. This is the precise
  mechanical content of "prison solidarity is key," and it is the reason the
  plank is worth a whole period of organizing.
- `decapitation_value` gives a cruel second-order result: **the best organizer is
  the most endangered, and the safest way to protect him is to make him
  redundant** — put three people at his level. The player who builds a
  charismatic hub loses him; the player who builds a ring keeps everyone. That is
  `exposure.rs`'s "redundant structure divides its own yield… nothing anywhere says
  'if the org is distributed, skip it'" — applied to a knife instead of a subpoena.

**What the player reads.** Not `decapitation_value`. He reads: *"They got Arnett on
the yard at count. He was alone — he'd been eating by himself since the shakedown."*
The isolation is a fact he can see; the quotient is the author's desk drawer.

### 4.3 Hazard B — the dope: a market with an enforcing authority or without one

The corpus's anchor is a prisoner's report from New York, 1995:

> "the guards at this facility are **selling drugs to prisoners in order to keep
> them in a zombie state of mind**. So far several officers were arrested for
> running drug operations in this facility. Goes to show who the criminals are."
> (`ulk/ulk/ulk105.html`)

Note the two claims in one sentence: it is a *market* (guards selling), and it is a
*suppression technique* ("zombie state of mind"). Both are true, and the design
must carry both.

**Mechanism:**

$$\text{flow}_t = \min\big(\text{smuggle-capacity}(B_{\text{admin}}^{\text{ADMIN}}),\; \text{demand}_t\big), \qquad \text{demand}_t = \max\big(0,\; (\text{occupied} - \text{pact-covered}) - \text{study-cell}\big)$$

The demand term is the important one and it is not moral: a customer is a prisoner
with **no collective protection and no school seat**. Two counts and a `max`, no
coefficient. A yard with a full study cell and a functioning pact has *less* demand,
which lowers the price, which lowers the gang's $\mu V$, which shrinks the `ARMED`
budget in §4.2. **The dope and the knife are the same budget from two
directions.**

**Damage, and it is not death:**

- `dependent` increments: prisoners who now owe. Debt is the gang's recruitment
  instrument and the admin's leverage.
- `organization` decay on the confined class: a nod is not a cell.
- `cadre` loss by *conversion*, not killing: the organizer who starts using is gone
  even though he is alive, and the player is not told which one.
- Deaths: `floor(flow × dose-lethality)`, a Calibrated constant with an explicitly
  declared era (1995 heroin/crack and 2020s fentanyl are different worlds and must
  be different constants, not one tuned number).

**The counter.** Not a "drug policy."
- PEACE creates the **enforcing authority** that a market requires and a prison
  lacks: the pact can *actually stop* a seller, because it has 400 people who will
  shun him, and the administration cannot credibly promise that.
- GROWTH fills the hours. MIM's own answer to the purity trap — "how do we not
  contribute to the system rather than how do we contribute to something that will
  change or end the system" — cuts here: a boycott of commissary is a purity move
  that costs the prisoner his soap; a study cell is an institution that costs the
  dealer his market.
- INDEPENDENCE removes the guard-brokered channel.

### 4.4 Hazard C — the snitch and the Trojan release

This is the hazard the user named "breed traitors," and it is the one with the
richest corpus support (Serge, ch. 3, in full).

**The three stages, each a gate:**

1. **Isolation.** `SHU`: `ties(c) := 0`. The prisoner's graph degree drops to the
   wall. Mechanically this is not a morale penalty — it is the *destruction of the
   collective verification* that UNITY depends on. Note the corpus's own SHU
   testimony (`campaigns/ca/corcoran.shu.repression.html`): no laundry system, one
   bar of soap a week for body, cell and toilet, cold food on stacked paper plates,
   and "the practice of handcuffing, then beating, kicking, spitting" — with the
   writer's own addendum, "This letter may cause me to be beaten and kicked around,
   of course after I've been handcuffed."
2. **Interrogation.** The Serge script, verbatim from the corpus: "We know
   everything!" (a bluff), "your Comrade So and So has talked" (a bluff), "you'll
   pay for this" (true, and it is the only true one). The prisoner who has been
   taught to expect these three moves has a *cheaper* interrogation; the one who has
   not is broken by surprise.
3. **The deal.** Sentence reduction, a fabricated "snitch jacket" placed in the file
   so that the yard will kill him if he refuses, or an early release.

**The flip condition, as a comparison of two prices:**

$$\text{flip}(c) \iff \underbrace{R_{\text{remaining}} \cdot u_{\text{release}}}_{\text{the state's offer}} \;>\; \underbrace{D_{\text{isolation}} + H_{\text{remaining}}}_{\text{the cost of refusing}}$$

where $R$ is the remaining sentence in periods, $u$ the value of release to him,
$D$ the accumulated deprivation of SHU, and $H$ the expected remaining sentence if
he refuses (which the state can lengthen by adding a charge — the CA prisoner's
account of a battery charge from a food slot becoming a third strike and "25 years
to life" is the corpus's own example of exactly this).

**The counter is Serge's, and it works by making the prisoner worthless rather than
loyal.** A cadre trained to say nothing has nothing to sell. The state's offer then
converts from *testimony* (cheap, useful, immediately actionable) to *fabrication*
(expensive, fragile, and exposable by `INVESTIGATE`). So:

- `organization/security-discipline` (already the porch's "say nothing" teaching,
  research/05's WITBD line) **raises the state's cost**, not the cadre's loyalty.
- The UNITY plank is the *collective* form of the same rule: "keep an open line…
  true facts… because of how the pigs utilize tactics such as rumours, snitches and
  fake communications." A chapter that verifies cannot be broken by a single
  confession, because a single confession is not evidence to them.

**The Trojan release, and the re-lease problem.** The flipped cadre comes home with
a clean file and a handler. He is now a `Malinovsky` inside your organization — and
per porch-02 §3, "a real wrecker must produce real successes to keep cover: an
infiltrated node never shows a lazy −20% modifier; it looks like a star performer
right up until a load-bearing moment." The engine knows. The player does not.

**The counter is a documented MIM(P) programme**, from
`agitation/prisons/organizing/expandwork.html`, item 6: "**Prisoner re-lease on life
program — working with released prisoners to stay on the streets and stay
politically active**." Mechanism:

- Every release passes through a defined re-entry period in which he holds no
  security-critical role — not because he is suspected, but because *everyone* does.
  A universal rule is not an accusation.
- INVESTIGATE can surface the handler relationship (a visit from someone not on the
  approved list; a bank deposit; a new car).
- **GROWTH's "right to leave" is load-bearing here**, and this is the subtlest point
  in the feature: a chapter that punishes suspicion with expulsion becomes a place
  where nobody tells the truth, which is precisely the condition a snitch needs. The
  plank that looks like liberalism is the counter-intelligence measure.

**Delayed discovery is the drama.** The flip is written to `social-class/flipped` and
is *not* readable by the player surface. It surfaces three periods later as an
event — the wrong person warned, the meeting that was known in advance, the raid
that arrived at the right hour. That is the knowledge system's backdating used as
narrative (porch-01: "a betrayal surfacing three periods on through the knowledge
system. The wiki backfills; the player *discovers*").

### 4.5 Hazard D — the lockdown and the mail

The cheapest modes win. `capacity.rs`, verbatim: "**Cheap modes beat expensive ones
at equal damage.** Disinformation is the cheapest mode by state capacity and among
the most expensive by movement cost — which is exactly why it dominates the
historical record." For a prison administration the two cheapest modes are not
disinformation but **the lockdown and the mail room**, and both cost almost nothing.

**Mechanism.** The chapter's ability to act is not a modifier — it is a **line of
communication**, and Debord's rule is that a node whose line is cut is paralyzed
immediately, not gradually (porch-02 §3). So:

- Routes are countable: legal mail (privileged), family visit, `Books for
  Prisoners`-style outside literature programme, attorney visit, released
  comrade as courier. Each is a route with a capacity and a censorship cost.
- The admin funds the cheapest set of censorship actions that drops
  `prison/legal-line` below the chapter's need. It does not need to censor
  everything; it needs to censor *enough*.
- `legal-line = 0` does **not** produce a "REFUSED" dialog. It produces **silence**:
  the `ORGANIZE` intent resolves, the cadre count does not move, and no error is
  shown, because a revolutionary organization does not receive an error message
  from the state — it receives nothing. **Silence is the correct UX and it is the
  hardest thing in the feature to get right**, because players read silence as a
  bug. The mitigation is the legal visit report (§7.2), which is a *different*
  channel that tells the player the mail is not moving.

**The counter is redundancy, and it is measured by `exposure.rs`.** The same
`components` / `giant_component_fraction` machinery that computes whether a raid
fragments an organization computes whether censoring *k* routes fragments the
prison's line. Four routes plus one courier is a ring; one route is a hub. The
player's job is to keep the graph of communication connected, and the wiki should
say so in the plain words of Debord rather than in graph theory.

**The transfer is the same hazard's expensive form** (§2.6). A lockdown is a
temporary cut; a transfer to another county is a permanent one that also books
revenue. The admin escalates from one to the other when the lockdown fails and the
budget allows.

### 4.6 The fifth, quieter hazard: time

Not one of the four, and it kills more cadres than the other four combined.

A sentence is 40–260 periods. The Party clock is 260 periods (porch-02 §6). So a
cadre sentenced at period 40 and released at period 300 comes out **after** the SPD
calcification deadline has already decided whether your organization became a
party or a fixture. He is not a resource in storage; he is a resource with an
expiry that may fall after the game is decided.

`prison/sentence-remaining` is therefore a **strategic clock display**, and it
belongs on the Ticker, not in a tooltip: *"Ruth Okonkwo, 8 years, 96 periods
remaining."* A player who reads it does the arithmetic himself and feels it.

---

## 5. Prison solidarity: five planks, five attacks on five revenue lines

### 5.1 Why the pact is not a buff

A buff is a number that goes up when you pay. The pact is five *facts about the
world* that, when they are true, remove a precondition that a hazard needs. Stated
as a table, which is how the corpus wrote it:

| Plank | Removes the precondition for | Revenue line it cuts |
|---|---|---|
| **PEACE** | Hazard A (needs an unaffiliated crowd to recruit from and an isolated target) and Hazard B (needs a market with no enforcing authority) | $\rho U$ protection rents; $\mu V$ market share |
| **UNITY** | Hazard C (needs a single unverified confession to be decisive) | the informant's price (converts testimony into fabrication) |
| **GROWTH** | Hazard B (demand comes from hours nobody fills) and Hazard C (a chapter that permits exit is one where truth is cheap) | $\mu V$; recruitment pool |
| **INTERNATIONALISM** | Hazard A's *targeting logic*: the race war is a **product segmentation** — each gang sells protection from a named other. A study cell with two national contingents in it has no "other" to sell. | the gang's product differentiation |
| **INDEPENDENCE** | Hazard D (the admin's leverage is that it supplies the goods) | $\gamma A$'s justification, and the admin's brokerage |

Note what INTERNATIONALISM does mechanically, because it is the least obvious and
the most important: a prison gang's business model requires an *enemy nation* on
the yard. If the New Afrikan and the white contingent sit in the same study cell,
the gang cannot sell "protection from them" — the product has no referent. This is
why the corpus's chauvinism analysis (`research/06` §4: "wrong line produces wrong
sentiment, not the reverse… Chauvinism is a *consequence* of a mis-specified edge")
applies to *both* sides of the yard. The fascist gang and the anti-racist training
are downstream of the same edge.

### 5.2 Earning each plank: world-facts, not purchases

Each plank is earned by a condition that the engine can read and the player cannot
fake. No currency, no tech, no button.

1. **PEACE** — a period in which `prison/yard-homicides = 0` **and** the pact's
   membership spans at least two contingents that were hostile in the previous
   period (a contradiction edge exists between the two organizations in the graph —
   the object the `DIVIDE` verb of `research/06` P2 would widen once that verb
   exists). Verified by the player's own `INVESTIGATE` on the facility, so the plank
   costs a practice and a period, not money.
2. **UNITY** — an `INVESTIGATE` on the facility that successfully identifies a
   planted rumour or a snitch (`social-class/flipped > 0` surfaced). One verified
   fact, not five.
3. **GROWTH** — `p08-study-cell` produced `cadre ≥ 1` for a full period **while**
   at least one member exercised the right to leave without penalty (a member left
   the chapter and was not `flipped`, `broken`, or expelled with a penalty). This is
   the corpus's own "right to leave" made a *test*, and it is the plank that prevents
   the pact from becoming a sect.
4. **INTERNATIONALISM** — two national contingents with cadre in the same study
   cell, for a full period.
5. **INDEPENDENCE** — a period in which the chapter received **zero** goods from the
   administration: no warden's "program," no guard-brokered commissary, no
   administration-supplied teacher, no grant. The books came from outside or nobody
   read.

The five conditions are all countable. None requires a coefficient. All of them can
be lost, and losing one is a *fact about the world* the player will read in a kite
before he reads it in a number.

### 5.3 The pact's arithmetic: defence is a count, and everything else follows

Once `pact-planks` is the state, the hazards resolve as:

- **Hazard A:** `defence(c)` counts pact-covered prisoners in the same yard;
  `pact-planks ≥ 1` is what makes "pact-covered" mean *will act* rather than
  *signed something*.
- **Hazard B:** `demand = max(0, (occupied − pact-covered) − study-cell)`; a pact that
  covers half the yard removes half the market.
- **Hazard C:** `security-discipline` rises with UNITY; the flip price rises with it.
- **Hazard D:** each plank the pact holds is an independent reason for an outside
  comrade to keep writing, so `legal-line`'s replenishment is a function of
  `pact-planks` **and** the outside organization's own strength.

And the pact's own **decay**, which is the 2006 mechanism (Hazard D working):

$$\text{planks} := 0 \quad\text{if}\quad \#\{\text{isolated initiators}\} \ge \#\{\text{initiators}\}$$

The admin does not need to break the pact. It needs to break *the people who can
hold it*, one at a time, and it can do that with SHU at almost no cost — provided
nobody outside notices. Which is why the outside line is not a support mechanic; it
is the pact's *replenishment*.

### 5.4 The pact's price: it is a floor, not a ceiling

This is the design's most important honesty, and it comes straight from the
corpus's own text: "**This statement does not grant authority to any party over any
other party.**"

Mechanically:

- The pact raises the yard's general cohesion, which is *not one of your fields*, and
  it lowers hazards. It does **not** raise `social-class/organization` toward *your*
  line. Peace is a commons.
- Cadre conversion requires `p08-study-cell`, and a study cell has a curriculum, and
  a curriculum has a line. That is where the player's politics enter — and it is the
  only place they enter.
- Therefore a player can **win the yard and lose the politics**: the pact holds, the
  homicides stop, the yard is safe, and the cadre that come out of it are
  peace-and-education people who will not endorse the necessity of revolutionary
  violence. That is the "respectability flip" and the "comprador flip" from
  `research/06` §10, arriving from inside a prison chapter instead of from a grant
  office.

**The post-pact contradiction (the second boss).** Per porch-02 §2, "Resolving a
contradiction never produces 'peace'—it births the next contradiction." Once
`pact-planks = 5` and `yard-homicides = 0` hold for several periods, the yard's
internal contradiction becomes **who leads**. The GROWTH-only tendency ("we have
peace and classes, why the politics") can invoke the right to leave, take the
study cell's students, and split the node — a `split` resolution on the Topology
canvas, spawning a breakaway chapter with a hot antagonistic edge. The player's
options are the corpus's: clarify the line (and risk the split), concede (and watch
the chapter become a literacy programme), or purge (and pay in the only currency
that matters, cadre who were sincere).

That is the prison's endgame, and it is a Decision Ceremony, not a random event.

### 5.5 The Revolutionary School: a three-way min

The conversion from lumpen to cadre is a supply chain with three inputs, and any
one missing caps it:

$$\Delta CL = \min\left(\; T_{\text{teachers}},\;\; \left\lfloor \frac{M_{\text{material}}}{m_{\text{package}}} \right\rfloor,\;\; S_{\text{receptive}} \;\right)$$

- $T$ = cadre in custody who can teach. Costs: a teaching cadre is **not**
  organizing that period, so `Δorganization` is negative in the short run. That is
  the "sectarian / reading group trap" (porch-02 §5: "all CL, no SL") expressed at
  yard scale, and the player must feel it.
- $M$ = study packages delivered. Capped by `legal-line` and by the outside
  organization's own press/books capacity. **This is where the street org pays for
  the prison**, and it is why a prison chapter decays when the outside is smashed
  even if the prisoners are willing.
- $S$ = receptive prisoners: confined lumpen who are not `dependent` (Hazard B) and
  not gang-sworn. A pact raises $S$ (fewer people need a gang for safety); narcotics
  lowers it.

The corpus's Oscar passage is the three-input model in miniature: two teachers
(Lenin and Krupskaya), one book (translated on the spot because $M$ was zero), one
receptive deported striker. Output: one cadre.

**Quality, not just quantity.** Long custody produces one of two things, and which
one is determined by whether $T$ existed:

$$\text{cadre}(c) \to \begin{cases}\text{hardened} & \text{if a study cell ran in his yard for most of his sentence}\\ \text{broken} & \text{otherwise}\end{cases}$$

A hardened cadre comes out with higher `security-discipline` and a longer horizon — he
has already survived the worst thing the state does to a person. A broken one comes
out with lower organization and a vulnerability that the state already knows how to
use. **Prison does not make cadres. Prison makes whatever the collective inside it
makes.** That is the whole thesis of the feature in one line, and it is why the
answer to "prison breeds traitors" is not "screen harder" but "keep the school
running."

### 5.6 Why the pact needs an outside line: the 2006 lesson as a mechanism

Restating §1.5 as a rule, because it is the difference between a mini-game and a
base area:

- A pact whose initiators can be isolated faster than they can be replaced decays to
  zero. Replacement requires new initiators to *arrive* — and new initiators arrive
  through the mail, from an outside organization that has been training people to
  become initiators before they are arrested.
- An outside organization makes reprisal expensive. The 2006 failure was not that
  Sacramento disbelieved the delegates; it is that *nobody outside could make them
  pay for disbelieving*. The 2011–2013 attempt had press, lawyers and a movement, so
  the same lie cost more.
- Therefore the prison's `legal-line` replenishment is
  $\propto$ (outside org's press capacity) × (outside org's legal capacity) ×
  (outside org's willingness to spend on prisoners rather than on its own immediate
  fight), and **the player's real decision is a budget allocation between the street
  and the wire.** That is a beautiful, miserable choice, and it is the correct one:
  every hour spent on a prison mailing is an hour not spent on the plant gate.

---

## 6. The carceral economy in the material circuit

### 6.1 Per-diem, the wage bill, and the guard local

`babylon-material-circuit` has the conserved objects: `CashAccount`,
`PublicAccountId`, `CashTransferPurpose::{Tax, PublicTransfer, HouseholdTransfer,
MutualAid, …}`, `PublicBudget`, `TaxPolicy`, `WageAccrualReceipt`. The carceral flow
uses only these:

```
county treasury ──PublicTransfer──► prison operating account ──WagePayment──► CARCERAL_ENFORCER households
   ▲                                                                              │
   └──────────── Tax (county levy) ◄──────────────────────────────────────────────┘
                          (the round trip is the town's economy)
```

Two things this makes visible without a single formula on screen:

- **The guard's wage is a transfer from the county's tax base, and the county's tax
  base is a city.** That is not a metaphor in Michigan: Chippewa County's largest
  employer is the prison, and the prisoners come from Wayne.
- **The per-diem is a *revenue* line that rises with occupancy**, so the Sheriff's
  and the warden's interests diverge from the DA's (who wants convictions) and from
  the Mayor's (who wants the budget). That is the division tactic, already available
  as an edge to widen.

`fact_coercive_infrastructure` supplies `beds`; `fact_qcew_county_rollup` supplies
the county wage base that the guard payroll competes with. Both are Observed. The
link between them — "how much of this county's employment is the prison" — is
Derived, and it is the number that should appear in a Wiki dossier on a prison town,
never in a tooltip.

### 6.2 Bail as a receivable, not an expense

- Cash bail: `MoneyTransferReceipt` from the org's `CashAccount` to the court's
  `PublicAccountId`, `purpose: MutualAid` (or a dedicated `Bail` purpose if the
  allowlist is extended), recorded as a **refundable claim**.
- Appearance: the claim reverses. Net cost zero.
- Forfeiture: the claim is extinguished and the org eats it. **This is the only
  catastrophic outcome and it happens when the cadre absconds** — i.e. when the
  player's own organization has lost him, which is the same failure as Hazard C seen
  from the other side.
- Bond premium: a non-refundable `MutualAid` payment to the bondsman. This is the
  real recurring cost, and it is a transfer to a node the player can also organize
  against.

`CashTransferPurpose` is an exact allowlist. A new `Bail` variant is a contract
change with its own conformance vectors; **v1 should use `MutualAid` and label the
receivable in the dossier**, adding the variant only when the bail flow earns it.

### 6.3 The visit is twelve hours out of a household's week

This is the mechanism that makes the whole feature land emotionally, and the repo
already has it: `household_time.rs` — `HouseholdTimeBook`,
`HouseholdTimeCommitment`, `HouseholdUnmetTimeBurden`, against the 168-hour week of
porch-02 §4 (Fortunati's double debt).

A visit to Chippewa from Detroit is a round trip of roughly 400 miles each way. As a
`HouseholdTimeCommitment` it consumes most of a working week's non-wage, non-
reproduction hours. The consequences are all derived:

- The family node's `HouseholdUnmetTimeBurden` rises, which lowers its ability to
  attend meetings, which lowers the *street* organization's capacity — **the prison
  reaches back out and taxes the movement through the family's calendar.**
- The `visits` route in §4.5 has a *cost borne by someone other than the player*.
  The player can fund a bus (`MUTUAL_AID`), and that is a real, unglamorous,
  correct thing to spend money on — MIM(P)'s own list includes exactly this kind of
  unglamorous work ("bulk book purchasing", "a typing pool requiring a postal
  address and PGP", `research/06` §7(iv)).
- And the Ticker can show it: *"Greyhound, Detroit–Kinross, $94 round trip, 11h 40m."*
  A price and a duration. No formula.

### 6.4 What must not be added to the circuit

- No prison "budget line" outside the accounts. The per-diem is a
  `PublicTransfer`; the wages are `WagePayment`s; conservation holds or the tick is
  wrong.
- No per-diem rate derived by dividing anything. It is a contracted price and it is
  Observed (Michigan's out-of-state bed contracts are public documents).
- No "cost per prisoner" scalar on the HUD. The player can compute it; the game
  must not.

---

## 7. Gameplay feel under the Mao visibility rule

The rule (porch-01, canonical): "Show only what a participant could learn from
reading a communist history book… Concrete countable world-events (funds, chapters,
votes, crowds) may show; engine-computed abstractions (scores, multipliers, trigger
weights) stay buried." Working test: *would Mao have put it in the treatise?*

Applied to this feature, the answer is unusually clean, because a prison **naturally
produces documents**: kites, legal visit reports, commissary ledgers, mail logs,
charge sheets, autopsy lines. The interface is a reading room, not a dashboard.

### 7.1 The kite

A kite is the primary prison surface, and it is rendered as a **document, not a
panel**:

> `— intercepted? no — via: legal mail — sent: P41 — received: P43`
>
> `They moved Arnett to 4 Block after the shake. He's eating alone. Tell his people
> not to write for a while. The classes are going — 14 on Tuesday, more than last
> week, but [two lines cut out] and the brother from Grand Rapids says he can get us
> the Manifesto if the books come. We need the books. Also tell them about Oscar.`

Three design properties, all of which are the visibility rule in action:

1. **Two-period latency, always.** The kite arrives after the decision it should
   have informed. That is not a UI delay; it is the strategy.
2. **The hand is visible, the meaning is not.** "[two lines cut out]" is a fact (the
   mail was opened) and simultaneously an epistemic hole (what was in them?). The
   player never learns. That is Serge's "your mail will be opened" as a *reading
   experience*.
3. **"Tell them about Oscar."** The curriculum is named but not shown. A player who
   has read §1.6 knows what it means; a player who has not will learn by watching
   the conversion rate move, and then find the Wiki entry. **The feature teaches by
   reference, not by explanation.**

The kite never contains a number the player could not have counted himself. It
contains *names, counts of people in a room, and requests for things*.

### 7.2 The legal visit report

A second, independent channel, and the one that tells the player the mail is dead:

> `ATTORNEY VISIT — 30 minutes, monitored — P44`
>
> `Present: R. Okonkwo (client), M. Feldman (counsel). Corrections officer present
> throughout. Client states: conditions on 4 Block; a hunger strike is being
> discussed; he has not been charged in the 3/12 incident. Counsel states: the
> §1983 filing is docketed; the mail room has returned three items as
> "unauthorized publication." Client requests: books; a list of the other men's
> names; his sister be told he is all right.`
>
> `Note: two names were written down and then struck out by the officer.`

This is the corpus's own genre (the Corcoran SHU missive, the "Attica Talk" flyer,
the ULK letters): a monitored document with an official present, in which the
*omissions* carry the information. And it is a **second route**: if the mail is cut
and the attorney visit still happens, the player knows the censorship is selective —
which is the difference between a lockdown (temporary) and a transfer (permanent).

### 7.3 Ticker and Corporate Feed

The Corporate Feed's voice is the hegemonic euphemism, and the prison story is where
that voice is funniest and most damning:

> **"DOC to Add 200 Beds at Kinross Following Yard Disturbance"**
> *Corrections officials said the expansion reflects 'ongoing population pressures'
> and a commitment to 'staff and inmate safety.' Three injuries were reported
> Tuesday. The department's request cites a 9% rise in 'serious incidents' fiscal
> year to date.*

The player who has read §4.1 knows exactly what that headline is: the warden
monetizing the disturbance. The *player* sees a headline; the *engine* computed
$\gamma A$. That is the Mao rule working perfectly — the causal variable is buried
and its consequence is a sentence in a newspaper.

And the **Liberated Signal**'s counter-voice, from the same immutable journal:

> **"They Are Paying Themselves For The Knife"**
> *Third stabbing in six weeks at Kinross. The department's budget request went up
> 9% this quarter. Do the arithmetic they will not do for you.*

Same facts. Contested meaning. Neither is a number the player could not count.

### 7.4 The three Decision Ceremonies

**Ceremony 1 — the phone call at 2 a.m. (post bail or leave him).**
Split pane, two options, honest summaries of what each *means*:

- **Post bail.** "Twelve thousand dollars, refundable if he appears. He is out in
  three days. He learns nothing about the inside, and the county keeps its bed
  empty." Costs shown. Outcomes not previewed. If he absconds, the money is gone
  and so is he — and the player is told that risk in those words, not as a
  probability.
- **Leave him.** "He stays in county lockup until trial, then probably Chippewa. He
  will be in a yard with four hundred men who have nothing to lose, and he is the
  best organizer you have. The mail takes two periods." No promise that he
  organizes. No warning that he might be flipped.

This is the gate that teaches the player the feature's thesis in one click: **the
cheap option is usually the one that wastes the cadre.**

**Ceremony 2 — the pact (sign or not).**
Not a treaty screen with a "sign" button. A document, in the corpus's own words,
with the five planks, and the player's choice is *which plank to put his name to
first* — because signing PEACE without UNITY gives the gangs a ceasefire they will
use to rearm, and signing UNITY without GROWTH builds a security apparatus with no
school. The choice is a sequencing decision with real consequences and no preview.

**Ceremony 3 — the lockdown.**
The admin's move arrives as a *fact*, not a menu: visits suspended, mail held,
count cancelled, the yard locked for 14 days. The player's only decision is what to
do with the silence: `pause_standing` (protect the chapter, lose the period),
`resume_standing` (risk the shakedown finding the cell, keep the cadres), or spend
money on the legal route (expensive, slow, and the only one that ends the lockdown
early). The organizer-command parameter set is already these names.

### 7.5 One event, three feeds

The arrest of a named cadre, rendered three ways from one journal record:

- **Corporate Feed:** *"Task force arrests fugitive in Dearborn raid. Two officers
  treated for minor injuries. The suspect is held without bond pending arraignment."*
- **Liberated Signal:** *"They Took Amina At 4 A.M. And Broke Her Brother's Arm
  Doing It."*
- **Intel Stream:** `ARREST — node: wayne-branch-3 — persons: 1 — agency: FBI
  (Detroit Field Office) — charge: 18 U.S.C. § 371 — custody: LOCKUP (Wayne County
  Jail) — bail: denied — decapitation_value: [not shown]`

Note the Intel Stream's honest bracket. That is the one place the game admits there
is a number it will not show, and it teaches the player that the game is not lying
to him — it is *withholding the state's model*, which is what a revolutionary
organization actually faces.

### 7.6 The delayed discovery

The flip is the feature's best use of `observed_period` vs `acquired_period`:

1. Period 41: a cadre is flipped in SHU. Nothing surfaces. `social-class/flipped`
   increments; no surface reads it.
2. Period 44: a meeting is raided at the right hour, and a courier is arrested who
   should not have been known. The Liberated Signal prints an argument about
   security culture. The Wiki backfills a page.
3. Period 47 or never: an `INVESTIGATE` on the county jail surfaces the handler
   relationship — a visitor not on the approved list, a deposit, a phone number
   called four times from a pay phone outside the facility.

The player is never told "you have a mole." He is told that a thing happened that
should not have happened, and he is given verbs.

### 7.7 What the player never sees

- Any hazard probability, `decapitation_value`, `expected_yield`, gang budget, or
  flip flag.
- The number of prisoners in a yard as a HUD counter. He sees a kite that says
  "14 on Tuesday."
- The per-diem rate, the control-unit increment, or the admin's budget lines — only
  the appropriations vote and the budget request's percentage, which are public
  documents.
- The word "organization" as a scalar for the confined class. He sees a man who
  used to come to meetings and now does not.
- The reconciliation of the pact's five planks into a score. He sees a yard where
  nobody has been stabbed in five periods, and he knows why, and if he does not know
  why he will find out.

---

## 8. Integration notes: what this closes, and what it reopens

**8.1 `control-ratio` terminal branch (ADR070, Director-reserved).** This feature's
output is the input to a reserved decision: `c04-terminal` compares
`prisoner-org-weighted / prisoner-population` against
`carceral/revolution-threshold` and emits `TERMINAL_DECISION` = REVOLUTION or
GENOCIDE. Prison organizing writes `social-class/organization` for the confined
classes, so **the feature's whole point is that the player can move a reserved
variable by organizing a prison** — which is the correct design and touches a
reserved line, so it needs explicit Director acknowledgement and no rule changes to
`c04` itself.

**8.2 The `INCARCERATED` community floor is a named problem this feature can close.**
`community/c06a-floor-dispatch` has a 14-arm chain including
`CommunityType/INCARCERATED` → `community/floor-incarcerated` = `0.18p`, and the
conformance world's own comment records its status:

> `(defconst community/floor-incarcerated 0.18p) ; unchanged (Ruling 2) — NAMED
> PROBLEM: unreachable in principle from B17001 (the universe excludes the
> institutionalized); a future ruling needs BJS/Vera-class data`

The prison node is the missing universe. Once a county's incarcerated population is
`occupied` summed over `fact_coercive_infrastructure` capacities rather than
inferred from a household survey, the floor becomes *measurable* — and the 0.18 stops
being a placeholder. This is a Director ruling to request, not a change to make: the
alternative data source changes the evidence class from an unreachable Observed to a
Derived, and the ruling must say which.

**8.3 The phase-order constraint is real and cheap to satisfy.** §3.3 gives both
routes. Route A (prefix `control-ratio/p…`, own file) costs nothing today. Route B (a
governed `carceral` slot) is the clean home and requires a schedule-digest change and
full receremony. The recommendation is A now, B when a second carceral system needs
the slot.

**8.4 One Cargo-cult risk, named.** `territory/p4-penal-suppression` is *ported,
conformance-tested, and correct for its purpose*. The temptation will be to reuse it
on a `PRISON` node because both are "places where prisoners are." Doing so makes
organization a per-tick flow, blinds the terminal branch, and requires editing a
ported rule's expected values in `territory-conformance.bscn` and `query-lane-e2e.bscn`
Shape D. **Do not.** A `PRISON` has no `territory/territory-type`, so the rule never
fires on it, and that is by design.

---

## 9. Open questions for the porch

1. **Does the player ever command a yard directly?** The practice allowlist says
   `ORGANIZE` targets a `SOCIAL_CLASS`; but a prison chapter is inside, and a player
   on the street cannot attend a meeting. Is the prison chapter a *player-controlled
   organization* with delegated authority, or an *autonomous* one that reports late?
   The second is truer and the first is more fun, and the tension is real.
2. **What is the right sentence distribution?** 40–260 periods spans the whole
   useful range, and if most sentences are long, prison becomes a write-off; if most
   are short, the study cell never pays back. The distribution is a Designed choice
   with a large behavioural consequence and it should be set by a stated target (e.g.
   "a third of prison cadre return within one Party generation").
3. **Does `STRIKE` on a `LABOR_PROCESS` inside a prison need a separate escalation
   curve?** The CA prisoner's account gives one (weight 184 → 168 → 158, guards
   betting on duration, medical called after three meals missed). That curve is
   empirical and it is better than anything invented; does it become the prison's
   canonical strike ladder, distinct from a plant strike?
4. **Is the pact a node or a hyperedge?** A `UNITED_FRONT` is a multi-org object with
   no authority over members (`research/06` §10), which is exactly what a
   `HyperedgeType` is for — first-class membership without a privileged owner. The
   pact probably wants a hyperedge, and this is the feature's one genuinely new
   *structure*, so it needs an explicit call.
5. **Can the player lose a yard to a preacher?** The post-pact split (§5.4) is the
   feature's best second act, and it requires modelling a *religious* mass tendency
   as a legitimate competitor rather than a deviation. Is that in scope, or does it
   collapse into the generic "respectability flip"?
6. **What does the terminal REVOLUTION branch actually show inside a prison?** The
   reserved line says organized prisoners plus radicalized guards. Mechanically that
   is `avg_organization ≥ threshold`, and the *narrative* of a prison that turns is
   the single most powerful scene the game could have. Does the feature own that
   scene, or does the reserved branch?
7. **Should the FBI's protection of its own informants be visible here?** Porch-02
   §3 gives the FBI the behaviour of "arresting loyal cadres above a mole to engineer
   the mole's promotion." Inside a prison that becomes: the bureau's asset is
   *protected from* the yard while your organizer is *exposed to* it. That asymmetry
   is a superb hidden mechanic and it is currently unspecified anywhere.

---

## 10. Sources read

**In-repo specifications and reference**

- `ai/epochs/epoch1/carceral-geography.yaml` (full: territory types, displacement
  priority modes, necropolitics phase, `_suppress_organization`, theoretical
  framework).
- `ai/epochs/epoch3/reactionary-subject.yaml` (head: thesis, theory sources
  including George Jackson's *Blood in My Eye* for "lumpenproletariat as
  revolutionary force, prison as class war").
- `docs/gameplay/2026-10-25-porch-01.md` (visibility rule, decision ceremony, the
  three-layer answer, the three narrator feeds, knowledge backdating).
- `docs/gameplay/2026-10-25-porch-02.md` (six screens, `Capacity::allocate` cell
  doctrine, the four base-area terrains, the three resources, the 260-period clock,
  the `fascist-faction`/`POSSE` objectives).
- `docs/gameplay/research/06-mimp-and-mlm-tw-canon.md` (the five UFPP principles and
  membership test, the cell/party/`form_ceiling`, the eight flip rules, P7 prison
  siting, the prison-economy facts: 2.3m held, $1trn aggregate, 1,370/100k Louisiana,
  24% New Afrikan guards in 2017).
- `docs/reference/systems.rst` (DecompositionSystem 15%/85%, ControlRatioSystem
  `max_controllable = enforcer_population × control_capacity`, the REVOLUTION/GENOCIDE
  terminal table at `avg_organization ≥ 0.5`).

**Executable Rust surfaces**

- `rust/crates/babylon-tick/content/rules/territory.bsl` — `p4-penal-suppression`
  (verbatim quoted), `p4-camp-decay`.
- `rust/crates/babylon-tick/content/rules/control-ratio.bsl` — `c01-prisoner-census`,
  `c02-publish-census`, `c03-crisis`, `c04-terminal`; the D116 byte-order header and
  the `_PRISONER_ROLES` D-record.
- `rust/crates/babylon-tick/content/rules/decomposition.bsl` — the intake/transfer
  idiom (`p04` ADD, `p05` SET, `p06` deactivate) used as the model for arrest.
- `rust/crates/babylon-tick/content/rules/community.bsl` — `c06a-floor-dispatch`, the
  14-arm community chain including `CommunityType/INCARCERATED`.
- `rust/crates/babylon-tick/content/scenarios/community-conformance.bscn` — the
  `floor-incarcerated` "NAMED PROBLEM: unreachable in principle from B17001" comment.
- `rust/crates/babylon-tick/src/phase_order.rs` — the 34-slot registry, the
  prefix→slot `execution_key` resolution, `is_material_base_interior` and the
  interior-anchor refusal text.
- `rust/crates/babylon-graph/src/capacity.rs` — `Candidate`, `Allocation`,
  `Declined.remaining`, `Capacity`; the "capacity belongs to organizations," "repression
  and revolutionary action are the same allocation," and "yield is computed on `L`,
  never on truth" rulings.
- `rust/crates/babylon-graph/src/exposure.rs` — `decapitation_value`, the
  replaceability quotient, and "a redundant structure divides its own yield."
- `rust/crates/babylon-bsl/src/causal_contract.rs` — `RuleRole`
  (mechanic/recognizer/external-event/intent), `EvidenceClass`
  (observed/derived/calibrated/designed), `GOVERNED_RULE_ATTRIBUTIONS`.
- `rust/crates/babylon-bsl/src/query.rs`, `evaluator.rs` — the six query heads and
  `fold`'s acceptance of any of them (which is what makes a local per-prison census
  expressible).
- `rust/crates/babylon-bsl/src/intrinsic_host.rs` — the kernel intrinsic table
  (`floor`, `exp`, `log`, and ADR219's sextet), i.e. the exhaustive list of
  mathematics available to this feature.
- `contracts/practice_intent.yaml` — the nine `practice_ids`, `target_allowlists`,
  and the `ORGANIZE` organizer-command values (`reinforce`/`hold`/`pause_standing`/
  `resume_standing`/`saved_standing_contact`).
- `contracts/practice_budget_topology.yaml` — `max_organizations`, `VerbStem`,
  `PracticeTargetDomain` (SOCIAL_CLASS), contract error codes, and the
  "practice execution remains unwired" header.
- `CONSTITUTION.md` — Article IX (vocabulary vs. mathematical primitive; the Director's
  reserved line) and Amendments AH/AL.

**MIM(Prisons) corpus** (`/media/user/data/mim/textonly/` unless noted)

- `FPLmimp.pdf` pp. 6 and following — the UFPP Statement of Principles in full, the
  joining procedure, and the "all prisoners are political prisoners" formulation.
- `agitation/prisons/organizing/expandwork.html` — "Building MIM's prison
  organizing": web work, prisoner correspondence, books by mail, legal work,
  agitation, and **"prisoner re-lease on life program."**
- `agitation/prisons/campaigns/ca/history.peace.summit.html` — the 2006 Pelican Bay
  Peace Summit post-mortem, including the "no grassroots community support" failure
  and the "vested economic interest in seeing that the cycle of violence remained"
  passage.
- `agitation/prisons/campaigns/ca/corcoran.shu.repression.html` — the SHU conditions
  letter (soap, laundry, cold food, handcuffing and beating) and its retaliation
  warning.
- `agitation/prisons/campaigns/ca/ca.strike.html` — the hunger-strike account with
  the weigh-in ladder (184 → 168 → 158 lb), the DA referral and third-strike
  arithmetic, and the guards' betting on duration.
- `agitation/prisons/essays/the.dragon.html` — George Jackson (age, $70, one-to-life,
  seven years in solitary, the 1971 racial composition, "prisons could not be
  changed").
- `agitation/prisons/essays/need.struggle.html` — the "Need for Struggle and
  Practice Behind Bars" letter and MIM's reply on tactical caution ("We should be
  afraid of oppression… Our comrades in prison are under much more scrutiny").
- `atticatalk.html` and `aa/old/januaryevents.html` — Big Black (Frank Smith) as an
  Attica prisoner leader; `aa/articles/prisonboom.txt` — Michigan's prison build-out,
  the CCA/Oklahoma and West Virginia transfers, MCL 791.211.83, and the Attica
  background sentence.
- `ulk/ulk/ulk105.html` — "NEW YORK GUARDS SELL DRUGS" ("to keep them in a zombie
  state of mind"), the Jackson "civil exam" quote, and the satire of the organizer
  who "committed suicide by swallowing a bar of soap" after brokering a gang truce.
- `ulk/ulk/ulk110.html` — a control-unit transfer warning from inside MCC
  (Westville, Indiana) and the corrosion of collective study ("what ever happened to
  collective struggle?").

**Marxists Internet Archive** (`/media/user/data/old-hdd/old-hdd/www.marxists.org/`)

- `archive/serge/1926/repression/preface.htm` — "the immediate aim of the police is
  more to know than to repress"; the anti-legalist warning.
- `archive/serge/1926/repression/ch2.htm` — illegality, the Yugoslav/Italian/German
  comparisons, private police, and the Pinkerton employment figures.
- `archive/serge/1926/repression/ch3.htm` — "Simple advice to revolutionaries": tail
  detection, correspondence, "say nothing," "never confess," "we know everything" as
  a bluff, and conduct before judges.
- `archive/krupskaya/works/rol/rol02.htm` — Lenin in Shushenskoye; the deported
  striker Oscar and the *Manifesto* study cell; Kurnatovsky's "exile after exile";
  Zaporozhets and Vaneyev.

**Reference data**

- `/media/user/data/babylon-data/sqlite/marxist-data-3NF.sqlite`, tables
  `fact_coercive_infrastructure` (3,867 rows), `dim_coercive_type` (15 rows; 6
  carceral, 9 military, **0 enforcement**), `dim_county`, `dim_state`. Michigan
  queries: 109 local jails / 79 counties / 16,686 beds; 31 state prisons / 21
  counties / 12,376 beds; 1 federal; Wayne 4 jails + 1 state prison; Chippewa 2
  prisons / 3,870 beds.

**Limits, stated plainly**

- **No Attica primary source on disk.** The 1971 sequence (dates, the 1,300
  prisoners and 42 hostages, the 39 dead including 29 prisoners, the state-fire
  autopsy finding) is from general historical recall, not from this corpus. It must
  be sourced before any of those numbers reach a player surface.
- **No Pelican Bay 2011–2013 primary source on disk.** The *Agreement to End
  Hostilities*, the 2011 and 2013 hunger strikes, and the *Ashker v. Governor*
  settlement are from recall. The corpus's MIM material is 1994–2009 vintage and
  predates them; only the 2006 failure is primary here. The design *argument* in
  §1.5 rests on that 2006 primary document, and the 2011–2013 contrast is the
  comparative claim that needs a source.
- **No Serge *Men in Prison* and no Stalin archive on disk.** Serge's prison
  experience is represented only by the *Repression* chapters; the Tsarist-prison
  baseline comes from Krupskaya's exile memoir, not from a prison memoir.
- **The MIM corpus is a movement archive, not a dataset.** Its prison-economy
  figures are as of their publication dates (2005–2009), and every one of them must
  be re-sourced before appearing in a Wiki dossier with a citation.
- **`fact_coercive_infrastructure` has no police agencies**, so every enforcement
  node's staffing is Designed or Calibrated, not Observed.
