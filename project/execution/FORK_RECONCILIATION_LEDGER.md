# Fork Reconciliation Ledger — Part 2 of the `src/` simplification sweep

Companion to **ADR058** (`ai-docs/decisions/ADR058_src_simplification_sweep.yaml`) and the sweep plan.
Part 1 (Phases A–D) landed the decision-free wins on local `dev` (@ `ea403107`). Every candidate
that required **a judgment about which of two implementations is "more correct"** was deferred *by
rule* to this ledger. Here each "successor fork" — a richer implementation built while the swap into
the live path never happened — gets one entry: a rigor + data-accuracy analysis and a single firm
recommendation.

**The ledger proposes; the owner disposes.** Nothing in `src/` changed to author this. Each entry
carries a `— Percy's ruling:` slot; once ruled, a separate **Part-2b** phase implements the rulings,
each behind `mise run check` + byte-identical `mise run qa:regression` (or a documented rebaseline
where a "wire-orphan" ruling legitimately moves a number).

**Method.** 15 fork analysts (one per fork, high-effort, each handed this session's verified wiring
facts + the constitutional yardstick) each read the *actual* competing implementations and returned
a structured entry; each recommendation was then **adversarially verified** by an independent skeptic
prompted to refute it (real citations? determinism preserved? fixture smuggled in as runtime?).
30 agents, 0 errors. **14/15 CONFIRMED; 1 CHALLENGED** (Fork 4 — its dissent is recorded in full).
The analysts overturned several of the plan's own premises — flagged inline as **[correction]**.

**Governing rule (Percy's):** *keep the most ideologically / mathematically rigorous, data-accurate
implementation — even if that means WIRING the orphan and RETIRING the live path.* Rigor is judged
against the Constitution (`.specify/memory/constitution.md` v2.7.0), not invented standards. The
recurring levers: **III.8 Aleksandrov** (a construct must trace to a named material relation — the
P0 tie-breaker), **III.10 Earn-Its-Keep** (ships only if it yields a LAW / PREDICTION / running
COMPUTATION — kills built-but-inert code), **II.2** (Φ, c/v/s, r are *derived*; never stored),
**III.4.2** (a validation fixture is NEVER a runtime dependency), **III.1** (no magic constants),
**III.7** (every tick's deterministic hash; a "wire" that moves it is a deliberate rebaseline).

## Disposition counts

| Disposition | Count | Forks | Meaning |
| --- | --- | --- | --- |
| `delete-orphan` | 5 | 2, 7, 9, 10, 12 | Remove the unwired path; live path is equal-or-superior in rigor. All byte-identical. |
| `wire-orphan/retire-live` | 4 | 1, 3, 4\*, 6 | Orphan is more rigorous/data-accurate; wire it, retire the live simplification. Moves baseline. |
| `reconcile` | 4 | 5, 8, 13, 14 | Both name real (often different) relations; add an invariant / convention, don't delete. |
| `unify` | 2 | 11, 15 | Parallel impls of one thing; keep the canonical, delete/route the rest. |
| **Total** | **15** | | Plus 2 correction notes (below). |

\* Fork 4 is the one **CHALLENGED** entry — the skeptic materially revised it (below). Of the 15,
**only 4 recommendations move the regression baseline** (Forks 1, 3, 6, and — per the dissent —
the `compute_action_cost` half of 4). The other 11 are byte-identical deletions/unifies/doc-notes.

**Routing for the owner.** Two tiers:

- **Clean, byte-identical calls Percy can rubber-stamp** (deletions/unifies of inert code, no number
  moves): Forks **2, 7, 9, 10, 11, 12** (bundle 10+11 — the observers are TraceRecorder's only
  callers). Rigor-safe by the analysis; adversarially confirmed.
- **Genuine rigor rulings** (baseline-moving, or a value/theory judgment reserved to the BD):
  Forks **1** (wire spec-057 + the double-counting question + the Hickel fixture ruling), **3**
  (the turnout units/value ruling), **4** (contested — read the dissent), **5** (freeze-and-schedule
  a spec-040 migration), **6** (gamma data program), **8** (is the internal-colony differential a
  4th Φ channel? — an I.2 amendment question), **13**, **14**, **15**.

---

## Fork 1 — Full Leontief imperial-rent stack (spec-057) vs `county_exposure` spatial key

**Disposition: `wire-orphan/retire-live`** · confidence medium · moves baseline: **yes** · verify: CONFIRMED

**[correction]** `county_exposure` is **not** a rival Φ computation and **not** a "magic multiplier":
`county_exposure.py:150-152` returns a *normalized spatial-distribution key* (Σw = 1). The Φ magnitude
it splits arrives from the trade system (`external_nodes_phi`, `runner.py:1085`) via the live
`DRAIN_EDGE` path (spec-100/101/063). So the Leontief stack and `county_exposure` are **complementary,
not substitutes** — retiring `county_exposure` is *not* on the table. The true "simplified live path"
being retired is the `_stub_zero_pass_through` no-op that fires every tick because the 5 spec-057
services are never instantiated (`imperial_rent.py:86,158`; `services.py:216-221`). `phi_hour` is read
at `derived_rates.py:108` (→ Φ_aggregate) and fed a constant 0 today.

| Aspect | Live (stub) | Orphan (Leontief) | Rigor verdict |
| --- | --- | --- | --- |
| Φ magnitude provenance | `external_nodes_phi` — a DB-queried scalar derived outside this fork | `M = A_m·L_d · (w_ratio−1) · final_demand`, recomputed from primitives | Orphan wins **II.2 / II.12** — recompute from primitives, operator algebra is source of truth |
| Aleksandrov III.8 | exposure weight = a spatial key; names no value-transfer process | each operator names a material relation (import-content, core/periphery wage gap, realized rent) | Orphan wins III.8 for the *magnitude* |
| III.10 Earn-Its-Keep | runs every tick | 3788 LOC that **never runs** (gate → stub-zero) | Live wins III.10 **today** — orphan is exactly the built-but-inert code III.10 kills |
| III.4.2 data | reads a refreshable spec-100 table | BEA I-O + QCEW blessed runtime, **but** reads `fact_hickel_erdi_annual` (a **FIXTURE**) per-tick | Split — orphan's BEA/QCEW legs are superior; its Hickel leg trips III.4.2 |

**Rigor:** The Leontief stack is the more rigorous *magnitude* model (III.8/II.2/II.12), and spec-057
is officially "Implemented (2026-05-09)" with the express mandate to replace the stub — so the
constitutionally correct cure for the III.10 violation is to **activate** the grounded model, not
delete it. **But wiring must ship with a conservation invariant** relating Σ(`phi_hour`·hours) to the
trade `DRAIN_EDGE` total, or the two paths **double-count Φ** (a II.2 double-derivation).

**Strongest counter-case:** the project may have moved *past* spec-057 — the trade DRAIN path
(spec-101/063, Jul 2026) is newer and may now be the canonical Φ source. If so, wiring the orphan
double-counts and **delete-orphan** (or reconcile-with-invariant-only) is correct. Wiring also turns
the **Hickel fixture into a per-tick runtime dependency** (III.4.2) — needs an owner ruling or a
catalog reclassification (per the verifier, arguably an **IX.3 amendment**, since it relaxes a
prohibition).

**Recommendation:** Instantiate the 4 `Default*` sources + `bea_industries` at scenario-load so
`_compute_imperial_rent` computes real per-county `phi_hour`; retire the stub. Ship *with* the
DRAIN-reconciliation invariant. **Rule first:** (a) is the Leontief path or the trade DRAIN path the
canonical Φ magnitude? (b) may the Hickel fixture be read at runtime? · Cost **L** · moves baseline.

**Cites:** `imperial_rent.py:86,158` · `services.py:216-221,264-352` · `production_chain_rent.py:176-189`
· `county_exposure.py:150-152` · `economic.py:104-160` · `derived_rates.py:108` ·
`leontief_rent/periphery_labor_coefficients.py:103` (reads Hickel fixture) · `specs/057-*/spec.md` ·
Constitution III.8 / III.10 / II.2 / II.12 / III.4.2

**Adversarial verdict:** CONFIRMED. Cites real and on-point (no II.11 misfire); the fixture-as-runtime
smuggling is genuine and the verifier upgrades it toward **IX.3 escalate-amendment**.

> **— Percy's ruling:** _(pending)_

---

## Fork 2 — `InterpolatingBEASource` vs `DefaultBEAShareLookupService`

**Disposition: `delete-orphan`** · confidence high · moves baseline: no · verify: CONFIRMED

**[correction]** The two are **not** drop-in substitutes: the orphan computes Marxian tensor *ratios*
(s/v, c/v) for `MarxianHydrator`; the live service computes *intermediate-input shares* (ii/go, va/go)
for `hydrate_hex_state`. So "wire-orphan/unify" is structurally impossible — the live consumer needs
shares the orphan never produces. **Two hard disqualifiers for ever wiring the orphan:** (1) it
performs **DDL** (`DROP/CREATE/INSERT` on `_cache_national_wages_bea`, `adapters.py:544-670`) against
the **read-only** reference DB — a substrate-immutability violation; (2) **II.11** correctly applies —
the live service *lives in* the owning subsystem `reference/bea/` and *is* the declared cross-subsystem
interface, whereas the orphan does foreign raw SQL from `economics/`. (Raw-SQL per se is *not* the
discriminator — both use it; subsystem **location** is.)

| Aspect | Live | Orphan | Rigor verdict |
| --- | --- | --- | --- |
| III.10 Earn-Its-Keep | wired at `postgres_initialization.py:851` | 474 LOC, callers = tests + 1 demo only | Live wins decisively — orphan is vocabulary |
| II.11 subsystem ownership | *is* the `reference/bea/` interface | foreign raw SQL on BEA tables from `economics/` | Live wins — wiring the orphan is a federation defect |
| Substrate immutability | read-only SELECTs | DROP/CREATE/INSERT on the read-only reference DB | Live wins — disqualifying |
| Missing-year accuracy | forward-fill + `0.5` magic default (III.1 blemish) | **linear interpolation** — genuinely more accurate | **Orphan wins this one aspect** — worth salvaging |

**Recommendation:** Delete `InterpolatingBEASource` + its 2 exports + its dead tests/demo. **Salvage
first:** port the ~60-line linear-interpolation algorithm (`adapters.py:333-335`) into the live
`DefaultBEAShareLookupService` as an optional mode, and give `GLOBAL_FALLBACK_SHARE=0.5` a
GameDefines source to close the III.1 gap — that salvage is a *separate*, baseline-moving change with
its own ruling. The deletion itself is inert and byte-identical. · Cost **S** (deletion).

**Cites:** `adapters.py:207,333-335,544-670` · `reference/bea/share_lookup_service.py:70,79,1-11` ·
`postgres_initialization.py:851` · Constitution II.11 / III.10 / III.4.2 (a tie — both read blessed runtime)

**Adversarial verdict:** CONFIRMED. II.11 applied correctly this time (location, not raw-SQL). One
loose label: substrate-immutability is Amendment G / I.20, not "II.6" — a secondary lever, non-load-bearing.

> **— Percy's ruling:** _(pending)_

---

## Fork 3 — `MobilizeDefines` / `AidDefines` vs hardcoded drifted resolver constants

**Disposition: `wire-orphan/retire-live`** · confidence high · moves baseline: **yes** (see note) · verify: CONFIRMED

**[correction]** `AidDefines` is **not** composed into GameDefines *at all* — it is a sibling
`BaseModel` in `survival.py:250`; `SurvivalDefines` (composed) has no `aid` field. (This overturns a
prior memory note.) `MobilizeDefines` *is* composed (`_assembler.py:126,265`) but the resolver ignores
it (`mobilize.py:95` `# no MobilizeDefines yet`, drives turnout off `_TURNOUT_PER_SL = 10.0`).
**[correction]** a *fourth* silent drift beyond the three cited: `solidarity_amplification_per_edge`
= 0.05 (define) vs 0.1 (resolver).

| Aspect | Live (hardcoded) | Orphan (defines) | Rigor verdict |
| --- | --- | --- | --- |
| III.1 No Magic Constants | 7 module floats in `mobilize.py` + 1 in `aid.py`, none tracing to a define | defines.yaml is the canonical config surface | Defines win categorically — the live path is a standing III.1 violation |
| `aid_efficiency` value | `1.0` (frictionless) | `0.85` ("logistics overhead") | **Orphan wins III.8** — 0.85 names a material process; 1.0 names none |
| `turnout_per_sl` value+units | `10.0` = demonstrators / solidarity-link (self-contained) | `0.01` = fraction *of population* (needs a population input) | **Genuine units/semantics mismatch** — neither is drop-in; a BD ruling |

**Rigor:** III.1 forces the constants into defines *regardless of which value wins*. III.8 settles
`aid_efficiency` at **0.85**. The turnout question is a real design ruling (0.01 pop-fraction vs 10.0
demonstrators/SL are different formulas with different inputs) — **not** an IX.3 amendment (no new
primitive), but reserved to Percy. **The value ruling must land BEFORE the wire** — wiring at the
define's 0.01 default is a silent ~1000× turnout collapse dressed as "de-hardcoding."

**Recommendation:** (mechanical) compose `AidDefines` into GameDefines; route both resolvers to
`services.defines`, deleting the floats; reconcile the 0.05-vs-0.1 drift. (ruling) pick the turnout
model+units and confirm `aid_efficiency` 0.85. · Cost **S–M**. **Baseline note:** the verifier flags
the `qa:regression` gate specifically may stay *green* — MOBILIZE/AID are player verbs that don't fire
in the 5 autonomous scenarios — so "moves baseline" bites a live playthrough, not necessarily the gate.

**Cites:** `mobilize.py:31,33,95,120` · `aid.py:30,57-58,89,101` · `organizations.py:491,507-512` ·
`survival.py:250,253` · `_assembler.py:126,265` (no aid ref) · Constitution III.1 / III.8 / III.10

**Adversarial verdict:** CONFIRMED. All cites real; IX escalation correctly ruled out; the
land-the-value-ruling-before-wiring hazard is the load-bearing point.

> **— Percy's ruling:** _(pending)_

---

## Fork 4 — Feature-032 action-cost / constraint machinery (spec-032 FR-040)

**Disposition: `wire-orphan/retire-live` — CONTESTED (revised by the skeptic)** · confidence medium ·
moves baseline: **partly** · verify: **CHALLENGED**

**[correction]** the "not enforced until Epoch 3" clause is **narrow** — spec.md defers *only* the
resource costs (cadre/sympathizer/budget). **FR-040 `coordination_range` and the autonomy modifier are
present-tense MUSTs** ("Specify behavior now"). `compute_action_cost` is III.8-grounded (its
`_CONTRADICTION_PAIRS` name settler/patriarchal material relations). `enforce_action_points` duplicates
an inline AP loop already live in `npc_stub.py:84-108`.

**The challenge (recorded in full, because it revises the disposition):** the analyst led with
`enforce_coordination_range` as the "outright winner," but the live NPC generator is **single-target**
(`ooda.py:250` picks `territory_ids[0]`), so distinct-territories-per-org is always 1 — a
`coordination_range` guard **structurally can never fire** and earns nothing under III.10, and is
**hash-preserving**, not baseline-moving. So `moves_regression_baseline=true` is wrong *for the two
guards the recommendation leads with.* The FR-005 citation is also wrong (autonomy is **FR-041**).

**Revised recommendation (skeptic):**

1. The genuinely III.10-earning + III.8-grounded + hash-moving piece is **`compute_action_cost`** —
   wire it as the AP-cost source (replacing bare `defines.get_base_cost`), rebaseline all 5 scenarios
   with owner sign-off. *This, and only this, is what makes the baseline move.*
2. Fold `npc_stub.py`'s inline AP loop into `enforce_action_points` as a **DRY unify** — verify
   byte-identical, don't assume.
3. Treat `enforce_coordination_range` + `apply_autonomy_modifier` as **BLOCKED on a multi-territory
   action generator** — the real FR-040/FR-041 gap is upstream in single-target generation, not the
   missing guard. Wire the guards *with* a multi-target generator (larger scope), or hold them with
   the OODA-workstream pickup. Do **not** claim the guard-only wiring satisfies FR-040.

**Rigor (both agree on direction):** III.10 forbids parking built-but-inert code forever, and the
no-MVP rule forbids deleting spec-blessed work — so *wire (soon), don't delete, don't park.* The
disagreement is *what* earns wiring now. · Cost **M**; 31 unit tests pre-pay the red phase.

**Cites:** `ooda/constraints.py:18,54,92` · `ooda/action_costs.py:26-32,35` · `ooda/npc_stub.py:84-108`
· `ooda.py:250` (single-target) · `types.py:75` (`coordination_range=1`) · `specs/032-*/spec.md:5`
(Draft),`:178` (FR-040),`:12` · Constitution III.10 / III.8 / III.7

**Adversarial verdict:** **CHALLENGED** — central FR-040 rigor claim and the determinism claim are both
materially wrong (guard is a structural no-op); coarse direction defensible. **Percy: rule on the
revised three-part split, not the original.**

> **— Percy's ruling:** _(pending)_

---

## Fork 5 — `institution/` package (spec-040) + deprecated `is_institution` bool vs `Institution` entity

**Disposition: `reconcile`** · confidence medium · moves baseline: no · verify: CONFIRMED

**[correction]** the migration is **inverted** from the usual pattern: the *deprecated* bool is the
one **in-tick** (`is_institution` gates ASSIMILATE eligibility at `action_eligibility.py:168`, inside
OODASystem @14), while the *newer* `Institution` entity + `institution/` package (311 LOC, 11 test
files) are the **inert** side (zero tick reach). The entity is more wired than "graph-orphan" implies —
`WorldState` reconstructs it (`from_graph`) — but no system drives it.

| Aspect | Live (bool) | Orphan (entity/package) | Rigor verdict |
| --- | --- | --- | --- |
| Grounding (III.8 / **I.16**) | a thin flag proxying "crystallized into an institution" | Althusserian ISA/RSA layer: crystallized relations, internal balance-of-forces, survives member turnover | **Orphan wins** — richer named material relation; delete-orphan is thus *ruled out* (can't discard the more-grounded side) |
| III.10 Earn-Its-Keep | runs in-tick + persisted | 311 LOC + entity dynamics, zero production callers | Live wins — the blessed layer is built-but-inert |

**Rigor:** the two levers pull opposite ways because this is **one half-finished migration**, not two
rival implementations. `delete-orphan` requires the live path be equal-or-superior in rigor — the bool
is *strictly less* grounded than the entity (III.8 / **I.16 Organization vs Institution**, the on-point
article per the verifier), so deleting the package would be a rigor regression. And Percy's
full-vision-no-MVP rule protects Draft-spec work from deletion.

**Recommendation:** Keep both; **freeze** the bool (its `DeprecationWarning` is the bridge; add a guard
that no new code sets it True); record an ADR/convention that the terminal state is
**wire-orphan/retire-live once spec-040 is ratified** and its systems join `_DEFAULT_SYSTEMS` (at which
point the bool + its schema column retire). The ledger-scope action is **documentation + the freeze**;
the full wire is a feature. · Cost **S** (docs + freeze guard; zero runtime change).

**Cites:** `institution/__init__.py` · `action_eligibility.py:168-169` · `organization.py:186,207-212`
· `postgres_schema.py:111` · `world_state.py:183-201,391,397` · `entities/institution.py:279,21` ·
`specs/040-*/spec.md` (Draft) · `tests/unit/institution/` (11 files) · Constitution I.16 / III.8 / III.10

**Adversarial verdict:** CONFIRMED. Verifier note: **I.16** is the more literal article than III.8 here,
and III.10's category-theory scoping *weakens* the delete counter-case — both corrections **strengthen**
`reconcile`.

> **— Percy's ruling:** _(pending)_

---

## Fork 6 — gamma-III visibility tensor inert outside 2022

**Disposition: `wire-orphan/retire-live`** · confidence medium · moves baseline: **yes** (full fix) · verify: CONFIRMED

**[correction]** gamma_III **is wired** (`runner.py:896-900`) — the defect is **data-starvation**, not
non-wiring. Its paid-care adapter returns a real value **only for `year==2022`** (`adapters.py:112-118`);
worse, the tick feeds `year = base_year + tick//52` with `base_year` defaulting to **2010** here vs 2022
in `production.py` — so the canonical 520-tick run **never reaches 2022** and gamma_III is the **0.33
fallback for the entire run**. That 0.33 is an ungrounded magic constant (III.1) that only coincidentally
equals an unrelated ratio — and it's **wrong**: the real 2022 value is **0.3725** (independently
recomputed by the verifier: 19.6B paid / 52.6B total).

| Aspect | Live (0.33 fallback) | Orphan (computed gamma_III) | Rigor verdict |
| --- | --- | --- | --- |
| III.8 / III.1 | ungrounded magic constant | `L_paid/(L_paid+L_unpaid)`, traces to reproductive-labor visibility (Fortunati) | gamma_III wins decisively; 0.33 also violates III.1 |
| III.10 Earn-Its-Keep | always runs, but is a constant dressed as a per-year coefficient | carries a real LAW (Fortunati exploitation `(1−g)/g`) but **as wired never executes** (data only for a year the run skips) | Split — the *construct* earns keep; the *current data wiring* does not |
| III.4.2 Fixture vs Runtime | an honest (if ungrounded) constant | backed by two **in-code pinned dicts** used as production runtime | Both flawed; gamma_III's dicts **violate III.4.2** — the concrete blocker to remove regardless |

**Recommendation (staged):** **(immediate, in-scope, no baseline move if `base_year=2010`)** delete the
two fixture-as-runtime dicts from the production path to cure III.4.2, and make the static-ness honest
(loud WARNING + documented constant, or refuse to fabricate a per-year value). **(data program)** load
QCEW care-sector facts (NAICS 61/62/814 — QCEW already blessed; specs 086/097/098) and add ATUS to the
data catalog with a loader (Spec-057-style — a normal III.4 add, **not** an IX.3 amendment), then back
the adapters with real multi-year runtime data. **Do not delete gamma_III.** · Cost **S** now / **L** full.
*(Aligns with owner-queue item 9: "wire gamma now.")*

**Cites:** `gamma/adapters.py:60,112-118,140-150` · `gamma/gamma_iii.py:161-164` ·
`tick/system/__init__.py:283-284,404,412` · `runner.py:896-900` · `reference_data_cache.py:53` ·
Constitution III.8 / III.10 / III.4.2 / III.1 · memory obs 42790 (care NAICS have zero QCEW facts)

**Adversarial verdict:** CONFIRMED. Verifier independently recomputed 0.3726 vs the 0.33 fallback;
confirmed the immediate fixture-cleanup is byte-identical while the full fix moves the baseline.

> **— Percy's ruling:** _(pending)_

---

## Fork 7 — `organizations/consciousness.py` typed trio vs `ooda/action_effects.py` dict path

**Disposition: `delete-orphan`** · confidence high · moves baseline: no · verify: CONFIRMED

**[correction]** the framing was backwards: the orphan trio is the Feature-031 **predecessor**; the live
`action_effects.py` is the Feature-032 **superset** (its docstring says it *extends* the 031 formula with
membership-overlap credibility, action-type multipliers, and a per-tick clamp). The "live violates
Pydantic-first" argument is **weak** — reading graph-node dicts in the hot loop is the *sanctioned*
CLAUDE.md convention, not a typing violation. `tendency_modifier` (line 58) **is shared** (imported live)
and must be kept.

| Aspect | Live (dict superset) | Orphan (typed trio) | Rigor verdict |
| --- | --- | --- | --- |
| Formula richness (III.8) | five-factor + membership-overlap + action_base + clamp | bare five-factor product | Live wins — a strict superset of grounded factors |
| III.10 Earn-Its-Keep | runs every tick via `engine/actions` dispatch | zero runtime callers (re-exports + docstrings only) | Live wins decisively — the trio is vocabulary |

**Recommendation:** Delete `derive_credibility`, `consciousness_effect`, `aggregate_consciousness_effects`
+ their re-exports + orphan tests (`test_consciousness_effect.py`, one Detroit call). **Keep
`tendency_modifier`.** Do **not** wire the orphan in — it takes typed models (needs Organization
reconstruction in the hot loop = a graph-round-trip regression) and its Business-workforce default
differs. · Cost **S** · byte-identical (zero runtime callers).

**Cites:** `consciousness.py:21,58,71,121` · `action_effects.py:1-9,19,33-103,325` ·
`engine/actions/__init__.py:59-64` · Constitution III.10 / III.8 · CLAUDE.md hot-path gotcha

**Adversarial verdict:** CONFIRMED. Deleting zero-caller code can't move the hash; the numeric divergence
confirms a naive swap would *not* be byte-identical, so deletion (not reconcile) is the honest call.

> **— Percy's ruling:** _(pending)_

---

## Fork 8 — Three imperial-rent Φ sites at different scales

**Disposition: `reconcile`** · confidence high · moves baseline: no · verify: CONFIRMED

**[correction]** sites 1 and 2 are **not** independent — site 2 *consumes* site 1: `imperial_rent.py:126-142`
takes the national per-industry `phi_vector` (site 1) and pushes it down to per-county `phi_hour` via the
QCEW-share allocator. They are two scales of **one** quantity, **already reconciled by construction**.
Site 3 (`melt/rent_differential.py`) is a **different material relation** (settler / internal-colony wage
gap) — and it reads hardcoded `_MOCK_EARNINGS/_MOCK_EMPLOYMENT` (a III.4.2 + III.1 defect). Site 4 is a
pass-through consumer. All three *recompute* Φ, none *stores* it (II.2 satisfied).

| Aspect | Sites 1+2 | Site 3 | Rigor verdict |
| --- | --- | --- | --- |
| Relationship | one pipeline (allocator distributes the national vector) | standalone wage-differential calc | Premise "three unreconciled parallels" is **false** — 1↔2 reconcile by an explicit deterministic transform |
| Material relation (III.8) | international unequal exchange (an **I.2** channel) | internal-colony wage gap — **not** one of I.2's three channels | Different processes → must **not** be summed into one Φ |
| Data (III.4.2) | blessed runtime BEA I-O + QCEW | in-source mock for ACS (not catalogued) | Site 3 is a standalone fixture-as-runtime defect |

**Recommendation:** Delete none. (a) Document that 1+2 are one pipeline and add the assertable invariant
`Σ_counties(phi_hour·emp·HOURS) == national total_phi` (tolerance-aware under QCEW suppression). (b) Add a
convention note that site 3 measures a *distinct* relation and must **not** be folded into the I.2
aggregate Φ without an **I.2 amendment (IX.3)**. (c) File site 3's mock data as a separate III.4.2/III.1
defect. · Cost **S** (docs + one invariant test; no math change).

**Cites:** `production_chain_rent.py:176-189` · `imperial_rent.py:86-88,126-142` ·
`leontief_rent/industry_to_county_allocator.py` · `melt/rent_differential.py:102-153,272` ·
Constitution I.2 (three Φ channels) / II.2 / III.4.2 / III.8 / IX.3

**Adversarial verdict:** CONFIRMED. I.2 does enumerate exactly three channels, so the internal colony is
genuinely a 4th → folding it correctly triggers IX.3. The invariant must be residual-aware (QCEW suppression).

> **— Percy's ruling:** _(pending)_

---

## Fork 9 — `derivations/` decorator-registry vs `world_state.py` `@computed_field`

**Disposition: `delete-orphan`** · confidence high · moves baseline: no · verify: CONFIRMED

**[correction]** `metabolic.py`'s docstring claims the WorldState computed_fields "delegate to these
functions" — **false**: `world_state.py:763-781` inlines the sums and does **not** import `derivations`.
It's a pure **parallel duplicate** (byte-identical math, same `≤0 → 999.0` guard), and the docstring
actively misrepresents the live code.

**Rigor:** III.10 is decisive — the `@derived`/registry pair is introspection **vocabulary** (nothing in
production reads the marks; no test converts the registry into an invariant). The II.2 "derivations are
functions, never stored" stance is **already fully satisfied** by the live `@computed_field` path
(recomputed on access, excluded from the frozen constructor), so the orphan buys **no** incremental rigor.
III.8 neutral (same Metabolic Rift relation).

**Recommendation:** Delete `src/babylon/derivations/` (4 files, 190 LOC) + its 2 orphan tests. If Percy
later wants a *global* "no `@derived` name is ever persisted" enforcement lint (a real II.2 invariant),
re-introduce a registry inside an actual enforcement spec — that's new code under IX.3, not a reason to
keep an inert duplicate now. · Cost **S** · byte-identical.

**Cites:** `derivations/metabolic.py:6-8` (false docstring),`:26-66` · `registry.py:13-63` ·
`decorator.py:44-56` · `world_state.py:763-781` (no `derivations` import) · Constitution III.10 / II.2 / III.8

**Adversarial verdict:** CONFIRMED. rg confirms the only external importers are the two named test files;
the byte-identical duplication and false docstring both verified.

> **— Percy's ruling:** _(pending)_

---

## Fork 10 — `TraceRecorder` / `trace_log` buffered-event subsystem vs the live trace VIEW

**Disposition: `delete-orphan`** · confidence high · moves baseline: no · verify: CONFIRMED

**[correction — load-bearing]** the premise "superseded by the migration-0019/0023 SQL trace-emission
view" mislabels the objects. 0019/0023 create the **VIEW** `view_runtime_trace_emission` (the live
determinism trace → byte-identical `trace.csv`, read by the headless runner) — they do **not** emit into
`trace_log`. The `trace_log` **table** is written *only* by `TraceRecorder.flush()` via the two **unwired**
observers (Fork 11), and has **zero** live SELECT readers. So "table vs Python buffer" is a false
dichotomy: `trace_log` + `TraceRecorder` is a **wholly dead** arbitrary-event debug log; the VIEW is the
live trace and captures entirely different (Marx-primitive) data.

**Rigor:** III.10 dispositive (the chain runs zero times in production). III.8 reinforces — the view's 22
columns each name a material relation; `TraceRecorder` is content-agnostic `{system,event,data}` soup.
III.7's real mechanism is the view + `trace_emitter`, untouched.

**Recommendation:** Delete the whole dead cluster — `trace_recorder.py`, the `TraceCollector` protocol
block, `persist_traces()` + partition helpers, the `TRACE_LOG_DDL` templates, the 4 exports — **bundled
with Fork 11** (the observers are its only callers). Keep migrations 0019/0023 + the view. · Cost **S**
(bundled) · byte-identical. **Counter-case:** if Fork 11 *wires* the observers, `TraceRecorder` is their
sink and must be kept — so decide 10 and 11 together.

**Cites:** `trace_recorder.py:32,94,105` · `postgres_runtime/_legacy.py:894-925` (sole writer) ·
`postgres_schema.py:358` (`trace_log` TABLE) · `session_recorder.py:78` + `persistence_observer.py:14`
(sole, unwired callers) · `migrations/0019,0023` (create the VIEW) · `runner.py:540,738,794,810` (live
readers) · Constitution III.10 / III.7 / III.8 / II.11

**Adversarial verdict:** CONFIRMED. II.11 used correctly (the migration SQL self-declares the view as the
cross-subsystem interface); zero live SELECT on `trace_log` confirmed.

> **— Percy's ruling:** _(pending)_

---

## Fork 11 — Three parallel recorders (PersistenceObserver / SessionRecorder / JsonlSessionRecorder)

**Disposition: `unify`** · confidence high · moves baseline: no · verify: CONFIRMED

**[correction]** even the "canonical" `SessionRecorder` is **unwired** today — the live run persists via
`WorldStateBridge.persist_tick` (`bridge.py:429`), bypassing all three observers. `PersistenceObserver` is
a **strict subset** of `SessionRecorder` (writes the identical `RuntimePersistence` sink; its only unique
feature is a `perf_counter` debug log). `JsonlSessionRecorder` is a **different sink** (local JSONL/ZIP
forensics), not a duplicate.

**Recommendation:** Keep the canonical `SessionRecorder` (verified superset: `start_tick` + `_started`
ordering guard); **delete `PersistenceObserver`** (209 LOC) + its 2 exports + the self-skipping
`TestPersistenceObserver`. Treat `JsonlSessionRecorder` as a **separate item** — also orphaned; recommend
`delete-orphan` unless Percy wants the debug-archive export wired. **Note for Percy:** keeping
`SessionRecorder` is a *bet* that the observer pattern is the future replay seam (CLAUDE.md designates it
canonical), not a claim it runs today — if replay will live permanently in `WorldStateBridge`, downgrade
to `delete-orphan` on **all three** (~650 LOC). Bundle with Fork 10. · Cost **S** · byte-identical.

**Cites:** `session_recorder.py:115,108,134-136` (superset) · `persistence_observer.py:108-116` (only
unique feature) · `bridge.py:429,565` (live persistence bypasses all 3) · `utils/recorder.py:30` (JSONL —
different sink) · `test_postgres_runtime.py:1102-1160` (self-skipping) · Constitution III.10 / III.7 · CLAUDE.md

**Adversarial verdict:** CONFIRMED. III.8 honestly declared inapplicable to IO plumbing (no mis-forcing);
`SessionRecorder` is genuinely the superset.

> **— Percy's ruling:** _(pending)_

---

## Fork 12 — Marx reference formulas `calculate_rate_of_profit` / `calculate_organic_composition`

**Disposition: `delete-orphan`** · confidence high · moves baseline: no · verify: CONFIRMED

**[correction]** line numbers in the brief had drifted (imports `__init__.py:130-131`, `__all__ :185-186`).
Both functions self-label "Epoch 2 placeholder," are **unregistered** in `FormulaRegistry.default()`, and
have **zero** production callers (only tests + docs). The live path — `ValueTensor4x3.profit_rate`
(`s/(c+v)`) and `.organic_composition` (`c/v`) — is the same arithmetic but **derives** c/v/s from the
QCEW-fed 4×3 reproduction schema rather than taking bare floats.

**Rigor:** III.8 — the tensor grounds r and OCC in a named value decomposition sourced from blessed QCEW;
the standalone functions ground nowhere (their "QCEW mapping" is docstring prose, never wired). III.10 —
unregistered + uncalled = the textbook inert construct. II.2 tie. The tensor is equal-or-superior on every
axis → the delete-orphan predicate.

**Recommendation:** Delete both functions + imports + `__all__` + their tests + 2 RST doc refs. **Preserve
the Epoch-2 intent** in `ai-docs/epochs/epoch3/epoch2-trpf.yaml` (the proper Future-Enhancements home per
Percy's global rule). Keep `calculate_trpf_multiplier` (out of scope). · Cost **S** · byte-identical.
**Counter-case:** spec-088 plans to wire these per-node — but that's future work; delete now, plan preserved.

**Cites:** `trpf.py:107,174` · `formulas/__init__.py:130-131,185-186` · `formula_registry.py` (neither
registered) · `tensor.py:350,384,178` · `specs/010-*/spec.md:66` · `ai-docs/epochs/epoch3/epoch2-trpf.yaml`
· Constitution III.8 / III.10 / II.2

**Adversarial verdict:** CONFIRMED. Zero production callers verified; the Future-Enhancements preservation
satisfies Percy's "don't delete working code — keep a Future-Enhancements doc" rule while III.10 removes the
inert code.

> **— Percy's ruling:** _(pending)_

---

## Fork 13 — C2: duplicated QCEW hydrator construction in `engine/hydration/reference.py`

**Disposition: `reconcile`** · confidence medium · moves baseline: no · verify: CONFIRMED

**[correction]** the duplication is **two** patterns, not one. (1) The straight-line hydrator-build block
(`SQLiteQCEWSource`+`StubBEASource`+`DepartmentMapper`+`MarxianHydrator`) is duplicated verbatim at
`:184-199` and `:408-421` — unbranched, **trivially byte-identical** to extract. (2) The `DimCounty→DimTime`
resolution at **four** sites has **differing short-circuit shapes** — this is the part that bit the reverted
Part-1 C2 attempt (which ran the DimTime query unconditionally). The county-first short-circuit is the
byte-identity contract.

**Rigor:** the ideological levers (III.8/II.2/III.10) don't discriminate — both copies read the same blessed
QCEW path. The one live lever is **III.7**: any extraction must preserve the county-first short-circuit.
DRY is a code-quality concern, not a constitutional mandate.

**Recommendation:** Extract **only** the safe hydrator-build block into `_build_hydrator(session)`. Do
**not** re-attempt the resolver unless it reproduces the short-circuit at all four sites (document that as
an explicit determinism contract); otherwise leave those four as-is (`keep/no-action` for that half). Low
stakes. · Cost **S** · byte-identical. (Verifier nuance: strictly, an extra *read-only* SELECT doesn't move
a determinism hash — only changed outputs do — but the conservatism is fine.)

**Cites:** `reference.py:184-199,408-421` (hydrator build) · `:262-275,440-447,508-518,653-679` (4 resolver
sites) · Constitution III.7 / III.4.2 (not triggered) · memory obs 45936 (C2 reverted)

**Adversarial verdict:** CONFIRMED. The recommendation confines extraction to the unbranched half and
degrades the resolver half to keep/no-action — no path risks the baseline.

> **— Percy's ruling:** _(pending)_

---

## Fork 14 — C3: zero-denominator convention `inf` (tensor.py) vs `0.0` (substrate)

**Disposition: `reconcile`** · confidence high · moves baseline: no · verify: CONFIRMED

**[correction — premise largely false]** `equalization.py:95`'s `return 0.0` is a **scale-factor guard**
(empty hex, `c_i==0`), **not** a zero-denominator ratio. The substrate's actual ratio handling is inline in
`_compute_capital_weighted_rates` (`r_i` clamped to 0.0 when `cv ≤ _MIN_RATE_BASIS` or non-finite), and it
is **computed inline, never read from a stored field** — so tensor.py's `inf` has **no propagation path**
into the conservation gradient. There is no correctness bug, only reader-confusion risk.

**Rigor:** legitimate **specialization**, not an inconsistency. `inf` is the mathematically-honest undefined
ratio for a degenerate department (a *leaf metric*, never summed); `0.0` is **III.7-mandated** — the module's
own comment (`equalization.py:35-41`) documents that `inf` would yield `inf−inf = NaN` and break the INV-001
conservation proof and the tick hash. The two modules genuinely **cannot** swap conventions. A shared
`_safe_ratio` would earn nothing (III.10) and risk perturbing the clamp.

**Recommendation:** Add a one-line documented convention in each module's docstrings (tensor.py: `inf` =
honest undefined leaf sentinel, intentionally not the substrate convention; equalization.py: `0.0` =
conservation-mandated clamp), optionally an ADR. No code change. (Defensible alternative: `keep/no-action`
as premise-false.) · Cost **S** (docs only).

**Cites:** `tensor.py:187-189,202-204,359-362` (`inf`) · `equalization.py:35-41` (inf→NaN→broken
conservation),`:49-50` (r_i inline),`:64-73` (0.0 clamp),`:89-99` (line 95 is a scale guard) ·
Constitution III.7 / III.8 / II.2 · spec-053 INV-001

**Adversarial verdict:** CONFIRMED. The analyst's correction to the fork premise is itself correct; the
two modules cannot swap conventions without breaking the hash.

> **— Percy's ruling:** _(pending)_

---

## Fork 15 — C5: EndgameDetector overshoot guard vs the canonical 999.0 convention

**Disposition: `unify`** · confidence high · moves baseline: no *(unconfirmed — run the gate)* · verify: CONFIRMED

**[correction]** the numerators are **identical** — `SocialClass.consumption_needs` is a computed_field
returning `s_bio + s_class` (`social_class.py:474-476`), so `WorldState.total_consumption` equals
EndgameDetector's `sum(s_bio + s_class)`. The **only** divergence is the zero-biocapacity guard. And
EndgameDetector is a **lone outlier against three** canonical impls that all cap at 999.0 (the blessed
`metabolic_rift.calculate_overshoot_ratio` that `MetabolismSystem` itself calls, the `world_state`
computed_field, and `derivations/metabolic`).

| Aspect | EndgameDetector | Canonical (×3) | Rigor verdict |
| --- | --- | --- | --- |
| Zero biocapacity | `return False` **and resets** the consecutive-tick counter (reads exhaustion as "no data") | `999.0` → maximal finite overshoot ≫ threshold(2.0), collapse-eligible | Canonical wins **III.8** — exhausted biocapacity *is* the ecological-collapse state, not a data gap |
| Single definition (II.2) | inlines its own C/B + guard | one blessed formula already exists | Canonical wins — one definition; the inline reimpl only manufactures a latent mis-fire |

**Rigor:** the False-on-zero guard is **materially backwards** — it makes the single most-collapsed world
(zero regenerative capacity) *structurally unable* to fire its own `ECOLOGICAL_COLLAPSE` terminal outcome.
A latent bug, not a style choice.

**Recommendation:** Route `_check_ecological_collapse` through the canonical `state.overshoot_ratio` (as
sibling `metrics.py:282` already does), **keeping** its consecutive-tick counter; add a unit test that
zero-biocapacity sustained N ticks *does* trigger collapse. **Baseline caveat:** expected byte-identical
(the divergent branch is reachable only when total biocapacity ≤ 0, which the 5 short scenarios likely never
hit) but **this was NOT confirmed — run `mise run qa:regression` before merge** and treat any change as a
deliberate rebaseline. · Cost **S**.

**Cites:** `endgame_detector.py:361-363,365-372` · `world_state.py:779-780` · `social_class.py:474-476`
(numerators identical) · `metabolic_rift.py:82-83` · `derivations/metabolic.py:64-65` · `metrics.py:282` ·
`endgame.py:53-63` (threshold 2.0, sustained 5) · Constitution II.2 / III.8 / III.10 / III.7

**Adversarial verdict:** CONFIRMED. The baseline caveat is the constitutionally-correct posture (honest
"unconfirmed, run the gate"), not an overclaim. Verifier adds: confirm `state.entities` holds only
`SocialClass` before routing through `consumption_needs`.

---

## Correction notes (not forks)

- **`validate_schemas.py` — no action.** The plan flagged it as "obsolete post `schemas/` deletion." The
  premise is **false**: `src/babylon/schemas/` (5 JSON) was *not* deleted, so `tools/validate_schemas.py`
  (points `SCHEMAS_DIR`/`DATA_DIR` at live dirs) still functions. No entry, no change.
- **`SimulationConfig` shell — Part 3.** B1 pruned its 36 dead coefficient fields (kept `rng_seed`).
  Retiring the *class shell* (its `ServiceContainer`/observer-protocol/web-config couplings) is
  architectural and belongs to the **Part-3 persistence/frontend track**, not this rigor ledger.

## Cross-cutting observations

- **"The stub-zero *is* the live path."** Twice (Forks 1, 6, and structurally 8) the "simplified live
  path" turned out to be a graceful-degradation stub firing because a spec's services were never wired —
  the rich model is present, tested, and gated off. These aren't "simple vs rich" so much as
  "spec-Implemented-on-paper but never activated at runtime."
- **Fixture-as-runtime (III.4.2) recurs.** Hickel (Fork 1), the gamma-2022 dicts (Fork 6), and the
  `rent_differential` ACS mock (Fork 8) all read a pinned/fixture snapshot where a refreshable runtime
  source belongs. This is a **cross-cutting data-provenance theme** worth its own remediation pass.
- **III.10 does most of the work**, with **III.8** as the tie-breaker for *which* side is more grounded —
  and it repeatedly favored the orphan on grounding while favoring the live path on earn-its-keep, which is
  exactly why these were judgment calls, not sweep items.
- **Bundle Forks 10 + 11** (shared dead cluster). **Sequence Fork 3's value ruling before its wire.**
  **Fork 1 needs the trade-DRAIN reconciliation decision** before any wiring.

---

*Verification addendum (Opus 4.8, 2026-07-09, branch `docs/fork-reconciliation-ledger`, `dev` @ `ea403107`).
Authored by a 30-agent workflow (15 rigor analysts + 15 adversarial verifiers, 0 errors), each grounded in
first-verified wiring facts and the Constitution v2.7.0; every recommendation carries an independent
CONFIRMED/CHALLENGED verdict. No `src/` file was modified to produce this ledger — `git status` shows only
docs/ai-docs/project/memory. The one CHALLENGED entry (Fork 4) records its dissent in full and defers to the
skeptic's revised recommendation. Implementation of any ruling is Part-2b, gated on `mise run check` +
`qa:regression`.*
