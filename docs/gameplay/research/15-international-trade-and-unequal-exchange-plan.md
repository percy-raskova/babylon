# 15 — International Trade and Unequal Exchange: synthesis and build plan

Read-only synthesis, 2026-10-25. Question: **how does the world market actually work in Babylon today,
what does the canon require of it, and what is the shortest honest path from the hash-pinned tables
already in the tree to a player who can act on Imperial Rent from inside the United States?**

**Guardrail.** No Trotsky. The line is MIM(P)/MLM-TW: the Third World is the main force, the core
proletariat is not the subject, and "workers unite" is a failure mode to encode, never a mechanism to
derive (`07` §3.6, `06` §0). Every design consequence below is checked against that.

**Visibility rule (porch-01 §94).** No screen shows Φ, `s/v`, ERDI, an extraction coefficient or any
rate. Countable world-events — shipments, tonnages, prices, ports, border crossings, strikes, layoffs,
leaked dossiers — may show. The one legal place for a formula is an enemy artifact: an IMF letter of
intent, a TNC sourcing manual, a World Bank country strategy (`07` §2.6).

**Evidence discipline.** Tree claims cite a path; data claims are 2026-10-25 row counts or query
results; proposals say **proposed**. Nothing here implements or changes game law.

---

# Part I — What already exists

## 1. The designed layer (P26, P10, ADR055/057/160–165)

Program 26 was chartered 2026-07-27 (ADR160) after a three-agent audit found trade live **only on the
headless batch path** (`project/programs/26-international-trade.md` §1):

- **Landed.** spec-101 (ADR055) distributed Hickel's national Φ across eight engine nodes by
  bilateral-trade share into `boundary_flow_register` DRAIN_EDGE rows, gated on four `TickContext` keys
  that only `engine/headless_runner/runner.py` wrote.
- **Absent from play.** `game/session.py` seeded no external nodes, no Φ distribution (silent no-op), a
  zero-stub Leontief pipeline, zero TRIBUTE edges. ADR162 (U2) later fixed this on the Python path.
- **Never authored.** Programs 10 (σ-gradient) and 11 (Transport Substrate) were ratified as prose;
  `specs/107-*` and `specs/108-*` were never written.
- **Disclosed gaps.** `bilateral_trade_tons = 0.0`; `india`/`latin_america` receive Φ = 0; the
  trade-share crosswalk double-counts (the "#1 owner-review item"); sub-national runs absorb the **full
  national Φ_week** — measured at 84×–141× on a three-county run.
- **U6 (ADR164)** shipped the backend seam only: `TradeBlocView` in the projection union, pure
  `project_trade_bloc` / `project_trade_overview`, `kind="trade"` dispatch. No client rendered it.

ADR165 answered the whole ruling queue in one sitting: **Option C, σ-gradient composition** governs Φ
attribution (not trade share); core-bloc drain must be grounded in **Amin + Wallerstein + MIM internal
colonies**; Mexico folds into `latin_america`; a **disjoint partner taxonomy** replaces the Census
containing-bloc set that produced the 138.6% denominator; Ricci is re-ingested (a declared partial undo
of ADR076 R2); `_fetch_node_erdi`'s inert-1.0 defect is fixed inside U5. Two rulings matter most:
**blocs are a static label set at campaign start**, and **tariff rates, duties and taxes belong to the
trade system, adjusted through Policy/Electoral** — the first concrete P25↔P26 coupling.

## 2. The live Rust layer — much further along than the program doc says

The program doc is a **Python-era** document. The Rust path has since grown an international economy.

**The twelve markets are typed kernel identity.** `babylon_kernel::economic_location` defines
`ForeignCounterpart` as `#[repr(u8)]` 1–12 — Canada, Mexico, China, Russia, India, Japan, EU (pinned
EU27), Remaining Europe, Latin America/Caribbean, West Asia/North Africa, Sub-Saharan Africa, Remaining
Asia-Pacific — plus `UsDependency` 1–6 keyed by UN M49. `EconomicLocation` is a closed three-way union
with **six canonical bytes** and a strict `FromStr` over `county:`/`foreign:`/`dependency:`. Its doc
comment is a constitutional statement: *"Aggregated markets do not imply a shared government or
political alignment."*

**Each counterpart is a finite economy.** `content/scenarios/national/defines.toml` carries a
`[counterpart."…"]` block for all twelve, and the reader refuses any set whose length ≠ 12
(`policy/admission.rs::counterparts`):

| | wage µ/hour | price bps | vs US |
|---|---:|---:|---:|
| United States | 24,000,000 | 10,000 | 1.00 |
| Japan / EU | 22,000,000 | 10,000 / 9,500 | 0.92 |
| Canada | 20,000,000 | 10,000 | 0.83 |
| Remaining Europe | 14,000,000 | 7,000 | 0.58 |
| Russia | 11,000,000 | 5,500 | 0.46 |
| China | 10,000,000 | 4,500 | 0.42 |
| Remaining Asia-Pacific | 9,000,000 | 4,500 | 0.38 |
| West Asia / North Africa | 8,000,000 | 4,500 | 0.33 |
| Mexico / Latin America | 7,000,000 | 4,000 | 0.29 |
| India | 5,000,000 | 2,200 | 0.21 |
| Sub-Saharan Africa | 4,000,000 | 1,800 | 0.17 |

That table **is** Emmanuel's narrow-sense permissive condition, already authored, already integer,
already in the catalog hash. The design record is explicit that these are *"Designed gameplay
differences in the common accounting currency, not an exchange-rate model or a measured
purchasing-power conversion"* (`reports/national-economy-design-2026-09-20.md`).

**Each counterpart is opened as a full actor set.** `opening/external.rs` iterates
`ForeignCounterpart::ALL`, reads real population from `world_reference` (UN WPP 2024 with explicit
`IncludedInParent` / `TradeOnly` / `NotPublished` dispositions), creates a pooled household cohort,
then one site **per economic function** with employed and reserve staffing, price-scaled offers, and
deterministic identity from `sha256("NationalExternalSiteV1" ‖ location ‖ function)`. Its doc line is
the theory: *"Bounded world cohorts. Trade dollars create neither people nor capacity."*

**Freight is a real multimodal graph.** `national_transport_reference_2024` (SHA-256 pinned) supplies
node kinds `Airport/Border/Bulk/County/Dependency/Faf/Foreign/Liquid/Marine/Trunk`; four `CargoClass`es
(`General`, `DryBulk`, `CrudeOil`, `RefinedLiquid`); eight continental trunk counties (06037, 13121,
17031, 26163, 34013, 48113, 48201, 53033); seven marine gateways with capacities (houston 67, anchorage
77, kahului 71, tacoma 51, newark 33, los_angeles 29, honolulu 20).
`contracts/national_transport_policy_v1.json` assigns each counterpart its gateway set — Canada and
Mexico via **border** nodes, the rest via named ports. Service profiles give exact `capacity_grams`,
`cost_micros_per_tonne`, `loss_ppm`, `travel_periods`. The policy states the binding honest limit:
*"Twelve Designed markets are abstract endpoints, not observed foreign port facilities. FAF8 foreign
areas remain independent context; no 12-market tonnage inferred from dollar trade shares."*

**Cross-border ownership is live.** `opening/financial.rs` installs two reciprocal Designed claims — a
Wayne capital-goods plant owned from Japan, a Canadian capital-goods plant owned from Wayne — with
`cross_border_ownership_bps = 2000`. `OwnershipClaim` names issuer, beneficiary and shares;
distribution and remittance are separate receipts. This is Nkrumah's profit-remittance circuit with
actual counterparties, and the code refuses to conflate location with ownership.

**The verb vocabulary already covers blockade and capital strike.** `PracticeId` = Organize, Agitate,
MutualAid, Strike, **Blockade**, Occupation, **Damage**, **CapitalStrike**, Investigate.
`intent.rs::target_is_valid` gives the legal pairs: Blockade → Route / ShipmentClass / AccessPoint;
Damage → Facility / Stock; CapitalStrike → Investment / Credit / Procurement / ProductionCommitment;
Occupation → Facility / Territory / AccessPoint; **Investigate → Facility only**.

**Corridor capacity lives in state, not in the hashed catalog.**
`MaterialCircuitState.corridor_capacities: Vec<CorridorCapacity { corridor_id, period,
available_grams }>`. That single fact makes blockade a mechanism rather than a feature request: a
picket line is a dated reduction of an existing unsigned row — no new primitive, operator or curve.

**What the Rust does not have.** No Φ, ERDI, tariff, import duty, migration or border policy, and no
bilateral-share attribution. `babylon-material-circuit` (5,883 lines; `catalog.rs` read in full) has
**no international concept** — no external market, trade good, currency or origin. `imperial-rent.bsl`
ports Extraction and Tribute only; Wages, Subsidy and Decision are unlanded, and Phase 4 Subsidy is
Director-reserved under IX.5.

**The data is loaded and unused.** `world_reference` parses and validates
`economy/international_counterpart_reference_2024.csv.gz` — 252 reporting areas, per-area US imports
and exports, annual **and** twelve months, with provenance status — exposing only
`us_imports_annual_millions_raw()` / `us_exports_annual_millions_raw()`. **Nothing in the opening build
or the tick reads them.** Same for the checked-in `babylon_hickel_final.csv` and
`babylon_ricci_final.csv`. And `faf_bloc_trade_tons.csv.gz` — the U3 artifact — covers **six** of twelve
counterparts (canada, china, eu, latin_america, southeast_asia, sub_saharan_africa), 2018–2024, in the
**retired** taxonomy, consumed by no Rust code.

The gap in one line: *twelve finite economies, a multimodal freight graph, wage and price differentials,
cross-border ownership and a blockade verb — wired to each other, and unwired from any measurement of
what the wiring transfers.*

## 3. The 3NF warehouse (`/media/user/data/babylon-data`)

Verified read-only, 2026-10-25:

| Table / view | Rows | Grounds |
|---|---:|---|
| `fact_trade_monthly` | 44,808 | per-country US imports/exports, monthly |
| `fact_bilateral_trade_annual` | 540 | 2010–2024, 15 years |
| `dim_country` | 273 | 32 `core`, 37 `semi_periphery`, 193 `periphery`, 11 null |
| `dim_sctg_commodity` | 42 | SCTG codes with `category`, `strategic_value` |
| `fact_faf_commodity_flow` | 2,494,901 | FAF5 **2022 only**; 132 CFS areas, modes 1–8 |
| `fact_hickel_erdi_annual` | 58 | national Φ, 1960–2017 |
| `fact_ricci_unequal_exchange_gvc` | 51 | Ricci GVC transfers, 1995–2009 |
| `dim_cfs_area` | 132 | **domestic only** — FAF foreign zones 801–808 absent |

Raw sources match: `babylon_hickel_final.csv` (2010 drain 8,625.0 / erdi 7.6; 2017 drain 13,000.0 /
erdi 7.20; `Extensive` 1960–79, `Intensive` 1980–2017); `babylon_ricci_final.csv` (North America CORE
**INFLOW** 70.7 bn / 0.9% of GDP 1995 → 255.5 bn / 1.7% 2007; India **OUTFLOW** 73.2 / 20.9% → 189.3 /
17.0%; China 125.7 / 17.3% → 382.5 / **10.9%** — richer and still drained);
`freight/faf/FAF5.7.1_State_2018-2024.csv` (`trade_type` 1=domestic, 2=import, 3=export; foreign zones
801–808; 456,237 foreign rows); `bts_border/border_crossing_entry_data.csv` (275,901 port-level monthly
rows with coordinates); `bts_transborder/` (monthly zips 2019–2024); `imperial_rent/country.xlsx`
(USITC/Census country imports 1997–2024).

**Three traps.** (1) `view_unequal_exchange` is a *trade-deficit ratio* by world-system tier — it is not
unequal exchange and must never be read as one. (2) `view_imperial_rent` computes labour compensation
**minus sectoral output** — that is why the July ensemble recorded Φ negative in NAICS 211 and in 40 of
3,220 counties. (3) Hickel's `alpha` is undocumented and inconsistent with `1 − 1/erdi`; recompute or
omit.

## 4. What was left behind on `p27-python-freeze`

Recoverable but retired: `ImperialRentSystem` (the five-phase pool circuit), the BEA Leontief Φ
pipeline, the Φ tri-decomposition (`phi_unequal_exchange` / `phi_reproduction` / `phi_domestic`), and
all four `formulas/unequal_exchange.py` functions — including `exchange_ratio`, Emmanuel's double
factorial terms of trade — which every audit found **registered with zero callers**. Read them as
specification, never as an oracle: the port posture is ADR183 (structure, not byte equality), and the
July ensemble failed at year rollover after 294 seconds on two seeds. The freeze is a source of
*shapes*, and one caution: `_NODE_TO_BLOC`, the 84–141× inflation and the 138.6% denominator all live
there and must not be ported.

---

# Part II — The coupled model: conservation first, no magic constants

## 5. The one identity that governs everything

Φ is not a quantity to be estimated. It is a **transfer**, and a transfer has two sides:

```
Σ over all nodes of Δvalue = 0            (world closure)
Φ_core  =  −Σ Φ_periphery                 (rent appears twice, opposite signs)
no flow without a source; no rent without a payer
```

`14` §4.1 already names this as the fix for the negative-Φ counties. In Rust it is stronger *and*
cheaper than in Python, because both sides already exist as first-class actors — every counterpart has
a site, workforce, wage, price scale and budget, and every shipment is a `RoutedFreightLot` with an
owner. Conservation is therefore **checkable on the receipts**, not asserted on a scalar.

Three consequences, each killing a family of bad implementations:

1. **Hickel's Φ cannot be an input.** A national aggregate with no partner dimension cannot be both
   attributed and conserved; attributing it is exactly how 48.5% of the drain got booked to Western
   Europe and Canada (`u4` §2.4 L1). In Rust, Φ is a *residual of the trade and remittance book*, and
   Hickel becomes a **calibration target** — a falsifier, never an input. This is the move ADR035's own
   `orthogonality_caveat` admits Python could not make.
2. **The unit is the shipment.** A transfer exists only where a lot moved and a payment settled. That
   forces the model onto the freight graph instead of onto a shares table — which is why the Mao
   visibility rule and the conservation rule turn out to be one rule.
3. **Nothing needs a new primitive.** Every quantity below is an integer, a share of a conserved total,
   or a difference of two measured prices. No sigmoid, no second curve, no fitted multiplier.

## 6. The four couplings

### 6.1 Bilateral flows: one matrix, three grounded layers

`F[o→d, sctg, mode]` is **not** estimated. It is assembled from three disjoint, hash-pinned sources:

- **Overseas value and direction** — `international_counterpart_reference_2024` (252 areas, monthly and
  annual). Already loaded, validated, unused.
- **Land-border volume and port utilisation** — BTS border entries (275,901 rows, coordinates, monthly)
  for Canada and Mexico, whose gateway lists in the transport policy are deliberately empty because the
  *border node* is the gateway.
- **Mode and domestic leg** — FAF5 filtered to `trade_type ∈ {2,3}` and foreign zones 801–808,
  giving tonnage and value per gateway per mode per year.

The precedence rule is the one thing to rule, and it is small: FAF gives **tons and modes** but coarse
origin; Census gives **value and country** but no mode. So join `tons` from FAF by
`(foreign zone, mode, domestic CFS area)` and `value` from Census by `country`, with the
zone→counterpart map fixed in policy. **Refuse to reconcile by ratio.** The transport policy already
forbids inferring tonnage from dollar shares and it is right: a dollar of SCTG-33 crude and a dollar of
SCTG-34 manufactures are not the same grams, and the freight graph is denominated in grams.

### 6.2 Leontief requirements: what a shipment drags in behind it

The domestic Leontief inverse exists in the trove (`input-output/total-domestic-requirements/`, 107
industries), and the Rust production circuit already carries `input_coefficients` per `ProcessId`. The
coupling is **one function**: for a good entering at a gateway, its embodied domestic requirement is
the inverse's column for the receiving industry, scaled by delivered quantity. That is how a
cheap-import shock becomes *hours not worked in Ohio* without anyone authoring a multiplier.

Deliberately out of scope: a foreign Leontief inverse. No foreign I-O data exists in the reference DB
(`u4` §7 verified), and inventing one is the largest possible fabricated-specificity violation.
Foreign production structure enters as σ — a *coordinate*, not a matrix.

### 6.3 Price distortion and the wage differential

Two measured ratios, both already in the data, both integer-expressible:

- **`d_t`** — Hickel's ERDI series (2.40 → 8.38 over 1960–2017), national-only and to be used as such.
  Its local derivative `∂D/∂d = X/d²` is remarkably stable (~$284 bn per ERDI point in 1960, ~$291 bn
  in 2017): **the level of Φ is policy-determined; the sensitivity is structural** (`14` §2.2).
- **`w_periphery / w_core`** — already authored per counterpart, and the only quantity in the model a
  player can move by organizing.

Emmanuel's broad/narrow distinction (`07` §1) decides what the engine may claim. Broad-sense follows
from differing organic composition and occurs in *every* exchange. Narrow-sense follows from the wage
differential alone and requires **labour immobility** as its permissive condition. Model both; never
report them as one number — only narrow-sense responds to organisation, and only narrow-sense vanishes
if the border opens (Emmanuel p. 161: make Guinea a French *département* with free circulation of
capital *and people* and narrow-sense UE "would vanish" while broad-sense continues).

### 6.4 σ as the attribution coordinate (ruled: Option C)

σ composes organic composition, capital intensity and vertically-integrated labour content,
z-standardised, linearly weighted `(1/3, 1/3, 1/3)`, homed in `defines.yaml` so any re-weighting is a
declared coefficient change. **The circular-dependency hazard is real and must be handled, not
hidden:** σ's weights were delegated rather than ruled, spec-107's world-anchor item is open, the
σ-index artifact is ungenerated, and σ for the twelve counterparts cannot be *computed* because no
foreign capital-stock, employment or I-O series exists. Therefore:

- σ for **US counties** is computed from BEA fixed assets + QCEW + Leontief.
- σ for **counterparts** is **anchored**, not computed — the only defensible anchor today is Ricci's
  region type (`CORE`/`SEMI_PERIPHERY`/`PERIPHERY`) mapped through the membership policy, with the
  wage/price differential as the second observable. That is an *inference*: label it `Derived`, record
  its basis, revisit when foreign production data is ingested.
- σ **never enters the tick**. Init-time, hash-stamped artifact, or it does not ship. In-tick σ would
  put libm transcendentals inside `NominalWorldHash` and break Determinism III.7.

The useful σ is not the level but the **gap**: `σ_US − σ_i` is the up-gradient ordering, which makes
"value flows up-gradient" computable rather than a slogan. Keep spec-107 D6's non-enforcement of
`slope > 0` — if the alignment fails on real data the failure should be loud.

## 7. The per-period identity set

Check exactly these over the receipts. Anything not here is not conserved and not shippable.

| # | Identity | Falsifies |
|---|---|---|
| I1 | `Σ settled import value = Σ settled export value + Δ foreign claims` | a Φ from nowhere |
| I2 | `Σ grams dispatched = Σ grams arrived + Σ grams lost` per corridor | a blockade that only changes a number |
| I3 | `Σ DRAIN_EDGE = Σ counterpart outflow`, both signed | attribution that labels rather than transfers (`u4` L5) |
| I4 | `Σ domestic hours required by delivered imports` reconciles with the Leontief column sum | a shock with no domestic hours |
| I5 | `Σ share over 12 counterparts = 1` on a **disjoint** taxonomy | the 138.6% denominator (`u4` L2) |
| I6 | `wage bill paid = wage obligations incurred + Δ accrued unpaid` | a super-wage that is really unpaid wages |

I6 is the one that will bite. It is the MIM tell from `06` §11: *a paycheque that is a dividend behaves
differently from one that is a cost, and the difference shows in what the employer does when the worker
organizes.*

## 8. Runtime cost

Kilobytes, not clusters: twelve counterpart profiles (already in `defines.toml`), one `f × 12` flow
matrix per period, one σ per node, this period's corridor capacities, and the ownership claim rows. The
4.9 GB warehouse, the 30 GB `dot/` tree and the 2.5M-row FAF table never ship — `14` §5 applied to
trade, with PER-354's embedded SQLite (ADR287) as the home for the small derived tables.

---

# Part III — Player agency inside the belly of the beast

The organization is in Wayne County. It cannot make trade policy. It can make trade policy *cost
something*, and it can make the rent visible to the people who receive it. The class-stand test applies
to every option: does this weaken Φ, or redistribute it downward (`07` §3.7)? Those are different
goals, and the second is often available when the first is not — that gap is the game.

**Six surfaces.** porch-01 rules five: Topology, Electoral, Physical map, Ticker, Wiki. The sixth used
here is the **Archive** — the dossier/chronicle layer where `TradeBlocView` already projects (ADR164).
Trade facts live in the Archive and the Wiki and intrude into the other four as pressure. If the
Director means a different sixth, only placement changes; no mechanism does.

## 9. Physical map and Topology — choking the bottlenecks

When the US intervenes against a delinking Southern state, the intervention has a **shape on the
freight graph**, and the player can find it. This is the strongest position in the design because the
mechanism and the verb both already exist.

A blockade is: pick a `Route`, `ShipmentClass` or `AccessPoint`; the resolver reduces
`CorridorCapacity.available_grams` for the affected `(corridor_id, period)` rows for N periods. Every
consequence then follows from the existing allocator — buyers lose shipments by ordinary allocation
order, production plans lose inputs, prices move through the existing responsive policy, and the loss
appears as real unmet need. **No new primitive, system position or event type.** On the map, a corridor
goes healthy → degraded → cut, which is exactly spec-108 item 5's ruled indicator.

- **Specificity.** A port is not a metaphor. Tacoma and Los Angeles is a different act from Newark, and
  the ten counterpart gateway sets let the player reason about *whose* trade they stop.
- **Two-sidedness.** Blockading an outbound machine shipment to an attacked state is internationalist;
  blockading inbound consumer goods is a labour-aristocrat demand that raises local living costs. Both
  are legal under the same verb. The engine must not distinguish them morally — the *incidence* does.
- **Discoverability.** The player finds the bottleneck. A corridor whose utilisation rises while
  redundancy falls is a shape under fog, not a number.
- **The danger.** Blockading wage-goods raises Φ's *domestic* cost while lowering the periphery's drain.
  A real contradiction; let it fail. `07` §3.6 lists "militancy that keeps disappointing" as the correct
  Ticker experience.

One honest gap: `Investigate` targets `Facility` only, so a player cannot investigate a TNC's
`ProcurementCommitment` directly. Do **not** widen the table — that is an authority amendment. Route the
same play through the legal target: investigate the *plant* whose procurement is the thing and let the
dossier name the counterparty. The facility is the door.

## 10. Electoral — dividing protectionists from importers

The sharpest internal contradiction available to a US organization, and materially grounded rather than
rhetorical. The labour aristocracy's income depends on cheap imports *and* on the wage it defends; the
import-competing fraction of capital depends on tariffs; the TNC fraction depends on open supply chains.
Three different payers for the same policy.

The mechanism ADR165 already ruled: **tariff and duty coefficients are declared trade defines consumed
by the attribution dataflow, moved by LEGISLATE motions and electoral outcomes subject to the reform
ceiling.** So the player does not "set tariffs." The player does what a real organization does:

- **Builds a bloc spanning the fissure and watches it split.** `csdraft`'s shift from "end outsourcing" to
  "jobs that can't be outsourced" is a demand for *immovability* — for the rent to be defended by
  geography. A legible position with a legible cost.
- **Plays incidence.** Every demand carries a hidden `who_pays` set (`06` P3). Payers all core ⇒
  `appendage_risk`; naming the periphery ⇒ not. The player sees who screams, never the set.
- **Uses the vote for space, not for rent.** `06` §11: the vote buys a venue, a legal meeting, a press;
  it cannot reach Φ. County presidential returns (3,155–3,156 counties, 2000–2024) make the
  demonstration empirical, not asserted.

The trap that must exist: a tariff on wage-goods is popular, raises the domestic cost of reproduction,
and **does not touch Φ's source**. A player who wins that fight and stops has built economism with a
flag on it (`07` §3.6).

## 11. Ticker — the cheap-import shock and super-wage erosion

`07` §2.2 names the felt form: *the raise that arrives the same month the imports get cheaper, and the
plant that closes anyway.* Two visible events, no explanation — that is the whole design.

What the engine must genuinely produce, not narrate:

- **Cheaper imports** — the counterpart `price_scale_bps` differential clearing through the settlement
  book, so real purchasing power rises.
- **A plant closure** — the Leontief requirement: hours embodied in displaced output stop being
  demanded, so the funded-employment commitment shrinks next period.
- **A wage that keeps beating the cost of living** — from I6: the wage bill paid exceeds what the
  employer's own realization covers, and the gap arrives as trade and remittance receipts.
- **Militancy that keeps disappointing** — because the employer's answer to organization is constrained
  by whether the paycheque is a cost or a dividend, visible only in what the employer *does*.

No Φ number, no "super-wage index." Prices, payrolls, hours, closures, arriving goods. The player infers
the rent. Hard requirement: `W_c − V_c` renders as **the gap, never a formula** (`06` §11). The
American numbers are a derivative; the independent variable is `periphery_wage / core_wage`, reaching
the player only as Intel fragments, Archive dossiers on Southern workplaces, and the *absence* of cheap
goods on a shelf. A player watching only American indicators will be surprised by their own endgame —
correct, because the same is true of every organization in this corpus (`06` §9).

## 12. Archive and Wiki — the dossiers, and the one legal formula

ADR164's `TradeBlocView` is the right contract and its discipline is right: `phi_year_inflow`,
`bilateral_trade_value`, `bilateral_trade_tons`, `erdi_ratio`, `exposure_top` project honest `None`
rather than fabricated zero. In Rust these become per-counterpart dossier pages: what arrives at which
gateway, on what mode, from whose workplaces, at what price, and what the state's own documents say.

The Wiki is where the enemy's arithmetic appears — and only there. A leaked TNC sourcing manual showing
a landed-cost comparison. An IMF letter of intent with a wage-ceiling condition. A World Bank country
strategy. That is `02`'s doctrine-as-leaked-SOP pattern and `07` §2.6's single exception: the formula
is the artifact, the footnote is the argument.

The Wiki also carries the comparison no tooltip may make: Ricci's own intensities — the core absorbs
1–2% of its GDP while the periphery surrenders 11–31%. A cited dossier may say "this is a net-exploiting
country." No tooltip ever does (`06` §11).

## 13. The late game the player is actually playing toward

Two exits, both reachable from inside the US (`07` §6):

- **Delinking works.** A Southern state that prioritises its internal market confiscates the visible
  rent. The US organization loses the cheap goods, the local plant that depended on the export order,
  and the political cover at once. Amin's advance-post claim becomes material fact.
- **Φ's political energy runs out.** Φ has **no natural decay** (`07` ruling 8). It is maintained by
  borders, repression and a service stratum. Stop paying and it falls — and the fall is the late game.

What must not happen: an ending where the core proletariat leads. The Fundamental Theorem is a
*material* statement. The party is defined by whose interests it serves in practice, and the test is
what it does when the two conflict (`07` §3.1).

---

# Part IV — The build plan

Sequenced to start **after PER-354 lands** (embedded SQLite campaign owner, ADR287). Each step names
its existing asset, its consumer, and what would prove it failed. No step requires a new primitive; two
require a Director ruling and are marked.

**Step 0 — Truth pass (½ day).** Re-verify post-PER-354: (a) `corridor_capacities` still carries
per-period grams; (b) `Blockade × Route|ShipmentClass|AccessPoint` is still legal; (c) `world_reference`
still parses trade with no consumer; (d) `faf_bloc_trade_tons` is still six-of-twelve and unconsumed.
If any is false the plan shifts — do not proceed on this document's authority.

**Step 1 — One artifact, twelve counterparts, one schema.** Replace `faf_bloc_trade_tons.csv.gz` with a
single hash-stamped artifact (ADR121 LODES pattern, `tools/`-generated, never hand-edited) keyed on the
**live** twelve-counterpart taxonomy, carrying per `(counterpart, year)`: imports/exports **value** in
USD millions (Census); imports/exports **tons and ton-miles by mode** (FAF5 `trade_type 2/3`, zones
801–808); SCTG composition against the 42 codes in `dim_sctg_commodity`; the gateway set actually used,
joined to `national_transport_policy_v1.json`; and a source+status column per field so
`IncludedInParent` / `TradeOnly` / `NotPublished` survive.
*Refusal:* no per-counterpart tonnage derived from dollar shares. Partners with no FAF zone read
`unknown`, not zero and not a ratio.
*Falsifier:* the twelve import values must reconcile with the published US goods-import total within a
declared tolerance, and shares must sum to 1.0 over a **disjoint** partition. That one check kills `u4`
L2 permanently. **Ruling needed:** the FAF-zone→counterpart map and the disjointness rule.

**Step 2 — Consume it in the opening build.** In `babylon-persistence`, after
`opening::external::world` creates the twelve actor sets, hydrate a per-counterpart trade opening row
(`bilateral_value_in/out`, `bilateral_tons`, `mode_mix`, `sctg_mix`, `gateway_set`) onto the identity and
thread it into campaign state. `world_reference` already exposes the values; this is the first consumer.
*Falsifier:* the twelve `imports` sum to the national total, and removing the artifact fails admission
loudly rather than silently zeroing (III.11).

**Step 3 — Dated corridor capacity as a mechanism.** `CorridorCapacity` is already in state; add **no
new type**. What is missing is a resolver that, given an admitted `Blockade` intent (or a state
interdiction), writes reduced `available_grams` for the affected corridor and periods, plus restoration
on expiry.
*Falsifier:* hold everything else fixed and remove the blockade — delivered grams, unmet need and
domestic hours demanded must all differ, reconciling with I2. A blockade that changes only a displayed
number has failed.
*Note:* this mutates state inside a hashed campaign, so it belongs under `NominalWorldHash` discipline
and a receipt. It is not a new mathematical primitive — it is a dated unsigned row that already exists —
but it changes what "the catalog is immutable" means in practice. Confirm with the Director.

**Step 4 — The Φ residual, with two sides.** Compute Φ as a **residual over receipts**: the trade side
(value settled across the boundary net of captured terms, I1/I3); the remittance side (distributions on
`OwnershipClaim`s whose beneficiary is foreign, and foreign claims' distributions to domestic
beneficiaries — Nkrumah's circuit, already live in `opening/financial.rs`); the domestic side (wage bill
paid against the value the paid hours produced in the same period). Compare the aggregate against
`babylon_hickel_final.csv` as a **calibration target**, using only `erdi` and
`annual_drain_usd_billions`, never `alpha`.
*Falsifier:* Φ must be zero-sum against the counterparty side (I1/I3) and must never be negative at a
node without a payer. That single test is the fix for the July ensemble's 40 negative counties.
**Ruling needed:** whether Φ's domestic side is the BSL `economics/fundamental-theorem` rule's
`wages − value-produced` (already landed, the only rule in that namespace) or a receipt-level residual.
They must not both be authoritative. Recommend: the residual measures, the rule judges.

**Step 5 — σ artifact, anchored, init-time only.** US counties from BEA fixed assets + QCEW + Leontief;
the twelve counterparts **anchored** from Ricci tier plus the authored wage/price differential, labelled
`Derived` with the anchor basis per row.
*Falsifier:* D6's `slope > 0` must be *reported*. If higher σ does not align with higher wages on the
real data, say so in the artifact and do not tune the weights. **Do not** compute σ in-tick.

**Step 6 — Attribution, disjointly.** σ-gap composition, renormalised to 1.0 over the disjoint
partition, computed **once at init**, sorted iteration, integer shares. I5 is the gate.
*Falsifier:* any partner receiving a share with no trade relation; any share over an overlapping set;
any residual above tolerance.

**Step 7 — Leontief incidence.** For delivered imports, compute the domestic requirement column and
record it as a receipt. This makes a closure *cause* another county's short-time rather than merely
coincide with it.
*Falsifier:* the counterfactual already written into
`reports/national-economy-design-2026-09-20.md` — sever the gateway, hold everything else, and the
incidence receipt must move.

**Step 8 — The two client surfaces.** Archive first (the `TradeBlocView` contract exists and projects
honest `None`), then the Physical-map corridor health indicator ADR165 item 5 ruled. Both read the
projection seam; no client computes anything.
*Falsifier (play, not tests):* a player who has never read this document can, from dossiers and map,
explain *whose* trade moves through the corridor they are blockading — and can be wrong in an
interesting way.

**Step 9 — Retire what is finished.** `faf_bloc_trade_tons.csv.gz`, the `_NODE_TO_BLOC` crosswalk, the
`view_unequal_exchange` mislabel, and the dormant Python UE functions as *code* (keep them as
specification on `p27-python-freeze`). The Python reference build keeps producing the warehouse; it
stops being a consumer of game state, which PER-354 already requires.

---

# Part V — Director Rulings Added on the Porch (2026-10-25) & Open Questions

## Rulings locked during Porch Session 02

1. **Trade Blocs + Four Standalone Geopolitical Actors (No 200-Country Simulation):**
   The player is never playing as Canada, China, or Botswana (though a peripheral-insurgency expansion pack like *"Babylon: Delinking"* is noted as a fun far-future DLC idea, strictly out of v1 scope). Outside U.S. borders, the world is abstracted into **regional Trade Blocs** plus **four explicit standalone geopolitical actors** whose contradictions directly shake the U.S. circuit: **China**, **Russia**, **Iran**, and **Israel**.
2. **Israel as America's Rowdy Settler-Colonial Franchise (Never the Reverse):**
   The causal and material arrow runs strictly from **U.S. imperialism ("daddy USA") $\rightarrow$ Israel (its Jewish colonial franchise / forward military garrison)**, never the reverse (*Israel does not control America*). Because a settler-colonial franchise has its own internal expansionist contradictions, it acts as America's rowdy settler child—periodically defying Washington's tactical restraint, starting regional escalations, and forcing the U.S. metropole to pour weapons, budget, diplomatic cover, and domestic repression into bailing out its garrison. For the domestic player, that makes the U.S.$\rightarrow$Israel supply chain (Midwest arms plants, port/rail corridors, university endowments, congressional appropriations) a primary site where internationalist blockade, division tactics, and political exposures meet.
3. **The Sixth Screen is Line / Doctrine:**
   Approved in `2026-10-25-porch-02.md`: the six canonical player screens are **Topology, Electoral, Physical Map, Ticker, Wiki, and Line / Doctrine**. Trade dossiers live in the **Wiki** (Archive) and surface as material pressures across Ticker, Physical Map, Topology, and Electoral.

## Remaining technical questions for post-PER-354 implementation

1. **FAF-zone → counterpart map, and the disjointness rule** (extending the `ForeignCounterpart` enum to ensure Iran and Israel are distinct from the general West Asia / North Africa bloc where geopolitical/military corridors require it). World-system geography, IX.5.
2. **Φ's domestic side:** BSL verdict rule vs receipt residual — may both be authoritative? (Recommend
   no.)
3. **Blockade on hashed corridor capacity:** confirm dated capacity reduction in state is within current
   provenance, or rule the alternative.
4. **σ for counterparts** staying `Derived`-anchored from Ricci tiers + the wage differential until
   foreign production data is ingested. `u4` §7's blocking item; it does not go away.
5. **Ricci re-ingestion** (ADR165 D2/D3) — still the basis for the world-scale anchor, still a partial
   undo of ADR076 R2, still needs the pinned rebuild ceremony.
6. **`Investigate` targeting.** Confirm facility-as-door, or rule an authority amendment. Do not widen
   it silently.
7. **The sixth surface.** If Archive is not it, where do trade dossiers live?

---

# Part VI — What not to build

- **No new mathematical primitive.** The dialectic is primitive; a shipment, a wage bill, an ownership
  claim and a corridor capacity are already first-class. Φ is a residual, not an operator.
- **No foreign Leontief inverse.** No data exists; inventing one is the exact failure the Aleksandrov
  test forbids.
- **No ERDI as a live readout.** National-only series, used at init.
- **No `alpha` column.** Undocumented and inconsistent with `1 − 1/erdi`.
- **No second income flow for theoretical unequal exchange** (`docs/concepts/economics-pipeline-theory.rst`).
  Cope's double-counting warning: reports cannot add an estimated UE transfer on top of the payments
  that already carry it.
- **No world map.** ADR057 settled it: blocs appear as lines and bars inside CONUS-primary screens.
- **No "solidarity" or "extraction" scalar.** One scalar destroys two mechanisms that fail differently
  (`07` ruling 2).
- **No convergence story.** China's Ricci row — absolute transfer rising 3×, share of own GDP falling by
  a third — is the interesting state and it is measured. A node can get richer and stay drained.
- **No Trotsky.** Any design that lets the player assemble "workers of the world" out of the US working
  class has already left the line.

---

# Part VII — Evidence ledger

| Claim | Source |
|---|---|
| Twelve counterparts, six dependencies, six-byte locations | `rust/crates/babylon-kernel/src/economic_location.rs` |
| Per-counterpart wages, price scales, function weights; 12 exactly | `content/scenarios/national/defines.toml`; `national_economy/policy/admission.rs` |
| Counterparts opened as finite actor sets from real population | `national_economy/opening/external.rs`; `world_reference/parse.rs` |
| Gateways, trunks, marine pools, profiles, "no tonnage from dollar shares" | `contracts/national_transport_policy_v1.json` |
| Transport reference SHA-256, node kinds, cargo classes | `national_transport/artifact.rs`; `model.rs` |
| Trade CSV parsed and unconsumed; 252 areas, monthly + annual | `world_reference/model.rs` |
| Cross-border ownership live; `cross_border_ownership_bps = 2000` | `national_economy/opening/financial.rs` |
| Blockade / Damage / CapitalStrike target sets; Investigate = Facility only | `babylon-practice-contract/src/intent.rs::target_is_valid` |
| Corridor capacity in state, per period, in grams | `rust/crates/babylon-material-circuit/src/model.rs:301` |
| Material circuit has no international concept | `babylon-material-circuit/src/catalog.rs` (read in full) |
| No ERDI / tariff / migration in the Rust engine | targeted `rg` over `rust/crates/` → no engine hits |
| `faf_bloc_trade_tons.csv.gz` = 6 counterparts × 2018–2024, unconsumed | `src/babylon/data/reference/faf_bloc_trade_tons.csv.gz` |
| P26 audit, non-overlap covenant, U0–U6 | `project/programs/26-international-trade.md` |
| Option C, Mexico→latin_america, disjoint taxonomy, tariff via Policy/Electoral | `ai/decisions/ADR165_p26_director_rulings_trade_slate.yaml` |
| 48.5% core drain, 138.6% denominator, L1–L5, σ circularity | `specs/101-trade-activation/u4-phi-attribution-options.md` |
| ADR055 baseline and its five disclosed gaps | `ai/decisions/ADR055_spec101_trade_activation.yaml` |
| Leontief Φ pipeline, three-layer axiom, orthogonality caveat | `ai/decisions/ADR035_leontief_imperial_rent_pipeline.yaml` |
| Interaction parity and Tribute seeding; Archive trade seam | `ADR162_…yaml`; `ADR164_…yaml` |
| Hickel/Ricci values and traps; conservation-first method; zero-Spark runtime | `docs/gameplay/research/14-babylon-data-treasure-trove.md` |
| Emmanuel narrow/broad sense, Marini, Amin, Nkrumah, MIM line, screens, visibility | `docs/gameplay/research/07-…md`; `06-…md`; `docs/gameplay/2026-10-25-porch-01.md` |
| σ composition, world anchor, dormancy of the four UE formulas | `project/programs/10-spectrum-of-unequal-exchange.md` |
| Twelve compressed external markets; no second UE income flow | `docs/concepts/economics-pipeline-theory.rst` |
| Row counts, views, three named traps | read-only `sqlite3` against `marxist-data-3NF.sqlite`, 2026-10-25 |
| National-scale and retained-growth evidence | `reports/national-economy-design-2026-09-20.md`; `reports/recurring-economy-kernel-2026-09-20.md` |
