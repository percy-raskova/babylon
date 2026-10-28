# 13 — Leverage, not dials: state-snapshot dynamics, the 33/33/33/0 restoring force, and why a reform gets eaten

Read-only sweep, 2026-10-25. Question: **Babylon must not contain a number that carries a law's shape.**
What replaces the numbers — and once they are gone, what makes the system non-linear?

Three parts, one argument. A **state snapshot** supplies every coefficient as a *ratio of measured
period-$t$ quantities*. A **distribution integrated against a threshold** supplies every curve, S-curves
included, as a theorem. A **coupled difference system** over those ratios then produces what a designer
would otherwise dial in: the 33/33/33/0 partition, its restoring force, the 2020 snap-back, and the
bifurcation boundary the player has to find. Nothing needs a new primitive — every operation is
`+ − × ÷`, comparison, and a fold over a population; constants are `0`, `1`, exact integers.

**Guardrail honoured.** No Trotsky. Sources are Marx, Amin, Hickel, Cope, MIM(P), Strogatz,
Farjoun–Machover, Cottrell–Cockshott–Michaelson. `CONSTITUTION.md` v4.3.0 position: no sigmoids, no
stipulated response shapes, no new BSL primitive.

---

## 0. The rule this document enforces

`CONSTITUTION.md:120-122`: "Historical data can set envelopes, scales, priors, and comparison cases. It
must not silently set a mechanic's response shape or dictate its result."

`ai/THE_FORMALISM.md` §VII.1 turns that into an admission test. There is a **feel** region
$\Theta^{\ast}$ — the coefficient points at which every law of Parts I–V still holds — and the laws are
$\forall \theta \in \Theta^{\ast}$ statements. A legitimate knob moves the system *inside* $\Theta^{\ast}$
and changes only tempo: "The theorem is scale-free; the knob is pure tempo. … leaving $\Theta^{\ast}$ is
not 'hard mode,' it is a broken law the property suite catches" (`:784-786`). The anti-list bans a pinned
profit rate because it commits "II.2 (storing a derived quantity) and III.1 (a magic constant)
simultaneously" (`:801`).

So the distinction is not "number bad, no number good":

| kind | example | what it carries | verdict |
|---|---|---|---|
| **Tempo** | `TICK_DURATION_DAYS = 28` | how fast the clock runs | legitimate, declare it |
| **Mass / count** | `TRUCK_GROSS_WEIGHT_KG = 40000` | a designed object in the world | legitimate, declare it |
| **Fitted linear rate** | `α21 = 0.0006` per quarter | the *strength* of a stipulated form | suspect: the form is assumed, so the number does physics |
| **Shape parameter** | `steepness_k = 10.0` | the curvature of a stipulated curve | **banned** (ADR173) |
| **Stored equilibrium** | `W*₁ = 0.305` | a derived attractor, frozen | **banned** (II.2) |
| **State-snapshot ratio** | $c/v = K/V$ this period | nothing but the state | **correct** |

The test is one question: **given the state snapshot, does this number still need to exist?** If yes it is
a magic number; if no it is a cache of something the engine can read — and a cache of a derived quantity
is a II.2 violation waiting to drift.

---

# Part I — The 33% / 33% / 33% / 0% partition is a measured attractor

## 1.1 The claim and the arithmetic

`docs/reference/class-dynamics.rst:16-42` records the Director's theory verbatim: four wealth classes —
Top 1%, next 9%, next 40%, bottom 50% — each of the top three holding roughly a third of total wealth,
the bottom half holding essentially nothing. The heap encodes the claim as a partition, not an opinion:

```
dim_wealth_class (marxist-data-3NF.sqlite)
id | code | label        | babylon_class
1  | LT01 | Top 1%       | core_bourgeoisie
2  | N09  | 90-99%       | petty_bourgeoisie
3  | N40  | 50-90%       | labor_aristocracy
4  | B50  | Bottom 50%   | internal_proletariat
```

Net worth shares, `fact_fred_wealth_shares` ⋈ `dim_asset_category` where `category_label = 'Net Worth'`:

| Tier | Pop | Wealth 2024Q4 | mean 2010Q1–2024Q4 | min | max | SD | theory |
|---|---|---|---|---|---|---|---|
| Top 1% | 1% | **31.0%** | 30.14% | 28.1 | 31.0 | 0.68 | ~33% |
| 90–99% | 9% | **36.4%** | 38.71% | 36.4 | 40.1 | — | ~33% |
| 50–90% | 40% | **30.1%** | 29.70% | 28.1 | 31.6 | — | ~33% |
| Bottom 50% | 50% | **2.5%** | 1.48% | 0.4 | 2.7 | — | ~0% |

Heap coverage: **60 quarters, 2010Q1–2024Q4** ($8041 \le 4y+q \le 8100$). Three of four tiers sit within
3 pp of a clean third. The structure holds. Two corrections:

1. **`class-dynamics.rst:5` says "Fitted from FRED Distributional Financial Accounts (2015-2025)"** and
   its table is labelled "2025 Q2". The heap has no 2025 observation. Closest row is 2024Q4 =
   31.0/36.4/30.1/2.5; the doc's "2025 Q2" row is 30.7/36.4/30.3/2.5. The vintage label is unsupported by
   the heap it cites.
2. **The stored equilibria are outside the band's own mean.** `class-dynamics.rst:207-225` gives
   $W^\ast = (0.305, 0.382, 0.294, 0.020)$; the heap's 15-year means are $(0.3014, 0.3871, 0.2970,
   0.0148)$. A genuine attractor fitted to a stationary series should sit on the series mean. Three of
   four do not. These are 2015–2025-window fits wearing a 15-year label — the exact class of stored
   derived quantity `THE_FORMALISM.md:801` bans.

## 1.2 The series is a *band*, not a trend

Top 1% moved 2.9 pp in fifteen years (28.1 → 31.0), then 1.4 pp in one quarter, then 1.4 pp back in three.
No secular drift to extract. There is a **width**, and the width is the phenomenon. This is Cottrell,
Cockshott & Michaelson's *statistical* equilibrium, and they name the distinction Babylon needs:

> "Unlike a mechanical equilibrium, in which the system configuration remains static, a system can be in
> statistical equilibrium even when its configuration is continually changing. It is the probability
> distribution over possible system configurations that remains constant over time."
> — *Classical Econophysics* (2009), p. 143

**But the band is not the whole story, and the exception is the finding.** The 90–99% tier does not drift —
it *plateaus* at ~39.3 through 2012–2019, **steps down 3.3 pp across 2020–2022**, then plateaus at 36.4.
Five-year deltas, 2019Q4 → 2024Q4:

| Tier | 2019Q4 | 2022Q4 | 2024Q4 | Δ 5y |
|---|---|---|---|---|
| Top 1% | 30.4 | 29.5 | 31.0 | **+0.6** |
| 90–99% | 39.7 | 36.4 | 36.4 | **−3.3** |
| 50–90% | 28.2 | 31.4 | 30.1 | **+1.9** |
| Bottom 50% | 1.7 | 2.7 | 2.5 | **+0.8** |

The 2020 crisis did not produce a temporary shock that reverted. It **permanently compressed the
professional-managerial tier** and pushed value down into the 50–90% and bottom 50%, while Top 1% ended
slightly *ahead*. "Homeostatic" is therefore a property of the Top-1% share and of the aggregate; it is
**not** a property of the class structure. This is a basin shift in the parts riding inside a fixed sum, and
§4.3 is where it belongs.

The mechanism behind the aggregate band needs **no stipulated curve**: "if this process is continued the
economy settles to a Boltzmann–Gibbs distribution, $P(m) \propto \lambda e^{-\lambda m}$" (p. 141). The tail
follows — "a lognormal distribution with a Pareto tail" (p. 290) — and they draw the political conclusion
Babylon's design rests on: "extreme income inequality and recessions[] are necessary consequences of the
social relations of production and hence enduring and essential properties of capitalism, rather than
accidental, exogenous or transitory" (p. 291).

Farjoun & Machover reach the same place from the profit rate, as an *impossibility* result — a uniform rate
of profit "does violate a basic physical law, the second law of thermodynamics, known also as the law of
entropy. … A state in which all the particles travel at the same speed is much too 'orderly' to be a state
of equilibrium" (*Laws of Chaos*, pp. 53–54). Then the economic object: "the 'most chaotic' partition of
this total kinetic energy among the molecules results in a gamma distribution … the analogy of statistical
mechanics suggests that $R$ may also have a gamma distribution" (p. 68), where $R$ is the profit rate and
their $Z$ (wage-bill over capital) "is similar to what Marx calls organic composition."

**This is the constitutional argument for emergence, stated independently by two literatures.** The shape
is a theorem about a partition, not a function someone chose. Babylon cannot stipulate the gamma exponent
for the same reason it cannot stipulate a sigmoid: the exponent *is* the distribution of firm-level
capital and profit, and must be read off the state.

## 1.3 `invert_wealth_to_population` — reproduced from the heap

`class-dynamics.rst:305-314` specifies the function and gives worked answers (90.1% owns the bottom third;
1.6% the top; 8.3% the middle) without stating the within-class density assumption. It can be recovered
exactly, because the four class shares *are* the four knot points of the cumulative distribution, and the
answers come out only for **piecewise-linear in population** (uniform within-class density). At 2024Q4 the
curve is $(0,0) \to (50, 2.5) \to (90, 32.6) \to (99, 69.0) \to (100, 100)$, with

$$x(y) = x_i + (x_{i+1}-x_i)\cdot\frac{y - y_i}{y_{i+1}-y_i}$$

| Target | Computation | Result | doc says |
|---|---|---|---|
| pop owning bottom third | $90 + 9\cdot\frac{33.333-32.6}{69.0-32.6}$ | **90.18%** | 90.1% ✓ |
| pop owning top third | $100 - \left(90 + 9\cdot\frac{66.667-32.6}{69.0-32.6}\right)$ | **1.57%** | 1.6% ✓ |
| middle third (residual) | $98.43 - 90.18$ | **8.25%** | 8.3% ✓ |

All three reproduce to one decimal from the heap plus one assumption — **and that assumption is the open
item.** The BSL Architecture Standard records it as audit Q3: "within-class wealth distribution (canonical
form OPEN — audit Q3)" (`ai/bsl-architecture-standard.md:548`), alongside OQ-1e: "a population measure is
not among A0's enumerated G-members" (`:600-602`). So the function does double duty:

- **Empirically** it is a *falsification test for the canonical within-class form*. Uniform density
  reproduces the published inversion to 0.1 pp; Pareto and lognormal will not unless calibrated to the
  same knots. The three numbers in `class-dynamics.rst` are evidence *for* the polynomial reading and
  should be frozen as a conformance vector rather than left as prose.
- **Formally** it is a **measure over a population against a threshold** — precisely ADR173's ruled
  formulation for $P(S\mid A)$: "the measure of class members whose wealth clears subsistence; the S-curve
  is read off the within-class wealth distribution; `steepness_k` ceases to exist as a knob."

One operation answers both open questions. The class boundary is not a stored label; it is the inverse
image of a wealth target under the population measure. Change the distribution and the boundary moves,
because it was never stored.

## 1.4 The restoring force, measured — and its contradiction

The obvious model is a linear spring, $\Delta W = -\kappa(W-\bar W)$. Regressing the heap's quarterly
differences on the deviation from the mean, Top 1% over 59 observations:

$$\kappa = 0.0745\ \text{per quarter},\qquad \bar W = 30.136,\qquad \sigma_W = 0.684$$

a half-life of about **nine quarters**. Now look at what happened:

| Quarter | Top 1% | Δ | Quarter | Top 1% | Δ |
|---|---|---|---|---|---|
| 2019Q4 | 30.6 | — | 2020Q3 | 30.0 | +0.1 |
| **2020Q1** | **29.2** | **−1.4** | 2020Q4 | 30.6 | +0.6 |
| 2020Q2 | 29.9 | +0.7 | 2021Q1 | 30.7 | +0.1 |

Full recovery in **three** quarters — three times faster than the fitted linear force predicts.
`class-dynamics.rst:421-431` is right about the outcome ("the system restored homeostasis") and wrong
about the mechanism it implies ("rapid return to equilibrium demonstrates the structural nature").

The honest reading is stronger and it is what matters for gameplay:

1. The **−1.4 pp shock was a valuation event**, not a redistribution event. Equities collapsed; claims on
   future surplus were marked down; the *underlying* claims did not change hands. Asset prices reflated on
   liquidity support; the measured share reflated with them.
2. So **the return was not the spring pulling the state back; it was the measurement undoing a paper
   loss.** The linear $\kappa$ is small *because* the underlying distribution barely moves.
3. The system therefore has **two dynamics at different speeds**: slow weak drift in real claims
   ($\kappa \approx 0.07$/q) and fast strong oscillation in fictitious valuation. Marx names the second —
   *Capital* III ch. 25, "Credit and Fictitious Capital". The Market Scissors is that gap.

A single $\kappa$ cannot represent both. Neither can a sigmoid. **Only a coupled system with two state
variables — real value and its fictitious claim — reproduces a 1.4-point shock fully absorbed in three
quarters while the fifteen-year band stays 2.9 points wide.** That is the empirical case for Part III.

## 1.5 What the partition licenses

Not a class definition. A **quotient of the wealth measure**, implemented as one: store a **distribution**
$F_t(w)$ per class (or per member where resolution allows), never a class membership plus a wealth
average; the three wealth-third boundaries are targets `33.333`, `66.667` on the *wealth* axis; the
**population** percentile owning each third is a *projection*, recomputed every tick. The four Marxian
classes are then two readings of the same $F_t$ — the FRED percentile cuts (1/9/40/50) and the
wealth-thirds inversion. When they disagree, the disagreement is the story, and it is legible: *"the
professional-managerial buffer is thinning."* `invert_wealth_to_population` becomes a runtime projection
rather than a one-off analysis script.

---

# Part II — Inventory of magic numbers to kill

| # | Site | The number | Why it is a magic number | State snapshot that replaces it |
|---|---|---|---|---|
| 1 | `SurvivalDefines.steepness_k = 10.0` (frozen reference estate, `p27-python-freeze`; ADR173's named subject) | sigmoid sharpness | **Already killed**, ADR173(1): "steepness becomes the class's actual wealth dispersion" | $\frac{1}{N}\sum_i \mathbf{1}[w_i \ge s]$ |
| 2 | `formulas.rst:193` $k$ = "curve steepness" | generic $k$ | imposed logistic, live doc survivor | same as #1 |
| 3 | `theoretical-foundations.rst:174` $k_{steep}$ | sigmoid scale | same form, different live doc | same as #1 |
| 4 | `theoretical-foundations.rst:151` $\gamma = 0.1$ "routing efficiency" | 0.1 | fixes how much agitation routes to class vs national consciousness — the *ratio* is the mechanic and the constant smuggles the answer | $\sigma$ = measured SOLIDARITY weight / total edge weight; routing is $\sigma$ and $1-\sigma$ |
| 5 | defines key `θ.behavioral.loss_aversion_lambda` | 2.25 | imported behavioural-economics *shape* (`THE_FORMALISM.md:800`) | measured loss ÷ measured surplus claim: $\Delta w / w$ |
| 6 | `dpd-lifecycle-circuit.rst:78-86` legitimation weights 0.35/0.30/0.20/0.10/0.05 | five weights | a hand-weighted sum *is* a stipulated response shape | five frontier quantities; the index is the measure of $D'$ members clearing subsistence |
| 7 | `dpd-lifecycle-circuit.rst:92-99` CRISIS<0.3, UNSTABLE<0.5 | 0.3, 0.5 | two fiat cut points decide a regime | which side of $P(S\mid R) > P(S\mid A)$ the county sits on |
| 8 | `class-dynamics.rst:153-158` $\alpha_{21} = 0.0006$ | 6e-4/q | linear extraction rate fitted to a *linear ODE the author chose*; the form is the assumption | measured flow $2\to1$ ÷ measured $W_2$ |
| 9 | `class-dynamics.rst:169-177` $\delta_{1..3}$ | 1e-3…2e-3 | same; taxation is a *policy rate* the player sets | observed receipts ÷ observed class wealth |
| 10 | `class-dynamics.rst:186-188` $\gamma_3 = 0.0057$ | 5.7e-3/q | **this is $\Phi$ wearing a scalar**; freezing it makes the late game impossible | $\Phi = W_c/V_c - 1$ from wages and value produced |
| 11 | `class-dynamics.rst:207-225` $W^\ast$ ×4 | 0.305…0.020 | stored derived quantity (II.2), and off the series mean (§1.1) | delete; the attractor is an *output* |
| 12 | `class-dynamics.rst:283-292` `damping=-0.1, frequency=0.05` | −0.1, 0.05 | pure stipulation, and the function needs a target equilibrium — so it also violates #11 | momentum from consecutive measured shares; no frequency |
| 13 | `class-dynamics.rst:261-272` `resistance` default 0.0 | 0.0 | consciousness as a free scalar | organizational stock ÷ repression capacity |
| 14 | `Babylon*.csv` `Extraction_Coefficient_Alpha (Inferred)`, `$1.8T to $2.1T` | 0.15, ranges-as-text | hand-built calibration tables mixing numbers, ranges and prose; not parseable, not observed | the offline deduction step (§3.8), never the runtime |
| 15 | `defines.toml` `[process]`, `[template]` | batch sizes, labour hours, masses | **legitimate** — designed masses and counts, declared `EVIDENCE_CLASS = "Designed"` | keep as-is |

Rows 1–3 are ruled. Rows 4–13 will bite at Gate 4 and 5, because they sit in the social layer not yet
ported. Row 14 is a caution. Row 15 is the positive example, and it is worth naming why: **`defines.toml`
is legitimate because every value answers "what is in the world?", not "how strongly does the world
respond?"**

## The one-line filter

> **A magic number answers *how strongly*. A state snapshot answers *what is*.**
>
> If it can be written as (measured numerator) ÷ (measured denominator) on the same period-$t$ snapshot,
> it is a state snapshot wearing a costume and must be recomputed each tick.
>
> If it cannot, ask whether it expresses **tempo** (a duration, a count, a mass, a rate the *player* sets).
> If yes, declare it Designed. If no, it is a shape, and shapes are banned.

Run that filter over `class-dynamics.rst` and eleven of fourteen defaults die. Run it over `defines.toml`
and none do. That asymmetry is the whole test.

---

# Part III — The coupled difference system

Babylon's tick is a Picard iteration, $W_{n+1} = T(W_n)$ (`bsl-architecture-standard.md:658`: "a tick IS
one iteration"). So this is a **difference** system; $\Delta t = 28$ days, exactly. Everything below is a
per-period map so it lands on the engine's shape.

**State vector, all integers.** $K$ advanced constant capital (`material-circuit/src/valuation/`); $V$
variable capital as wages (`src/payments/`, `src/recurring/firms.rs`); $s$ surplus value $=$ gross output
$-(K\ \text{used}+V)$; $H$ labour hours (`fact_productivity_annual.hours_worked_millions`); $N_i, W_i$
class population and wealth (`fact_fred_wealth_levels`, `view_class_composition`); $O$ organizational
stock (graph: org nodes + SOLIDARITY edges); $R$ repression capacity (`fact_coercive_infrastructure`);
$d$ ERDI ratio (`fact_hickel_erdi_annual.erdi`, `view_unequal_exchange`); $\alpha$ the core's share of the
drain (`fact_hickel_erdi_annual.alpha`); $X$ periphery exports to core (`fact_trade_monthly`).

## 3.1 Organic composition and the profit rate, with its own counter-tendencies

Marx's ch. 13 derivation is already a difference equation; he writes it as a table:

> "If c = 50, and v = 100, then p′ = 100/150 = 66⅔%; c = 100, and v = 100, then p′ = 100/200 = 50%;
> c = 200, and v = 100, then p′ = 100/300 = 33⅓% …" — *Capital* III, ch. XIII

$$q_t \equiv \frac{K_t}{V_t},\qquad e_t \equiv \frac{s_t}{V_t},\qquad r_t = \frac{s_t}{K_t+V_t} = \frac{e_t}{q_t+1}$$

The fall is a *tendency*, not an outcome, and the counteracting influences are internal to the same
motion: "There must be some counteracting influences at work, which cross and annul the effect of the
general law" (ch. XIV). And, decisively for a game that must not script a decline: "this fall does not
manifest itself in an absolute form, but rather as a tendency toward a progressive fall" (ch. XIII).

So the engine does **not** move $r$ toward a target. It lets $r_t$ be whatever measured $e_t$ and $q_t$
say, and lets the counter-tendencies act through their own material channels:

$$q_{t+1} = q_t\cdot\frac{K_t + I_t}{K_t}\cdot\frac{V_t}{V_t + \Delta V_t},\qquad
e_{t+1} = e_t\cdot\frac{H^{surplus}_{t+1}/H^{necessary}_{t+1}}{H^{surplus}_t/H^{necessary}_t}$$

**Rising intensity of exploitation** (counter-tendency I) is $\Delta e > 0$ from a longer or denser period
— a measured hours ratio. **Cheapening of constant capital** is $I_t$ buying more $K$ per unit value — a
measured price index. **The reserve army** is not a wage-pressure coefficient; it is $\Delta V$ limited by
$\min(\text{employed}, \text{reserve})$ in the staffing model, already integer.

`THE_FORMALISM.md:808-810` already states the non-axiom: "The algebra deliberately contains no
stable-rate-of-profit axiom: $r$'s trajectory is a derived observable of tendency and counter-tendencies in
interaction." Equation 1 is that sentence written out. **No $\kappa$, no target, no half-life.**

## 3.2 Department I / Department II as a balance condition

$$D_I:\ (K,V) \to K',\qquad D_{II}:\ (K,V) \to C,\qquad K'_{t+1} = s_{I,t} + s_{II,t}$$

Investment goods must be *bought* out of surplus value, so reproduction is a **conservation check that can
fail loudly**, not a smoothing term. When $s_I + s_{II}$ exceeds what $D_I$ can deliver, the engine reports
a disproportionality rather than damping it. That is the crisis channel, and it is `AuditReceipt`-shaped: a
flow with no row is an error.

## 3.3 Unequal exchange, straight from Köhler / Hickel / Amin

> "His formula is as follows: $T = d*X - X$ … $T$ = value transferred through unequal exchange; $X$ =
> exports from periphery to core; $d$ = the ratio of the peripheral country's ERDI to the core country's
> ERDI." — Hickel et al., *Plunder in the Post-Colonial Era* (2021), p. 4

$$T_t = X_t\,(d_t - 1),\qquad d_t = \frac{\text{ERDI}_{periphery,t}}{\text{ERDI}_{core,t}}$$

**Two measured price levels, one subtraction, one multiplication.** No coefficient. The heap carries both:

```
fact_hickel_erdi_annual
scale_type                  | n  | y0   | y1   | ERDI min | ERDI max
Extensive                   | 20 | 1960 | 1979 | 3.20     | 3.99
Intensive                   | 37 | 1980 | 2017 | 2.40     | 8.38
Intensive_China_Inflection  |  1 | 2005 | 2005 | 6.80     | 6.80
```

with `annual_drain_usd_billions` (2000 → 13000), `alpha` (0.2981 → 0.8401), `core_gain_per_capita_usd`
(2500 → 15000) on anchor years. Cross-check against the trade heap (`view_unequal_exchange`, 44,808 rows
in `fact_trade_monthly`): core 0.238 (2010) → 0.411 (2020); semi-periphery 0.828 → 0.977; periphery 0.509
→ 0.637.

Amin supplies the reason the ratio is the right object — and the reason Φ must be a defect, not a subsidy:

> "…though there exists but one sole value of labor-power on the scale of globalized capitalism, that
> labor-power is nonetheless recompensed at very different rates. … the amplitude of the transfer of value
> from the peripheries to the centers: a transfer that is hidden behind the observed price and wage
> system." — *The Law of Worldwide Value* (2010), ch. 4

One value, many prices. The difference is the flow. **Φ is that difference, not a parameter.**

## 3.4 Imperial rent into the labor aristocracy, and the MIM boundary

Here two literatures snap together, closely enough that it should be a design ruling. MIM's definition of
the stratum is *not* an income cut: "we can clearly see that the working class is paid much more than they
need to eke out their survival as a class. … the labor aristocracy is paid more than the value of their
labor power" (MIM Theory **10**, *The Labor Aristocracy*, 1996), with the material source named in the
resolution: "The recognition of superprofits extracted from the oppressed nations as a central fact of
economic life in the imperialist countries." So the boundary is **members whose wage exceeds the value of
their labour-power**, funded by superprofits. As a state snapshot:

$$\Phi_t = \frac{W_{c,t}}{V_{c,t}} - 1,\qquad a_t = \frac{1}{N}\sum_i \mathbf{1}\left[w_{i,t} > v_{i,t}\right]$$

Read that beside ADR173's ruled formulation and the two are the same operation with different thresholds:

| | threshold | measure | who it separates |
|---|---|---|---|
| ADR173 $P(S\mid A)$ | subsistence $s$ | $\frac{1}{N}\sum \mathbf{1}[w_i \ge s]$ | acquiescence vs. rupture |
| MIM aristocracy | value of labour-power $v$ | $\frac{1}{N}\sum \mathbf{1}[w_i > v_i]$ | bribed stratum vs. proletariat |

**One primitive operation, two thresholds, two of the game's central questions.** This is the single most
useful finding in this sweep: Babylon does not need a "labor aristocracy mechanic." It needs the measure,
and then two cut points on it. The S-curve at each cut point is the CDF of the within-class distribution —
a theorem, not a stipulation. The dynamics follow without a coefficient:

$$\Phi_{t+1} = \Phi_t\cdot\frac{1 + \alpha_t\,T_t / Y_{c,t}}{1 + g_{c,t}}$$

$\alpha_t$ measured (heap: 0.30 → 0.84, rising), $T_t$ from §3.3, $g_{c,t}$ core output growth. **Φ has no
natural decay** — `07` already ruled this ("maintained by borders, repression, and a service stratum").
Here the ruling falls out of the algebra: nothing reduces Φ except losing the drain.

## 3.5 Fictitious capital, and why 2020 snapped back in three quarters

The two-speed problem needs a second state variable. Marx supplies it: value and its claim.

$$V^{real}_{t+1} = V^{real}_t + s_t,\qquad
V^{fic}_{t+1} = V^{fic}_t\left(1 + \rho_t\right) - \text{realisation}_t$$

$\rho_t$ is the measured rate of change of asset prices; $\text{realisation}_t$ is the portion of the claim
actually converted into value. The **Market Scissors** is $V^{fic}/V^{real}$. This makes §1.4 legible:
2020Q1 $\rho$ collapses, $V^{fic}$ falls ~1.4/30 of the measured share, $V^{real}$ unchanged; 2020Q2–Q4
liquidity support restores $\rho$, $V^{fic}$ reflates, the measured share returns; 2022Q2 $\rho$ falls
again (−1.0 pp), partially recovers.

**The measured Top-1% share is a reading of $V^{fic}$, not of $V^{real}$.** The band's tightness (SD 0.68
pp) is the tightness of the *scissors gap*, not of the underlying appropriation. That distinction is the
difference between a game that teaches something and a game that shows a wiggly line.

## 3.6 The wealth flow, with conservation and no stipulated exponent

$$W_{i,t+1} = W_{i,t} + \sum_j f_{j\to i,t} - \sum_j f_{i\to j,t} + \Phi_{i,t},
\qquad \sum_i W_i = \text{total wealth, exactly, every tick}$$

The distribution's *shape* — the gamma/Pareto split of §1.2 — is then an output. If it does not emerge, the
flows are wrong, and that is a bug with a name, not a tuning problem.

**This is where Babylon improves on the heap's ODE.** `class-dynamics.rst:131-136` writes
$\frac{dW_1}{dt} = \alpha_{41}W_4 + \alpha_{31}W_3 + \alpha_{21}W_2 - \delta_1 W_1$ and then fits **five of
those $\alpha$'s to zero** (`:153-158`, "Other extraction rates (negligible)"). That is the model reporting
the flows do not exist in the data — and rather than conclude anything, the doc keeps the terms with a zero
coefficient. A zero-fitted parameter is a claim the mechanism is absent. Delete the term, or find the flow.

## 3.7 The crossover, already a pure ratio

$$P(S\mid R)_t = \frac{O_t}{R_t},\qquad P(S\mid A)_t = \frac{1}{N}\sum_i \mathbf{1}\left[w_{i,t} \ge s_{i,t}\right]$$

Rupture fires when the left exceeds the right. Neither side has a coefficient; both are snapshots. The whole
"revolution probability" apparatus collapses to a comparison of two measured quantities, and the Warsaw
Ghetto corollary (`THE_FORMALISM.md:530-532`) is automatic: when the measure on the right goes to zero,
*any* positive organization wins.

## 3.8 What is primitive, and why the runtime needs no Spark cluster

Nothing above is a mathematical primitive. The dialectic $D=(A,\bar A,w,T,\sigma)$ is untouched; every
operation is `+ − × ÷`, comparison, `min`/`max`, and a fold over a population; the only constants are `0`,
`1`, exact integers. The S-curves appear at the *outputs* of §3.4 and §3.7, read off a CDF —
ADR173-compliant by construction: "the S-curve is derived as a THEOREM from within-class wealth dispersion
integrated against the threshold." So the answer to "does this need an amendment?" is **no**. It needs
content, and it needs the per-family Director review ADR175 requires for the bifurcation,
reactionary-defection, reserve-army and wealth-spring families.

The 8.8 GB heap is an **offline deduction instrument**, and the constitution already provides the
consumption pattern: `defines.toml` captures typed parameters per campaign. Two rules keep it honest.
**Ship observations, not fits** — if a coefficient is needed at runtime, prefer the *distribution* (a table)
over the *number* (a fit); a table can be re-integrated against a different threshold, a fit cannot.
**Capture, then freeze, then declare** — a campaign records its `defines_hash` and parameter snapshot, and
the offline fit is `Calibrated` or `Derived` on that campaign, never `Observed` unless it is a direct
transcription. The `Babylon*.csv` files are the negative example: `"Extraction_Coefficient_Alpha
(Inferred)": 0.15` and `"$1.8T to $2.1T (Annualized)"` are ranges-as-strings in a numeric column. Sourcing
leads, never runtime parameters.

---

# Part IV — Chaos: why the reform gets eaten, and what the player has to find

## 4.1 Statistical equilibrium is why reform loses

Cottrell et al. p. 143 again, but read as a *mechanic*: "Over time the distribution of wealth in the economy
converges to an exponential distribution, and stays there. Even though the individual economic actors
continue to exchange money, and ascend or descend the wealth scale, the overall distribution of wealth in
the economy remains constant. Some poor people may get rich, some rich people get poorer, but the overall
situation remains the same."

That is the precise form of the thing the player will hate and learn from. Not "the rich are always rich."
Rather: **the churn is real, the mobility is real, and the distribution is unmoved.** A reform that lets some
poor people get rich has changed nothing. A reform that changes the *exchange rule* has changed everything.
Babylon can therefore show what no other game can: **the player made a difference to individuals and no
difference to the distribution, and the ticker says so honestly.** `MaterialReplaySession` carries both the
flow rows and the distribution summary, so the disappointment is auditable rather than narrated.

## 4.2 The Q1→Q4 2020 sequence, read correctly

`class-dynamics.rst` calls it a natural experiment and reads it as proof concentration "cannot be reformed
away." The conclusion is right; the inference is wrong, and the difference matters because it tells us
*which* reform can work.

What it proves: a 1.4-point downward shock to the measured share was fully absorbed in three quarters, with
no tax, transfer, or expropriation. What it does *not* prove: that the system resists redistribution.
Nobody redistributed. Asset prices fell and rose. What it does prove is the design-relevant part: **the
restoring force the player feels first is a valuation force — strong, fast, and purely symbolic.** The
player will spend political capital, see the number snap back, and conclude the game is rigged. The engine
must be able to explain *why* it snapped back — the $V^{fic}$ channel — or the game teaches cynicism instead
of political economy.

## 4.3 Basins: locally stable, not globally stable

> "In the range $r_s < r < 0$, two qualitatively different stable states coexist … The initial condition
> $x_0$ determines which fixed point is approached as $t \to \infty$. One consequence is that the origin is
> stable to small perturbations, but not to large ones — in this sense the origin is locally stable, but
> not globally stable." — Strogatz, §3.4

And hysteresis, which is the late game: "the state remains at the origin until $r = 0$, when the origin
loses stability. Now the slightest nudge will cause the state to jump to one of the large-amplitude
branches. … If $r$ is now decreased, the state remains on the large-amplitude branch, even when $r$ is
decreased below 0! … This lack of reversibility as a parameter is varied is called hysteresis" (§3.4).

**§1.2 is an instance of this, and it is the strongest empirical support in the sweep.** The Top-1% share
sat in the small-amplitude basin for fifteen years. The 90–99% tier did not: it held a plateau, then stepped
3.3 pp across 2020–2022 and settled at a new level. That is a jump to a different branch with no return, and
it happened without any legislation — which means the engine will have to produce it from the flow equations
alone or admit it cannot.

Two consequences, and they are the two halves of "why is this electrifying":

1. **The invisible wall.** A push that stays inside the basin is *absorbed*, proportionally to how small it
   was. Not a penalty mechanic — the actual structure of the object being simulated. The player must learn
   that the way to move a homeostatic system is to move the *parameter*, not the state.
2. **You cannot un-revolution.** Once the jump happens, restoring the parameter does not restore the old
   equilibrium. Sharper still for the subcritical Hopf case: "once large-amplitude oscillations have begun,
   they cannot be turned off by bringing $\mu$ back to zero. In fact, the large oscillations will persist
   until $\mu = -1/4$" (§8.2). A player who wanted a reform and got a revolution does not get to go back.
   That is a *rule with a citation*, not an authored script.

## 4.4 Where Babylon's bifurcation boundary actually is

Strogatz's cusp catastrophe needs **two** control parameters, and it is the right picture because it
produces three regimes from one surface: "saddle-node bifurcations occur all along the boundary of the
regions, except at the cusp point, where we have a codimension-2 bifurcation" (§3.6). Babylon's two
parameters are already in the equation set: $r \equiv \Phi_t$, the imperial-rent gap (§3.4), and
$h \equiv O_t/R_t$, the correlation of forces (§3.7). Both are state snapshots, both measured. Put them on
two axes and the cusp surface is the game's political phase diagram — **and it is not authored.** It falls
out of the two equations already required.

| region | $(r,h)$ | behaviour | historically-loaded case |
|---|---|---|---|
| stable reproduction | high $\Phi$, low $O/R$ | small pushes absorbed; T-6 forward-invariant | the ordinary imperial-core period |
| crisis, no organization | falling $\Phi$, low $O/R$ | agitation with no class channel — routes to national identity | T-7's fascist pole |
| crisis with organization | falling $\Phi$, high $O/R$ | rupture | T-7's revolutionary pole |

`THE_FORMALISM.md:527` states the first row as **T-6** and the third as **T-7**, with the routing sign set
by "the consciousness-weighted solidarity topology across the principal contradiction axis." Strogatz §3.6
supplies the geometry that makes T-6 and T-7 *the same surface* rather than two mechanisms. That is what the
formalism has been missing: T-6 and T-7 read as separate theorems; they are two regions of one cusp. **Do
not script the regions.** 1905, 1917, 1933 are not three points the engine must visit. They are three
*addresses* on a surface the engine computes, and the interesting game is that a fourth address exists.

## 4.5 Critical slowing down: the tell the player can learn to read

Strogatz names the diagnostic — "it is called critical slowing down" (§2.4), a "signature of a second-order
phase transition" (§2.4.9). Because the engine measures recovery time from its own state transitions,
**critical slowing down is free.** No new mechanic. A player who watches how fast a shock is absorbed learns
where they are on the surface — not from a UI gauge, but from the behaviour of the thing itself. That is the
difference between a game with a "revolution meter" and a game where you can feel the ground getting soft.

## 4.6 What would falsify all of this

1. **The Top-1% share is homeostatic; the class structure is not.** Falsified if a 15-year window shows a
   monotone trend in all four shares, or if band width exceeds within-window drift. Heap: Top 1% SD 0.68 pp
   against a 2.9 pp range — holds — while 90–99% steps down 3.3 pp across 2020–2022 (§1.2). The aggregate is
   stationary; the composition is not.
2. **The restoring force is nonlinear.** Falsified if a linear $\Delta W = -\kappa(W-\bar W)$ predicts the
   2020 recovery. It does not: 9-quarter half-life vs 3-quarter observed. The two-variable model is
   *required*, not preferred.
3. **The inversion needs only the four knot points.** Falsified if Pareto or lognormal is needed to
   reproduce 90.1/8.3/1.6. Uniform reproduces them to 0.1 pp. Two of three forms are excluded by the
   published numbers — a result, not a preference.
4. **The MIM boundary and the ADR173 boundary are one operation.** Falsified if a mechanic needs a threshold
   that is neither a subsistence requirement nor a value-of-labour-power. None of the fourteen rows in
   Part II needs one.
5. **No α survives.** Falsified if any term in §3.6 needs a nonzero fitted coefficient after the flows are
   measured. Five α's currently fitted to zero is evidence the flows are unmeasured in the reference data,
   not that they are absent.

---

# Part V — Rulings proposed, open questions, and heap defects found

## 5.1 Proposed rulings

1. **Class membership is never stored.** It is a measure over $F_t$ against a threshold; the four FRED tiers
   and the three wealth-thirds are two readings of the same measure.
2. **Every social-layer coefficient is recomputed per tick from the snapshot**, or it does not exist. Apply
   the Part II filter to `class-dynamics.rst`, the defines registry (`θ.behavioral.*`, `θ.survival.*`) and
   `dpd-lifecycle-circuit.rst` before Gate 4 lands.
3. **Freeze `invert_wealth_to_population`'s three answers as a conformance vector** (90.1 / 8.3 / 1.6),
   recording that they discriminate between within-class forms — converting audit Q3 from an open design
   question into a testable one.
4. **Retire `steepness_k`'s three doc survivors** (`formulas.rst:193`, `theoretical-foundations.rst:174`,
   `:206`). ADR173 killed the knob in code; the docs still teach it.
5. **Delete the $W^\ast$ block from `class-dynamics.rst`** — four stored equilibria, three off the heap's own
   mean, is a II.2 violation with a measurement error on top.
6. **T-6 and T-7 are one cusp surface**, parameterised by $(\Phi,\ O/R)$ — the largest architectural win
   available in the political layer, needing no amendment, only the observation that both parameters are
   already required.
7. **$\Phi$ enters as a defect, never as a coefficient.** `γ₃ = 0.0057` is Φ in disguise.

## 5.2 Open questions for the porch

- **Which within-class distribution is canonical?** §1.3 shows uniform reproduces the published inversion and
  Pareto/lognormal do not — but uniform is the *least* theoretically motivated choice (no tail). A piecewise
  form, uniform across the bottom 90% and Pareto above, would satisfy Cottrell et al.'s "lognormal with a
  Pareto tail" *and* the 90.1 number, and is strictly better than either pure form.
- **How many state variables does $V^{fic}$ need?** One valuation index, or one per asset class
  (`dim_asset_category`: Total Assets / Real Estate / Net Worth)? Real estate and equities reflate on
  different schedules, and 2020 is an equity story.
- **Does the cusp's $h$ axis need a third dimension for legitimacy?** If T-7's solidarity topology is a third
  parameter the surface becomes a swallowtail, and the fascist region gets its own boundary rather than
  sharing one.
- **What is the tick-level granularity of $F_t(w)$?** Per-member wealth is honest and expensive; per-class
  with a stored shape parameter is cheap and reintroduces a magic number by the back door.
- **Does 2010–2024 contain a second basin?** §1.2: the 90–99% tier plateaus at ~39.3 (2012–2019), steps
  down 3.3 pp across 2020–2022, then plateaus at 36.4. That is a *discrete* level change, not drift — the
  signature of a basin shift, not a restoring force. If the engine can reproduce a step of that shape from
  the flow equations alone, the emergence claim is strong; if it can only produce it with a fitted
  coefficient, the claim is broken and we should say so.

## 5.3 Heap defects found during this sweep

Each is reproducible with `sqlite3 -readonly`.

1. **`view_rent_crisis.annual_rent_to_income_ratio` is integer division and returns 0 for every row.**
   Columns are declared `NUMERIC(8,2)`/`NUMERIC(10,2)` but stored with integer affinity, so
   `(fr.median_rent_usd * 12) / fi.median_income_usd` truncates. Wayne County: rent 759, income 26888 →
   correct ratio **0.3387**, view returns **0**. Any Gate 4 mechanic reading this view gets a confident "no
   rent crisis." Fix: `* 12.0` or an explicit `CAST`.
2. **`view_imperial_rent` and `view_surplus_value` return zero rows.** Both depend on
   `fact_productivity_annual`, which has **0 rows**. The views exist and are named in the brief; they are
   unpopulated. The imperial-rent formula must come from another source (BEA IO coefficients have 105,448
   rows; `fact_bea_final_demand_annual` exists) or the views must be retired.
3. **`view_class_composition` sums across ACS source vintages.** Wayne County reports "proletariat
   16,147,580" by summing every 5-year vintage. The deduplicated structure (proletariat / state_worker /
   petty_bourgeois / unpaid_labor) is correct; the magnitudes are not headcounts. Consumers must group by
   `source_id`.
4. **`fact_fred_wealth_shares` starts at 2010Q1, not 1960.** `dim_time` spans 1960–2024 and
   `fact_fred_national` has 1,395 rows, but the wealth table has 60 quarters. "15 years" is supported; longer
   wealth history is not.
5. **`fact_hickel_erdi_annual` has a 1990 discontinuity** (ERDI 4.1 in 1980 → 2.4 in 1990 → 5.5 in 1995) and
   `scale_type` changes mid-series (Extensive → Intensive). Any mechanic reading ERDI as continuous inherits
   a 55% artefactual drop. Treat the series as three regimes.

## 5.4 The one-sentence version

> Babylon replaces Paradox's dials with **ratios of the period-$t$ snapshot**; replaces every curve with **a
> measure over a population against a threshold**; and then lets conservation, unequal exchange, and a
> two-parameter cusp produce the 33/33/33/0 attractor, the fast valuation snap-back, and the bifurcation the
> player has to find — none of it authored, all of it falsifiable against an 8.8 GB heap that already
> contains the evidence.

---

## Sources read

**Repository.** `CONSTITUTION.md` (Art. IV, Art. V) · `docs/reference/class-dynamics.rst` (full) ·
`docs/reference/formulas.rst:150-260` · `docs/concepts/dpd-lifecycle-circuit.rst` (full) ·
`docs/commentary/theoretical-foundations.rst:140-200` · `ai/THE_FORMALISM.md:515-535, 780-812` ·
`ai/bsl-architecture-standard.md:500-680` (emergence diagram, ADR173/ADR175 posture) ·
`ai/decisions/ADR173_...yaml`, `ADR175_...yaml` · `content/scenarios/michigan/defines.toml` (full) ·
`content/scenarios/*/*.bsl` (4 files, 44 lines) · `rust/crates/babylon-bsl/src/` and
`rust/crates/babylon-material-circuit/src/` (no sigmoid; no social dynamics yet) ·
`docs/gameplay/research/07`, `12` (non-duplication).

**Heap.** `/media/user/data/marxist-data-3NF.sqlite`, read-only: `fact_fred_wealth_shares`,
`fact_fred_wealth_levels`, `dim_wealth_class`, `dim_asset_category`, `dim_time`,
`view_wealth_concentration`, `fact_hickel_erdi_annual`, `view_imperial_rent`, `view_surplus_value`,
`view_unequal_exchange`, `view_class_composition`, `view_rent_crisis`, `dim_country` (world_system_tier: 27
core / 35 semi-periphery / 189 periphery), `fact_trade_monthly`, `fact_census_worker_class`,
`fact_census_rent`, `fact_census_median_income`, `fact_productivity_annual` (0 rows),
`fact_census_rent_burden`, `dim_county`. §1 and §5.3 figures recomputed from it.

**Books.** Marx, *Capital* III — ch. XIII ("The Law As Such": the $c/v$ table and the tendency), ch. XIV
("Counteracting Influences"), ch. XXV (credit and fictitious capital) · Marx, *Mathematical Manuscripts* —
`babylon_books/math/marx-math-manuscripts.pdf` is a **page-image scan with no text layer** (`pdftotext` →
157 bytes), so it is cited only for its standing argument that the derivative is the trace of a *process* of
change, never for a quotation · Amin, *The Law of Worldwide Value*, ch. 4 · Hickel et al., *Plunder in the
Post-Colonial Era* (2021) — Köhler's $T=dX-X$, ERDI, \$62tn aggregate, \$2.2tn in 2017, Cope's \$2.8tn for
2010 · Hickel 2020 = the **SDI** paper, *Ecological Economics* 167:106331 — a *different* paper from the
drain paper, noted so the porch does not mis-cite · Cottrell, Cockshott & Michaelson, *Classical
Econophysics* (2009) pp. 141–143, 290–291, Appendix D · Farjoun & Machover, *Laws of Chaos* (1983) pp.
53–54, 68 · Strogatz, *Nonlinear Dynamics and Chaos*, 3rd ed. §2.4.9, §3.4, §3.6, §8.2 · MIM Theory **10**,
*The Labor Aristocracy* (1996) — the resolution's four preconditions and the "paid above the value of its
labour power" definition · Emmanuel, *Unequal Exchange* and Cope, *Divided World, Divided Class* — read via
`07` and via Hickel's citation of Cope p. 81.

**Not read, load-bearing.** `mt1.pdf` (*A White Proletariat?*) is a scan with no text layer. `Capital` Vol.
I and the Grundrisse are available at `/media/user/data/old-hdd/old-hdd/prolewiki/Exports/Library/` but were
not needed here. No quotation above is attributed to a file that was not opened.
