<!-- vale off -->
<!-- Research briefing: dated evidence with literal identifiers preserved. Not governed prose. -->

# 40 — Class agents on MIM's line: research brief for PER-366

*Babylon class-agent lane. Research input for the next design conversation, not a spec. Prepared 18
Nov 2026 from 19 verified reader reports. Revised the same day against an adversarial review (see
Method and revision record). The 488 verified findings, with sources, locators and quotes, are in
`40-class-agents-evidence.jsonl` beside this note.*

**How to read this brief.**
- Quotes appear only where a citation checker verified or corrected the quote.
- Where a checker corrected a claim, the corrected version is used.
- Each passage is tagged by kind:
  - **Sources say**: theory and history.
  - **Engine today**: what the Rust code and the live rulings do now.
  - **Proposal**: this brief's suggestion. Nothing here is decided.
- **[MIM forces]** marks a place where MIM's line forces a concrete design choice.
- **[Director]** marks a question that only the Director can settle.
- MCU, FRSO, RU/RCP, CPUSA, Trotskyist and social-democratic texts appear only as evidence of rival
  lines. They never support a rule for how the game models class or organizing.
- Finding IDs carry the name of the reader that produced them (for example `mim-practice F07`,
  `design-corpus F27`), because bare IDs collide across readers. Each ID resolves in
  `40-class-agents-evidence.jsonl` (one finding per line, with `reader` and `id` fields).

---

## 1. What was asked

The Director's words:

- 18 Nov 2026: "we need to develop a concept of "who" which means we need classes and groups of
  people to act as agents in the economy and before we do an endorsement we need an electoral
  system, i'm realizing we need more agents in the population"
- Opening this session, 18 Nov 2026: "I want to start factoring in the population of people as
  classes, labor supply, hypergraphs, etc. make this simulation very interesting and entertaining,
  turn it into a game"
- During the research, 18 Nov 2026: "we have to make this a class-based game as it is based on
  Marxism, look at Lawvere as well as our Marxist literature, our MIM literature"
- Earlier: "this is a simulation *game* ultimately - realism is good but as long as its emergent,
  entertaining, and resembles reality and the ideology im down with it"

Two rulings made during the research:

- "the games ideology sides with MIM"
- "MCU and FRSO are both settler communist organizations opposed to the MIM line"

**The chosen direction (option 2).** Population groups make a few bounded choices every four-week
period. Each choice is made from the group's own material accounts. Examples: keep looking for work
or stop; move county; join, attend or leave an organization; back or withhold a delegate; later,
vote. Organizations compete for those choices: the player's organization, employers, the state and
rivals.

**What a group is, and at what grain (Proposal).** A group is a cell of household cohorts at
**county scale**. Its class and nation labels are **Designed partitions valid at that scale only**.
Only the extensive profile and the signed balance (§3) are pushed forward to CZ, MSA, state and
nation; labels are never claimed to survive aggregation. This is how groups can exist without the
invariance proof Article II requires of any claimed partition ("Any claimed partition must include
an invariance proof under its declared coarse-graining", CONSTITUTION Art. II:51–52; lawvere L16,
L28). See §11 item 4.

Two alternatives were rejected:
- passive constituencies that never choose;
- every group as a full organization.

"More agents" therefore means more *counted cohort-groups that decide*. It does not mean individual
persons. NORTH_STAR says "Households are the smallest economic decision unit", and ADR270 keeps
people as conserved counts. NORTH_STAR already invites option 2: "Residents can share a class
position and choose different organizations or decline to join one." (NORTH_STAR:61, 69–71;
ADR270:23)

---

## 2. The short answer: ten theses

1. **Class is read from accounts, never stored as a label. [MIM forces] The reading is a stock that
   carries its history.** The Constitution requires class position to "emerge from composed material
   relations at a declared scale" (CONSTITUTION Art. II:50–51). Lenin, Mao and MIM all define class
   by relations. MIM adds that the labor aristocracy hardens "first as a stratum and then as a
   class" (mim-class-structure MC-16), that oppressed-nation labor aristocracies are "newer and less
   stable" (MC-16), and that "There is a high likelihood that the labor aristocracy will never be
   re-proletarianized before communism is achieved." (MC-17). So a group's class reading is Derived,
   but it is not recomputed fresh each period: it carries its history (periods of positive balance;
   lawvere L26's carried history) and moves only when the transfer term itself moves. No threshold
   constant is involved. One bad period cannot flip a cohort's class. **[Director]** How hardening
   is represented is a new question (§13 Q4).

2. **[MIM forces] By default, a US wage-earning cohort reads as labor aristocracy, not
   proletariat.** MIM: "salary and wage-receiving people within U$ borders are labor-aristocracy or
   higher, unless they are undocumented" (contemp/internalclass3.htm §I, the Newton and Cleaver
   paragraph). Separately: "it is impossible to see any proletariat where there is an imperialist
   country minimum wage in effect." (internalclass3 §II.c). The tests are the sign of net transfer
   (wage received against value created, once imperial inflows are counted) and coverage by legal
   working rights and the wage floor. There is no wage cutoff (mim-class-structure MC-02, MC-11).

3. **[MIM forces] Nation is a first-class axis on every group, and it is separate from class.** MIM:
   "The principal contradiction inside the U$A is nation" (wim/cong/assort91.html:48). It also says
   "The vast majority of the employed Black, First Nation and Asian-descended peoples is labor
   aristocracy or higher" (internalclass3 §II.c). Nation decides alliances, policing and which
   organizations can reach a group. Class decides the group's place in production. The two must
   never be merged into one score.

4. **[MIM forces] The proletariat inside US borders is small and legally excluded.** MIM names
   "undocumented immigrant workers who are paid less than minimum wage and working prisoners"
   (mn/mn225/strike.txt), narrows it to "only class sectors dominated by undocumented work in the
   productive sectors form a proletariat" (internalclass3 §II.c), and adds that "A good portion
   enters the petty-bourgeoisie immediately upon migration through family connections and various
   legal fronts." (mim-class-structure MC-03, MC-04). The lumpen sit beside them. The engine needs
   pools outside the admitted, wage-floor-covered labor force, or this class cannot exist in the
   accounts. Whether working prisoners are proletarian or excluded lumpen is an open conflict inside
   MIM's texts (§11 item 10).

5. **A class "in itself" becomes a class "for itself" only through organization. The engine should
   detect this, never impose it.** Marx: "already a class as against capital, but not yet for
   itself" (Poverty of Philosophy ch.2 §5). The engine can count the connected pieces of each
   class's membership ties. Aid never counts as membership or consciousness (ADR270).

6. **Groups choose by rank order under their own budgets. Organizations compete through offers paid
   from their own capacity.** Time, cash and risk are the budget. Organizer-hours (ADR262) and
   currency (ADR184) fund the offers. A rule cannot impose a sigmoid or a second fixed response
   curve (AGENTS.md:41); escalation is rank order under a budget with no threshold constant (ADR184
   R3–R4). What the ranking reads is a Director question (§13 Q1).

7. **A labor aristocracy defends its share. Where that energy goes politically is not yet ruled.**
   MIM, quoting Lenin (1921), places the petty-bourgeoisie's hold on workers "who are afraid that if
   revolution breaks out they will lose the relative petty-bourgeois prosperity created by the
   privileges of imperialism", and says the labor aristocracy "fights for imperialism more
   desperately than any other class, because of a psychology of being just above water and gasping
   for breath." (mim-class-structure MC-18). When the share shrinks: "When the labor aristocracy
   feels that the imperialists aren't giving it enough of the booty from international profits, it
   complains and turns to economic nationalism." (mim-practice F16). Its politics run toward
   protectionism, nativism and, in crisis, fascism (MC-19). What holds fascism back, for MIM, is
   external: "Briefly put, what is preventing fascism is the nature of international division of the
   exploiters today." (MC-20). Cope complicates the picture: imperial powers "could use the
   superprofits obtained from their colonial, neocolonial and internal-colonial spheres of influence
   to purchase social peace" (imperialism-reproduction IR-07). The stronger claim that "A positive
   balance does not suppress political energy. It redirects it." comes only from a Python-era draft
   spec (design-corpus F12) and frozen BSL (rulings R17). It needs the consciousness ruling in §11
   item 8 before it is used.

8. **[MIM forces] Elections move allocations among bribed groups. They cannot reach imperial rent.**
   The electorate (people with legal working rights) and the in-border proletariat barely overlap
   (mim-class-structure MC-24, MC-32 item 3). The electorate must therefore exclude the undocumented
   and the incarcerated by construction (§9). The electoral path must still be real and winnable for
   local stakes such as space and budget lines, and its limits should show up in receipts.

9. **Rival lines are organizations with offers, judged by accounts, never by label.** The "settler"
   pattern is computed from what an organization's program does. It leaves land claims, the
   superwage, border restrictions and enforcement jobs intact, and the cost falls on named other
   cohorts (settler-thesis ST-18, ST-20, ST-27).

10. **[MIM forces][Director] Under MIM's line, the revolutionary opening is largely set outside the
    US.** MIM(Prisons): revolution comes "as the military becomes over-extended" (FPLmimp p.4). On
    MIM's reading it is not reachable from US cohort choices alone. How the game supplies the
    outside conditions is a reserved design call (see §11 item 1).

---

## 3. Class position: definitions and how to read them from today's accounts

### Sources say

- **Marx: identity of revenues.** Capital III ch.52 answers "what makes a class" first with "At
  first glance – the identity of revenues and sources of revenue". The sources are wages, profit and
  rent. Marx then shows this test fragments by interest, and the manuscript breaks off. Middle
  strata "obliterate lines of demarcation everywhere" (Capital III ch.52; marx-engels M1–M3). Read
  the three pure positions as limits. Mixed households are normal; NORTH_STAR: "One household can
  draw wages and ownership income, support a dependent and have someone seeking work."
- **Marx: the double freedom.** The worker is "free in the double sense": free to sell labour-power,
  and with nothing else to sell (Capital I ch.6, p.120). Whether a household *must* sell
  labour-power depends on its other means: owned assets, cash, pantry.
- **Lenin (1919).** "Classes are groups of people one of which can appropriate the labour of another
  owing to the different places they occupy in a definite system of social economy." (A Great
  Beginning, marxists.org/archive/lenin/works/1919/jun/19.htm)
- **Mao (1933): operational criteria by dominant income source.**
  - Landlord: lives by rent and does little or no labor.
  - Rich peasant: relies on exploitation for "part or even the major part of his income".
  - Middle peasant: income "wholly or mainly from his own labour".
  - Poor peasant: "has to sell part of his labour power". Mao calls this "the principal criterion"
    separating poor from middle peasant.
  - Worker: lives "wholly or mainly by selling their labour power".

  (Mao, mswv1_8.htm) Any numeric "mainly" cutoff must be classed Designed or Calibrated.
- **Mao (1926): disposition is a separate reading from class.** The petty bourgeoisie splits by
  material balance: those who earn a yearly surplus, those who break even (about half), and those
  who go into deficit. "In normal times these three sections of the petty bourgeoisie differ in
  their attitude to the revolution." (mswv1_1.htm; prolewiki PW-01, lenin-stalin-mao F05)
  - **[MIM forces]** For oppressor-nation labor-aristocratic cohorts, a deficit trend is **not**
    read as a move to the left. MIM says a shrinking share turns toward economic nationalism and
    ultra-nationalist groups (mim-practice F16; mim-class-structure MC-19, MC-20). The
    surplus/break-even/deficit reading applies only *inside* each nation-and-class cell, and MIM's
    routing governs what a deficit means in that cell. MIM places the in-border base in the
    oppressed nations, the lumpen and the undocumented (mim-class-structure MC-29; mim-practice
    F08).
- **MIM: labor aristocracy by wage versus value.** "A worker is exploited if ey earns less than the
  value of the work ey performs." The labor aristocracy earns "more than the value of their labor"
  and sits "as the lower segment of the petty-bourgeoisie" (FPLmimp p.19). Third cardinal principle:
  the imperialist-country working class "is in fact no longer an exploited class"
  (classics/cardinal.txt:48).
  - MIM's 2×2 classifies by productive vs unproductive sector × exploited vs not. In imperialist
    countries the unexploited cells hold the majority (imp97a4).
  - The class of an exploited-but-unproductive cell is relational: it can be "either labor
    aristocracy or proletarian, depending in particular on the balance of other workers in the
    country who are exerting a pull on this group." (imp97a4; mim-class-structure MC-13). This
    supports a neighbourhood-relative reading computed over county or hypergraph incidence, never
    over a community node.
  - MIM's US numbers are 1985–1999 vintage and MIM's own calculations. They are **unchecked**:
    surplus value about $998bn (1993), superprofit about 86.6% of unproductive-sector pay with a ×8
    multiplier, capitalist class about 1% of households (mim-class-structure MC-06, MC-08, MC-09).
    Use them at most as Calibrated validation targets, never as constants.
  - MIM Theory 1, which holds the income tables behind these claims, could not be read (image-only
    PDF).
- **MIM's mass reading governs over Lenin's "handful".** Lenin (1916) wrote of bribing smaller upper
  strata than England's 1848–68 aristocracy, a "handful in the top layers" (lenin-stalin-mao F13).
  MIM reads the bribed stratum as the mass of the imperialist-country working population, and
  ADR171's measured bribe mass (18,691,613 persons, 1.55× the deprivation mass) is far larger than a
  handful. Under the Director's ruling MIM's mass reading is the game's reading; Lenin's wording is
  lineage.
- **MIM: access matters, not title.** "What is important is not the literal ownership of means of
  production but access". Home equity, pensions and credit count: "net worth is means of production,
  in which home equity and pension funds have to be counted." (faq/bourgeoisie.html;
  contemp/whitemyths/index.html)
- **MIM: nation.** Oppressed nations are internal semi-colonies, and their penalty is mostly
  exclusion, not extraction. MIM(Prisons)' 2011 edit: "Exploitation of the oppressed nations is the
  exception, not the rule in the United $tates." (FPLmimp p.35) MIM also says "Classes and nations
  are groups of people not individuals or families." (internalclass3 §II.a) MIM's glossary defines
  the settler nation as a nation: "The white settler nation which has occupied North America since
  the 1600s." (FPLmimp p.19; settler-thesis ST-01)
- **ADR171 (ruled).** Nations are real, non-contiguous and people-attached. The named nations are
  Black, Chicano and Indigenous, with a disclosed overlap policy. Bribe mass is 18,691,613 persons,
  1.55× the deprivation mass. Research/06's "contiguous counties" reading is superseded on this
  point (design-corpus F10).
- **Lumpen.** MIM: those unable to sell labor-power. The First World lumpen are found within the
  oppressed nations; prisoners are "excluded from the economic system of production and
  distribution" (FPLmimp pp.19, 39). Mao: lumpen "can become a revolutionary force if given proper
  guidance" (mswv1_1). MIM Notes 225 (2000) instead counts working prisoners as proletarian (see §11
  item 10).
- **Reserve-army layers (Marx).** "it has always three forms, the floating, the latent, the
  stagnant", plus pauperism as the "hospital of the active labour-army" (Capital I ch.25 §4).
- **Rentiers and state employees.**
  - Lenin names a "stratum of rentiers, capitalists who live by 'clipping coupons'" (1916, x01.htm).
  - MIM: "the government sector is the ultimate expression of the imperialists' loyalty to the
    oppressor nation working class", because such jobs cannot be shipped overseas; and "The
    increased taxation of German workers is actually a barometer of parasitism." (imp97d1;
    mim-class-structure MC-21). County payroll and taxes are therefore class-forming levers.
  - Marx treats officials as faux frais. The marx-engels M13 correction: the "ideological class"
    sentence reports what apologists proclaimed; it is not Marx's own claim.

### Engine today

- **Cohort key.** Cohorts are keyed by `HouseholdBudgetKey` with six values: EarningNonowner,
  EarningOwner, NoEarnerNonowner, NoEarnerOwner, CollectiveResidence, PooledExternal
  (babylon-persistence/.../national_household_allocation/model.rs:13–20). The key records
  provenance, not class. ADR269: the owner split "measures neither observed wealth nor a political
  class" (ADR269:24).
- **Owner exposure** is a flat captured fraction: `private_owner_households_bps = 1000`
  (content/scenarios/national/defines.toml:20).
- **Three income flows already exist per principal:**
  - wages via `EmploymentTerms.payee` (material-circuit/payments/attendance.rs:36–42);
  - ownership distributions to owner-exposure budgets (opening/financial.rs:279);
  - `PublicTransferTreatment::HouseholdIncomeSupport` (financial/model.rs).
- **Staffing members.** These are household-bound partitions with employed and reserve counts in
  SOCIAL_CLASS nodes (structure.bscn:12–13). The binding says "Political class is not inferred."
  (staffing/members.rs:22)
- **WorkerClass.** The ACS WorkerClass (eight employer-type classes) drives resident allocation
  only, and collapses to Employee / WorkingOwner / UnpaidFamily. It is not on cohorts. The claim
  that it is also absent from the graph was not verified (engine E05).
- **Missing data.** There is no wage-versus-value measure, no productive/unproductive sector tag, no
  legal-status or wage-floor coverage count, no nation incidence on cohorts, and no credit or
  net-worth account. The ported `imperial-rent.bsl` says "Wages, subsidy and decision are not
  implemented here." `class-dynamics.bsl` is header-only (engine E13).

### Table: from stratum to available accounts

| Class or stratum | Operational criterion (source) | Accounts available now (engine) | Evidence class | What is missing |
|---|---|---|---|---|
| Bourgeoisie | Lives by others' labor or ownership returns; about 1% of households (Lenin 1919; mim-class-structure MC-06, unchecked) | Owner-exposure budgets; company distributions (financial.rs:279; defines.toml:20) | Designed (flat 10%) | Ownership finer than a flat fraction; company-to-owner mapping (engine E04) |
| Rentier fraction | Coupon, dividend or interest income (Lenin 1916; ADR208 sub-fraction) | Same distributions, not split by kind | Designed | Income-kind split |
| Petty bourgeoisie (own-account) | Own labor plus own means; access to capital (Mao 1933; MIM bourgeoisie.html) | WorkingOwner attendance mode (allocation.rs:59–65) | Observed seed (ACS) | Credit and net-worth account; carrying the attendance mode onto cohorts |
| Labor aristocracy [MIM forces] | Wage above value created once inflows are counted; sign test, no cutoff; covered by legal working rights and the wage floor (FPLmimp p.19; mim-class-structure MC-01, MC-02, MC-11) | Wage receipts per payee (attendance.rs); staffing pools | Derived, once a value term exists; display default "labor aristocracy (MIM default; value term pending)" | Signed wage-versus-value balance with a Calibrated imperial-transfer term; productive/unproductive tag per workplace and occupation (MC-12); coverage counts |
| In-border proletariat [MIM forces] | Undocumented work **in productive sectors** below the wage floor, without kin capital or a legal front; working prisoners per MN225 (contested, §11 item 10) (internalclass3 §II.c; mim-class-structure MC-03, MC-04) | None | — | Off-the-books pool; prison pool; legal-status split inside the labor force; productive-sector test; kin-capital/legal-front test (MC-03, MC-04, MC-25) |
| Semi-proletariat / stagnant | Must sell part of labor-power; irregular hours, low pay (Mao 1933; Capital I ch.25) | Hours receipts; reserve counts | Derived | Duration and hours history per member |
| Reserve: floating | Recently separated, searching (Capital I ch.25) | `reserve` integer (staffing/model.rs) | Derived | Sub-state split (§8) |
| Reserve: latent | Outside the market but available (Capital I ch.25 §4) | None; labor force only shrinks (labor-supply E3) | — | Entry and return flows |
| Lumpen / pauper | Cannot sell labor-power; excluded; found within the oppressed nations (FPLmimp p.19, 39) | Only the Wayne claimant subset (policy/game.rs:319). No account marks the excluded state yet. NoEarner budgets are provenance and include retirees and dependents. | Designed subset | An "excluded" state distinct from reserve [Director] |
| State and unproductive employees | Revenue from taxes or surplus; MIM: an aristocratic anchor (imp97d1; mim-class-structure MC-21; Marx TSV) | County public budgets; WorkerClass government categories | Observed seed | Workplace sector tag carried to cohorts; which cohorts each appropriation pays |
| Oppressed-nation incidence [MIM forces] | People-attached, declared, with overlap disclosed (ADR171) | ADR171 artifact, not wired (ADR171 Phase 2 blocker) | Observed / Designed per ADR171 | A producer for cohort nation shares; an oppressor-nation counterpart (§11 item 3) |

**Proposal: the class profile has three parts, and the MIM reading comes from two of them.**

1. **Livelihood profile (answers Marx's and Mao's question).** A Derived extensive profile per
   cohort: persons, hours and income by relation to the means of livelihood (hours sold, own-account
   hours, unpaid household hours, property returns, transfers). Additive pushforward preserves sums
   at every rung, so the profile meets Article II's invariance duty (ADR296:34–35; Lawvere 1992 on
   extensive and intensive quantity). Any discrete label, such as "dominant source", is a lossy
   sorting at one scale and must never be claimed scale-invariant. Lawvere L16 works the example:
   cohorts at 60% and 45% wage income get different labels, yet merge to 48.75%.
2. **(a) Signed wage-versus-value balance — required.** An extensive currency quantity per cohort
   per period: wages and benefits received minus value created by the cohort's own labor, with
   imperial inflows counted. Because it is extensive, it sums under aggregation. Its
   imperial-transfer component is tagged **Calibrated** (MIM's imports × 8–10 multiplier, 1990s
   data, unchecked; mim-class-structure MC-09, MC-32 item 4) unless the Director rules it Designed
   (§13 Q2).
3. **(b) Legal-status and wage-floor coverage counts — required.** Persons and hours in each cohort
   covered by legal working rights and the wage floor, versus undocumented, sub-floor and
   incarcerated (mim-class-structure MC-02, MC-03), plus the productive-sector and
   kin-capital/legal-front tests of §8.

The **MIM reading of a cohort comes from (a) and (b)**, never from the income-source mix alone.
Under the mix alone a pure-wage US cohort would read "wage", that is, worker, which MIM's line rules
out. **Until (a) exists, every portrait and roster entry for a covered wage-earning cohort shows
"labor aristocracy (MIM default; value term pending)", never "worker".**

---

## 4. When a class acts

### Sources say

- **Combination (Marx).** "This mass is thus already a class as against capital, but not yet for
  itself." In struggle the mass "constitutes itself as a class for itself". Combination's "double
  aim" is first "stopping competition among the workers" (Poverty of Philosophy ch.2 §5,
  marxists.org).
- **Representation (Marx).** Dispersed holders form a class "much as potatoes in a sack form a sack
  of potatoes". When their shared interest forms "no community, no national bond, and no political
  organization" they cannot act: "They cannot represent themselves, they must be represented." (18th
  Brumaire ch.7)
- **Spontaneity (Lenin).** "the working class, exclusively by its own effort, is able to develop
  only trade union consciousness" (WITBD ch.II). Research/05 reads two ceilings: a sphere ceiling
  that exposure can lift, and a rent ceiling no line can lift.
- **The mass line (Mao and MIM).**
  - Mao: "The masses in any given place are generally composed of three parts, the relatively
    active, the intermediate and the relatively backward." Leadership is "all correct leadership is
    necessarily 'from the masses, to the masses'." (mswv3_13)
  - MIM(Prisons): "It is by collecting the ideas of the masses and synthesizing them through
    practice that the vanguard finds the correct path" (FPLmimp p.17).
  - MIM adds that who counts as the masses is defined by appropriation of surplus labor: "Belonging
    to the 'masses' or the 'proletariat' is not a question of" self-identification
    (wim/cong/onmasses01.html:292).
  - The three-part split also appears in FRSO and CPP texts. Here it is sourced only from Mao.
- **Staged participation (Hunan).** "It was not until the second period, when the peasant
  associations were already exercising great power, that the middle peasants came in." Poor peasants
  were the main force throughout. Enrollment was by household: "a membership of two million means a
  mass following of about ten million" (mswv1_2).
  - **[MIM forces]** Translated to the US under MIM's line, this is an ordering **among cohorts
    outside the bribe** — undocumented productive-sector workers, the lumpen, oppressed-nation
    excluded and sub-floor cohorts — not "poorest first" across all US cohorts. A low-income covered
    oppressor-nation cohort is not Hunan's poor peasant.
- **Attitudes shift with the tide (Mao 1926).** In normal times strata differ. When the tide runs
  high, the middle "may join" and right-wingers "will have to go along" (mswv1_1).
- **Lawvere.**
  - A level zero ("in itself") is discrete. Unity is measured by components realized along
    one-dimensional ties: "if a point (or figure) can become another one, then it can do so along
    some 1-dimensional process of 'becoming'" (1992 Categories of Space and Quantity p.29).
  - The codiscrete pole, where everyone is tied to everyone, is structureless chaos (1994 p.9).
  - Collective thinking happens in institutions; individuals "think, but so do clans, 'schools of
    thought,' professions, social classes," (1994 Tools p.44).
  - The body-politic sketch has parts, sub-wholes linked by membership, passive aggregation and
    active influence with delay: "In the thinking of the body politic, democracy begins with the
    people U whom individual P knows." (1994 Tools p.54)
  - Lawvere offers method only. He has no formal model of social class (lawvere L02).
- **Direction is not given by connection.** A labor-aristocratic bloc can be fully "for itself"
  along chauvinist lines (lawvere L27; mim-class-structure MC-19). MIM(Prisons): "petty bourgeois
  class consciousness is overwhelmingly dominant among white people of all classes." (FPLmimp p.49)

### Engine today

- No consciousness, grievance or allegiance state exists in the national graph (engine E22).
- `consciousness.bsl` keeps a ternary (r, l, f). Its routing rule reads: "solidarity routes
  agitation revolutionary-ward, its absence fascist-ward; chauvinist pressure (the positive-balance
  imperial bribe, Director flag 2's ruling) biases the split fascist-ward". It runs only in
  conformance content, which no national preset loads (rulings R17, engine E12).
- ADR171's Phase 3 consciousness wiring was withdrawn as engineering, and ADR208 narrowed ADR171's
  scope (rulings R15).

### Proposal: what to detect and what never to impose

- **Detect:**
  - connected pieces of each class position's membership incidences, per declared scale. Union-find
    over member lists works without pairwise expansion (lawvere L09).
  - ties *across* the declared national divides, reported separately (lawvere L27).
  - surplus, break-even and deficit trend per cohort **within each nation-and-class cell** (Mao
    1926), read through MIM's routing: for oppressor-nation labor-aristocratic cohorts a deficit
    trend is a share-defense signal, not a leftward one (§3).
  - first open acts, such as a strike held or a delegate sent, recorded as history
    (collective-action CA-06; lawvere L26).
- **Never impose:**
  - a consciousness scalar raised by aid (ADR270; mim-docs p.7, charity is subordinate — inference:
    service use ≠ agreement, mim-practice F07);
  - a fixed one-third active/intermediate/backward split;
  - a stage triggered by a threshold constant (mim-practice F02; design-corpus F27);
  - a "class consciousness bar" that scores an organized settler bloc as progress.

**[Director]** BSL cannot compute connected components: it has no recursion. The recognizer would
need a host recognizer, a new intrinsic beyond the capped nine, or a new adjunction kind. All three
are new-primitive questions (lawvere L09, L30).

---

## 5. The bounded choices of option 2

**Engine anchors.**
- Choice rules can run in the Action partition, anchored `:after ooda` beside organizer-practice.
  They read closed-period receipts and write rows consumed in period N+1, as ADR299 does when it
  "consumes the settlement in the following period" (phase_order.rs:127–131; ADR299:26–27; engine
  E23).
- `PracticeIntent` is organization-authority-bound and has no join, leave, migrate or vote verbs, so
  do not reuse it (intent.rs:214–216; engine E15).

**Three kinds of choice (Proposal, from lawvere L21).**
1. **Distributive.** Each member's own decision: seek work or stop, enter, move, attend, join,
   leave. The cohort's counts are pushed through a finite map with apportionment and carried
   remainders. Precedents: lifecycle `fraction(...carry)` (household_lifecycle/advance.rs:49) and
   `proportional_shares` with largest-remainder and index tie-break (staffing/members.rs:180, 203) —
   signatures and tie-break checked; bodies not read (lawvere L20). No RNG is used. Joint outcomes
   are authored as ordered conditionals (labor status first, then migration given status), never as
   products of marginals (lawvere L18).
2. **Collective.** A body decides: back or withhold a delegate, grant a mandate, later vote. These
   are counted procedures over member households, with authorization counts recorded (ADR299:16–17;
   lawvere L29).
3. **Contingent.** A raid, an incident, whether a strike holds. These use an ADR248 kernel with one
   governed draw and a receipt.

**Weights.** Weights come from ratios of extensive quantities in accounts. They pass the BSL test
"can this be re-derived as a measure instead?" (bsl-language.rst §3.10). They are never a response
curve (AGENTS.md:41). **What the ranking reads is the Director's call (§13 Q1).** Proposed: the
material effect of each offer on the group's own accounts, including its share of the transfer for
bribed cohorts (the share-defense of mim-class-structure MC-18), with no consciousness term until
§11 item 8 is ruled. Rulings R23 flags this choice — expected material gain versus a consciousness
gap — as theory-line.

**[Director]** Must distributive choices also produce ADR248 choice receipts, or may they be
deterministic mechanics?

### The choice menu

| Choice | Accounts read | Who competes | Rule form | Receipt |
|---|---|---|---|---|
| Keep seeking / stop / enter labor force | Cash and pantry runway, unmet needs, hours, reserve duration (household_time.rs; Capital I ch.6); legal status and coverage | Employers (wages, hours), state (support terms), organizations (relief) | Distributive split of reserve sub-states (§8) | "412 households stopped looking; 60 re-entered" (game-prior-art P-2) |
| Hours / second job | Attended vs contribution-available hours (household_time.rs:83–86) | Employers | Distributive, inside the hours partition | Hours receipt |
| Move county | Offered wages and support by county; kin ties; nation incidence; legal status; repression exposure (deportation, arrest risk) | Employers, county budgets | Deterministic allocation or a Director-approved joint kernel: a cross-node write that V1 cannot enumerate (ADR248 decision 3) | Person transfer between fixed counties |
| Contact / attend / join / leave | Contribution-available hours; delivery of past offers; nation incidence; legal status; repression exposure | Player organization, rivals, unions, churches, the state (Althusser's ISAs). Reach rules by nation: an oppressed-nation cohort may prefer an organization led by its own nation, and MIM says it "would defer to such a party on the question of organizing the oppressed nationality in question" (mim-practice F29). Immigrant, migrant and prisoner unions are MIM's named exceptions to its critique of US union struggle (mim-practice F17). | Rank order of reachable offers plus "decline" under the time budget (lawvere L23) | Attributed-membership incidence (§7) |
| Use a service | Unmet need | Any organization running an institution | Distributive | Service receipt, never a membership (ADR270) |
| Back / withhold a delegate; mandate | Settlement offers against claim accounts | Assembly delegates, county | Collective count (ADR299 pattern) | Authorizing households, refusals, mandate terms |
| Vote (later) | Office decision set against cohort accounts; delivery gap; nation incidence; legal status (eligibility) | Parties and slates | Collective count with explicit abstention (§9) | Counted ballots per cohort |

### How organizations compete

**Sources say:**
- **Hegemony (Gramsci).** Consent "is 'historically' caused by the prestige (and consequent
  confidence) which the dominant group enjoys because of its position and function in the world of
  production" (Prison Notebooks p.12). Coercion stays in reserve.
- **Ideological apparatuses (Althusser).** "while there is one (Repressive) State Apparatus, there
  is a plurality of Ideological State Apparatuses": school, church, union, family, media. Class
  struggle in them is "possible, serious" (pp.243, 153).
- **Non-participation is the default (Reich).** Most of the exploited do not strike. "The economic
  situation is not directly and immediately converted into political consciousness." (Mass
  Psychology p.23)
- **MIM's principal task.** "The principal task is to 'create public opinion and the independent
  institutions of the oppressed to seize power.' That means discrediting the state as it exists."
  (faq/mnstyle.html:74) Charity is subordinate: "believes that as a strategy charity can never
  provide more than temporary and limited relief." (mim-docs.pdf p.7)
- **MIM's funnel and time budget.** Contact → RAIL member → MIM cadre, with the army as a support
  tier. "All people we meet will be RAIL recruits before they are MIM recruits"; RAIL members are
  "under limited obligations of discipline and they focus their work on building public opinion";
  party members are the cadre. "All MCs must have 10 hours per week of contact with the masses."
  (wim/dc/primerabridged.txt:912, 945, 1203; mim-practice F04, F05). This fits the Supporter Labor
  versus Cadre Labor split in the approved peacetime-verbs design (design-corpus F05).
- **Exit, covert action and control.**
  - Scott: low-risk covert action (foot-dragging, exit) dominates. Its form follows the labor regime
    and expected retaliation (collective-action CA-01–03).
  - Kalyvas: collaboration follows control "irrespective of their true or initial preferences"
    (collective-action CA-11).
  - Wood: most residents free-ride, and agency and defiance matter (collective-action CA-07–09;
    derived thresholds come out of her Appendix model).

**Failure modes, sourced from MIM and its lineage:**
- **Economism.** "Rightist economists cheerlead for wage struggles as tantamount to revolution."
  (MIM, MIM.essays/critique.of.rcp:69–70) and "waiting for economic conditions to dish up
  revolutionaries on the silver platter" (mim-docs p.5). Gramsci: the movement never develops
  "beyond the economic-corporate stage" (p.255).
- **Tailism / right opportunism.** "This 'right opportunism' is the main danger in the
  party-building process in the world." (critique.of.rcp:76–77) A large First World following
  signals "bourgeois ideals" (FPLmimp p.59).
- **Commandism.** "The masses are asses line results in commandism and attacks on the masses."
  (critique.of.rcp:141–143). MIM(Prisons) later confirms that errors are judged by conditions
  (FPLmimp p.59, below).
- **Adventurism / focoism.** MIM's program: "armed struggle in the imperialist countries is a
  serious strategic mistake until the bourgeoisie becomes really helpless." (wim/program.html:44;
  mim F13). MIM's editorial note in MIM Notes 195: a focoist has "some significant disagreements
  with Marxism-Leninism-Maoism". The backlash argument there is the prisoner author Lord Grim's, not
  MIM's.
- **Sectarianism.** "an organization puts its own needs above those of the international
  proletariat" (faq/sectarian.html:46).
- **Liquidationism.** "We say their practice is liquidationist because they turned all their energy
  to building mass organizations focused on largely petty" bourgeois projects (FPLmimp p.34).
  Gramsci's decapitation: "the popular masses were decapitated, not absorbed" (p.98).
- **Errors are relative to conditions.** "what is left and what is right changes as conditions
  change." (FPLmimp p.59)

**Proposal.** Compute each failure mode from the organization's practice and allocation record,
never store it as a label (NORTH_STAR:26–27). Each is a ratio or a rank among organizations, never a
cutoff:
- **Advanced, intermediate and backward counts** come from recorded participation history, not a
  readiness scalar: advanced = reached persons with tenure and held mandates; intermediate = reached
  persons who have attended at least once; backward = reached persons who have never attended. Mao
  supplies the three parts (mswv3_13); the split is emergent, never one-third each.
- **commandism** = ratio of what an organization asks (hours, risk) to the best recorded
  participation of the intermediate count it reaches; shown as a rank across organizations;
- **tailism** = share of asks pegged at or below the recorded participation of the backward count,
  with exits of the advanced count shown beside it;
- **economism** = share of offer value in wage and relief terms against institution and
  public-opinion work;
- **sectarianism** = share of cadre-hours spent on own growth against coalition work;
- **liquidationism** = share of cadre-hours that moves, period over period, from cadre and
  institution work into mass-organization projects;
- **adventurism** = repression receipts incurred per armed or illegal action, set against the
  institution stock it puts at risk.

(The readiness-gap framing of commandism and tailism also appears in FRSO and CPP mass-line texts —
organizing-practice OP-13, OP-15. It is not used as the source.)

**[MIM forces]** Wage gains for a labor-aristocratic cohort should not raise that cohort's uptake of
revolutionary organizations' offers, and may raise its uptake of protectionist ones. MIM: "Fighting
union struggles in the united $tates --with the exception of immigrant, migrant and prisoner
unions-- only leads to a further crackdown" (faq/exploitedwhites.html). An organization takes its
class from its members (mim-class-structure MC-23).

---

## 6. Rival lines inside the game

**None of this is the game's method.** These are organizations that compete for the same groups. The
engine judges each one, the player's included, by material accounts. Nothing scripts a rival to
fail.

**Relation to ADR208 (accepted).** ADR208 rules a five-member parameterized faction list —
RESTORATIONIST, SOCIAL_DEMOCRATIC, DECOLONIAL, LIBERAL_IMPERIAL, FASCIST_VEHICLE — with fascism as
"parameter values on shared faction machinery", and charters a Sakai/MIM fascist-base dossier
(rulings R18). **Proposal:** rival organizations below are instances on that shared faction
machinery, carrying the dossier fields (class reading, target cohorts, offers, nation stance,
election strategy). **[Director]** How the archetypes map onto the five factions (for example
CPUSA-type and DSA-type onto SOCIAL_DEMOCRATIC, patsoc onto FASCIST_VEHICLE) needs a ruling. Rulings
R18 notes the generalization "rides a post-port D-record" under ADR183, which limits timing.

**Relation to the project's own rival taxonomy (research/21).** The Opportunist Zoo briefing of 25
Oct 2026 already types the player's rivals as five cells: `MORALIST_ADVENTURIST`,
`STRASSERITE_GRIFTER`, `DOCTRINAL_SECT`, `PROTEST_CIRCUIT_TROTSKYIST` and `SPECTACLE_INFLUENCER`.
Its `DOCTRINAL_SECT` has an ultra-left strain and a right-opportunist strain, described as
"First-Worldist 'Maoism': the MCU type that keeps the mantle and drops Third-Worldism". Its
guardrail reads "MIM(P) / MLM-TW", and it says the named contemporary organizations are
illustrations of a type: "no factual claim about a named contemporary organization is load-bearing".
The Director's ruling on MCU and FRSO therefore matches the project's existing notes. The table
below adds the remaining lines from MIM's own criticism. None of the five cells, and none of
ADR208's factions, exists in the Rust engine yet; organization kinds there are STATE_APPARATUS,
BUSINESS, POLITICAL_FACTION and CIVIL_SOCIETY.

**What a settler communist organization is, on MIM's line.** MIM's own test: "does the movement
fundamentally oppose Amerika and all that it stands for? Or does it merely pose left in its quest --
deliberate or accidental -- for a unified oppressor nation?" (MIM.essays/500.years.white.unity). MIM
names the shared error of social democrats, Trotskyists and the CPUSA as the "mythology of the white
proletariat" (mim.worker.world.review §III). Unity on the labor aristocracy's terms is refused: "the
kind of unity the critics were advocating is the kind where the proletarians unite with the labor
aristocracy on the latter's terms. No thanks!" (mn/mn129.txt).

**Detection, in accounts and relations rather than a label (Proposal, settler-thesis ST-20,
ST-27).** For each demand an organization advances, compute:
- (a) the change in each cohort's signed wage-versus-value balance and income;
- (b) the cost to named oppressed-nation, periphery or lumpen cohorts, through four channels:
  - land claims (an overlay);
  - superwage;
  - restrictions on a named group's labor supply;
  - enforcement budget, where MIM says "the rest of the oppressor nation is willing to go along with
    the job security plans of the police and correctional officers as a means of protecting their
    collective privilege." (FPLmimp p.38);
- (c) who holds the leading positions.

The settler pattern shows when gains concentrate in labor-aristocratic cohorts and the costs fall on
others. **Computable from today's accounts:** only the enforcement channel. The Wayne City PD holds
an agency appropriation paid from the county budget under the same period cap that funds household
income support and provider grants, and "Lower captured priority numbers are funded first"
(national_economy/city_pd.rs; material-circuit/financial/model.rs:77). The superwage channel waits
on the value term, the labor-supply channel on the legal-status split, and the land channel on a
claims overlay. The same test applies to oppressed-nation organizations with "bigger piece of the
pie" programs (FPLmimp p.34; research/06 flip rules 3 and 8).

**Rivals.** Every line below is described from MIM's texts or from the rival's own documents. The
criticism column is MIM's view. The last column is an expected trajectory with its source; every
entry is a hypothesis the engine tests, not a script.

| Rival (archetype) | Its line and offer | Whom it attracts, and the material reason | MIM's criticism | Expected trajectory (source) |
|---|---|---|---|---|
| CPUSA-type | Public-works jobs, New Deal reforms, anti-NAFTA protectionism (mim.cpusa.75th.review) | Union and public-sector cohorts defending job security | "the CPUSA's real basis is labor aristocracy job security for Amerikans" | "Currently tails Democrats" (wim/wyl/socialdem.html); absorption |
| DSA / social democrats | Electoral reform inside the Democratic Party | Cohorts seeking welfare, housing and jobs relief | "Pro-imperialist. The furthest right of all groups in this list." | Electoral wins change little ("a. Nothing. Witness Mitterand in France.") or draw repression when they touch property (faq/demsoc.html; a Third World record, not a US rule) |
| Workers World / wage-demand left | $10 minimum wage | Low-wage and unemployed oppressor-nation cohorts (reader interpretation) | Stokes chauvinism; MIM "does not support a $10 an hour minimum wage" (mim.worker.world.review §I) | Movements that raise parasitism, "whether from the 'left' or the 'right' are feeding the flames of fascism" (thesesonfascism02 thesis 1) |
| Trotskyist (SL, SWP, ISO) | Pure class line, multiracial working class, no national liberation for the Black nation (wyl/trot.html) | Students, young professionals, some union activists | "Without exception, Trotskyism is idealism."; base "where the petty-bourgeoisie pines for a 'perfect' socialism or none at all" | Splits, little material gain; neglect of oppressed-nation cohorts (mim-on-other-lines F11, F12) |
| RCP-type (RU lineage) | Poorest and youth as base; heroic-leader branding. Avakian: "there are objectively white proletarians, quite a few of them." | Poor and young cohorts | "MIM sees hard-boiled racism and national chauvinism"; "left economism"; commandism (critique.of.rcp) | Hypothesis to test: whether its asks rank high on the commandism ratio (§5) and whether reached cohorts that are not already committed leave (from MIM's commandism critique). MIM's later CIA-front assertion is not used. |
| PLP-type | "PL's line is that all nationalism is reactionary." | Workers hostile to nationalism | Ignores superprofit; repels oppressed-nation cohorts | Misreads cohort responses to wage offers (mim-on-other-lines F18) |
| Focoist (Weatherman pattern) | Armed example | Young student cohorts | "If the focoists survive the battles, they burn out and sell out." | Membership spike, then loss (mim-on-other-lines F19) |
| FRSO (settler communist per Director ruling) | United front against monopoly capital; labor demands; self-determination for named nations; immigrant legal status (frso.org program pages) | Immigrant and oppressed-nation cohorts (plainest material reason: legal status and ICE); petty-bourgeois allies — reader interpretation | "they and their FRSO descendants are for feel-good subjectivist politics" (wim/cong/subreform.html); unity on the aristocracy's terms (MN129) | Wide, fragile front — reader interpretation, not MIM (low confidence) |
| MCU (settler communist per Director ruling) | "We concentrate our organizing efforts and propaganda on the advanced workers in the labor union movement, especially the industrial proletariat."; labor aristocracy "only a small subsection of the working class"; boring-from-within; critical endorsements; labor-party aim | In practice, student and activist cohorts entering union jobs (its own self-criticism); union militants | MIM does not discuss MCU. MIM's general line applies: no strategic unity with the imperialist-country working classes (program.html point 7) | Small, study-heavy, strong only in union cohorts — reader interpretation, not MIM (low confidence) |
| Patsoc / Strasserite grifter | "respectability inside the settler nation" (research/21) | Labor aristocracy and small business | Class unity "that never names a class relation" | Fascist-vehicle pull in crisis (research/21; ADR208 FASCIST_VEHICLE) |
| Labor-aristocratic unions | Defense of "privileged" jobs; prison-guard jobs; anti-immigrant ballots (MN225; mt11labor) | Covered workers, guards, homeowners | Union leaders are "the most dangerous" enemy section (FPLmimp p.30) | Protectionism → nativism; "In another situation with a different class structure, the same strategy and tactics unleash fascism." (imp97c6) |

**Caveats.**
- Several MIM claims about rivals are polemic: SL as FBI, RCP as CIA, Gus Hall's wording. Use them
  as dossier voice at most, never as engine fact.
- Pre-1987 MIM critiques predate MIM's class line (mimhist.html, mim-on-other-lines F15).
- **[Director]** Whether rivals carry real organization names or generic archetypes is a naming and
  impersonation question.

---

## 7. Membership as hyperedges

**Engine today.**
- Amendment AG / ADR189 already ratifies attributed membership. The (member, hyperedge) pair is a
  first-class typed element, and a member list "crosses WHOLE, never C(n,2)" (ADR189:42–43;
  CONSTITUTION:159).
- The store's slot is `struct MembershipPayload;`, "Carried, empty, unhashed — nothing in this train
  writes it." (babylon-graph/src/hypergraph_store.rs:64). Upstream hypergraph-rs exposes no
  accessors (hypergraph-rs#2).
- ADR262 says organizer operations write no membership (ADR262:43). `organization.bsl` defers
  membership to "future committed-intent and attributed-membership boundaries" (lines 6–9).
- Organizations are ORGANIZATION nodes plus ORGANIZATION_BODY hyperedges. Contributors bind to
  households through `OrganizerHouseholdBinding`, "Captured identity only"
  (organizer/types.rs:64–71).
- ADR299 forms the claimants' assembly "from consenting households", and warns that a shared income
  source is no evidence of shared organization.

**Sources say.**
- The organization spec (Director-approved 2026-08-11) has three strata: social base (weight below
  1), mass membership and cadre. Hollowing-out is derived, "never a stored flag" (§4, lines
  113–119).
- Its per-member payload needs a "Director ADR per the standing hash-widening ruling" (line 226).
- MIM's funnel (§5) and Hunan's one-name-per-family enrollment support household-cohort membership
  counts.

**Proposal.**
- Membership is a weighted span: cohort ← incidence → organization (lawvere L22).
- Payload fields are extensive and bounded by the cohort's persons and shared household time
  (ADR270:52–53): member persons, hours attended, tenure, mandate record, entry step (contact /
  RAIL-type mass member / cadre). These fields are also the participation history from which §5's
  advanced, intermediate and backward counts are derived.
- **Overlaps.** One cohort can belong to several organizations, so "how many are organized by
  anyone" is not canonical. Report bounds, max(x, y) ≤ union ≤ min(x + y, N), or use a declared
  overlap policy like ADR171's.
- **Change per period.** Each period's change falls into one of Lawvere's five arrow kinds relative
  to an organization: inside, outside, entering, leaving, excursion (lapsed attendance). This gives
  a finite vocabulary in place of a loyalty scale (lawvere L24).
- **Consent.** Only the cohort's own recorded choice writes an incidence. Aid, provisioning or
  shared income never write one.
- **Community stays out of the graph.**
  - INV-010, "community is NEVER a graph node", is recorded in ADR084. Amendment U is **ADR091**:
    county is the atom, and CZ/MSA/state are parallel county aggregations.
  - Groups live as county-keyed cohort accounts plus membership hyperedges. A per-place
    political-capacity pool (research/11) attaches to a county overlay, never to a community node.
  - Allocate/aggregate is additive pushforward per ADR296, "not ... an invented aggregation
    adjunction" (ADR296:35–36; lawvere L17). See §11 item 15.

---

## 8. Labor supply

**Engine today.**
- **Demand-driven staffing.** `retained = max(current_request, previous_unretained_hours)`, `target
  = requested_people.min(labor_force)`. Hires move reserve to employed and separations move employed
  to reserve; a period never has both (staffing/transition.rs:66–75; members.rs:164–168).
- **The labor force can only shrink**: "A demographic change cannot add to a captured labor force."
  (members.rs:58–61) "Exact completed account; V1 has no mortality, migration or inactivity flows."
  (staffing/model.rs:306)
- **Lifecycle (ADR298).** Births, aging and deaths run once per period over four age bands, with
  carried fractions. "positive age transitions do not add membership or employment."
  (household_lifecycle/workforce.rs:30–32)
  - "Eligible" includes ages 16–17 and 65+, so there is no retirement state.
  - Vital rates are Designed per-band constants. That they have no class or shortage response is
    inferred from constant rate arrays in model.rs, not stated in ADR298 (engine E17, labor-supply
    R1).
- **The open gap, in the project's own words:** "New labor-force entrants, old-age entitlements and
  a response of mortality to shortages need explicit policy."
  (reports/economic-flows-qualification-2026-11-14.md:286)
- **Household time.** The hours partition is exact: endowment = attended + protected + unpaid +
  contribution-available. Unemployment does not turn unmet provisioning into leisure
  (household_time.rs:47, 83–86; ADR270).
- **Not verified here:** the Linear texts of PER-32 and PER-337. ADR255, ADR267, ADR269 and ADR270
  record the same constraints.

**Sources say.**
- **Reserve army (Marx).** Wages are regulated by the active/reserve proportion, and overwork of the
  employed swells the reserve. Organizing "a regular co-operation between employed and unemployed"
  attacks that mechanism (Capital I ch.25 §3).
- **Superexploitation (Osorio, afterword to Marini).** It "throws children and adolescents
  prematurely into the job market, and forces workers to accept prolonged working days"
  (pp.179–180). Osorio scopes this in the centre to "certain sectors of workers, particularly
  documented or undocumented migrants" (imperialism-reproduction IR-11). The project's draft
  consciousness-recoupling spec records the ratified line of no superexploitation inside US borders
  (design-corpus F12).
- **[MIM forces] Segmented supply.** Borders are closed "through alliance with the labor
  aristocracy. The free market for labor-power in the imperialist country is eliminated." (imp97a5)
  MIM places the reserve army mostly abroad and the First World lumpen as excluded (mim F11).

**Proposal: a labor-status ledger inside existing member stocks (labor-supply P1).** One authority:
the sub-states sit inside the graph-owned stocks, not beside them. Reserve splits into counted
states whose sum equals today's `reserve`:
- floating (recently separated);
- stagnant (low hours, long duration);
- latent (available but out of the market);
- pauper / excluded.

Every move between states is a paired transfer.

**Conservation laws (labor-supply P4):**
- (a) persons change only through lifecycle births, deaths and migration transfers;
- (b) employed + all reserve states = labor force ≤ eligible ≤ persons (ADR270:34–36);
- (c) the hours partition holds;
- (d) jobs are requests for hours and never persons, so employment ≤ labor force;
- (e) entrants arrive only as reserve, never as employed (ADR298: "A change in eligibility creates
  no paid position.").

**[MIM forces] Legal status and coverage inside the labor force.** Split each labor force into
covered (legal working rights, under the wage floor) and uncovered (undocumented, sub-floor), plus a
prison pool. Within the uncovered pool apply two further tests before reading a cohort as
proletarian:
- a **productive-sector test**: "only class sectors dominated by undocumented work in the productive
  sectors form a proletariat" (internalclass3 §II.c; mim-class-structure MC-03);
- a **kin-capital or legal-front test**: "A good portion enters the petty-bourgeoisie immediately
  upon migration through family connections and various legal fronts." (MC-04).

**Prison labor and the identity.** To keep law (b) and (d) true, prison labor must be one of two
declared states (§11 item 10): **(i) excluded with in-kind work** — incarcerated persons sit outside
the labor force, and their prison work is recorded as hours outside the employed count (this follows
the later MIM(Prisons) reading, FPLmimp p.39); or **(ii) employed in a separate prison labor force**
with its own employed + reserve identity and sub-floor pay (the MIM Notes 225 reading). Proposal:
(i) by default, pending the Director.

**Closing PER-293 and PER-32:**
- **Entry at 16 and 18.**
  - For the **undocumented and migrant pool only**, Osorio's mechanism applies: entry pressure rises
    when reproduction coverage falls (imperialism-reproduction IR-11).
  - For **covered, labor-aristocratic cohorts**, a separate entry rule labelled **Designed**: an
    entitlement or household-runway rule that moves 16–17 and 18+ persons into reserve.
- **Old age at 65.** An explicit entitlement rule moves 65+ out of eligible labor force. Whether it
  is a choice or an institution is a Designed choice.
- **Mortality under shortage (labor-supply P6).** Unmet-need mass shifts the cohort's death carry,
  tagged Designed and shown on the receipt. This changes ruled ADR298 → **[Director]**.
- **Migration.** A conserved person flow between fixed counties needs a destination principal
  identity (engine E18), plus a joint kernel or deterministic allocation. Build it last.
- **Wage pressure from the reserve ratio is secondary under MIM's line.** US wages are set mainly by
  closed borders and imperial transfer; the reserve army sits mostly abroad (imp97a5; mim F11). The
  domestic reserve ratio still presses hours and local hiring. It must not port the Python
  ReserveArmy sigmoid (ADR188 Row 7 bans it). `vitality-attrition.bsl`'s threshold-free hold-out
  measure is a candidate (labor-supply T1, E8).
- **Hours constant.** MIM uses 2,000 hours a year; the project uses 2,080. Convert when reusing MIM
  figures.

**Holism test (labor-supply P5).** Sever each link and name what changes:
- no cash read → nobody stops seeking;
- no unmet-needs read → unemployment becomes leisure;
- no entry rule → the labor force depletes over twenty years;
- no wage-versus-value read → the bribe disappears and employment becomes politically neutral;
- no legal-status split → the in-border proletariat cannot exist and the electorate overcounts.

---

## 9. Toward elections

**What NORTH_STAR requires.** Three tables before any endorsement: who can vote, what office is at
stake, what its holder can decide (NORTH_STAR:82–83).

**Engine today.**
- **Phase slots** `allegiance` (22), `electoral` (23) and `policy` (24) are reserved in the
  Consequence partition, with nothing behind them. This rests on a grep, not a full trace
  (phase_order.rs:163–176).
- **County fiscal levers exist and are set from scenario constants, not by any office:**
  - `PublicAllocation{priority, amount_per_period}` with treatments HouseholdIncomeSupport,
    ProviderOperatingGrant and AgencyAppropriation;
  - `TaxPolicy.rate_bps`;
  - `PublicBudget{period_cap, cash_floor}`;
  - receipts that show requested, paid and unfunded.

  (financial/model.rs; defines.toml:29; electoral-path E5, E6)
- **Electorate floor.** Voting age is 18–64 plus 65+ (ADR298). The engine has no citizenship,
  registration or felony status, and the repo has no dataset for them.
- **Returns data.** County presidential returns exist through a mirror. The official MIT file is a
  122-byte guestbook stub. No local-office returns exist (electoral-path E9).

**Sources say.**
- **MIM's stance (the game's reading).**
  - "don't vote, organize!" (elections/dontvote.html).
  - Registered MIM comrades do not vote or run (wim/cong/voting91.html).
  - Narrow local exception: city-hall candidates who back public space for revolutionaries: "it
    might be worth supporting them." (elections/dontvote.html); "If we could win a Congress seat, we
    would fight for it." (imp97c6).
  - Reforms came from outside the ballot: "most of the progressive reforms won in this country in
    the past century were the result of organizing and agitation outside of the electoral arena."
    (dontvote.html)
  - Electorate: "Since oppressed nationalities vote heavily for Democrats"
    (democratsfascism2004.html). MIM Notes 96 cites USA Today that Republicans took 63% of the white
    male vote in 1994 (unchecked).
- **Gramsci.** Votes are a measure, "simply an instrumental value". Comparing tiers diagnoses cadre
  depth (p.287).
- **Lenin (the lineage).** Participate "for the purpose of educating the backward strata of its own
  class", because "we must not regard what is obsolete to us as something obsolete to a class, to
  the masses." (LWC ch.7). This is the lineage MIM builds on; **MIM's abstention, with its
  local-space exception, is the game's reading.** The electoral path stays a player option, judged
  by accounts.
- **Research/10.** An office is "a **verb set with a material reach**"; "No municipal, state, or
  congressional act reaches Φ"; the honest ending is "you won, and the number did not move."

**Proposal.**
- **Office.** One county board first. Its decision set:
  - allocation priority order;
  - grant sizes;
  - agency appropriation (including the City PD line);
  - operating-income tax rate.

  All of it sits inside a `period_cap` the board does not set. Wards, if added later, are claims
  overlays on fixed counties. **[MIM forces]** The office panel shows which cohorts' payroll each
  appropriation funds, because public payroll and taxes anchor the labor aristocracy
  (mim-class-structure MC-21).
- **Electorate — [MIM forces].** A counted subset of cohort persons aged 18+ that **excludes by
  construction** two pools: the undocumented (from §8's covered versus uncovered split) and the
  prison pool. Legal status and the prison pool are required inputs, so "the electorate and the
  in-border proletariat barely overlap" (mim-class-structure MC-24, MC-32 item 3) holds by
  construction. ACS citizenship tables are the candidate Derived source for the exclusions
  (electoral-path gaps). If slice C comes before the legal-status split exists, the office panel
  labels the 18+ proxy as an overcount of exactly those two pools.
- **[MIM forces]** The ballot result should read as a contest among labor-aristocratic and
  petty-bourgeois cohorts (mim-class-structure MC-24).
- **Voting.** A collective choice per cohort: candidate A / B / abstain / back an assembly /
  withhold. Shares are conserved within the cohort. Ranking follows what each office's promised
  decision does to the cohort's accounts (subject to §13 Q1). Abstention is explicit.
  - **Memory.** The best reusable P25 idea is the *delivery gap*: a cohort remembers whether the
    office it backed delivered, measured from `PublicBudgetReceipt` requested, paid and unfunded
    (electoral-path E16).
  - **Excluded.** Allegiance drift's P25 Θ coefficients and the hope-valve gain form are fixed
    response forms; re-derive them or drop them.
- **Keeping three paths open.**
  - Electoral: run or back slates.
  - Reformist: hold office; the ceiling bites through unfunded receipts, preemption and absorption.
  - Revolutionary: boycott and build institutions, priced by lost reach among cohorts that still use
    the ballot.

  Stances are read from practice, not bought (ADR137 replaced static tag deltas). Research/24: the
  electoral path is not scripted to lose; "It does not license making the DSA path lose."
- **Reuse versus rebuild.** Treat Program 25 as a spec library: funding identity, five barriers,
  five goldens (restated, not byte-matched, per ADR183), term-frozen results, and electoral → policy
  consumption (research/11). Rebuild everything that was keyed to Python class nodes. ADR126's
  allegiance-as-attribute ruling conflicts with ADR270 and must be re-ruled (§11 item 11).

---

## 10. Making it a game

**Adopt from prior art:**
- **Victoria 3:**
  - data-declared eligibility plus material weights for joining (interest groups);
  - movements competing for each pop "compared to other movements that are valid for them";
  - street pressure changing who leads a group (`MOVEMENT_PRESSURE_IDEOLOGY_FACTOR`, reused as
    structure only).

  (game-prior-art V3-3, V3-4, V3-7)
- **Conserved place capacity.** A per-place political-capacity pool partitioned by participation, so
  nobody counts the same strength twice (research/11).
- **Promise ledger.** Frostpunk 2's promise-for-votes, recorded as delivered or broken against
  next-period accounts, with no trust integer (game-prior-art FP2-2).
- **Dwarf Fortress legibility.** Causes readable after the fact, at cohort grain.
- **Through the Darkest of Times.** Supporters who show up, stay home or are arrested.

**Avoid:**
- V3's radicalism 0–1 bar and radical heat map, with its fixed 25% saturation (00_graphics.txt:99);
- per-type engagement constants ("# 10% - 70% politically engaged");
- momentum dice;
- Democracy 4's support cutoff ("If its over 50%, they vote for the player, if its less, they vote
  for the opposition.") and its 0.2% landslide swing;
- Frostpunk's Hope / Discontent meters;
- CK3 pulse events (scheduled drama);
- loyalty and approval bars (negotiation design A2: "One-dimensional 'Loyalty' bars");
- size worship.

The repo's rule: "Every clause is countable; nothing is a percentage to optimize." (research/10
§2.7)

**Portraits.** Portraits represent groups and organizations (NORTH_STAR:56). Named faces are
personified slots minted at receipts (combat design ruling 2026-10-26). A group portrait, and every
roster entry, shows:
- class profile: income-source mix **plus** (a) signed wage-versus-value balance and (b)
  legal-status and wage-floor coverage counts; the MIM reading comes from (a) and (b), shown as
  "labor aristocracy (MIM default; value term pending)" until (a) exists;
- nation incidence;
- labor-status counts;
- memberships with bounds;
- the delegate it backs;
- its last three choices with causes.

How MIM class readings are worded in player-facing text is a Director question (§13 Q16).

**Progress for a MIM-line organization: two stocks, read from receipts.** MIM's principal task is to
"create public opinion and the independent institutions of the oppressed to seize power"
(faq/mnstyle.html:74; mim-practice F01). The MIM-line organization's progress is measured as two
stocks:
- **public opinion (reach):** persons reached, readership, attendance at its events, counted per
  cohort and nation;
- **independent institutions:** standing programs it runs (Serve-the-People services, assemblies,
  base-area-style "dual power" — "the Red Army built base areas that prototyped socialist relations
  of production and culture as a form of dual power", FPLmimp p.17; mim-practice F06), with their
  members, hours and continuity.

MIM's stages (create public opinion and institutions now; a later leap only after power has
accumulated; mim-practice F02) appear as **descriptive labels** on these stocks, never as triggers.
The Φ-disruption loop gives an engine-computed opening (§11 item 1, option b). Electoral and
reformist players get readable wins too — local space, budget lines, an appropriation moved — and
readable costs: unfunded receipts, preemption, absorption, lost independence. Each path needs a real
win somewhere, "else the dilemma is fake and the game is a sermon" (design-corpus F18).

**New displays and the decision question each answers:**
- **Group roster per county.** "Which groups can my organization reach this period, and at what hour
  cost?"
- **Choice receipt.** "What did each group do, and which account drove it?"
- **Pieces map, per class and across national divides.** "Where would one more bridging organization
  fuse a class's pieces, and where is unity running chauvinist?"
- **Incidence panel for any organization's program, rivals included.** "Who gains, who pays, what
  stays intact?"
- **Office panel.** "What can this seat change, whose payroll does each appropriation fund, and what
  will it leave unfunded?"
- **Labor-status ledger.** "Who is about to stop looking, where is the local reserve pressing hours,
  and how much of each cohort's wage rests on the transfer term rather than the local reserve?"
  (Under MIM's line the domestic reserve ratio is secondary to border and transfer terms.)
- **Progress panel (MIM-line organization).** "How much reach and how many institutions do I hold,
  and which of them would survive repression?"

---

## 11. Conflicts with current rulings, and what needs the Director

*Ranked by consequence for the game's whole arc and its theory line. §13 ranks the same questions by
a different criterion: how much the answer changes what the first slice builds.*

1. **Is a revolutionary outcome reachable from US cohort choices?** MIM's line puts the main force
   abroad and the opening at imperial overextension (mim-class-structure MC-30; FPLmimp p.4).
   NORTH_STAR keeps the revolutionary project playable, and "direction emerges from practice". The
   engine has no overextension signal. **Decide among:** (a) an exogenous opening; (b) an
   engine-computed opening from the owner-ratified Φ-disruption loop, in which "a revolutionary
   movement that disrupts Φ genuinely proletarianizes /" lumpenizes much of the labor aristocracy,
   gated by a conjunctive predicate over geopolitical state that must not become a threshold
   constant (design-corpus F14); or both.
2. **Wage-versus-value instrument.** Under the MIM ruling, the class reading uses MIM's
   international comparison (wage floor, legal working rights, net transfer). A domestic
   reproduction floor would put low-wage US cohorts into the proletariat, which MIM's line rules out
   (mim F25 tension). **Decide:** (i) whether ADR171's domestic reproduction floor stays as the
   separate national-question bribe and deprivation instrument or becomes only a validation check;
   and (ii) whether the external-transfer term is Calibrated (MIM's ×8–10 import multiplier, 1990s
   data, unchecked) or Designed.
3. **Oppressor-nation counterpart.** ADR171 already carries one as a reference: the non-Hispanic
   white census universe (`H`, 192,609,332 persons) stands in for what MIM calls the settler nation,
   with a proxy disclosure, and ADR171 records that "SETTLER as an on-screen name awaits the
   Director" (ADR171 decision, open questions 2 and 8; reports/national-oppression-proposal.md).
   MIM's glossary defines the settler nation as a nation (FPLmimp p.19; settler-thesis ST-01), and
   membership in it is conferred by privilege over time (ST-23). Still open: the on-screen name, a
   producer that attaches the `H` reference and the named-nation shares to household cohorts in the
   Rust engine, and the boundary cases. MIM's own data bear on the boundary: "at least 42 percent of
   the Latino workers as of 1995 are in the productive sector", and the employed Asian-descended
   population is mostly labor aristocracy or higher (mim-class-structure MC-14).
4. **Article II and the grain of groups.** Groups are county-scale cohort cells whose class and
   nation labels are Designed partitions at that scale only; only the extensive profile and the
   signed balance are pushed forward (§1, §3). Confirm this disposition. Caution: the ADR296 fold
   can create unity that is not there — a fold that merges cohorts with different memberships
   manufactures connection, so pieces counts on folded representatives and on detailed principals
   are not comparable (lawvere L28).
5. **Hardening of class (new).** MIM holds that class readings harden and rarely reverse (MC-16,
   MC-17). **Decide** how: as carried history in the state (periods of positive balance; lawvere
   L26), or as a lag on the transfer term. Either way, no threshold constant.
6. **Participation as a choice.** ADR269 fixes participation, and ADR255 and ADR267 omit inactivity,
   migration and entry. "Keep looking / stop" needs a new ADR that partly supersedes them.
7. **Membership write path.** ADR262 and organization.bsl write no membership. AG(i) payload hashing
   is a "Director act". Upstream accessors are missing.
8. **Consciousness and the nation guard.** ADR171 Phase 3 was withdrawn and ADR208 narrowed it. The
   ported ternary pack is test-only, and the bourgeois-nationalism guard ships first. The "a
   positive balance redirects political energy" claim rests on a draft spec and frozen BSL only
   (Thesis 7). Any behavioral effect of nation or balance needs its own ruling.
9. **Connectivity recognizer and joint kernels.** Both are new-primitive questions (lawvere L30).
   The same goes for whether distributive population choices skip ADR248 receipts.
10. **Lumpen and prisoners.** A theory ruling: reserve army or a separate excluded state. **MIM's
    own texts disagree on prisoners.** MIM Notes 225 (2000) counts "working prisoners" as
    proletarian; MIM(Prisons)' FPL says prisoners are "excluded from the economic system of
    production and distribution" and groups them with the First World lumpen (FPLmimp p.39).
    MIM(Prisons) says "some older documents in the etext archive represent an earlier stage in MIM's
    international work and so contradict the more recent developments" (FPLmimp p.10; mim-practice
    F26), which makes the later FPL statement the current line. Also specify whether prison labor is
    an employed state inside a prison labor force or an excluded state with in-kind work, so the
    labor-force identity holds (§8; proposal: excluded with in-kind work).
11. **Electoral scope and allegiance.** ADR126 and P25 are Python-era. ADR126 rules "Allegiance =
    node-attribute distribution over (parties ∪ abstention)"; ADR270 rules "Political agreement
    remains a separate explicit relation, not a household category or an effect of receipt of aid."
    The two conflict for cohorts. Decide whether cohort allegiance is replaced by recorded
    collective choices and membership incidences; then the first office and the eligibility
    evidence.
12. **Mortality response to shortage.** This changes ADR298's Designed constants.
13. **Population scale.** ADR296's grain qualification (fewer principals, bounded advance time)
    limits how many class cohorts per county are affordable. Class splits must subdivide existing
    principals (the `debit_household_parent` pattern).
14. **Rival archetypes and ADR208.** Map rival organizations onto ADR208's five-member faction
    machinery, or rule otherwise (§6); note R18's post-port D-record timing.
15. **Two corrections to the research instructions (no ruling needed).** The instructions given to
    the readers said "allocate ⊣ aggregate" and "Amendment U / ADR090". Both came from a stale
    project note. The live statements are ADR296 (additive pushforward, "not ... an invented
    aggregation adjunction") and ADR091.
16. **Gender.** Unpaid household hours are a candidate material relation (design-corpus F11;
    imperialism-reproduction IR-14). MIM's gender-aristocracy line has no account, and ADR270
    excludes gender assignment. Hold it.
17. **Old Python-era precedents** (ADR070 slots-as-positions, P25, THE_FORMALISM's social chain
    individual ≺ community ≺ class ≺ bloc). Useful priors only; the chain conflicts with ADR270 and
    INV-010 and should not be ported.

---

## 12. Build approaches for the first slice

**A. Derive and display first. No choices.** Build the class profile per cohort (livelihood mix,
signed balance, coverage counts), the labor-status ledger and the group roster. The choice menu is
shown, not executed.
- *For:* no new write paths and no membership ADR; it answers "who" visibly; it tests the class
  derivation against ADR171 masses.
- *Against:* groups still do not decide, so the Director's option 2 is unmet. It may build
  attachment to labels before behavior exists.

**B. One vertical choice slice in Wayne, generalizing ADR299.** Includes the A-level profile for
Wayne only, the reserve sub-state ledger, and two choices:
- (1) the claimant cohort's labor-force status as a distributive split;
- (2) attend / back the assembly delegate as a collective count, with an emergent mandate replacing
  the captured config.

It adds the first consent-written attributed membership, plus receipts.
- *For:* real group decisions on an existing seam (hearing, time accounts, next-period consumption,
  `distribute_staffing_members`); exercises every hard rule (consent, conservation, no curve);
  playable.
- *Against:* needs three ADRs (participation, membership write, emergent mandate) and a hash-surface
  ceremony. Wayne-only grain must later scale under ADR296.
- **Two gaps B must state plainly.**
  - **Nation is deferred.** Thesis 3 makes nation a first-class axis on every group, but B's Wayne
    claimant cohort is a "Designed counted subset of Wayne's no-earner nonowner households" with no
    nation incidence, because the ADR171 Phase 2 producer for cohort nation shares is still blocked.
    Either **B+** brings a Wayne nation-incidence producer into scope (moving the ADR171 Phase 2
    blocker into this slice), or B ships with nation explicitly deferred. **[Director]** approve the
    deferral or require B+ (§13 Q9).
  - **The value term is absent.** B's class reading shows "MIM default, value term pending" for
    covered wage cohorts; the claimant cohort (no earners) shows its Designed claimant label and
    labor-status counts, never "worker".

**C. Electoral first: a county board in Wayne.**
- *For:* answers "electoral system before endorsement"; county fiscal levers already exist.
- *Against:* without group choice, class reading and the legal-status split, votes would come from a
  proxy and risk the D4 pattern, and the electorate would overcount the undocumented and
  incarcerated pools. Under MIM's line the board is also the least informative place to start.

**Recommendation: B (or B+), with the profile and ledger from A built as B's first two pieces.** B
is the smallest slice where groups really choose and organizations really compete, and it reuses
ADR299's proven shape. C follows once cohorts carry class profiles, nation incidence, the
legal-status split and a delivery-gap history to vote from.

---

## 13. Open questions for the Director

*Ranked by how much the answer changes what gets built in the first slice. §11 ranks the same ground
by consequence for the whole game; that is why revolution reachability sits first there and lower
here.*

1. **What does a group's ranking read?** Proposed: the material effect of each offer on the group's
   own accounts, including its share of the transfer for bribed cohorts, with no consciousness term
   until the consciousness question (Q7) is ruled. Every choice depends on this (rulings R23;
   mim-class-structure MC-18).
2. **Wage-versus-value instrument.** Under the MIM ruling, the class reading uses MIM's
   international comparison (wage floor, legal working rights, net transfer). Decide: (i) whether
   ADR171's domestic reproduction floor stays as the separate national-question bribe and
   deprivation instrument or becomes only a validation check, and (ii) whether the external-transfer
   term is Calibrated (MIM's ×8–10 import multiplier, 1990s data, unchecked) or Designed.
3. **Oppressor-nation counterpart.** ADR171 already uses the non-Hispanic white census universe
   (`H`) as the settler reference. May SETTLER be named on screen (ADR171's open question 8)? How do
   cohorts carry the reference and the named-nation shares in the Rust engine, and how are overlaps
   and integration over time handled (settler-thesis ST-23)?
4. **Hardening.** Is a cohort's class reading carried history (lawvere L26) or a lag on the transfer
   term?
5. May the first slice make labor-force participation a group choice (a new ADR partly superseding
   ADR269 and ADR255)?
6. Approve a membership write path and the AG(i) payload ceremony (fields, hashing)?
7. **Consciousness wiring.** How is the consciousness and bifurcation rule wired for cohorts (the
   frozen ternary pack, the draft "redirects" claim, MIM's share-defense and economic-nationalism
   routing), and does the oppressed-nation bourgeois-nationalism guard ship first as ADR171
   requires?
8. **Allegiance.** Is ADR126's cohort allegiance attribute replaced by recorded collective choices
   and membership incidences, given ADR270's "Political agreement remains a separate explicit
   relation, not a household category"?
9. **Slice B and nation.** Approve shipping B with nation incidence deferred, or require B+ with a
   Wayne nation-incidence producer?
10. **Prisoners and the lumpen.** Confirm the later MIM(Prisons) reading (prisoners excluded, First
    World lumpen) over MIM Notes 225, and whether prison work is an excluded state with in-kind
    hours or a separate prison labor force; and whether the prison pool and legal-status split land
    now or later.
11. **Article II grain.** Confirm that groups are county-scale cells with Designed labels and that
    only the extensive profile and balance are pushed forward.
12. Are distributive population choices deterministic mechanics, or do they carry ADR248 receipts?
13. **Revolution reachability.** Exogenous opening, engine-computed opening from the Φ-disruption
    loop (design-corpus F14), or both?
14. Approve a connectivity (pieces) recognizer, and in which form?
15. First office and its decision set (county board as proposed)? Eligibility exclusions from ACS
    citizenship and the prison pool?
16. **Player-facing class text.** How do MIM class readings appear in text and portraits? Proposed:
    as the game's analytic note beside the counts ("labor aristocracy — MIM reading"), never as a
    judgment that a group "is" an enemy (mim F16, F25; for example a Black wage-earning cohort reads
    labor aristocracy under mim-class-structure MC-14).
17. Mortality and fertility response to shortage: allowed to change ADR298?
18. Rival organizations: real names or generic archetypes, and how do archetypes map onto ADR208's
    five factions?
19. Gender: held until a material relation is named and ADR270's exclusion of gender assignment is
    revisited?

---

## Source standing

How each body of sources is used in this brief. The governing, lineage and opposed-line rows follow
the Director's rulings of 18 Nov 2026. Rows marked *inference* are this brief's reading of those
rulings, not the Director's words. The row marked *undecided* needs a ruling.

| Standing | Sources | Use |
|---|---|---|
| Governing line | MIM and MIM(Prisons). The current MIM(Prisons) statement governs; early MIM texts count only where still upheld (mim-practice F26) | Sets how the game reads class, nation, unions, elections and mass work |
| Lineage | Marx, Engels, Lenin, Stalin, Mao | Definitions and method. Where MIM departs, MIM governs, as with the mass reading of the labor aristocracy over Lenin's "handful" |
| MIM-endorsed history | J. Sakai, *Settlers* (settler-thesis ST-06) | History behind the settler thesis; not MIM-authored |
| Opposed lines (Director ruling) | MCU, FRSO | Rival organizations inside the game only; never a source of method |
| Other non-MIM lines (*inference*) | RU and RCP, CPUSA, PLP, Workers World, Trotskyist groups, DSA and social democrats; ProleWiki's Marxist-Leninist line | Contrast and rival archetypes; never a source of method |
| Undecided (*needs a ruling*) | Gramsci, Althusser, Reich; the CPP activist study | Used here only as descriptive aids on consent, institutions and non-participation. No rule rests on them |
| Supporting scholarship | Cope, Smith, Marini and Osorio, Amin, Meillassoux, Mies, Federici, Fortunati, Banaji | Evidence on transfer and reproduction, each within its stated scope |
| Descriptive social science | Scott, Wood, Kalyvas, Weinstein, Jackson | How people join, free-ride, exit and comply; no line authority |
| Method only | Lawvere | Bookkeeping discipline: extensive profiles, detected connection, finite kernels. No model of class |
| Game prior art | Victoria 3, Democracy 4, Frostpunk 2 and others | Patterns to adopt or avoid |
| Project law | Constitution, NORTH_STAR, AGENTS.md, accepted ADRs | Binding |

---

## Appendix A: Source map by reader

- **rulings:** CONSTITUTION, NORTH_STAR, AGENTS,
  ADR070/084/091/126/134/171/180/184/189/208/248/255/262/267/269/270/296/298/299, phase_order.rs,
  hypergraph_store.rs. *Not found:* Linear PER-32 and PER-337 texts; a live ADR authorizing group
  choosers; Rust electoral code; Amendment U under ADR090 (it is ADR091).
- **design-corpus:** docs/gameplay research 01, 05, 06, 07, 10, 11, 12, 21–25; peacetime-verbs,
  negotiation/party-life and combat designs; organization spec; consciousness-recoupling spec; the
  Electoral Question; Program 19 and 25. *Not found:* any prior document making population groups
  decision-makers.
- **engine:** national_household_allocation, staffing, household_time, household_lifecycle,
  financial model, organizer contract and hearing, preset.rs, structure.bscn, client money_map and
  organizer surfaces. *Not found:* class fields, consciousness state, migration and inactivity
  flows, electoral code, group intents, a membership writer.
- **mim:** cardinal.txt, threepoints, FPLmimp.pdf, imp97 (A.3, A.4, C.4–C.6), faq pages, congress
  resolutions, elections pages, program.html. *Not found:* MT1 text (image-only); an authoritative
  US class-share split.
- **marx-engels:** Capital I (ch.6, ch.25), II, III ch.52; TSV excerpt; Manifesto; Poverty of
  Philosophy and Brumaire (web); Engels letters (clause-level only).
- **lenin-stalin-mao:** A Great Beginning; Imperialism; Split in Socialism; WITBD; LWC; Mao 1926,
  1927, 1933, 1937, 1943, 1957; Stalin 1913.
- **imperialism-reproduction:** Cope, Smith, Marini/Osorio, Meillassoux, Mies, Federici, Fortunati,
  Banaji, Amin. *Not found:* Emmanuel and Amin's Law of Worldwide Value (image-only).
- **prolewiki:** Library texts (Mao, Dimitrov, Dutt, Political Economy, Haywood, Bolshevik
  Tendency). Its Main namespace lacks class articles.
- **lawvere:** 1962, 1969, 1970, 1972, 1975, 1986, 1988–1999, 2003, 2007 and 2009 texts; repo
  research/32. *Not found:* any Lawvere model of social class.
- **collective-action:** Scott (three books), Wood, Weinstein, Kalyvas, Jackson. *Not found:* Nan
  Lin (no text layer).
- **organizing-practice:** ADR262/184, organization spec, Gramsci, Althusser, Reich, MIM FAQs, CPP
  study; MCU and FRSO texts as opposed lines.
- **game-prior-art:** Victoria 3 data files and repo readings; D4, Frostpunk 2, Terra Invicta,
  Tropico, TDoT, Disco Elysium, DF, Suzerain (web summaries).
- **labor-supply:** staffing and lifecycle code, ADR255/267/270/298, qualification report, Capital I
  ch.25.
- **electoral-path:** NORTH_STAR, ADR126/136/140/299, financial model, defines, the Electoral
  Question, research 10/11, MIM elections pages, MIT returns.
- **mim-class-structure:** imp97 (full), internalclass3, MIM Notes 201/224/225, whitemyths, faq.
  *Not found:* MT1 and MT10 articles.
- **mim-practice:** primer, mnstyle, FPLmimp, mt7, mt10bpp, critique.of.rcp, focoism, mim-docs,
  mim-gender (page images).
- **mim-on-other-lines:** wim/wyl directory pages, Workers World and CPUSA reviews, theses on
  fascism, mimhist, sds, subreform, mn129. *Not found:* MIM text on MCU; "First Worldism" as a term.
- **settler-thesis:** FPLmimp, MIM Notes 69/96/129/145/153, readsettlers.org ch.4–7 and ch.14,
  research 06/21/24, ADR054.
- **mcu-frso-as-rivals:** MCU theses, flyer, pre-party document, W2W statement; frso.org program
  pages; MIM counter-texts.

## Appendix B: Claims dropped or left unverified

- **CK3 faction mechanics (game-prior-art CK3-1)** dropped: the source page did not load.
- **Lawvere 2007 "points and pieces"** sentence only weakly confirmed (fragment match). The 1969
  quantifier wording was partially confirmed.
- **Engels 1858 and 1882 letters and the 1892 and 1895 prefaces (marx-engels M19–M22):**
  clause-level only, via fetch summaries. Re-check before quoting. M21's claim that privilege is
  lost when monopoly breaks was dropped.
- **mim-practice F02/F03:** the lines that armed struggle is not yet a serious question and that
  victory is made by the whole world are the prisoner author Lord Grim's, not MIM's. mim-practice
  F07 (service use is not agreement) and F16 (no route from a lost bribe to revolution) are
  inferences.
- **mim F13** corrected: the Panthers' lumpen alliance *repelled* Euro-Amerikan workers.
- **mim F16:** the claim that Mao counted the labor aristocracy only as an enemy was dropped.
- **lenin-stalin-mao F14** corrected: Lenin calls a bourgeois labour party improbable to prevail for
  long, not lasting until the revolution.
- **MIM numerical claims** (1985–1999 surplus value, superprofit share, capitalist 1%, lumpen shares
  by nation 2010, 63% white male vote) are unchecked against current data. MT1's tables are unread.
- **Engine negatives only partly evidenced:** WorkerClass absent from the graph; client shows no
  class surfaces; Python-port packs absent from every preset; `claimant_mandate` and
  `partner_mandate` seen only in tests (engine E05, E10, E12, E19).
- **Lifecycle and staffing precedents:** "no shortage response" is inferred from constant rate
  arrays (engine E17, labor-supply R1); exact apportionment and carried remainders rest on
  signatures and the tie-break sort, with function bodies not read (lawvere L20).
- **MCU/FRSO trajectory synthesis** downgraded to low-confidence reader interpretation, not MIM.
  FRSO "strategic alliance" appears only as a site navigation title.
- **ProleWiki PW-07** paraphrases ("partners to a certain degree", "natural ally") unverified.
  PW-10's "freedom of discussion" was not found.
- **Wood "pleasure of agency":** the formal model's sign conventions are not fully read. Jackson's
  threshold form needs a Director check before use.
- **The claim that a positive balance redirects political energy:** confirmed only as frozen BSL and
  draft-spec text (rulings R17; design-corpus F12), not in live Rust. Thesis 7 no longer states it
  as settled.
- **Victoria 3 consolidation thresholds and officer weights:** taken from repo readings, not re-read
  in game files.

---

## Method and revision record

- **Readers.** Nineteen readers each covered one body of sources (Appendix A). A second agent then
  opened every citation and checked each quote against its source. 488 findings were kept. 26 of
  them rest on MCU, FRSO or RU texts and are tagged as opposed-line or other-line evidence in the
  evidence file.
- **Rulings applied.** The Director's two rulings of 18 Nov 2026 were given to the synthesis, review
  and revision steps.
- **Review.** One adversarial review of the first draft raised 2 blockers, 16 major and 14 minor
  issues. Every blocker and major issue was applied. The blockers: the class display defaulted to an
  income-source reading in which a US wage cohort would show as a worker, and the first Director
  question offered MIM's international wage-versus-value reading as one option of two.
- **Declined.** The two Director lists (§11 and §13) keep different orders on purpose. §11 ranks by
  consequence for the whole game, §13 by effect on the first slice.
- **Final corrections by the lead, not from the review.** ADR171 already carries a settler reference
  and an open question on naming it (§11 item 3, §13 Q3). The project's Opportunist Zoo briefing
  already types the MCU kind of rival (§6). Only the enforcement channel of the settler pattern is
  computable from today's accounts (§6). Two errors in the research instructions were corrected (§11
  item 15). The source-standing table was added.
- **Limits.** MIM's numerical claims are unchecked against current data. MIM Theory 1 could not be
  read. Engine negatives rest on searches, not full traces (Appendix B).
