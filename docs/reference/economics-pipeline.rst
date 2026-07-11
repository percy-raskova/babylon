Economics Pipeline Reference (Features 012–016)
=================================================

Technical reference for the five economics modules that compute
capital dynamics, MELT, visibility tensors, throughput position,
and class transitions. These features form a dependency chain from
the ValueTensor4x3 primitive (Feature 011) through to simulated
class distribution evolution.

.. contents:: On this page
   :local:
   :depth: 2

Feature 012: Capital Stock Dynamics
-----------------------------------

Computes accumulated capital stock *K* via the perpetual inventory
method, enabling the TRPF (tendency of the rate of profit to fall)
analysis.

Depreciation Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Preset
     - Rate (δ)
     - Description
   * - ``default()``
     - 0.07
     - Standard annual depreciation
   * - ``slow()``
     - 0.05
     - Long-lived capital (infrastructure)
   * - ``fast()``
     - 0.10
     - Short-lived capital (tech equipment)

Valid range: [0.01, 0.20].

Formulas
~~~~~~~~

**Perpetual inventory method** (TVT Axiom A3):

.. math::

   K_{t+1} = K_t \cdot (1 - \delta) + c_t

Where *c_t* = ``total_c`` from the ValueTensor4x3. Initial
condition uses steady-state:

.. math::

   K_0 = \frac{c_0}{\delta}

**Stock-based profit rate** (TVT Section 3.6):

.. math::

   r_{\text{stock}} = \frac{\sum s_\mu}{K + \sum v_\mu}

**Flow-based profit rate** (from tensor directly):

.. math::

   r_{\text{flow}} = \frac{s}{c + v}

DerivedTensorMetrics
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Field
     - Type
     - Description
   * - ``capital_stock``
     - ``float``
     - Accumulated K via perpetual inventory
   * - ``profit_rate_stock``
     - ``float``
     - s / (K + v) — stock-based
   * - ``profit_rate_flow``
     - ``float``
     - s / (c + v) — flow-based (from tensor)
   * - ``organic_composition``
     - ``float``
     - c / v
   * - ``exploitation_rate``
     - ``float``
     - s / v
   * - ``depreciation_rate``
     - ``float``
     - δ used for this computation
   * - ``tensor``
     - ``ValueTensor4x3``
     - Source tensor

**Implementation:**
:py:class:`babylon.domain.economics.capital_stock.CapitalStockCalculator`

Year range: 2010–2025. Thread-safe via RLock.

Feature 013: MELT and Basket Visibility
----------------------------------------

Computes the Monetary Expression of Labor Time (MELT), basket
visibility, class position classification, and imperial rent per
hour.

MELT (τ)
~~~~~~~~~

**Formula** (TVT Axiom B3):

.. math::

   \tau = \frac{\text{GDP}}{\text{employment} \times 2080}

Where 2080 = HOURS_PER_YEAR (40 hrs/wk × 52 wks). Units:
$/labor-hour. One τ per currency zone (TVT Axiom B4).

.. list-table:: Validation Ranges
   :header-rows: 1
   :widths: 20 40 40

   * - Tier
     - Range
     - Action
   * - Expected
     - $55–75/hr
     - Pass
   * - Warning
     - $40–100/hr
     - Log warning
   * - Fail
     - <$20 or >$200/hr
     - Return error

Basket Visibility (γ_basket)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Formula** (TVT Axiom D3):

.. math::

   \gamma_{\text{basket}} = \frac{1}
   {\frac{\alpha}{\gamma_{\text{import}}} + (1 - \alpha)}

Where α = import share of consumption, γ_import = import
visibility. Edge cases: α=0 → 1.0; α=1 → γ_import.

MVP defaults: α=0.25, γ_import=0.35 → γ_basket=0.68.

**Effective MELT** (TVT Axiom D4):

.. math::

   \tau_{\text{eff}} = \tau \times \gamma_{\text{basket}}

Imperial Rent Per Hour (Φ_hour)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Formula** (TVT Axiom E3):

.. math::

   \Phi_{\text{hour}} = \frac{W}{\tau} \cdot
   \frac{1}{\gamma_{\text{basket}}} - 1

Φ_hour > 0: net extractor (labor aristocracy flow position).
Φ_hour < 0: net exploited. Break-even at W = τ_eff.

**Labor commanded** (TVT Axiom E4):

.. math::

   L_{\text{cmd}} = \frac{W}{\tau \cdot \gamma_{\text{basket}}}

Class Position Classifier
~~~~~~~~~~~~~~~~~~~~~~~~~~

Class position is determined by **wealth percentile** (stock),
not income (flow). Thresholds from Fed Survey of Consumer
Finances:

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Class
     - Threshold
     - Description
   * - BOURGEOISIE
     - ≥ 99th percentile
     - ~$13M+ net worth
   * - PETIT_BOURGEOISIE
     - ≥ 90th percentile
     - ~$1.88M+ net worth
   * - LABOR_ARISTOCRACY
     - ≥ 50th percentile
     - ~$142K+ net worth
   * - PROLETARIAT
     - < 50th percentile
     - Below median wealth
   * - LUMPENPROLETARIAT
     - Excluded from labor
     - PrecarityStatus.EXCLUDED

NationalParameters
~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 60

   * - Field
     - Description
   * - ``tau``
     - National MELT ($/labor-hour)
   * - ``alpha``
     - Import share of consumption
   * - ``gamma_import``
     - Import visibility coefficient
   * - ``gamma_basket``
     - Composite basket visibility
   * - ``tau_effective``
     - τ × γ_basket
   * - ``v_reproduction``
     - Labor cost of reproducing labor power
   * - ``p50_wealth_threshold``
     - ~$142K (LA boundary)
   * - ``p90_wealth_threshold``
     - ~$1.88M (PB boundary)
   * - ``p99_wealth_threshold``
     - ~$13M (Bourgeoisie boundary)

Feature 014: Throughput Position
---------------------------------

Computes county-level throughput intensity and position relative
to the national MELT, with commuter-adjusted variants.

Formulas
~~~~~~~~

**Throughput intensity**:

.. math::

   \tau_{\text{through}} = \frac{\text{GDP}}
   {\text{employment} \times 2080}

**Throughput position** (dimensionless):

.. math::

   \pi = \frac{\tau_{\text{through}}}{\tau_{\text{national}}}

π > 1: county produces more value per labor-hour than national
average. π < 1: below average.

**Commuter-adjusted residence throughput**:

.. math::

   \tau_{\text{res}} = \frac{\text{GDP}}
   {\text{residence\_employment} \times 2080}

Using LODES commuter flow data to distinguish workplace vs
residence employment.

**Supply chain depth** (employment-weighted):

.. math::

   D = \frac{\sum_{i} e_i \cdot d_i}{\sum_{i} e_i}

ThroughputMetrics
~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 60

   * - Field
     - Description
   * - ``tau_through``
     - County throughput intensity ($/labor-hour)
   * - ``pi``
     - Position relative to national MELT
   * - ``supply_chain_depth``
     - Employment-weighted depth [0–5]
   * - ``data_quality``
     - ``"high"`` / ``"medium"`` / ``"low"``

NAICS Depth Scale
~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 25 65

   * - Depth
     - Layer
     - NAICS
   * - 0.0
     - Extraction
     - 11 (Agriculture), 21 (Mining)
   * - 1.5
     - Manufacturing
     - 31, 32, 33
   * - 2.0
     - Transformation
     - 22 (Utilities), 23 (Construction)
   * - 3.0
     - Logistics
     - 42, 48, 49, 56, 81
   * - 4.0
     - Services
     - 44, 45, 51, 54, 61, 62, 71, 72, 92
   * - 5.0
     - Finance
     - 52, 53, 55

Feature 015: Gamma Visibility Tensor
--------------------------------------

Computes the three visibility coefficients and shadow value
transfers that measure how much labor is invisible to the
price system.

Gamma III (γ_III) — Reproductive Labor
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Formula** (TVT Axiom I.5):

.. math::

   \gamma_{\text{III}} = \frac{L_{\text{paid care}}}
   {L_{\text{paid care}} + L_{\text{unpaid care}}}

γ_III < 1: some care labor is naturalized as unpaid (invisible).
US estimate ~0.30 (70% of care work unpaid).

**Fortunati exploitation rate**:

.. math::

   e_F = \frac{1 - \gamma_{\text{III}}}{\gamma_{\text{III}}}

Ratio of invisible to visible care labor.

Data sources: ATUS (unpaid hours), QCEW (paid care sector
employment).

Gamma Import (γ_import)
~~~~~~~~~~~~~~~~~~~~~~~~

**Formula** (Emmanuel-Amin / TVT Axiom C1):

.. math::

   \gamma_{\text{import}} = \sum_i
   \frac{s_i}{\text{ERDI}_i}

Where *s_i* = import share from country *i*, ERDI = Exchange
Rate Deviation Index (GDP_PPP / GDP_MER).

.. list-table:: MVP ERDI Values (Penn World Tables 10.01)
   :header-rows: 1
   :widths: 20 10 70

   * - Country
     - ERDI
     - Note
   * - China
     - 1.80
     - Second-largest import source
   * - Mexico
     - 1.50
     - NAFTA partner
   * - Vietnam
     - 2.50
     - Rising periphery source
   * - India
     - 2.80
     - Highest ERDI in top partners
   * - Germany, Japan
     - 1.00
     - Core countries (no deviation)
   * - Rest of world
     - 2.00
     - Default periphery ERDI

Shadow Value Transfers
~~~~~~~~~~~~~~~~~~~~~~

**Phi III** — reproductive shadow subsidy (TVT Axiom I.5):

.. math::

   \Phi_{\text{III}} = (1 - \gamma_{\text{III}})
   \times L_{\text{unpaid}} \times \tau

**Phi Imperial** — imperial shadow subsidy (TVT Axiom I.2):

.. math::

   \Phi_{\text{imperial}} = (1 - \gamma_{\text{basket}})
   \times \text{Consumption}

.. list-table:: Validation Ranges
   :header-rows: 1
   :widths: 20 25 25 30

   * - Coefficient
     - Expected
     - Warning
     - Fail
   * - γ_III
     - [0.20, 0.40]
     - [0.10, 0.50]
     - Outside [0, 1]
   * - γ_import
     - [0.40, 0.70]
     - [0.30, 0.80]
     - ≤ 0
   * - γ_basket
     - [0.60, 0.85]
     - [0.40, 0.95]
     - ≤ 0

Feature 016: Class Dynamics Engine
-----------------------------------

Simulates class distribution evolution through transition flows:
accumulation (upward mobility), dispossession (downward mobility),
precaritization, and stabilization.

Class Distribution
~~~~~~~~~~~~~~~~~~

Five-class distribution summing to 1.0:

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Class
     - Typical Share
     - Dynamic
   * - Bourgeoisie
     - 1%
     - Fixed (structural)
   * - Petit Bourgeoisie
     - 9%
     - Fixed (structural)
   * - Labor Aristocracy
     - 30–50%
     - Dynamic: gains from accumulation, loses to dispossession
   * - Proletariat
     - 25–45%
     - Dynamic: gains from dispossession, loses to precaritization
   * - Lumpenproletariat
     - 10–25%
     - Dynamic: gains from precaritization, loses to stabilization

Transition Flow Equations
~~~~~~~~~~~~~~~~~~~~~~~~~

Discrete ODE per tick:

.. math::

   \text{LA}' = \text{LA} - d \cdot \text{LA}
   + a \cdot \text{Prol}

.. math::

   \text{Prol}' = \text{Prol} + d \cdot \text{LA}
   - a \cdot \text{Prol}
   - p \cdot \text{Prol} + z \cdot \text{Lum}

.. math::

   \text{Lum}' = \text{Lum} + p \cdot \text{Prol}
   - z \cdot \text{Lum}

Where *d* = dispossession, *a* = accumulation,
*p* = precaritization, *z* = stabilization.

Transition Rate Formulas
~~~~~~~~~~~~~~~~~~~~~~~~~

**Dispossession** (LA → Proletariat):

.. math::

   d = 0.6 \cdot r_f + 0.3 \cdot r_b + 0.1 \cdot r_e

Where r_f = foreclosure rate, r_b = bankruptcy rate,
r_e = eviction rate.

**Accumulation** (Proletariat → LA):

.. math::

   s_{\text{eff}} = s_{\text{base}} +
   \min\left(\frac{\Phi_h \times 2080}{W},\; \phi_{\text{cap}}
   \right)

.. math::

   A = W \cdot s_{\text{eff}}^2

.. math::

   a = \min\left(\frac{A}{W_{\text{threshold}}},\; 0.08\right)

Where W_threshold = $142K (Fed SCF p50 2022).

**Savings rates** (Fed SCF calibrated):

.. list-table::
   :header-rows: 1
   :widths: 30 20

   * - Class
     - Base Rate
   * - Bourgeoisie
     - 0.38
   * - Petit Bourgeoisie
     - 0.20
   * - Labor Aristocracy
     - 0.12
   * - Proletariat
     - 0.03
   * - Lumpenproletariat
     - 0.00

**Precaritization** (Proletariat → Lumpen):

.. math::

   p = u \cdot w_e + r_e \cdot (1 - w_e)

Where u = unemployment rate, w_e = eviction weight (default 0.5).

**Stabilization** (Lumpen → Proletariat):

.. math::

   z = z_0 \cdot (1 - u)

Where z_0 = base stabilization rate (default 0.15).

Crisis Amplification
~~~~~~~~~~~~~~~~~~~~

.. list-table:: Phased Crisis Multipliers
   :header-rows: 1
   :widths: 15 15 17 18 18

   * - Phase
     - Disp ×
     - Precari ×
     - Accum ×
     - Stab ×
   * - NORMAL
     - 1.0
     - 1.0
     - 1.0
     - 1.0
   * - ONSET
     - 1.2
     - 1.5
     - 0.8
     - 0.7
   * - EARLY
     - 1.8
     - 2.5
     - 0.4
     - 0.4
   * - DEEP
     - 3.0
     - 3.5
     - 0.1
     - 0.2
   * - RECOVERY
     - 1.3
     - 1.2
     - 0.6
     - 0.5

Dependency Chain
----------------

.. code-block:: text

   Feature 011 (ValueTensor4x3)
     ├── Feature 012 (K from total_c via perpetual inventory)
     ├── Feature 013 (τ from GDP/employment, γ_basket, Φ_hour)
     │     ├── Feature 014 (π = τ_through / τ_national)
     │     └── Feature 016 (AccumulationResult uses Φ_hour)
     └── Feature 015 (γ_III, γ_import → γ_basket, Φ_III)

All features share ``NoDataSentinel`` from
:py:mod:`babylon.domain.economics.tensor` as the universal missing-data
carrier.

See Also
--------

- :doc:`/concepts/economics-pipeline-theory` — Theoretical
  exposition of the economics pipeline
- :doc:`/reference/tensor-primitive` — ValueTensor4x3 reference
- :doc:`/reference/volume-i-production` — Volume I mechanisms
- :doc:`/reference/formulas` — Complete formula reference
