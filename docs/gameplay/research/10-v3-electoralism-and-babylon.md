# 10 — Victoria 3's electoralism, and what Babylon should take from it

**Status:** porch-session design research. Nothing here implements or changes game
law. Claims about shipped Babylon code cite the file; proposals say **proposed**.

**Provenance.** Victoria 3 local install, `release/1.13.11` (`caligula_rev.txt`),
Steam buildid `24799966`. Read the data and UI labels, not the binary: `game/common/`
(`laws/`, `law_groups/`, `interest_groups/`, `parties/`, `political_movements/`,
`institutions/`, `defines/`, `amendments/`, `static_modifiers/`, `script_values/`,
`scripted_effects/`), the politics panels under `game/gui/`, and the shipped concept
text in `localization/english/concepts_l_english.yml`. Every constant below is a
define.

**Guardrail.** Structure only; no Paradox text, art, or scripting enters Babylon.
The synthesis is MIM(P)/MLM-TW per `06-mimp-and-mlm-tw-canon.md`: the vote cannot
reach Φ, it can buy *space*, and electoralism is a trap you may walk into and read
the receipt for.

**Screen count.** The brief says "Six Screens"; `2026-10-25-porch-01.md` rules
**five**, Electoral as #2, and `02-systems-and-surfaces.md` §227 confirms it. This
treats Electoral as screen 2 of five and invents no sixth.

---

# Part I — How Victoria 3 actually does it

## 1.1 The pipeline

Pops generate political strength; strength becomes clout; franchise law converts clout
into votes; votes go to parties; parties are made of interest groups; the IGs you seat
decide what you can enact and how legitimate you look doing it. Outside that building,
movements press from the street and can rewrite who leads an IG. Two currencies with an
explicit exchange rate — *clout* (permanent, material, from population and wealth) and
*votes* (periodic, legal, from the franchise) — and legitimacy, momentum, radicalism are
derived readings of those two.

## 1.2 Clout is the only hard currency

Political strength comes from pop size, wealth, and law. Baseline `base_values`
(`static_modifiers/00_code_static_modifiers.txt`) sets `country_officers_pol_str_mult =
3` and `country_soldiers_pol_str_mult = 1.5`, commented "to account for the power
derived from bearing arms" — armed men count triple before any law says so. Clout is an
IG's *share* of national political strength, not an absolute
(`POWERFUL_IG_THRESHOLD 0.20`, `MARGINAL_IG_THRESHOLD 0.05`), and it does everything: in
government it sets legitimacy, in opposition movement support and activism, so out of
office is a different verb set rather than out of the game.

## 1.3 The franchise is the exchange rate

The best structural idea in the layer. Each distribution-of-power law trades votes
against clout against coherence against democratic confidence
(`laws/00_distribution_of_power.txt`):

| Law | `…total_votes_add` | `…total_clout_add` | incoherence mult | `electoral_confidence_impact_mult` |
|---|---|---|---|---|
| `law_landed_voting` | 40 | 100 | 0.2 | −0.3 |
| `law_wealth_voting` | 65 | 75 | 0.2 | −0.2 |
| `law_census_voting` | 85 | 55 | 0.1 | −0.1 |
| `law_universal_suffrage` | 110 | 25 | — | — |
| `law_single_party_state` | 100 | — | −0.25 | −1.0 |

An accounting identity: a narrow franchise runs the state on **clout** (who owns
things legitimates the government), a broad one on **votes** (who shows up legitimates
it). Widening the franchise does not make government legitimate in the abstract — it
*refinances* legitimacy onto a different balance sheet, and a coalition that suited
the old franchise loses coherence under the new one.

`electoral_confidence` is the sharp end. It derives from an index
(`script_values/ideology_values.txt: eagle_burger_freedom_index`) built from
urbanization and literacy; low confidence applies `country_legitimacy_base_add = -50`,
`country_voting_power_mult = -0.5`, and `state_political_strength_from_wealth_mult =
0.5`. When the forms rot, government loses legitimacy, **every vote is worth half**,
and **wealth's political strength rises by half**: backsliding does not add a penalty,
it reweights the polity toward money. Most useful thing in the file for Babylon.

## 1.4 Elections: four years, six months, and dice

`ELECTION_INTERVAL_YEARS 4`, `CAMPAIGN_PERIOD_MONTHS 6`, `INITIAL_MOMENTUM_MIN 0.5` /
`MAX 1.5`, `POPULARITY_MOMENTUM_FACTOR 0.005`, `REFORM_GOVERNMENT_PERIOD 6`,
`REFORM_GOVERNMENT_RADICALIZATION_RATE 0.25`. The concept text is candid: momentum "can
be affected by **random chance**, special events, and the popularity of its party
leader," and once cast the party's votes are "**fixed until the next election**" while
raising "the clout of any interest groups that are members of the party."

Six months of campaign, momentum partly dice, then election day freezes the result for
four years and converts it into permanent clout. You get exactly one free government
reshuffle inside six months; later ones radicalize 25% of the removed IG's supporters.
The frozen-votes design is genuinely good — an election is a four-year material fact,
not a mood. The dice are the error (1.9).

## 1.5 Parties: coalitions that form themselves, and never split

Twelve party *types* in `common/parties/`, each declaring
`available_for_interest_group` and a `join_weight` — an additive list of ideological and
law-context terms, then multiplied `×2` for the first non-marginal member, `×0.5` for the
second, `×0` for the third and beyond. **A party cannot exceed three member IGs**, and
the third free-rides on the first two, so coalition size is bounded by formation
arithmetic rather than ambition.

Discipline is narrow. Per `concept_party_whip_desc` the whip "partially overrides the
ideological law stances on the other interest groups in the party **for the purposes of
calculating ideological incoherence**," base `country_party_whip_impact_add = 0.5` — it
buys *legitimacy*, not votes.

The absences matter as much: no floor defection, crossing the aisle, recall, expulsion,
by-election, or donor pressure on an individual member; parties dissolve wholesale by
script (`scripted_effect_parties_disappearence`) on regime change. **V3 models coalition
formation and financing, but not coalition decay.** Ideology belongs to the IG leader, and
leaders change; the line does not.

## 1.6 Law enactment: a three-checkpoint slot machine

`LAW_ENACTMENT_DEFAULT_BASE_DAYS 100` (law groups override to 150–200 for power
structure), `MAX_PHASES 3`, `ADVANCE_FACTOR 2` (advance chance = 2 × success),
`MIN_SUCCESS_CHANCE 0.01`, `COOLDOWN_DAYS 730`, `IG_CLOUT_STALL_EFFECT 1.0` with
`IG_NEUTRAL_MULT 0.5` / `UNHAPPY_MULT 1.0` / `ANGRY_MULT 1.5`,
`MOVEMENT_SUPPORT_PASS_EFFECT 1.0` / `STALL_EFFECT 1.0`, `RULER_IDEOLOGY_EFFECT 0.05`.

Each checkpoint resolves into one of four outcomes named in
`politics_panel_change_law.gui`: `OUTCOME_SUCCESS`, `OUTCOME_ADVANCE`,
`OUTCOME_DEBATE`, `OUTCOME_STALL`. Success advances a phase, advance moves the clock,
debate costs time, stall adds a **setback**, and enough setbacks fail the chain into a
two-year lockout. Legitimacy enters as speed, not chance. The shape is right: a law is
a multi-stage object that can die *at a named stage*, death has a cooldown, and the two
pressures are inside-government clout (scaled by how angry that IG is) and outside
movement support. The surface is the trap — four percentages and a progress bar
(`GetCheckpointSuccessChance`, `…AdvanceChance`, `…DebateChance`, `…StallChance`) turn
legislation into a gacha pull with a pity timer.

## 1.7 Movements: the outside game, and the best mechanic in the file

`MOVEMENT_SUPPORT_POPULAR_SUPPORT_FRACTION 0.34`, `…_MILITARY_ 0.33`,
`…_WEALTH_ 0.33`. **A movement is one-third funded by wealth** — remarkable for a
Paradox game, and true to Babylon's world: a mass movement in the core has a donor
wing whether or not it admits it.

Radicalism is a 0–1 scalar (`AGITATING 0.25`, `PROTESTING 0.50`, `MILITANT 0.75`, civil
war at 1.0). Below 0.25 it does not affect enactment — and a define comment explains it
is floored at 0.25 *while a law it cares about is being enacted*, so placation cannot
defuse the fight mid-way. Above 0.5 supporters radicalize monthly (0.5–2.5%), and
radicalism produces state **obstinance** (`OBSTINANCE_MAX 0.2`, needs 0.5): local
administration stops working.

The pressure channel is the good part. A movement backed by ≥10% of an IG's clout becomes
an *influencing* movement for it (max 3 per IG), and pressure raises the weight of that
movement's ideology when the IG **generates its next leader**
(`MOVEMENT_PRESSURE_IDEOLOGY_FACTOR 1000`). Street pressure does not lobby the IG; it
changes who the IG is — a better model of party capture than any influence score, and the
mechanism Babylon's Topology/Electoral seam needs.

## 1.8 Legitimacy: what the number is made of

Clout of in-government IGs + their votes + **ideological incoherence** (approval
divergence × `INCOHERENCE_FACTOR 5`) + `LEGITIMACY_PENALTY_FOR_EACH_EXCESS_ENTITY
20` per IG over the allowance + law and head-of-state bases. The levels' ends carry
the design: **illegitimate** (<25) sets `country_must_have_movement_to_enact_laws_bool
= yes` — *under total illegitimacy only street pressure legislates*, a superb rule
Babylon should copy; **unacceptable** costs 25% enactment speed; **righteous**
grants 25%.

"Fit between who governs and what is law" is the right concept, and incoherence is the
honest term; what is dishonest is one scalar with no creditor named.

## 1.9 What V3 gets right, and where the trap closes

Borrowable: two currencies with a stated exchange rate; **frozen election results**;
coalition size bounded by formation arithmetic; the whip buying coherence rather than
votes; legitimacy with teeth at the bottom; movements rewriting personnel; anger scaling
obstruction; enactment failure carrying a cooldown; and amendments as riders — named,
sponsorable attachments, a better primitive than a slider.

Each row below is a Babylon prohibition, not a taste preference.

| V3 mechanism | Why Babylon cannot have it |
|---|---|
| Momentum rolled 0.5–1.5 | Dice. Equal input bytes must produce equal output bytes, and an election result is caused, not rolled. |
| Four checkpoint percentages on screen | Visible math: the player optimizes the number instead of reading the room. |
| `authority` as spendable currency | A resource with no payer. Real costs are money, time, legitimacy with named blocs, repression. |
| Legitimacy as one integer | Names no interest. "Legitimacy 62" cannot be argued with; an unpaid realtors' association can. |
| Radicalism as a 0–1 bar | Turns militancy into a fuel gauge. Babylon's version is countable: struck, showed up, arrested. |
| Institutions as 1–5 dials | Bureaucracy points buy modifiers; the honest version is staffing, caseloads, refusal. |
| Ideology as a scalar (−3…+3) | Collapses line, grievance, method into one axis; `06-mimp` requires the triple. |
| No donors, staff, or apparatus | The absorption mechanism is missing, so the staffer flip is unrepresentable. |
| No courts, preemption, injunction | A hard federal/state/municipal hierarchy V3 models nowhere. |
| No capital strike or bond market | The strongest constraint on a radical municipality; V3's investment pool does not punish politics. |
| No defection, recall, floor revolt | Office-holders are perfectly disciplined by construction. |

---

# Part II — Electoral as Babylon's screen 2

## 2.1 The screen's one job

**Let the player try to take state power by ballot, and find out what the ballot can and
cannot reach.** Not an electoral minigame, not a DSA-stickered side path: the DSA
electoralist is first-class, so the screen must be good enough that a competent player
wins real things on it, because only a real win teaches the real limit. `06-mimp` §11
already rules the content — the vote cannot reach Φ, it can buy **space** — and this
screen makes that sentence playable instead of asserted. Every element answers one of
three questions: who is with us and what do they cost; what can this office actually do;
what is stopping it right now, who do I move, and by when.

Three nested calendars, never bars. **The campaign** (six months, mirroring
`CAMPAIGN_PERIOD_MONTHS`): petition filing, endorsement season, first debate, the union's
endorsement meeting, last filing deadline. **The session**: a bill moves introduced →
committee (named chair) → floor → other chamber → executive → court, each stage holdable
by a named person, and adjournment kills, so failure is never a setback icon but "the
session ended." **The term** (four years, mirroring frozen votes): what you won is frozen
and accrues, so a year-one budget cut is a closed clinic in year three.

## 2.2 What is shown, what stays buried

| Visible — a participant could read it in a communist history book | Buried — the author's desk drawer |
|---|---|
| Votes cast per ward and candidate | Any projection or vote-share probability |
| Seats held, by party and ward | Party momentum |
| Endorsements, by organization name | Endorsement weight |
| Funds raised, and from whom | Donor propensity |
| Volunteers and hours | Capacity coefficients |
| Bills introduced, committee, chair, week | Checkpoint success chance |
| Injunctions, case numbers, courts | Legitimacy scalar |
| What got cut, and whose money moved | Creditworthiness formula |
| Police union sick-outs and staffing | Control-ratio internals |
| Strikes, picket counts, arrests | Radicalism scalar |

The rule is mechanical, not stylistic: **if it has a percent sign, it belongs in
the engine, not on the screen.**

## 2.3 From Topology to the arena

Nothing enters the arena except as a node with an edge. There is no free-floating
"public opinion" and no national mood bar; the arena is a *projection* of the graph,
and that projection is the claim: **politics is the set of organizations that can be
made to act.** Each node projects with four attributes — members, money, discipline,
willingness.

| Node | What it gives | What it wants | Its contradiction |
|---|---|---|---|
| Union local | Bodies, dues, strike threat, ward walks | Contract, recognition, jobs | Leadership's peace with the employer vs. members' militancy |
| Church congregation | Trust, space, volunteers, moral cover | Respect, autonomy, quiet on social questions | Pastor's respectability vs. the congregation's material life |
| Landlord association | Money, legal firepower, council access | Rent enforcement, no inspection regime | Small owner's debt vs. the association's line |
| Police union | The other side of the strike threat | Contract, staffing, immunity | Public-safety credibility vs. insubordination as a veto |
| Chamber of commerce | Money, media access, the rating agency's ear | Low taxes, no labor ordinance | Downtown vs. outer-ring membership |
| NGO | Staff, legal aid, respectability, grants | Access, measurable outputs | Funder's line vs. base's line (respectability flip) |
| Party chapter | Volunteers, canvass, ballot line | Endorsements, patronage, careers | Activist base vs. office-holder (spokesperson flip) |
| Tenant association | Turnout, direct action, the eviction count | Rent freeze, code enforcement | Defending members vs. growing citywide |
| Prison guard local | Blocking power over anything carceral | Overtime, headcount | The prison as jobs program (`06-mimp` §12) |
| University | Expertise, students, venue, legitimacy | Funding, autonomy | Research money vs. campus as a base |

**Proposed** projection contract: `arena_weight = f(members, dues, discipline,
willingness)`, willingness a function of how the node was recently treated by the player's
organization and by the state. The engine computes the weight; the screen shows the four
inputs as world-facts — "Local 1199: 4,200 members, endorsed, $18,000, sixty canvassers
on Saturday." So **an endorsement is a decision, not a token** (a union spends its own
discipline to deliver members, and failure shows up on election day as absent bodies),
and **money is traceable** (the financial layer publishes receipts, so a rival's donation
is a visible transfer).

## 2.4 What a seat can actually do

An office is a **verb set with a material reach**. Every verb must resolve into an
existing system or it does not ship.

| Verb | What it touches | Bound |
|---|---|---|
| **Space** — permits, plazas, bulletin boards, halls, non-enforcement of assembly rules | Topology: new venue and legal-meeting edges; the MIM carve-out | Reach ends at the municipal line |
| **Budget** — allocations, priorities, hiring freeze, shelter contract | `babylon-material-circuit::financial`: `PublicBudget{period_cap, cash_floor}`, `PublicAllocation{priority}`, receipts with `paid`/`unfunded` | `period_cap` is not the council's to set |
| **Non-cooperation** — sanctuary ordinance, no immigration referrals, no carceral expansion | Sovereignty and control-ratio flows; a specific transfer stops | A superior jurisdiction can void it |
| **Bail, pardon, charging** — DA and sheriff are the highest-leverage races | Carceral node capacity; released organizers become new edges | Judges are not elected everywhere; the union still staffs |
| **Tribune** — hearings, subpoenas, oversight | Intel ledger unlocks: a named fact becomes public knowledge | Changes what is known, never what is produced |
| **Appointments** — police review board, election board, zoning | Repression intensity, ballot access | Appointees are people with careers |

And the verb that does not exist, said plainly in the world: **no municipal, state,
or congressional act reaches Φ.** A bill claiming to redistribute imperial rent
either fails at incidence — the cost lands on the workers it meant to help — or
becomes a claim *on* the rent, the `bigger-slice` trap of `06-mimp` §6. Not a locked
button: a mechanism the player can hit repeatedly, from different coalitions, and get
the same receipt from.

## 2.5 The five barriers, as systems and not vetoes

Each is executed by a system that exists or is already scheduled, and each produces a
named world-fact with a date. The fact is the teaching.

**1. Capital strike and the bond market.** A radical council passes a tenant bill; the
money does not arrive. The channel is `PublicBudget.period_cap` and `cash_floor` — the
allocation is authorized, the receipt returns with `unfunded` non-zero, and the shelter
does not open; ownership claims relocate, because the tax base was not where the council
thought. **Honest limit:** `babylon-material-circuit` models taxes, ownership,
distributions, budgets, allocations, and capital contributions (`financial/model.rs`),
but no debt instrument. A municipal bond market is **proposed** — "the rating agency
downgraded the city" is the most legible fact in American municipal politics — and until
then `period_cap` and `unfunded` carry the argument with less flavor.

**2. Injunction and preemption.** The ordinance passes; a court voids it. Sovereignty
says a superior jurisdiction supersedes a subordinate's rule, so the ordinance row
becomes `void` with a case number and a court. The bill was not blocked — it was *won and
then annulled*, a different and far more instructive defeat. State preemption of
municipal labor and sanctuary law is the ordinary American condition and should be the
ordinary Babylon condition.

**3. Police union insubordination.** The reform passes, is funded, and is not enforced.
Armed men carry triple political strength by baseline, so refusal is not a modifier but a
weight; control-ratio falls while the budget line rises. The screen shows a sick-out, a
staffing table, a union president's statement, and an arrest count that did not change.

**4. Absorption.** The candidate wins, and eighteen months later votes with the chamber.
No single flip event — drift with visible symptoms, per `06-mimp`'s flip rules: the
chapter newsletter's byline mix changes before the line does; the donor mix shifts; the
office-holder's `who_pays` set gains a member; the whip stops holding because the person
being whipped now has a career. The DSA character is "the most competent person in the
room and the least able to say the word rent" — competence is what makes absorption work,
because competence is employable.

**5. The Φ ceiling.** `fundamental-theorem.bsl` is twelve lines and it is the whole
argument: while core wages exceed the value core labor produces, the gap is imperial rent
and revolution in the core is materially foreclosed. No bill changes `W_c − V_c`. Only
the levers that change the circuit do — the periphery, the border, decomposition, the
wage relation. Every other demand is a claim on the dividend. So the honest ending is not
"you lost the election"; it is "you won, and the number did not move."

## 2.6 Anti-rail doctrine

**The refusal is never at the door; it is at incidence.** File any bill, run any race,
build any coalition; discover who pays. **`ActionAvailability::Unavailable(reason)` is
reserved for constitutional impossibility** — `babylon-client/src/decision_surface.rs`
already carries the pattern (ADR249 R9: a declared, honestly-unavailable verb with its
reason), and it must never become "the designers think this strategy is wrong." Reserve
it for what a city council genuinely cannot do: secede a state, repeal a treaty, abolish
the wage relation by ordinance. **Bias sits in starting conditions, never in endings:**
the DSA start is high competence, high access to respectability and money, deep ward
knowledge, low incidence literacy, and a chapter whose most active members want to win —
a real advantage that should feel like one. **No dice:** determinism forbids the
checkpoint roll, so uncertainty comes from fog (the chair's intentions) and adversary
intent (the bank, the union, the county party, the court), and a result that cannot be
re-rolled is *more* frightening.

`porch-01`'s three layers map cleanly: **the seal** is the filing or the vote (sting,
receipt stub, "the county party will react; you'll read about it"); **the reckoning** is
election night or the committee vote, story first, numbers second; **the long tail** is
the injunction three periods later and the byline that changed two periods before the
line did. The epilogue is not a verdict on the strategy: it says what happened — the
ordinance, the injunction, the shelter that never opened, the number that did not move —
and lets the player argue about it. What is not borrowed: visible probabilities, a
spendable authority currency, dice at the moment of decision, a one-dimensional ideology
axis, institution dials for state capacity, or the party-as-archetype-file pattern —
Babylon's parties should be made of nodes, not selected from a list of twelve.

## 2.7 A worked election night

Not a mockup — a constraint on the data model; every clause must be a fact the engine
can emit.

> Twelve wards, three blocs filed. Local 1199 endorsed on the 14th and delivered sixty
> canvassers for three weekends; the landlord association put $40,000 into the
> incumbent's race and $9,000 into a mailer that landed on the 2nd. Turnout was 31% in
> the two university wards and 12% in the two outer-ring wards. We took four seats, lost
> the two we needed for a majority, and won the ward where the church endorsed.
>
> The morning after: the council president offered the housing committee to our
> second-best vote-getter. The water authority's bond note came back at a higher rate.
> The police union president said the department would "review its staffing model."

Every clause is countable; nothing is a percentage to optimize. The next decision is
legible: take the committee and lose a vote-getter to the whip, or refuse and keep the
bloc intact and outside.

## 2.8 Open questions for the porch

1. **Does the organization run candidates or endorse them?** That decides whether the
   office-holder sits inside the graph, and therefore whether the spokesperson flip is
   a drift or a defection.
2. **Does the bond market belong here or in the material circuit's next cut?** It is a
   `financial` model extension and must not be smuggled in through a screen.
3. **How does the DSA player learn incidence?** By losing once to an unseen payer, or by
   an INVESTIGATE that names the payer before the vote? The first teaches better; the
   second is kinder, and the veil-of-money rule suggests it only after Tier 1.
4. **Confirm the slot ordering.** `babylon-tick/src/phase_order.rs` declares `electoral`
   (ordinal 23, Consequence) immediately before `policy` (24): the election adjudicates
   and policy consumes, so the vote should be an *event* the policy slot reads, not a
   state the electoral slot writes straight into law.
