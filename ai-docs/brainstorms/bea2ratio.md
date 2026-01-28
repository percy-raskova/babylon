# Calibrating NAICS industries to Marxian reproduction departments

The **Bureau of Economic Analysis Input-Output Use Tables** provide the empirical foundation for mapping US industries to Marxian departments, while **BLS Consumer Expenditure Survey** income-stratified data enables the IIa/IIb (necessary vs. luxury consumption) split. Integrating these with **Fortunati and Federici's reproductive labor theory** yields a rigorous, data-grounded calibration framework. The key finding: most raw materials and heavy manufacturing flows to Dept I (**55-65% intermediate use**), consumer goods split roughly **56% necessary / 44% luxury** based on income quintile consumption patterns, and social reproduction industries (childcare, elder care, domestic work) constitute a distinct Dept III that produces labor power itself.

---

## BEA Use Tables reveal intermediate vs. final demand splits

The BEA Input-Output Accounts (accessible at bea.gov/itable/input-output) provide the primary empirical source for Dept I vs. Dept II classification. The **Use Tables** show commodities (rows) consumed by industries (columns) for intermediate use, with separate columns for Personal Consumption Expenditures (PCE), government consumption, and investment.

**Key structural insight**: Calculate **Intermediate Use %** = (Sum of all industry columns) ÷ Total Commodity Output. This directly measures "means of production" character—commodities purchased by capital as constant capital. The **PCE column** captures household consumption (Dept II destination).

Available granularity levels enable different calibration approaches:

| Level | Industries | Best Use Case |
|-------|------------|---------------|
| Summary | 71 industries | Broad sector calibration |
| Underlying | 138 industries | 3-digit NAICS mapping |
| Detail (2017 benchmark) | 402+ industries | Fine-grained calibration |

**BEA methodology note**: The 2017 benchmark tables (most recent detailed) derive from the Economic Census. Annual updates extrapolate benchmark relationships using industry output data. Healthcare and education present complications—some government-funded services flow through PCE via "third-party payer" treatment (Medicare/Medicaid payments appear in PCE).

**Illustrative data from BEA tables**: Computer and electronic products (NAICS 334) shows **61.9% intermediate use**, demonstrating strong Dept I character. Total manufacturing shows **63.8% intermediate use**, with the remainder split across PCE, investment, government, and net exports.

---

## Income quintile spending patterns distinguish necessary from luxury goods

The **BLS Consumer Expenditure Survey** (Table 1101, "Quintiles of income before taxes") provides the empirical basis for the IIa/IIb split. The theoretical criterion—goods required for worker reproduction (IIa) vs. surplus-funded bourgeois consumption (IIb)—operationalizes as: **if bottom 60% of households spend a higher budget share than top 40%, the good is necessary**.

The **"necessity index"** (lowest quintile budget share ÷ highest quintile budget share) cleanly separates categories:

**Strong Dept IIa indicators** (necessity index > 1.5):
- Rented dwellings: **5.96** (15.5% vs. 2.6% of budget)
- Food at home: **1.82** (11.1% vs. 6.1%)
- Utilities: **1.89** (8.7% vs. 4.6%)
- Healthcare: **1.64** (10.3% vs. 6.3%)
- Gasoline: **1.45** (4.8% vs. 3.3%)

**Strong Dept IIb indicators** (highest quintile spends dramatically more):
- Pensions/insurance: lowest quintile $636/year vs. highest quintile **$24,543** (38x difference)
- Entertainment fees/admissions: $139 vs. **$2,328** (16.7x)
- Food away from home: $1,466 vs. **$7,191** (4.9x)
- Education: $652 vs. **$3,678** (5.6x)

The aggregate split across all consumer expenditures: approximately **56% Dept IIa (necessary)** and **44% Dept IIb (luxury)**. This serves as the baseline for allocating retail and consumer services.

---

## Fortunati and Federici define Dept III as labor power production

The theoretical innovation of **Department III** draws on Leopoldina Fortunati's *The Arcane of Reproduction* (1995) and Silvia Federici's work on reproductive labor. Their key distinction: **reproductive labor produces labor power (the capacity to work), not commodities**.

Fortunati argues capitalism depends on a "hidden abode of reproduction" where living labor transforms wage goods (food, housing) into the renewed capacity to work. The housewife, in her framework, is "an *indirectly* waged worker"—a specifically capitalist category, not a feudal remnant. Her formula: between the purchase of commodities and the renewed sale of labor power, reproduction occurs: **C → M...R(eproduction)...C**.

Federici extends this historically, arguing in *Caliban and the Witch* (2004) that primitive accumulation required not only enclosures but **the subjugation of women to reproductive labor**. The "patriarchy of the wage" enabled two workers to be exploited with one wage.

**Criterial distinction for Dept III**:

| Productive Labor (Dept I/II) | Reproductive Labor (Dept III) |
|------------------------------|-------------------------------|
| Produces commodities | Produces labor power itself |
| Product separable from production | Product inseparable from living person |
| Creates exchange-value directly | Creates use-value of labor power |
| Measured in socially necessary labor time | Systematically undervalued |

**Critical theoretical resolution**: Commodified care work (paid daycare, nursing homes) remains reproductive *in function* even when organized for profit. The daycare worker produces labor power, not a commodity separable from the child. This justifies including paid care industries in Dept III.

---

## Recommended NAICS classifications for Department III

Based on the Fortunati/Federici framework, these industries should carry significant or full Dept III allocation:

**Core Dept III industries (100% allocation)**:
- **814** Private Households—domestic workers performing housework, Fortunati's paradigmatic reproductive labor
- **6244** Child Day Care Services—generational reproduction, creating future labor power
- **6241** Individual & Family Services—maintaining worker capacity through social support
- **6242** Community Food & Housing Services—emergency reproduction (feeding, housing workers)
- **6243** Vocational Rehabilitation Services—restoring damaged labor power to productive capacity
- **623** Nursing & Residential Care Facilities—elder care is explicitly reproductive in Federici; manages workers beyond productive life
- **6216** Home Health Care Services—directly maintains labor power in domestic settings

**Partial Dept III (recommended 30-50% allocation)**:
- **611** Educational Services—K-12 and community colleges produce the *general* capacity to work; professional training may lean Dept I
- **621** Ambulatory Healthcare—primary/preventive care maintains workers; elective procedures lean Dept IIb
- **722** Food Services—worker meals replace home cooking (Dept III function), but restaurants also serve luxury consumption (IIb)

The key ambiguity concerns **healthcare (621-622)**. Fortunati's framework suggests healthcare restoring workers to productive capacity is reproductive. Resolution: distinguish by function—occupational health, primary care, mental health services for workers = Dept III; cosmetic surgery, elective procedures = Dept IIb.

---

## Quantitative splits for priority industries

**Agriculture (NAICS 11)**: USDA data shows **34% of grains go to animal feed** (intermediate use), while farm products flowing to food processing constitute the majority of output. Direct-to-consumer sales represent only **33% of direct farm sales** (~$3B of $9B). Recommended split: **60-65% Dept I** (food processing intermediate), **30-35% Dept IIa** (food consumption), **~5% Dept IIb** (specialty/luxury foods).

**Manufacturing subsectors**:

| NAICS | Industry | Dept I | Dept IIa | Dept IIb |
|-------|----------|--------|----------|----------|
| 311 | Food Manufacturing | 5% | 85% | 10% |
| 325 | Chemical Manufacturing | 55-60% | 30-35% | 10% |
| 333 | Machinery | 95% | 5% | — |
| 334 | Computers/Electronics | 55-60% | 30% | 10% |
| 336 | Motor Vehicles | 20-25% | 65-70% | 10% |

**Chemical manufacturing** requires subsector disaggregation: Basic chemicals (3251) are **~95% Dept I**; pharmaceuticals (3254) split **70% IIa** (essential medicines), **15% IIb** (elective), **15% III** (healthcare system); soap/toiletries (3256) are **75% IIa**, **20% IIb** (luxury cosmetics).

**Motor vehicles** data shows light trucks (SUVs, pickups) comprise **74-80% of vehicle sales**. Heavy trucks (Class 4+, commercial fleet purchases) represent **~20-25% Dept I**; consumer vehicles are **~65-70% Dept IIa**, **~10% Dept IIb** (luxury).

**Retail trade (44-45)**: All final consumption; question is IIa/IIb allocation. Food retailers (445): **90% IIa**. Clothing (448): **60% IIa, 40% IIb**. General merchandise (455): **70% IIa, 30% IIb**. **Overall retail**: **70-75% Dept IIa, 25-30% Dept IIb**.

**Real estate (531)**: Commercial vs. residential data from industry sources shows commercial real estate at **~$27 trillion (45%)** → Dept I. Residential at **~$33 trillion (55%)**, with **~85% workforce housing (IIa)** and **~15% luxury (IIb)**. Recommended split: **35-40% Dept I, 50-55% Dept IIa, 10-15% Dept IIb**.

**Transportation (48-49)** freight/passenger splits:

| Subsector | Dept I (Freight) | Dept II (Passenger) |
|-----------|------------------|---------------------|
| 481 Air | 15% | 85% |
| 482 Rail | 95% | 5% |
| 484 Trucking | 95% | 5% |
| 485 Transit | 0% | 100% |
| 492 Couriers | 40% | 60% |

Rail data is definitive: freight rail revenue (~$71B) dwarfs Amtrak passenger revenue (~$3B). Amtrak owns only **3% of US rail track**.

---

## Healthcare allocation requires three-way split

CDC/CMS National Health Expenditure data enables a granular healthcare breakdown:

| Category | % of Total | Department |
|----------|------------|------------|
| Hospital Care | 31.4% | Mixed IIa/IIb |
| Physician Services | 20.3% | Mixed IIa/IIb |
| Prescription Drugs | 9.7% | ~85% IIa, ~15% IIb |
| Nursing Facilities | 4.5% | Dept III |
| Home Health Care | 3.0% | Dept III |

Cosmetic/elective procedures represent **<1% of total healthcare spending** (~$26B of ~$4.5 trillion). The childcare market stands at **$65-75 billion** (2024).

**Recommended healthcare (NAICS 62) allocation**: **75-80% Dept IIa** (essential care), **2-3% Dept IIb** (elective/cosmetic), **15-20% Dept III** (nursing, home health, childcare, elder care services).

---

## Consolidated calibration recommendations

**Summary table for YAML mapping adjustments**:

| NAICS | Industry | Dept I | Dept IIa | Dept IIb | Dept III |
|-------|----------|--------|----------|----------|----------|
| 11 | Agriculture | 62% | 33% | 5% | — |
| 21 | Mining | 95% | 5% | — | — |
| 311 | Food Manufacturing | 5% | 85% | 10% | — |
| 325 | Chemical Manufacturing | 57% | 33% | 10% | — |
| 333 | Machinery | 95% | 5% | — | — |
| 334 | Computer/Electronics | 58% | 30% | 12% | — |
| 336 | Motor Vehicles | 23% | 67% | 10% | — |
| 42 | Wholesale Trade | 85% | 15% | — | — |
| 44-45 | Retail Trade | — | 72% | 28% | — |
| 481 | Air Transportation | 15% | 75% | 10% | — |
| 482 | Rail Transportation | 95% | 5% | — | — |
| 484 | Truck Transportation | 95% | 5% | — | — |
| 485 | Transit | — | 90% | 10% | — |
| 531 | Real Estate | 38% | 52% | 10% | — |
| 611 | Educational Services | — | 30% | 20% | 50% |
| 621 | Ambulatory Healthcare | — | 70% | 10% | 20% |
| 622 | Hospitals | — | 75% | 5% | 20% |
| 623 | Nursing/Residential Care | — | — | — | 100% |
| 624 | Social Assistance | — | 10% | — | 90% |
| 6244 | Child Day Care | — | — | — | 100% |
| 722 | Food Services | — | 50% | 40% | 10% |
| 814 | Private Households | — | — | — | 100% |

**Key methodological notes**:

1. **Data limitations flagged**: No government source tracks retail purchases by consumer income class, residential housing by "workforce" vs. "luxury" categories, or consumer vs. commercial vehicle purchases precisely. The splits above rely on proxy indicators.

2. **BEA download path**: For precise calibration, download the **2022 Summary Use Table** and calculate intermediate use percentage = Sum(industry columns) ÷ Total commodity output for each row. The NAICS-BEA concordance file maps codes.

3. **Dept III theoretical justification**: Industries producing, maintaining, or restoring *labor power* (capacity to work) rather than commodities. The paid/unpaid distinction is secondary to the *what is produced* criterion.

4. **IIa/IIb operationalization**: Use expenditure *shares by income quintile* rather than absolute spending. Categories where bottom 60% spends higher budget proportion = IIa; categories where spending concentrates in top 40% = IIb.

---

## Conclusion: A theoretically grounded empirical framework

This calibration framework bridges classical Marxian reproduction schemas with contemporary US industrial classification. The BEA Use Tables provide authoritative intermediate/final demand splits for Dept I/II allocation. The CEX income quintile data operationalizes the necessary/luxury distinction for IIa/IIb classification with a clear "necessity index" metric. The Fortunati-Federici framework theoretically grounds Dept III as industries producing labor power itself—childcare, elder care, domestic work, and the reproductive components of healthcare and education.

**Three adjustments are recommended** relative to typical mappings: (1) Healthcare should carry **15-20% Dept III** allocation rather than pure Dept II, reflecting its labor-power-maintenance function; (2) Educational services warrant **50% Dept III** for K-12/community college levels that produce general work capacity; (3) Food services should split **50% IIa / 40% IIb / 10% III**, recognizing worker meals as reproductive and fine dining as luxury.

The framework enables the Babylon simulation to model commodity flows consistent with both empirical input-output data and Marxian value-theoretic categories. For industries where data is ambiguous, the splits provided reflect informed estimates that should be refined as additional BEA detailed industry data becomes available.
