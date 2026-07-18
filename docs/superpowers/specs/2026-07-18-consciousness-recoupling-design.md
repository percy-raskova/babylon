# Consciousness Recoupling — Design Spec

**Status:** Draft, owner-ratified in outline 2026-07-18. Requires an ADR and
probably a constitutional amendment (see §8).

**Supersedes in part:** the Task-2/2b "sustained exploitation" approach in
`docs/superpowers/plans/2026-07-18-null-play-political-coupling.md`. Those
commits (`948e46ad`, `7289df75`) stay — the per-class fix is a prerequisite —
but the `balance < 0` agitation gate they feed is replaced here.

**Theory sources (primary, read 2026-07-18):** MIM corpus
(`project/notes/percy/`), Amin *Unequal Development* (UD) and *The Law of
Worldwide Value* (LWV), Emmanuel *Unequal Exchange* (UE). Citations are to
printed page numbers. Full findings: memory `consciousness-theory-grounding`.

---

## 1. The defect

Under null play every political axis is flat for 520 ticks. Root cause chain:

1. `agitation` is a pure first difference (`consciousness_routing.py`), so
   material steady state drives it to zero and decay erases the remainder.
2. Fixed in part by adding a LEVEL term reading the wage opposition's `balance`
   (`948e46ad`), then correcting it from a global class-mean to a per-class
   read (`7289df75`).
3. **The remaining defect:** that term fires only when `balance < 0`. Under the
   ratified theory, `balance > 0` for every wage-earning class inside US
   borders. So the term is correct and fires never — verified empirically
   (min per-class balance across all 5 canonical scenarios: ~1e-6, floor 0.0,
   never negative over 60 ticks).

The engine currently discards the entire positive branch, which is where the
whole domestic population lives. **That is the complete explanation of null-play
flatness.**

## 2. The correction

> A positive balance does not suppress political energy. It redirects it.

Three independent derivations:

- **Emmanuel UE p.180:** "the antagonism between rich and poor nations is likely
  to prevail over that between classes." His worked cases of positive-balance
  workers — British dockers defending empire, the US labor aristocracy,
  Algeria's European proletariat (pp.180-184) — are all instances of *high*
  political energy, aimed at chauvinism.
- **MIM `mim-lumpen.txt:206-217`:** falling class status + settler national
  consciousness routes to fascism *as the rule*; the revolutionary exception
  requires cross-national proximity to oppressed-nation lumpen (`:190-193`).
- **Amin LWV p.127:** the social-democratic compromise is the political form of
  the bribe, and was "difficult to imagine without the imperialist rent."

**Design consequence:** `balance` sign feeds the **bifurcation direction**, not
a gate on whether agitation exists. Magnitude drives intensity on either branch.

```
agitation_magnitude = f(|balance|, repression, national_term, ...)   # always >= 0
bifurcation_direction:
    balance > 0  ->  chauvinist / fascist pole
    balance < 0  ->  revolutionary pole
```

Babylon already has the bifurcation mechanism (±1 routing by SOLIDARITY edge).
This is wiring, not new machinery.

## 3. The primitive is the noncompeting labor pool, not "class"

Neither Amin nor Emmanuel licenses a per-class balance as such:

- **Emmanuel UE pp.162-164:** the mechanism requires noncompeting labor markets
  under a common profit rate. Inside a *competitive* national labor market the
  wage-based transfer vanishes. A per-class balance for an undifferentiated
  national working class is a category error in his own terms.
- **Amin LWV p.92:** the core proletariat's wage tracks productivity "more or
  less parallel" — near zero, **not** positive. Amin explicitly rejects the broad
  labor-aristocracy thesis (UD p.362: the concept "has now been overtaken in
  reality by more complex differentiations"); LWV drops the term entirely.

But Emmanuel supplies the bridge himself — "Wages Zones within a Nation"
(UE pp.121-123) treats racially segmented US and South African labor as
functionally equivalent to the international case. Amin independently names the
same structure (UD p.362: "the proletarianization of the blacks in the United
States... the extreme form: South Africa, Rhodesia, Israel"). MIM names it
internal semi-colonies.

**Therefore:** the balance formula is valid between **labor pools walled off
from wage-equalizing competition**, not between arbitrary classes. This is a
*national* boundary drawn inside the country — the axis MIM calls principal in
the US (`mim-lumpen.txt:193-196`), and the layer ADR080 made live
(`engine_bridge.py:7273-7287`; sovereignty is no longer inert). Consciousness
simply does not read it.

**Implementation:** a class's balance participates in the transfer relation only
where a segmentation boundary exists. Segmentation must be an explicit,
inspectable property, not inferred.

## 4. The Φ feedback loop — the game loop

Ratified line: **late MIM(Prisons) 2011-2016** — no super-exploitation inside US
borders; only undocumented productive-sector workers and the lumpen are
revolutionary subjects. With the owner's caveat, which is theoretically
load-bearing rather than a hedge:

> a revolutionary movement that disrupts Φ genuinely proletarianizes /
> lumpenizes much of the labor aristocracy, at which point they *do* become
> revolutionary.

This is Amin's mechanism (LWV p.127 — the compromise depended on the rent) and
MIM's Comintern predicate (`labor-aristocracy:63-71`, which lists "loss of
colonies" and "loss by certain Powers of their monopoly position" as conditions
under which "the labor aristocracy will truly fall"). MIM explicitly rules
ordinary recessions insufficient (`:418-425`).

```
player action -> periphery disruption -> Φ falls -> LA balance crosses 0
              -> bifurcation flips to revolutionary pole -> feedback
```

**This closes the loop and is what makes the hard line playable rather than a
static verdict.** It also means the existing `balance < 0` trigger is not wrong
— it is *downstream*. Φ is the driver, and the engine already computes Φ.

Gate design: a conjunctive predicate over geopolitical state, not a continuous
function of domestic wages. Ordinary economic fluctuation must not open it.

## 5. Additional channels the theory requires

| # | Channel | Source | Status in engine |
|---|---|---|---|
| 1 | **Repression → consciousness** | MIM `labor-aristocracy:34-40`: "The lack of violent conflict itself is a fundamental reason for the lack of political consciousness among the workers." | `StruggleSystem` @16 already runs before `Consciousness` @17. **Ordering correct, edge not drawn.** |
| 2 | **National term that can override class** | MIM `mim-lumpen.txt:186-189`: petty-bourgeois consciousness "overwhelmingly dominant among white people of *all classes*." | Sovereignty layer live post-ADR080; unread by consciousness. |
| 3 | **Trajectory / expectation** | MIM `mim-lumpen.txt:258-268`: identical current position, opposite outcome, determined by the distribution of *neighbours'* trajectories. | Not present. A per-node float cannot express it; a neighbourhood aggregate over `BabylonGraph` can. |
| 4 | **Monotonicity guard** | MIM `mim-internal-colonies.txt:521-525`: the *marginal* labor aristocracy is "the most reactionary of all." | Violated by any smooth `agitation ↑ as balance → 0⁺`. That band must *amplify* fascist routing. |
| 5 | **Periphery exploitation rises over time** | Amin UD pp.360-361: the rate of surplus-value must climb to fight the core's falling profit rate. | Held constant — a missing driver. |
| 6 | **Exogenous periphery agency** | Amin LWV pp.110, 126-128 ("Southern awakening"). | Absent. Destabilization originates in the periphery, not core wage movement. |

Bifurcation refinement: routing to the revolutionary pole requires
**cross-national** adjacency (MIM `mim-lumpen.txt:190-193`). A same-nation
SOLIDARITY edge must not flip the sign.

## 6. Coefficients — grounding available

- Core:periphery wage ratio **20-40×** (UE p.66); Bettelheim **20-30×** (p.385)
- Wage dispersion amplitude "multiplied tenfold on the global scale" (LWV p.84)
- Profit rates **15-22%** Latin America vs **11-14%** US (UD p.162)
- US minimum wage "almost ten times the average wage in the Third World"
  (`mim-internal-colonies.txt:556-557`)
- MIM lumpen census ~2010: 11.48M lumpen + 8.5M semi-proletariat; 20-25% of New
  Afrika, 15-20% of Raza, 30% of First Nations; ~4% of US population
  (`mim-lumpen.txt:319-323`, `373-412`)

**Gap:** the actual value-transfer arithmetic lives in MIM's "Imperialism and Its
Class Structure in 1997", which is *not* in the local corpus. Zak Cope's
*Divided World Divided Class* **is** on disk
(`ai/_inbox/babylon_books/DividedWorldDividedClass_ZakCope.pdf`) and is the
acquisition target for a grounded Φ coefficient. Until then, coefficients are
provisional and must be declared as such.

Every coefficient goes in `GameDefines` with an Aleksandrov trace naming the
material relation. No hardcoded values.

## 7. Sentinels — required, not optional

Per the standing rule that every phase ships a gate preventing its error *class*:

1. **Correct-but-inert.** This work exists because a change passed every gate
   while its triggering condition never occurred. Gate: over a real canonical
   run, every declared-live branch must be taken at least once; unreached
   branches must be explicitly declared dormant with a reason. Would have caught
   `948e46ad` on the day it landed.
2. **Intensive aggregation.** Dispatch aggregation on field type — extensive
   sums, intensive uses `ScaleAdjunction.aggregate_intensive` (share-weighted).
   Fail loudly on an unclassified field. `_mean_asymmetry` is the known
   violation.
3. **Gate blindness.** `qa:regression` returned 5/5 byte-identical on a
   consciousness-math change because the facade never reconstructs
   `opposition_states` (`world_state.py:505-518`) and the 5 scenarios contain no
   Territory objects. A determinism gate must be *provably able to fail* —
   demonstrate by mutation, not assertion.
4. **Monotonicity.** Property test: agitation must not increase smoothly as
   balance → 0⁺ (§5.4).
5. **Theory-trace.** Each new coefficient carries a citation; a coefficient
   without one fails the gate.

Every sentinel is validated by **mutation** — reintroduce the original bug and
confirm the gate catches it. An unmutated gate is an unproven gate.

## 8. Constitutional exposure

- **Aleksandrov Test (III.8):** the *current* design derives a US political
  variable from a quantity the ratified theory says is uniformly positive in the
  US, and therefore carries no US signal. That is a formal construct without a
  material relation — a standing violation this spec resolves.
- **Amendment S / apex abstraction:** the national axis is a second opposition
  alongside the class axis, not a new primitive — it is expressible as a
  dialectic `D = (A, Ā, w, T, σ)` and belongs in the `OppositionRegistry`. The
  parallel aristocracy schema (`mim-three-oppressions.txt:207-209` — labor,
  national, and gender aristocracies) means this is *one* abstraction
  instantiated three times, not three bespoke systems.
- **III.10 earn-its-keep:** each channel ships with a law, a prediction, or a
  running computation. None ships as vocabulary.
- Needs an ADR. If the national axis is promoted to a CANONICAL opposition,
  that follows the ADR077-shadow → ADR078-promotion pattern: observe first,
  wire second.

## 9. Acceptance criteria

1. Under null play on the canonical nationwide scenario, political axes **move**
   over 520 ticks — and move in the *theoretically correct direction*: domestic
   classes accumulate chauvinist/fascist pressure, not revolutionary pressure,
   absent Φ disruption.
2. A player action that disrupts Φ measurably shifts labor-aristocracy balance
   toward zero, and crossing zero flips bifurcation direction.
3. Two classes with identical `balance` but different neighbourhoods diverge
   (§5.3).
4. The marginal-aristocracy band amplifies fascist routing rather than
   revolutionary (§5.4).
5. All five sentinels (§7) land and are mutation-validated.
6. `mise run check` green; `qa:regression` movement **declared** per scenario
   with direction and magnitude, in a ceremony commit + ADR, baselines
   regenerated once (ADR078 pattern).
7. No coefficient without an Aleksandrov trace.

## 10. Open questions for the owner

1. **Gender axis.** MIM treats it as a third independent oppression with its own
   material basis (leisure time, `mim-basics.txt:46-49`). In scope now, or
   declared and deferred?
2. **Segmentation source of truth.** Should the noncompeting-labor-pool boundary
   be derived from the sovereignty/nation layer, declared per social class, or
   both with a consistency sentinel?
3. **Periphery representation.** Amin's mechanism (§5.5, §5.6) needs periphery
   nodes with their own rising exploitation rate. Does the nationwide US
   scenario carry a periphery, or is Φ currently an exogenous scalar?
4. **Cope acquisition.** Read *Divided World Divided Class* for the Φ
   coefficient, or ship provisional coefficients and calibrate against observed
   curves?
