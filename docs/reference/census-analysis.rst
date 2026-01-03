.. _census-analysis:

==================================
Census Data Analysis for Babylon
==================================

This document presents empirical findings from the 2017-2021 American Community
Survey (ACS) 5-Year Estimates, analyzed through the lens of Marxist-Leninist-Maoist
Third Worldist theory. These patterns inform Babylon's game mechanics and provide
material grounding for the simulation's class dynamics.

.. contents:: Table of Contents
   :local:
   :depth: 2

Data Overview
=============

The analysis draws from 8 ACS tables covering 392 U.S. Metropolitan Statistical
Areas (MSAs), yielding 104,150 records in the census research database:

.. list-table:: Census Tables Analyzed
   :header-rows: 1
   :widths: 15 40 25

   * - Table
     - Description
     - Game Relevance
   * - B19001
     - Household Income Distribution (17 brackets)
     - Inequality coefficient, class stratification
   * - B19013
     - Median Household Income
     - Labor aristocracy identification
   * - B23025
     - Employment Status
     - Reserve army of labor
   * - B24080
     - Class of Worker by Gender
     - State dependency, self-employment
   * - B25003
     - Housing Tenure (Owner/Renter)
     - Atomization index
   * - B25064
     - Median Gross Rent
     - Material conditions
   * - B25070
     - Rent Burden Distribution
     - Proletarianization pressure
   * - C24010
     - Occupation by Gender
     - Production vs service economy

The Labor Aristocracy Map
=========================

*"The bomb factory pays well. That's the problem."*

The labor aristocracy—workers whose wages exceed the value they produce due to
imperial rent extraction—is geographically concentrated in specific metro areas.
These workers have the highest material stake in system preservation.

.. list-table:: Top 10 Labor Aristocracy Metros by Median Income
   :header-rows: 1
   :widths: 45 20 20

   * - Metro Area
     - Median Income
     - Income/Rent Ratio
   * - San Jose-Sunnyvale-Santa Clara, CA
     - $138,370
     - 4.59
   * - San Francisco-Oakland-Berkeley, CA
     - $118,547
     - 4.58
   * - Washington-Arlington-Alexandria, DC
     - $111,252
     - 5.20
   * - California-Lexington Park, MD
     - $102,859
     - 5.75
   * - Bridgeport-Stamford-Norwalk, CT
     - $101,194
     - 5.29
   * - Boston-Cambridge-Newton, MA-NH
     - $99,039
     - 4.97
   * - Seattle-Tacoma-Bellevue, WA
     - $97,675
     - 4.79
   * - Minneapolis-St. Paul-Bloomington, MN
     - $87,397
     - 6.03
   * - Midland, TX
     - $87,812
     - 5.76
   * - Baltimore-Columbia-Towson, MD
     - $87,513
     - 5.26

**Key Pattern**: The "income-to-annual-rent ratio" measures how many years of
rent a household's income could cover. Minneapolis leads at 6.03—exceptionally
comfortable. California metros show high incomes but lower ratios (4.0-4.6),
revealing the "California Contradiction."

**Game Implication**: These metros should initialize with high ``super_wage_rate``
and strong ``fascist_bifurcation`` tendencies. Workers here will defend
imperialism because they benefit materially.

The Rent Burden Crisis
======================

*Agitation Without Solidarity = Fascism*

.. warning::

   **CRITICAL MLM-TW CORRECTION**: High rent burden does NOT automatically
   create revolutionary potential. The fascist bifurcation formula is explicit:
   *"Agitation without solidarity produces fascism, not revolution."*

   Rent burden in atomized populations (college towns, transient workers)
   produces: DSA membership, Bernie votes, lifestyle leftism, and when
   crisis intensifies—scapegoating and reaction. NOT revolutionary organization.

.. list-table:: Metros with Highest Severe Rent Burden (50%+ of Income)
   :header-rows: 1
   :widths: 35 15 15 20

   * - Metro Area
     - % Burdened
     - Income
     - MLM-TW Analysis
   * - Ithaca, NY
     - 37.9%
     - $64,260
     - COUNTER-REV: Aspirational LA
   * - Vineland-Bridgeton, NJ
     - 37.3%
     - $58,397
     - POTENTIAL: Agricultural workers
   * - Bloomington, IN
     - 37.1%
     - $54,060
     - COUNTER-REV: Student transience
   * - Miami-Fort Lauderdale, FL
     - 33.4%
     - $62,870
     - COMPLEX: Cuban exile bloc
   * - College Station-Bryan, TX
     - 33.7%
     - $53,541
     - COUNTER-REV: Military feeder
   * - Gainesville, FL
     - 34.8%
     - $51,755
     - COUNTER-REV: Liberal bubble
   * - New York-Newark, NY
     - 27.5%
     - $86,445
     - VELVET GLOVE liberalism

**The College Town Pattern**: University towns dominate rent burden because:

1. Student populations are TRANSIENT = high atomization
2. Students are ASPIRATIONAL LABOR ARISTOCRACY—they foresee survival within
   the system (P(S|A) is high) because they expect professional-managerial
   class integration
3. No organic community bonds to transmit class consciousness
4. Service workers are atomized, serving the student/professional class

**The Exception**: Palestinian solidarity movements (2024 encampments) show that
SPECIFIC international solidarity CAN briefly penetrate the bubble, but this
requires external organizing infrastructure—it doesn't emerge organically.

**The Velvet Glove**: New York/Manhattan shows high rent burden producing
DSA chapters and tenant organizing that explicitly REJECTS revolutionary
politics. The non-profit industrial complex channels grievance into
system-preserving reformism.

**Game Implication**: Rent burden should increase ``AGITATION_ENERGY``, NOT
revolutionary potential. The routing depends on solidarity infrastructure::

    if solidarity_strength > 0:
        consciousness_drift += agitation_energy * k
    else:
        ideology_drift_toward_nationalism += agitation_energy * k

College towns should have NEGATIVE ``solidarity_baseline`` due to transience.
This makes them fascism-prone despite high agitation.

The Contradiction Metros
========================

*High Income Does Not Mean Material Security*

Some metros show both high median income AND severe housing burden. These
workers are labor aristocracy by paycheck but proletariat by experience.
They are historically crucial for both fascism AND revolution.

.. list-table:: High-Income Metros with Severe Housing Crisis
   :header-rows: 1
   :widths: 40 20 20

   * - Metro Area
     - Median Income
     - % 50%+ Burden
   * - Boulder, CO
     - $92,466
     - 31.7%
   * - Los Angeles-Long Beach-Anaheim, CA
     - $81,652
     - 30.0%
   * - San Diego-Chula Vista-Carlsbad, CA
     - $88,240
     - 29.1%
   * - Bridgeport-Stamford-Norwalk, CT
     - $101,194
     - 28.7%
   * - New York-Newark-Jersey City, NY
     - $86,445
     - 27.5%

**Historical Parallel**: The "betrayed middle class" has been key to fascist
movements (Weimar Germany) and revolutionary movements (French Revolution).
Workers who expected prosperity but find precarity are more radicalized than
workers who never expected prosperity.

**Game Implication**: Create ``real_wage_ratio = nominal_income / housing_cost``.
Workers with high nominal income but low real wages should have HIGHER
``consciousness_drift`` sensitivity than low-income workers.

Military and Federal Dominance
==============================

*The Primary Counter-Revolutionary Formation*

.. important::

   **CRITICAL MLM-TW INSIGHT**: Military and federal installations are THE
   dominant factor determining counter-revolutionary stability. This
   OVERWHELMS all other economic factors including rent burden.

   Military towns with adjacent universities are NOT "contradiction zones"—
   the military/federal influence far outweighs student population effects.
   From firsthand organizing experience: revolutionary work is effectively
   impossible in these environments because the majority population has
   DIRECT material stake in imperial apparatus continuation.

.. list-table:: Military/Federal Employment Concentration
   :header-rows: 1
   :widths: 35 12 13 25

   * - Metro Area
     - % Govt
     - Federal
     - MLM-TW Analysis
   * - California-Lexington Park, MD
     - 12.3%
     - 11,330
     - HARD COUNTER-REV: Naval Air Station
   * - Manhattan, KS
     - 11.7%
     - 4,403
     - Fort Riley DOMINATES despite K-State
   * - Sierra Vista-Douglas, AZ
     - 11.0%
     - 6,490
     - Army Intelligence - NSA/CIA presence
   * - Bremerton-Silverdale-Port Orchard, WA
     - 11.0%
     - 19,165
     - Nuclear sub base - clearance culture
   * - Hinesville, GA
     - 9.8%
     - --
     - Fort Stewart - organizing suicide

**Why Military Towns Are Counter-Revolutionary**:

1. **Direct material stake** in imperial apparatus continuation
2. **Self-selection for ideological conformity** (security clearances)
3. **Concentrated state violence capacity** (QRF always available)
4. **Cultural hegemony** of military values in surrounding community
5. **Adjacent universities become MILITARY FEEDERS**, not opposition
   (e.g., Texas A&M Corps of Cadets is largest outside service academies)

**CRITICAL CORRECTION**: Manhattan KS, College Station TX, and Hinesville GA
were incorrectly rated as "revolutionary potential" in preliminary analysis.
Military influence is HEGEMONIC in these territories. University populations
do not create "contradiction zones"—they are absorbed into military culture
or serve as military feeders.

**Game Implication**: ``MILITARY_PRESENCE`` should be the DOMINANT territory
modifier:

- Sets ``consciousness_ceiling`` at 0.3 (cannot exceed even with crisis)
- Reduces ``solidarity_edge_formation`` by 80%
- Increases ``COINTELPRO_effectiveness`` by 200%
- Provides instant QRF deployment (zero response time)
- Creates "informant culture" multiplier on organization exposure

State capitals have weaker but still significant counter-revolutionary effect.
University employment alone (without military) has minimal effect.

Atomization Patterns
====================

*Renters vs. Owners*

Renter concentration proxies for atomization—renters are mobile, have less
stake in local property values, and can be organized (or scattered) more easily.

.. list-table:: Highest Renter Concentration
   :header-rows: 1
   :widths: 45 20 20

   * - Metro Area
     - % Renter
     - Renter Count
   * - Los Angeles-Long Beach-Anaheim, CA
     - 51.2%
     - 2,252,034
   * - Lawrence, KS
     - 49.9%
     - 24,590
   * - Manhattan, KS
     - 49.0%
     - 23,927
   * - New York-Newark-Jersey City, NY
     - 48.2%
     - 3,495,249
   * - San Francisco-Oakland-Berkeley, CA
     - 44.8%
     - 769,393

**Los Angeles**: The only major metro with a renter *majority*. This is the
largest potential organizing base in the United States—2.25 million renter
households concentrated in one metro.

.. list-table:: Lowest Renter Concentration (Counter-Revolutionary Base)
   :header-rows: 1
   :widths: 45 20 20

   * - Metro Area
     - % Renter
     - Notes
   * - The Villages, FL
     - 12.9%
     - Retirement community
   * - Homosassa Springs, FL
     - 16.3%
     - Retirement community
   * - Punta Gorda, FL
     - 17.9%
     - Retirement community
   * - Barnstable Town, MA
     - 19.2%
     - Cape Cod wealth

**Florida Retirement Pattern**: Property-owning retirees with nothing to lose
from fascism and everything to lose from redistribution. These are
counter-revolutionary strongholds.

Production Worker Heartlands
============================

*The Traditional Proletariat*

Production workers—manufacturing, transportation, material moving—are
concentrated in specific industrial metros with union traditions and
concentrated workplaces.

.. list-table:: Production Worker Strongholds
   :header-rows: 1
   :widths: 40 20 20

   * - Metro Area
     - % Production
     - Median Income
   * - Dalton, GA
     - 20.5%
     - $52,898
   * - Elkhart-Goshen, IN
     - 17.1%
     - $61,182
   * - Hickory-Lenoir-Morganton, NC
     - 15.2%
     - $53,163
   * - Sheboygan, WI
     - 15.1%
     - $65,352
   * - Muskegon, MI
     - 15.0%
     - $57,047

**Dalton, GA**: The carpet manufacturing capital of the world. One in five
workers is in production—the highest concentration in any U.S. metro.

**Game Implication**: High production worker concentration should increase
``organization_potential`` (concentrated workplaces) and ``strike_effectiveness``.
However, these workers are also vulnerable to automation/globalization
narratives that fascism exploits.

Income Inequality Distribution
==============================

*The Gini Proxy*

We approximate inequality using the ratio of households earning $100k+ to
households earning under $25k.

.. list-table:: Most Unequal Metros (Highest Top/Bottom Ratio)
   :header-rows: 1
   :widths: 45 20 20

   * - Metro Area
     - Ratio
     - Median Income
   * - San Jose-Sunnyvale-Santa Clara, CA
     - 7.53
     - $138,370
   * - Washington-Arlington-Alexandria, DC
     - 5.91
     - $111,252
   * - San Francisco-Oakland-Berkeley, CA
     - 5.16
     - $118,547

**San Jose**: For every household earning under $25k, there are 7.5 households
earning over $100k. Tech billionaires and service workers share the same metro.
This visible inequality generates agitation but also enables scapegoating.

.. list-table:: Most Equal Metros (Excluding Puerto Rico)
   :header-rows: 1
   :widths: 45 20 20

   * - Metro Area
     - Ratio
     - Median Income
   * - Beckley, WV
     - 0.55
     - $44,466
   * - Brownsville-Harlingen, TX
     - 0.56
     - $43,057
   * - Pine Bluff, AR
     - 0.58
     - $44,756

**Uniform Poverty**: These metros are "equal" because almost everyone is poor.
This is NOT a desirable equality—it's the equality of collective immiseration.
However, reduced internal stratification may ease class solidarity formation.

The Colonial Pattern: Puerto Rico
=================================

*Imperial Extraction in Pure Form*

Puerto Rico metros consistently show the clearest colonial extraction patterns:

.. list-table:: Puerto Rico Economic Indicators
   :header-rows: 1
   :widths: 35 20 20 20

   * - Metro Area
     - Unemployment
     - Median Income
     - Top/Bottom Ratio
   * - Mayagüez
     - 22.7%
     - $16,456
     - 0.06
   * - Yauco
     - 20.7%
     - $16,749
     - 0.02
   * - Ponce
     - 16.2%
     - $18,439
     - 0.06
   * - San Juan-Bayamón-Caguas
     - 14.3%
     - $24,755
     - 0.13

**The Colonial Signature**:

- Unemployment 3-4x mainland average
- Median income 1/4 of mainland average
- Near-zero top/bottom ratio (the "equality of poverty")

This is imperial rent extraction—value flows from Puerto Rico to the mainland,
leaving colonial subjects uniformly impoverished.

**Game Implication**: Puerto Rico should be modeled as INTERNAL_PERIPHERY with
maximum ``extraction_rate`` and minimum ``super_wage_receipt``.

Composite Indices
=================

Revolutionary Potential Index (CORRECTED)
-----------------------------------------

.. warning::

   **FUNDAMENTAL FLAW IN ORIGINAL FORMULA**: The preliminary analysis treated
   rent burden and renter % as positive indicators of revolutionary potential.
   This is ORTHODOX MARXIST ECONOMISM, not MLM-TW analysis.

   Census data measures AGITATION ENERGY, not revolutionary potential.
   Actual revolutionary potential requires LOCAL ASSESSMENT of:

   - Existing solidarity infrastructure (unions, mutual aid, organizing history)
   - Organic community bonds (stable vs transient population)
   - Class composition (aspirational LA vs genuine proletariat)
   - Military/federal presence (dominant counter-revolutionary factor)

.. list-table:: INCORRECTLY Rated High in Preliminary Analysis
   :header-rows: 1
   :widths: 35 15 35

   * - Metro Area
     - Old Score
     - Correction
   * - College Station-Bryan, TX
     - 32.9
     - MILITARY FEEDER (A&M Corps of Cadets)
   * - Bloomington, IN
     - 32.6
     - Aspirational LA, transient, atomized
   * - Athens-Clarke County, GA
     - 32.3
     - Student transience, service economy
   * - Hinesville, GA
     - 31.2
     - FORT STEWART - organizing suicide
   * - Gainesville, FL
     - 31.2
     - Liberal bubble, aspirational LA
   * - Ithaca, NY
     - 30.9
     - Cornell PMC pipeline, velvet glove

.. list-table:: Metros with GENUINE Revolutionary Potential
   :header-rows: 1
   :widths: 40 40

   * - Metro Area
     - Why This Has Potential
   * - Mayagüez, PR
     - Colonial territory, W_c/V_c < 1, independence tradition
   * - Vineland-Bridgeton, NJ
     - Agricultural workers, stable residence, farmworker history
   * - El Centro, CA
     - Imperial Valley agriculture, UFW organizing history
   * - Dalton, GA
     - Industrial proletariat, concentrated workplace
   * - Brownsville-Harlingen, TX
     - Border community, uniform poverty, colonias organizing
   * - Elkhart-Goshen, IN
     - RV manufacturing, union traditions, stable workforce

**Puerto Rico Exception**: Puerto Rico metros DO have genuine revolutionary
potential because:

1. Colonial extraction = W_c/V_c ratio BELOW 1 (true periphery)
2. Non-transient population with organic community roots
3. Historical independence organizing tradition (Nationalists, FALN)
4. No labor aristocracy buffer (uniform poverty)

Puerto Rico is INTERNAL PERIPHERY within US territory—the exception that
proves the rule of core impossibilism.

**Key Insight**: Census data measures AGITATION ENERGY. That energy routes
through the fascist bifurcation:

- WITH solidarity infrastructure → class consciousness
- WITHOUT solidarity infrastructure → national identity / reaction

College towns: HIGH agitation, LOW solidarity (atomization) = FASCISM-PRONE
Military towns: NEGATIVE potential regardless of other factors

Stability Index
---------------

A composite score combining income (35%), low rent burden (30%),
and ownership (35%):

.. list-table:: Top 15 Counter-Revolutionary Strongholds
   :header-rows: 1
   :widths: 45 15

   * - Metro Area
     - Score
   * - San Jose-Sunnyvale-Santa Clara, CA
     - 91.9
   * - Washington-Arlington-Alexandria, DC
     - 84.5
   * - California-Lexington Park, MD
     - 84.4
   * - San Francisco-Oakland-Berkeley, CA
     - 83.9
   * - Ogden-Clearfield, UT
     - 80.4
   * - Minneapolis-St. Paul-Bloomington, MN
     - 78.8
   * - Barnstable Town, MA
     - 78.5
   * - Appleton, WI
     - 77.3
   * - Midland, TX
     - 77.3

**The Utah Pattern**: Utah metros (Ogden, Provo, Salt Lake) appear repeatedly
because of high home ownership, strong community ties (LDS culture), and
conservative ideology. These are fascist stronghold candidates in crisis.

Summary: What the Data Actually Teaches (MLM-TW Corrected)
==========================================================

1. **Labor aristocracy is geographically concentrated** in tech hubs,
   government centers, and military-industrial metros. These workers will
   defend imperialism because they benefit materially. This is CORRECT.

2. **Rent burden is AGITATION ENERGY, not revolutionary potential**. The
   fascist bifurcation formula: *agitation without solidarity = fascism*.
   College towns have high agitation but LOW solidarity due to transience.
   They are COUNTER-REVOLUTIONARY despite material conditions.

3. **Military/federal presence is THE dominant factor**. This overwhelms
   ALL other economic indicators. Military-adjacent college towns are
   NOT contradiction zones—military influence is hegemonic. Organizing
   in these territories is suicide.

4. **The "velvet glove" captures grievance in metro cores**. Manhattan,
   San Francisco, and similar metros have high rent burden but channel
   that energy into liberal reformism (DSA, tenant organizing, electoral
   politics). This is system-preserving, not revolutionary.

5. **Aspirational labor aristocracy ≠ proletariat**. College students
   foresee survival within the system (high P(S|A)). Their current
   suffering is TEMPORARY—they expect professional-managerial integration.
   Transience destroys organic solidarity bonds.

6. **Property ownership + no future horizon = fascist base**. Florida
   retirement communities are counter-revolutionary strongholds. They
   have everything to lose from redistribution, nothing to gain from
   revolution.

7. **Puerto Rico is the exception that proves the rule**. As INTERNAL
   PERIPHERY with W_c/V_c < 1, non-transient population, and independence
   organizing tradition, it represents genuine revolutionary potential
   within US territory. The colonial pattern is pure.

8. **GENUINE organizing targets are stable working-class communities**:

   - Agricultural proletariat with UFW/farmworker history
   - Industrial production workers with union traditions
   - Border communities with colonias organizing experience
   - Colonial territories with independence movements

   NOT college towns. NOT military-adjacent metros. NOT liberal enclaves.

See Also
========

- :doc:`demographics` - Mass Line Refactor and population mechanics
- :doc:`formulas` - Mathematical models for consciousness and survival
- :doc:`../concepts/imperial-rent` - Theory of imperial rent extraction
- :ref:`ai-docs/census-insights.yaml <census-insights>` - Machine-readable data

Technical Reference
===================

The census data is stored in ``data/sqlite/census.sqlite`` and can be queried
directly:

.. code-block:: bash

   # Open SQLite CLI
   mise run data:census-query

   # Example: Top 10 metros by median income
   SELECT m.name, mi.estimate
   FROM census_metro_areas m
   JOIN census_median_income mi ON m.id = mi.metro_id
   ORDER BY mi.estimate DESC LIMIT 10;

See ``src/babylon/data/census/`` for the Python ingestion module.
