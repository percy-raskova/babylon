# Institution System: Spec-Kit Prompts (v1)

**Purpose**: Prompts for Claude Code + spec-kit to generate specifications for the Institution system
**Usage**: Feed each prompt to `/speckit.specify` sequentially; each phase builds on the prior
**Prerequisite**: Organization base model (030) is the required foundation. Community hyperedge layer (022) is ALREADY IMPLEMENTED via XGI.
**Context**: Existing codebase has Organization ABC, four subtypes (StateApparatus, Business, PoliticalFaction, CivilSocietyOrg), OODA profiles, community hyperedge infrastructure with CommunityConsciousness, and `institution.schema.json` (to be deprecated and replaced).
**Key Insight**: Institutions are NOT Organizations with persistence. They are a distinct third layer between substrate and agents — agent-generating substrate that crystallizes past class struggles into self-reproducing social relations.

---

## Theoretical Foundation

### The Marxist Lineage on Institutions

Four major theoretical frameworks converge on what Babylon's Institution model must capture. They are not all saying the same thing, and the tensions between them are productive.

**Marx & Engels (classical)**: Two views in tension. Engels: the state as instrument of class rule — whoever holds economic power wields state power. Marx: the state as parasite — an alienated social institution that develops its own reproductive logic independent of any class. The synthesis in *The German Ideology*: "since the state is the form in which the individuals of a ruling class assert their common interests... it follows that all institutions are set up with the help of the state and are given a political form." Institutions are always political even when they present as neutral.

**Althusser (RSA/ISA distinction)**: The repressive state apparatus (government, courts, police, armed forces) functions predominantly by violence, secondarily by ideology. Ideological state apparatuses (churches, schools, family, media, cultural institutions) function predominantly by ideology, secondarily by violence. EVERY apparatus uses BOTH — the question is which dominates. Critical for Babylon: "ISAs may be not only the stake, but also the site of class struggle." ISAs are *contestable terrain*, not monolithic instruments. The exploited classes "find means and occasions to express themselves there, either by the utilization of their contradictions, or by conquering combat positions in them in struggle."

**Gramsci (hegemony and war of position)**: Civil society institutions (trade unions, churches, schools, media, cultural organizations) are the terrain where hegemony is manufactured and contested. The "war of position" — the gradual winning of tactical strongholds within civil society — is the revolutionary strategy for advanced capitalist states where the ruling class rules through consent, not just coercion. "The conquest of hegemony precedes the conquest of power." The war of position IS the game loop of Babylon. Building counter-hegemonic institutions, capturing existing ones, contesting ideological terrain through civil society.

**Poulantzas (the state as social relation)**: The state is "the material condensation of a relationship of forces between classes." Not a thing, not a subject — a terrain. "Political domination is inscribed in the state's institutional materiality." Institutions crystallize past class struggles and provide the field for ongoing ones. The state is "a complex, contradictory ensemble of institutions" — not monolithic, but traversed by contradictions between different class fractions reflected in struggles between different branches and apparatuses. This gives us the modeling framework: institutions have internal balance-of-forces, strategic selectivity, and relative autonomy.

### The Bonapartism Thesis: Intra-Ruling-Class Institutional Warfare

Marx's *Eighteenth Brumaire* demonstrates that the state apparatus can gain independence from the ruling class during periods when ruling-class factions are deadlocked. But the thesis extends further: different institutions *represent* different ruling-class fractions, and inter-institutional conflict is the form that intra-ruling-class struggle takes.

**Concrete examples that the model must capture:**

CIA vs FBI budget fights: Not just turf wars — different fractions of capital with different strategic orientations. CIA serves finance capital and extractive industries (protecting imperial rent flows from periphery). FBI serves domestic capital (protecting settler-colonial order at home). Budget conflict = proxy fight over whether scarce ruling-class attention goes to imperial extraction maintenance or domestic contradiction management.

FBI vs local sheriff jurisdiction: Federal institutions represent cosmopolitan, financialized bourgeoisie needing national-scale coordination. Local sheriff departments represent settler petit-bourgeoisie whose power depends on local autonomy. The jurisdictional conflict is the class contradiction between these fractions expressing itself through institutional channels. The sheriff's department is often more explicitly embedded in the SETTLER community hyperedge; the FBI operates at a level that sometimes requires disciplining local settler excesses to protect systemic legitimacy.

The revanchist/liberal split within state institutions: "What is the risk from *not* arresting this communist?" (revanchist faction — capital that has abandoned the legitimation bargain, wants naked repression) versus "What is the risk to the rule of law if we arrest this communist?" (liberal faction — capital that still depends on institutional legitimacy and consent-manufacturing). Both are bourgeois. Both want to maintain class rule. They disagree on *method*, and that disagreement plays out *within* the same institutions. The DOJ under different attorneys general oscillates between these poles. The same FBI field office contains agents with both orientations.

**Three ruling-class fractions within institutions:**

1. **Liberal-technocratic**: Maintains legitimation bargain. Rules through consent + soft power. Dominant during stable accumulation. Corresponds to ASSIMILATIONIST_LIBERAL at the community level. Prefers ASSIMILATE operations ("we're all Americans under the law"). Escalates repression reluctantly.

2. **Revanchist-fascist**: Abandons legitimation bargain. Rules through naked repression. Gains ground during crisis as liberal methods fail. Corresponds to ASSIMILATIONIST_FASCIST. Skips straight to network surgery. Doesn't care about legitimacy costs.

3. **Institutionalist-Bonapartist**: The institution's own self-preservation logic. Defends institutional prerogatives against ALL external forces including the class it ostensibly serves. The bureaucratic tendency Marx identified as the "parasite state." Emerges when crisis delegitimizes both liberal and revanchist orientations and the apparatus starts operating in its own interest.

Crisis intensifies intra-institutional contradictions. Under normal conditions, the liberal-technocratic fraction maintains hegemony. Under crisis, the revanchist fraction gains ground. At extreme crisis, the Bonapartist tendency emerges — the police functioning as an independent political force rather than a tool of any civilian authority. This is Poulantzas's "authoritarian statism."

### Three-Layer Architecture: Substrate → Institutions → Agents

```
SUBSTRATE LAYER (no agency, no self-reproduction)
├── SocialClass blocks (demographic reservoirs)
├── Territory (spatial grid, H3 hexagons)
└── Community hyperedges (IMPLEMENTED — three categories + consciousness)

INSTITUTION LAYER (no OODA agency, but self-reproducing)
├── Institutions persist through member turnover
├── Institutions generate and constrain Organizations
├── Institutions have internal balance-of-forces between class fractions
├── Institutions are sites of class struggle (contestable terrain)
├── Institutions have structural selectivity (make some actions easier, others harder)
└── Institutions carry social functions that must be replaced, not just destroyed

AGENT LAYER (has agency via OODA)
└── Organization (the ONLY agent type)
    ├── StateApparatus (housed in RSA-type Institutions)
    ├── Business (housed in economic Institutions)
    ├── PoliticalFaction (may capture Institutions or build new ones)
    └── CivilSocietyOrg (housed in ISA-type Institutions)
```

**Key architectural principle**: Institutions don't run OODA loops. They don't make decisions. They produce Organizations that make decisions, and they constrain what kinds of Organizations can form within them. The DOJ doesn't decide to surveil a revolutionary org — the FBI (an Organization housed within it) does. But the DOJ ensures that *some* FBI-like Organization always exists. Kill the current FBI director, the DOJ spawns a replacement. That's what "survives member turnover" means mechanistically.

**Institutions as "structural selectivity"** (Poulantzas/Jessop): Institutions don't have agency in the OODA sense, but they make certain actions easier and others harder, certain Organizations more viable and others impossible. A university makes it easy to form study groups but hard to form militias. A police department makes it easy to form surveillance units but hard to form community mediation programs. The institutional materiality — procedures, budgets, legal authorities, physical infrastructure — selects for certain kinds of organizational activity.

### Organization → Institution Transition

Formalization transforms organizations into institutions. This is a one-way threshold crossing (Constitution I.7 — quantitative accumulation → qualitative transformation).

**Preconditions for transition:**
- Bylaws / formal procedures (routinization of charisma)
- Property / fixed assets (material persistence beyond personnel)
- Paid staff / formalized roles (role survives individual)
- Succession protocols (reproductive capacity)
- Legal standing (recognized by existing institutional order)

**What changes at transition:**
- Disruption response: destroying all current members DEGRADES but does not DESTROY
- New members recruited into existing roles (institutional reproduction)
- Class inscription becomes more resistant to change than org class_character
- Institutional inertia: harder to change direction, harder to destroy
- Gains structural selectivity: shapes what Organizations can form within it

**Historical examples:**
- Black Panther Party (Organization, destroyed by COINTELPRO) vs NYPD (Institution, survives any personnel change)
- Mutual aid network (Organization) → 501(c)(3) nonprofit (Institution)
- Guerrilla cell (Organization) → Vanguard party with dues, discipline, succession (Institution)
- Study circle (Organization) → University department (Institution)

### Institutional Destruction vs Organizational Destruction

Constitution I.16: "Destroying an institution requires replacing the social relations it crystallizes, not just removing personnel."

Mechanically: Institution has a `social_function` (employment, education, worship, policing, healthcare, care, adjudication). The Institution persists until an alternative institution with the same social_function reaches sufficient legitimacy to absorb its constituency. You can't destroy the patriarchal family by arresting husbands — you destroy it by building alternative care structures that make the patriarchal family unnecessary (Federici). You can't abolish the police by defunding — you abolish policing by building community safety institutions that make police unnecessary.

**Institutional replacement** is the win condition beyond the bifurcation. You don't just need the solidarity topology to be right at crisis moment — you need alternative institutions ready to absorb the social functions that collapse when the old order breaks.

---

## Phase 1: Institution Base Model

### Spec ID: `036-institution-base-model`

### Prompt:

```
Create a specification for the Institution Base Model.

CONTEXT:
- Institutions are a THIRD LAYER between substrate and agents
- Organizations (030) are the ONLY agents. Institutions don't run OODA loops.
- Institutions GENERATE and CONSTRAIN Organizations housed within them
- Institutions have INTERNAL BALANCE OF FORCES between ruling-class fractions
- Community hyperedge layer is ALREADY IMPLEMENTED (XGI)
- Existing codebase has institution.schema.json — to be DEPRECATED and replaced
- Requires: 030-organization-base-model

THEORETICAL FOUNDATION:

**What Institutions ARE (Poulantzas)**:
"The material condensation of a relationship of forces between classes."
Not a thing, not a subject — a terrain crystallizing past class struggles.
Institutions have "institutional materiality" — procedures, budgets, legal
authorities, physical infrastructure — that persists independent of personnel.

**What Institutions DO**:
1. Persist through member turnover (roles survive individuals)
2. Generate Organizations (FBI is generated by DOJ Institution)
3. Constrain Organizations (institutional materiality shapes what orgs can do)
4. Carry social functions (employment, education, policing, care, adjudication)
5. Reproduce social relations (the relations persist, not just the people)
6. Serve as sites of class struggle (Althusser: ISAs are contestable terrain)
7. Have internal factional balance that shifts with broader class struggle

**Institution Model**:
```python
class Institution(BaseModel):
    """Third-layer entity: agent-generating substrate.

    Crystallized social relations that reproduce themselves.
    Persists through member turnover. Does NOT run OODA loops.
    Generates and constrains Organizations housed within it.

    Poulantzas: "the material condensation of a relationship
    of forces between classes."
    """
    id: str
    name: str

    # === ALTHUSSERIAN CLASSIFICATION ===
    apparatus_type: ApparatusType
    # RSA: Government, courts, police, prisons, military
    # ISA_EDUCATIONAL: Schools, universities
    # ISA_RELIGIOUS: Churches, religious orders
    # ISA_FAMILY: The family as institution
    # ISA_LEGAL: The legal system as ideological apparatus
    # ISA_POLITICAL: Electoral system, parties-as-institutions
    # ISA_COMMUNICATIONS: Media organizations
    # ISA_CULTURAL: Arts, sports, cultural bodies
    # ECONOMIC: Firms, banks, markets, industry associations
    #
    # Every institution functions by BOTH violence and ideology.
    # apparatus_type determines which DOMINATES.

    # === SOCIAL FUNCTION ===
    social_function: SocialFunction
    # EMPLOYMENT, EDUCATION, WORSHIP, POLICING, HEALTHCARE,
    # CARE, ADJUDICATION, COMMUNICATION, LEGISLATION,
    # INCARCERATION, MILITARY_DEFENSE, FINANCIAL_INTERMEDIATION
    #
    # An institution persists until an alternative institution
    # with the same social_function absorbs its constituency.
    # Destruction requires REPLACEMENT, not just removal.

    # === CLASS INSCRIPTION ===
    # More resistant to change than Organization.class_character.
    # Changes only through sustained struggle that rewrites
    # internal rules, procedures, and resource flows.
    class_inscription: ClassInscription  # BOURGEOIS | PROLETARIAN | CONTESTED

    # === INTERNAL BALANCE OF FORCES (Poulantzas/Bonapartism) ===
    internal_balance: InternalBalanceOfForces
    # Which ruling-class fraction currently dominates?
    # How contested is the internal terrain?
    # This modulates the OODA orientation of housed Organizations.

    # === STRUCTURAL SELECTIVITY ===
    # What kinds of Organizations can form within this Institution?
    # What actions are easier/harder?
    permitted_org_types: set[OrgType]
    action_modifiers: dict[ActionType, float]
    # e.g., university: {EDUCATE: 0.7, RECRUIT: 0.8, REPRESS: 2.0}
    # Lower = easier. Repress from within a university is expensive.

    # === MATERIAL INFRASTRUCTURE ===
    budget: float
    fixed_assets: list[str]  # Territory IDs
    legal_authorities: set[LegalAuthority]
    personnel_capacity: int  # Max roles, not current personnel

    # === PERSISTENCE & REPRODUCTION ===
    formalization_level: float  # [0,1] — how crystallized
    succession_protocol: bool   # Can it replace lost personnel?
    institutional_inertia: float  # [0,1] — resistance to change
    legitimacy: float  # [0,1] — public acceptance of its social function

    # === HOUSED ORGANIZATIONS ===
    housed_org_ids: list[str]
    # Organizations operating within this Institution.
    # Multiple orgs can be housed in one Institution.
    # Orgs within the same Institution may have conflicting
    # factional alignments (e.g., FBI Civil Rights Division
    # vs FBI Counterintelligence Division).

    # === SPATIAL ===
    territory_ids: list[str]  # Where infrastructure exists
    jurisdiction: set[str] | None  # For RSA-type: legal jurisdiction

    # === D-P-D' PHASE ===
    lifecycle_function: LifecyclePhase | None
    # D: Schools, childcare — controls ideological transmission
    # P: Workplaces, unions — where surplus extraction occurs
    # D': Elder care, pensions — the legitimation bargain
    # None: Not phase-specific
```

**InternalBalanceOfForces (the Bonapartism mechanic)**:
```python
class RulingClassFraction(Enum):
    LIBERAL_TECHNOCRATIC = "liberal_technocratic"
    # Maintains legitimation bargain. Rules through consent.
    # Prefers ASSIMILATE ("we're all Americans").
    # Escalates repression reluctantly.
    # Dominant during stable accumulation.

    REVANCHIST_FASCIST = "revanchist_fascist"
    # Abandons legitimation bargain. Naked repression.
    # Skips to network surgery. Doesn't care about legitimacy.
    # Gains ground during crisis.

    INSTITUTIONALIST_BONAPARTIST = "institutionalist_bonapartist"
    # Institution's own self-preservation logic.
    # Defends institutional prerogatives against ALL external forces.
    # Emerges when crisis delegitimizes both liberal and revanchist.
    # The bureaucratic tendency Marx called "parasite state."

class InternalBalanceOfForces(BaseModel):
    """Which fraction currently dominates within this institution?

    Poulantzas: institutions are traversed by contradictions
    between class fractions, reflected in inter-branch struggle.
    """
    faction_weights: dict[RulingClassFraction, float]
    # Weights sum to 1.0. e.g.:
    # FBI normal: {LIBERAL: 0.5, REVANCHIST: 0.3, BONAPARTIST: 0.2}
    # FBI under crisis: {LIBERAL: 0.2, REVANCHIST: 0.5, BONAPARTIST: 0.3}
    # FBI deep crisis: {LIBERAL: 0.1, REVANCHIST: 0.3, BONAPARTIST: 0.6}

    @computed_field
    def hegemonic_fraction(self) -> RulingClassFraction:
        """Which fraction holds internal hegemony?"""
        return max(self.faction_weights, key=self.faction_weights.get)

    internal_contestation: float  # [0,1]
    # High = active factional warfare within the institution.
    # Low = settled hegemony of one fraction.
    # Rises with crisis intensity.
```

**ApparatusType Enum (Althusserian)**:
```python
class ApparatusType(Enum):
    # Repressive State Apparatus — functions predominantly by violence
    RSA_EXECUTIVE = "rsa_executive"      # Government, administration
    RSA_MILITARY = "rsa_military"        # Armed forces
    RSA_POLICE = "rsa_police"            # Police departments
    RSA_JUDICIAL = "rsa_judicial"        # Courts
    RSA_CARCERAL = "rsa_carceral"        # Prisons

    # Ideological State Apparatus — functions predominantly by ideology
    ISA_EDUCATIONAL = "isa_educational"  # Schools, universities
    ISA_RELIGIOUS = "isa_religious"      # Churches, religious orders
    ISA_FAMILY = "isa_family"            # The family as institution
    ISA_LEGAL = "isa_legal"              # Legal system as ideology
    ISA_POLITICAL = "isa_political"      # Electoral system, party system
    ISA_COMMUNICATIONS = "isa_communications"  # Media
    ISA_CULTURAL = "isa_cultural"        # Arts, sports, cultural bodies

    # Economic institutions (neither purely RSA nor ISA)
    ECONOMIC_PRODUCTIVE = "economic_productive"  # Firms, factories
    ECONOMIC_FINANCIAL = "economic_financial"     # Banks, exchanges
    ECONOMIC_EXTRACTIVE = "economic_extractive"   # Mining, resource firms
```

**Institution-Organization Relationship**:
```python
class InstitutionOrgRelation(BaseModel):
    """How an Institution relates to its housed Organizations."""
    institution_id: str
    organization_id: str

    # What does the Institution provide?
    resource_provision: float    # Budget share allocated
    legal_cover: bool           # Legal authority delegated
    legitimacy_transfer: float  # How much institutional legitimacy flows to org

    # What does the Institution constrain?
    action_oversight: float     # [0,1] How much the institution monitors the org
    factional_alignment: RulingClassFraction | None
    # Which internal faction does this org align with?
    # FBI Civil Rights Division: LIBERAL_TECHNOCRATIC
    # FBI Counterintelligence Division: REVANCHIST_FASCIST
    # Both housed in same DOJ Institution.
```

**Institutional Reproduction (the self-perpetuation mechanic)**:
```python
class ReproductionMechanism(BaseModel):
    """How the institution replaces lost personnel and maintains itself.

    This is what makes it an Institution rather than an Organization.
    Arresting all current members DEGRADES but does not DESTROY.
    """
    recruitment_pipeline: bool      # Formal hiring/admissions process
    training_program: bool          # Socializes new members into roles
    succession_protocol: bool       # Leadership replacement mechanism
    budget_independence: float      # [0,1] Self-funding capacity
    legal_self_perpetuation: bool   # Charter/law mandates existence

    @computed_field
    def reproduction_capacity(self) -> float:
        """How effectively can this institution replace lost members?"""
        factors = [self.recruitment_pipeline, self.training_program,
                   self.succession_protocol, self.legal_self_perpetuation]
        return (sum(factors) / 4) * 0.7 + self.budget_independence * 0.3
```

REQUIRED OUTPUTS:

**Models (Pydantic, frozen=True)**:
- Institution base model with all fields above
- ApparatusType enum (RSA/ISA/Economic — Althusserian)
- SocialFunction enum
- ClassInscription (distinct from Organization.ClassCharacter)
- InternalBalanceOfForces with RulingClassFraction
- InstitutionOrgRelation
- ReproductionMechanism
- StructuralSelectivity model (action modifiers)

**Graph Integration**:
- Institution.housed_orgs(G) -> list[Organization]
- Institution.territory_footprint(G) -> list[Territory]
- Institution.community_embeddedness(H) -> dict[CommunityType, float]
  (which community hyperedges is this institution embedded in?)
- Institution.hegemonic_fraction_effect() -> OODAModifier
  (how does internal balance affect housed orgs' OODA profiles?)
- Institution.structural_selectivity(action_type) -> float
  (cost modifier for actions taken by housed orgs)

**Deprecation**:
- institution.schema.json → Institution Pydantic model
- Organization.is_institution field (from 030) → separate Institution entity
- Organization.institutional_persistence → Institution.formalization_level

VALIDATION CRITERIA:
- DOJ instantiable as RSA_JUDICIAL Institution housing FBI StateApparatus
- Detroit Public Schools as ISA_EDUCATIONAL with lifecycle_function=D
- Ford Motor Company as ECONOMIC_PRODUCTIVE housing Business org
- Catholic Church as ISA_RELIGIOUS with consciousness_tendency inference
- FBI internal_balance shifts when crisis_intensity changes
- Destroying all FBI agents degrades but doesn't destroy DOJ
- DOJ spawns replacement Organization when FBI is destroyed
- Multiple conflicting Organizations housed in same Institution
- University structural_selectivity makes EDUCATE cheap, REPRESS expensive

CONSTRAINTS:
- Institutions do NOT run OODA loops
- Frozen Pydantic; mutations create new instances
- No magic constants — faction_weights from empirical calibration
- Integrates with existing Organization ABC, GraphProtocol, community hyperedges
- Class inscription changes on coefficient timescale (α-smoothed), not quantity timescale

DEPENDENCIES:
- Requires: 030-organization-base-model, community hyperedge layer (IMPLEMENTED)
- Deprecates: institution.schema.json, Organization.is_institution

WHAT THIS DOES NOT INCLUDE:
- Institutional capture mechanics (Phase 2)
- Organization → Institution transition (Phase 3)
- Intra-institutional factional dynamics (Phase 4)
- Institutional replacement/destruction (Phase 5)
- Integration with bifurcation analysis (Phase 6)
```

---

## Phase 2: Institutional Capture Mechanics

### Spec ID: `037-institutional-capture`

### Prompt:

```
Create a specification for Institutional Capture — how Organizations contest
for control within Institutions, and how Institutions drift toward whoever
feeds them.

CONTEXT:
- Institutions are contestable terrain (Althusser: ISAs are sites of class struggle)
- Organizations housed within Institutions fight over internal balance of forces
- External Organizations can attempt entry/capture (Gramsci: war of position)
- Institutions drift toward material funding sources (gravitational capture)
- Requires: 036-institution-base-model, 030-organization-base-model, 031-ooda-loop-system

THEORETICAL FOUNDATION:

**Althusser's Contestability Thesis**:
The exploited classes can express themselves within ISAs "either by the
utilization of their contradictions, or by conquering combat positions
in them in struggle." ISAs are not monolithic instruments — they are
terrains where class struggle plays out.

**Gramsci's War of Position**:
"The gradual winning of tactical strongholds" within civil society.
A revolutionary project must "first build consent across civil society
before taking formal power." The war of position involves "building
institutions, spreading alternative ideas, and gradually winning over
key segments of society."

Institutional capture IS the war of position made concrete.

**Gravitational Capture (from religious topology conversation)**:
Institutions drift toward whoever feeds them. The capture dynamics:

```python
# Institutional drift toward material funding source
# α-smoothed, coefficient-level (slow)
d(class_inscription)/dt = η * (material_flow_vector - class_inscription)
```

Where material_flow_vector is determined by: who funds the institution,
who staffs it, who its constituency serves, who its legal framework
protects. Institutions follow the money on long timescales.

**Three Capture Strategies**:

1. **Entryism** (Organizations enter and contest from within):
   - Join the institution through legitimate channels
   - Build factional power within institutional roles
   - Gradually shift internal balance of forces
   - Example: revolutionary activists taking school board seats
   - Example: progressive prosecutors winning DA elections
   - Requires: PRESENCE within Institution's territory,
     members with relevant credentials/standing
   - Cost: time-intensive, requires maintaining cover
   - Risk: co-optation (the institution changes YOU instead)

2. **Material Capture** (redirect funding/resource flows):
   - Change who funds the institution
   - Change who the institution's constituency is
   - The gravitational drift does the rest
   - Example: community takeover of a nonprofit board
     by redirecting donors and changing mission
   - Example: gentrification changing a church's congregation
     composition, which changes its class character
   - Requires: control over funding sources or constituency
   - Cost: requires resources to redirect
   - Risk: losing the original base during transition

3. **Crisis Exploitation** (use institutional contradictions):
   - When internal_contestation is high, factions seek allies
   - External Organizations can ally with internal factions
   - Crisis creates openings that don't exist in stable periods
   - Example: liberal DOJ faction leaking information to
     journalists during a revanchist administration
   - Example: progressive teachers allying with parent
     organizations against school privatization
   - Requires: high internal_contestation + compatible faction
   - Cost: opportunistic, timing-dependent
   - Risk: unpredictable outcomes

**Co-optation Mechanics** (the reverse capture):
Institutions capture Organizations too. An Organization entering an
Institution risks being absorbed into its logic. The institution's
structural selectivity shapes what the org can do, and over time
the org's behavior converges with institutional norms.

```python
def co_optation_pressure(org, institution) -> float:
    """How much does the institution pull the org toward its logic?"""
    exposure = org.ticks_housed_in(institution) / 52  # years
    selectivity = institution.structural_selectivity  # constrains actions
    resource_dependency = org.budget_from(institution) / org.total_budget

    # The more you depend on the institution, the more it shapes you
    return exposure * resource_dependency * institution.institutional_inertia
```

If co_optation_pressure exceeds org.cadre_level (ideological discipline),
the org's class_character drifts toward the institution's class_inscription.
This is how revolutionary organizations get domesticated by operating within
bourgeois institutions — the structural selectivity shapes behavior until
the org is effectively liberal.

**Consciousness Effects of Capture**:
When a revolutionary Organization captures (or partially shifts) an ISA,
the consciousness effects are significant:
- A school under revolutionary influence teaches different content
- A media institution under progressive control changes the narrative
- A church under liberation theology raises collective_identity

But the reverse is also true:
- A revolutionary org operating within a liberal institution absorbs
  liberal framing and lowers collective_identity in its community

REQUIRED OUTPUTS:

**Models**:
- CaptureStrategy enum (ENTRYISM, MATERIAL_CAPTURE, CRISIS_EXPLOITATION)
- CaptureAttempt model (org, institution, strategy, progress)
- CoOptationState (tracking org drift within institution)
- InstitutionalDrift (α-smoothed class_inscription change)

**Actions (extend ActionType enum from 031)**:
- INFILTRATE_INSTITUTION: Place members in institutional roles
- CONTEST_INTERNALLY: Factional struggle within institution
- REDIRECT_RESOURCES: Change funding/constituency flows
- EXPLOIT_CONTRADICTION: Ally with internal faction during crisis
- BUILD_ALTERNATIVE: Create competing institution with same social_function

**System**:
- CaptureSystem integrated with OODA turn resolution
- Co-optation pressure computed per tick
- Gravitational drift computed per tick (coefficient-level, slow)
- Capture progress tracked across ticks
- Consciousness side-effects of institutional control changes

VALIDATION CRITERIA:
- Entryism into school board: slow, requires credentials, shifts EDUCATE content
- Material capture of nonprofit: redirect donors, mission drifts
- Crisis exploitation: high contestation enables factional alliance
- Co-optation: revolutionary org inside liberal institution drifts toward liberal
- Cadre discipline (cadre_level) resists co-optation
- Gravitational drift: institution follows funding on long timescale
- Capture of school (ISA_EDUCATIONAL, lifecycle=D) changes YOUTH consciousness
- Detroit test: progressive org attempting to shift DPS (Detroit Public Schools)

CONSTRAINTS:
- Capture is SLOW (institutional inertia resists change)
- Co-optation is the default outcome without active resistance
- No magic constants — co-optation rate from empirical calibration
- Must integrate with EXISTING OODA system and consciousness mechanics

DEPENDENCIES:
- Requires: 036, 030, 031
- Integrates with: CommunityConsciousness, ActionType enum

WHAT THIS DOES NOT INCLUDE:
- Organization → Institution transition (Phase 3)
- Factional dynamics within RSA institutions specifically (Phase 4)
- Institutional destruction/replacement (Phase 5)
```

---

## Phase 3: Organization → Institution Transition

### Spec ID: `038-org-institution-transition`

### Prompt:

```
Create a specification for Organization → Institution Transition — the
formalization threshold crossing.

CONTEXT:
- Constitution I.7: quantitative accumulation → qualitative transformation
- Constitution I.16: formalization is a one-way threshold crossing
- Organizations accumulate institutional attributes until they cross
  a phase transition into self-reproducing Institutions
- Requires: 036, 030

THEORETICAL FOUNDATION:

**Formalization as Phase Transition**:
An Organization accumulates institutional attributes:
- Bylaws (routinization of decision-making)
- Property (material persistence beyond personnel)
- Paid staff (role-based, not personality-based labor)
- Succession protocols (reproductive capacity)
- Legal standing (recognized by existing order)
- Budget independence (self-funding)
- Training programs (socialization of new members)

Each attribute is a float [0,1] that accumulates through specific
player/NPC actions. When the composite formalization_score crosses
a threshold, the Organization undergoes a phase transition into
an Institution.

**The Transition Is Not Free**:
Formalization has costs:
- Democratic responsiveness decreases (institutional inertia rises)
- Structural selectivity constrains future action
- Co-optation vulnerability increases (legal standing = legibility to state)
- Class character becomes class inscription (harder to change)
- Radical potential may diminish (Roberto Michels' iron law of oligarchy)

**But It Provides**:
- Persistence (survives leadership loss)
- Resource accumulation capacity
- Legitimacy
- Structural selectivity (shapes the field in your favor)
- Reproductive capacity (training pipeline)

**The Player's Dilemma**:
Formalize too early → co-optation, loss of revolutionary character
Formalize too late → vulnerability to targeted disruption (COINTELPRO)
Never formalize → can never hold territory long-term

This dilemma IS the central strategic tension of revolutionary practice.
The Bolsheviks formalized into a vanguard party institution. The Panthers
were destroyed before they could. The Democratic Party formalized into
an institution that lost all revolutionary content. Each represents a
different resolution of the same dilemma.

**Transition Actions** (player verbs):
- FORMALIZE: Invest cadre labor hours into institutional attributes
  (write bylaws, acquire property, establish training)
- DE-FORMALIZE: Deliberately reduce institutional attributes
  (rarely done, but sometimes necessary to escape co-optation)

**Transition is one-way with hysteresis**:
- Threshold to formalize: formalization_score > 0.7
- Threshold to de-formalize: requires deliberate action + crisis
- Hysteresis: the institution resists de-formalization even when
  the organization within it wants to change

REQUIRED OUTPUTS:

**Models**:
- FormalizationState (tracking all institutional attribute floats)
- TransitionEvent (the discrete phase change)
- InstitutionBirthRecord (what it was, what it became)

**Actions**:
- FORMALIZE verb (invest cadre labor into institutional attributes)
- DE_FORMALIZE verb (rare, deliberate, costly)

**System**:
- FormalizationTracker (monitors accumulation per tick)
- TransitionDetector (fires when threshold crossed)
- InstitutionFactory (creates Institution from Organization at transition)
- PostTransitionSetup (housed_org relationship, initial balance_of_forces)

VALIDATION CRITERIA:
- Mutual aid network formalizes into nonprofit at threshold
- Revolutionary cell formalizes into vanguard party
- Formalization increases institutional_inertia
- Formalization increases co-optation vulnerability
- De-formalization requires deliberate action
- Post-transition: old Organization becomes first housed_org of new Institution
- Detroit test: player org formalizing decision with tradeoffs visible

CONSTRAINTS:
- Threshold crossing is discrete (I.7)
- One-way with hysteresis (I.16)
- No magic constants — threshold empirically calibrated
- Formalization rate proportional to cadre_labor invested

DEPENDENCIES:
- Requires: 036, 030
```

---

## Phase 4: Intra-Institutional Factional Dynamics (Bonapartism)

### Spec ID: `039-bonapartism-factional-dynamics`

### Prompt:

```
Create a specification for Intra-Institutional Factional Dynamics —
the Bonapartism mechanic where ruling-class fractions fight each other
through institutional positions.

CONTEXT:
- Poulantzas: the state is "traversed by contradictions between different
  class fractions, reflected in struggles between different branches
  and apparatuses of the state"
- Crisis intensifies intra-institutional contradictions
- The player can EXPLOIT these contradictions (Althusser)
- State OODA behavior depends on which fraction is hegemonic (Phase 5 NPC AI)
- Requires: 036, 037, 032-attention-thread-system

THEORETICAL FOUNDATION:

**Inter-Institutional Conflict** (CIA vs FBI):
Different RSA institutions represent different class fractions.
Competition over budget, jurisdiction, and strategic priority
is a proxy for intra-ruling-class factional warfare.

```python
class InterInstitutionalConflict(BaseModel):
    """Conflict between state institutions representing different fractions."""
    institution_a_id: str
    institution_b_id: str
    conflict_type: ConflictType
    # JURISDICTIONAL: Who has authority over this territory/domain?
    # BUDGETARY: Who gets the scarce resources?
    # STRATEGIC: Which approach to a shared problem?
    # INFORMATIONAL: Who controls the intelligence flow?

    intensity: float  # [0,1]

    # What fraction does each institution's hegemonic faction represent?
    # When both are LIBERAL_TECHNOCRATIC → low conflict (bureaucratic routine)
    # When one is LIBERAL and other is REVANCHIST → high conflict
    # When BONAPARTIST emerges → conflict with EVERYONE
```

**Intra-Institutional Factional Shift**:
The internal_balance_of_forces shifts based on:

1. Crisis intensity (rising crisis → revanchist gains ground)
2. Legitimacy erosion (failing legitimation bargain → liberal loses ground)
3. External pressure (revolutionary threat → both liberal and revanchist
   may yield to Bonapartist self-preservation)
4. Personnel changes (new appointments shift factional weight)
5. Housed Organization actions (factional orgs contest internally)

```python
def update_internal_balance(
    institution: Institution,
    crisis_intensity: float,
    legitimacy: float,
    external_threat: float
) -> InternalBalanceOfForces:
    """Shift factional weights based on material conditions.

    This is α-smoothed (coefficient-level change, slow).
    """
    # Rising crisis empowers revanchist faction
    revanchist_pressure = crisis_intensity * (1 - legitimacy)

    # Failing legitimacy weakens liberal faction
    liberal_erosion = max(0, 0.5 - legitimacy) * 2

    # High external threat empowers Bonapartist self-preservation
    bonapartist_pressure = external_threat * crisis_intensity

    # Smooth update
    new_weights = alpha_smooth(
        institution.internal_balance.faction_weights,
        compute_target_weights(revanchist_pressure, liberal_erosion, bonapartist_pressure),
        alpha=0.05  # Slow, coefficient-level
    )

    return InternalBalanceOfForces(
        faction_weights=normalize(new_weights),
        internal_contestation=compute_contestation(new_weights)
    )
```

**Effect on Housed Organizations' OODA**:
The hegemonic fraction MODULATES the OODA profile of housed Organizations:

- LIBERAL hegemony → StateApparatus OBSERVE with civil liberties constraints,
  DECIDE through legal review, ACT with proportionality doctrine.
  Prefers ASSIMILATE over REPRESS. Slow escalation.

- REVANCHIST hegemony → StateApparatus OBSERVE without constraints,
  DECIDE through threat assessment only, ACT with maximum force.
  Prefers REPRESS over ASSIMILATE. Fast escalation.

- BONAPARTIST hegemony → StateApparatus OBSERVE focused on institutional
  threats (including from own government), DECIDE based on self-preservation,
  ACT to defend institutional prerogatives. May ignore political direction
  from either liberal or revanchist civilian leadership.

**The Bonapartist Threshold**:
When BONAPARTIST faction_weight > 0.4 AND no other fraction > 0.35,
the institution enters Bonapartist mode:
- Ignores civilian oversight
- Pursues institutional self-interest
- May conflict with other state institutions
- Historical precedent: police departments operating as independent
  political forces, military juntas, deep state phenomena

This is the "parasite state" Marx identified — the bureaucratic apparatus
treating the state as its own private property.

**Player Exploitation of Contradictions**:
When internal_contestation is high (>0.6), the player can:
- EXPLOIT_CONTRADICTION: ally with the faction closest to player interests
- LEAK_INFORMATION: use internal factional contacts as intel sources
- PLAY_FACTIONS: provoke one faction to overreact, discrediting the other
- FORCE_ESCALATION: deliberately trigger revanchist overreaction to
  radicalize fence-sitters (extremely dangerous — Jackson bifurcation risk)

REQUIRED OUTPUTS:

**Models**:
- InterInstitutionalConflict
- FractionalShiftEvent (when hegemonic_fraction changes)
- BonapartistThreshold
- OODAModifier (how faction hegemony modulates housed org behavior)

**System**:
- FactionalDynamicsSystem (updates balance per tick, α-smoothed)
- InterInstitutionalConflictSystem (computes conflicts between RSA institutions)
- BonapartistDetector (fires when threshold crossed)
- OODAModulation (applies faction effects to housed org OODA profiles)

**Actions (extend ActionType)**:
- EXPLOIT_CONTRADICTION
- PLAY_FACTIONS
- FORCE_ESCALATION (high risk / high reward)

VALIDATION CRITERIA:
- Rising crisis shifts FBI balance toward REVANCHIST
- Falling legitimacy weakens LIBERAL faction
- High external threat activates BONAPARTIST
- FBI vs local PD jurisdictional conflict when fractions differ
- LIBERAL-hegemonic FBI uses ASSIMILATE; REVANCHIST uses REPRESS
- BONAPARTIST FBI ignores AG directives
- Player EXPLOIT_CONTRADICTION requires high internal_contestation
- FORCE_ESCALATION can produce radicalization OR fascist consolidation
- Detroit test: DPD factional dynamics during crisis, player exploitation

CONSTRAINTS:
- Factional shifts are α-smoothed (slow, coefficient-level)
- BONAPARTIST mode is emergent, not scripted
- Player exploitation actions have genuine risk (can backfire)
- No magic constants — thresholds from empirical/historical calibration
- Integrates with existing attention thread system (032)

DEPENDENCIES:
- Requires: 036, 037, 030, 031, 032

REFERENCES:
- Marx, Eighteenth Brumaire
- Poulantzas, State Power Socialism
- state-repression-research.md
```

---

## Phase 5: Institutional Destruction and Replacement

### Spec ID: `040-institutional-destruction-replacement`

### Prompt:

```
Create a specification for Institutional Destruction and Replacement —
how Institutions die and what replaces them.

CONTEXT:
- Constitution I.16: "Destroying an institution requires replacing the
  social relations it crystallizes."
- Institutions persist until alternatives absorb their social function
- Revolutionary strategy requires building REPLACEMENT institutions
- Requires: 036, 037, 038, 033-bifurcation-topology

THEORETICAL FOUNDATION:

**The Replacement Principle**:
An Institution's social_function is a NEED that the population has.
Policing fulfills a safety need (however distorted). Schools fulfill
an education need. Hospitals fulfill a healthcare need. Churches fulfill
a meaning-making and community need.

Attacking an Institution without providing an alternative leaves the
need unmet, which generates backlash. Defunding the police without
building community safety produces INCREASED support for police
among people who feel unsafe. This is not false consciousness — it's
rational behavior in the absence of alternatives.

**Destruction Conditions**:
An Institution is destroyed when:
1. legitimacy < destruction_threshold (varies by apparatus_type)
   AND
2. alternative_coverage > replacement_threshold
   (an alternative institution serves the same social_function
    to the same constituency with sufficient legitimacy)

OR:
3. Violent overthrow (revolution/coup) — but this only destroys the
   CURRENT institutional form. The social_function persists and must
   be served by whatever replaces it. The Commune still needed courts;
   it just replaced bourgeois courts with people's tribunals.

**Alternative Institution Building**:
This is the core revolutionary strategy beyond the bifurcation.
BUILD_ALTERNATIVE creates a competing institution:

```python
class AlternativeInstitution(BaseModel):
    """A proto-institution serving the same social function
    as an existing institution but with different class character."""

    social_function: SocialFunction  # Same as target institution
    class_inscription: ClassInscription  # Different from target

    coverage: float  # [0,1] What fraction of constituency served
    legitimacy: float  # [0,1] How accepted by constituency

    # When coverage * legitimacy > threshold,
    # this alternative can REPLACE the target institution.

    # Examples:
    # Mutual aid → alternative to capitalist welfare
    # People's tribunal → alternative to bourgeois courts
    # Community patrol → alternative to police
    # Liberation school → alternative to public school
    # Free clinic → alternative to for-profit healthcare
```

**Institutional Replacement as Win Condition**:
The bifurcation analysis (033) determines WHETHER crisis resolves
as revolution or fascism. But even revolutionary resolution requires
institutional replacement to consolidate. A revolution that topples
bourgeois institutions without replacement institutions ready
produces chaos → backlash → counter-revolution.

The player's LONG GAME:
1. Build solidarity topology (Phases 030-035)
2. Build alternative institutions (this phase)
3. Contest existing institutions (Phase 037)
4. When crisis hits and bifurcation resolves revolutionary (033),
   alternative institutions absorb social functions from collapsing
   bourgeois institutions

**Institutional Death Mechanics**:
When an Institution IS destroyed:
- All housed Organizations lose institutional support
- Legal authorities lapse
- Fixed assets become contested
- Personnel capacity drops to 0
- Social function becomes UNMET in affected territories
- UNMET social function generates CRISIS_OF_REPRODUCTION
  in affected SocialClass blocks

**The D-P-D' Dimension**:
Institutional replacement is especially critical for lifecycle infrastructure:
- Replace bourgeois schools (D-phase) → control ideological transmission
- Replace capitalist workplaces (P-phase) → end surplus extraction
- Replace inadequate elder care (D'-phase) → honor the legitimation bargain
  under new terms

REQUIRED OUTPUTS:

**Models**:
- AlternativeInstitution
- ReplacementProgress (coverage, legitimacy trajectory)
- InstitutionalDeathEvent
- SocialFunctionGap (unmet function → crisis_of_reproduction)
- ConsolidationState (post-revolution institutional landscape)

**Actions**:
- BUILD_ALTERNATIVE: Create proto-institution serving social function
- EXPAND_COVERAGE: Grow alternative institution's reach
- ABSORB_FUNCTION: Alternative replaces target (threshold crossing)
- CONSOLIDATE: Post-revolution institutional establishment

**System**:
- AlternativeInstitutionTracker
- ReplacementDetector (fires when alt can replace target)
- SocialFunctionGapSystem (computes unmet needs → crisis)
- ConsolidationSystem (post-bifurcation institutional transition)

VALIDATION CRITERIA:
- Mutual aid network as alternative to welfare: builds coverage, legitimacy
- Destroying police without alternative → safety crisis → backlash
- Community patrol + alternative → police can be replaced
- Post-revolution: alternative institutions absorb social functions
- UNMET social function generates crisis_of_reproduction
- D-phase replacement (alternative school) shifts YOUTH consciousness
- Detroit test: player builds alternative institutions in Wayne County,
  tests whether they can absorb functions during crisis

CONSTRAINTS:
- Destruction without replacement generates backlash (not moralized — emergent)
- Alternative institutions start fragile and grow
- Replacement threshold varies by social_function
  (easier to replace a church than a police department)
- No magic constants
- Integrates with bifurcation analysis (033)

DEPENDENCIES:
- Requires: 036, 037, 038, 033
```

---

## Phase 6: Institution-Bifurcation Integration

### Spec ID: `041-institution-bifurcation-integration`

### Prompt:

```
Create a specification for Institution-Bifurcation Integration —
how the institutional landscape determines bifurcation outcomes.

CONTEXT:
- The bifurcation (033) predicts revolution vs fascism based on
  solidarity topology + consciousness
- But institutional landscape determines whether revolutionary
  resolution can CONSOLIDATE
- Intra-institutional factional dynamics affect state response to crisis
- Alternative institution readiness determines post-crisis viability
- This is the capstone integration phase
- Requires: 036-040, 033

THEORETICAL FOUNDATION:

**The Extended Bifurcation**:
The original George Jackson bifurcation asks:
  "Does crisis produce revolution or fascism?"
  Answer: depends on solidarity topology + consciousness.

The EXTENDED bifurcation adds:
  "If revolution, can it consolidate?"
  Answer: depends on alternative institutional readiness.

  "If fascism, through which institutional pathway?"
  Answer: depends on which ruling-class fraction captures state institutions.

**Fascist Consolidation Pathways** (via institutional capture):
1. REVANCHIST CAPTURE: Existing institutions shift to revanchist hegemony.
   Police, courts, military all shift to naked repression. Formal democratic
   institutions hollowed out but maintained as shells. (Weimar → Third Reich)

2. BONAPARTIST AUTONOMY: State apparatus detaches from ALL class fractions
   and operates in self-interest. Military junta, police state, deep state.
   Neither liberal nor fascist in ideology — purely self-preserving.
   (Egypt under Sisi)

3. LIBERAL COLLAPSE → FASCIST DEFAULT: Liberal institutions fail to
   maintain legitimation bargain. No revolutionary alternative ready.
   Population defaults to fascist institutions that promise order.
   The Democratic Party coalition collapses; MAGA absorbs the void.
   This is the "assimilation trap" from 033 at the institutional level.

**Revolutionary Consolidation Requirements**:
For revolutionary bifurcation to consolidate (not collapse into
counter-revolution), the following institutional conditions must hold:

1. Alternative institutions exist for critical social functions
2. Alternative coverage * legitimacy > replacement threshold
3. Solidarity topology resilient (033: high β₁, low singletons)
4. Community consciousness weighted solidarity is high (033)
5. State institutional coherence degraded
   (high internal_contestation across RSA institutions,
    inter-institutional conflicts active,
    Bonapartist tendencies fragmenting state response)

**BifurcationResult Extension**:
```python
class ExtendedBifurcationResult(BifurcationResult):
    """Extends 033 BifurcationResult with institutional dimension."""

    # Institutional readiness for revolutionary consolidation
    alternative_institution_coverage: dict[SocialFunction, float]
    critical_gaps: list[SocialFunction]  # Functions with no alternative
    consolidation_viability: float  # [0,1]

    # State institutional coherence
    state_internal_contestation: float  # Mean across RSA institutions
    inter_institutional_conflict_count: int
    bonapartist_institutions: list[str]  # IDs of Bonapartist-mode institutions
    state_coherence: float  # [0,1] — how unified is state response

    # Fascist consolidation pathway
    fascist_pathway: Literal["revanchist", "bonapartist", "liberal_collapse", "none"]
    revanchist_institutional_penetration: float

    # The ruling-class bifurcation (mirrors the George Jackson bifurcation
    # but WITHIN the ruling class)
    ruling_class_faction_balance: dict[RulingClassFraction, float]
```

REQUIRED OUTPUTS:

**Analysis Functions**:
- compute_institutional_readiness(institutions, alternatives) -> float
- compute_state_coherence(rsa_institutions) -> float
- identify_critical_gaps(alternatives, social_functions) -> list
- compute_fascist_pathway(institutions, crisis) -> str
- extended_bifurcation(G, H, consciousness, institutions) -> ExtendedBifurcationResult

**Models**:
- ExtendedBifurcationResult
- ConsolidationViability
- FascistPathway

VALIDATION CRITERIA:
- Revolution without alternative institutions → consolidation_viability low
- Revolution WITH alternatives → consolidation_viability high
- High state internal_contestation → state_coherence low → revolution easier
- Revanchist institutional capture → fascist_pathway = "revanchist"
- Bonapartist emergence → fascist_pathway = "bonapartist"
- Liberal collapse without revolutionary alternative → "liberal_collapse"
- Critical gaps in social function coverage → counter-revolution risk
- Detroit test: full institutional landscape affects bifurcation outcome

CONSTRAINTS:
- Integrates with existing BifurcationResult (extends, doesn't replace)
- All institutional data flows from Phase 1-5 models
- No magic constants

DEPENDENCIES:
- Requires: 036-040, 033-bifurcation-topology
```

---

## Dependency Graph

```
Community Hyperedge Layer + CommunityConsciousness (IMPLEMENTED) ──────┐
030-organization-base-model ──────────────────────────────────────────┐│
031-ooda-loop-system ────────────────────────────────────────────────┐││
032-attention-thread-system ────────────────────────────────────────┐│││
033-bifurcation-topology ──────────────────────────────────────────┐││││
                                                                   │││││
036-institution-base-model ◄───────────────────────────────────────┘││││
    │                                                               ││││
    ├── 037-institutional-capture ◄─────────────────────────────────┘│││
    │       │                                                        │││
    │       └── 038-org-institution-transition                       │││
    │                                                                │││
    ├── 039-bonapartism-factional-dynamics ◄──────────────────────────┘││
    │       (modulates attention thread behavior via OODA)             ││
    │                                                                  ││
    ├── 040-institutional-destruction-replacement ◄────────────────────┘│
    │       (requires bifurcation as outcome variable)                  │
    │                                                                   │
    └── 041-institution-bifurcation-integration ◄───────────────────────┘
            (capstone: extends BifurcationResult)
```

Recommended implementation order: 036 → 037 → 039 → 038 → 040 → 041

- 036 (base model) is foundation, must be first
- 037 (capture) needed early because it's core gameplay
- 039 (Bonapartism) is the most novel mechanic, benefits from stable base
- 038 (transition) is a player decision system, less complex
- 040 (destruction/replacement) is the strategic endgame
- 041 (integration) is capstone, needs everything else

---

## Cross-Cutting Concerns

### The Three-Layer Architecture

| Layer | Entities | Agency | Persistence | Role |
|-------|----------|--------|-------------|------|
| **Substrate** | SocialClass, Territory, Community hyperedges | None | Continuous | Material base |
| **Institution** | All Institution types | None (structural selectivity) | Self-reproducing | Agent-generating substrate; sites of class struggle |
| **Agent** | Organization (4 subtypes) | OODA loops | Requires active participation | Decision-making, action execution |

### The Althusserian RSA/ISA Thread

| Spec | RSA Dimension | ISA Dimension | Economic Dimension |
|------|--------------|---------------|-------------------|
| 036 | apparatus_type classification | apparatus_type classification | ECONOMIC subtypes |
| 037 | RSA capture = coup, revolution | ISA capture = war of position | Economic capture = market power |
| 039 | Factional warfare within RSA | Less relevant (ISA more diffuse) | Corporate factional politics |
| 040 | RSA destruction = smash the state | ISA replacement = build counter-hegemony | Economic replacement = new mode of production |
| 041 | State coherence for bifurcation | ISA landscape for consolidation | Economic base for reproduction |

### The Bonapartism Thread

| Spec | Role |
|------|------|
| 036 | InternalBalanceOfForces model, RulingClassFraction enum |
| 037 | Crisis exploitation of internal contradictions |
| 039 | Full factional dynamics, OODA modulation, inter-institutional conflict |
| 041 | State coherence degradation as revolutionary opening; fascist pathway selection |

### The War of Position Thread (Gramsci)

| Spec | Gramscian Mechanic |
|------|-------------------|
| 037 | Entryism, material capture — "conquering combat positions" |
| 038 | Building new institutions — "creating an opposing civil society" |
| 040 | Alternative institution building — counter-hegemonic infrastructure |
| 041 | Consolidation — "the conquest of hegemony precedes the conquest of power" |

### The Replacement Principle Thread

| Spec | How Replacement Appears |
|------|------------------------|
| 036 | social_function field on Institution |
| 040 | AlternativeInstitution model, coverage + legitimacy tracking |
| 041 | critical_gaps analysis, consolidation_viability |

### Integration with Organization Specs (030-035)

| Org Spec | Institution Integration Point |
|----------|------------------------------|
| 030 (base) | Organization.institution_id → housed_in relationship; deprecate is_institution |
| 031 (OODA) | InternalBalanceOfForces modulates housed org OODA profiles |
| 032 (attention) | Factional hegemony determines state escalation logic |
| 033 (bifurcation) | Extended with institutional readiness + state coherence |
| 034 (NPC AI) | StateAI behavior depends on hegemonic_fraction of housing institution |
| 035 (territory) | Institution.territory_ids, fixed_assets spatial dimension |

### The D-P-D' Institutional Dimension

| Lifecycle Phase | Institutional Form | Control Effect |
|----------------|-------------------|----------------|
| D (Dependent/Youth) | Schools, childcare, youth programs | Controls ideological transmission to next generation |
| P (Productive/Adult) | Workplaces, unions, firms | Where surplus extraction and class struggle occur |
| D' (Dependent'/Elder) | Pensions, elder care, Social Security | The legitimation bargain — promise that justifies P-phase compliance |

Controlling D-phase institutions is the LONG GAME of ideological struggle.
Whoever controls schools controls the next generation's consciousness.
This is why educational ISAs are Althusser's primary example.

### Consciousness Interaction

| Institution Action | Consciousness Effect |
|-------------------|---------------------|
| RSA REPRESS through institution | Raises consciousness if illegitimate; lowers if seen as justified |
| ISA EDUCATE through institution | Depends on class_inscription: bourgeois → assimilationist, revolutionary → raises collective_identity |
| Alternative institution PROVIDE_SERVICE | Demonstrates that community can meet needs without hegemonic order → raises collective_identity |
| Institution capture shifts class_inscription | Changed institution now propagates different ideology through same channels |
| Institutional destruction without replacement | Social function gap → crisis_of_reproduction → backlash → LOWERS collective_identity |
