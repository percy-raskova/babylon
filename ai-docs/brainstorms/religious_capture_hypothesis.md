# Hypothesis: Gravitational Capture Model of Religious Ideological Bias

**Status**: Preliminary formalization, untested
**Date**: 2026-01-25
**Context**: Babylon simulation engine, George Jackson bifurcation framework

---

## Core Claim

Religious institutions function as **field sources** in ideological space, not neutral transmission infrastructure. Their bias direction is determined by **gravitational capture**—tidal lock to dominant economic/political structures that sustain them materially. The capture mechanism operates through **desire path dynamics** exhibiting myelination-like reinforcement.

---

## Mathematical Formalization

### 1. Hegemonic Attractors

Let $\mathcal{A} = \{A_1, \ldots, A_K\}$ be the set of hegemonic centers (class positions with accumulated weight).

Each attractor $A_k$ has mass $M_k$ grounded in:
- Control over means of production
- Control over means of coercion
- Control over means of reproduction

**Open question**: How $M_k$ derives from primitives in the four-node model.

---

### 2. Institutional Capture

Each institution $i$ has a capture vector on the (K-1)-simplex:

$$\mathbf{c}_i \in \Delta^{K-1}, \quad \sum_k c_{ik} = 1$$

**Dynamics** (slow, coefficient-level, $\alpha$-smoothed):

$$\frac{d\mathbf{c}_i}{dt} = \eta \left( \mathbf{f}_i - \mathbf{c}_i \right)$$

where $\mathbf{f}_i$ is the material flow vector (funding, resources, personnel origin).

**Interpretation**: Institutions drift toward whoever feeds them. Capture is zero-sum across attractors.

---

### 3. Ideological Field Contribution

Each institution contributes to the ideological field at node $n$:

$$\mathbf{E}(n) = \sum_{i \in \mathcal{I}} \frac{\rho_i \cdot \mathbf{b}_i}{d(n, i)^\gamma} \cdot T_{in}$$

| Symbol | Meaning | Grounding |
|--------|---------|-----------|
| $\rho_i$ | Institutional reach | Membership, media presence, resource base |
| $\mathbf{b}_i$ | Bias direction | $\mathbf{b}_i = \sum_k c_{ik} \mathbf{v}_k$ |
| $\mathbf{v}_k$ | Ideological vector of attractor $k$ | **Unspecified—requires definition** |
| $d(n,i)$ | Graph distance | Network topology |
| $\gamma$ | Decay exponent | Empirically calibrated |
| $T_{in}$ | Transmission efficiency | Myelination state of path |

---

### 4. Desire Path Dynamics (Myelination)

Edge weights evolve according to use:

$$\frac{dw_{ij}}{dt} = \alpha \cdot \phi_{ij}(t) - \lambda w_{ij} + \sigma \xi(t)$$

| Symbol | Meaning |
|--------|---------|
| $\phi_{ij}(t)$ | Ideological flow through edge |
| $\alpha$ | Reinforcement rate |
| $\lambda$ | Decay rate |
| $\sigma \xi(t)$ | Noise term |

**Myelination threshold**: At $w_{ij} > w^*$, edge transitions to myelinated regime:
- Higher transmission speed
- Lower decay rate (infrastructure persists)
- Higher crosstalk resistance

**Claim**: This is a phase transition, not continuous change.

---

### 5. Transmission Efficiency

$$T_{in} = \prod_{e \in \text{path}(i,n)} \tau(w_e)$$

where:

$$\tau(w) = \frac{1}{1 + e^{-\beta(w - w^*)}}$$

Sigmoid activation centered on myelination threshold $w^*$.

---

### 6. George Jackson Vector Dynamics

$$\frac{d\mathbf{g}_n}{dt} = \mu \mathbf{E}(n) + \nu \sum_{m \in N(n)} w_{nm}(\mathbf{g}_m - \mathbf{g}_n) + \mathbf{S}_n$$

| Term | Interpretation |
|------|----------------|
| $\mu \mathbf{E}(n)$ | Field pressure from institutions |
| $\nu \sum w_{nm}(\mathbf{g}_m - \mathbf{g}_n)$ | Neighbor diffusion (solidarity transmission) |
| $\mathbf{S}_n$ | Material conditions (survival calculus, accommodation viability) |

**Bifurcation prediction**: When $\mathbf{S}_n$ collapses (crisis), resolution direction depends on:
1. Local field source dominance
2. Existence of myelinated counter-hegemonic paths
3. Network topology (which signals arrive first)

---

## Unresolved Questions

### Foundational

1. **What space does $\mathbf{g}$ live in?**
   - Circle (1D, fascism ↔ revolution as antipodes)?
   - Sphere (2D, independent axes)?
   - Higher-dimensional manifold?
   - Dimensionality determines what "bifurcation" means mathematically.

2. **What are the basis vectors $\mathbf{v}_k$?**
   - How many independent ideological dimensions?
   - Are they orthogonal or do they have intrinsic geometry?

3. **Is capture determined by discrete attractors or positions in the four-node model?**
   - Current formulation assumes external attractors
   - May need reformulation where capture is to {Core, Periphery} × {Bourgeoisie, Proletariat} positions

### Empirical

4. **What observables ground the capture vector $\mathbf{c}_i$?**
   Candidates:
   - Funding source composition
   - Clergy class origin
   - Congregation voting patterns
   - Institutional investment portfolios
   - State relationship (tax status, legal privileges)

5. **Is myelination a phase transition or continuous?**
   - What empirical signature distinguishes them?
   - Historical cases of rapid infrastructure consolidation vs. gradual buildup?

6. **Does ideology superpose linearly?**
   - Current model sums field contributions
   - Competing frameworks may interfere destructively
   - What would nonlinear interaction look like?

---

## Falsifiability Criteria

The hypothesis is **meaningful** only if it generates different predictions than the null hypothesis (religion as neutral transmission infrastructure).

### Prediction 1: Capture Predicts Bias Direction

Institutions with different $\mathbf{c}_i$ vectors should exhibit different bias directions even when controlling for:
- Theological content
- Denominational tradition
- Geographic location

**Test**: Compare ideological output of materially-captured-by-capital churches vs. materially-captured-by-community churches within same denomination.

### Prediction 2: Flow Precedes Capture Shift

Changes in $\mathbf{f}_i$ (material flow) should precede changes in $\mathbf{c}_i$ (ideological orientation) with lag determined by $\eta$.

**Test**: Historical cases where funding shifted before theology shifted (prosperity gospel emergence, NGO-ification of religious charities).

### Prediction 3: Myelinated Paths Determine Bifurcation

In crisis conditions, populations with access to myelinated counter-hegemonic paths should bifurcate toward solidarity at higher rates than topologically equivalent populations without such paths.

**Test**: Compare crisis outcomes in regions with/without pre-existing organizational infrastructure, controlling for material conditions.

### Prediction 4: Transmission Efficiency Is Path-Dependent

Ideological signals should propagate faster and with less attenuation along high-$w$ edges than low-$w$ edges.

**Test**: Measure propagation speed of specific ideological framings through networks with known edge weight distributions.

---

## Null Hypothesis

Religion functions as content-neutral transmission infrastructure (pure sheath model). Bias is determined by:
- Theological content (intrinsic to the religion)
- Individual belief (atomized, not structurally determined)
- Historical contingency (path-dependent but not predictable from material flows)

Under the null, $\mathbf{c}_i$ has no predictive power beyond what's already captured by denomination/theology variables.

---

## Next Steps

1. Define the manifold $\mathbf{g}$ lives on
2. Operationalize $\mathbf{c}_i$ against available data (candidate: IRS 990 filings for funding, ARDA for congregation demographics)
3. Identify historical test cases for Prediction 2 (flow → capture lag)
4. Determine whether myelination threshold is empirically distinguishable from continuous reinforcement

---

## Dependencies

- George Jackson bifurcation framework (existing)
- Four-node recursive model (existing)
- Organizational topology / Betti number analysis (existing)
- Desire path / hegemony-as-habit theoretical grounding (this document)
