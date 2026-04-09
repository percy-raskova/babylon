# Feature Specification: Dynamic Land Ownership Substrate

**Spec ID**: `043-land-ownership-substrate`
**Feature Branch**: `043-land-ownership-substrate`
**Created**: 2026-04-08
**Status**: Draft
**Depends On**: `026-tri-county-economic-substrate`, `030-dpd-lifecycle-circuit`, `038-unified-class-system`

---

## Theoretical Foundation

Babylon previously used ACS home ownership rates as a static, population-level proxy to estimate Labor Aristocracy (LA) share (via an `equity_factor` scaler). This spec replaces that static proxy with a dynamic, mechanistic land ownership system at the tri-county hex substrate level.

### The Core Claim

Home ownership is not a *marker* of the Labor Aristocracy; it **constitutes** the Labor Aristocracy. The mortgage is the co-optation mechanism: it gives households a material stake in the property system (driving material alignment with property values, policing, and exclusion) and binds their class interest to the settler-colonial project.

Property *type* determines class position:
- **Residential real estate with meaningful equity** &rarr; Labor Aristocracy
- **Commercial/industrial property, means of production** &rarr; Bourgeoisie
- **Small business premises (shop, workshop)** &rarr; Petit Bourgeoisie
- **No property, or nominal title without equity** &rarr; Proletariat / Lumpenproletariat

A household's relationship to ownership dictates its class configuration. Ownership transitions are discrete mutations in the class structure.

### Equity Factor
Nominal ownership &ne; LA position. A household in an underwater mortgage or nominally owning a home in a depreciated area (like Detroit hexes where land value is near zero) does not possess the structural material stake that defines the LA. The threshold of meaningful equity separates nominal ownership from the Labor Aristocracy. This is modeled using an endogenous equity threshold test, replacing the statistical `equity_factor` coefficient.

---

## Data Model

The spatial hex mesh defined in Spec `026` tracks land tenure at H3 Resolution 7.

### `HexTenureComposition`

A new frozen Pydantic model integrated into the geographic hex substrate, representing the share of land within the hex.

```python
from pydantic import BaseModel, ConfigDict, model_validator

class HexTenureComposition(BaseModel):
    """Composition of land ownership by tenure type at H3 R7 resolution.
    Each share represents the fraction of land surface area.
    """
    model_config = ConfigDict(frozen=True)

    residential_owner_occupied: float # Constitutes LA households
    residential_rental: float         # Tenants = Proletariat; Landlords = Bourgeoisie/PB
    commercial: float                 # Bourgeoisie
    industrial: float                 # Bourgeoisie (Means of Production)
    public: float                     # State-controlled
    trust_land: float                 # INDIGENOUS filtration / unalienable
    vacant_abandoned: float           # Crisis signature; Lumpenproletariat / Proletariat

    @model_validator(mode="after")
    def validate_conservation(self) -> "HexTenureComposition":
        total = (self.residential_owner_occupied + self.residential_rental +
                 self.commercial + self.industrial + self.public +
                 self.trust_land + self.vacant_abandoned)
        if abs(total - 1.0) > 1e-10:
            raise ValueError(f"Tenure shares must sum to 1.0, got {total}")
        return self
```

---

## Ground Rent Circuit

Ground rent is surplus extraction at the point of circulation, distinct from exploitation (`s/v`) at the point of production. It operates via dyadic landlord-tenant edges.

Marx's distinctions modeled:
- **Absolute Rent**: Baseline rent extracted simply by virtue of the private monopoly over land, functioning as a price floor regardless of the property's condition.
- **Differential Rent I**: Rent extracted due to spatial location advantages (proximity to jobs, services, or transit). E.g., Oakland County hexes extract higher Differential Rent I than Wayne County hexes.
- **Differential Rent II**: Rent derived from capital improvements on the land itself.

### Integration with `ValueTensor4x3`
- **Residential Rent**: Intersects with Variable Capital (`v`). Landlords extract value directly from the worker's reproduction fund, redistributing `v` outward along the graph.
- **Commercial / Industrial Rent**: Intersects with Surplus Value (`s`). Ground rent captures a specific fraction of the surplus value generated at the point of production, separating aggregate surplus into profit of enterprise vs. ground rent.

---

## Discrete Ownership Transitions

Class dynamics flow from the property system as **discrete state machine transitions**. Continuous drift representations (violating Constitution VIII.1) are replaced.

| Transition | Mechanism | Class Effect |
|---|---|---|
| **Purchase** | Proletariat acquires residential property overcoming the meaningful equity threshold. | Proletariat &rarr; LA |
| **Foreclosure** | Financial default; structural dispossession by finance capital. | LA &rarr; Proletariat |
| **Inheritance** | D-P-D' Lifecycle Circuit: intergenerational property transmission. | Sustains LA Reproduction |
| **Eminent Domain** | State `DEVELOP` or `ADMINISTER` action confiscating land. | Displacement; LA &rarr; Proletariat |
| **Abandonment** | Tax delinquency or severe structural obsolescence leading to exit. | LA &rarr; Proletariat; Hex Vacancy Increases |
| **Speculation** | Exchange-value of land drastically decouples from use-value. | Pricing pressure; setup for gentrification |
| **Gentrification** | Coordinated capital infusion shifting hex composition (rental &rarr; commercial / owner_occupied). | Proletariat displacement |

---

## Technical & Constitutional Constraints

### Constitutional Anti-Patterns Addressed
- **VIII.1 (Continuous Quality)**: Ownership changes invoke instant boolean state switches regarding class classification.
- **VIII.3 (Magic Constants)**: Ownership threshold (`equity_factor`) is an absolute test on equity, retrieved from `GameDefines`, not arbitrarily scaled across demographics.
- **VIII.5 (Storing Derived Quantities)**: Household class positioning evaluates the hex tenure composition and dyadic rent edges directly. Redundant storage of class position separate from ownership logic is forbidden.
- **VIII.9 (Pairwise Communities)**: Rent flows form distinct **dyadic edges** (`landlord &rarr; tenant`). They do not utilize the community hyperedge filtration mechanics (e.g., INDIGENOUS filter modifies interpretation, but landlord relationships remain strictly directional dyadic interactions).

---

## Falsifiability Criteria

The dynamic mechanism makes explicitly falsifiable predictions distinct from the static proxy:
1. **Detroit Dispossession**: Massive tax foreclosure and real-estate collapse (property values dropping near/below zero) eliminates the equity factor threshold, tearing down the D-P-D' inheritance mechanism. This correctly reproduces Wayne County's macro-scale demographic shift (LA &rarr; Proletariat demotion) *endogenously*, absent explicit scripting.
2. **Macomb / Oakland Bifurcation**: Differential Rent I enables Oakland County value to swell without an unnatural inflation curve. Given Oakland's locational advantages, its LA capacity must expand natively relative to Wayne County's shrinkage.
3. **Event-Driven Decay**: The class demographic composition of affected hexes will exhibit step-changes strongly correlated with isolated waves of eviction and foreclosure events, failing the test if the metrics demonstrate "smooth" interpolation decays over time.

---

## Dependencies
- `013-melt-basket-visibility`: Feeds the precarity assessments related to structural abandonment.
- `026-tri-county-economic-substrate`: Provides the base geographic structure and economic states that `HexTenureComposition` merges into natively.
- `030-dpd-lifecycle-circuit`: Dictates the inheritance function where property translates directly to intergenerational LA stability.
- `038-unified-class-system`: Alters the class evaluation rules to point at this spec's logic.

## What This Spec Does NOT Include
- A specific definition of housing architecture, unit sizes, or Euclidean zoning laws.
- Fully simulated physics for gentrification/building quality (restricted instead to Marxian capital flows).
