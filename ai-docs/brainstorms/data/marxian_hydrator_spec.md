# MarxianHydrator Technical Specification

**Status:** Ready for Implementation
**Dependencies:** `DepartmentMapper`, QCEW fact tables, BEA industry tables, `dim_county`
**Output:** `ValueTensor4x3` per county-year

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         MarxianHydrator                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌───────────────────┐    ┌────────────────────┐   │
│  │   QCEW DB    │───▶│ DepartmentMapper  │───▶│  ValueTensor4x3    │   │
│  │ (wages by    │    │ (NAICS → Dept     │    │  (c, v, s by row)  │   │
│  │  NAICS)      │    │  allocation)      │    │                    │   │
│  └──────────────┘    └───────────────────┘    └────────────────────┘   │
│         │                                              ▲                │
│         │            ┌───────────────────┐             │                │
│         └───────────▶│  BEA Ratios       │─────────────┘                │
│                      │  (s/v by sector)  │                              │
│                      └───────────────────┘                              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Data Flow

### Step 1: Extract QCEW wages by NAICS for county-year

```sql
SELECT
    q.naics_code,
    q.annual_avg_emplvl AS employment,
    q.total_annual_wages AS wages_v
FROM fact_qcew_annual q
JOIN dim_county c ON q.county_id = c.county_id
JOIN dim_industry i ON q.industry_id = i.industry_id
WHERE c.fips_code = :fips
  AND q.year = :year
  AND q.own_code = '5'  -- Private sector only
  AND i.naics_level >= 2  -- Exclude aggregates
```

### Step 2: Allocate wages to departments via DepartmentMapper

```python
from department_mapper import DepartmentMapper, Department

mapper = DepartmentMapper.from_yaml("naics_to_dept.yaml")
dept_wages: dict[Department, float] = {d: 0.0 for d in Department}

for naics_code, wages in qcew_records:
    allocation = mapper.allocate_value(naics_code, wages)
    if allocation:  # None if excluded (NAICS 92)
        for dept, val in allocation.items():
            dept_wages[dept] += val
```

### Step 3: Derive surplus (s) from BEA value-added ratios

**Key insight:** BEA provides Value Added = Compensation + Gross Operating Surplus.
At national level: `s/v ≈ (Value_Added - Compensation) / Compensation`

```sql
-- National s/v ratios by BEA industry (precomputed, stored in dim_bea_industry or separate table)
SELECT
    b.bea_code,
    b.industry_name,
    (b.value_added - b.compensation) / NULLIF(b.compensation, 0) AS surplus_rate
FROM bea_industry_accounts b
WHERE b.year = :year
```

**Department-level s/v derivation:**

| Department | Typical Industries | Expected s/v Range | Rationale |
|------------|-------------------|-------------------|-----------|
| I (Means of Production) | Mining, Machinery, Chemicals | 1.5 - 3.0 | High organic composition, capital-intensive |
| IIa (Necessary Consumption) | Food retail, Basic healthcare | 0.8 - 1.5 | Labor-intensive, competitive margins |
| IIb (Luxury) | Jewelry, Golf courses, Fine dining | 2.0 - 4.0 | High markups, monopoly rents |
| III (Reproduction) | Childcare, Private households | 0.5 - 1.0 | Suppressed wages, low capital |

**Implementation:** Weight BEA industry s/v ratios by their contribution to each department (via NAICS-BEA concordance and DepartmentMapper weights).

### Step 4: Estimate constant capital (c) from BEA intermediate inputs

```sql
-- Intermediate inputs / gross output ratio by BEA industry
SELECT
    b.bea_code,
    b.intermediate_inputs / NULLIF(b.gross_output, 0) AS c_ratio
FROM bea_industry_accounts b
WHERE b.year = :year
```

For county-level: `c = wages * (industry_avg_c_ratio / industry_avg_v_ratio)`

---

## 3. Output Schema: ValueTensor4x3

```python
from pydantic import BaseModel
from enum import Enum

class Department(str, Enum):
    I = "means_of_production"
    IIa = "necessary_consumption"
    IIb = "luxury_consumption"
    III = "social_reproduction"

class ValueComponent(str, Enum):
    c = "constant_capital"
    v = "variable_capital"
    s = "surplus_value"

class DepartmentRow(BaseModel):
    """Single row of the value tensor."""
    c: float  # Constant capital (intermediate inputs)
    v: float  # Variable capital (wages)
    s: float  # Surplus value (profit + rent + interest)

    @property
    def total_value(self) -> float:
        return self.c + self.v + self.s

    @property
    def organic_composition(self) -> float:
        """c/v ratio."""
        return self.c / self.v if self.v > 0 else float('inf')

    @property
    def exploitation_rate(self) -> float:
        """s/v ratio."""
        return self.s / self.v if self.v > 0 else 0.0

class ValueTensor4x3(BaseModel):
    """4x3 value tensor for a county-year."""
    fips_code: str
    year: int

    dept_I: DepartmentRow    # Means of Production
    dept_IIa: DepartmentRow  # Necessary Consumption
    dept_IIb: DepartmentRow  # Luxury Consumption
    dept_III: DepartmentRow  # Social Reproduction

    # Metadata
    naics_granularity: float  # Avg NAICS digits used (data quality metric)
    excluded_wages: float     # NAICS 92 wages (tracked but outside tensor)

    @property
    def total_c(self) -> float:
        return self.dept_I.c + self.dept_IIa.c + self.dept_IIb.c + self.dept_III.c

    @property
    def total_v(self) -> float:
        return self.dept_I.v + self.dept_IIa.v + self.dept_IIb.v + self.dept_III.v

    @property
    def total_s(self) -> float:
        return self.dept_I.s + self.dept_IIa.s + self.dept_IIb.s + self.dept_III.s

    @property
    def profit_rate(self) -> float:
        """r = s / (c + v)"""
        denom = self.total_c + self.total_v
        return self.total_s / denom if denom > 0 else 0.0
```

---

## 4. Implementation: MarxianHydrator Class

```python
class MarxianHydrator:
    """Hydrates ValueTensor4x3 from database for a county-year."""

    def __init__(
        self,
        session: Session,
        dept_mapper: DepartmentMapper,
        bea_ratios: BEASurplusRatios,  # Preloaded national ratios
    ):
        self.session = session
        self.dept_mapper = dept_mapper
        self.bea_ratios = bea_ratios

    def hydrate(self, fips_code: str, year: int) -> ValueTensor4x3:
        """Generate tensor for county-year."""

        # 1. Pull QCEW wages by NAICS
        qcew_records = self._fetch_qcew(fips_code, year)

        # 2. Allocate to departments
        dept_v = self._allocate_wages(qcew_records)
        excluded_v = self._sum_excluded(qcew_records)

        # 3. Derive s from BEA ratios
        dept_s = self._derive_surplus(qcew_records, dept_v)

        # 4. Derive c from BEA intermediate input ratios
        dept_c = self._derive_constant_capital(qcew_records, dept_v)

        # 5. Compute data quality metric
        granularity = self._compute_granularity(qcew_records)

        return ValueTensor4x3(
            fips_code=fips_code,
            year=year,
            dept_I=DepartmentRow(c=dept_c[Department.I], v=dept_v[Department.I], s=dept_s[Department.I]),
            dept_IIa=DepartmentRow(c=dept_c[Department.IIa], v=dept_v[Department.IIa], s=dept_s[Department.IIa]),
            dept_IIb=DepartmentRow(c=dept_c[Department.IIb], v=dept_v[Department.IIb], s=dept_s[Department.IIb]),
            dept_III=DepartmentRow(c=dept_c[Department.III], v=dept_v[Department.III], s=dept_s[Department.III]),
            naics_granularity=granularity,
            excluded_wages=excluded_v,
        )

    def _derive_surplus(
        self,
        qcew_records: list[tuple[str, float]],
        dept_v: dict[Department, float],
    ) -> dict[Department, float]:
        """
        Derive s for each department using BEA-weighted s/v ratios.

        For each QCEW record:
          1. Map NAICS → BEA industry via concordance
          2. Get BEA industry's s/v ratio
          3. Weight by department allocation
        """
        dept_s: dict[Department, float] = {d: 0.0 for d in Department}

        for naics_code, wages in qcew_records:
            # Get department allocation weights
            alloc = self.dept_mapper.get_allocation(naics_code)
            if alloc is None:
                continue

            # Get BEA s/v ratio for this NAICS (via concordance)
            sv_ratio = self.bea_ratios.get_sv_ratio(naics_code)

            # Distribute surplus across departments
            for dept in Department:
                weight = getattr(alloc, dept.value)
                if weight > 0:
                    dept_s[dept] += wages * weight * sv_ratio

        return dept_s
```

---

## 5. Deferred: Imperial Rent

**Decision:** Do NOT subtract imperial rent at county level for MVP.

**Rationale:** Imperial rent (Φ = W_c - V_c) is a *global* structural property, not a local adjustment. A county's wages are high because the county is embedded in core-periphery flows, not because of a peelable local factor.

**Future approach:** When we instantiate the 4-node global model, imperial rent emerges from the inter-node flow tensor. Core counties' tensors will show elevated v relative to periphery counties, and Φ is computed as the difference—not stipulated.

**For now:** The county-level tensor captures the *local* reproduction dynamics. Imperial rent calibration happens at the global aggregation layer against Piketty/WID benchmarks.

---

## 6. Verification Tests

### Test 1: Department Allocation Sanity

```python
def test_allocation_sums_to_total():
    """All wages should be allocated (excluding NAICS 92)."""
    tensor = hydrator.hydrate("26163", 2020)  # Wayne County

    total_qcew_private = fetch_total_private_wages("26163", 2020)
    allocated = tensor.total_v + tensor.excluded_wages

    assert abs(allocated - total_qcew_private) < 1000  # Within $1K tolerance
```

### Test 2: Dept III Isolation

```python
def test_dept_iii_contains_reproductive_labor():
    """Dept III should contain only NAICS 814 and 6244."""
    tensor = hydrator.hydrate("26163", 2020)

    # Fetch direct wages for 814 + 6244
    reproductive_wages = fetch_wages_for_naics(["814", "6244"], "26163", 2020)

    assert abs(tensor.dept_III.v - reproductive_wages) < 1000
```

### Test 3: Gentrification Signal

```python
def test_gentrification_shifts_iia_to_iib():
    """Oakland County should have higher IIb/IIa ratio than Wayne."""
    wayne = hydrator.hydrate("26163", 2020)
    oakland = hydrator.hydrate("26125", 2020)

    wayne_ratio = wayne.dept_IIb.v / wayne.dept_IIa.v
    oakland_ratio = oakland.dept_IIb.v / oakland.dept_IIa.v

    # Oakland (affluent suburb) should show more luxury consumption
    assert oakland_ratio > wayne_ratio
```

### Test 4: Surplus Rate Variation by Department

```python
def test_surplus_rates_vary_by_department():
    """Dept I and IIb should have higher s/v than IIa and III."""
    tensor = hydrator.hydrate("26163", 2020)

    # Capital-intensive and luxury sectors extract more surplus
    assert tensor.dept_I.exploitation_rate > tensor.dept_IIa.exploitation_rate
    assert tensor.dept_IIb.exploitation_rate > tensor.dept_III.exploitation_rate
```

### Test 5: Data Quality Metric

```python
def test_granularity_metric():
    """Urban counties should have finer NAICS granularity."""
    wayne = hydrator.hydrate("26163", 2020)  # Urban
    rural = hydrator.hydrate("26001", 2020)  # Rural MI county

    # Wayne should have more 4-6 digit NAICS data available
    assert wayne.naics_granularity > rural.naics_granularity
```

---

## 7. BEASurplusRatios Loader (Prerequisite)

```python
class BEASurplusRatios:
    """Precomputed s/v and c/v ratios from BEA national accounts."""

    def __init__(self, session: Session, year: int):
        self._sv_by_bea: dict[str, float] = {}
        self._cv_by_bea: dict[str, float] = {}
        self._naics_to_bea: dict[str, str] = {}
        self._load(session, year)

    def _load(self, session: Session, year: int):
        # Load BEA industry accounts
        # Load NAICS-BEA concordance
        # Compute ratios
        pass

    def get_sv_ratio(self, naics_code: str) -> float:
        """Get s/v ratio for NAICS code via BEA concordance."""
        bea_code = self._naics_to_bea.get(naics_code[:4])  # 4-digit match
        if bea_code and bea_code in self._sv_by_bea:
            return self._sv_by_bea[bea_code]
        return 1.5  # Default fallback

    def get_cv_ratio(self, naics_code: str) -> float:
        """Get c/v ratio for NAICS code via BEA concordance."""
        bea_code = self._naics_to_bea.get(naics_code[:4])
        if bea_code and bea_code in self._cv_by_bea:
            return self._cv_by_bea[bea_code]
        return 2.0  # Default fallback
```

---

## 8. File Placement

```
babylon/
├── data/
│   ├── mappings/
│   │   └── naics_to_dept.yaml      # Department allocation config
│   └── reference/
│       └── department_mapper.py    # DepartmentMapper class
├── core/
│   ├── tensor.py                   # ValueTensor4x3, DepartmentRow
│   └── hydrator.py                 # MarxianHydrator
└── tests/
    └── test_hydrator.py            # Verification tests
```

---

## 9. Open Questions for Review

1. **c/v default fallback:** Should missing BEA concordances use department-specific defaults (e.g., Dept I → c/v=3.0, Dept III → c/v=0.5) rather than a single global default?

2. **Multi-year smoothing:** Should the tensor support α-smoothing across years, or is that a layer above the Hydrator?

3. **Establishment counts:** QCEW has establishment counts. Should we include a "firm density" metric on the tensor for network topology seeding?

---

**Ready for implementation.** The DepartmentMapper is complete. Next step is BEASurplusRatios loader, then MarxianHydrator, then verification tests against Wayne/Oakland.
