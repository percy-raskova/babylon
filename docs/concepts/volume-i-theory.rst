Capital Volume I: The Production of Surplus Value
==================================================

Marx's *Capital Volume I* (1867) analyzes the **production** of surplus
value — the extraction of unpaid labor at the point of production. This
document explains the three Volume I mechanisms implemented in Babylon
and the theoretical reasoning behind their formalization.

.. contents:: On this page
   :local:
   :depth: 2

Why Volume I Matters for the Simulation
---------------------------------------

Babylon's simulation engine already models the **composition** of value
(constant capital *c*, variable capital *v*, surplus value *s* in the
value tensor) and the **distribution** of surplus (Volume III's tendency
of the rate of profit to fall). But these are *descriptive* — they tell
us what value looks like at a moment in time, not *why* it changes.

Volume I provides the **causal engines**:

1. **The Reserve Army** explains *why wages move* — not supply and demand
   in the bourgeois sense, but the structural production of a surplus
   population that disciplines the entire working class.

2. **Dispossession** explains *why wealth transfers* — not through market
   competition, but through extra-economic seizure that Marx called
   "primitive accumulation" and that continues as an ongoing process
   (Harvey's "accumulation by dispossession").

3. **The Working Day** explains *how surplus is extracted* — either by
   lengthening the working day (absolute) or by intensifying labor
   within a fixed day (relative), with radically different consequences
   for worker consciousness.

Without these mechanisms, the simulation describes the anatomy of
capitalism. With them, it describes its physiology.

The Industrial Reserve Army of Labor
-------------------------------------

Theory
~~~~~~

In Chapter 25 of *Capital*, Marx demonstrates that capitalist
accumulation *necessarily* produces a relative surplus population — workers
who are surplus to capital's immediate requirements. This is not a market
failure but a structural feature: capital needs the reserve army to
discipline wages and maintain labor flexibility.

Marx identifies four layers:

**Floating reserve** — Workers between jobs. In the BLS data, this
approximates the U-3 (official) unemployed. These are workers recently
displaced by firm closures, layoffs, or sectoral shifts who are actively
seeking work. Capital can reabsorb them during expansions.

**Latent reserve** — Workers who are underemployed, discouraged, or
marginally attached. The BLS captures this as the gap between U-6 and
U-3. These workers have been pushed to the margins — working part-time
involuntarily, or giving up active job search — but could be drawn back
into production if conditions change.

**Stagnant reserve** — Workers in chronic irregular employment. The BLS
"part-time for economic reasons" (PTER) category captures this layer.
These workers are *in* the labor force but trapped in precarious, low-wage,
intermittent work — the gig economy, day labor, temp agencies.

**Pauperized** — Workers unable to work at all. This includes the
disabled, institutionalized, and permanently excluded. Marx calls this
"the hospital of the active labour-army and the dead weight of the
industrial reserve army." Census disability and incarceration data
approximate this layer.

The key insight is that **pauperized workers are excluded from the
reserve ratio calculation**. Marx explicitly separates pauperism from
the active reserve army — paupers exert no disciplinary pressure on
wages because they are structurally excluded from the labor market.

The General Law of Capitalist Accumulation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Marx's "general law" states that accumulation produces the reserve army,
and the reserve army depresses wages, which in turn raises the rate of
surplus value, which accelerates accumulation. This is a positive
feedback loop:

.. math::

   \text{Accumulation} \rightarrow \text{Mechanization}
   \rightarrow \uparrow \text{Reserve Army}
   \rightarrow \downarrow \text{Wages}
   \rightarrow \uparrow s/v
   \rightarrow \text{Accumulation}

The simulation models this by:

1. Computing ``reserve_ratio`` from BLS labor force data
2. Mapping ``reserve_ratio`` to ``wage_pressure`` via a bounded sigmoid
3. Applying wage pressure as a multiplicative reduction to ``median_wage``
4. The reduced wages feed downstream into variable capital (*v*) in the
   value tensor

Why a Sigmoid?
~~~~~~~~~~~~~~

The wage-pressure function uses a sigmoid rather than a linear mapping
for three reasons grounded in Marx's analysis:

1. **Threshold effect**: Below a certain reserve ratio (~3–4% "natural"
   unemployment), there is essentially no wage pressure. The sigmoid's
   flat region near zero captures this.

2. **Saturation**: Even with massive unemployment, wages cannot fall to
   zero — workers must receive *some* subsistence to reproduce their
   labor power. The ceiling parameter (default 0.5) prevents total wage
   elimination.

3. **Accelerating middle region**: The sharpest wage effects occur in the
   middle range (8–15% unemployment), where the reserve army is large
   enough to create real competition for jobs but not so large that the
   system has already adjusted. This matches the empirical Phillips curve
   literature, reinterpreted through Marx's structural lens.

The midpoint parameter *r₀* = 0.08 is calibrated to reflect that
meaningful wage pressure begins around 8% effective unemployment — roughly
where the 2008 crisis started producing observable wage stagnation in the
Detroit metro area.

Primitive Accumulation / Ongoing Dispossession
----------------------------------------------

Theory
~~~~~~

Marx devotes Part VIII of *Capital* to "primitive accumulation" — the
historical process by which the peasantry was separated from the means of
production through enclosure, colonization, and state violence. The
orthodox reading treats this as a *historical* phase that preceded
capitalism. Rosa Luxemburg, David Harvey, and Glen Coulthard have
demonstrated that primitive accumulation is an **ongoing** process
essential to capitalism's continued reproduction.

In Babylon's Detroit case study, ongoing dispossession takes eight forms:

**Foreclosure** — The 2008 crisis produced a foreclosure epidemic in
Wayne County. Between 2005 and 2012, an estimated 100,000+ homes were
foreclosed, transferring property wealth from working-class households
(disproportionately Black labor aristocracy) to banks and institutional
investors. This is the clearest example of dispossession: wealth that
was accumulated through decades of wage labor is seized through financial
mechanisms in a matter of months.

**Eviction** — The corollary to foreclosure for renters. Princeton's
Eviction Lab data shows that Wayne County consistently has eviction rates
3–5x higher than Oakland County — a spatial pattern that maps directly
onto the racial geography of the Detroit metro area.

**Tax sale** — Wayne County conducted the largest tax foreclosure
auction in US history, selling 62,000 properties between 2011 and 2015.
Tax sales transfer property for pennies on the dollar, often to
speculators and institutional investors.

**Gentrification displacement** — As capital flows back into
post-industrial urban cores, long-term residents are displaced by rising
rents. This is primitive accumulation operating through the rent form —
Harvey's "accumulation by dispossession" in its most visible spatial
manifestation.

**Wage theft** — Unpaid wages, tip theft, and worker misclassification
represent direct extraction of value from workers outside the normal
surplus value relation. The EPI estimates $15 billion in annual wage
theft nationally.

**Incarceration seizure** — The carceral system seizes assets through
civil forfeiture, extracts commissary fees, and destroys earning capacity
through criminal records. This connects to the carceral geography system
already modeled in Babylon.

**Pension default** — Corporate bankruptcies (Detroit's own 2013
municipal bankruptcy) eliminate earned pension obligations, transferring
decades of deferred compensation from retirees to creditors.

**Eminent domain** — State seizure for "public use" that
disproportionately targets communities of color. The Poletown case
(1981) demolished an entire Detroit neighborhood for a GM plant.

Value Transfer Accounting
~~~~~~~~~~~~~~~~~~~~~~~~~

Dispossession is fundamentally a **transfer** operation — wealth is not
destroyed (except for deadweight loss), it is moved. The simulation
tracks this through balanced accounting:

.. math::

   V_{\text{total}} = V_{\text{received}} + V_{\text{deadweight}}

The deadweight loss fraction (default 5%) represents the real economic
destruction that accompanies dispossession: legal costs, property
deterioration during vacancy, community disruption, health impacts.

The intensity weights reflect the *scale* and *frequency* of each
dispossession type. Foreclosure dominates (weight 0.40) because it
involves the largest individual value transfers and was the primary
mechanism of wealth destruction in the Detroit metro area during
2008–2012.

The Working Day
---------------

Theory
~~~~~~

In Chapters 10–15 of *Capital*, Marx distinguishes two methods of
increasing surplus value:

**Absolute surplus value** is produced by lengthening the working day.
If the necessary labor time (time to reproduce the worker's labor power)
is fixed at 4 hours, extending the day from 8 to 10 hours increases
surplus labor from 4 to 6 hours. The rate of exploitation (s/v) rises
from 100% to 150%.

This is the method of early industrial capitalism: 14-hour days, child
labor, no weekends. It is *visible* to workers — they experience the
exploitation directly as exhaustion, injury, and death.

**Relative surplus value** is produced by reducing necessary labor time
through technological innovation. If productivity doubles, the worker
reproduces their labor power in 2 hours instead of 4. With the same
8-hour day, surplus labor rises from 4 to 6 hours. The rate of
exploitation rises from 100% to 200%.

This is the method of mature industrial capitalism: automation,
rationalization, lean production. It is *invisible* to workers — wages
may even rise in nominal terms while the rate of exploitation increases.

Why This Matters for Consciousness
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The absolute/relative distinction is critical for consciousness dynamics:

**Absolute exploitation produces visible suffering.** A warehouse worker
doing 55 hours per week with mandatory overtime *knows* they are being
exploited. The exploitation is inscribed in their body — back pain,
sleep deprivation, family disruption. This visibility generates
spontaneous resistance: the 19th century Ten Hours Movement, today's
Fight for $15.

**Relative exploitation is invisible.** A software engineer working
37 hours per week at $120K salary does not *feel* exploited, even if
their rate of exploitation (s/v) is higher than the warehouse worker's.
The productivity gains that generated their surplus value are abstract —
they cannot point to the specific moment their labor was appropriated.

The simulation captures this through the **visibility modifier**:

- ABSOLUTE_DOMINANT: visibility = 1.0 (full consciousness effect)
- RELATIVE_DOMINANT: visibility = 0.3 (muted consciousness effect)
- MIXED: interpolated between 0.3 and 1.0

This creates a concrete mechanism for Marx's observation that the most
exploited workers are not necessarily the most revolutionary. Revolution
requires not just exploitation but *visible* exploitation combined with
organizational capacity — which is why the warehouse workers and gig
economy precariat of Detroit's current economy may generate more
revolutionary potential than the tech workers of Oakland County, despite
the latter's potentially higher rates of exploitation.

Detroit as Case Study
~~~~~~~~~~~~~~~~~~~~~

Detroit's economic transformation illustrates the absolute/relative
shift:

**Manufacturing era (pre-2000)**: Auto assembly was a *relative*
extraction regime. High productivity, high wages, 40-hour weeks. The
UAW secured the conditions that made the Detroit working class a labor
aristocracy. Exploitation was invisible — mediated through speed-up,
automation, and outsourcing.

**Post-industrial era (2000+)**: The collapse of manufacturing and rise
of logistics, gig work, and service employment pushed Detroit toward
*absolute* extraction. Amazon warehouses, DoorDash, temporary staffing
agencies — long hours, low productivity, visible exploitation.

This shift should produce different consciousness dynamics in the
simulation: a working class that was politically quiescent under relative
extraction (high wages, invisible exploitation) becomes increasingly
volatile under absolute extraction (low wages, visible exploitation).

The Feedback Loop
-----------------

The three mechanisms form a self-reinforcing cycle that models the
fundamental dynamic of capitalist accumulation:

1. **Accumulation** drives investment in labor-saving technology
   (mechanization)
2. **Mechanization** displaces workers into the reserve army
3. **Reserve army growth** suppresses wages (wage pressure)
4. **Lower wages** reduce variable capital (*v*), raising the rate
   of surplus value (*s/v*)
5. **Higher exploitation rate** accelerates accumulation
6. **Dispossession** transfers accumulated wealth from working class
   to capital, accelerating the process
7. **Working day extension** (absolute extraction) increases surplus
   directly, but makes exploitation *visible*, eventually generating
   resistance

This is the loop that the integration tests verify: over multiple ticks,
wages decline, wealth transfers from high-dispossession territories
(Wayne County) to capital, and exploitation mode visibility feeds back
into consciousness dynamics.

The loop contains its own negation: as absolute exploitation becomes
dominant and visible, the conditions for revolutionary consciousness
improve. This is Marx's fundamental insight — capitalism produces its
own gravedigger, not through moral failure, but through the structural
dynamics of accumulation.

See Also
--------

- :doc:`/reference/volume-i-production` — Data types, formulas, and parameters
- :doc:`/concepts/imperial-rent` — How imperial rent extracts from periphery
- :doc:`/concepts/survival-calculus` — How material conditions drive action
- :doc:`/concepts/george-jackson-model` — Consciousness bifurcation dynamics
