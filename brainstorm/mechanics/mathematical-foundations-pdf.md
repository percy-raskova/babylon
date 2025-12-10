---
title: "The Fall of AmeriKKKa"
subtitle: "MLM-TW as Differential Equations"
date: "Persephone Raskova\\newline\\newline December 2025"
titlepage: true
titlepage-color: "1a0000"
titlepage-text-color: "c0c0c0"
titlepage-rule-color: "ffd700"
titlepage-rule-height: 4
toc: true
toc-own-page: true
numbersections: true
colorlinks: true
linkcolor: red
urlcolor: blue
header-left: "The Fall of AmeriKKKa"
header-right: "\\thepage"
---

\newpage

> *"The philosophers have only interpreted the world, in various ways. The point, however, is to change it."*
>
> --- Karl Marx, *Theses on Feuerbach* (1845)

\vspace{1em}

# Is Class Struggle Bananas?

You might be wondering: what the hell is a "simulation engine" doing with differential equations about class struggle? Can you really reduce the messy, bloody, beautiful chaos of human history to a bunch of formulas?

The short answer is: yes, absolutely. And if that sounds reductive or mechanical to you, I'd ask you to reconsider.

When we calculated that a single hour of core labor purchases 68 hours of periphery labor on a Honduran banana plantation, that wasn't philosophy. That was arithmetic. When we showed that the "fair" price of a pound of bananas would be $11.10 instead of 63 cents, that was just following the math where it leads. The exploitation isn't hidden in some mystical superstructure --- **it's encoded in the very prices we pay at the grocery store**.

The Babylon simulation engine is an attempt to take this insight seriously. What if we actually modeled the material conditions that produce revolution? Not as vibes, not as "historical forces" in the abstract, but as **concrete mathematical relationships** that can be computed, verified, and tested against historical reality?

This document provides the complete formal treatment of the 14 mathematical formulas that govern the simulation. We organize them into five theoretical domains:

1. **The Fundamental Theorem of MLM-TW** --- Imperial rent and the labor aristocracy
2. **Consciousness Dynamics** --- How ideology actually evolves
3. **Survival Calculus** --- Why revolution is sometimes rational
4. **Unequal Exchange** --- The value transfer mechanisms of imperialism
5. **System Dynamics** --- Tension, solidarity, and bourgeois decision-making

\newpage

# Part I: The Fundamental Theorem

## Imperial Rent: Where the Money Actually Goes

Let me be blunt about something: **the labor aristocracy is not about "treats."** Every time some terminally online pseudo-leftist reduces this concept to "you have an iPhone, hypocrite," they're missing the entire point. The labor aristocracy is about the **distribution of labor-power** and what it's geared towards.

Consider what Engels observed way back in 1858:

> *"The English proletariat is actually becoming more and more bourgeois, so that this most bourgeois of all nations is apparently aiming ultimately at the possession of a bourgeois aristocracy and a bourgeois proletariat alongside the bourgeoisie. For a nation which exploits the whole world this is of course to a certain extent justifiable."*
>
> --- Friedrich Engels, Letter to Marx, October 7, 1858

Engels' "bourgeois proletariat" is precisely what we mean by a labor aristocracy. And the mechanism by which this bourgeoisification occurs is **Imperial Rent** ($\Phi$).

> **Definition: Imperial Rent**
>
> **Imperial Rent** ($\Phi$) is the value extracted from the periphery that flows to the core, enabling wages to exceed value produced. It is the material foundation of the labor aristocracy.

The imperial rent formula captures the extraction of value from periphery workers:

$$\Phi(W_p, \Psi_p) = \alpha \cdot W_p \cdot (1 - \Psi_p)$$

Where:

- $\Phi$ --- Imperial rent extracted (Currency, $\geq 0$)
- $\alpha$ --- Extraction efficiency coefficient $\in [0, 1]$
- $W_p$ --- Periphery wages / value available for extraction
- $\Psi_p$ --- Periphery consciousness $\in [0, 1]$ (0 = submissive, 1 = revolutionary)

Here's the crucial insight encoded in that formula: **as periphery consciousness rises ($\Psi_p \to 1$), imperial rent collapses ($\Phi \to 0$).** This is the material basis of anti-colonial struggle. Awakened workers resist extraction. This isn't idealism --- it's just what happens when people start organizing.

We saw this in Bolivia with the Cochabamba Water War of 2000 --- when Bechtel privatized the water supply and tripled rates, 50,000 Bolivians voted 95% to terminate the contract, shut down the city with general strikes, and won. We saw it in Vietnam with the resistance, in Palestine right now. The formula captures something real.

**Implementation:** `src/babylon/systems/formulas.py:37-57`

## The Labor Aristocracy Condition: Are You In or Out?

The **Fundamental Theorem of MLM-TW** states something that should be obvious but somehow isn't:

$$\text{Revolution in the Core is impossible if } W_c > V_c$$

Where $W_c$ is core wages and $V_c$ is value produced by core workers. The difference is imperial rent.

This is what Wallerstein spent his entire career documenting. The imperialist bourgeoisie say to the first world proletariat: *"Shut up and don't shake things up too much, and we'll provide you with an offshore class of servants to cater to your every whim. They'll be out of sight and out of mind, so you never need to think much about them."* This is the bargain at its core.

The **Labor Aristocracy Ratio** provides a quantitative test:

$$\rho = \frac{W_c}{V_c}$$

> **Definition: Labor Aristocracy**
>
> A worker belongs to the **labor aristocracy** if and only if:
> $$\rho = \frac{W_c}{V_c} > 1$$
>
> That is, they receive more value than they produce. The difference comes from imperial rent extracted from the periphery.

**Binary test function:** `is_labor_aristocracy()` returns `True` when $W_c > V_c$.

Some comrades get very uncomfortable at this point. They start making objections that boil down to: "But surely *I'm* not part of the problem?" To which I respond: being part of the labor aristocracy isn't a moral failing --- it's a material condition. Individual members of any class can consciously choose to align however they want. Marx himself was raised in an upper-middle class household. Engels was a factory-owning bourgeoisie. The question isn't about guilt. The question is about correctly analyzing the situation.

\newpage

# Part II: Consciousness Dynamics

## The Consciousness Differential Equation

Here's where things get interesting. How does consciousness actually change over time? Not vibes, not "the arc of history" --- actual mathematical evolution.

The evolution of consciousness follows a **first-order ordinary differential equation**:

$$\frac{d\Psi_c}{dt} = k\left(1 - \frac{W_c}{V_c}\right) - \lambda\Psi_c + B(\Delta W, \sigma)$$

Let me break this down in plain language:

**Term 1: The Material Term** --- $k(1 - W_c/V_c)$

When wages exceed value produced ($W_c > V_c$), this term is negative. Consciousness decays. Why? Because life is materially comfortable! Revolution is irrational when the rent is low and the bananas are cheap.

When wages fall below value ($W_c < V_c$), this term is positive. Consciousness rises. Material conditions are forcing people to question things.

**Term 2: The Decay Term** --- $-\lambda\Psi_c$

Consciousness naturally regresses without constant material reinforcement. This encodes the ideological weight of the superstructure. Every day, the bourgeoisie are pumping out propaganda designed to shorten attention spans and render critical thinking impossible. This term captures that reality.

**Term 3: The Bifurcation Term** --- $B(\Delta W, \sigma)$

This is the crucial one. It determines *where* crisis energy routes: fascism or revolution.

## The Fascist Bifurcation: Germany 1933 vs. Russia 1917

> **Historical Encoding**
>
> This formula encodes a crucial historical lesson: **Agitation without solidarity produces fascism, not revolution.**
>
> - **Germany 1933:** Falling wages + no internationalist solidarity $\to$ Fascism
> - **Russia 1917:** Falling wages + strong internationalist solidarity $\to$ Revolution

When wages fall ($\Delta W < 0$), **agitation energy** is generated. But here's what the comfortable left keeps getting wrong: that energy doesn't automatically go toward revolution. It goes somewhere --- and where it goes depends on the infrastructure of solidarity.

The agitation energy formula uses the Kahneman-Tversky loss aversion principle:

$$E_{agitation} = |\Delta W| \cdot \lambda_{KT}$$

Where $\lambda_{KT} = 2.25$ is the **loss aversion coefficient** --- losses are perceived as $2.25\times$ more impactful than equivalent gains. This is empirically validated behavioral economics, not ideology.

This energy then **routes** based on solidarity infrastructure:

$$\begin{aligned}
\Delta\Psi_{class} &= E_{agitation} \cdot \sigma \cdot \gamma \\
\Delta\Psi_{national} &= E_{agitation} \cdot (1 - \sigma) \cdot \gamma
\end{aligned}$$

Where:

- $\sigma$ --- Solidarity strength from incoming SOLIDARITY edges $\in [0, 1]$
- $\gamma = 0.1$ --- Routing efficiency constant

**Translation:** When crisis hits and there's no international working-class solidarity ($\sigma = 0$), that agitation energy routes to national identity. Hello, fascism. When solidarity infrastructure exists ($\sigma > 0$), energy routes to class consciousness. Hello, revolution.

This is why building those solidarity networks *before* the crisis hits is so essential. The fascists understand this. Why don't we?

> **The George Jackson Refactor (Sprint 3.4.3)**
>
> Named after the revolutionary theorist, this mechanic replaces scalar ideology with a **multi-dimensional IdeologicalProfile**:
> $$\vec{\Psi} = (\Psi_{class}, \Psi_{national}, E_{agitation})$$

George Jackson understood that consciousness isn't one-dimensional. You can have agitation without class consciousness. You can have national consciousness without revolutionary potential. The vector formulation captures this reality.

\newpage

# Part III: Survival Calculus

## Why Revolution Is Sometimes Rational

Every agent faces a fundamental choice between two survival strategies:

1. **Acquiescence ($A$):** Survive by compliance, accepting exploitation
2. **Revolution ($R$):** Survive through collective action, overthrowing exploitation

The poverty draft thesis fails because it treats soldiers as playthings of circumstance, denying them human agency. But the legionnaire thesis fails because it ignores material conditions entirely. The truth, as always, lies in *dividing one into two* and extracting the kernels of truth from both positions.

The same logic applies here. Revolution isn't irrational. But it's also not *always* rational. It depends on the material conditions.

## The Acquiescence Sigmoid

The probability of survival through acquiescence follows a **logistic sigmoid**:

$$P(S|A) = \frac{1}{1 + e^{-k(x - x_{critical})}}$$

Where:

- $x$ --- Current wealth
- $x_{critical}$ --- Subsistence threshold (the poverty line)
- $k$ --- Steepness parameter (how sharply survival drops near threshold)

**Properties of the Acquiescence Sigmoid:**

| Condition | $P(S|A)$ | Interpretation |
|-----------|----------|----------------|
| $x = x_{critical}$ | 0.5 | Coin flip --- at the edge |
| $x \ll x_{critical}$ | $\to 0$ | Starvation imminent |
| $x \gg x_{critical}$ | $\to 1$ | Comfortable survival |

When you're comfortable, compliance works. When you're starving, compliance means death. The sigmoid captures this gracefully.

## Revolution Probability

The probability of survival through revolution depends on the ratio of organization to repression:

$$P(S|R) = \frac{\text{Cohesion}}{\text{Repression} + \epsilon}$$

Where:

- **Cohesion** = $\text{organization} \times \text{solidarity\_multiplier}$
- **Repression** = State violence capacity $\in [0, 1]$
- $\epsilon = 10^{-6}$ --- Small constant preventing division by zero

This is why organization matters. This is why solidarity matters. They're not just nice words --- they're the numerator in a survival equation.

## The Rupture Condition

> **Definition: Rupture**
>
> A **Rupture Event** occurs when revolution becomes the rational survival strategy:
> $$P(S|R) > P(S|A)$$
>
> This is not an ideological threshold but a **material calculation**: when peaceful compliance means death, resistance becomes logical.

This is the crossover point. The moment when the math says: revolt or die. And here's the thing --- this crossover point can be calculated:

$$x_{crossover} = x_{critical} - \frac{1}{k}\ln\left(\frac{1}{P(S|R)} - 1\right)$$

That's the **critical wealth level** below which revolution is the rational survival strategy.

## Loss Aversion: Why Crises Hit Different

Following Kahneman and Tversky's Prospect Theory:

$$\text{Perceived}(v) = \begin{cases}
\lambda_{KT} \cdot v & \text{if } v < 0 \text{ (loss)} \\
v & \text{if } v \geq 0 \text{ (gain)}
\end{cases}$$

Where $\lambda_{KT} = 2.25$ is the empirically-derived loss aversion coefficient.

The pain of losing $100 is approximately $2.25\times$ greater than the pleasure of gaining $100. This asymmetry drives the **Fascist Bifurcation**: crises generate disproportionate agitation energy. When people lose things, they *feel* it more than when they gain things.

This is why austerity is politically explosive. This is why "but the economy is growing!" doesn't matter if your wages are falling. The math captures the psychology.

\newpage

# Part IV: Unequal Exchange

## The Exchange Ratio: Is This Theory Bananas?

The **Prebisch-Singer** framework quantifies unequal exchange between core and periphery:

$$\varepsilon = \frac{L_p}{L_c} \cdot \frac{W_c}{W_p}$$

Where:

- $L_p$ --- Labor hours expended in periphery
- $L_c$ --- Labor hours expended in core
- $W_c$ --- Core wages
- $W_p$ --- Periphery wages

Let me give you a concrete example, because I'm sick of abstractions.

Consider the Finca Tropical S.A. plantation in La Lima, Honduras. According to university studies, the average banana farmer markets about 30,000 pounds of bananas per acre per year. The Finca plantation has 578 acres and 217 employees. By the estimates, 17.34 million pounds of bananas are harvested per year, requiring 542,500 labor hours. A pound of bananas in the United States retails for 63 cents.

Plantation worker Norma Gomez testified that she and her coworkers are paid by piece wages --- at the absolute highest, $14 per day for a 14-hour shift. That's $1/hour.

Meanwhile, the average US grocery store worker earns $17.64/hour.

The ratio of unequal exchange: **$\varepsilon = 68.25$**

> **In other words: 1 hour of labor in the imperialist core can purchase 68.25 hours worth of peripheral labor.**

This isn't ideology. This is arithmetic.

## What Would a "Fair" Banana Cost?

The rate of exploitation on that Honduran plantation is **1493%**. For every $1 in plantation wages, the plantation owner profits $14.93.

If we paid workers in the periphery the same wages as first-world proletarians, and maintained the same rate of exploitation (because capitalism), the price of 1 lb of bananas would need to increase to **$11.10**.

That's a **1762% increase** from the current 63 cents.

The cheap bananas in your kitchen aren't cheap because of efficiency gains or technological progress. They're cheap because somewhere in Honduras, a worker's hands are bleeding for a dollar an hour. The formula captures this.

## Purchasing Power Parity: The "Unearned Increment"

The **PPP Model** captures how superwages manifest not as direct cash handouts but as **purchasing power**:

$$\text{PPP}_{mult} = 1 + (\alpha \cdot m_{super} \cdot p_{impact})$$

The **Effective Wealth** and **Unearned Increment**:

$$\begin{aligned}
\text{Effective Wealth} &= \text{Nominal Wage} \cdot \text{PPP}_{mult} \\
\text{Unearned Increment} &= \text{Effective Wealth} - \text{Nominal Wage}
\end{aligned}$$

> **The Value Split (In Strict Marxist Terms)**
>
> | Class | Captures | Form |
> |-------|----------|------|
> | **Bourgeoisie** | Surplus Value | Money/Profit (Capital Accumulation) |
> | **Labor Aristocracy** | Use Value | Cheap Commodities (Purchasing Power) |

The **Unearned Increment** is not a cash handout. It's the enhanced purchasing power from cheap periphery commodities. Your dollar goes further at Walmart because someone in Bangladesh is sewing shirts for pennies.

This is the **material basis of labor aristocracy loyalty**. It's not false consciousness (though that exists too). It's rational self-interest given material conditions.

\newpage

# Part V: System Dynamics

## Solidarity Transmission: How Consciousness Spreads

Consciousness spreads through SOLIDARITY edges via a **discrete diffusion** equation:

$$\Delta\Psi_{target} = \sigma \cdot (\Psi_{source} - \Psi_{target})$$

Subject to conditions:

1. $\Psi_{source} > \theta_{activation}$ (source must be in active struggle)
2. $\sigma > 0$ (solidarity infrastructure must exist)

Here's the practical implication:

> **When $\sigma = 0$ (no solidarity infrastructure):**
>
> - Periphery can revolt (high $\Psi_{source}$)
> - But consciousness does NOT transmit to core
> - Core workers route crisis energy to national identity $\to$ **Fascism**
>
> **When $\sigma > 0$ (solidarity exists):**
>
> - Periphery revolt transmits consciousness to core
> - Core workers route crisis energy to class consciousness $\to$ **Revolution**

This is why the "just-as-the-American-empire-collapses-there-will-be-an-American-revolution" take is dangerously naive. Collapse without solidarity infrastructure produces fascism, not revolution. We've seen this movie before. It was called Weimar Germany.

## Tension Dynamics: How Contradictions Sharpen

Tension accumulates on edges according to wealth inequality:

$$\text{tension}_{t+1} = \min\left(1.0, \text{tension}_t + |\Delta W| \cdot r_{accum}\right)$$

When $\text{tension} = 1.0$, a **Rupture Event** fires --- the contradiction has become antagonistic.

This is the simulation encoding of dialectics. Quantitative changes accumulate until they produce qualitative leaps. The tension formula makes this concrete.

## Bourgeoisie Decision Heuristics: What the Ruling Class Actually Does

The bourgeoisie responds to material conditions via a **decision matrix**:

$$D(p, \tau) = \begin{cases}
\text{CRISIS} & p < 0.1 \\
\text{BRIBERY} & p \geq 0.7 \land \tau < 0.3 \\
\text{IRON\_FIST} & p < 0.3 \land \tau > 0.5 \\
\text{AUSTERITY} & p < 0.3 \land \tau \leq 0.5 \\
\text{NO\_CHANGE} & \text{otherwise}
\end{cases}$$

Where:

- $p$ --- Pool ratio (current imperial rent pool / initial pool)
- $\tau$ --- Aggregate tension across the graph

**Decision Matrix Effects:**

| Decision | Wage $\Delta$ | Repression $\Delta$ |
|----------|---------------|---------------------|
| CRISIS | -15% | +20% |
| BRIBERY | +5% | 0% |
| IRON_FIST | 0% | +10% |
| AUSTERITY | -5% | 0% |
| NO_CHANGE | 0% | 0% |

The bourgeoisie aren't stupid. They have a playbook. When the rent pool is healthy and tensions are low, they bribe the workers. When the pool is depleted but tensions are high, they crack down. When tensions are low but the pool is depleted, they implement austerity.

The simulation encodes this because **understanding your enemy's decision-making is essential for any organizer**.

\newpage

# Part VI: The System Architecture

## The Simulation Loop

The engine executes six systems in order each tick:

1. **ImperialRentSystem** --- Extracts wealth via imperial rent
2. **SolidaritySystem** --- Transmits consciousness via solidarity edges
3. **ConsciousnessSystem** --- Evolves ideology through bifurcation routing
4. **SurvivalSystem** --- Calculates $P(S|A)$ and $P(S|R)$
5. **ContradictionSystem** --- Accumulates tension, triggers ruptures
6. **TerritorySystem** --- Manages heat, eviction, and spatial spillover

This ordering matters. Imperial rent extraction happens first because material conditions determine consciousness, not the other way around. The base determines the superstructure.

## Symbolic Parameters

| Symbol | Name | Range | Description |
|--------|------|-------|-------------|
| $\alpha$ | Extraction efficiency | $[0, 1]$ | How effectively rent is extracted |
| $\lambda$ | Decay coefficient | $[0, 1]$ | Natural consciousness regression |
| $\lambda_{KT}$ | Loss aversion | 2.25 | Kahneman-Tversky coefficient |
| $k$ | Sensitivity | $[0, \infty)$ | Sigmoid steepness |
| $\sigma$ | Solidarity strength | $[0, 1]$ | Edge weight for transmission |
| $\Psi$ | Consciousness | $[0, 1]$ | 0=submissive, 1=revolutionary |
| $\Phi$ | Imperial rent | $[0, \infty)$ | Extracted value |
| $\varepsilon$ | Exchange ratio | $(0, \infty)$ | Unequal exchange measure |
| $\rho$ | Labor aristocracy ratio | $(0, \infty)$ | $W_c / V_c$ |
| $\tau$ | Tension | $[0, 1]$ | Contradiction intensity |

\newpage

# Appendix A: Formula Summary

| # | Category | Formula | Type | Location |
|---|----------|---------|------|----------|
| 1 | Fundamental | $\Phi = \alpha W_p (1-\Psi_p)$ | Algebraic | `formulas.py:37` |
| 2 | Fundamental | $\rho = W_c / V_c$ | Ratio | `formulas.py:60` |
| 3 | Consciousness | $d\Psi/dt = k(1-\rho) - \lambda\Psi + B$ | ODE | `formulas.py:105` |
| 4 | Survival | $P(S|A) = 1/(1+e^{-k(x-x_0)})$ | Sigmoid | `formulas.py:178` |
| 5 | Survival | $P(S|R) = C/(R+\epsilon)$ | Ratio | `formulas.py:202` |
| 6 | Survival | $x_{cross} = x_0 - \ln(...)/k$ | Inverse | `formulas.py:225` |
| 7 | Survival | $\lambda_{KT} = 2.25$ | Coefficient | `formulas.py:265` |
| 8 | Exchange | $\varepsilon = (L_p/L_c)(W_c/W_p)$ | Ratio | `formulas.py:287` |
| 9 | Exchange | $E\% = (\varepsilon-1) \times 100$ | Percentage | `formulas.py:321` |
| 10 | Exchange | $T = P(1-1/\varepsilon)$ | Algebraic | `formulas.py:336` |
| 11 | Exchange | $P_{new} = P_0(1+e\Delta L)$ | Elasticity | `formulas.py:358` |
| 12 | Solidarity | $\Delta\Psi = \sigma(\Psi_s - \Psi_t)$ | Diffusion | `formulas.py:389` |
| 13 | Ideology | $(\Delta\Psi_c, \Delta\Psi_n, E)$ | Vector | `formulas.py:442` |
| 14 | Economic | $D(p, \tau)$ | Heuristic | `formulas.py:544` |

\newpage

# Appendix B: Historical Validation

The model encodes several historically-validated dynamics. This isn't just math for math's sake --- it's math that produces known historical outcomes when you plug in known historical conditions.

## Germany 1933

- **Conditions:** Falling wages ($\Delta W < 0$), weak internationalism ($\sigma \approx 0$)
- **Model Prediction:** Agitation routes to national identity $\to$ Fascism
- **Historical Outcome:** Nazi rise to power

The Weimar Republic had a large, organized working class. But the SPD had gutted international solidarity in favor of national chauvinism. When the crisis hit, the agitation energy had nowhere revolutionary to go.

## Russia 1917

- **Conditions:** Falling wages ($\Delta W < 0$), strong internationalism ($\sigma > 0$)
- **Model Prediction:** Agitation routes to class consciousness $\to$ Revolution
- **Historical Outcome:** October Revolution

The Bolsheviks had spent years building international solidarity networks. When the crisis hit, the infrastructure was there to route that energy toward revolution.

## United States 2025

- **Conditions:** $W_c > V_c$ (labor aristocracy ratio > 1), high PPP multiplier
- **Model Prediction:** $P(S|A) \gg P(S|R)$, revolution irrational
- **Historical Outcome:** Political passivity of working class

This is where we are now. The math explains why "Do the fucking reading!" doesn't work when material conditions make acquiescence the rational survival strategy. Our job is to build solidarity infrastructure *now*, before the crisis hits, so when the conditions change, the energy routes somewhere productive.

\newpage

# Conclusion: Why This Matters

Some comrades, who are rightfully frustrated about the state of the left, simply throw their hands up and say the American working class is a lost cause. Others, equally frustrated, insist that we just need to educate people harder, that theory will somehow overcome material conditions.

Both are wrong. Both represent deviations from the correct line.

As Mao taught us: **Concrete analysis of concrete conditions is the living soul of Marxism.** These formulas are an attempt at exactly that. They're not perfect --- no model is. But they encode actual material dynamics, grounded in actual data, producing actual historical predictions.

The takeaway isn't despair. The takeaway is that **building solidarity infrastructure is the key variable we can influence**. The $\sigma$ in those equations is something we can change through organizing. When crisis hits --- and it will hit --- that infrastructure will determine whether the energy routes toward revolution or fascism.

Every book club you run increases $\sigma$. Every international solidarity action increases $\sigma$. Every connection you build between core workers and periphery struggles increases $\sigma$.

The math is clear. The task is before us.

---

> *"Whether you can do a thing or not depends on whether you will do it."*
>
> --- Mao Zedong

\vspace{2em}

# References

1. Marx, Karl. (1867). *Das Kapital*, Volume I.
2. Lenin, Vladimir Ilyich. (1916). *Imperialism, the Highest Stage of Capitalism*.
3. Amin, Samir. (1974). *Accumulation on a World Scale*.
4. Cope, Zak. (2019). *The Wealth of (Some) Nations*.
5. Kahneman, Daniel & Tversky, Amos. (1979). "Prospect Theory: An Analysis of Decision under Risk."
6. Prebisch, Raúl. (1950). *The Economic Development of Latin America and Its Principal Problems*.
7. Jackson, George. (1971). *Blood in My Eye*.
8. Wallerstein, Immanuel. (1995). "Response: Declining States, Declining Rights?"
9. Mao, Zedong. (1930). *Oppose Book Worship*.
10. Engels, Friedrich. (1858). Letter to Marx, October 7.

---

*This document is part of the Babylon simulation engine. All formulas are implemented in `src/babylon/systems/formulas.py` with comprehensive test coverage. The code is the theory made executable.*
