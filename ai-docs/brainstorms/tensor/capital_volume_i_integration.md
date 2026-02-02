# Capital Volume I Integration

## The Production of Surplus Value: What Babylon Needs

**Status**: Gap Analysis & Integration Specification
**Depends On**: ValueTensor4x3, Department Schemata, QCEW Loaders
**Scope**: Foundational concepts for value production that aren't covered in Volumes II/III docs

---

## 1. Volume I Structure and Coverage Assessment

Volume I analyzes **production** — the extraction of surplus value at the point of production. This is the foundation on which Volumes II (circulation) and III (distribution) build.

| Part | Topic | Babylon Status |
|------|-------|----------------|
| I | Commodities and Money | **Implicit** — value-form in tensor, fetishism NOT modeled |
| II | Transformation of Money into Capital | **Covered in Vol II doc** — M-C-M' circuit |
| III | Absolute Surplus-Value | **Partial** — c/v/s modeled, working day limits NOT modeled |
| IV | Relative Surplus-Value | **NOT modeled** — subsumption, machinery effects missing |
| V | Absolute AND Relative Surplus-Value | **NOT modeled** — combined dynamics |
| VI | Wages | **Partial** — wage determination implicit in v, national differences NOT explicit |
| VII | Accumulation of Capital | **Critical gap** — Reserve Army NOT modeled, concentration/centralization missing |
| VIII | Primitive Accumulation | **Critical gap** — dispossession NOT formalized despite settler colonialism frame |

**Key Insight**: Babylon has a tensor for value composition (c, v, s) but lacks the *dynamics* that generate those values — specifically, the mechanisms that determine the *length* of the working day, the *relative* productivity gains from machinery, and the *reserve army* that disciplines labor.

---

## 2. Critical Gaps Requiring Implementation

### 2.1 The Reserve Army of Labor (CRITICAL)

**Volume I, Part 7, Chapter 25: The General Law of Capitalist Accumulation**

This is the most significant gap. Marx shows that capital accumulation necessarily produces a "relative surplus population" — workers rendered unemployed by mechanization who form a reserve army that:

1. **Disciplines employed workers**: Threat of replacement suppresses wage demands
2. **Provides elastic labor supply**: Absorbs expansion during boom, expelled during bust
3. **Depresses wages toward subsistence**: Competition among unemployed drives wages down

**Current State**: Babylon mentions "reserve_army_size: float" in `CounterTendencyStrength` (Vol III doc) but has no explicit model of reserve army *dynamics* — how it forms, its composition, or its effect on v.

**Required Model**:

```python
class ReserveArmyState(BaseModel):
    """Industrial reserve army composition and dynamics.

    Marx identifies three forms:
    1. Floating: Regularly expelled/absorbed by industry cycles
    2. Latent: Agricultural/domestic workers available for industrial absorption
    3. Stagnant: Chronically underemployed, irregular work

    Plus the pauperized layer (lumpenproletariat).
    """

    fips_code: str
    year: int

    # Stock measures
    floating_reserve: int
    """Workers between jobs, counted in U-3."""

    latent_reserve: int
    """Underemployed, discouraged workers, counted in U-6 - U-3."""

    stagnant_reserve: int
    """Chronic irregular employment, gig workers, part-time wanting full-time."""

    pauperized: int
    """Unable to work, institutionalized, disabled without accommodation."""

    @computed_field
    def total_reserve(self) -> int:
        """Total relative surplus population."""
        return self.floating_reserve + self.latent_reserve + self.stagnant_reserve

    @computed_field
    def reserve_ratio(self) -> float:
        """Reserve as fraction of labor force — key disciplinary metric."""
        # Higher ratio = more disciplinary pressure on wages
        ...

    @computed_field
    def wage_pressure(self) -> float:
        """Estimated downward pressure on wages from reserve army.

        When reserve_ratio is high, workers compete for jobs,
        accepting lower wages. This is a counter-tendency to TRPF
        that increases s/v.
        """
        # Empirically calibrated from Phillips curve literature
        ...


class ReserveArmyDynamics(BaseModel):
    """Flow dynamics of reserve army formation and absorption."""

    # Inflows (formation)
    mechanization_displacement: int
    """Workers displaced by machinery per tick."""

    firm_failures: int
    """Workers from bankrupt enterprises."""

    deskilling_redundancy: int
    """Skilled workers made redundant by division of labor."""

    # Outflows (absorption)
    expansion_absorption: int
    """Workers hired during expansion."""

    new_sector_absorption: int
    """Workers absorbed by new industries."""

    emigration: int
    """Workers leaving the territory."""
```

**Data Sources**:
- BLS: U-3, U-6 unemployment rates
- BLS: Part-time for economic reasons (PTER)
- BLS: Discouraged workers, marginally attached
- Census: Labor force participation rate by demographics

**Integration Point**: The reserve army directly affects the computation of v in the tensor. When reserve_ratio is high, v can be pushed *below* the value of labor power — wages below subsistence. This is one of Marx's counter-tendencies to TRPF.

---

### 2.2 Primitive Accumulation / Ongoing Dispossession (CRITICAL)

**Volume I, Part 8: The So-Called Primitive Accumulation**

Marx's account of the "secret of primitive accumulation" — the forcible separation of producers from their means of production — is foundational to Babylon's settler colonialism frame. But this isn't just historical origin story; **primitive accumulation is ongoing**.

**Current State**: The system prompt mentions "settler colonialism is the frame; gentrification is internal colonization post-frontier" but there's no explicit model of dispossession mechanics.

**Theoretical Claim**: Gentrification *is* primitive accumulation operating within the imperial core — a transfer of accumulated wealth (housing equity) from internal colonies to settler populations through:

1. **Direct dispossession**: Foreclosure, eviction, eminent domain
2. **Displacement through rent extraction**: Rising costs force relocation
3. **Devaluation-revaluation cycles**: Devalue neighborhood → buy cheap → revalue → extract rent

**Required Model**:

```python
class DispossessionEvent(BaseModel):
    """A discrete act of primitive accumulation.

    Tracks the transfer of accumulated wealth/property
    from one class/territory to another through extra-economic means.
    """

    event_id: str
    tick: int

    # Parties
    dispossessed_entity: str
    """Who loses property/wealth."""

    appropriator_entity: str
    """Who gains — often a class category, not individual."""

    # What's transferred
    dispossession_type: DispossessionType
    """FORECLOSURE, EVICTION, TAX_SALE, EMINENT_DOMAIN, WAGE_THEFT, etc."""

    asset_type: str
    """Housing, land, business, pension, etc."""

    value_transferred: Currency
    """Monetary value of transferred asset."""

    labor_time_transferred: float
    """Value in SNLT — accumulated labor being expropriated."""


class DispossessionType(StrEnum):
    """Categories of primitive accumulation mechanisms."""

    FORECLOSURE = "foreclosure"
    """Bank seizure of mortgaged property."""

    EVICTION = "eviction"
    """Removal of tenant, loss of accumulated improvements."""

    TAX_SALE = "tax_sale"
    """Seizure for unpaid property taxes."""

    EMINENT_DOMAIN = "eminent_domain"
    """State seizure for 'public use' — often highways, stadiums."""

    WAGE_THEFT = "wage_theft"
    """Unpaid wages, tip theft, misclassification."""

    INCARCERATION_SEIZURE = "incarceration"
    """Asset forfeiture, job loss, family disruption from carceral system."""

    PENSION_DEFAULT = "pension_default"
    """Corporate bankruptcy eliminating earned pension."""

    GENTRIFICATION_DISPLACEMENT = "displacement"
    """Forced relocation due to rent increases beyond affordability."""


class TerritoryDispossessionState(BaseModel):
    """Aggregate dispossession dynamics for a territory."""

    fips_code: str
    year: int

    # Flow measures
    foreclosure_rate: float
    """Foreclosures per 1000 mortgaged units."""

    eviction_rate: float
    """Evictions per 1000 renter households."""

    displacement_rate: float
    """Net out-migration due to housing costs."""

    # Stock measures
    concentrated_ownership: float
    """Fraction of housing owned by institutional investors."""

    absentee_landlord_share: float
    """Fraction of rentals owned by non-residents."""

    @computed_field
    def dispossession_intensity(self) -> float:
        """Aggregate primitive accumulation pressure."""
        return (
            self.foreclosure_rate * FORECLOSURE_WEIGHT +
            self.eviction_rate * EVICTION_WEIGHT +
            self.displacement_rate * DISPLACEMENT_WEIGHT
        )
```

**Data Sources**:
- Census: Housing tenure changes, migration patterns
- Eviction Lab: Eviction filings and executions by county
- CoreLogic/ATTOM: Foreclosure rates
- Census: Institutional ownership rates (new in 2020 ACS)
- BLS: Wage and hour complaints

**Integration with Detroit Case Study**: This model directly supports the gentrification analysis. Wayne County → Oakland County value transfer can be quantified as accumulated dispossession events plus ongoing rent extraction.

---

### 2.3 The Working Day (Moderate Priority)

**Volume I, Part 3, Chapter 10: The Working Day**

Marx shows that the length of the working day is not economically determined but is the outcome of class struggle. The working day has:

1. **Minimum**: Time to reproduce labor power (necessary labor)
2. **Maximum**: Physical/moral limits of human endurance
3. **Actual**: Determined by balance of class forces

**Current State**: The tensor captures v (wages) and s (surplus), but doesn't model *how* surplus is extracted — whether through **absolute surplus value** (lengthening the working day) or **relative surplus value** (increasing productivity during a fixed day).

**Why This Matters**: The distinction affects consciousness dynamics. Absolute surplus value extraction is *visible* — workers experience it as longer hours, more intense work. Relative surplus value extraction is *invisible* — workers may not perceive intensification.

```python
class WorkingDayState(BaseModel):
    """Characteristics of the working day for a territory/sector.

    Absolute surplus value = extending working day beyond necessary labor
    Relative surplus value = reducing necessary labor time through productivity
    """

    fips_code: str
    naics_sector: str
    year: int

    # Time components
    avg_weekly_hours: float
    """Average actual hours worked per week."""

    necessary_labor_hours: float
    """Hours to produce value equivalent to wages (v)."""

    surplus_labor_hours: float
    """Hours producing surplus value (s)."""

    # Intensity
    labor_intensity_index: float
    """Output per hour relative to baseline — captures speedup."""

    # Limits
    legal_limit: float | None
    """Statutory maximum hours (if any)."""

    physical_limit: float
    """Estimated physiological maximum sustainable hours."""

    @computed_field
    def absolute_sv_margin(self) -> float:
        """Room to extend working day (toward physical limit)."""
        return self.physical_limit - self.avg_weekly_hours

    @computed_field
    def relative_sv_index(self) -> float:
        """Productivity gains reducing necessary labor time."""
        # Higher = more relative surplus value extraction
        return self.labor_intensity_index

    @computed_field
    def exploitation_mode(self) -> str:
        """Primary mode of surplus extraction."""
        if self.avg_weekly_hours > 45 and self.labor_intensity_index < 1.1:
            return "ABSOLUTE_DOMINANT"
        elif self.avg_weekly_hours <= 40 and self.labor_intensity_index > 1.2:
            return "RELATIVE_DOMINANT"
        else:
            return "MIXED"
```

**Data Sources**:
- BLS: Average weekly hours by industry
- BLS: Productivity indices (output per hour)
- BLS: Unit labor costs
- ATUS: Time use for work vs. non-work

---

### 2.4 Subsumption of Labor Under Capital (Lower Priority)

**Volume I, Part 4, Chapters 13-15: Cooperation, Manufacture, Machinery**

Marx distinguishes:

1. **Formal Subsumption**: Worker retains craft knowledge but works for wages
2. **Real Subsumption**: Labor process itself reorganized by capital (Taylorism, assembly line, algorithmic management)

This affects the *qualitative* character of labor — and consciousness.

**Current State**: Not modeled. The tensor treats all labor as homogeneous abstract labor.

**Why It Matters**: Workers under formal subsumption retain potential independence (could return to craft production). Workers under real subsumption are *deskilled* — their labor power has lower value because it's more easily replaceable.

```python
class SubsumptionState(StrEnum):
    """Mode of labor's subordination to capital."""

    FORMAL = "formal"
    """Worker sells labor power but retains control of labor process.
    Examples: Uber driver, freelance developer, artisan."""

    REAL = "real"
    """Capital controls labor process, worker deskilled.
    Examples: Assembly line, call center, warehouse picker."""

    HYBRID = "hybrid"
    """Mixed — some autonomy within capital-controlled framework.
    Examples: Professional services with billable hours."""


class SectorSubsumption(BaseModel):
    """Subsumption characteristics by industry sector."""

    naics_code: str
    year: int

    formal_share: float
    """Fraction of employment under formal subsumption."""

    real_share: float
    """Fraction under real subsumption."""

    avg_skill_level: float
    """Proxy: years of training required."""

    automation_exposure: float
    """Fraction of tasks automatable with current technology."""

    @computed_field
    def deskilling_pressure(self) -> float:
        """Tendency toward real subsumption and devaluation of labor power."""
        return self.automation_exposure * (1 - self.avg_skill_level / 20)
```

**Data Sources**:
- O*NET: Occupation skill requirements
- McKinsey/Brookings: Automation exposure indices
- BLS: Employment by occupation within industry

---

### 2.5 Concentration and Centralization of Capital (Lower Priority)

**Volume I, Part 7, Chapter 25**

Marx distinguishes:

1. **Concentration**: Individual capitals grow through accumulation (reinvested surplus)
2. **Centralization**: Existing capitals combine (mergers, acquisitions)

Centralization can proceed faster than concentration — it redistributes existing capital without requiring new accumulation.

**Current State**: Not modeled. Lenin's extension (monopoly capital) is discussed in the corpus but not formalized.

```python
class CapitalConcentrationState(BaseModel):
    """Concentration and centralization metrics for a territory/sector."""

    fips_code: str | None
    naics_code: str
    year: int

    # Concentration (size distribution)
    herfindahl_index: float
    """Market concentration: sum of squared market shares."""

    top_4_share: float
    """CR4: Share held by top 4 firms."""

    avg_establishment_size: int
    """Average employees per establishment."""

    # Centralization (M&A activity)
    merger_volume: Currency
    """Value of M&A activity in sector."""

    private_equity_share: float
    """Fraction of firms PE-owned."""

    @computed_field
    def monopoly_tendency(self) -> str:
        """Assess competition → monopoly progression."""
        if self.herfindahl_index > 0.25:
            return "MONOPOLY"
        elif self.herfindahl_index > 0.15:
            return "OLIGOPOLY"
        else:
            return "COMPETITIVE"
```

**Data Sources**:
- Census: Business Dynamics Statistics
- Census: Concentration ratios by industry
- SEC: M&A filings
- Pitchbook/Preqin: PE ownership data

---

## 3. Concepts Already Adequately Covered

### 3.1 Value Composition (c, v, s)

**Covered in**: `tensor.py`, `DepartmentRow`, `ValueTensor4x3`

The fundamental value categories are implemented:
- `c`: Constant capital (dead labor transferred)
- `v`: Variable capital (wages, living labor)
- `s`: Surplus value (unpaid labor)

Derived ratios also present:
- `organic_composition`: c/v
- `exploitation_rate`: s/v
- `profit_rate`: s/(c+v)

### 3.2 Labor-Power as Commodity

**Covered in**: Department III formalization, corpus texts

The unique character of labor power — that it produces more value than it costs to reproduce — is the theoretical foundation. Department III explicitly models the production of labor power itself.

### 3.3 Reproduction Schemas

**Covered in**: `capital_volume_ii_integration.md`

Simple and extended reproduction conditions are modeled. The balance equations between departments are specified.

### 3.4 Two-Fold Character of Labor

**Covered implicitly**: The distinction between concrete labor (use-value production) and abstract labor (value production) is implicit in the SNLT calculations and UseValue types.

---

## 4. Integration Architecture

### 4.1 How Reserve Army Affects the Tensor

```
ReserveArmyState
    │
    ├── wage_pressure
    │   │
    │   └──► ValueTensor4x3.v (downward pressure when reserve_ratio high)
    │
    └── labor_supply_elasticity
        │
        └──► ReproductionConditions.labor_supply_adequate (Vol II)


Connection to Counter-Tendencies (Vol III):

reserve_army_size ──► CounterTendencyStrength.reserve_army_size
                      │
                      └──► Offsets TRPF by enabling increased s/v
```

### 4.2 How Dispossession Flows Through the System

```
DispossessionEvent(s)
    │
    ├──► Value transfer between territories
    │    Wayne County → Oakland County
    │
    ├──► Class decomposition trigger
    │    LaborAristocracy → Proletariat (loss of housing equity)
    │
    └──► Imperial rent component
         Φ includes ongoing primitive accumulation
```

### 4.3 New Data Loaders Required

```
src/babylon/data/
├── bls/
│   ├── unemployment_loader.py  # U-3, U-6, PTER
│   └── hours_loader.py         # Average weekly hours
├── eviction_lab/
│   └── eviction_loader.py      # Eviction filings by county
├── census/
│   └── institutional_ownership_loader.py  # Housing ownership patterns
└── attom/
    └── foreclosure_loader.py   # Foreclosure rates
```

### 4.4 Schema Extensions

```sql
-- Reserve army state by county-year
CREATE TABLE reserve_army_state (
    fips_code TEXT,
    year INTEGER,
    floating_reserve INTEGER,
    latent_reserve INTEGER,
    stagnant_reserve INTEGER,
    pauperized INTEGER,
    reserve_ratio REAL,
    PRIMARY KEY (fips_code, year)
);

-- Dispossession events
CREATE TABLE dispossession_events (
    event_id TEXT PRIMARY KEY,
    tick INTEGER,
    fips_code TEXT,
    dispossession_type TEXT,
    value_transferred REAL,
    dispossessed_class TEXT,
    appropriator_class TEXT
);

-- Working day by sector
CREATE TABLE working_day_state (
    fips_code TEXT,
    naics_sector TEXT,
    year INTEGER,
    avg_weekly_hours REAL,
    labor_intensity_index REAL,
    exploitation_mode TEXT,
    PRIMARY KEY (fips_code, naics_sector, year)
);
```

---

## 5. Theoretical Summary

### 5.1 What Volume I Adds to Babylon

| Concept | Theoretical Contribution | Simulation Implementation | Priority |
|---------|-------------------------|---------------------------|----------|
| **Reserve Army** | Explains wage discipline, why v can fall below reproduction | Explicit model with demographic composition | **CRITICAL** |
| **Primitive Accumulation** | Explains ongoing dispossession, gentrification mechanics | DispossessionEvent tracking | **CRITICAL** |
| **Working Day** | Absolute vs relative surplus value distinction | WorkingDayState with exploitation mode | Moderate |
| **Subsumption** | Formal vs real — affects consciousness and replaceability | SectorSubsumption classification | Lower |
| **Concentration/Centralization** | Capital consolidation dynamics, monopoly tendency | Market structure metrics | Lower |
| **Commodity Fetishism** | Mystification of social relations as thing-relations | Consciousness model extension | Deferred |

### 5.2 Connection to Existing Framework

```
PRODUCTION (Volume I) ← THIS DOCUMENT
    │
    │ Reserve army disciplines v
    │ Dispossession transfers accumulated value
    │ Working day determines absolute/relative s
    │
    ▼
CIRCULATION (Volume II)
    │
    │ Circuit dynamics: M - C ... P ... C' - M'
    │ Turnover affects annual surplus
    │
    ▼
DISTRIBUTION (Volume III)
    │
    │ Surplus divides: s → profit + interest + rent
    │ TRPF + counter-tendencies (including reserve army)
```

### 5.3 Detroit Case Study Integration

The Volume I concepts directly support the Detroit analysis:

1. **Reserve Army**: Detroit's 2008-2012 crisis created massive floating reserve → enabled super-exploitation of remaining workers and wage suppression

2. **Primitive Accumulation**: Foreclosure wave 2008-2012 was largest peacetime dispossession event in US history. Wayne County lost billions in accumulated housing equity → transferred to institutional investors and eventually Oakland County settlers

3. **Working Day**: Gig economy growth in Detroit represents return of absolute surplus value extraction (long hours, multiple jobs) plus platform-mediated real subsumption

---

## 6. Implementation Priorities

### Phase 1: Reserve Army (Highest Priority)

1. Add BLS unemployment loaders (U-3, U-6, PTER, discouraged)
2. Create `ReserveArmyState` model with demographic decomposition
3. Integrate wage_pressure into tensor hydration
4. Validate against historical Wayne County data

### Phase 2: Primitive Accumulation

1. Add Eviction Lab data loader
2. Add foreclosure rate loader (ATTOM or CoreLogic)
3. Create `DispossessionEvent` ledger
4. Build gentrification tracking for Wayne/Oakland

### Phase 3: Working Day

1. Add BLS hours and productivity loaders
2. Create `WorkingDayState` model
3. Classify sectors by exploitation mode
4. Integrate with consciousness dynamics

### Phase 4: Subsumption and Concentration

1. Add O*NET skill data
2. Add Census concentration ratios
3. Create sector classification system
4. Link to deskilling pressure and reserve army formation

---

## 7. Falsification Criteria

Volume I integration enables new empirical tests:

1. **Reserve Army Effect**: Does higher U-6 predict lower wage growth in following quarters? (Should see negative coefficient)

2. **Dispossession and Class Position**: Do dispossession events predict downward class mobility? (Foreclosure → Labor Aristocracy → Proletariat transition)

3. **Working Day Mode**: Do sectors with ABSOLUTE_DOMINANT exploitation show different consciousness patterns than RELATIVE_DOMINANT?

4. **Subsumption and Organizing**: Is formal subsumption correlated with higher union density? (Workers with more autonomy have more capacity to organize)

Each of these can be tested against QCEW/BLS/Census data within the Detroit case study timeframe.
