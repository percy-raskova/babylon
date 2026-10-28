# 11 — Victoria 3's electoralism, read out of the compiled binary

**Status:** porch-session design research. Nothing here implements or changes game
law. Claims about shipped Babylon code cite the file; proposals say **proposed**.

**Provenance.** Victoria 3 local install, `release/1.13.11`; caligula rev
`15aa89ae429b6bcff8d195f2a650f98ba95cd64c`, clausewitz rev
`a93467deb3d07433163df1bf541cce7a05dd110e`; ELF build-id `dc1d1a8fdfaed905`,
1 576 608 824 bytes, `with debug_info, not stripped`. DWARF file names resolve to
`/mnt/gsg/caligula/caligula/source/logic/*.cpp`, so every claim lands on a line of
Paradox's own source tree.

**Relation to `10-v3-electoralism-and-babylon.md`.** Ten read the *data*. This reads
the *code*: it confirms ten, corrects it in three places (§4), and finds four
mechanisms data alone could not show. Ten remains the design argument; this is the
mechanism, not a competing authority.

**Guardrail unchanged.** Structure only; no Paradox text, art, or scripting enters
Babylon. MIM(P)/MLM-TW per `06-mimp-and-mlm-tw-canon.md`: the vote cannot reach Φ,
it can buy *space*, and electoralism is a trap you may walk into and read the
receipt for.

---

## 0 — Evidence ledger

| Attempt | Result |
|---|---|
| REA `binary_session` | `open: true`, full Ghidra capability set |
| REA `procedure_info(0x2d32ec0)` | **`provider_timeout`, `timeout_ms: 330000`** — "Analysis took too long." Ghidra's whole-program import cannot finish inside the REA budget on a 1.57 GB ELF. No Evidence ID produced; every Ghidra-backed operation on this artifact is expected to fail identically, as on Stellaris/HOI4/Civ6. |
| `nm -C` / `gdb … ptype /o` / `objdump -d -l --demangle --disassemble=<sym>` / local `call rel32` scan of `.text` | 537 269 symbols; ~14 s to load; per-instruction `source/logic/*.cpp:LINE`; callers the symbol table withholds |

**Limits.** No decompiler ran (REA timed out; Ghidra not invoked out of process).
Pseudo-C below is hand-reconstructed from `objdump -dl`: reliable on control flow
and operand identity, less so on expression grouping inside the `fixed_int64.h`
reciprocal-division sequences. Two claims are marked *inference*.

---

## 1 — The object model

### 1.1 Election state is a country-level scalar per party, and nothing finer

```c
struct SElectionData {                        // 88 B, one per country
  TPdxRef<CCountry> _Country;                 // +24
  CGameDate _NextElectionDate, _LastElectionDate;       // +28, +36
  CFixedPoint _ElectoralConfidence;           // +48
  CPdxArray<SPartyElectionData> _PartyElectionDataArr;  // +56
  bool _HasCampaignStarted, _HasChangedGovernment,
       _StartedCampaignHadElection;           // +80..+82
};
struct SPartyElectionData {                   // 112 B, one per party
  TPdxRef<CParty> _Party;  CFixedPoint _RawMomentum;   // +8,  +16
  int64 _RawVotingPower;   int64 _RawNumVoters;        // +24, +32
  int64 _LastVotes;        TIndividuals _LastNumVoters;// +40, +48
  CGameDate _LastVotesDate; CTrend _VotesTrend;        // +56, +64
};
```

There is **no ward, district, candidate, or per-pop vote record** in the election
object graph — an election is `n_parties` integers. Everything granular V3 appears
to show is computed elsewhere and discarded. This is the largest thing Babylon must
not copy, and precisely why ten §2.7 can promise twelve wards as countable facts.
`CElectionManager` (240 B) adds only a `CPdxArray<SElectionData*>` and a
`CPdxRefLookup<CCountry, CJominiHistoricalDate> _CountryLastReformDates`.

### 1.2 Parties: archetype, two membership lists, one frozen number

`CParty` (152 B): `_pDef` +40 (the archetype file), `_Members` +48, `_MembersToBe`
+72, `_Leader` +96, **`_VotingPowerLastElection` +104**, `_NumVotersLastElection`
+112. `CParty::Join` (party.cpp:121–128) searches `_Members` then searches
`_MembersToBe` and returns early if *either* holds the IG;
`PromoteAndRemoveMembers()` reconciles them; `EPartySwitchType {Instant,
NextElection}` picks the boundary. *Inference:* `NextElection` is the `_MembersToBe`
path. Either way membership change is **staged and boundary-committed**.
`_VotingPowerLastElection` is the only durable output of an election: office-holding,
cabinet seat splits, and the legitimacy vote term all read it until the next
election overwrites it.

### 1.3 Interest groups: one clout scalar, plus the street map

`CInterestGroup` (736 B): `_Party` +0x9c, **`_PoliticalStrength` +0xc8**,
`_MovementSupport` +0x200 (map → `SInterestGroupMovementSupport
{_SupportingIndividuals, _SupportingPoliticalStrength, _SupportingFractionOfClout}`),
`_InfluencingMovements` +0x220 (cap `IG_MAX_INFLUENCING_MOVEMENTS = 3`).

The street→IG channel is not a modifier. It is a **row recording how much of this
IG's clout stands with that movement**, which is what
`GetFractionOfCloutSupportingMovement` returns and what the 5 %/10 % defines gate.

### 1.4 Laws

`CCountryLaw` (144 B) carries **`_EnactmentRandomSeed` +104 (persisted)**,
`_CheckpointProgress` +112, `_EnactmentPhase` +120, `_EnactmentSetbackCount` +124,
`_EnactmentLastCheckpointResult` +128. Enums:
`ELawEnactmentCheckpointResult {None, Success, Advance, Debate, Stall}`;
`SLawCheckpointResultChances {_SuccessChance, _AdvanceChance, _DebateChance,
_StallChance}` at +0/+8/+16/+24.

---

## 2 — Five pipelines, decompiled

### 2.1 Clout: one pool per pop, split by who shows up

`CInterestGroup::CalculatePopPoliticalStrength` (interest_group.cpp:674–682,
`0x3833e20`) sums, over member pops,
`pop.GetPoliticalStrength(pop.GetNumInterestGroupMembers(this->GetType()))`.
`CPop::GetPoliticalStrength(int64 n)` (pop.cpp:1633–1651, `0x3bc8550`):

```c
if (popType->Flags & 0x2) return 0;                 // 1634  dependents
int64 active = CalcNumPoliticalParticipants();      // 1639
if (active <= 0) return 0;                          // 1640
int64 pool = SPopPoliticalStrength[pop]._TotalPoliticalStrength;  // 1644
if (active == n) return pool;                       // 1645
return fixed_mul(pool, fixed_div(n, active));       // 1645-1651
```

Bit `0x2` is the same pop-type flag `GetNumInterestGroupMembers` tests to refuse
membership (pop.cpp:2217), i.e. dependent pops — *inference from the shared flag*,
but the two sites are unambiguous.

**The best primitive in the layer.** A place's political capacity is one `int64`;
two IG types cannot both count it, because the pool is partitioned by
`members/politically-active`. Class politics is not two power scores added, it is a
**division of one local quantity**: a pop 60 % union and 40 % petite-bourgeoisie
yields 60/40 of its own clout, and double-counting is structurally impossible.
`GetTotalPoliticalStrengthIncludingPartyVotes` (686–690) =
`_PoliticalStrength + Party->GetVotingPowerFor(*this)`.

### 2.2 Votes: the franchise is a code path, not a coefficient

`CElectionManager::CalculateVoteCountFor` (election_manager.cpp:849–868,
`0x30ee150`) walks each member IG (853→855), then each of that IG's pops in the IG's
country, and takes `n = pop.GetNumInterestGroupMembers(igType)` (858),
`vp = pop.CalcVotingPower(n, nullptr)` (859), accumulating `votes += vp; voters += n`
when `vp > 0` (860–863). The voter is the **IG member**, not the pop.

`CPop::CalcVotingPower(int64 n, CString *desc)` (pop.cpp:1772–1840, `0x3bc9fa0`)
gates in order: pop type votable (1773); `pop.Wealth() >=
mod(CountryVotingPowerWealthThresholdAdd)` (1750–1780); state incorporation > 0
(1785–1787); pop-type voting weight > 0 (1794–1797); then (1832–1840) a
`CValueCalculator` sums `voting_power_base + voting_power_pop_type +
voting_power_wealth + voting_power_literacy`, scaled by `country_voting_power_mult`.

Those entry names are shipped strings, and modifier localisation fixes the
semantics: `country_voting_power_base_add` is "**political strength per Vote**";
`country_voting_power_from_literacy_add` is the same "modified by the literacy of
the voting pop"; `country_voting_power_wealth_threshold_add` is the "**Wealth
Threshold for Voting**". Joined to `laws/00_distribution_of_power.txt`, three
franchises become three different code paths:

| Law | wealth gate | `voting_power_base` | per-class weight | result |
|---|---|---|---|---|
| `law_landed_voting` | none | 0 | aristocrats +100, officers +50, clergymen +50, capitalists +50 | **class franchise** — four IG types vote, unequally |
| `law_wealth_voting` | `wealth ≥ 20` | 50 | none | **property franchise** — flat vote above a wealth line |
| `law_universal_suffrage` | none | 50 | none | **headcount** — flat vote per eligible individual |

V3 does not model "wealth buys votes". It models **three distinct enfranchisement
algorithms**, and wealth-weighted *political strength* is a separate always-on
quantity that never enters this function. The two currencies are two different
functions of the same pop, and only one consults the franchise.

### 2.3 The finding ten could not see: seats split by clout, not votes

`CParty::GetVotingPowerFor(CInterestGroup const&)` (party.cpp:285–318,
`0x3b68b90`):

```c
int64 partyVotes = GetCurrentVotingPower();                  // 287  frozen last election
if (partyVotes == 0 || !_Members.Contains(ig)) return 0;      // 287, 293
if (_Members.size() == 1) return partyVotes;                  // 299  sole member takes all
int64 total = 0;
for (auto m : _Members) total += m->GetPoliticalStrength();   // 305-307 (+0xc8)
return fixed_mul(partyVotes, fixed_div(ig.GetPoliticalStrength(), total));  // 318
```

**Votes nominate the party; clout allocates the party's seats.** A frozen electoral
result is divided among member IGs by *pre-election political strength*, not votes.
Win 30 % with a party whose largest member is the chamber of commerce and the
chamber takes almost all of it. This is "electoralism is a trap" on executable
grounds: you do not lose by losing — you win, and then discover who inside the
coalition the win belonged to.

### 2.4 Campaign: polls run six months a cycle, and momentum only renormalises

`RecordVotingPowerToPoll` (`0x30ece00`, election_manager.cpp:110+) early-returns
unless `IsCampaignPeriod(country)` (112), then parallel-sums
`CalculateVoteCountFor` into `_RawVotingPower`/`_RawNumVoters` (124). **Outside the
campaign window there is no live vote count at all** — results freeze because the
sampler stops, not because a flag is set. `AddMomentum` (910–923, `0x30ee5f0`)
likewise early-returns (913), creates the party row through
`FindOrCreateElectionDataForParty(party, NRandom::GlobalRandom)` (919–920), and
writes `max(_RawMomentum + amount, 0)` (921) — **clamped at zero**.

`CalcMomentumScaledVotes` (406–442, `0x30eb110`) computes, over every party row,
`sv = mul_shift14(_RawVotingPower, momentum)` and `sn = mul_shift14(_RawNumVoters,
momentum)` (418–419), tracks the party's own pair (420) and the two sums (425–428),
then returns `votes = myVotes × 100000 / Σsv`, `voters = myVoters × 100000 / Σsn`
(438, 441). Share is `(clout-votes × momentum) / Σ(clout-votes × momentum)` in
1/100000 units.

Momentum **redistributes** share and creates nothing: a party with no clout cannot
be helped by it, and momentum is `_RawMomentum + leader.popularity ×
POPULARITY_MOMENTUM_FACTOR` (374–403, `0x30ea7f0`). On election day
`RecordFinalResults` (999–1017, `0x30eeb70`) loops potential parties calling
`SetVotingPowerFromLastElection(pd._LastVotes, pd._LastNumVoters)` (inlined,
party.cpp:253); `TriggerElection` (1020–1027, `0x30ec160`) stamps
`_LastElectionDate` and adds `ELECTION_INTERVAL_YEARS × days/year`, reading the
define from the live global at `0x8743418` — defines are runtime data.

### 2.5 Law enactment: a persisted hash, and a fourth number nobody uses

`CCountryLaw::ResolveEnactmentCheckpoint` (country_law.cpp:991–1025, `0x2d32ec0`):

```c
SLawCheckpointResultChances c = CalcCheckpointChances({}, 0,0,0,0);      // 993
uint32 seed = _CountryRef.id + _EnactmentRandomSeed + gameState.tickOffset;  // 1298
int64 roll = CNoiseRandom(seed).SampleInt64(0, 100001);   // roll ∈ [0, 100000]
if      (roll <= c._SuccessChance)                    r = Success;   // 997
else if (roll - c._SuccessChance <= c._AdvanceChance)  r = Advance;   // 1003
else if (roll <= c._Success + c._Advance + c._Debate)  r = Debate;
else                                                   r = Stall;     // residual
SetEnactmentCheckpoint(r); _EnactmentLastCheckpointOrStopDate = now;  // 1022-1023
```

1. **It is not dice.** The roll is a pure function of `(country id, persisted law
   seed, tick)`. Same save, same tick, same roll, forever.
2. **`_StallChance` is never compared.** Four percentages are computed and shown;
   three are used. The UI is more precise than the engine.
3. Inputs come from `CalcCheckpointChances` (`0x2d297c0`): ruler ideology (655–656),
   per-IG `CalcLawApprovalValue` scaled by neutral/unhappy/angry multipliers (610,
   646), treaty commitment (691–712), and **per-movement
   `GetCountryLawEnactmentStance`** (725, `0x3b9ff00`). Both pressure channels merge
   into one scalar — which is exactly why the honest surface had to be a
   percentage: the engine no longer knows *who* is stalling.

### 2.6 Legitimacy: the franchise law sets the coefficients

`CGovernmentHelper::CalcLegitimacy` (`0x378f4a0`) composes

```
  mod(CountryLegitimacyBaseAdd) + mod(CountryLegitimacyHeadOfStateAdd)
+ mod(CountryLegitimacyGovtLeaderCloutAdd)   × governing leader's IG clout
+ mod(CountryLegitimacyGovtTotalCloutAdd)    × CalcTotalClout()
+ mod(CountryLegitimacyGovtTotalVotesAdd)    × CPartyManager::CalculateVotingPowerShare(p)
− Σ_lawgroups[CalcIdeologicalIncoherenceForLawGroup(g)] × mod(..._IdeologicalIncoherenceMult)
− (govt size − mod(CountryLegitimacyGovtSizeAdd)) × LEGITIMACY_PENALTY_FOR_EACH_EXCESS_ENTITY
  clamped by mod(CountryLegitimacyMinAdd)
```

All eight modifier types exist in the binary. The franchise law supplies the two
coefficients: landed 100 clout / 40 votes; wealth 75/65; census 55/85; universal
**25/110**. Widening the franchise does not add legitimacy — it **reprices
legitimacy from a clout-denominated asset into a vote-denominated one**. The teeth
live in data (`common/legitimacy_levels/`): `illegitimate` sets
`country_must_have_movement_to_enact_laws_bool = yes`; `unacceptable` sets
`country_law_enactment_speed_mult = -0.25`. `CalcDailyProgress` (`0x2d28bc0`) reads
both boolean modifiers before computing anything: **under total illegitimacy the
only legislator is the street**, confirmed in code and not only in data.

### 2.7 Movements: three support channels, a slow lag, a cadenced escalation

`CPoliticalMovement::UpdateSupportAndRadicalismData` (political_movement.cpp:502–507,
`0x3b99940`) is five calls: `CalcPopSupportData(popular)` (503),
`CalcPopSupportData(military)` (504), `CalcSupportData` (505),
`CalcUnclampedRadicalism` (506), `CalcRadicalismData` (506). The three
`MOVEMENT_SUPPORT_*_FRACTION` defines (0.34/0.33/0.33, documented as summing to 1)
are the combination weights. `DoWeeklyRadicalismChange` moves radicalism toward
target by `MOVEMENT_WEEKLY_RADICALISM_CHANGE = 0.01` per week — a first-order lag
with a ~70-week constant, not a slider. Above 0.5 radicals accrue at 0.5–2.5 % a
month; at 0.5 obstinance accrues (cap 0.2) and the local state stops administering.
`CCivilWar::CalcCivilWarProgressAtCheckpoint` (`0x2ef30a0`, civil_war.cpp:1197+)
clamps to 0.25 per 8-week checkpoint, decays 0.1 without support, weights by
0.2 × radicalism; start needs radicalism ≥ 1.0.

The outside game is therefore **slow lag → countable defection → named threshold →
cadenced escalation**. Nothing in it is a bar the player nudges.

---

## 3 — What this proves about street vs. coalition

The separation is not stylistic. It is two disjoint data structures with exactly one
shared scalar in each direction.

| | Coalition (inside) | Movement (outside) |
|---|---|---|
| Currency | clout + frozen ballots | `_SupportingFractionOfClout` + radicalism |
| Membership | `CParty._Members` (≤ 3 by formation arithmetic) | `_Pops`, `_Characters`, one `_Identity` triple |
| Persistence | committed at election, frozen a term | weekly integrator, no boundary |
| Reaches the law | `CalcCheckpointChances`: IG approval × angry multiplier | the *same* function: `GetCountryLawEnactmentStance` |
| Reaches personnel | `CParty::UpdateLeader` | `MOVEMENT_PRESSURE_IDEOLOGY_FACTOR = 1000` on the next leader draw |
| Failure mode | loses a vote, loses legitimacy, gets whipped | obstinance, radicalisation, civil-war checkpoints |
| Buyable? | yes — approval is a number | no — a third wealth, a third bodies, a third guns |

**The only place the two channels meet is the enactment chance scalar.** That is an
architectural weakness and it explains the surface: the engine merges two
incompatible politics into one number, so the only honest UI is a number. Babylon
should keep them apart to the outcome — the bill dies at a *named committee* held by
a *named chair*, and separately the ordinance is not enforced because a *named
union* refused. Two actors, two failures, no shared probability.

**The street reaches personnel, not policy.**
`MOVEMENT_PRESSURE_IDEOLOGY_FACTOR` raises an ideology's weight when an IG
*generates its next leader*: pressure does not lobby the IG, it changes who the IG
is. That is the correct model of institutional capture, and the seam where Topology
and Electoral physically meet — a movement node grows edges into an IG node, the
leader edge rewires, and the party's line changes with no vote having moved.

---

## 4 — Three corrections to document 10

**4.1 "Dice" is the wrong objection; causality is the right one.** Ten forbids
momentum 0.5–1.5 because "equal input bytes must produce equal output bytes." But
both the momentum draw and the enactment roll are seeded from persisted state
(`_EnactmentRandomSeed` is a stored field), so V3 already *satisfies*
byte-determinism. The real objection is epistemic: a hash roll makes the outcome a
function of a seed rather than of causes, so nobody can be blamed and the receipt
names no creditor. The stronger Babylon rule is **"every outcome must be
attributable to a named actor's decision"** — which forbids the roll without
forbidding a seeded tie-break inside a count that turnout already explains.

**4.2 Parties do decay, at a boundary.** Ten says V3 has "no coalition decay."
`_Members`/`_MembersToBe` plus `EPartySwitchType{Instant, NextElection}` mean IG
membership does change. What V3 lacks is **defection by a person**: an office-holder
is never separable from their IG, so there is no floor revolt, caucus, or recall.
Babylon's absorption (ten §2.5 item 4) needs that missing entity — the individual
office-holder as a graph node with their own `who_pays` set — and it is a *topology*
addition, not an electoral one.

**4.3 Legitimacy is not one integer even inside V3.** It is a five-term composition
whose coefficients come from the franchise law and whose incoherence term is summed
*per law group*. The "one scalar with no creditor" critique is about the **display**
and it stands, but Babylon needs no scalar to get the effect: the teeth are
thresholds on a computed quantity. Compute a **named coalition-coherence ledger**
(who owes what, which law group each debt violates) and derive enactment speed and
radical growth from it, never showing a `62`.

---

## 5 — What Babylon takes, and what it inverts

### 5.1 Take — five primitives that survive the compact

1. **One political-capacity pool per place, partitioned by participation.** Class
   conflict gets a *conserved quantity* and double-counting becomes impossible. It
   maps onto a public hyperedge: the pool is the place, the partition is each IG's
   incidence on it, the split is observable.
2. **Two currencies with a law-set exchange rate.** Clout permanent and always on;
   ballot weight an enfranchisement algorithm. Keeping them separate is what lets a
   player *win* and still not hold the office.
3. **Results frozen for a term, because the sampler stops.** The vote becomes an
   event the policy phase consumes (`babylon-tick/src/phase_order.rs`: `electoral`
   23 → `policy` 24) and office-holding a durable graph edge with a term. Breaking
   it early costs something paid by people — `REFORM_GOVERNMENT_RADICALIZATION_RATE
   = 0.25` is the right *shape*, not a resource.
4. **Street pressure rewires personnel** — promote
   `MOVEMENT_PRESSURE_IDEOLOGY_FACTOR` from hidden multiplier to visible graph
   event: *"the chapter elected a new chair, 61–39."* Best borrow in the file.
5. **Illegitimacy hands legislation to the street** — copy the rule, not the number.

### 5.2 Invert — four things that must not survive translation

| V3 | Babylon |
|---|---|
| Four checkpoint percentages, three of them used | The bill dies at a named stage held by a named person, or the session adjourns. No percentage exists. |
| One scalar `legitimacy` | A coherence ledger naming which bloc's demand each active law violates. |
| Party = archetype file out of twelve | Party = a coalition of graph nodes with a written platform (ten §2.3). No catalogue. |
| Election = `n_parties` integers | Ward-level tallies with candidate identity, so "we lost the two we needed" is printable. |

### 5.3 Where the collisions plug in

- **Franchise arithmetic → whose win it was.** Before universal suffrage the class
  franchise weights ballots per IG type; after it headcount rules — but
  `GetVotingPowerFor` still splits seats by clout. Passing universal suffrage is not
  a buff, it is a **change of accounting basis**: a labour party gains votes while
  its petit-bourgeois partner keeps the seats. Available on day one, no new mechanic.
- **Legitimacy coefficients → capital's structural advantage.** The clout coefficient
  falling 100 → 25 as the franchise widens is the material form of "the bourgeoisie
  does not need the vote, it has the balance sheet." Babylon needs no coefficient:
  the organs that answer to ownership (bond market, courts, preemption) are simply
  *not the organs that answer to votes*, so widening the franchise moves power
  between institutions and owners switch venues.
- **Obstinance → preemption and non-enforcement.** `OBSTINANCE_MAX = 0.2` at
  radicalism ≥ 0.5 is V3 admitting a hostile locality stops administering; Babylon
  has the honest form already (ten §2.5 items 2–3).
- **The Φ ceiling.** Nothing in this binary touches it, which is the point: the whole
  electoral apparatus — `SElectionData`, `CCountryLaw`, `CGovernmentHelper` —
  manipulates distribution and legitimacy, and not one instruction reads or writes
  the wage/value relation. The largest political machine Paradox has shipped has no
  wire to `W_c − V_c`. That belongs in the epilogue, because it is true of the
  artifact and not only of the argument.

### 5.4 Proposed, explicitly not implementation

- **`PoliticalCapacity` per place** — one pool per hex/settlement, partitioned across
  IGs by `participants/active`, emitting a `CapacityPartition` receipt so the split
  is auditable and the pool conserved. `Derived`.
- **`FranchiseRule`** — typed (`ClassWeighted | WealthGated | Headcount`), coefficients
  authored in `content/scenarios/michigan/defines.toml` per ADR258. `Designed`.
- **`SeatAllocation`** — party tallies × member clout → per-IG seat counts plus a
  receipt naming each member's share; makes "you won and it wasn't yours" computed
  rather than scripted.
- **`CoalitionCoherence`** — per law group, the named conflict between an active law
  and a governing bloc's platform; feeds enactment speed and radical growth as an
  *effect*, never as a stored score. `Derived`.
- **`MovementPressure`** — a movement→IG edge carrying
  `{individuals, clout_fraction}` whose only consumer is the IG's next leadership
  selection. Never a modifier on behaviour.

All five respect the compact: no new mathematical primitive, typed effects,
determinism holds because each is a function of stored state, and each answers a
decision question ("whose seats are these?", "who do I have to move by Tuesday?")
rather than an administrative one.

---

## Appendix — Evidence index

| Address | Symbol | Source |
|---|---|---|
| `0x3bc8550` | `CPop::GetPoliticalStrength(long long)` | pop.cpp:1633–1651 |
| `0x3bc9fa0` | `CPop::CalcVotingPower(long long, CString*)` | pop.cpp:1772–1840 |
| `0x3833e20` | `CInterestGroup::CalculatePopPoliticalStrength()` | interest_group.cpp:674–682 |
| `0x30ee150` | `CElectionManager::CalculateVoteCountFor` | election_manager.cpp:849–868 |
| `0x30ece00` | `RecordVotingPowerToPoll` | election_manager.cpp:110+ |
| `0x30ea7f0` | `…::CalcCurrentMomentumWithPopularity` | election_manager.cpp:374–403 |
| `0x30eb110` | `…::CalcMomentumScaledVotes` | election_manager.cpp:406–442 |
| `0x30ee5f0` | `…::AddMomentum` | election_manager.cpp:910–923 |
| `0x30eeb70` | `…::RecordFinalResults` | election_manager.cpp:999–1017 |
| `0x30ec160` | `…::TriggerElection` | election_manager.cpp:1020–1027 |
| `0x3b68b90` | `CParty::GetVotingPowerFor(CInterestGroup const&)` | party.cpp:285–318 |
| `0x3b68060` | `CParty::Join(CInterestGroup&, EPartySwitchType)` | party.cpp:121–162 |
| `0x2d32ec0` | `CCountryLaw::ResolveEnactmentCheckpoint()` | country_law.cpp:991–1025 |
| `0x2d297c0` | `CCountryLaw::CalcCheckpointChances(...)` | country_law.cpp:533–~990 |
| `0x2d28bc0` | `CCountryLaw::CalcDailyProgress()` | country_law.cpp:~520 |
| `0x378f4a0` | `CGovernmentHelper::CalcLegitimacy(CString*)` | governmenthelper.cpp:363+ |
| `0x3b99940` | `CPoliticalMovement::UpdateSupportAndRadicalismData()` | political_movement.cpp:502–507 |
| `0x2ef30a0` | `CCivilWar::CalcCivilWarProgressAtCheckpoint` | civil_war.cpp:1197+ |

`NDefines` are live runtime objects, e.g. `0x8743418
NDefines::NPolitics::ELECTION_INTERVAL_YEARS` and `0x8742b48
…::LAW_ENACTMENT_MIN_TOTAL_DAYS` — which is why the values in
`game/common/defines/00_defines.txt` are authoritative for every formula above.
