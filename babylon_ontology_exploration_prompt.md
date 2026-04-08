# Babylon Ontology Exploration — Claude Code Prompt

## Context

Babylon is a political simulation engine modeling imperial collapse through MLM-TW political economy. We've been working on a formal ontology that maps every object and relation to its theoretical origin, computational representation, and data source. This session is about exploring and solidifying that ontology, particularly the hypergraph layer and how industry membership works.

Read these files first:

- The ontology document (attached or in project knowledge)
- `spec_033_unified_class_system.md`
- `036-state-verb-system.md`
- `038-django-web-application-v3.md`
- `player-verb-resolution-speckit-prompt.md`
- The NAICS-to-Department YAML mapping (if present in codebase)

## What We've Decided

### Hypergraph Has Two Categories of Membership

**Political/Social communities** (gate consciousness, credibility, solidarity potential):

- These are the existing spec 029 community hyperedges: SETTLER, NEW_AFRIKAN, FIRST_NATIONS, CHICANO, INCARCERATED, DISABLED, QUEER, UNDOCUMENTED, etc.
- MVP needs only: SETTLER, NEW_AFRIKAN
- These gate EDUCATE credibility, solidarity potential computation, and consciousness propagation

**Industry sectors** (gate economic metabolism, business coordination, profit rate equalization):

- NEW category. Each 2-digit NAICS code is a hyperedge in XGI.
- Business org nodes are members of their industry hyperedge.
- Worker population blocks can also be members (they work IN the industry).
- Each industry hyperedge carries `department_weights` from the NAICS-to-Department YAML.
- Profit rate equalization (Volume III) operates within and across industry hyperedges.
- The `HyperedgeCategory` enum from spec 029 needs a fourth value: `ECONOMIC_SECTOR`.

### NAICS as Universal Join Key

NAICS code unifies the entire data pipeline:

- SQLite reference: QCEW wages/employment by NAICS × FIPS, BEA value-added by industry
- XGI hypergraph: industry hyperedge ID IS the 2-digit NAICS code
- NetworkX: Business org nodes carry NAICS as a first-class attribute
- Department mapping: YAML maps NAICS → Dept I/IIa/IIb/III weights
- ACS: earnings by race × NAICS feeds rent differential (Φ_diff) computation

### Database Indexing

- NAICS must be indexed in both SQLite reference and Postgres runtime
- In Postgres, NAICS on Business org nodes should be a proper column, NOT buried in JSONB
- The critical query pattern: `SELECT SUM(v), SUM(c), SUM(s) FROM node_state WHERE naics_code = ? GROUP BY naics_code` — Layer 0 aggregation per industry per tick

### Business Agent Granularity

- One Business org per NAICS × county for MVP
- Tri-county Detroit × ~15 significant NAICS = ~30-45 Business agents
- Each aggregates all establishments in that sector in that county
- QCEW `establishment_count` is an attribute on the Business node
- Business NPC behavior: mostly passive (Layer 0 runs M-C-M' automatically), activates only when circuit is disrupted (strike, regulation, profit rate differential triggers capital flight)

### The Contradiction Engine (Theoretical Foundation)

The four-node pattern `{Core, Periphery} × {Bourgeoisie, Proletariat}` is NOT a primitive. It is a derived output of the Contradiction Engine:

```python
class Contradiction:
    type: ContradictionType          # IMPERIAL, COLONIAL, CLASS, GENDER, CARCERAL, etc.
    aspect_a: NodeID                 # dominant aspect
    aspect_b: NodeID                 # subordinate aspect
    principal_aspect: Literal["a", "b"]  # which side currently dominates
    identity: float                  # mutual presupposition strength
    tension: float                   # accumulated struggle (float per tick)
    is_antagonistic: bool            # resolvable within existing relations?
    form_of_struggle: EdgeMode       # EXTRACTIVE, TRANSACTIONAL, SOLIDARISTIC, ANTAGONISTIC, CO-OPTIVE

class ContradictionFrame:
    """The 2×2 at a given scale and moment — COMPUTED, not stored."""
    principal: Contradiction
    secondary: Contradiction
    # quadrants = cross-product of the two contradictions' aspects
```

The four-node pattern emerges from `ContradictionFrame.quadrants` when principal=IMPERIAL/COLONIAL and secondary=CLASS. At different scales or moments, different contradictions fill those slots. Same code path, different content.

Semi-periphery is NOT a third structural position. It's `tension` accumulating toward a `principal_aspect` flip — a float approaching a threshold. The 2×2 is always preserved.

## What to Explore

### 1. Entity Inventory for MVP

Enumerate every concrete entity instance needed for tri-county Detroit at tick 0:

**Territories**: H3 hex count per county (Wayne, Oakland, Macomb). ~1,500 total at res 7.

**Population blocks**: How many per county? One per ClassPosition per county = 5 × 3 = 15? Or finer (per hex)? What's the right resolution for MVP?

**Organizations**: List every org that should exist at initialization:

- 1 player PoliticalFaction (Wayne County, revolutionary, NEW_AFRIKAN community embedding)
- N StateApparatus nodes (FBI? DPD? Schools? Courts? How many and which ones?)
- N Business orgs (one per significant NAICS × county — enumerate them from QCEW data if accessible)
- N CivilSocietyOrgs (which churches, unions, nonprofits matter for Detroit?)

**Community hyperedges**:

- Political: SETTLER, NEW_AFRIKAN (MVP minimum)
- Industry: one per 2-digit NAICS with significant employment in tri-county

### 2. Schema Exploration

Look at the existing codebase and database schema. For each entity type in the ontology, trace:

- Does a Pydantic model exist?
- Does a database table exist (SQLite or Postgres)?
- Does a NetworkX node type or XGI hyperedge type exist?
- What's missing?

Specific things to check:

- Is `HyperedgeCategory` an enum? Does it need `ECONOMIC_SECTOR` added?
- Is there a `Business` org subtype or just the generic `Organization`?
- How is NAICS currently stored/indexed in SQLite?
- What NAICS codes have significant employment (>1000 workers) in Wayne (26163), Oakland (26125), Macomb (26099)?

### 3. Industry Hyperedge Prototype

If the codebase has XGI integration:

- Create industry hyperedges from QCEW data
- Assign Business org nodes as members
- Compute `I @ I.T` (which businesses share an industry)
- Compute cross-industry Department aggregation using YAML weights
- Verify that the NAICS join key connects QCEW → hyperedge → Business node → Department

If XGI integration doesn't exist yet, draft the data model:

```python
class IndustryHyperedge:
    naics_2digit: str                    # "62", "31-33", "52", etc.
    naics_label: str                     # "Health Care and Social Assistance"
    department_weights: dict[str, float] # {"dept_I": 0.0, "dept_IIa": 0.7, ...}
    member_business_ids: set[NodeID]
    member_worker_block_ids: set[NodeID]
    county_fips: set[str]               # which counties have this industry
    # Derived:
    total_employment: int
    total_wages: float                   # v for this industry
    profit_rate: float                   # derived from BEA
    occ: float                          # c/v for this industry
```

### 4. Layer 0 Minimum Viable Metabolism

The ontology says Layer 0 runs "value production, wage circulation, profit equalization" automatically per tick. For MVP, what's the minimum computation?

Explore whether this is sufficient:

1. Each Business node has v, c, s from QCEW/BEA initialization
1. Per tick: s is produced (automatic), wages (v) flow to worker population blocks in the territory
1. Volume II: LODES commute data determines WHERE wages are spent (value produced in Oakland, wages spent in Wayne)
1. Volume III: profit rate comparison across industry hyperedges — if r(NAICS_62, Wayne) < r(NAICS_62, Oakland), capital pressure to migrate. But actual migration requires a Business MOVE decision, which is NPC behavior.

Can Layer 0 be static for MVP (just replay QCEW data per tick with small perturbations) while the political layer is dynamic? Or does it need to actually compute?

### 5. NAICS Index Verification

Check the SQLite reference database:

- What tables contain NAICS codes?
- Are they indexed?
- What's the granularity (2-digit, 4-digit, 6-digit)?
- Run: `SELECT naics_code, COUNT(*), SUM(annual_avg_emplvl) FROM qcew_annual WHERE area_fips IN ('26163','26125','26099') GROUP BY naics_code ORDER BY SUM(annual_avg_emplvl) DESC LIMIT 20`
- This tells you which industries actually matter for Detroit

### 6. Contradiction Data Model Gap Analysis

The Contradiction primitive from the ontology integrates with existing specs. Check what exists:

- `ContradictionAxis` from spec 029 — does it exist in code?
- `EdgeMode` enum — does it exist? Does it have all 5 modes?
- Community hyperedge contradiction pairs — are they implemented?
- What would need to change to support `Contradiction` as a first-class edge attribute?

Don't implement the full ContradictionFrame / derive_frame() machinery. That's post-MVP. Just identify the data model gaps.

## Output

Produce a report covering:

1. **Entity census**: every concrete entity instance at MVP tick 0, with data source
1. **Schema gaps**: what Pydantic models, DB tables, and graph types exist vs. what's needed
1. **NAICS profile**: top industries by employment for each county, with Department mapping
1. **Industry hyperedge draft**: data model and initialization logic
1. **Layer 0 recommendation**: minimum viable metabolism for MVP
1. **Contradiction gaps**: what exists vs. what's needed (inventory only, don't implement)

Be concrete. Use actual NAICS codes. Query actual data if the SQLite database is accessible. Enumerate actual org instances, not abstract types.

## Constraints

- Don't implement anything yet. This is exploration and inventory.
- Don't expand scope beyond tri-county Detroit MVP.
- If you find conflicts between the ontology and existing specs, flag them — don't resolve them silently.
- NAICS as join key is decided. Don't re-litigate.
- Industry hyperedges as XGI membership is decided. Don't propose alternatives.
- The Contradiction Engine as theoretical foundation is decided. The four-node pattern derives from it. Don't revert to hardcoded 2×2.
