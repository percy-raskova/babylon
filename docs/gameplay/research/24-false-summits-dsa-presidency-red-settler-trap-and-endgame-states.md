<!-- vale off -->
<!-- Research briefing: dated evidence, literal identifiers preserved. Not governed prose. -->

# 24 — The False Summits: DSA in the White House, the Red-Settler Trap, the Warlord Archipelago, and What Winning Is

Read-only design briefing, 2026-10-25. Nothing here implements or changes game law.
Claims about shipped code cite the file; proposals say **proposed**; conflicts between an
old YAML and landed code are named and resolved toward the code.

**The question.** Babylon has no Fukuyama screen and no rails. A player who downloads this
game to prove that DSA electoralism works — or that "workers unite" socialism works without
decolonization — must be able to *win*, and then must be made to live in what they won.
What are the exact state transitions that carry that player from the summit to the receipt?

**Answer in one line.** A summit is an **address**, not a verdict: four reachable positions on
the cusp surface Babylon already computes, distinguished by which fiscal pool paid, whose
extraction continued, and how much autonomy the coercive cells acquired. Nothing is authored
as an ending; every ending is a fixed point of arithmetic the engine already runs.

**Sources.** Read directly today: `ai/epochs/epoch3/{balkanization-spec,warlord-trajectory,
cohesion-mechanic,reactionary-subject,political-economy-liquidity}.yaml`;
`specs/070-balkanization/spec.md` (FR-029…FR-040); `specs/095-endgame-chronicle/{spec.md,
contracts/endgame.yaml}`; `docs/gameplay/{2026-10-25-porch-01.md,2026-10-25-porch-02.md}`;
`docs/gameplay/research/{10,12,13,15,16,17,18}.md`; landed BSL at
`rust/crates/babylon-tick/content/rules/{fundamental-theorem,imperial-rent,metabolism,
production,territory,control-ratio,decomposition,consciousness}.bsl`;
`rust/crates/babylon-tick/src/phase_order.rs`;
`rust/crates/babylon-material-circuit/src/financial/model.rs`;
`rust/crates/babylon-client/src/decision_surface.rs`.

Primary texts: Marx, *Capital* Vol. I ch. 15 §10 and ch. 26 (verbatim, this host);
Marx, *The Civil War in France* and *Critique of the Gotha Programme* — **the full bodies are
absent from this host**; the load-bearing sentences reach this briefing through the 1871
index page and Lenin's verbatim quotations in *The State and Revolution* ch. 2, and are
flagged where used. Lenin, *The State and Revolution* ch. 2 and *The Collapse of the Second
International* ch. VIII (verbatim, this host); *Imperialism* ch. 2–3 only (ch. VIII, the
parasitism/labour-aristocracy chapter, is **absent**). Stalin, *Foundations of Leninism*
ch. VI — **absent**; cited as standard text and flagged. Mao, *On the Correct Handling of
Contradictions Among the People* §I and §VI (verbatim, this host). MIM:
`MIM.essays/democratic.socialism`, `MIM.essays/indigenous.unity`,
`contemp/cons/exploiterpatriotism.html` (verbatim, this host).

**Guardrail.** MIM(P) / MLM-TW. No Trotsky; Trotskyism appears only as the class-reductionist
trap. No teleology: the DSA player is not scripted to lose, and the design must survive the
possibility that they win and keep winning.

---

## 0. Two theses and one inversion

### 0.1 The summit is real, and reaching it is the tutorial

`10` §2.6 rules the shape: the refusal is never at the door, it is at **incidence**. That rule
must survive contact with the national tier. A player who spends forty periods building a
big-tent coalition, taking county parties, winning the statehouse, and finally holding both
chambers and the presidency has done something the engine permitted at every step. There is
no moment where the game says *no*. There is a moment where the budget says *who pays*.

So the electoral screen's ceiling is not an office the player cannot reach. It is the one
verb set that has no federal form: **no act of Congress, no executive order, and no treaty
reaches Φ.** Not a locked button — a mechanism the player can hit from four different
coalitions and get the same receipt from. `10` §2.4 states it; this briefing makes the receipt
computable.

### 0.2 A summit is an address on a surface the engine already draws

`13` §4.4 already places Babylon's politics on a cusp surface whose two control parameters
are measured state snapshots, not authored dials:

- `r ≡ Φ_t` — the imperial-rent gap (`13` §3.4: `Φ_t = W_c,t / V_c,t − 1`);
- `h ≡ O_t / R_t` — the correlation of forces (`13` §3.7: organization over repression).

`13` is explicit: "Do not script the regions. 1905, 1917, 1933 are not three points the
engine must visit. They are three *addresses* on a surface the engine computes." The four
endgames below are four more addresses. None of them needs an event type that says "now the
story turns." Each is where the arithmetic settles when a particular set of receipts
accumulates.

### 0.3 The inversion that makes the trap experiential: **stance is declared, policy is observed**

`balkanization-spec.yaml` derives the sovereign's `extraction_policy` *from* the ruling
faction's declared `colonial_stance`:

```yaml
extraction_policy:
  derived_from: "ruling_faction.colonial_stance"
```

That makes the label sovereign. A player types `ABOLISH`, the pipeline becomes moral, and the
game has taught the opposite of its own thesis. **Proposed inversion:**

| Quantity | Kind | Written by | Read by |
|---|---|---|---|
| `colonial_stance` | **declared claim** — an overlay | the faction's programme (authored, or the player's Line/Doctrine choice) | the Chronicle, the Corporate Feed, other factions' polemics |
| `extraction_policy` | **observed material fact** | the sovereignty slot, from the period's extraction receipts on claimed territories | every endgame predicate, the metabolic ratchet, the Ticker |

`extraction_policy` is then a *read* of `territory/extraction-intensity` and
`territory/production-total` (both landed fields, §2.2 below) over the claimed footprint, not
a transcription of a slogan. A programme that says Land Back while the tonnage is unchanged
produces `CONTINUE`. The engine judges; the narrator quotes the programme back at the player
next to the tonnage table. That is `AGENTS.md`'s "AI can parse, retrieve, and narrate. Only
the engine judges mechanics" applied to the one place it matters most: the player's own
professed politics.

This is also the honest reading of Mao §VI: "The key to this question lies in overcoming Han
chauvinism." Chauvinism is not a belief you renounce in a programme; it is a relation you
stop reproducing in practice. A stance enum cannot hold that. A receipt can.

---

## 1. Theoretical grounding

### 1.1 Marx — the machine is not inheritable, and the soil is not a metaphor

**The state machine.** Lenin quotes the *Eighteenth Brumaire* to fix the point, and the
sentence is the one the whole DSA fork turns on: "All revolutions perfected this machine
instead of smashing it. The parties that contended in turn for domination regarded the
possession of this huge state edifice as the principal spoils of the victor."
(`staterev/ch02.htm`, verbatim.) Lenin's gloss: "all previous revolutions perfected the state
machine, whereas it must be broken, smashed… This conclusion is the chief and fundamental
point in the Marxist theory of the state." The 1871 index page carries the compressed form:
"But the working class cannot simply lay hold of the ready-made state machinery, and wield it
for its own purposes."

Applied: winning the presidency is *taking possession of the spoils*. The machine is not
neutral hardware the winner operates; it is a set of cells with their own appropriations
(`17` §4.5). The DSA administration inherits the cells, not the capacity to command them.

**The soil.** *Capital* Vol. I ch. 15 §10, verbatim from this host:

> "Capitalist production, by collecting the population in great centres… disturbs the
> circulation of matter between man and the soil, i.e., prevents the return to the soil of
> its elements consumed by man in the form of food and clothing; it therefore violates the
> conditions necessary to lasting fertility of the soil." … "all progress in capitalistic
> agriculture is a progress in the art, not only of robbing the labourer, but of robbing the
> soil; all progress in increasing the fertility of the soil for a given time, is a progress
> towards ruining the lasting sources of that fertility. **The more a country starts its
> development on the foundation of modern industry, like the United States, for example, the
> more rapid is this process of destruction.**"

Marx names the United States as the fastest case. The Red Settler trap is not a designer's
invention laid over Marxism; it is a sentence in *Capital* that the metabolism rule already
implements (§4.3).

**Primitive accumulation.** *Capital* Vol. I ch. 26: "In actual history it is notorious that
conquest, enslavement, robbery, murder, briefly force, play the great part." Land Back is
therefore not a moral supplement to the class struggle; it is the un-doing of the
accumulation that constituted the wage relation on this continent. A socialism that leaves
that accumulation intact has left the founding act of its own working class intact.

### 1.2 Lenin — the fiscal form of betrayal

*The Collapse of the Second International* ch. VIII, verbatim:

> "The initiation of revolutionary activities would obviously have led to the dissolution of
> these legal organisations by the police, and the old party — from Legien to Kautsky
> inclusively — sacrificed the revolutionary aims of the proletariat for the sake of
> preserving the present legal organisations. No matter how much this may be denied, it is a
> fact. **The proletariat's right to revolution was sold for a mess of pottage — organisations
> permitted by the present police law.**"

This is the exact mechanism `12` §5.4 formalises as `survival_interest` and the 260-period
clock — and it is also **Fork 1's engine**. A party with a national apparatus, a staff, a
press, a health-care programme and four years of a legislative calendar has a material
interest in the legal shell continuing. When the shell's continuation requires the Navy, the
shell votes for the Navy. Not because the people in it are cowards: because the shell is
their livelihood, and the livelihood has a budget line.

Lenin's *Imperialism* supplies the other half — finance capital, export of capital, the
rentier — which is why the bond market is not a mood but an actor with an appropriation
(§3.3).

### 1.3 Stalin — the national question is a reserve, not a decoration

*Foundations of Leninism* ch. VI ("The National Question") is **absent from this host**; the
1913 *Marxism and the National Question* is present only as a title page. The standard text
is cited and flagged. Its load-bearing content for this design is not the four-part
definition of a nation. It is the *strategic* claim: the national question in an oppressor
country is not a minority addendum to the class question but a condition of the class
question's resolution, because the oppressed nations are reservoirs of revolutionary force
that the oppressor nation's workers are materially invested in not mobilising.

That is precisely what `balkanization-spec.yaml` encodes as `is_settler_formation: true` with
the note: "Settler workers have a material stake in colonialism (cheap land, jobs on stolen
resources, wages subsidized by imperial rent). This doesn't mean they can't support
decolonization, but it creates contradictions that must be addressed."

### 1.4 Mao — two types of contradiction, and the one that must not be mishandled

*On the Correct Handling of Contradictions Among the People* §I, verbatim:

> "In ordinary circumstances, contradictions among the people are not antagonistic. But if
> they are not handled properly, or if we relax our vigilance and lower our guard, antagonism
> may arise."

And §VI, verbatim:

> "The minority nationalities in our country number more than thirty million. Although they
> constitute only 6 per cent of the total population, they inhabit extensive regions which
> comprise 50 to 60 per cent of China's total area… **The key to this question lies in
> overcoming Han chauvinism.** At the same time, efforts should also be made to overcome
> local-nationality chauvinism, wherever it exists among the minority nationalities."

Two mechanical consequences, and they are the whole of §4:

1. **The contradiction's character is a state variable, not a label.** Mao's "if they are not
   handled properly… antagonism may arise" is a transition rule. The same contradiction
   (Workers' State vs. internal semi-colony) is non-antagonistic under one policy and
   antagonistic under another, and the engine must be able to move it in either direction.
2. **The dominant nation's chauvinism is the key term, not the oppressed nation's.** A
   Workers' State that demands unity while refusing to name the settlers' material stake has
   done nothing about the key. In engine terms: `RED_SETTLER_TRAP_DETECTED` (spec-070 FR-034)
   fires on *the ruling faction's own* high `class_reduction` with a non-ABOLISH material
   record.

### 1.5 MIM — the two outcomes were already written down

`MIM.essays/democratic.socialism`, verbatim:

> "Where democratic socialists DO succeed in coming to power, one of two things happens:
> a. Nothing. Witness Mitterand in France. Case closed.
> b. Something — followed by military coup."

The essay then lists Chile 1973, Iran 1953, Guatemala 1954, the Dominican Republic 1965, and
Brazil 1964, and concludes: "the ballot box only leads to slaughter of the oppressed."

**Fork 1 is (a). Fork 2 is (b).** This briefing does not invent the fork; it transcribes it
and supplies the arithmetic. That is the correct relationship between theory and mechanics
under `AGENTS.md`: theory constrains causes, and the engine computes them.

`MIM.essays/indigenous.unity`, verbatim:

> "MIM also sees that it is not just the Amerikan ruling elites which benefits from their
> oppression of indigenous nations. Rather, throughout the history of Amerika, it has been
> the vast majority of Amerikan citizens, often led by the white working class, who have
> vehemently fought to run indigenous nations out of existence."

That sentence is why `is_settler_formation` must be a material property of a faction and not
an accusation, and why the Red Settler's base — not the bourgeoisie — is the force that
suppresses the secession in §4.

`contemp/cons/exploiterpatriotism.html`, verbatim: "The reason for that is that they believe
Amerikans' votes are just as good as Third World votes, when in fact from a socialist
perspective, **Amerikans are the global headquarters of capitalism**. The democratic
socialists and social-democrats do not see the class line as it actually is globally."

### 1.6 What the theory does *not* license

- It does not license making the DSA path lose. The engine gives the player a real victory
  and a real bill.
- It does not license a "correct line" button. `Line/Doctrine` is a set of branching,
  mutually exclusive, *degenerating* trunks (`porch-02` §4.6), not a tech tree with a right
  answer highlighted.
- It does not license collapse-as-good. `WarlordArchipelago` is a **regressive mode of
  production** (`warlord-trajectory.yaml`), not a revolutionary opening. The apparatus of
  death finds new masters; that is a defeat with a body count, not a phase.

---

## 2. The apparatus: live, declared, proposed

The most important discipline in this briefing is not to describe a system as if it exists.
`03-program-state-and-gaps.md` exists because that mistake is expensive.

### 2.1 What the Rust engine actually computes today

| Quantity | Home | Status |
|---|---|---|
| `Φ` at class level: `social-class/imperial-rent ← wages − value-produced` when `wages > value-produced` | `content/rules/fundamental-theorem.bsl` (14 lines, `:role mechanic`, `:evidence derived`) | **live** |
| Rent pool: `institution/rent-pool`, `institution/rent-tribute-inflow`, from `EXPLOITATION` and `TRIBUTE` edges | `content/rules/imperial-rent.bsl` r00–r04 | **live** (r05–r09 super-wage payment, pool decay and pool-threshold policy are **not landed**) |
| Metabolic ratchet: `territory/biocapacity`, `territory/max-biocapacity`, permanent ceiling damage | `content/rules/metabolism.bsl` `biocapacity-update` | **live** (Phase 1 only; global overshoot + `ECOLOGICAL_OVERSHOOT` **blocked**, D-4) |
| `territory/extraction-intensity = clamp(production_total / max_biocapacity, 0, 1)` | `content/rules/production.bsl` `p4-extraction-intensity` | **live** |
| Carceral control ratio and the terminal branch (`REVOLUTION` vs `GENOCIDE`, threshold `0.5`) | `content/rules/control-ratio.bsl` c03/c04 | **live** (ADR070-reserved branch, verbatim) |
| Labor-aristocracy decomposition into enforcers + internal proletariat, `enforcer-fraction 0.15`, `proletariat-fraction 0.85`, `decomposition-delay 52` | `content/rules/decomposition.bsl` p01–p06 | **live** |
| Necropolitical rules: `CONCENTRATION_CAMP` population decay; `PENAL_COLONY` zeroes tenants' organization | `content/rules/territory.bsl` p4-camp-decay, p4-penal-suppression | **live** |
| Budget receipts with `requested / paid / unfunded` | `financial/model.rs`: `PublicBudget`, `PublicAllocation`, `PublicBudgetReceipt`, `CapitalContributionOrder`, `CapitalContributionReceipt` | **live types** |
| Tax bases | `financial/model.rs`: `TaxBasis::{WageIncome, PositiveOperatingIncome}` | **live**, and **only two** (see §10 Q3) |
| Declared causal slots `electoral` (23), `policy` (24), `sovereignty` (25), `collapse-transition` (30), `wealth-distribution` (32) | `phase_order.rs` | **declared**, no registered system behind most of them |
| `AgencyCell`, `FiscalPool`, `Capacity::allocate` per cell | `17` §4.2–4.5; `babylon-graph/src/{capacity,dossier,exposure,backfire,induced}.rs` | `Capacity`/`Dossier` **live, zero callers**; the automaton itself **proposed** (plan Task 4) |
| `ColonialStance`, `Faction`, `Sovereign`, `INFLUENCES`, `extraction_policy`, `habitability` | `balkanization-spec.yaml`; `specs/070` | **spec-only** — no Rust type, no landed field |
| National electoral tier, seats, offices, franchise | — | **does not exist** (SurfaceId is `TitleLockup`, `CountyDossier`, `ObserverShell`, `ObserverProduction`, `OrganizerWorkspace`) |

Two consequences for everything below. First, the **endgame predicates of §7 are written
against quantities that are partly spec-only**; they are proposals with a named dependency,
not descriptions. Second, the pieces that make the Red Settler trap *provable* —
`production/p4` and `metabolism/biocapacity-update` — are **already live and already coupled
in the causal schedule**. The trap is the one endgame that needs no new system at all.

### 2.2 The four slots every endgame runs through

The scheduler already orders the relevant consequences (`phase_order.rs`, `TickPartition::Consequence`):

| ordinal | slot | what it settles |
|---|---|---|
| 11 | `imperial-rent` | `Φ`, the rent pool, super-wage funding |
| 13 | `control-ratio` | enforcers vs. captives; the terminal branch |
| 14 | `metabolism` | biocapacity, and the permanent ceiling |
| 15 | `decomposition` | labor aristocracy → enforcers + internal proletariat |
| 23 | `electoral` | the vote is adjudicated |
| 24 | `policy` | the vote becomes law and budget |
| 25 | `sovereignty` | claims, ruling faction, `extraction_policy` |
| 30 | `collapse-transition` | secession, sovereign death, endgame settlement |
| 32 | `wealth-distribution` | the `33/33/33/0` partition |

`electoral → policy → sovereignty → collapse-transition` is the exact causal spine of every
one of the four summits. No new phase is required for any of them. That is the strongest
possible argument that these endings are emergent rather than scripted: the schedule already
has the addresses.

### 2.3 The closed federal budget identity

This is the mechanism that turns a political victory into a forced choice, and it is an
accounting identity, not a script:

```
T_w  +  T_K  +  Φ  +  ΔD   =   R  +  S  +  I
```

| term | meaning | what it is in the engine |
|---|---|---|
| `T_w` | taxes whose incidence lands on wages | `TaxPolicy{basis: WageIncome, rate_bps}` |
| `T_K` | taxes whose incidence lands on capital | `TaxPolicy{basis: PositiveOperatingIncome, rate_bps}` |
| `Φ` | imperial rent | **not a policy variable** — a residual of the trade book (`15` §5: "no flow without a source; no rent without a payer") |
| `ΔD` | new debt | *not representable*: `financial/model.rs` has no debt instrument (`10` §2.5 barrier 1 flags this as **proposed**) |
| `R` | repression | the coercive cells' appropriations |
| `S` | social reproduction / transfers | `PublicAllocation{treatment: HouseholdIncomeSupport}` |
| `I` | investment | `CapitalContributionOrder` |

There are **four payers and no fifth**. Every dollar of Medicare-for-All or a Green New Deal
comes out of a wage tax, a capital tax, imperial rent, or a bond market that does not yet
exist in the model. The DSA administration's entire freedom is the *mix*, and each term in
the mix has a named constituency that screams.

That is the whole design of False Summit A. It is also why the fork is not authored: the
player chooses the mix, and the mix chooses the ending.

---

## 3. False Summit A — `FalseSummitDsaPresidency`

> "Correct! Or it could be the DSA wins Congress and AOC is President."

### 3.1 The win, with no invisible wall

**Reachability.** The national tier is `ElectoralTier::Federal` (**proposed**) with three
gates the player must actually clear, each an existing graph fact:

1. **Seats.** Votes go to the party; clout divides the seats inside the coalition
   (`porch-02` §4.2, on `11`'s `CParty::GetVotingPowerFor`). A union local in a popular front
   wins the election for its wealthier liberal partner — which means the player's own base can
   deliver a majority whose *composition* is not theirs. This is the built-in contradiction of
   the big tent and it must be visible in the seat table, not in a modifier.
2. **The executive.** The presidency is a `personification` (`porch-02` §2) over a coalition
   node. It confers the six office verbs at federal reach and **one** non-verb: the pulpit.
3. **The reproduction of the coalition.** `survival_interest` begins accruing the moment the
   apparatus has staff, a press, and a legislative calendar (`12` §5.4). It accrues whether or
   not the player notices, and it accrues *faster* the more the party wins.

**What the office can do.** All six verbs from `10` §2.4 with federal reach: `Space`,
`Budget`, `Non-Cooperation`, `Bail/Pardon/Charging`, `Tribune`, `Appointments`. The `Tribune`
verb is the strongest and the most underrated: subpoenas force hidden facts into the intel
ledger, which means the DSA administration can *publish* the rent — and publishing is not
redirecting.

**The verb that does not exist.** No federal act reaches `Φ`. `fundamental-theorem.bsl` is
twelve lines and it is the whole argument: while `wages > value-produced`, the gap is
imperial rent, and no appropriation changes it. A bill that claims to redistribute it either
fails at incidence — the cost lands on the workers it meant to help — or becomes a claim *on*
the rent, which is the `bigger-slice` trap of `06-mimp` §6. The player may reintroduce that
bill in four different coalitions and will get the same receipt each time. That repetition is
the pedagogy.

### 3.2 The first period after the inauguration: the arithmetic arrives

At `policy` (24) the new administration writes its first budget. Four candidate mixes, and
the player must pick one because the identity has no slack:

| Mix | Engine effect | Whose receipt shows it |
|---|---|---|
| **Wage-funded** (`T_w` up) | price level on wage-goods rises via the settlement book (`15` §11) | internal proletariat: `P(S|A) = (1/N)Σ 1[w_i ≥ s_i]` falls (`13` §3.7) — the base that elected you |
| **Capital-funded** (`T_K` up) | `CapitalContributionOrder` returns `paid < requested` | `CapitalContributionReceipt.unfunded > 0`; the clinic, the grid link, the retrofit does not happen |
| **Rent-funded** (`Φ` up) | requires `ActiveDuty` in `ExternalGarrison` and `CorridorCapacity` restored | the periphery's `Φ` side of the identity (`15` I1, I3); the movement's internationalist flank |
| **Debt-funded** (`ΔD` up) | **no instrument exists**; the honest version is `PublicBudget.period_cap` refusing the allocation and `PublicBudgetReceipt.unfunded > 0` | the rating agency line, which `10` §2.5 asks for and the circuit cannot yet express |

Whichever mix the player picks, the other three constituencies get a receipt in the same
period. The DSA administration is not fought by an enemy; it is fought by its own budget.

### 3.3 Fork 1 — `DsaForkSocialImperial` (Kautsky / SPD 1914)

**The trigger is exogenous and material, not scripted.** A peripheral trade bloc moves to
delink, or the Israeli franchise starts a regional war and requires cover. In engine terms:

```
corridor_capacity(bloc) ↓   ⇒   Φ inflow ↓ at slot 11 (imperial-rent)
                            ⇒   rent_pool ↓, super-wage funding short
                            ⇒   S and R unfunded at slot 24 (policy)
```

The administration now has two periods to choose. The choice is *only* between:

- **(a) Accept the fall.** `Φ` falls, the pool cannot fund `S` at the promised level, and the
  labor aristocracy's wage-rate falls (`imperial-rent.bsl` r08's designed response —
  `economy/pool-high-threshold 0.7`, `pool-low-threshold 0.3`, `pool-critical-threshold 0.1`).
  The labor-aristocrat electorate — the bloc that delivered the majority — defects. `12`'s
  clock keeps running. The party loses the next election and keeps its staff.
- **(b) Restore the flow.** `ManpowerTier::ActiveDuty` stays at `ExternalGarrison`;
  `CorridorCapacity.available_grams` is restored by force; `Φ` recovers; the budget balances;
  the programme is saved.

**(b) is the social-imperialist accommodation, and the engine records it as a fact rather
than a betrayal:** `extraction_policy` on the claimed footprint is `CONTINUE` or `INTENSIFY`,
and the receipt is a corridor tonnage table. The player became the left wing of imperialism
by voting for the budget that kept the clinics open. That is Lenin's "sold for a mess of
pottage" with the mess of pottage itemised.

**The permanent consequence.** At `sovereignty` (25), the internal semi-colonies and treaty
nations read the deployment, not the programme. `INFLUENCES` collapses toward the ABOLISH
pole; the contiguous components reach the `> 0.5` gate (FR-029a(2)). Every
`EdgeType/SOLIDARITY` edge that crossed the colonial divide is severed by the split
(`BarrierResolution::AntagonisticSplit`). **FR-031a's cross-divide solidarity gate can never
be satisfied in this run again**, because the edges do not exist and the nodes that would
build them are now enemies of the state the player runs.

This is the single most important anti-rail property in the document: Fork 1 is not punished
by an event. It is punished by the graph, permanently, in the same period the clinics open.

### 3.4 Fork 2 — `DsaForkCaesaristCoup` (Allende / Weimar)

**Trigger.** The administration refuses to enforce the flow *and* taxes capital *without*
having smashed the bourgeois state machine and without armed dual power. In engine terms:

```
T_K ↑ at slot 24
  ⇒ CapitalContributionReceipt.unfunded > 0 on the orders that fund the programme
  ⇒ ownership claims relocate (OwnershipClaim rows shift beneficiary)
  ⇒ PublicBudget.period_cap cannot be met; PublicBudgetReceipt.unfunded > 0
  ⇒ the ruling faction's transfer share to the coercive cells falls (1 − max_faction_transfer_share) ↑
  ⇒ autonomy(c) ↑ at the fiscal settlement
```

`17` §4.5 gives the formula, and it is the whole coup:

```
autonomy(c) = threat_keyed_share(c)
            × reproduction_capacity(c)
            × (1 − max_faction_transfer_share(c))
```

`threat_keyed_share` rises *mechanically* in a fiscal contraction, because service-keyed lines
are cut proportionally and threat-keyed lines are not — demand for threat rises exactly when
the pool falls. `17`: "The Caesar is the agency the depression did not defund."

When `autonomy(c) > 0.4` (`institution/bonapartist_threshold`) while no faction weight clears
`0.35` (`bonapartist_exclusion_threshold`), the cell enters Bonapartist mode. **No coup event
fires.** What happens instead is that the executive's verbs stop returning effects:

- `LEGISLATE` and `FUND` return `ActionAvailability::Unavailable("the appropriation was made
  elsewhere")` — the accepted pattern already in `decision_surface.rs`, used here for its
  honest purpose rather than as a rail;
- the security cells' `Capacity::allocate` continues to fund `REPRESS`, `SURVEIL` and
  `PROSECUTE` candidates from their own replenishment;
- the president remains in the building, signs things, and is obeyed by nobody who costs money.

**Why the president cannot fight back.** The DSA coalition's assets are `SupporterLabor` and
`Money`, not `CadreLabor` with an armed wing. `porch-02` §5 names the trap: "a million
followers and zero soldiers." `DualPowerState` requires that the cheapest state entry into a
zone be a `QrfOperation` the state cannot fund *and* that independent institutions cover goods
and justice (`porch-02` §10). A party that won an election has neither. The unarmed base
watches the takeover on the feed, which is exactly the historical scene: Allende's workers
had votes and a constitutional army, and the army was a cell with its own appropriation.

**Where the coup goes.** `BonapartistInterregnum` is a **transit, not a terminal outcome** —
`17` §4.5: "Bonapartism is a *form of capitalist rule*, not an escape from it." It resolves
by which of the following the new pool holder needs:

| Interregnum resolution | Condition | Terminal `GameOutcome` |
|---|---|---|
| Restore accumulation and legality | `T_K` restored, `autonomy` falls back below threshold | none — campaign continues, movement illegal |
| Settler restoration | UPHOLD majority + max violence + `INTENSIFY` (FR-031 route 2) | `FASCIST_CONSOLIDATION` |
| Rent restored, class bought off | `Φ` restored, `class_reduction` high, extraction `CONTINUE` | `RED_OGV` |
| Pool never restores | federal `FiscalPool` empty, ≥3 sovereigns, ≥10 periods | `FRAGMENTED_COLLAPSE` |
| Movement survives underground and rebuilds | cadre network intact, `Dossier` stale, dual power in ≥1 zone | possibly `REVOLUTIONARY_VICTORY`, much later |

That last row matters. The coup must not be a game-over screen. It must be a **change of
operating conditions**: the legal shell is gone, `survival_interest` is wiped with it (the
staff defect or are arrested), and what remains is whatever the player built that did not
depend on legality. A run that invested only in the shell ends here; a run that kept a cadre
network has a game.

### 3.5 Why this is not a rail

Every step reads a quantity the player moved. A player who builds dual power *before* taking
office, who keeps `CadreLabor` separate from the electoral apparatus, who does not tax `K`
until the coercive cells are divided — reaches the presidency and survives. The engine does
not prevent it; it merely charges for it. That is the difference between a rail and a price.

---

## 4. False Summit B — `FalseSummitRedSettler` (`RED_OGV`)

> Seize the factories, raise the red flag, keep `ColonialStance::Ignore`, keep the pipelines.

### 4.1 The win

`balkanization-spec.yaml`'s `FAC_WORKERS_CONGRESS` wins on: `extraction_modifier 0.8`,
`violence_modifier 0.5`, `class_reduction 0.7`, `metabolic_reduction 0.0`,
`extraction_policy CONTINUE`. Translated: wages up, police violence down, class tension down,
**and nothing whatsoever happens to the land.**

This is the most comfortable faction in the game for a player positioned as a settler, and
the spec says so: "They speak the language of class struggle… They don't require confronting
colonial guilt." It must remain comfortable. The trap's power is that it *is* a victory — the
best material conditions most of the player's base has ever had.

### 4.2 The next tick: secession, not a cutscene

At `sovereignty` (25) the settlement reads the receipts:

1. **The internal semi-colonies and treaty nations read extraction, not the programme.**
   Under §0.3's inversion, a Workers' State whose `territory/extraction-intensity` on
   `RESERVATION` and semi-colonial counties is unchanged is running `CONTINUE`, whatever its
   congress said. `INFLUENCES` shifts to the ABOLISH pole.
2. **Contiguity is checked** on `EdgeType/ADJACENCY` (FR-029b). New Afrika and Aztlán are
   contiguous by construction; so are the treaty nations. Scattered influence cannot secede —
   which is why the physical map's contiguity is a strategic fact and not decoration.
3. **`SECESSION_DECLARED`, then `CIVIL_WAR_DECLARED`** (FR-029a(2)), after the hysteresis
   window (FR-029c, default N=3 periods).

Mao §I applies exactly: the contradiction between the Workers' State and the internal
semi-colonies is *by nature* antagonistic — it is a colonial relation — and mishandling
transforms it from a contradiction among the people into "a contradiction between ourselves
and the enemy." The engine does not need a script for this. It needs the relation to be
represented, and to be read from material facts.

**And here is the part the design must not soften: the player can win that civil war.** The
Workers' State has the enforcers, the prisons, the intel apparatus and the arms. Winning it
is the necropolitical threshold of `warlord-trajectory.yaml`: "rule through the administration
of death." A player who does this has not failed to win the revolution. They have won a
counter-revolution while flying the revolution's flag, and the game should let them find out.

### 4.3 The metabolic ratchet does the killing, and it is already executable

This is the strongest finding in the briefing: **the Red Settler trap is a theorem of two
landed rules**, not a claim in a YAML.

From `production.bsl` `p4-extraction-intensity`:

```
i_t = clamp(production_total_t / max_biocapacity_t, 0, 1)
```

From `metabolism.bsl` `biocapacity-update`:

```
raw       = i_t · B_t
cost      = entropy_factor · raw            (entropy_factor default 1.2)
regen     = regeneration_rate · M_t         (regeneration_rate 0.02)
damage    = hysteresis_rate · raw           (hysteresis_rate 0.005)
B_{t+1}   = clamp( B_t + regen − cost , 0 , M_{t+1} )
M_{t+1}   = max( 0 , M_t − damage )          ← the ratchet: M never returns
```

Three results follow by arithmetic alone, with no new coefficient, plus a fourth that corrects
the current spec:

**(i) There is a sustainability threshold, and it is a ratio.** A territory is in biocapacity
equilibrium only where `regen = cost`, i.e.

```
i* = regeneration_rate / entropy_factor = 0.02 / 1.2 = 1/60 ≈ 0.0167
```

Above `i*`, biocapacity converges to a lower plateau `B* = M/(60·i)` with time constant
`1/(entropy·i)`. At `i = 0.05` (three times the threshold) the plateau is `M/3` and it is
reached in ~17 periods. **The drawdown is fast — one or two game-years.**

**(ii) The plateau is stable, which is what makes it a false summit.** Once `B` settles at
`B*`, the slope of habitability is **zero**. The metric stops falling. The Corporate Feed
reports a "stabilised ecological footprint." The player's dashboard looks like success. This
is the precise mechanical content of "sustainable extraction": a genuine steady state at a
lower level, indistinguishable from victory on any slope-based readout.

**(iii) No positive intensity is sustainable, because `M` ratchets.** `damage = hysteresis · i · B`,
so `dM/dt < 0` for every `i > 0`. The ceiling decays; at steady state its rate is
`hysteresis · regeneration_rate / entropy_factor`, *independent of intensity*. Cutting from
`i = 0.05` to `i = 0.04` (the `IGNORE` `extraction_modifier 0.8`) buys the plateau a little
height and buys the ceiling nothing at all. **The only fixed point at zero damage is `i = 0`.**
That is `balkanization-spec.yaml`'s "only abolition heals" — derived, not stipulated.

> **Coefficient caveat, stated plainly.** The three constants above are the values in the
> metabolism conformance scenarios (`metabolism-conformance.bscn`: `regeneration-rate 0.02c`,
> `hysteresis-rate 0.005c`) plus the documented `entropy_factor` shipped default of `1.2`
> (`metabolism.bsl` D-1 header). They are **conformance values, not calibrated game content**;
> no Michigan scenario declares metabolism defconsts at all. The *structure* above holds for
> any positive values; the *pacing* is a calibration decision with an evidence class attached
> (`ADR258`). Do not quote the period counts as designed.

**(iv) A corollary that fixes an error in the current spec.** FR-032 requires aggregate
habitability "below a configured floor **AND slope still negative**", and FR-031 requires
"habitability slope ≥ 0" for liberation. Both read the wrong observable. A scarred steady
state has slope ≥ 0 and is not liberation; a fast drawdown can have a steep negative slope
while the ceiling is barely touched. **Proposed amendment:** read `territory/max-biocapacity`
(the ratchet) and `territory/extraction-intensity` (the policy), not the slope.

- `RED_OGV` ⇔ a majority whose **observed** policy is `CONTINUE` — declared `IGNORE`, or
  declared `ABOLISH` with unchanged tonnage — **and** aggregate `extraction-intensity > 0` on
  claimed extractive territories **and** aggregate `max-biocapacity` strictly declining **and**
  class tension below floor (the workers really are better off).
- `TrueLiberation` ⇔ aggregate `extraction-intensity == 0` on claimed territories **and**
  `max-biocapacity` non-declining **and** FR-031a's cross-divide solidarity edges **and** the
  percolation/consciousness conditions.

### 4.4 Why the secession is the *correct* response and the state's suppression is the trap

A common failure mode in designing this would be to make the secession read as ingratitude.
The theory says the opposite. MIM (`indigenous.unity`): the settler majority — "often led by
the white working class" — is a beneficiary of the colonial relation. A Workers' State that
has not broken that relation has not changed the beneficiary. The internal semi-colonies are
not splitting from socialism; they are splitting from a state that has re-founded the
colonial relation with better health insurance.

Mao's line on the key term is the design rule: the fault is in the dominant nation's
chauvinism, and the dominant nation's party is the one that must move. The Red Settler's
tragedy is that it moves everything except that.

### 4.5 The endgame arrives twice

`RED_OGV` is classified `DELAYED_GAME_OVER` in the YAML, and that is right: it fires when the
political victory and the ecological defeat are simultaneously true, and then the campaign
keeps running inside it. The later `ECOLOGICAL_COLLAPSE` is not a second ending; it is the
same ending arriving at the floor. The player gets to govern the decline for as long as they
can stand it. No screen says "you lose." The habitability table just keeps printing.

---

## 5. Collapse Trajectory C — `WarlordArchipelago`

> Φ collapses, the federal state goes broke, and neither the Vanguard nor the Executive holds
> the map.

### 5.1 The condition, not the event

FR-032a's predicate, verbatim from `specs/070`:

> (a) no single Faction holds majority influence across active Territories; (b) ≥3 distinct
> Sovereigns persist with non-zero CLAIMS; (c) at least one Sovereign has
> `sovereignty_type ∈ {INSURGENT, OCCUPATION, EMERGENCY}`; (d) the configuration has persisted
> for ≥10 ticks without consolidation.

Every clause is a read of the graph. None is an authored trigger. What produces the condition
is the fiscal chain in §5.2–5.4, and each link is already executable.

### 5.2 The revanchist coalition is a class decomposition, and it is already written

`warlord-trajectory.yaml` describes the new ruling formation as "revanchist cops +
petit-bourgeoisie remnants + decomposed labor aristocracy," and calls the key insight
"the apparatus of violence outlives its economic base."

`decomposition.bsl` already implements the middle term:

1. `p01-la-census` — the labor aristocracy's population/wealth census each tick.
2. `p02-superwage-warning` — when the active LA approaches subsistence and no crisis is
   latched, `SUPERWAGE_CRISIS` fires (once).
3. `p03-trigger` — after `carceral/decomposition-delay 52`, `CLASS_DECOMPOSITION` fires and
   splits the LA: `enforcer-fraction 0.15` into `CARCERAL_ENFORCER`, `proletariat-fraction
   0.85` into `INTERNAL_PROLETARIAT` (each floored independently — the deliberate
   non-conservation, D173 item 3).
4. `p04`/`p05`/`p06` — the enforcer intake is additive, the proletariat intake overwrites,
   and the LA is deactivated with population and wealth left untouched.

So the sequence "Φ falls → the super-wage cannot be paid → the labor aristocracy decomposes →
15% become enforcers and 85% become proletarians" is **not a narrative**. It is four landed
rules and one constant. The warlord coalition's manpower is produced by the failure of
imperial rent, exactly as the theory says.

### 5.3 `autonomy(c) → 1`: the federal pool empties and only threat sells

```
federal FiscalPool ↓ (tax base falls, Φ falls, no debt instrument)
  ⇒ service-keyed lines cut proportionally
  ⇒ threat_keyed_share(c) → 1 for cells whose repertoire IS threat
  ⇒ autonomy(c) → reproduction_capacity(c)
```

The cells that survive are the ones whose output is unverifiable and whose demand rises in a
crisis: sheriff (per-diem beds), prison administration (bed-days), local police (clearance
claims), fusion center (products produced), CIA (deniable), and the Guard (a cell with its
own grievance, `17` §4.6).

The cells that die are the ones that produce verifiable service: the public defender, the
clinic, the code inspector, the transit authority. **The archipelago is not built; it is what
is left when everything with a measurable output is defunded.** That is `17`'s fiscal
derivation and it needs no warlord event.

### 5.4 `control-ratio` and the terminal branch

The coercive arithmetic is already live (`control-ratio.bsl`):

```
max_controllable = enforcer_population × control_capacity        (control_capacity 4)
crisis           ⇔ prisoner_population > max_controllable
terminal         ⇔ avg_organization(prisoners) ≥ revolution_threshold (0.5)
                     ? REVOLUTION : GENOCIDE
```

Two readings matter here.

1. **The archipelago lowers `enforcer_population` in relative terms while raising the captive
   population**, because the decomposed LA's 85% join the internal proletariat that the
   carceral circuit counts. The ratio crosses from the state's side without anyone deciding
   to make it cross.
2. **The George Jackson Bifurcation is the archipelago's internal fork.** Where prisoners are
   organized above 0.5, the camp yields revolution; below it, `GENOCIDE` — the reserved branch
   (ADR070). This is the only place in the current engine where the necropolitical mode is
   named as an outcome, and it is a verbatim port. The archipelago's character is decided
   *inside the camps*, not in the capital.

### 5.5 The necropolitical mode of production, in two rules

`warlord-trajectory.yaml` insists this is a **regressive mode of production**, not merely a
political change: no wage labour, no commodity production for exchange, extraction by direct
violence, and a captive population that is a liability rather than an asset. Two landed rules
already express it:

- `territory/p4-camp-decay` — a `CONCENTRATION_CAMP`'s population is multiplied by
  `(1 − concentration-camp-decay-rate)` and floored, every tick. Elimination as a rate.
- `territory/p4-penal-suppression` — every `SOCIAL_CLASS` tenant of a `PENAL_COLONY` has
  `social-class/organization` **set to 0**. Atomisation as a write.

Together they are the whole theory: the population is consumed, and the organization that
could resist is zeroed. The archipelago needs no new mechanic to be horrifying. It needs the
player to watch a county's population column fall while the sheriff's bed revenue rises.

### 5.6 The two sub-addresses

`warlord-trajectory.yaml`'s `epoch2_design` branches, and the branch is a fiscal comparison,
not a threshold ladder:

| Branch | Condition (as the engine can read it) | Result |
|---|---|---|
| **A — Classical Concentration** (bourgeois necropolis) | `CORE_BOURGEOISIE` wealth above the payment threshold **and** military loyalty purchased (appropriation funded, `Guard` morale term positive) | federal shell survives, pretense of law maintained, `FASCIST_CONSOLIDATION` route available |
| **B — Necropolitical Prison-Plantation** (warlord era) | bourgeoisie insolvent, military unfunded, revanchist cells autonomous, settler consciousness activated | decentralized fiefdoms, `FRAGMENTED_COLLAPSE` |
| **C — Revolutionary Rupture** | `prisoner_organization ≥ 0.5` **or** enforcer radicalisation past the flip point | `REVOLUTIONARY_VICTORY` from the camp |

Note the YAML's own pseudocode uses free-floating thresholds (`> threshold`) for
`military_loyalty`, `revanchist_cohesion`, `settler_consciousness`. **Those must not be
ported.** Each is a ratio over live state: `military_loyalty` is funded-vs-requested
appropriation plus the Guard's own material condition; `revanchist_cohesion` is the share of
the pooled appropriation flowing to threat-keyed cells; `settler_consciousness` is
`community/c08-dominant-tendency` over settler-coded communities, which is already a measured
readout. Any authored constant here would violate `ADR172 r5`.

### 5.7 What the archipelago is *not*

It is not a win for the player's movement, and it must not be dressed as one. `17` §3.3's
razor applies: "A player who reads the fractures as 'the state is weak' builds on a false
premise and loses to the redundancy." The archipelago is a state that has stopped paying for
coordination and started paying for death. If the player's organization is in one of those
fiefdoms, it is a subject population, not a government.

---

## 6. `TrueLiberation`

### 6.1 Five conditions, all of them material

| # | Condition | Engine read | Why it cannot be faked |
|---|---|---|---|
| 1 | **Extraction ceases** | aggregate `territory/extraction-intensity == 0` on claimed extractive territories | intensity is `production_total / max_biocapacity`; only an actual production stop produces zero |
| 2 | **The ratchet stops** | `territory/max-biocapacity` non-declining over the window | follows from (1) by the damage formula |
| 3 | **The colonial relation is dismantled** | ABOLISH-majority claims with `sovereignty_type` recognising internal-nation sovereignty (the `RESERVATION` territory type already exists) | a claim on the map, not a stance enum |
| 4 | **Cross-divide solidarity is real** | ≥ N active `SOLIDARITY` edges from `is_settler_formation=true` to `false` nodes (FR-031a, default 5) | edges are built by organizing, severed by splits |
| 5 | **Φ has fallen** | `Φ` at or below the calibrated floor, and `ActiveDuty` not in `ExternalGarrison` | the rent identity, not a policy |

Condition 5 is the one that makes `TrueLiberation` structurally different from every other
ending: **it requires the player to destroy their own material basis.** `fundamental-theorem.bsl`
states that while `W_c > V_c` revolution in the core is materially foreclosed. Delinking is
what ends `W_c > V_c`. A player cannot liberate the core while the rent flows, because the
rent is the reason the core's working class is not the agent. `13` §3.4: "Φ has no natural
decay… nothing reduces Φ except losing the drain."

So True Liberation is not the DSA path continued. It is the **opposite** of the DSA path's
successful fork. Fork 1 restores Φ and locks the player out of this ending permanently. That
asymmetry is the design's spine.

### 6.2 What it costs, itemised — because a victory with no bill is a fantasy

`15` §13 names two exits from inside the US, and both hurt:

1. **Cheap goods are lost.** A delinked periphery means the wage-goods basket rises. The
   Ticker prints it: the same basket, more hours. The internal proletariat bears it first.
2. **The plant that depended on the export order loses the order.** Leontief requirements
   (`15` §6.2) mean the domestic hours embodied in the lost trade stop being demanded. A
   county closes.
3. **The labor aristocracy decomposes.** Φ falls, the super-wage cannot be paid,
   `SUPERWAGE_CRISIS` → `CLASS_DECOMPOSITION` → 15% enforcers, 85% proletarians. The player's
   own most skilled, most loyal, most numerous cadre are among the decomposed. Some become
   enemies.
4. **The 33/33/33/0 partition inverts, and the restoring force fights back.** `13` §1.4: inside
   the basin, second-order restoring forces eat ordinary reforms. Only a bifurcation — cracking
   Φ, severing circulation, breaking the control ratio — moves the system to a new basin. All
   three of those are things the player must do *and* survive.
5. **The state comes for you**, because conditions 1–3 are an existential threat to every cell
   whose appropriation is threat-keyed. The endgame is reached through the hardest fight in
   the game, not around it.

### 6.3 The scar: the epilogue must not lie

`balkanization-spec.yaml` says `CEASE` produces `metabolic_impact +0.01` and "habitability
stabilizes, then slowly improves." **The landed rule is harsher and the landed rule wins.**
`M_{t+1} = max(0, M_t − damage)`: the ceiling never returns. `CEASE` sets `damage = 0`, so
the ceiling *stops falling*; biocapacity then regenerates toward the *damaged* ceiling at
`regeneration_rate`. What heals is the gap between `B` and `M`. What does not heal is `M`.

So `TrueLiberation`'s honest epilogue is: **the bleeding stops, and the land is smaller than
it was.** That is a better ending than a green screenshot, because it is the truth about
capitalist agriculture (`Capital` I ch. 15 §10: "ruining the lasting sources of that
fertility") and because it gives the player something to argue about. It also blocks the
sentimental failure mode: a victory screen full of recovered forest would tell the player that
500 years of extraction was reversible in a generation.

The `ECOLOGICAL_OVERSHOOT` predicate in FR-031 (overshoot ratio > 2.0) still applies *during*
the transition: a player who ceases extraction but has already destroyed the ceiling can
starve. Liberation is a race against the floor.

### 6.4 Abolition without coalition is another false summit

FR-031a is right and should be protected:

> A run with ABOLISH-Sovereign majority + extraction stopped + habitability stabilizing but
> WITHOUT cross-divide solidarity routes to `RED_OGV` rather than `REVOLUTIONARY_VICTORY` —
> abolition without coalition is itself a trap.

Note what this means, and it is subtle: `RED_OGV` is not only the settler-socialist ending. It
is also the ending of a *correct policy imposed by the wrong bloc* — a settler vanguard that
stops the pipelines by decree and hands nothing over. It has the policy and not the relation.
That is a fifth summit hiding inside the fourth condition, and the taxonomy should say so
plainly: there are **three ways to arrive at the Red Settler address** (Ignore, Accommodate,
Impose), and only one of them is comfortable.

### 6.5 Φ ≠ 0 as a *feasible* end state is a genuine design question

Condition 5 assumes Φ can actually be driven to the floor inside a 260-period campaign. That
is an empirical question about the calibrated magnitude of the drain and the speed of
peripheral delinking. It must be tested, not assumed (`13` §4.6's falsification discipline).
**If a full campaign cannot move Φ by more than a few percent, `TrueLiberation` is
unreachable and the design has a rail made of arithmetic.** That is the single highest-risk
item in this document and it belongs in the Director's docket (§10 Q1).

---

## 7. The full taxonomy

### 7.1 `SummitState` — the Chronicle-facing label

**Proposed**: a `SummitState` is a *derived read* over the graph, computed at
`collapse-transition` (30), never stored as a flag and never written by a script. It exists
so the Chronicle can name where the player is; the mechanics never read it.

| `SummitState` | Terminal? | `GameOutcome` | The receipt that convicts |
|---|---|---|---|
| `FalseSummitDsaPresidency` | transit | — (campaign continues) | the first budget's four-way incidence |
| `└ DsaForkSocialImperial` | delayed | `RED_OGV` (then `ECOLOGICAL_COLLAPSE`) | corridor tonnage restored; solidarity edges severed |
| `└ DsaForkCaesaristCoup` → `BonapartistInterregnum` | transit | resolves per §3.4 | `unfunded` on capital contributions; `autonomy(c) > 0.4` |
| `FalseSummitRedSettler` | delayed | `RED_OGV` | `extraction-intensity > 0` under an ABOLISH programme |
| `WarlordArchipelago` | yes | `FRAGMENTED_COLLAPSE` | federal pool empty; ≥3 sovereigns; `autonomy → 1` |
| `TrueLiberation` | yes | `REVOLUTIONARY_VICTORY` | `extraction-intensity == 0`; `max-biocapacity` non-declining; cross-divide edges |

### 7.2 Mapping onto the existing enum, with no new values

`specs/095/contracts/endgame.yaml` and `specs/070` FR-030 fix six `GameOutcome` values:
`revolutionary_victory`, `ecological_collapse`, `fascist_consolidation`, `red_ogv`,
`fragmented_collapse`, `unresolved`. **This briefing adds none of them.** `SummitState` is a
presentation label; `GameOutcome` is the engine's verdict. Keeping them separate is the same
discipline `spec-095` already applies to `TRUE_LIBERATION` (a user-facing framing over
`REVOLUTIONARY_VICTORY`).

The one thing I would ask for is a **diagnostic, not an enum value**:
`BONAPARTIST_INTERREGNUM` as an event on the existing `BonapartistModeEvent` contract
(`17` §4.5), so the Chronicle can date the moment the appropriation changed hands without
asserting the run is over.

### 7.3 FR-033's priority order, re-read

`RED_OGV → FRAGMENTED_COLLAPSE → ECOLOGICAL_COLLAPSE → FASCIST_CONSOLIDATION →
REVOLUTIONARY_VICTORY`, first-match-wins.

The rationale given is that `RED_OGV` is a strict subset of `ECOLOGICAL_COLLAPSE` conditions
and so must be checked first to fire the more informative outcome. Under §4.3's amendment the
same logic holds with a better observable: `RED_OGV` is the *political* description of a
metabolic fact, so it must win the tie. Two further notes:

1. `WarlordArchipelago` (→ `FRAGMENTED_COLLAPSE`) and `RED_OGV` can hold simultaneously — a
   fragment of the country running settler socialism while the centre dissolves. The priority
   order resolves it to `RED_OGV`, which is arguably wrong: the archipelago is the larger
   fact. **Proposed**: make the `FRAGMENTED_COLLAPSE` predicate require the *absence* of a
   RED_OGV-majority sovereign rather than relying on order, so the two are mutually exclusive
   by construction and the priority list stops carrying semantic weight it cannot bear.
2. `REVOLUTIONARY_VICTORY` last is correct and should stay last even though it is the
   rarest. The last check is the most expensive claim; a run that satisfies liberation *and*
   collapse is a collapse.

### 7.4 The endgame is not a screen

`2026-10-25-porch-02.md` §6: "History never hits an arcade 'GAME OVER' wall—the simulation
continues and you can always keep playing inside the world you made." `spec-116`'s
`UNRESOLVED` outcome at the fixed horizon already encodes this. Four properties follow:

- Every endgame is an **event plus continued play**, except where the world genuinely ends
  (the player's organization dissolved, the base area lost, the line abandoned).
- `RED_OGV`, `FASCIST_CONSOLIDATION` and `WARLORD` runs are **governable**: the player is
  still a participant and can still lose worse or claw back.
- Only `TrueLiberation` and `ECOLOGICAL_COLLAPSE` justify a terminal framing, and even then
  the Chronicle continues as post-endgame observation (`spec-070` FR-031's "or enters
  post-endgame observation mode").
- The player can always keep playing. That is the anti-teleology guarantee: no ending is a
  door closing on the world.

---

## 8. Gameplay feel — the four summits on four surfaces

The Mao visibility rule (`porch-01` §"The visibility rule"): show only what a participant
could learn from a communist history book. Concrete world-facts yes; multipliers, scores,
heat floats and legitimacy scalars never. Working test: *would Mao have put it in the
treatise?*

Three authors, one record (`porch-01` §"The narrator"): **Corporate Feed** (hegemonic
euphemism), **Liberated Signal** (the movement's samizdat, witty and partisan), **Intel
Stream** (raw, no adjectives, deterministic fallback). The **Chronicle/Wiki** is the permanent
record, chapters titled by the period's dominant task in verb form. The **Topology** map is
the graph under fog, quantised to named qualitative states — `holds / dislodged / broken` —
never hit-point bars.

Sample renderings, written to be shippable strings rather than mood boards.

### 8.1 `FalseSummitDsaPresidency` — inauguration period

**Chronicle** — *Chapter: Take Office, and Read the Budget.*
> The coalition holds 218 seats and the presidency. The first appropriation is due in
> fourteen days. Four line items are on the table and each of them has a constituency sitting
> in the gallery.

**Corporate Feed**
> "MARKETS GREET NEW ADMINISTRATION WITH CAUTION. Bond desks cite 'fiscal uncertainty' as the
> incoming government prepares its first budget. A spokesperson said the transition team is
> 'committed to fiscal responsibility and to the promises that were made.'"

**Liberated Signal**
> "WE WON. Now read the fine print. The President wants Medicare for All and the money has to
> come from somewhere, and 'somewhere' has a name and a zip code. Four doors, one room. Pick
> one and watch who screams."

**Topology**
> The coalition node is large and its edges are *thin*: a union local, two church networks, a
> tenant federation, a liberal party chapter, and a donor bloc, all connected to the centre and
> barely connected to each other. Two nodes are *contested* (a police union local, a chamber of
> commerce). The internal semi-colony nodes show **no edge at all** to the coalition centre —
> they were not in the tent and are not in it now. That empty arc on the map *is* the ending,
> visible thirty periods before it fires.

### 8.2 `DsaForkSocialImperial` — the period the Navy sails

**Chronicle** — *Chapter: Fund the Clinics.*
> The corridor reopened on the 14th. Six clinics opened in the same fortnight. The same
> appropriation paid for both.

**Corporate Feed**
> "ADMINISTRATION STABILISES SUPPLY CHAINS. The President hailed the reopening of the southern
> corridor as 'proof that a humane foreign policy and a prosperous economy are the same
> policy.' Hospital administrators welcomed the funding."

**Liberated Signal**
> "The ships went out and the clinics opened and nobody lied about it, which is the worst part.
> We built a health service on a rent we did not collect ourselves. Read the tonnage table on
> page four and then read our own programme on page one, and tell me which one is the
> movement."

**Topology**
> The map has a new shape: a thick edge from the coalition centre to the Pentagon cell, and
> every edge that used to cross the colonial divide is **broken** — greyed, dated, with the
> period they were cut. The internal semi-colony nodes are no longer contested; they are
> *hostile* (antagonistic edges, red). The solidarity subgraph that once had nine crossing
> edges has none. The tooltip says what the map says: *"No path."*

### 8.3 `DsaForkCaesaristCoup` — the period the money stops answering

**Chronicle** — *Chapter: Sign What You Are Given.*
> The appropriation cleared the committee. The departments did not draw on it. The President
> signed the order and the order was filed.

**Corporate Feed**
> "INSTITUTIONAL CONTINUITY MAINTAINED. Spokespeople for the security services declined to
> comment on 'operational matters.' The President's office reaffirmed its commitment to the
> constitutional process."

**Liberated Signal**
> "The office is warm and the phones are dead. Every agency that costs money still has a
> budget; every agency that helps people does not. They did not arrest her. They just stopped
> taking her calls. That is what a coup looks like when the country still has a constitution."

**Topology**
> The state cells are now *autonomous*: their edges to the executive are drawn as dashed
> (appropriation unclear) and their edges to each other are thick. The executive node still
> exists, still has the biggest single node size, and has **no outgoing edge that reaches a
> cell that can act**. Clicking it gives the honest unknown: *"What can this office order? You
> do not know. You have not been told."*

### 8.4 `FalseSummitRedSettler` — the period after the revolution

**Chronicle** — *Chapter: Raise the Flag, Keep the Pipeline.*
> Wages rose in the first quarter. The mines reopened in the second. The habitability table
> printed the same number for eleven straight periods.

**Corporate Feed**
> "WORKERS' REPUBLIC REPORTS STABLE ECOLOGICAL FOOTPRINT. Planning officials credit 'socialist
> rationalisation' for the first sustained plateau in a decade. Green jobs figures are up."

**Liberated Signal**
> "We won. Read that again: we won, and the water table is still dropping, and the number on the
> wall has not moved in eleven periods. A stable number is not a healed river. Go and look at
> the river."

**Topology**
> The flag is red and the graph is unchanged. The same extraction edges from the same
> semi-colony nodes to the same industrial centres; the same pipeline corridors; the only
> difference is that the *centre* node is now the Workers' Congress. Then the secessions fire:
> three contiguous blocs light up as separate sovereignty clusters with hostile edges to the
> centre and **no** edge between each other. The map shows a red state at war with three
> nations it says it liberated. The `is_settler_formation` tag on the ruling node is visible
> — and it is the player's own node.

### 8.5 `WarlordArchipelago` — the period the county stops counting

**Chronicle** — *Chapter: Administer What Remains.*
> The federal payment did not arrive in March. The sheriff's office began billing the county
> for bed-days. Two hundred and forty people were moved from the county jail to the facility
> at the old airfield, which is now the county's largest employer.

**Corporate Feed**
> "REGIONAL AUTHORITIES STEP UP. Local leaders praised 'community-based public safety
> solutions' as federal transfers lapse. A spokesman for the sheriff said the department is
> 'doing more with less, and doing it for the people who live here.'"

**Liberated Signal**
> "There is no state. There is a man with a badge and a contract, and the contract is paid in
> bodies. The camp on the airfield is not a prison, it is a business plan. If you are in a
> county with a sheriff and no federal transfer, you are not a citizen, you are inventory."

**Topology**
> The national graph has come apart into four clusters with no paths between them. The federal
> node is *broken* (zero edges, dated). Inside each cluster, one cell has thick edges to
> everything and every other cell has thin edges to it — a star, not a network. Population
> counts on two counties fall each period. Organization is zero on every node inside the penal
> facility. The Intel Stream prints it without adjectives: `pop 1,204 → 1,131 → 1,062`;
> `org 0.00`. That is the necropolitical mode of production, rendered as two columns.

### 8.6 `TrueLiberation` — the period the tonnage goes to zero

**Chronicle** — *Chapter: Stop the Digging, and Count What It Cost.*
> Extraction ceased in the eleventh period. The wage-goods basket rose for six periods and then
> held. Three counties lost their largest employer. The habitability table turned upward in the
> nineteenth period, toward a ceiling lower than the one the county began with.

**Corporate Feed**
> "INVESTMENT CLIMATE DETERIORATES AS EXTRACTION HALTS. Ratings agencies downgrade the region.
> Analysts warn of 'a permanent reduction in productive capacity' and question whether the
> new authorities can 'sustain the confidence of capital.'"

**Liberated Signal**
> "The mines are closed and the water is coming back, slowly, to a river that will never be
> what it was. Some of our own people are out of work and some of them are angry and they are
> right to be. We said the land was not for sale. It turns out we meant it, and it turns out
> that is not free. This is what winning costs. Nobody told us the bill would be this honest."

**Topology**
> For the first time the map has *fewer* edges than last period, and the player did that. The
> extraction corridors are gone. The cross-divide solidarity edges are thick and numerous and
> bidirectional. The internal semi-colony nodes are sovereign nodes — same size, separate
> boundaries, thick treaty edges. The centre is smaller and less connected than it was. That
> shrinkage is the ending: a centre that no longer commands the periphery because the
> periphery is no longer a periphery.

---

## 9. Anti-rail audit and falsifiers

Each item is a test that would tell the team the design failed. Stated as falsifiers because
`13` §4.6 and `17` §4.11 already set that discipline.

1. **If the presidency is unreachable**, the design has a rail made of content. The DSA path
   must be winnable by a competent player using only permitted verbs.
2. **If a player can win the presidency, keep Φ flowing, and still reach `TrueLiberation`**,
   then `fundamental-theorem.bsl` is decorative and the entire theory of the core is wrong in
   the engine. This is the load-bearing falsifier.
3. **If the Red Settler's secessions can be suppressed without changing `extraction-intensity`**,
   the metabolic claim is decorative. (They *can* be suppressed — that is the horror — but the
   suppression must cost the `RED_OGV` outcome, not prevent it.)
4. **If Bonapartist mode is reachable without a fiscal contraction**, there is a hidden
   coefficient and `ADR172 r5` has been violated (`17` §4.11).
5. **If any of the four requires an authored threshold not derivable from a live ratio**, the
   endgame is a script wearing arithmetic.
6. **If `RED_OGV` fires on a run whose habitability slope is momentarily negative but whose
   ceiling is intact**, the observable is wrong (see §4.3(iv)).
7. **If the archipelago can be reached without the labor aristocracy decomposing**, the
   decomposition coupling is decorative and the warlord coalition has no class content.
8. **If `TrueLiberation` renders as ecological recovery to the pre-extraction ceiling**, the
   epilogue is lying about `M_{t+1} = max(0, M_t − damage)`.
9. **If any ending requires a cutscene to be understood**, the surfaces have failed. The four
   feeds in §8 are the acceptance test: every clause must be a fact the engine can emit.

## 10. Open questions for the Director

1. **Is Φ movable at campaign scale?** `TrueLiberation` requires driving `Φ` to a floor inside
   260 periods. If calibration makes the drain too large or peripheral delinking too slow, the
   true ending is arithmetically unreachable. Needs a measured feasibility run before the
   endgame predicates are frozen.
2. **Does `extraction_policy` become observed rather than declared (§0.3)?** This is the one
   change that turns the Red Settler trap from an assertion into an experience. It also
   demotes `colonial_stance` to an overlay claim, which touches `spec-070`'s data model and
   ADR029's ontology.
3. **`TaxBasis` has only `WageIncome` and `PositiveOperatingIncome`.** A federal wealth tax, a
   land-value tax, or an expropriation therefore *cannot be expressed* in the current circuit.
   Is widening the enum an authority amendment, or does the DSA fork's capital-tax arm stay
   unrepresentable until the material circuit's next cut? (This is a real constraint on Fork 2
   and should not be smuggled in through a screen.)
4. **Slope or ceiling (§4.3(iv))?** Amending FR-031/FR-032 to read `max-biocapacity` and
   `extraction-intensity` instead of habitability slope.
5. **Mutual exclusivity of `RED_OGV` and `FRAGMENTED_COLLAPSE`**: make the predicates disjoint,
   or keep leaning on FR-033's order?
6. **Calibrating metabolism.** The three coefficients in use are conformance values. The
   sustainability threshold `i* = regeneration_rate / entropy_factor` is a content decision
   with an evidence class, and it determines whether the Red Settler's plateau arrives in two
   years or twenty.
7. **`RESERVATION` is a declared `TerritoryType` with no rule of its own.** Treaty sovereignty
   needs a rule (violation costs legitimacy; the State "cannot abolish it, only violate it" —
   `porch-02` §10). Without it, condition 3 of §6.1 has nowhere to be written.
8. **Does the coup get a diagnostic event?** `BONAPARTIST_INTERREGNUM` as a dated fact on the
   existing `BonapartistModeEvent` contract, so the Chronicle can mark the period the
   appropriation changed hands.

---

## 11. One paragraph for the designer

The player who wants to prove the designer wrong by winning an election is not the game's
opponent; they are its ideal reader, and the game owes them a real victory followed by a real
bill. Give them the Congress and the presidency. Let the first budget be due in fourteen days
with four payers and no fifth. Let them fund the clinics with the corridor, and then show them
the tonnage table beside their own programme and say nothing. Give them the factories and the
red flag and the pipelines, and let the water table go quiet at a lower level so the dashboard
looks like success while the ceiling keeps falling — because that is what "sustainable
extraction" has always meant. When they finally close the mines, charge them the basket, the
closure, the decomposition of their own most loyal cadre, and give them a river that comes
back to something less than it was. There is no end of history screen. There is only the
receipt, printed in the player's own words on one side and their own tonnage on the other.
That is the game: *you may have anything you are willing to pay for, and the price is always
somebody's land.*

---

## Sources

**Primary, read verbatim on this host (2026-10-25):**
`/media/user/data/old-hdd/old-hdd/www.marxists.org/archive/marx/works/1867-c1/ch15.htm`
(*Capital* I ch. 15 §10) and `ch26.htm` (*Capital* I ch. 26);
`archive/marx/works/1871/index.htm` (the "ready-made state machinery" sentence);
`archive/marx/works/1875/gotha/{index,append,foreword}.htm` (index and apparatus only — the
body is absent);
`archive/lenin/works/1917/staterev/ch02.htm`;
`archive/lenin/works/1915/csi/viii.htm`;
`archive/lenin/works/1916/imp-hsc/{ch02,ch03}.htm`;
`archive/marx/works/1894-c3/ch25.htm` (*Capital* III ch. 25, credit and fictitious capital);
`reference/archive/mao/selected-works/volume-5/mswv5_58.htm` (*On the Correct Handling of
Contradictions Among the People*, §I and §VI).

**MIM, read verbatim:** `/media/user/data/mim/textonly/MIM.essays/democratic.socialism`;
`MIM.essays/indigenous.unity`; `contemp/cons/exploiterpatriotism.html`.

**Absent from this host, cited as standard text and flagged:** *The Civil War in France*
(full body); *Critique of the Gotha Programme* (Parts I–IV); Stalin, *Foundations of
Leninism* ch. VI (only ch. 1, 2, 9 are present); Stalin, *Marxism and the National Question*
(1913, title page only); Lenin, *Imperialism* ch. VIII (parasitism and the labour
aristocracy).

**Repository:** `AGENTS.md`; `specs/070-balkanization/spec.md` (FR-029…FR-040, FR-031a,
FR-033); `specs/095-endgame-chronicle/{spec.md,contracts/endgame.yaml}`;
`docs/gameplay/{00-overview.md,porch-handoff.md,2026-10-25-porch-01.md,2026-10-25-porch-02.md}`;
`docs/gameplay/research/{10,12,13,15,16,17,18}.md`;
`ai/epochs/epoch3/{balkanization-spec,warlord-trajectory,cohesion-mechanic,reactionary-subject,political-economy-liquidity}.yaml`;
`rust/crates/babylon-tick/content/rules/{fundamental-theorem,imperial-rent,metabolism,production,territory,control-ratio,decomposition}.bsl`;
`rust/crates/babylon-tick/content/scenarios/{metabolism-conformance,decomposition-conformance,territory-conformance}.bscn`;
`rust/crates/babylon-tick/src/phase_order.rs`;
`rust/crates/babylon-material-circuit/src/financial/model.rs`;
`rust/crates/babylon-client/src/decision_surface.rs`;
`docs/superpowers/plans/2026-10-25-babylon-gameplay-and-late-empire-plan.md` (Tasks 2, 4, 5, 6).
