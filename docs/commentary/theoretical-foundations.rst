Theoretical Foundations
=======================

This document explains the Marxist-Leninist-Maoist Third Worldist (MLM-TW)
theory encoded in the Babylon simulation engine. It bridges political
economy and code.

.. epigraph::

   The history of all hitherto existing society is the history of class
   struggles.

   -- Marx & Engels, *The Communist Manifesto* (1848)

Why MLM-TW?
-----------

Babylon doesn't simulate abstract "political systems." It encodes a
specific theoretical framework: MLM-TW (Marxist-Leninist-Maoist Third
Worldist) analysis of global imperialism.

This choice is deliberate:

1. **Predictive power** — MLM-TW offers testable predictions about class
   dynamics, imperial extraction, and revolutionary potential.

2. **Material grounding** — Every mechanic traces to observable economic
   relationships, not idealist abstractions.

3. **Historical validation** — The framework explains historical events
   (decolonization, labor aristocracy formation, fascist emergence) with
   mathematical precision.

The simulation is a tool for exploring these predictions computationally.

The Fundamental Theorem
-----------------------

The central thesis of MLM-TW encoded in Babylon:

.. admonition:: Fundamental Theorem

   Revolution in the imperial core is impossible when wages exceed value
   produced:

   .. math::

      W_c > V_c \implies P(Revolution) \approx 0

This isn't pessimism—it's material analysis. When core workers receive
more value than they produce, their material interest aligns with
imperialism, not revolution. The difference (``W_c - V_c``) is
**imperial rent** extracted from the periphery.

Imperial Rent
~~~~~~~~~~~~~

The formula for imperial rent extraction:

.. math::

   \Phi = \alpha \cdot W_p \cdot (1 - \Psi_p)

Where:

- :math:`\Phi` — Imperial rent (value extracted)
- :math:`\alpha` — Extraction efficiency (exploitation intensity)
- :math:`W_p` — Periphery wages (available value)
- :math:`\Psi_p` — Periphery consciousness (resistance)

**Key insight**: As periphery consciousness rises (:math:`\Psi_p \to 1`),
imperial rent collapses (:math:`\Phi \to 0`). This encodes the material
basis of anti-colonial struggle.

The Labor Aristocracy
~~~~~~~~~~~~~~~~~~~~~

A worker belongs to the **labor aristocracy** when:

.. math::

   \rho = \frac{W_c}{V_c} > 1

They receive more value than they produce. The surplus comes from
imperial rent. Their class interest diverges from the global proletariat.

This explains why revolutionary potential concentrates in the periphery,
not the core—a central MLM-TW prediction.

Consciousness Dynamics
----------------------

Consciousness evolution follows a differential equation:

.. math::

   \frac{d\Psi}{dt} = k(1 - \rho) - \lambda\Psi + B(\Delta W, \sigma)

Three terms govern consciousness change:

**Material Term**: :math:`k(1 - \rho)`
   When wages exceed value (:math:`\rho > 1`), consciousness decays.
   When wages fall below value (:math:`\rho < 1`), consciousness rises.
   Material conditions determine consciousness trajectory.

**Decay Term**: :math:`-\lambda\Psi`
   Consciousness naturally regresses without reinforcement.
   This encodes the ideological weight of the superstructure—media,
   education, cultural hegemony.

**Bifurcation Term**: :math:`B(\Delta W, \sigma)`
   When wages fall, crisis energy emerges. Where it routes depends on
   solidarity infrastructure.

The Fascist Bifurcation
-----------------------

.. admonition:: Historical Encoding

   This formula encodes a crucial historical lesson:

   **Agitation without solidarity produces fascism, not revolution.**

   - Germany 1933: Falling wages + no internationalist solidarity → Fascism
   - Russia 1917: Falling wages + strong internationalist solidarity → Revolution

When wages fall (:math:`\Delta W < 0`), agitation energy is generated:

.. math::

   E_{agitation} = |\Delta W| \cdot \lambda_{KT}

Where :math:`\lambda_{KT} = 2.25` is the Kahneman-Tversky loss aversion
coefficient—losses feel 2.25× more impactful than equivalent gains.

This energy routes based on solidarity:

.. math::

   \begin{aligned}
   \Delta\Psi_{class} &= E \cdot \sigma \cdot \gamma \\
   \Delta\Psi_{national} &= E \cdot (1 - \sigma) \cdot \gamma
   \end{aligned}

Where:

- :math:`\sigma` — Solidarity strength from SOLIDARITY edges [0, 1]
- :math:`\gamma = 0.1` — Routing efficiency constant

**With solidarity** (:math:`\sigma \to 1`): Energy routes to class
consciousness → revolutionary potential increases.

**Without solidarity** (:math:`\sigma \to 0`): Energy routes to national
identity → fascist potential increases.

This is the **George Jackson Bifurcation**, named after the revolutionary
theorist whose analysis of prison organizing informed this mechanic.

Survival Calculus
-----------------

Every agent faces a fundamental choice between survival strategies:

**P(S|A) — Survival by Acquiescence**

.. math::

   P(S|A) = \sigma\left(\frac{W - W_{sub}}{k_{steep}}\right)

Where:

- :math:`W` — Current wealth
- :math:`W_{sub}` — Subsistence threshold
- :math:`k_{steep}` — Steepness of transition
- :math:`\sigma` — Sigmoid function

Agents with wealth above subsistence survive by accepting the system.
As wealth approaches subsistence, this probability drops sharply.

**P(S|R) — Survival by Revolution**

.. math::

   P(S|R) = \frac{O}{R}

Where:

- :math:`O` — Organization level (collective capacity)
- :math:`R` — Repression level (state violence)

Well-organized agents facing weak repression have high revolutionary
survival probability.

**The Crossover Threshold**

Revolution becomes rational when:

.. math::

   P(S|R) > P(S|A)

At this point, revolutionary action offers better survival odds than
acquiescence. The agent's rational choice shifts.

Unequal Exchange
----------------

Value flows asymmetrically in the world system:

.. math::

   \frac{V_c}{V_p} = \frac{L_p \cdot p_p}{L_c \cdot p_c} > 1

Where:

- :math:`L` — Labor hours
- :math:`p` — Productivity per hour

Core workers produce more value per hour (higher :math:`p_c`) but the
exchange ratio favors core goods—periphery workers trade more labor hours
for equivalent core products.

The **Prebisch-Singer Effect** captures secular decline:

.. math::

   ToT(t) = ToT_0 \cdot e^{-\delta t}

Terms of trade deteriorate over time for commodity exporters, structurally
disadvantaging the periphery.

Topology and Solidarity
-----------------------

The NetworkX graph structure encodes class relations:

**Nodes**: Social classes (entities) and territories (spatial units)

**Edges**:

- EXPLOITATION — Value extraction relationships
- SOLIDARITY — Consciousness transmission channels
- WAGES — Payment flows from capital to labor
- TRIBUTE — Extraction flows (imperial rent)

Solidarity edges are critical infrastructure. Their presence or absence
determines whether crisis energy routes to revolution or fascism.

**Atomization** describes the destruction of solidarity edges—a deliberate
strategy of the ruling class to prevent class consciousness formation.

Why This Matters for Code
-------------------------

Every formula in ``src/babylon/systems/formulas.py`` implements one of
these theoretical concepts. When debugging unexpected behavior, trace
back to theory:

- Unexpected death? Check subsistence threshold and extraction rate.
- No revolution? Verify solidarity edges exist.
- Fascism emerging? Look for missing solidarity infrastructure.

The code is the theory made computational. Understanding one illuminates
the other.

See Also
--------

- :doc:`/reference/formulas` - Complete formula specifications
- :doc:`/concepts/george-jackson-model` - Bifurcation mechanics
- :doc:`/concepts/imperial-rent` - Extraction mechanics
- :doc:`/concepts/survival-calculus` - Survival strategy details
- ``brainstorm/mechanics/mathematical-foundations.md`` - Full formal treatment
