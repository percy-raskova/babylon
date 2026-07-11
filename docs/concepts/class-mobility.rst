.. _class-mobility:

===========================================================
Class Mobility: Markov Chains and Stationary Distributions
===========================================================

.. contents:: Table of Contents
   :local:
   :depth: 2

The ``DefaultClassTransitionComputer`` models class mobility as a Markov chain:
the probability of moving between classes depends only on current class position,
not on prior history. This document explains the mathematics of Markov chains,
the stationary distribution, and how Babylon computes and uses it.

For the API reference, see :ref:`tensor-hierarchy-reference`.

----

Class Transition as a Markov Chain
====================================

A **Markov chain** is a stochastic process where the future state depends only
on the present state. For class mobility, this means:

  *The probability of being in class j at time t+1 depends only on class
  membership at time t, not on class history at t-1, t-2, ...*

This is the **memoryless assumption**. It is an idealization—actual class
trajectories have path dependencies (inherited wealth, credential accumulation).
But for aggregate long-run structural analysis, the Markov approximation is
well-established in mobility research and provides computationally tractable
results.

The Transition Matrix *P*
--------------------------

The class transition matrix *P* is an *n*×*n* matrix where:

.. math::

   P[i, j] = \Pr(\text{class } j \text{ at } t+1 \mid \text{class } i \text{ at } t)

Each row represents a conditional distribution over next-period class membership,
given current-period class. The rows must sum to 1.0 (all possibilities are
covered) and all elements must be non-negative (probabilities cannot be negative).

This property—rows summing to 1—is called **row stochasticity**. Babylon
enforces it at construction time with tolerance 1e-6 and validates it in the
three-tier validation framework.

.. list-table:: Transition Matrix Validation Thresholds
   :header-rows: 1
   :widths: 35 25 40

   * - Property
     - Threshold
     - Enforcement
   * - Elements ≥ 0
     - 0.0
     - Fail if any element < 0
   * - Row sum deviation (expected)
     - ≤ 1e-6
     - Expected: exact row stochasticity
   * - Row sum deviation (warning)
     - ≤ 1e-4
     - Warning: floating-point drift
   * - Diagonal self-transition (expected)
     - ≥ 0.50
     - Most people stay in their class
   * - Diagonal self-transition (warning)
     - ≥ 0.20
     - High mobility period

The diagonal element *P*\[*i*,*i*] represents the probability of *staying* in
class *i*. The off-diagonal *P*\[*i*,*j*] represents *upward* or *downward*
mobility probability. The diagonal-dominance condition (high self-transition
probabilities) reflects the empirical reality that class positions are
relatively stable across short time horizons.

----

The Stationary Distribution
============================

As a Markov chain evolves through many periods, it converges toward a
**stationary distribution** π—a fixed-point probability vector that is
unchanged by one application of *P*:

.. math::

   \pi P = \pi, \quad \sum_i \pi_i = 1, \quad \pi_i \geq 0

The stationary distribution represents the *long-run equilibrium*: if the
transition matrix *P* remained constant indefinitely, the fraction of the
population in each class would converge to π. It is the gravitational attractor
of the class structure.

This is a structural measure, not a prediction of any individual's trajectory.
It says: given the *current structure* of class mobility (transition
probabilities), what is the long-run composition of classes that this structure
tends to reproduce?

Why the Stationary Distribution Matters
-----------------------------------------

The stationary distribution plays two roles in the tensor hierarchy:

1. **As a summary statistic.** π gives a single compact description of the
   long-run class composition implied by current mobility patterns. Changes
   in π over time reveal how the structure of class reproduction is shifting.

2. **As weights for class aggregation.** When aggregating a fine-grained class
   transition matrix into coarser categories, the stationary weights are the
   correct weights for combining rows (see Class Aggregation below).

----

Computing the Stationary Distribution
=======================================

The stationary distribution is the **dominant left eigenvector** of *P*—
equivalently, the right eigenvector of *P*\ :sup:`T` corresponding to
eigenvalue 1.0.

Why Eigenvalue 1.0?
--------------------

If π is a stationary distribution, then π*P* = π can be rewritten as:

.. math::

   \pi (P - I) = 0

This means π is a left eigenvector of *P* with eigenvalue 1.0. Equivalently,
(*P*\ :sup:`T`)π\ :sup:`T` = π\ :sup:`T`, so π\ :sup:`T` is a right eigenvector
of *P*\ :sup:`T` with eigenvalue 1.0.

For a row-stochastic matrix with irreducible and aperiodic structure
(Perron-Frobenius theorem), eigenvalue 1.0 is unique and the corresponding
eigenvector has all positive elements.

The Computation Algorithm
--------------------------

Babylon's ``DefaultClassTransitionComputer.stationary_distribution`` implements:

1. **Eigendecompose** *P*\ :sup:`T`: compute all eigenvalues and eigenvectors of
   the transpose.

2. **Find eigenvalue closest to 1.0**: uses ``argmin(|eigenvalues - 1.0|)`` rather
   than checking for equality. This tolerates floating-point representations
   of 1.0 that may be 0.9999999... or 1.0000001..., while still identifying
   the dominant eigenvector correctly.

3. **Extract the real part**: eigenvalues of real matrices may come in
   complex conjugate pairs. The dominant eigenvalue 1.0 always has a real
   eigenvector, so the real part is taken.

4. **Clip negatives**: tiny negative values arise from floating-point arithmetic
   on the imaginary residual. Values are clipped to [0, ∞).

5. **Normalize to sum 1.0**: divide by the sum to produce a probability
   distribution.

6. **Degenerate case**: if after clipping the sum is 0 (all-zero eigenvector),
   fall back to a uniform distribution over classes.

The result is a :class:`~babylon.domain.economics.tensor_hierarchy.types.StationaryDistribution`
with ``distribution`` summing to 1.0 within tolerance 1e-6.

----

Class Aggregation with Stationary Weights
==========================================

When a fine-grained transition matrix (e.g., 10 class categories) needs to
be reduced to a coarser representation (e.g., 3 aggregate classes), the
``DefaultClassTransitionComputer.aggregate_classes`` method performs a
**weighted block-sum reduction**.

Why Stationary Weights?
------------------------

Suppose we are merging two fine classes *A* and *B* into one aggregate class
*W* (working class). The aggregated row for *W* must represent the average
behavior of the merged classes. The correct average is:

  *Weight each fine class by its long-run prevalence in the population.*

Using the stationary distribution π as weights is the principled choice:
π[*A*] is the long-run fraction of the population in class *A*, so it is the
correct weight for class *A*'s transition row in the aggregate.

Using equal weights would distort the aggregate by treating rare classes the
same as common classes. Using current-period empirical shares would introduce
period-specific noise. The stationary distribution is invariant to period
choice while respecting the structure of the mobility process.

The Aggregation Algorithm
--------------------------

1. **Map** each source class to a target class via the provided mapping dict.
2. **Compute** the stationary distribution π of the source matrix.
3. **Accumulate** weighted flows: for each (source class *i*, destination class *j*)
   pair that maps to (aggregate origin *a*, aggregate destination *b*), add
   π[*i*] × *P*\[*i*,*j*] to the aggregate flow[*a*,*b*].
4. **Accumulate** total weights per aggregate origin class.
5. **Divide** each aggregate row by its total weight to re-normalize.
6. **Final normalization**: divide each row by its sum to remove floating-point
   drift and ensure exact row stochasticity.

The resulting matrix is itself row-stochastic, and its stationary distribution
approximates the coarsened stationary distribution of the fine-grained matrix.

----

Political Interpretation
=========================

The stationary distribution is not a neutral statistical tool. In Babylon's
framework it carries specific political meaning.

**Structural determination.** The stationary distribution π is determined
entirely by the transition matrix *P*—the *structural* mobility rates embedded
in the economy's institutions (education, inheritance, labor markets). This
makes π a measure of what the *current class structure tends to reproduce*,
independent of any individual choices or contingencies.

**The gravitational pull of capitalism.** Even if individual trajectories
are highly mobile in a given year, π reveals the long-run attractor. If the
Leontief structure and imperial rent field imply a transition matrix where
π shows 75% proletariat and 5% bourgeoisie, that is the structure capitalism
tends to reproduce. No amount of "social mobility" that changes individual
trajectories changes π if it leaves the transition matrix unchanged.

**Class struggle as P-matrix modification.** Revolutionary conditions are
conditions that change *P* itself—that alter the transition probabilities.
A successful struggle for reforms (union rights, public education) shows up
as changes in *P*\[proletariat→proletariat], *P*\[proletariat→petit_bourgeois],
etc. The simulation can compare stationary distributions before and after such
structural changes to measure their long-run effects.

----

The Deferred Loader
====================

The ``DefaultClassTransitionSource`` is a **stub** that returns
:class:`~babylon.domain.economics.tensor.NoDataSentinel` for all queries. The
production implementation requires PSID (Panel Study of Income Dynamics)
data from the University of Michigan, which requires a restricted-use data
agreement.

This deferred status does not affect the computation engine:
``DefaultClassTransitionComputer`` is fully implemented and all computation
tests pass using synthetic transition matrices. When PSID data becomes
available, only the source implementation changes.

----

Related Documentation
=====================

- :ref:`tensor-hierarchy-concept` — Three-level tensor hierarchy overview
- :ref:`leontief-analysis` — Input-output economics and the Leontief inverse
- :ref:`tensor-hierarchy-reference` — Complete tensor and protocol data dictionary
- :mod:`babylon.domain.economics.tensor_hierarchy.class_transition` — Implementation
