<!--
================================================================================
SYNC IMPACT REPORT
================================================================================
Version Change: 1.7.0 → 1.8.0
Bump Rationale: 3 new theoretical commitments + hyperedge categories + anti-pattern — MINOR

Modified Principles:
  - II.7 expanded with three hyperedge categories (contradiction pairs,
    institutional exclusion, lifecycle phases)

Added Sections:
  - I.16 Organization vs Institution (voluntary coordination vs crystallized relations)
  - I.17 OODA Loop as Organizational Metabolism (action capacity per turn)
  - I.18 Material-Ideological Distinction on Hyperedges (class-in-itself vs class-for-itself)
  - II.7 Category 1: Contradiction Pairs (only marginalized side as hyperedge)
  - II.7 Category 2: Institutional Exclusion (denial of access, not bilateral contradiction)
  - II.7 Category 3: Lifecycle Phases / D-P-D' Circuit (temporal, not identity)
  - VIII.10 Hegemonic Community as Hyperedge (anti-pattern)

Removed Sections: None

Cross-References Added:
  - I.16 references V (player builds orgs, state operates institutions)
  - I.17 references V (OODA constrains verb availability per tick)
  - I.18 references I.7 (gap between material/ideological = political struggle terrain)
  - VIII.10 references II.7 Category 1

Follow-up TODOs:
  - CODE: Restructure CommunityType enum per three-category taxonomy:
    Category 1 hegemonic: rename WHITE→SETTLER, add PATRIARCHAL
    Category 1 marginalized: keep NEW_AFRIKAN, FIRST_NATIONS, CHICANO, WOMEN, TRANS
    Category 2 exclusion: keep DISABLED, QUEER, UNDOCUMENTED; add INCARCERATED
    Category 2 remove: ABLED, HETEROSEXUAL, CISGENDER (institutional defaults, not communities)
    Category 3 lifecycle: add YOUTH, ADULT, ELDER
  - CODE: Update tests to reflect new taxonomy
  - SPEC: Update Feature 022 spec FR-003 with corrected community types

Templates Requiring Updates:
  ✅ plan-template.md: No hardcoded principle numbers
  ✅ spec-template.md: No constitution references
  ✅ tasks-template.md: No constitution references
  ✅ checklist-template.md: No constitution references
  ✅ agent-file-template.md: No constitution references

Previous Version History:
  1.7.0 (2026-02-25): Added V. State AI Verbs (6 verbs, asymmetric)
  1.6.1 (2026-02-25): Structural reorganization — annex architecture, core condensed ~78%
  1.6.0 (2026-02-25): Added II.7 Edges vs Hyperedges, VIII.9 Community as Pairwise Edge
  1.5.0 (2026-02-24): Added I.12-I.15 (Catastrophe Surface, Principal Contradiction,
                      Contradiction Internals, Edge Mode Transition Topology)
  1.4.0 (2026-02-24): Added V. Player Action Vocabulary (9 verbs, dual grouping)
  1.3.2 (2026-02-05): Added dispossession data sources to III.4 table
  1.3.1 (2026-02-05): Added PWT and Census Trade to III.4 approved sources
  1.3.0 (2026-01-31): Added VIII. Visual Design Principles (new article)
  1.2.0 (2026-01-30): Added I.8-I.11 (Tragedy, Metabolic Rift, Terminal Crisis, Pedagogy),
                      II.5-II.6 (AI Observes, State/Engine separation)
  1.1.0 (2026-01-30): Added I.7 Quantitative Accumulation → Qualitative Transformation
  1.0.0 (2026-01-30): Initial ratification with 6 theoretical commitments,
                      4 architecture principles, 5 methodological constraints
================================================================================
-->

# Babylon Constitution

Governing document for the political simulation engine testing MLM-TW political economy against empirical data. Full rationale, examples, and historical context for each article in `constitution/`.

## I. Theoretical Commitments

> Full article: `constitution/article-i-theory.md`

**1. Settler-Colonial Frame** — Principal contradiction: imperialism vs oppressed nations, NOT capital vs labor.

**2. Imperial Rent (Φ)** — Φ = unequal exchange + externalized reproduction + domestic shadow labor. W_c > V_c → imperial rent. Explains core working class pacification.

**3. TRPF with Counter-Tendencies** — Model tendency AND counter-tendencies separately. Stable r MUST emerge from interaction, not be assumed.

**4. George Jackson Bifurcation** — Crisis → fascism (no solidarity edges) or revolution (solidarity across colonial divide). Warsaw Ghetto corollary: P(S|A) → 0 triggers revolt regardless of organization. Hegemony prevents this realization.

**5. Department III** — Reproduction tensor MUST include Dept III. g₃₃ → 0 (invisible). Rising visibility compresses profits independent of TRPF.

**6. Solidarity as Edge Mode** — Four modes: EXTRACTIVE, TRANSACTIONAL, SOLIDARISTIC, ANTAGONISTIC. Organizing transforms types, not weights. Qualitative, not scalar.

**7. Quantitative → Qualitative** — Quantities accumulate (resilience, pressure, crisis, consciousness). Qualities transform discretely (edge modes, class position, system phase). Thresholds explicit. No continuous quality gradients. Enums for qualities, floats for quantities.

**8. Tragedy of Inevitability** — Collapse is default. Player shapes character, not outcome. Existence costs calories (`base_subsistence > 0`). Earth remembers wounds. Death is real. Banned: infinite biocapacity, equilibrium stability, player "victory."

**9. Metabolic Rift** — ΔB = R - (E × η), η > 1.0. Overshoot O = C/B. Extraction permanently reduces max biocapacity. Independent collapse vector alongside TRPF.

**10. Terminal Crisis Arc** — Plantation → Prison → Camp → Death Camp. Each transition when previous stage unprofitable. Carceral turn responds to Φ exhaustion.

**11. Emergent Pedagogy** — All strategies playable. Consequences modeled, not punished. Theory follows experience. No hidden win conditions. Decolonial victory is emergent, not enforced.

**12. Catastrophe Surface** — Control parameters continuous (floats per tick). State variables discrete (enums at fold crossings). Catastrophe surface explicit per phase transition. I.7 is the what; I.12 is the geometry.

**13. Principal Contradiction** — One contradiction leads per tick. Selection: intensity × structural position. Shifts are discrete events. Primary dynamics full effect; secondary dampened.

**14. Contradiction Internals** — Aspect (dominant/subordinate — reversal is phase transition). Character (antagonistic/non-antagonistic, independent of edge mode). Trajectory (1st + 2nd derivatives per tick). Edges MUST be directed.

**15. Edge Mode Transitions** — State machine governs permissible transitions. Prohibited: EXTRACTIVE → SOLIDARISTIC (requires TRANSACTIONAL intermediate). Conditions reference contradiction internals. Topology versioned as constitutional amendment.

**16. Organization vs Institution** — Organization = voluntary coordination, can be destroyed. Institution = crystallized social relations, survives member turnover. Organizations become institutions through formalization. The player builds organizations; the state operates institutions. Destroying an organization kills it. Destroying an institution requires replacing the social relations it crystallizes.

**17. OODA Loop as Organizational Metabolism** — Every organization/institution has an OODA profile (Observe-Orient-Decide-Act) determining action capacity per turn. Trade-offs: speed vs coherence, autonomy vs coordination, democracy vs reaction time. Decentralized orgs observe fast but orient slowly. Hierarchical institutions decide fast but observe poorly. The profile constrains which verbs are available and how many per tick.

**18. Material-Ideological Distinction on Hyperedges** — Every community hyperedge has two dimensions: material basis (objective structural position, exists regardless of member consciousness) and ideological dimension (whether members conceive of themselves as having collective interests opposed to hegemonic order). The GAP between material position and ideological consciousness is the terrain of political struggle. This is class-in-itself vs class-for-itself, generalized across all contradiction axes.

## II. Architecture Principles

> Full article: `constitution/article-ii-architecture.md`

**1. Four-Node Recursive** — {Core, Periphery} × {Bourgeoisie, Proletariat}. Fractal at any resolution.

**2. Primitives vs Derived** — Store: concrete labor time, physical substrate, reproduction requirements, topology. Compute: SNLT, value, c/v/s, Φ, r, s/v, OCC. NEVER store derived quantities.

**3. NetworkX as Discretized Manifold** — Graph is the manifold. Tensors are field values. Connectivity determines information/value flow.

**4. Quantities vs Coefficients** — Quantities flux per tick. Coefficients α-smooth. Crisis = discontinuous coefficient reset, not gradual drift.

**5. AI Observes, Never Controls** — State calculated then narrated. AI read-only. Reproducibility paramount. AI failure non-fatal.

**6. State is Data, Engine is Transformation** — WorldState: frozen Pydantic, `model_copy()` for changes. Engine: pure `step()`. Hydration: SQLite → WorldState → NetworkX → Systems → back. No DB I/O during tick.

**7. Edges vs Hyperedges (NetworkX + XGI)** — Dyadic flows between two entities → NetworkX edge. N-ary membership → XGI hyperedge. Two layers MUST remain separate. Hyperedge overlap = solidarity potential; edge = actuality. Edges per tick; hyperedges α-smooth. Three hyperedge categories:

- **Category 1 — Contradiction Pairs**: Both hegemonic and marginalized sides are real hyperedges with members, institutions, and political projects. SETTLER ↔ NEW_AFRIKAN/FIRST_NATIONS/CHICANO (land, imperial rent, carceral labor). PATRIARCHAL ↔ WOMEN/TRANS (unwaged reproductive labor, Dept III). Hegemonic hyperedges recruit, organize, and defend extraction positions.
- **Category 2 — Institutional Exclusion**: Only the marginalized side exists as a real hyperedge. No paired oppressor community — oppression flows through institutional defaults. DISABLED (built environment assumes able-bodiedness), QUEER (institutional heteronormativity), UNDOCUMENTED (legal exclusion), INCARCERATED (carceral system, civil death).
- **Category 3 — Lifecycle Phases (D-P-D' Circuit)**: Temporal positions in the intergenerational lifecycle. NOT identity communities — structural phases with distinct material conditions. YOUTH (D: pre-productive, dependent), ADULT (P: sells labor-power), ELDER (D': post-productive, legitimation bargain). Dependency ratio = (Pop_D + Pop_D') / Pop_P.

## III. Methodological Constraints

> Full article: `constitution/article-iii-methodology.md`

**1. No Magic Constants** — Every number traces to primitives or data sources.

**2. Falsifiability Required** — Every formula defines: prediction, null hypothesis, distinguishing observable, falsifying data.

**3. Physics Cosplay Prohibition** — Tensor notation earns its keep through actual invariance. Reject formalism without transformation laws.

**4. Data Source Traceability** — Approved: QCEW, Census/ACS, BEA, FRED, HIFLD, BTS, FCC, ATUS, CDC WONDER, Piketty/WID, PWT, Census Trade, Eviction Lab, US Courts, ATTOM/CoreLogic, Fed SCF. New sources require explicit addition.

**5. Empirical vs Strategic Separation** — Material conditions from data (nodes, constraints, extractive edges). Strategic intervention NOT from data (solidaristic edges, organizing, consciousness-raising).

## IV. Test Case: Metro Detroit (2010-2025)

> Full article: `constitution/article-iv-detroit.md`

Wayne County vs Oakland County. Crisis → Devaluation → Recolonization → Displacement. Model MUST reproduce observed class transitions using only QCEW/Census data + theoretical mechanisms. Failure = theory or implementation wrong.

## V. Action Vocabulary

> Full article: `constitution/article-v-verbs.md`

### Player (9 verbs)

**Educate, Aid, Attack, Mobilize, Campaign, Move, Investigate, Reproduce, Negotiate**.

Player-facing (3x3): Build org | Project power | Manage resources. Engine-facing: Organization (node) | Population (org↔class edges) | Other actors (org↔org edges). Every verb maps to a graph operation. Atomic. All always available. Deterministic.

### State AI (6 verbs)

**Administer** (Fund, Staff, Audit, Legislate) — reproduce state apparatus. **Develop** (Rezone, Invest, Eminent Domain, Tax Incentives) — reshape territory layer; asymmetric verb player lacks; gentrification as verb. **Research** — advance tech; products potentially seizable by player. **Co-opt** (Bribe, Propagandize, Incorporate, Divide) — absorb opposition or destroy relationships; Divide targets edges not nodes. **Repress** (Surveil, Infiltrate, Raid, Prosecute, Liquidate) — escalation ladder; each step costs more legitimacy. **Withdraw** (Strategic / Tactical / Scorched Earth) — concede, reposition, or deny territory; player must read which mode.

No separate state Negotiate verb — negotiation is a mode of Withdraw (terms of concession) or Co-opt (terms of absorption). Asymmetry is structural: state has fewer verbs but Develop operates on substrate player cannot directly modify.

## VI. Scope Control

> Full article: `constitution/article-vi-scope.md`

1. **Material Base First** — Economic extraction → class formation → solidarity → THEN repression.
2. **Zoom Where Data Exists** — Resolution matches data availability.
3. **Flag Scope Creep** — Must trace to Detroit prediction or improve falsifiability. Otherwise DEFER.

## VII. Visual Design Principles

> Full article: `constitution/article-vii-visual.md`

1. **UI Observes, Never Controls** — Passive observer. Emits intents, never mutates state.
2. **Color as Data** — BLOOD_VOID, BLACK, CRIMSON (power), GOLD (action/solidarity), SILVER (mass), ASH (muted). Luminosity = magnitude. All via palette tokens.
3. **Data-Ink Maximization** — Every pixel encodes data or enables navigation. Small multiples over animation.
4. **Graph Is Primary** — Node position/size/density ARE data. Verbs over nouns. Topology visible.
5. **Signifier Legibility** — No hidden verbs. All interactive elements have visual affordance.
6. **Semantic Invariance** — Color meaning invariant across all views.
7. **Smallest Effective Difference** — Minimum visual distinction necessary.
8. **Feedback/Feedforward** — State changes confirmed visually. Preview consequences.
9. **Typography** — Monospace dominant. Max two typeface families.
10. **Prohibitions** — No decorative glow, hardcoded colors, chartjunk, hidden state, gratuitous animation, corner legends, context-dependent color, mood over meaning.

## VIII. Anti-Patterns

> Full article: `constitution/article-viii-antipatterns.md`

1. **Solidarity as Scalar** — Edge type transforms, not `+= x`.
2. **Union Density as Revolutionary** — US unions = labor aristocracy institutions.
3. **Determinism from Material Conditions** — Conditions constrain, not determine.
4. **Ungrounded Tensor Notation** — See III.3.
5. **Claims Without Falsifiability** — See III.2.
6. **Constants Without Data Sources** — See III.1, III.4.
7. **Superstructure Before Base** — See VI.1.
8. **Decorative Visualization** — See VII.10.
9. **Community as Pairwise Edge** — Community = XGI hyperedge, not combinatorial pairwise edges. See II.7.
10. **Oppressor Hyperedge for Institutional Exclusion** — Category 2 communities (DISABLED, QUEER, UNDOCUMENTED, INCARCERATED) have NO paired oppressor hyperedge. ABLED is absence of disability, not a political community. HETEROSEXUAL is unmarked default, not solidarity community. Contrast with Category 1 where BOTH sides exist (SETTLER has institutions, recruits, defends extraction). See II.7.

## IX. Governance

> Full article: `constitution/article-ix-governance.md`

**Amendment**: Propose → demonstrate consistency → update artifacts → increment version.
**Versioning**: MAJOR (removal/redefinition), MINOR (new principle), PATCH (clarification).
**Compliance triggers**: New system, formula change, data source addition, scope expansion, UI implementation.

______________________________________________________________________

**Version**: 1.8.0 | **Ratified**: 2026-01-30 | **Last Amended**: 2026-02-25
