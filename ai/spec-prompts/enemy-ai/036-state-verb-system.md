# Feature Specification: State Verb System & Enemy AI Architecture

**Spec ID**: `036-state-verb-system`
**Feature Branch**: `036-state-verb-system`
**Created**: 2026-02-28
**Status**: Draft
**Depends On**: 022b-community-hyperedge-upgrade, 026-unified-class-system, 030-organization-base-model, 031-ooda-loop-system, 032-attention-thread-system, 034-npc-faction-ai-stub, 035-org-territory-integration

---

## Executive Summary

This specification defines the state's action vocabulary (six top-level verbs with sub-verbs), the factional politics model that determines how the state AI selects between those verbs, and the integration points where these systems distribute across the existing org-topology spec pipeline (030–035).

The core design claim: the state is not a unitary rational actor. It is a coalition with internal contradictions, and *which faction dominates the state apparatus at a given moment* determines the objective function weights over the verb space. The player's actions don't just provoke state *responses* — they shift *which version of the state* the player is fighting.

---

## Theoretical Foundation

### Why Six Verbs

The player's verb taxonomy (BUILD, MOBILIZE, STRIKE) reflects the strategic position of an insurgent force: building capacity from nothing, projecting that capacity outward, and attacking the existing order. The state occupies the inverse position: it already controls the material base, the legal framework, the ideological apparatus, and the means of violence. Its strategic problem is *maintenance*, not construction.

The state's six verbs reflect six structurally distinct modes of state action, each targeting a different layer of the simulation:

| Verb | Target Layer | Strategic Mode | Player Equivalent |
|------|-------------|----------------|-------------------|
| ADMINISTER | State apparatus (self) | Internal capacity reproduction | BUILD |
| DEVELOP | Territory / material base | Reshape the ground | *None* (asymmetric) |
| RESEARCH | Technology / capability space | Expand action space | *None* (asymmetric) |
| CO-OPT | Civil society / opposition | Absorb or neutralize | MOBILIZE (inverse) |
| REPRESS | Organizations / topology | Destroy or degrade | STRIKE (inverse) |
| WITHDRAW | Territory / commitment | Concede or reposition | *None* (asymmetric) |

Three verbs (ADMINISTER, CO-OPT, REPRESS) are rough mirrors of the player's three categories, operating from the opposite strategic position. Three verbs (DEVELOP, RESEARCH, WITHDRAW) are asymmetric — the player has no equivalent because these require state-level control over the material base, the legal framework, or sovereign territory.

This asymmetry is the point. The player cannot reshape the material base, cannot legislate, cannot invest in infrastructure or conduct R&D. The player can only organize, educate, and strike. The state can do all of those things *and* change the rules of the game, change the physical territory, and walk away. The asymmetry means the player wins not by matching the state's verb-for-verb but by making the state's verbs self-defeating — every REPRESS generates radicalization, every DEVELOP displaces but also concentrates, every CO-OPT attempt reveals the gap between promise and reality.

### The State as Factional Coalition

The state's objective function is not fixed. It is the *resultant* of competing factional interests within the ruling class, mediated through state apparatus control.

Three factions, each with distinct material bases and strategic preferences:

**Finance-Capital Faction**: Material base in extraction efficiency, capital circulation, and rent capture. Prefers stability over disruption. Favors CO-OPT and DEVELOP because repression disrupts markets. Tolerates organizing as long as it doesn't threaten accumulation. Will sacrifice political allies to preserve extraction flows. Strategic weakness: cannot tolerate profit rate decline, will escalate rapidly when accumulation is threatened.

**Security-State Faction**: Material base in the repressive apparatus itself — police, military, intelligence, courts, prisons. Budget and institutional power grow with threat levels. Favors REPRESS and ADMINISTER (expanding surveillance, hiring, legal authority). Institutional incentive to *maintain* threat perception even when actual threat is low. Strategic weakness: repression generates the conditions for its own escalation (each crackdown radicalizes, justifying the next).

**Settler-Populist Faction**: Material base in the imperial rent distributed to the settler nation — property values, wage premiums, cultural dominance. Favors DEVELOP (as displacement/gentrification), CO-OPT (bribe the labor aristocracy), and WITHDRAW (abandon "undesirable" territories). Provides mass base for fascism when imperial rent contracts. Strategic weakness: dependent on continued imperial rent flow; when the bribe runs out, this faction either radicalizes toward fascism or fragments.

No faction is monolithic. The factional balance shifts continuously based on material conditions (profit rate, crisis intensity, imperial rent pool) and player actions. The state AI's behavior at any moment reflects the *current dominant faction's* weighting over the verb space.

### Fascism as Factional Convergence

The George Jackson bifurcation becomes concrete through factional dynamics. Fascism is not "the state gets mean." It is what happens when:

1. The security-state faction achieves internal dominance (repression becomes the primary mode)
2. The settler-populist faction provides mass base (lateral antagonism mobilized along contradiction axes)
3. The finance-capital faction acquiesces (because their other options — concession, co-optation — have failed or become too expensive)

The player can read this convergence happening in the shifting verb preferences of the state AI. If the state stops CO-OPTing and starts REPRESSing everything, if DEVELOP shifts from "investment" to "displacement," if the settler-populist faction's collective_identity on the SETTLER hyperedge is rising — the factional balance has shifted and the timeline to bifurcation is shortening.

---

## State Verb Taxonomy

### ADMINISTER — Internal Capacity Management

The state reproducing and expanding its own apparatus. Analogous to the player's BUILD but from a position of incumbency. Low external visibility.

**Sub-verbs:**

**FUND**: Allocate budget to a specific apparatus (police, courts, social services, schools). The primary mechanism through which factional priorities become material. Funding surveillance expands thread capacity; funding social services raises legitimacy but reduces repression budget; funding schools controls D-phase ideological transmission.

| Parameter | Type | Description |
|-----------|------|-------------|
| target_apparatus | str | ID of the StateApparatus or CivilSocietyOrg receiving funds |
| amount | float | Budget allocation (from state revenue pool) |
| duration | int | Ticks of sustained funding (minimum 4, one month) |

Effects: Increases target apparatus capacity attributes (violence_capacity, surveillance_capacity, service_capacity). Reduces available state budget for other allocations. Faction-dependent: security-state faction funds repressive apparatus; finance-capital funds regulatory/stabilization; settler-populist funds cultural institutions and border enforcement.

**STAFF**: Hire and train personnel for state apparatus nodes. The state's version of Political Education — creating analysts, training police, appointing judges. Slow but expands operational capacity permanently.

| Parameter | Type | Description |
|-----------|------|-------------|
| target_apparatus | str | ID of StateApparatus being staffed |
| role_type | StaffRole | ANALYST, OFFICER, AGENT, JUDGE, ADMINISTRATOR |
| count | int | Number of positions to fill |
| training_ticks | int | Ticks before personnel become operational |

Effects: Draws from ADULT population in territory (reduces available labor pool). Creates KeyFigure nodes within apparatus topology. Trained personnel expand OODA capacity (more analysts = faster OBSERVE; more agents = more simultaneous operations). Cost: budget + training time + personnel drawn from labor market.

**LEGISLATE**: Create new legal frameworks. How the state *changes its own rules*. Anti-protest laws, surveillance authorization, emergency powers, zoning changes, tax policy. Each law has a legitimacy cost and an operational benefit. The player cannot do this — it is an asymmetric advantage.

| Parameter | Type | Description |
|-----------|------|-------------|
| law_type | LegislationType | SURVEILLANCE_AUTH, ANTI_PROTEST, EMERGENCY_POWERS, ZONING, TAX_INCENTIVE, LABOR_REGULATION |
| scope | Jurisdiction | MUNICIPAL, COUNTY, STATE, FEDERAL |
| severity | float | [0,1] — how aggressive the legislation is |

Effects: Modifies game rules within scope. SURVEILLANCE_AUTH increases observation_ceiling for threads in jurisdiction. ANTI_PROTEST raises Heat generation for PROTEST actions. EMERGENCY_POWERS temporarily doubles attention threads but at severe legitimacy cost. ZONING enables DEVELOP actions in target territory. Legitimacy cost proportional to severity — draconian laws are effective but delegitimizing.

**AUDIT**: Internal review of apparatus effectiveness. Counter-intelligence directed inward. Detects corruption, inefficiency, or infiltration by the player. The state's Rectification.

| Parameter | Type | Description |
|-----------|------|-------------|
| target_apparatus | str | ID of StateApparatus being audited |
| depth | AuditDepth | ROUTINE, THOROUGH, DEEP |

Effects: ROUTINE detects gross inefficiency, costs 1 tick. THOROUGH detects corruption and moderate infiltration, costs 4 ticks, ties up CL-equivalent within apparatus. DEEP detects sophisticated infiltration, costs 12 ticks, temporarily reduces apparatus operational capacity during audit (disruption from internal investigation). Returns IntelReport on apparatus health.

---

### DEVELOP — Reshape the Material Base

The asymmetric verb. The state actively reshaping the territory layer — not attacking organizations, but changing the ground they operate on. Gentrification is DEVELOP. Highway construction is DEVELOP. Eminent domain, tax increment financing districts, opportunity zones — all DEVELOP.

**Sub-verbs:**

**INVEST**: Direct capital investment into a territory. Infrastructure, commercial development, public works. Raises property values, changes economic character of territory, attracts different class composition.

| Parameter | Type | Description |
|-----------|------|-------------|
| territory_id | str | Target territory (H3 hexagon) |
| investment_type | InvestmentType | INFRASTRUCTURE, COMMERCIAL, RESIDENTIAL, INSTITUTIONAL |
| amount | float | Budget allocation |
| duration | int | Ticks of sustained investment |

Effects: Increases territory economic value (property values rise). Changes UseValue profile of territory (new businesses, different sectors). Over time, raises cost-of-living (V_reproduction increases for existing residents). Attracts higher-wealth population (potential LA in-migration). Precondition for displacement cascade. Faction-dependent: finance-capital invests for extraction; settler-populist invests for cultural displacement; security-state invests in hardened infrastructure.

**REZONE**: Change legal land use categories. Converts residential to commercial, enables luxury development, destroys existing housing stock through regulatory means. Requires prior LEGISLATE (ZONING) at appropriate jurisdiction.

| Parameter | Type | Description |
|-----------|------|-------------|
| territory_id | str | Target territory |
| new_zoning | ZoningType | RESIDENTIAL, COMMERCIAL, MIXED_USE, INDUSTRIAL, INSTITUTIONAL |
| displacement_expected | bool | Whether rezoning is likely to displace current residents |

Effects: Enables new investment types in territory. If displacement_expected=True, begins displacement countdown — existing residents face rising costs and regulatory pressure. Community infrastructure in territory begins to degrade (gathering spaces rezoned, service providers priced out). Low immediate visibility but devastating long-term effects.

**DISPLACE**: Active removal of population from territory. Eminent domain, code enforcement, demolition, "urban renewal." The kinetic end of DEVELOP. High visibility, high legitimacy cost, but achieves rapid territorial transformation.

| Parameter | Type | Description |
|-----------|------|-------------|
| territory_id | str | Target territory |
| mechanism | DisplacementMechanism | EMINENT_DOMAIN, CODE_ENFORCEMENT, RENT_INCREASE, DEMOLITION, TAX_FORECLOSURE |
| target_class | ClassPosition | None | Which class is primarily affected (None = indiscriminate) |

Effects: Forces population out of territory. Severs TENANCY edges. Destroys community infrastructure tied to territory. Scattered population loses organizational connections (solidarity edges severed). Displaced households must relocate — if no affordable territory available, push toward LUMPENPROLETARIAT. Generates Heat on the state (legitimacy cost). Generates agitation among displaced population (consciousness effect). The displaced population is the material from which revolutionary movements recruit — or from which fascist movements recruit, depending on which solidarity edges survive the displacement.

**NEGLECT**: Deliberate disinvestment. The slow DEVELOP — withdraw services, defer maintenance, allow infrastructure to decay. Lower visibility than active displacement but achieves territorial transformation over longer timescales. The mechanism by which "ghetto" is produced as a policy outcome, not a natural condition.

| Parameter | Type | Description |
|-----------|------|-------------|
| territory_id | str | Target territory |
| services_reduced | list[ServiceType] | Which public services to cut or reduce |

Effects: Reduces territory infrastructure quality. Raises V_reproduction for residents (must seek services elsewhere or go without). Lowers property values (opposite of INVEST). Over time, creates conditions for either DISPLACE (territory becomes "blighted," justifying demolition) or for future INVEST cycle (buy low, develop, sell high — the gentrification circuit). Low legitimacy cost because it's passive — the state isn't "doing" anything, it's just not maintaining. But the effects are cumulative and devastating.

---

### RESEARCH — Expand Capability Space

The only verb that modifies the state's own action space. All other verbs operate on existing game objects; RESEARCH creates new capabilities or enhances existing ones. Interfaces with the existing technology tree (technologies.json).

**Sub-verbs:**

**PURSUE_TECH**: Allocate resources to a specific technology in the tech tree. The state "researches" by funding R&D programs, contracting with private sector, or developing internal capabilities.

| Parameter | Type | Description |
|-----------|------|-------------|
| tech_id | str | ID from technologies.json |
| investment_level | float | Budget allocation (affects research speed) |
| classification | ResearchClassification | PUBLIC, CLASSIFIED, BLACK |

Effects: Advances progress toward technology unlock. PUBLIC research is visible to all (player can observe and potentially appropriate). CLASSIFIED is visible only to state apparatus with sufficient intel. BLACK is invisible unless player infiltrates the research apparatus. Higher investment_level = faster progress but higher budget cost.

Faction-dependent: security-state faction pursues Predictive Repression Systems (T009), Autonomous Disinformation (T008). Finance-capital pursues efficiency technologies. Settler-populist pursues border and surveillance tech. All factions fund LLMs (T006) because it benefits everyone — the disagreement is over application, not development.

**Player appropriation mechanic**: When a technology is researched, it becomes *potentially* available to the player. PUBLIC research is immediately appropriable if the player has cadre with relevant skills. CLASSIFIED requires intelligence gathering. BLACK requires infiltration of research apparatus. The player doesn't "research" — they seize, replicate, or repurpose. Cultural or ideological factors (anti-AI sentiment, pacifism, Luddism within the org's community base) can prevent adoption even when technically possible.

**DEPLOY_TECH**: Activate a researched technology in a specific apparatus or territory.

| Parameter | Type | Description |
|-----------|------|-------------|
| tech_id | str | Unlocked technology |
| target | str | Apparatus or territory receiving the technology |

Effects: Applies technology effects from technologies.json to target. Predictive Repression deployed to FBI increases PreemptiveRepression attribute. Disinformation deployed in a territory increases PublicSentiment.Confusion. Each deployment has operational costs (compute, personnel, maintenance) that consume ongoing budget.

---

### CO-OPT — Absorb, Neutralize, Divide

The ideological state apparatus in action. The state shaping civil society without direct violence. Targets organizations, communities, and the edges between them.

**Sub-verbs:**

**BRIBE**: Direct material transfer to buy loyalty or compliance. Not always literal cash — grants to NGOs, tax breaks to businesses, development contracts to neighborhoods, wage concessions to specific sectors. Converts SOLIDARISTIC edges to TRANSACTIONAL. This is how imperial rent gets distributed to maintain the labor aristocracy.

| Parameter | Type | Description |
|-----------|------|-------------|
| target | str | Organization ID or SocialClass block ID |
| bribe_type | BribeType | GRANT, TAX_BREAK, CONTRACT, WAGE_CONCESSION, PATRONAGE |
| amount | float | Material value of the bribe |
| conditions | list[str] | What the state expects in return (may be implicit) |

Effects: Increases target's material resources. Creates or strengthens TRANSACTIONAL edge between state and target. If target is a CivilSocietyOrg, shifts its consciousness_tendency toward ASSIMILATIONIST_LIBERAL (the price of the grant is political moderation). If target is a SocialClass block, raises their material position (Φ increases), reducing revolutionary potential. The Rightist Trap weaponized: workers who receive wage concessions defend the system at crisis moment.

Legitimacy effect: positive (state provides). Consciousness effect: pushes collective_identity downward ("the system works for us"). Budget cost: direct. The state can run out of bribe capacity — when imperial rent contracts, the bribe pool shrinks, and the labor aristocracy faces the material reality that was always underneath.

**PROPAGANDIZE**: Narrative control through media, education, and cultural institutions. Shape consciousness in a territory or community. Contests the player's Counter-Narrative and EDUCATE verbs.

| Parameter | Type | Description |
|-----------|------|-------------|
| target_community | CommunityType | None | Specific community to target (None = general population) |
| target_territory | str | None | Specific territory (None = jurisdiction-wide) |
| narrative | PropagandaNarrative | WE_ARE_ALL_AMERICANS, THREAT_NARRATIVE, REFORM_IS_WORKING, DELEGITIMIZE_OPPOSITION |
| intensity | float | [0,1] — resource allocation |

Effects: WE_ARE_ALL_AMERICANS directly attacks collective_identity of marginalized communities (ASSIMILATE action). THREAT_NARRATIVE raises SETTLER collective_identity (activates lateral antagonism — settler-populist faction preference). REFORM_IS_WORKING reinforces ASSIMILATIONIST_LIBERAL tendency ("the system can be fixed from within"). DELEGITIMIZE_OPPOSITION targets specific organizations, reducing their REP and SL recruitment rate.

Effectiveness scales with media infrastructure control in territory. Cheaper than direct action because institutional backing amplifies the message. Less effective per-capita than face-to-face EDUCATE but reaches far more people. The state's preferred first line of defense — if PROPAGANDIZE keeps collective_identity low, expensive repression is unnecessary.

**INCORPORATE**: Absorb opposition leadership into the system. Offer the community organizer a city council seat. Offer the activist group 501(c)(3) status and foundation funding. The Liberal Trap weaponized — specifically targets high-CL nodes and attempts to convert them from PoliticalFaction membership to CivilSocietyOrg membership (neutered, grant-dependent, legible).

| Parameter | Type | Description |
|-----------|------|-------------|
| target_figure | str | KeyFigure ID within a target organization |
| offer_type | IncorporationOffer | ELECTORAL_CANDIDACY, NONPROFIT_STATUS, ADVISORY_POSITION, ACADEMIC_APPOINTMENT, MEDIA_PLATFORM |
| resources | float | Material support accompanying the offer |

Effects: If target accepts (probability based on target's consciousness, org's Coherence, and offer attractiveness relative to current material conditions), the KeyFigure is removed from their current organization and placed in a state-aligned or neutralized institution. The source organization loses a cadre (CL decreases). If the target was a high-centrality node (Sparrow singleton), their removal may fragment the org's internal topology.

Acceptance probability: inversely proportional to collective_identity of target's primary community AND the target's org Coherence. High-CI, high-Coherence orgs resist incorporation. Low-CI, low-Coherence orgs hemorrhage leadership to incorporation offers. This is why the state pushes ASSIMILATIONIST consciousness *before* attempting incorporation — soften the ideological ground first, then pick off leaders.

**DIVIDE**: Manufacture ANTAGONISTIC edges between opposition groups. The Hoover directive operationalized. Spread rumors, fund sectarian disputes, leak selective intelligence to pit organizations against each other. Targets *edges*, not nodes. Cheap, deniable, devastating to percolation.

| Parameter | Type | Description |
|-----------|------|-------------|
| target_edge | tuple[str, str] | The two organization IDs whose relationship to attack |
| method | DivisionMethod | RUMOR, SELECTIVE_LEAK, PROVOCATEUR, FUND_RIVAL, IDENTITY_WEDGE |
| intensity | float | [0,1] — resource allocation |

Effects: Degrades edge between target organizations. SOLIDARISTIC → TRANSACTIONAL → ANTAGONISTIC over repeated applications. IDENTITY_WEDGE specifically activates contradiction pair dynamics — exploit the colonial axis or patriarchal axis to break cross-line solidarity ("why are you working with settlers?" / "why are you centering men?"). Most effective when collective_identity is moderate (high enough to feel the contradiction, low enough to lack the framework to transcend it).

Low budget cost (rumors are cheap). Low Heat (deniable). But requires intelligence — you need to know which edges exist and what the pressure points are. Requires attention thread investment in prior SURVEIL. This is why the state surveils even when it's not planning to repress — intelligence enables division, which is cheaper than repression and often more effective.

---

### REPRESS — Direct State Violence

The kinetic verb. Analogous to the player's STRIKE but with vastly more resources and the legitimacy shield (at least initially). Each sub-verb represents a step up the escalation ladder; each step costs more legitimacy but delivers more immediate effect.

**Sub-verbs:**

**SURVEIL**: Allocate an attention thread to passive intelligence gathering on a territory, organization, or community. Low cost, low visibility, but thread-consuming. The foundation for all other REPRESS actions and for DIVIDE (under CO-OPT).

| Parameter | Type | Description |
|-----------|------|-------------|
| target_type | TargetType | TERRITORY, ORGANIZATION, COMMUNITY |
| target_id | str | ID of target |
| method | SurveillanceMethod | SIGNALS, FINANCIAL, SOCIAL_MEDIA, INFORMANT, PHYSICAL |

Effects: Creates or intensifies an AttentionThread on target. Expands observed_subgraph incrementally. Different methods reveal different intelligence: SIGNALS reveals communication patterns (edge existence, not content). FINANCIAL reveals resource flows. SOCIAL_MEDIA reveals public-facing topology. INFORMANT reveals internal state (but with distortion — informant incentive problems from Sparrow). PHYSICAL reveals face-to-face meetings. Observation ceiling modified by target community's infiltration_resistance.

**INFILTRATE**: Insert a corrupted node into a target organization. The critical gap identified in state-repression-research.md. The informant doesn't just gather intelligence — they degrade Coherence from inside, introduce bad decisions, provoke premature action, create paranoia.

| Parameter | Type | Description |
|-----------|------|-------------|
| target_org | str | Organization ID to infiltrate |
| agent_type | InfiltrationAgentType | INFORMANT, PROVOCATEUR, MOLE |
| cover | InfiltrationCover | RECRUIT, TRANSFER, FABRICATED_HISTORY |

Effects: INFORMANT passively reports on org topology and plans (boosts intel_completeness for the attention thread on this org). PROVOCATEUR actively degrades: pushes for premature action (Ultra-Left Trap), introduces sectarian disputes (internal DIVIDE), generates Heat through visible operations the org didn't authorize. MOLE occupies leadership position (requires long infiltration timeline) and steers the org away from effective action.

Infiltration success probability modified by: target org's internal_topology (CELL structure limits exposure), target org's Coherence (high-Coherence orgs detect outsiders faster), community infiltration_resistance (embedded community notices strangers), and the state's observation_ceiling (can't insert agents you don't understand into structures you can't see).

Counter: player's COUNTER_INTEL action. Periodic vetting, compartmentalization, trust networks. The trade-off: aggressive counter-intel protects against infiltration but consumes CL and creates paranoia that itself degrades Coherence (the COINTELPRO double bind — the *threat* of infiltration is itself a weapon even without actual agents).

**RAID**: Kinetic action against a specific location, event, or organization. Arrests, seizures, disruption. High thread cost, high visibility, generates Heat on the state (legitimacy cost). Effective against physical infrastructure but can backfire.

| Parameter | Type | Description |
|-----------|------|-------------|
| target | str | Organization ID, territory ID, or event ID |
| scale | RaidScale | TARGETED, SWEEP, MASS |
| force_level | ForceLevel | POLICE, SWAT, MILITARY |
| legal_basis | LegalBasis | WARRANT, EMERGENCY, EXTRALEGAL |

Effects: TARGETED removes specific KeyFigures (arrests) or specific assets (seizures). Requires prior SURVEIL or INFILTRATE intelligence to identify targets. Minimal collateral. SWEEP covers a territory — arrests anyone matching a profile, seizes anything visible. Higher collateral, lower precision, higher legitimacy cost. MASS is a crackdown — widespread arrests, curfews, show of force. Maximum immediate suppression but generates maximum radicalization. Legal basis affects legitimacy cost: WARRANT is lowest, EXTRALEGAL is highest.

Consciousness side-effect: Raids raise ideological_contestation within affected communities. If community collective_identity is already high, raid radicalizes further (confirms the framework — "we told you the state is the enemy"). If collective_identity is low, raid can go either way — either it's a wake-up call or it's terrifying enough to suppress dissent. This is the dialectic: repression either crushes or radicalizes, and the direction depends on the ideological terrain at the moment of impact.

**PROSECUTE**: Legal warfare. Slower than raids but drains the target's resources, ties up leadership, and creates chilling effects. The state's attrition weapon.

| Parameter | Type | Description |
|-----------|------|-------------|
| target_figure | str | KeyFigure ID (individual) or target_org for org-level prosecution |
| charges | list[ChargeType] | CONSPIRACY, RACKETEERING, TAX, CIVIL_RIGHTS_VIOLATION, TERRORISM |
| severity | ProsecutionSeverity | MISDEMEANOR, FELONY, FEDERAL |

Effects: Target KeyFigure's CL contribution to their org drops to zero for prosecution duration (tied up in court). Target org must divert budget to legal defense. Duration proportional to severity — misdemeanor resolves in weeks, federal conspiracy case runs for years. If conviction: target removed from play (INCARCERATED hyperedge membership, D-P-D' circuit interrupted). If acquittal: target returns with increased REP (surviving prosecution is a legitimacy win).

Chilling effect: orgs in the same territory as a prosecution target experience reduced SL recruitment rate (potential sympathizers scared off). Proportional to severity of charges and media coverage.

**LIQUIDATE**: Assassination, forced disappearance, extreme rendition. The verb that dare not speak its name.

| Parameter | Type | Description |
|-----------|------|-------------|
| target_figure | str | KeyFigure ID |
| method | LiquidationMethod | ASSASSINATION, DISAPPEARANCE, RENDITION, PRISON_KILLING |
| deniability | float | [0,1] — how much effort spent on deniability |

Effects: Target KeyFigure removed permanently. If target was a Sparrow singleton, their removal may fragment the org (topological consequence). If target was high-profile, generates massive legitimacy cost for the state UNLESS deniability is high. PRISON_KILLING (target already INCARCERATED) is the most deniable — "died in custody," "prison violence."

Availability constraints: Available only under EMERGENCY_POWERS (from LEGISLATE) OR in territories with low international visibility OR against targets the state has classified as "terrorist" (requires prior PROSECUTE or LEGISLATE enabling designation). In core territories with high legitimacy and media presence, LIQUIDATE is extremely costly — this is why the state prefers to PROSECUTE and let the carceral system do the killing slowly. In peripheral territories or against undocumented populations, LIQUIDATE is nearly free. *This asymmetry is the colonial relation expressed as a game mechanic.*

---

### WITHDRAW — Concede, Reposition, Scorch

The verb that makes the whole system strategically interesting. A state that can only fight or hold produces boring games. A state that can withdraw introduces genuine strategic dilemmas for the player: is this retreat real? What are they leaving behind? What are they planning?

**Sub-verbs:**

**STRATEGIC_WITHDRAWAL**: The state concedes a territory because holding it costs more than it's worth. White flight, capital flight, base closures, service withdrawal. The state pulls apparatus out but *hollows the territory first*. Defunds services, lets infrastructure decay, pulls investment. The liberated territory becomes a resource desert. The player "wins" but inherits a husk.

| Parameter | Type | Description |
|-----------|------|-------------|
| territory_id | str | Territory being abandoned |
| withdrawal_speed | WithdrawalSpeed | GRADUAL, RAPID |
| asset_extraction | bool | Whether the state extracts remaining value before leaving |

Effects: State apparatus PRESENCE edges removed from territory. If asset_extraction=True, state seizes or destroys remaining state-owned infrastructure (schools, hospitals, utilities) or sells them to private interests (TRANSACTIONAL → extraction continues without state presence). Territory enters NEGLECT trajectory — infrastructure decays without maintenance, services disappear. V_reproduction rises for remaining population.

The player must decide: is this territory worth holding? Can the org provide the services the state abandoned? If yes, the territory becomes a liberated zone — a base for revolutionary organizing outside state control. If no, the territory becomes a trap — a resource sink that drains organizational capacity for no strategic gain. *This is the historical pattern of Black neighborhoods post-civil-rights: formal control without material base.*

**TACTICAL_RETREAT**: Temporary withdrawal to consolidate attention threads elsewhere. Not a concession — a repositioning. The state stops actively contesting the territory for a window but doesn't abandon its apparatus or infrastructure.

| Parameter | Type | Description |
|-----------|------|-------------|
| territory_id | str | Territory with reduced state attention |
| duration | int | Expected ticks of reduced presence |
| reason | RetreatReason | THREAD_REALLOCATION, CRISIS_ELSEWHERE, POLITICAL_PRESSURE |

Effects: Attention threads targeting the territory or orgs within it are redirected. State apparatus remains but at reduced operational tempo. Creates a window of opportunity for the player — reduced surveillance, reduced repression, more room to operate. But the window closes. If the player overextends during the window (builds visible infrastructure, recruits openly, generates Heat), the state returns to a *better-informed* position (it saw what happened while it was "away").

Danger for the player: treating a tactical retreat as permanent. Building openly in a territory the state merely stepped away from for a few ticks means the player has exposed their topology when the threads come back. This is the "honeypot" scenario — sometimes the state withdraws *specifically to see what emerges*.

**SCORCHED_EARTH**: The state cannot hold the territory and doesn't want the player to benefit from it. Active destruction of productive capacity, infrastructure, records. The nuclear option.

| Parameter | Type | Description |
|-----------|------|-------------|
| territory_id | str | Territory to devastate |
| destruction_targets | list[InfrastructureType] | What specifically to destroy |
| population_action | PopulationAction | IGNORE, EVACUATE, BLOCKADE |

Effects: Targeted infrastructure destroyed. If BLOCKADE: territory becomes inaccessible (no in-migration, no resource flows — siege conditions). Population trapped inside faces rising V_reproduction with no relief. EVACUATE forces population out (mass displacement — generates refugees, strains surrounding territories, creates humanitarian crisis that either generates sympathy for the player or overwhelms the player's capacity to respond).

Massive legitimacy cost in core territories. Nearly free in peripheral territories or territories the state has successfully delegitimized ("it was a lawless zone," "we had to restore order"). Historically: what colonial powers do on their way out. What the US did to Black Wall Street. What Israel does in Gaza. The mechanic must reflect the colonial asymmetry — the legitimacy cost is not inherent in the action but in who is watching and what they believe.

---

### NEGOTIATE — Not a Verb, a Resolution Mechanic

Negotiation is not a strategic mode. It is a *resolution mechanic* within modes the state has already committed to. The state doesn't negotiate because it wants to talk; it negotiates because it's already decided to WITHDRAW or CO-OPT and needs to determine the price.

WITHDRAW + negotiation = negotiating the terms of concession. What does the state retain? What infrastructure remains? What ongoing obligations? The player can demand service continuation, infrastructure preservation, or reparations as conditions. The state can accept, counter-offer, or abort the withdrawal.

CO-OPT + negotiation = negotiating the terms of the bribe. What does the state offer? What does it demand in return? The player can negotiate on behalf of their constituency — accepting a bribe that benefits the community while preserving organizational independence, or rejecting because the conditions are too compromising. Accepting generates the Rightist Trap risk; rejecting preserves revolutionary potential but at material cost to the community.

Negotiation probability: the state only opens negotiation when its cost-benefit analysis favors concession over continued contest. This depends on: the player's demonstrated capacity (credible threat), the state's resource constraints (can it afford to keep fighting?), factional balance (finance-capital faction prefers negotiated resolution to costly conflict), and legitimacy pressure (public opinion favors compromise).

---

## Factional Politics Model

### StateFaction Enum

```python
class StateFaction(Enum):
    FINANCE_CAPITAL = "finance_capital"
    SECURITY_STATE = "security_state"
    SETTLER_POPULIST = "settler_populist"
```

### FactionBalance Model

```python
class FactionBalance(BaseModel):
    """Tracks which faction dominates the state apparatus.

    The balance determines the objective function weights
    over the state's verb space. Shifts based on material
    conditions and player actions.
    """
    faction_weights: dict[StateFaction, float]
    # Sum to 1.0. Dominant faction = highest weight.
    # e.g., {FINANCE_CAPITAL: 0.5, SECURITY_STATE: 0.3, SETTLER_POPULIST: 0.2}

    dominant_faction: StateFaction  # Computed from weights

    stability: float  # [0,1] — how stable the current balance is
    # Low stability = balance is shifting, state behavior is inconsistent
    # High stability = clear dominant faction, coherent state strategy

    legitimacy: float  # [0,1] — overall state legitimacy
    # Aggregated from: service provision, representation, economic performance
    # Low legitimacy = state can't CO-OPT (nobody believes the bribe)
    # and REPRESS becomes more costly
```

### Faction Verb Preferences

Each faction has a preference weighting over the six top-level verbs. The dominant faction's preferences bias — but do not fully determine — the state AI's verb selection.

```python
FACTION_VERB_PREFERENCES: dict[StateFaction, dict[StateVerb, float]] = {
    StateFaction.FINANCE_CAPITAL: {
        ADMINISTER: 0.15,  # Moderate — maintain but don't expand
        DEVELOP: 0.30,     # High — reshape territory for extraction
        RESEARCH: 0.15,    # Moderate — efficiency tech
        CO_OPT: 0.25,      # High — stability through absorption
        REPRESS: 0.05,     # Low — disrupts markets
        WITHDRAW: 0.10,    # Moderate — cut losses when needed
    },
    StateFaction.SECURITY_STATE: {
        ADMINISTER: 0.25,  # High — expand apparatus
        DEVELOP: 0.05,     # Low — not their domain
        RESEARCH: 0.20,    # High — repression tech
        CO_OPT: 0.10,      # Low — prefer force
        REPRESS: 0.35,     # Very high — core competency
        WITHDRAW: 0.05,    # Very low — never retreat
    },
    StateFaction.SETTLER_POPULIST: {
        ADMINISTER: 0.10,  # Low — distrust bureaucracy
        DEVELOP: 0.25,     # High — displacement, gentrification
        RESEARCH: 0.05,    # Low — anti-intellectual tendency
        CO_OPT: 0.20,      # Moderate — bribe the base
        REPRESS: 0.20,     # Moderate — punish enemies
        WITHDRAW: 0.20,    # High — abandon "undesirable" zones
    },
}
```

These are starting preferences, not hard constraints. Crisis intensity, player actions, and resource availability all modify the effective weights at decision time.

### Faction Balance Dynamics

The factional balance shifts as a Layer 3 consequence of state and player actions:

**Player actions that shift faction balance:**

| Player Action | Effect on Faction Balance |
|---------------|--------------------------|
| Generate Heat (visible organizing) | +SECURITY_STATE weight (justifies their budget) |
| Disrupt extraction (strike, sabotage) | +SECURITY_STATE initially, +FINANCE_CAPITAL panic if sustained |
| Build legitimacy (mutual aid, services) | +CO_OPT pressure from FINANCE_CAPITAL ("absorb this") |
| Win narrative victories | +SETTLER_POPULIST reaction (cultural threat response) |
| Survive repression | -SECURITY_STATE credibility ("they're not working") |
| Accept CO-OPT offers | +FINANCE_CAPITAL ("see, this works") |
| Reject CO-OPT offers | +SECURITY_STATE ("told you, force is necessary") |

**Material conditions that shift faction balance:**

| Condition | Effect on Faction Balance |
|-----------|--------------------------|
| Profit rate decline | +FINANCE_CAPITAL influence (economic crisis = their domain) |
| Imperial rent contraction | +SETTLER_POPULIST panic (their bribe is shrinking) |
| Legitimacy crisis | +SECURITY_STATE (legitimacy failure → force as substitute) |
| Successful CO-OPT | +FINANCE_CAPITAL ("the system works") |
| Failed repression | -SECURITY_STATE, +FINANCE_CAPITAL ("try money instead") |

### Fascism Threshold

Fascist convergence occurs when:

```python
def is_fascist_convergence(balance: FactionBalance, communities: dict) -> bool:
    """Detect whether factional dynamics are producing fascism."""
    security_dominant = balance.faction_weights[SECURITY_STATE] > 0.4
    settler_mobilized = (
        communities[SETTLER].consciousness.collective_identity > 0.6
        and communities[SETTLER].consciousness.dominant_tendency
            == ConsciousnessTendency.ASSIMILATIONIST_FASCIST
    )
    finance_acquiescent = balance.faction_weights[FINANCE_CAPITAL] < 0.25

    return security_dominant and settler_mobilized and finance_acquiescent
```

When all three conditions hold, the state transitions to fascist mode: CO-OPT budget redirected to REPRESS, DEVELOP becomes explicitly displacement-oriented, WITHDRAW becomes scorched earth in "enemy" territories, LEGISLATE shifts to EMERGENCY_POWERS. The factional balance stabilizes at this configuration — fascism is an absorbing state without external intervention.

---

## Integration with Existing Spec Pipeline

This specification does not stand alone. Its components distribute across the existing specs as follows:

### 030 — Organization Base Model

**Add:**
- `StateFaction` enum
- `FactionBalance` model
- `factional_alignment: StateFaction` field on `StateApparatus`
- `StateBudget` model (tracks revenue, allocation, and factional claims on budget)

Rationale: factional alignment is an organizational attribute of state apparatuses, not an AI decision. The FBI is security-state-aligned; the Commerce Department is finance-capital-aligned; the Border Patrol is settler-populist-aligned. This is substrate that the AI reads.

### 031 — OODA Loop System

**Add:**
- `StateActionType` enum (the six top-level verbs and all sub-verbs defined in this spec)
- State action resolution in Layer 1 (state acts first, applying StateActionType instead of ActionType)
- Faction balance shift as Layer 3 consequence propagation
- Budget consumption for state actions (each verb has a budget cost profile)
- `StateAction` model parallel to `Action` but with budget/thread cost instead of CL/SL cost

Rationale: the verb taxonomy is an action type system. It resolves through the same OODA framework as player actions, just with different resource profiles and in a different resolution layer.

### 032 — Attention Thread System

**Expand:**
- Thread allocation influenced by `FactionBalance` (security-state dominance = more threads allocated to REPRESS; finance-capital dominance = more threads on SURVEIL for intelligence that enables CO-OPT)
- REPRESS sub-verbs (SURVEIL, INFILTRATE, RAID, PROSECUTE, LIQUIDATE) as thread-consuming operations
- Thread cost for non-REPRESS verbs where intelligence is required (DIVIDE requires prior SURVEIL; INCORPORATE requires knowing org topology)

Rationale: the attention thread system already implements the REPRESS verb's intelligence-gathering component. The expansion adds thread costs for intelligence that supports CO-OPT and DEVELOP.

### 033 — Bifurcation Topology

**Add:**
- Fascist convergence detection (the `is_fascist_convergence` function)
- Faction balance as input to bifurcation analysis (which faction dominates at crisis moment affects which attractor the system falls toward)

Rationale: bifurcation outcome depends not just on solidarity topology but on state behavior at the crisis moment, which depends on faction balance.

### 034 — NPC Faction AI Stub

**Expand significantly:**
- State AI selects across all six verb categories using faction-weighted objective function
- Decision function reads: `FactionBalance`, `AttentionThread` reports, community `collective_identity` levels, profit rate trajectory, imperial rent pool, and player-generated `Heat`
- Escalation logic generalized: PROPAGANDIZE → CO-OPT → DEVELOP (displacement) → REPRESS → SCORCHED_EARTH as threat level rises
- De-escalation logic: when player pressure reduces, state prefers cheaper verbs (CO-OPT over REPRESS, PROPAGANDIZE over RAID)
- RESEARCH selection based on factional priorities and current capability gaps
- WITHDRAW decision based on cost-benefit: is holding this territory worth the thread cost?

Rationale: 034 is where the enemy AI decision logic lives. The six-verb taxonomy gives it a richer action space; the factional politics gives it a shifting objective function.

### 035 — Organization-Territory Integration

**Add:**
- DEVELOP verb effects on territory layer (INVEST, REZONE, DISPLACE, NEGLECT as territory state transformations)
- WITHDRAW effects on territory (STRATEGIC_WITHDRAWAL as hollowing, SCORCHED_EARTH as destruction)
- Territory economic value changes from DEVELOP feeding back into class dynamics (rising property values → displacement → class composition change)
- NEGLECT as passive DEVELOP (territory decay without active state investment)

Rationale: DEVELOP and WITHDRAW primarily operate on the territory layer. Their effects are spatial transformations that change the substrate all organizations operate on.

---

## State AI Decision Architecture

### Objective Function

The state AI maximizes a weighted sum of objectives, where the weights are determined by the current `FactionBalance`:

```python
def state_objective(
    world: WorldState,
    action: StateAction,
    balance: FactionBalance
) -> float:
    """Evaluate a candidate state action against factional objectives."""

    # Each faction has its own objective
    fc_score = finance_capital_objective(world, action)
    # Maximize: extraction_efficiency, profit_rate, stability
    # Minimize: market_disruption, uncertainty

    ss_score = security_state_objective(world, action)
    # Maximize: threat_suppression, apparatus_size, surveillance_coverage
    # Minimize: percolation_ratio, collective_identity_max

    sp_score = settler_populist_objective(world, action)
    # Maximize: settler_property_values, cultural_homogeneity, imperial_rent_to_base
    # Minimize: cross_line_solidarity, demographic_change_in_settler_territories

    # Weighted by current factional balance
    return (
        balance.faction_weights[FINANCE_CAPITAL] * fc_score
        + balance.faction_weights[SECURITY_STATE] * ss_score
        + balance.faction_weights[SETTLER_POPULIST] * sp_score
    )
```

### Decision Flow Per Tick

```
1. OBSERVE: Read world state within intelligence limits
   - AttentionThread reports (incomplete, distorted)
   - Economic indicators (profit rate, imperial rent pool, budget)
   - Community consciousness levels (inferred from public actions)
   - Player-generated Heat across territories

2. ORIENT: Apply factional lens
   - Current FactionBalance determines which threats are prioritized
   - Finance-capital: prioritizes extraction threats
   - Security-state: prioritizes organizational threats
   - Settler-populist: prioritizes cultural/demographic threats

3. DECIDE: Select verb and sub-verb
   - Generate candidate actions across all six verb categories
   - Score each candidate against factional objective function
   - Apply resource constraints (budget, threads, legal authority)
   - Select highest-scoring feasible action

4. ACT: Execute in Layer 1
   - Consume resources (budget, thread allocation)
   - Apply effects to targets

5. CONSEQUENCES (Layer 3):
   - Legitimacy changes
   - Faction balance shifts
   - Community consciousness effects
   - Player response opportunities
```

### Escalation Logic

The state prefers cheap, low-visibility actions. It escalates only when cheaper options fail.

```
Preferred order (low to high cost/visibility):

PROPAGANDIZE → BRIBE → INCORPORATE → SURVEIL → DIVIDE
    → INFILTRATE → INVEST/REZONE → FUND (security) → LEGISLATE
        → RAID → PROSECUTE → DISPLACE → STRATEGIC_WITHDRAWAL
            → EMERGENCY_POWERS → MASS_RAID → LIQUIDATE → SCORCHED_EARTH
```

The state escalates when:
- Lower-intensity actions have been tried and failed (collective_identity still rising)
- Crisis is imminent (profit rate approaching threshold, percolation ratio rising)
- Dominant faction shifts toward security-state (loss of faith in soft power)

The state de-escalates when:
- Player pressure subsides (Heat drops, visible activity decreases)
- CO-OPT succeeds (leadership incorporated, solidarity edges degraded)
- Budget pressure forces cheaper options
- Legitimacy pressure makes continued repression unsustainable

---

## Data Requirements

### State Budget Model

State budget derives from:
- Tax revenue (proportional to economic activity in jurisdiction — QCEW-derived)
- Federal transfers (for sub-federal state apparatuses)
- Imperial rent pool (for the state's discretionary capacity)

Budget is allocated across the six verb categories each tick, influenced by factional balance. Budget is finite — this is the fundamental constraint that makes state behavior strategic rather than omnipotent.

### Faction Balance Initialization (Detroit Test Case)

For Metro Detroit 2010 start:
- FINANCE_CAPITAL: 0.45 (post-crisis, finance-capital asserting control over recovery)
- SECURITY_STATE: 0.30 (heightened post-9/11, but budget-constrained)
- SETTLER_POPULIST: 0.25 (Tea Party rising but not yet dominant)

These are SYNTHETIC defaults derived from political analysis, not empirical measurement. Flag as such. Validate by: does the simulated state behavior 2010–2015 qualitatively match actual Detroit policy (emergency management, austerity, selective reinvestment in downtown/Midtown)?

---

## Validation Criteria

### VC-001: Verb Coverage
All six top-level verbs and all sub-verbs are executable by the state AI in a 52-tick test run. No verb goes unused for 52 consecutive ticks (the AI should explore the full action space over a year).

### VC-002: Factional Influence
Changing FactionBalance weights produces measurably different state verb selections over a 52-tick run. Security-state dominance increases REPRESS frequency; finance-capital dominance increases CO-OPT and DEVELOP frequency.

### VC-003: Escalation Behavior
Given rising player Heat and collective_identity, the state AI escalates from PROPAGANDIZE through SURVEIL through RAID in a legible sequence. Given declining Heat, the state de-escalates.

### VC-004: Fascist Convergence
When security-state weight > 0.4, settler collective_identity > 0.6 with ASSIMILATIONIST_FASCIST tendency, and finance-capital weight < 0.25, the state AI transitions to qualitatively different behavior (repression-dominant, displacement-oriented).

### VC-005: Budget Constraint
The state AI respects budget limits. When budget is exhausted, state actions shift to zero-cost or low-cost options (SURVEIL over RAID, PROPAGANDIZE over BRIBE, NEGLECT over INVEST).

### VC-006: DEVELOP Effects Territory
INVEST in a territory measurably changes territory economic indicators (property value proxy rises, V_reproduction rises for existing residents). NEGLECT measurably degrades territory over time. DISPLACE removes population from territory.

### VC-007: CO-OPT Effects Consciousness
PROPAGANDIZE with WE_ARE_ALL_AMERICANS narrative measurably decreases collective_identity in target community. BRIBE measurably increases material position of target while creating TRANSACTIONAL edge. INCORPORATE removes a KeyFigure from target org.

### VC-008: WITHDRAW Taxonomy
Strategic withdrawal, tactical retreat, and scorched earth produce qualitatively different territory outcomes. Strategic withdrawal hollows; tactical retreat is temporary; scorched earth destroys.

### VC-009: Player Action → Faction Shift
Player-generated Heat measurably increases security-state faction weight. Player disruption of extraction measurably increases finance-capital panic response. Player legitimacy wins increase settler-populist reaction.

### VC-010: Asymmetry
The player cannot execute any StateActionType verb. The state cannot execute player-specific verbs (Political Education generating CL, Mutual Aid creating SOLIDARITY edges from scratch). The asymmetry is enforced by the type system.

---

## Assumptions

- A-001: Three factions are sufficient to model US state behavior at the resolution relevant to Detroit. A more granular factional model (separating industrial capital from finance capital, or distinguishing between local and federal security apparatus) would be more accurate but introduces scope creep beyond what's testable with current data.
- A-002: Faction balance can be represented as a weight vector summing to 1.0. This assumes factions compete for influence over a shared state apparatus rather than controlling separate parallel apparatuses. In reality both are true; the simplification is acceptable for MVP.
- A-003: The state AI's decision function is deterministic given world state and RNG seed. No external AI service is used for state decisions in the stub implementation. The strategy pattern allows hot-swapping to an LLM-backed decision function later.
- A-004: Budget is the binding constraint for non-REPRESS verbs; attention threads are the binding constraint for REPRESS verbs. This simplification may need revisiting if playtesting reveals that budget constraints on REPRESS or thread constraints on CO-OPT produce unrealistic behavior.
- A-005: LIQUIDATE availability in core territories requires EMERGENCY_POWERS. This is a game design constraint, not a claim about reality (the state kills people without emergency powers). The constraint exists to make LIQUIDATE a late-game escalation that requires prior LEGISLATE investment, creating a legible escalation path.
- A-006: The fascist convergence threshold (security > 0.4, settler CI > 0.6, finance < 0.25) is a game design parameter, not a theoretical derivation. Calibrate through playtesting.

---

## What This Spec Does NOT Include

- Detailed implementation of each sub-verb's effect calculations (those belong in the individual specs where the systems live: 031 for action resolution, 032 for thread mechanics, 035 for territory effects)
- International state relations (other states, international pressure, sanctions — defer)
- Intra-apparatus politics (factions within the FBI, progressive prosecutors vs. law-and-order DAs — defer to granular resolution)
- Electoral mechanics (how elections change faction balance — defer, but LEGISLATE and FactionBalance provide the hooks)
- Climate change effects on state capacity (defer)
- Player-controlled state apparatus (post-revolution governance — endgame, defer)
- LLM-backed decision function for state AI (the stub is rule-based; LLM integration is a future enhancement via the strategy pattern in 034)

---

## Dependencies

```
022b-community-hyperedge-upgrade
    ↓ (consciousness model, infiltration resistance)
026-unified-class-system
    ↓ (class positions, household model, wealth dynamics)
030-organization-base-model ← adds StateFaction, FactionBalance, factional_alignment
    ↓
031-ooda-loop-system ← adds StateActionType, state Layer 1 resolution, faction shift
    ↓
032-attention-thread-system ← adds faction-influenced thread allocation, REPRESS sub-verbs
    ↓
033-bifurcation-topology ← adds fascist convergence detection
    ↓
034-npc-faction-ai-stub ← MAJOR EXPANSION: six-verb decision function, factional objective
    ↓
035-org-territory-integration ← adds DEVELOP/WITHDRAW territory effects
```

Recommended implementation order unchanged from org-topology-speckit-prompts-v4:
030 → 031 → 033 → 032 → 034 → 035

This spec's additions at each phase are incremental, not blocking. The largest expansion is at 034 (the AI decision function), which is already last in the pipeline.
