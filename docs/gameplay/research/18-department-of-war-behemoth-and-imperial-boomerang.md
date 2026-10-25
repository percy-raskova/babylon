<!-- vale off -->
<!-- Research briefing: dated evidence with literal identifiers preserved. Not governed prose. -->

# 18 — The Department of War: the Behemoth, the Meta-Cell, and the Imperial Boomerang

Read-only briefing, 2026-10-25. Question: **the Director has added a late-game adversary — the US
Department of War, which "comes home" if the crisis intensifies to civil war, as a boss whose hulking
strength is the source of its arrogance and therefore of its weakness. What is that thing, materially,
and how does it work without adding a primitive or a curve?**

**Ruling under study (verbatim):** "If the crisis intensifies to civil war then the behemoth comes home.
Kinda like a 'boss mode' so to speak. But it's so behemoth it should have its own nested dynamics similar
to the competing agency cells, so it's like a meta-cell that itself is a cell if that makes sense! It is
hulking, massive, lethal, deadly, the most powerful army in world history. But that's also the source of
its arrogance and its weakness… the idea is in Babylon that the US military will do that to Chicago or LA
if it means suppressing the insurgency and killing the revolution."

**Sources.** Krooth, *Arms & Empire: Imperialized Toolmaking and the Ring of War* (scanned, no text
layer; pages 3, 6, 20, 46, 60, 70 read as images). Long, *On "Other War"* MG-482 (2006), ch. 3 and ch. 5
as extracted text. `design/mockups/synopticon/{data,gospel,doctrine}.jsx`;
`ai/epochs/epoch3/{kinetic-warfare,balkanization-spec,warlord-trajectory}.yaml`;
`docs/gameplay/research/{15,16,17}`; `rust/crates/babylon-graph/src/{capacity,dossier,exposure,backfire}.rs`;
`CONSTITUTION.md` (AJ, AK); `docs/gameplay/2026-10-25-porch-02.md`.

**Limits.** Krooth is an image-only scan of a *Harvest Quarterly* reprint, two book pages per rotated
sheet; six sheets were read and nothing below is attributed to unread chapters. The book's centre of
gravity is 1870–1945 (Krupp, Vickers, Schneider, Mitsubishi, the alliance and tariff blocs), not the
contemporary prime-contractor circuit; contemporary claims here are **derived**, not quoted. The "20 per
1,000 inhabitants" force-density figure is in no source in this corpus and appears below only as a
`Calibrated` illustration, never as a define.

**Guardrail.** MIM(P) / MLM-TW. No Trotsky, no permanent revolution, no insurrectionism, no "the army
will mutiny and liberate us." §6 states the four readings this briefing refuses and why.

---

## 0. Thesis

**The Department of War is one outward-facing cell in normal play and a fiscal sub-pool in civil war. It
does not turn inward because it chooses to. It turns inward because inward deployment is the only output
its repertoire can still demonstrate, and demonstration renews its appropriation.**

1. **Its hulking strength is a purchasing decision, not an attribute.** Firepower substitutes for
   knowledge. That substitution is rational for exactly as long as the enemy is *state-shaped* — a
   capital, a grid, a formation. A dispersed political organism has no capital to take, so the repertoire
   is indexed to an enemy type that does not exist in a civil war. Jenkins said it from inside in 1970:
   the Army was built for total war in central Europe and was "unwilling, and to some extent unable, to
   adapt."
2. **The fractal is free.** One institution, several organizations, one parent pool. `allocate` is
   already the local rule; a sub-cell is the same call with a different `owner` and a parent that funds
   it. No primitive, no curve, no authored event.
3. **The boomerang is a conservation law.** Formation-days are finite. Every brigade-day besieging
   Chicago is a brigade-day not enforcing the twelve external markets — and $\Phi$ is the budget the
   brigades are paid from. The spiral contains no coefficients.

---

## 1. What the Department of War is when nothing is wrong

`capacity.rs` is explicit that "the state" is not a node type: `organization` acts, `institution` houses
it, `sovereign` claims territory. The Department of War is one **organization** inside the defence
**institution**, carrying research 17 §4.2's five declared things:

| Field | Value |
|---|---|
| `mandate` | `{DEPLOY, GARRISON, PATROL_SEALANE, TRANSFER_ARMS, ADVISE}` — all aimed *outward* |
| `capacity` | federal appropriation, threat-keyed |
| `dossier` | wide and shallow: signals, basing agreements, foreign order of battle. High on *states*, ~zero on *streets* |
| `jurisdiction` | the twelve external markets, the sea lanes, the forward garrisons — **not** US counties |
| `appropriation` | federal pool; basis is threat level, not service delivered |

### 1.1 Its product is enforceable access, and $\Phi$ is what access yields

$\Phi = W_c - V_c$ originates in unequal exchange (research 15), but a wage/price differential between
Dearborn and Shenzhen is not self-enforcing. Somebody must guarantee that the counterpart keeps the
arrangement: the sea lane open, the debt in the creditor's money, the arms transfer continuing, the
signatory government not replaced. That guarantee is the cell's only real product.

Give each market $j$ an authored enforcement requirement $r_j$ (formation-days per period) and an
allocated amount $d_j$:

$$a_j = \min\left(1,\ \frac{d_j}{r_j}\right), \qquad \Phi_j = a_j \cdot \Phi_j^{\max}$$

The `min` is a cap, not a fitted curve: you cannot enforce more than fully. $r_j$ is `Designed`, authored
in the scenario and captured per campaign (ADR258); $\Phi_j^{\max}$ comes from the twelve
`[counterpart."…"]` blocks whose length the reader already refuses at $\neq 12$.

### 1.2 The conservation identity

$$ \sum_{j \in \text{external}} d_j \;+\; \sum_{r \in \text{domestic}} q_r \;\le\; D_{\text{period}} $$

$D_{\text{period}}$ is the lift-and-rotation budget: what can be moved and sustained for 28 days
(Amendment AK). It is one number, and it is the whole mechanic. There is no separate "imperial decline"
penalty and no escalation threshold. Redeploying home spends a budget that has one owner.

Because $\Phi$ arrives as `Currency` and `Capacity` is `Currency` (ADR184 R8 — the $\Phi \to$
replenishment path "needs no conversion at all"), the trade is direct. No coefficient sits between lost
enforcement and a smaller appropriation. It is the same money.

### 1.3 Why it wants to come home

**Garrisoning produces an outcome; siege produces outputs.** Deterrence is unobservable — a market that
stayed inside the arrangement looks identical whether the brigade deterred a delinking decision or
nothing was going to happen. Sparrow's rule is that overseers want tables that are aggregate, numerical,
comparable, "objective," and unambiguously one agency's contribution, and no outcome can satisfy it.
Sorties, targets serviced, blocks cleared, persons detained and "enemies neutralized" satisfy it
perfectly. Meanwhile the pool shrinks and the threat-keyed line does not, because demand for threat rises
exactly when the pool falls: `threat_keyed_share` rises mechanically and `autonomy` with it (research 17
§4.5).

The conclusion is not a conspiracy. **The Caesar is the agency the depression did not defund, and it
becomes Caesar by doing the only thing it can still show.** No general has to be a villain for this.

---

## 2. The Imperial Boomerang

### 2.1 The trigger is already written

Research 16 §3.6(c): "Civil war is not declared; it is the period in which the QRF calculus has failed in
more than one region at once and the zones begin to coordinate." Porch-02 says the same. Nothing here
changes it:

$$ \left|\{\, r : \text{QRF cost}(r) > \text{pool available to } r \,\}\right| \ge 2 \ \wedge\ \text{zones coordinate} $$

Both sides of that comparison are quantities in the same unit on the same account, so there is no
threshold constant — only "can this pool afford this operation this period," which `allocate` already
answers and whose *decline* is already a typed return.

### 2.2 The substitution, and what it costs

| Move | Buys | Spends | Breaks |
|---|---|---|---|
| Recall a brigade from a market | one more `q` domestically | $d_j$ | $a_j$ falls; that counterpart re-prices delinking |
| Extend rotations | more `q` without recall | `D` beyond one period | cohort grievance (§4.1) |
| Raise firepower per formation | same `q`, more effect | munitions, and CDE (§5.2) | destroyed $K$ (§5.1) |
| Call up the Guard | cheap `q` in-period | the state pool, not federal | the reserve is a cell with its own grievance |

The third row is the trap: firepower is the cheapest way for this cell to buy effect with a fixed
formation count, which is why it reaches for it, and why it loses.

### 2.3 The spiral, in five links, with no coefficients

1. QRF failure in $r_1, r_2$ re-prices domestic deployment above external garrisoning.
2. Formations move home; $d_j$ falls; $a_j$ falls; $\Phi$ falls.
3. The pool is smaller *and* more threat-keyed. Service lines — including the tonnage and sustainment the
   domestic deployment needs — are cut proportionally.
4. The deploying formations hit `OVERSTRETCHED` and their `allocate` begins *declining* candidates for
   lack of fuel and ammunition (§5.3). The shortfall is typed and visible.
5. The cell substitutes firepower for the precision it can no longer afford → more $K$ destroyed → the
   fraction that owns $K$ withholds → the pool contracts again.

Every link is a budget or a ratio of same-unit quantities. **No sigmoid, no second fixed response curve,
no escalation threshold anywhere.**

### 2.4 The periphery answers, because the twelve markets are cells too

This makes it a boomerang rather than a withdrawal. Each counterpart is a finite economy in the kernel
with its own wage/price pair and its own local maximum: stop paying the differential. When $a_j < 1$ its
`allocate` re-prices on the same yield-per-unit arithmetic — settle in a non-dollar channel, raise a
tariff or duty (the trade system owns these; research 15), source from the semi-periphery whose wage/OCC
upgrade is already squeezing $\Phi$, or simply wait, because a guarantee visibly withdrawn is a
guarantee. Delinking is therefore the argmax of a cell that has observed $a_j < 1$, not an event the
scenario authors.

### 2.5 Israel is the live demonstration, and it cannot be recalled

Porch-02 and research 15 pin the arrow: US imperialism → Israel as forward garrison, never the reverse.
That makes it the one external commitment with *domestic political enforcement* — a congressional line, an
arms pipeline through Midwest plants and port/rail corridors, and a franchise with its own expansionist
contradictions that periodically drags the metropole into bailing it out. So it is the **least
recallable** commitment, and therefore where the boomerang bites first: formations come home from *other*
markets while this one holds, and the visible delinking appears in West Asia, Latin America and Africa
before it appears anywhere else. It is also the **doctrine-transfer exhibit**; §5 argues the transfer home
is materially different, and that the difference is the whole boss fight.

---

## 3. The fractal meta-cell

### 3.1 Why nesting is legal

"A meta-cell that itself is a cell" needs no new type. `Capacity` carries `owner: NodeId` with no
`Default`; `Candidate.actor` names who pays; `allocate` rejects a candidate whose actor is not the
budget's owner. Research 17 §4.5 already proposed **nested fiscal pools** precisely because nesting
preserves CA locality: cross-pool competition becomes a boundary interaction, not a global auction.

```
federal pool
  └── DoW pool  (owner: dow_organization)      ← level 1: allocates MISSIONS to sub-cells
        ├── air_targeting    (owner: …)        ← level 2: allocates INSTRUMENTS to targets
        ├── heavy_ground     (owner: …)
        ├── jsoc_intel       (owner: …)
        ├── primes           (owner: …)
        └── enlisted_cohort  (owner: …)
```

Level 1 ranks sub-cells by demonstrated output per unit of parent money — the same yield-per-unit
ranking, one order of magnitude up. Level 2 is the unchanged `allocate` over each sub-cell's own
`Dossier`. Both run synchronously inside one tick before publication, with the same determinism
discipline: `BTreeMap` iteration, total order, seeded realization, fold into `NominalWorldHash` after the
detached tick succeeds.

**The meta-cell is a pool, not an actor.** That is what stops the fractal becoming a homunculus: the
Department of War has no will its children execute. It has a ranking of its children, the children have
rankings of their own, and the two rankings disagree — which is the whole point of §3.3.

### 3.2 What unfolds, and what does not

| Unfolds | Stays |
|---|---|
| the appropriated pool, split into sub-line items | the `mandate` grammar (content, BSL) |
| the dossier, forked per sub-cell — they stop sharing | `decapitation_value`, `Backfire`, `exposure` |
| jurisdiction: sub-cells get `PRESENCE` on US territories | the conservation accounts |
| the ranking of instruments inside each sub-cell | the strike kernel (§5.2) |

**Dossier forking is the fracture.** In normal play there is one DoW dossier; on unfold there are five,
and each resolves different things at different prices. Air resolves signatures; ground resolves terrain
and routes; JSOC resolves individuals; the primes resolve nothing (they do not target); the cohort
resolves *the street* and is forbidden to price it (§4.1). Five beliefs over one substrate, and per
`dossier.rs` they must be able to disagree — the anti-omniscience contract made checkable.

### 3.3 The conflict set

| Contended | Contenders | Why it is real |
|---|---|---|
| Fuel and tonnage | air vs ground | a surge of sorties is a surge of JP-8 on the same rail graph the armor needs |
| ISR hours | air vs JSOC | one drone cannot both service the queue and stake out a named individual |
| **CDE ceiling** | air **up**; ground and JSOC **down** | rubble blocks armor routes, and a flattened block destroys the human intelligence JSOC was cultivating |
| Dossiers | JSOC vs Army vs FBI | a file is a title deed to jurisdiction (research 17 §2.3); whoever holds the informant holds the case |
| Credit for "cleared" | air vs ground | the Air Force flattens a block, the Army "clears" it and books the clearance. One output, two claimants |

The CDE row is the sharpest. **The ceiling is not a moral slider; it is the price of the queue.** Air
raises it because the alternative is `declined`; ground wants it down because it has to drive through the
rubble; JSOC wants it down because its product is a living person who talks. When the player can see those
three positions, the ceiling stops being a number and becomes a coalition question inside the enemy.

---

## 4. The five sub-cells

**No sub-cell's local maximum is "win the war."**

| Sub-cell | `mandate` | Belief | Local maximum | Appropriation basis | Failure its success produces |
|---|---|---|---|---|---|
| **Air / Algorithmic Targeting** | `STRIKE_AIR`, `ISR_SORTIE`, `TARGET_DEVELOP`, `BDA` | wide, shallow, high on signatures, **zero on streets** — the Lavender/Gospel cell | queue clearance per sortie, zero friendly casualties | sorties, targets serviced, "neutralized" | ceiling rises to clear the backlog (§5.2); decoys struck; rubble booked as attrition, which raises the survivors' scores and refills the queue |
| **Heavy Ground** (Army/Marines) | `CORDON`, `CLEAR`, `HOLD`, `CONVOY` | medium, territorial: routes, bridges, load ratings | ground held, route-days open, tonnage delivered | brigade-days, tonnage, "cleared" polygons | disperses to hold, so it starves; checkpoints become rent; "cleared" reverts the day the brigade leaves |
| **JSOC / Military Intel** (DIA/NSA) | `RAID_NIGHT`, `INFILTRATE`, `DECAPITATE` | narrow, deep, individual | named individuals removed | high-value targets, no casualties | `decapitation_value` is a quotient, so it hunts only singletons; every raid indexes a family that becomes a candidate |
| **Primes** (contractors) | `PRODUCE`, `SUPPLY`, `REPLACE`, `LOBBY` | none — it prices | munitions burned + cost-plus replacement + share price | contracts, congressional line, the bourse | prefers the expensive round; no interest in termination; destroys its own customer's fixed capital |
| **Enlisted cohort** | `OBEY`, `LOAD`, `FIRE`, `REFUSE`, `LEAK` | **the street** — with no mandate to price it | survive the rotation, get home | pay, benefits, rotation | fragging, leakage, refusal; mutiny is a budget event before a political one |

**Air is not the dangerous one; it is the visible one.** It cannot verify that the block it flattened was
the target, because it does not own the ground. Its deadliness and its political fragility are one
property: it produces the rubble that breaks the finance-capital settlement (§5.1).

**JSOC hunts singletons and hoards the file.** Because `decapitation_value = Δφ(v) / |signature-class(v)|`
is a quotient, JSOC's own metric pushes it toward Sparrow's role-uniqueness: the courier who knows
everyone, the printer, the old cadre with no replacement (research 17 §1.5). Its failure is that every
night raid manufactures a family that is now *indexed* — the survivors have files, and files are
candidates. It also withholds: tip the Army's cordon toward a JSOC target and watch JSOC protect the asset
by burying the case. Malinovsky and Azef, federal-to-federal.

**The primes carry Krooth's material at a century's distance.** The armament firm is "a state within a
state": fixed costs spread over volume, permanent excess capacity, dependence on state orders and export
dumping, and profits from larger arms orders that surpassed those from fitting out troops (Krooth
pp. 78, 126–127, including his per-capita armament-tax table). His conclusion is the one a game needs:
**arms orders are more profitable than troops, so the firm's interest is the order book, not the war's
outcome.** That is cost-plus in one sentence: the primes are a supplier with a burn-rate objective, never
a patriot with a preference.

### 4.1 The cohort, and the MIM(P) correction

The cohort is the only sub-cell with beat-level legibility and no mandate to price it. Davis & Cragin's
finding that messages must be "built by people with a close understanding of those particular audiences"
is a statement about this cell: the knowledge sits in the part of the apparatus with no authority to use
it, and it cannot be transmitted upward without becoming the wide, shallow thing that cannot find a safe
house. Its local maximum is to survive the rotation and get home; its failure is fragging, leakage and
refusal; its mutiny is a budget event before a political one (research 17 §4.7). The fracture is to make
its material condition worse than the crowd's — February 1917, where the garrison was aggrieved before it
was sympathetic.

**The correction, and it is not optional.** A disaffected cohort is a *decomposition of the enemy's
instrument*, not a liberation. Research 16 records the one usable sentence from `stinsur.html`: liberation
does not arrive from a segment of the conquering army. Its maximum contribution is that the cheapest
instrument the state owns — territory-level mass action needing no dossier — stops being available. The
people still have to win it themselves. A design that lets the player *win* by flipping a division has
reproduced the Trotskyist fantasy in mechanical form.

**And the national question is inside this cell.** The army that would shell Chicago is recruited
disproportionately from the internal semi-colonies and from the settler working class. That is not
sentiment; it is two material positions in one body — a wage and a citizenship premium on one side, an
order to die for a differential that accrues to somebody else on the other. The local maximum can flip
because those two positions cannot both be satisfied.

---

## 5. Why its hulking strength is its weakness

Three mechanisms, three kinds of failure: financial, epistemological, logistical.

### 5.1 Destroying constant capital, and colliding with finance capital

Bombing Chicago or Los Angeles does not destroy the insurgency's means of production. It destroys
**constant capital**: plant and equipment, rolling stock, commercial real estate, the municipal utility,
the bond collateral behind it — and the *assessed value* a particular fraction holds. Write the ledgers:

$$ \Delta V_{FC} = -\sum_{\text{strikes}} \big(\text{plant} + \text{improvements} + \text{bond collateral}\big) $$
$$ \Delta \Phi_{\text{federal}} = +\ \text{enforcement secured} $$

**These never net, because they have different owners.** The gain accrues to the federal pool, the loss to
Finance-Capital's stock; `Capacity` is per-owner for exactly this reason. Finance-Capital's decisive power
is not coalition weight but the ability to *withhold* — investment strike, capital flight, bond market —
and that is what ends Bonapartist adventures which threaten accumulation (research 17 §4.1). So the
fracture needs no threshold: it declines to fund a cell whose operations reduce its own stock.

**This is the material difference between Gaza and Chicago, and it is the whole boss fight.** Abroad, the
destroyed built stock is not on the metropole's balance sheet, the dead are not voters, and the press is
not inside the wire. Domestically all three invert at once. The same doctrine that is *cheap* in a forward
garrison is *expensive* at home — not for moral reasons, but because the destruction lands on the fraction
that pays for the state.

**And the trap for the player.** The obvious play — "let the behemoth destroy its own base" — is
available and is a trap, because the destroyed plant employs the player's own mass base and the destroyed
bond collateral is the municipal fund behind the clinics and schools the player's dual power depends on
(research 16 §3.6(b)). A player who wins the finance-capital fracture by losing the city has won the state
and lost the base. That cost should be legible before the choice, not after.

### 5.2 Algorithmic blindness: high firepower, near-zero local legibility

The Synopticon's epigraph is the specification: *"The State does not hate you. The State processes you."*
The mechanism is a resolution problem, and it derives.

**Step 1 — the unresolved fraction.** The state can enumerate *persons* in a territory without resolving
*who they are*: census, utility hookups, permits, filings, school rolls. With $P_t$ that enumerated count
and $L_t$ the resolved nodes,

$$ u_t = 1 - \frac{|L_t \cap P_t|}{|P_t|} $$

Two counted quantities, no fitted constant. This is the honest content of "the Okhrana had files on every
committee in Petrograd and no file on the bread queue": it knew how many hundred thousand people lived
there, not which two hundred were organized.

**Step 2 — collateral is the shadow of ignorance.** To be *sure* of a target $x$ you must destroy the part
of its neighbourhood you cannot resolve:

$$ \mathrm{CDE}_{\min}(x) = u_{N(x)} \cdot |N(x)| $$

This is why the ceiling rises with nobody deciding to be cruel. The queue cannot be cleared at a low
ceiling because the dossier cannot support a low ceiling; the ceiling is raised so the queue is fundable
at all. **The Gospel does not skip — it holds** (the mockup's own line). A queue that holds produces no
demonstrable output, which is a budget problem for the cell. The ceiling moves.

**Step 3 — the strike resolves as a finite kernel, not a roll.** Amendment AJ gives the instrument: a
finite material transition kernel $K : C \to D_f(\Delta)$ over a typed enumeration of bounded effect
bundles, with exact mass. For a strike on $x$ the delta set has two elements:

$$ \Delta = \{\text{ATTRITION},\ \text{BLOWBACK}\}, \qquad
K(s,\text{BLOWBACK}) = \frac{p_{N(x)} + i_{N(x)}}{|A_{N(x)}|} $$

$p$ and $i$ are `Backfire`'s protected and interpreted counts — **counts of people in a structural
position**, whose sum is a measure in $[0,1]$ by construction because the cells are disjoint. Integer
counts give an exact rational admitted as `Mass`; nothing is sampled, nothing approximated, no event
carries an authored likelihood. The mockup's `Math.random()` and `decoy + 0.2` are mock data, and porting
them would be an ADR172 ruling-5 violation.

**Step 4 — the machine eats its own error.** The best idea already in the Synopticon:

> "ASSESS_MODULE will attribute the rise in agitation to insurgent activity, not to this strike. The
> Lavender score of nearby nodes will rise as a result. The system will recommend more strikes."

$$ L_{t+1} = \mathrm{reconcile}(L_t, \text{scope}) \cup \{\text{strike artifacts}\} $$

and **the artifacts are state-authored.** The state's own violence becomes evidence of the enemy's
strength, which justifies the violence: the apparatus manufactures the threat it is funded to meet. This
is research 17 §4.5's Bonapartist loop in a new register, and it is why the boss cannot de-escalate even
when de-escalation is winning.

**Step 5 — the boundary of the cut.** Where both `Backfire` channels are near zero the strike suppresses
(Santiago de María); where either is substantial the same act recruits. Kalyvas's mechanism is structural:
indiscriminate violence does not depolice a zone, it **clears the middle** — the uncommitted lose the
option of being uncommitted and attach to whoever can protect them. A flattened block is therefore not a
cost in legitimacy points but a *transfer of the uncommitted to the other side*, executed by the state and
booked as a success. The report the state reads says the block was enemy-held. It is not lying and it is
not stupid. It is reading its own handwriting.

### 5.3 The logistics tether

A mechanized force is a **flow**, not a stock. It consumes tonnage per formation-day — fuel, ammunition,
water, parts, and the tonnage to move the tonnage — so the binding constraint is feasibility, not enemy
action:

$$ \sum_{f} \tau_f \cdot n_f \;\le\; \sum_{e \in \text{rail} \cup \text{port}} c_e \cdot (1 - x_e) $$

$\tau_f$ is the per-formation-day requirement (authored, kg per 28-day period — the unit `shared_freight`
already uses), $c_e$ edge capacity, $x_e \in \{0,1\}$ interdiction. When the inequality fails the
formations get no penalty: they get **`AllocationOutcome.declined`**, with the shortfall carried. "Wanted
the armored sweep, could only afford the foot patrol," visible and typed.

Three properties make this the most player-legible of the three weaknesses:

- **Asymmetry of obligation.** The state must keep the line open *continuously*; the insurgency must close
  it *once*. Mao's interior/exterior-line relation run in reverse: the state fights on interior lines and
  must therefore defend everything, while the insurgent chooses the point.
- **Dual-use bites the state too.** Rail and port edges carry high `collateral_risk` for the *state*,
  because the state's own sustainment runs on them. `kinetic-warfare.yaml` built that field for the
  player's attacks; read from the other side it says the behemoth cannot cut its own tether to deny it.
- **Weight is a map fact.** A 60-tonne vehicle needs a bridge rated for it, and there are few. Debord and
  Mao coincide: the spectacle of the armoured column is also its itinerary, and an itinerary is a target
  list. The player does not defeat the column; the player learns which three bridges it must cross.

---

## 6. What the player does — and the four readings that are refused

**Levers, each already a mechanic.**

1. **Force the periphery choice.** Internationalist work on the Israel supply chain — ports, rail
   corridors, Midwest arms plants (research 15) — raises the value of external enforcement at the
   same moment it raises the cost of pulling formations home. Both branches become expensive.
2. **Cut the tether.** Interdict the rail/port edges the tonnage identity needs. Undramatic; the effect
   appears as declines inside the enemy's own funding list.
3. **Feed the machine legibility.** Manufacture a decoy: a legible artifact with high centrality and zero
   revolutionary value. This is an *information* operation, spending Heat and exposure rather than cadre,
   and if it fails the block pays.
4. **Split the ledgers.** Concentrate the contest where the built stock belongs to Finance-Capital and the
   population is not expendable to it. Downtown, not the block. The fracture then appears as a withholding
   decision rather than a debate.
5. **Work the cohort.** Material condition, not propaganda: rotation, stop-loss, casualties, pay.
6. **Steal the dossier.** Learn the blank spaces and organize there. The svodki that made the Okhrana
   formidable are the documents that convicted it (research 17 §2.4).

**Refused, with reasons.**

- **"The state splits, so push militarily."** Redundancy is the apparatus's resilience: of 648 groups
  ending 1968–2006, 43% politics, 40% policing, 10% victory, 7% military; in high-income states 92 of 96
  fully-ended groups ended via policing or politics (research 17 §3.3). A player who reads the turf war as
  weakness has built on a false premise and loses to the redundancy. The object is cost, not collapse.
- **"The army will mutiny and liberate."** Liberation does not arrive from a segment of the conquering
  army. The cohort decomposes an instrument; the people still have to win.
- **"Armed insurrection in the metropolis."** Research 16's focoism result stands: "never more than a
  flash of fury," plus a legitimacy transfer to the state. `kinetic-warfare.yaml`'s Isolation Spiral is
  the game-over for the player who takes that line against the behemoth.
- **"The behemoth is a monolith."** Also no — it is five cells with five beliefs and none of them is the
  war. But the opposite error is worse: treating the fracture as victory.

**And the one thing the player must not do:** treat the destroyed city as a resource. The municipal fund,
the plant, the clinic, the school and the bond collateral are one object. A player who trades the city for
the fracture has reproduced the state's accounting error with the sign reversed.

---

## 7. What the mockup already gets right, and the six things to change before porting

The mockup is design evidence and says so: "every entity is a code, not a name… the state does not see
people, it sees nodes." Keep that. Change these:

| Mockup | Problem | Replace with |
|---|---|---|
| `Math.random() < target.decoy + 0.2` | magic coefficient plus a sample | the AJ kernel, mass $(p+i)/\lvert A\rvert$ from integer counts |
| `legit_delta: -0.30 / -0.04` | authored legitimacy constants | `Backfire.total()` over the affected population |
| `agit_delta: 0.50 / 0.08` | authored agitation constants | the structural transfer: uncommitted nodes lose the neutral option |
| `cde_policy: 12` on a slider | reads as a moral choice | $\mathrm{CDE}_{\min}(x)$; the ceiling is the price of the queue |
| `threads_total: 320` | reads as a stat | `Currency` in the owning cell's `Capacity`, replenished from the pool |
| `coverage_pct: 0.78` | free-floating percentage | $u_t$ over an enumerated denominator, per territory |

Two things to keep exactly: **"The Gospel does not skip — it holds"**, and the Assess note that the system
will attribute the rise in agitation to the insurgent. Those two sentences are the boss.

---

## 8. Evidence classes, prohibitions, and falsifiers

| Claim | Class | Note |
|---|---|---|
| Firepower-intensive repertoire is institutional, not a doctrinal choice | **Observed** | Komer (1972), Jenkins (1970) via Long MG-482 pp. 42–43, verbatim |
| Outputs are measurable, outcomes are not, and the metric becomes the repertoire | **Observed** | Sparrow via research 17 §3.2; Long ch. 3 on body count and HES |
| Armament firms optimize the order book, not the war's outcome | **Observed** (hist.) | Krooth pp. 126–127; 1870–1945, not the contemporary circuit |
| Formation-days are conserved; $\Phi$ and `Capacity` share a unit | **Derived** | `capacity.rs`, ADR184 R8: no conversion coefficient exists |
| Redeployment lowers $a_j$ and therefore $\Phi_j$ | **Derived** | §1.1; the `min` is a cap, not a curve |
| The periphery re-prices delinking when $a_j < 1$ | **Derived** | each counterpart is a cell with its own argmax |
| $\mathrm{CDE}_{\min}$ follows from the unresolved fraction | **Derived** | §5.2 — this briefing's main original claim |
| Blowback mass $=(p+i)/\lvert A\rvert$ | **Derived** | `backfire.rs` measures; ADR172 ruling 5 |
| Domestic $K$ destruction breaks the finance-capital settlement | **Derived** | two ledgers, different owners; research 17 §4.1 |
| Force-density figures | **Calibrated — unverified** | in no source here; must be sourced before becoming a define |
| $r_j$, $\tau_f$, $D_{\text{period}}$, sub-cell line items | **Designed** | scenario-authored, typed, captured per campaign (ADR258) |
| Five sub-cells and their local maxima | **Designed** | a modelling choice; §9 says how it can be cut |

**No new primitive.** Everything composes from `Capacity`, `Dossier`, `exposure`, `Backfire`, $\Phi$,
`reproduction_capacity` and the existing conservation accounts. The meta-cell is a *pool* — a composition
of `Capacity` owners, not a new kind. `FormationDay` and `Tonnes` are accounting vocabulary in existing
conservation machinery: governed content, not mathematics.

**No sigmoid, no second fixed response curve, no escalation threshold.** Every quantity above is a ratio
of same-unit quantities, an integer count, or an exact rational. The `min` in $a_j$ and the `≤` in the
tonnage identity are a cap and a feasibility bound, not functional forms.

**No authored terminal branch (AJ).** "Boss mode" is not an event the scenario fires; it is what the
arithmetic does when the QRF comparison fails in two regions. `on_civil_war: deploy_dow()` would replace
the design with a script.

**Displays.** Each surface answers one decision question: the *enforcement ledger* ("which market do I
stop enforcing, and what does it cost me there?"), the *sub-cell conflict board* ("which of the five do I
starve this period?"), the *tether map* ("which three bridges?"), the *CDE ledger* ("what does this queue
item cost in buildings?"). No administrative display passes a gate.

**Falsifiers.**

1. If a campaign that never redeploys shows the same peripheral delinking as one that does, $a_j$ is
   decorative and §1.1 is wrong.
2. If the finance-capital fracture appears without domestic constant capital being destroyed, there is a
   hidden coefficient and §5.1 is wrong.
3. If the player's best response to every sub-cell is the same move, there is one sub-cell, not five, and
   the table should be cut to two — air and cohort.
4. If $\mathrm{CDE}_{\min}$ can be lowered without raising dossier resolution, the ceiling is a slider and
   §5.2 is wrong.
5. If the cohort mutinies without its material condition moving, the mutiny is a scripted event and
   should be deleted rather than faked.

---

## 9. Open questions for the Director

1. **One organization that unfolds, or five from tick zero?** This briefing models one organization
   unfolding into five on the same parent pool. Five from the start, with outward garrisoning merely the
   largest line item, is simpler and makes "boss mode" a *visibility* change rather than a structural
   one. The first is truer to how the Director described it; the second is cheaper.
2. **Does the cohort get a morale term, or is it `Backfire` read backwards?** Research 17 §4.12 asked
   this and it is still open. A mutinous reserve is a loyalty fact; `Backfire` measures the affected
   population's structure. Probably two quantities, and probably not one name.
3. **Is the domestic deployment's legal predicate a resource?** In the real apparatus the Guard call-up
   and the federal deployment each need a predicate with a political price. Modelling it as an instrument
   of the electoral screen would give the player a non-military lever on the behemoth — exactly the kind
   of lever the line prefers.
4. **Trajectories A and B are one branch here.** `warlord-trajectory.yaml` has the military stay with the
   bourgeoisie while the police form the revanchist coalition. If the DoW is home and besieging cities,
   trajectory A's condition ("bourgeois solvency AND military loyalty") is being tested by the same
   events that produce trajectory B. Read them as one branch.
5. **Which city first?** The Synopticon's heat zones are Detroit, Chicago, the Bronx, Long Beach, Oakland;
   the Director named Chicago and LA. The choice is material: LA's built stock is entertainment and
   logistics capital, Chicago's is rail, plant and finance. The first siege should follow the player's
   base-area geography, never a scenario constant.

---

## 10. Summary

The Department of War is not a boss with a health bar. It is the one cell whose product was always
unverifiable, and therefore the one that gains most from a war it can *show*. It comes home because home
is where the outputs are, and it flattens a block because a block is the only thing its dossier can
resolve. Its five sub-cells fight over one parent pool and one CDE ceiling, and its enlisted cohort is
drawn from the class and the nations it is ordered to shell.

Its strength — substituting firepower for knowledge — is exactly the substitution that destroys the
domestic constant capital of the fraction that pays for it, on a logistics graph it cannot cut without
cutting itself. The behemoth is not defeated. It is made expensive in three currencies at once: money it
must borrow from the fraction whose buildings it destroys, tonnage it cannot move over bridges it is
trying to hold, and legitimacy it spends purchasing the allegiance of the uncommitted by killing them.

A player who understands that does not beat the army. A player who understands that makes the army's own
accounting come apart, and then does the political work of being the thing the block attaches to instead.
That is the boss fight, and it is the same fight as the rest of the game, one order of magnitude up.
