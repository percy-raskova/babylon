# Babylon Negotiation, United Fronts & Internal Party Life — the room and the floor

Dated record, 2026-10-26. Status: APPROVED for design (user, 2026-10-26);
implementation explicitly NOT authorized (the PER-354 workhorse owns the
tree). This document is the authority the negotiation, coalition, and
internal party-life gameplay plan will argue from. Research briefings
and specs it rests on:
`docs/gameplay/2026-10-25-porch-01.md`, `docs/gameplay/2026-10-25-porch-02.md`,
`docs/gameplay/2026-10-26-combat-design.md` (§4, §5, §13),
`docs/gameplay/2026-10-26-peacetime-economic-verbs-design.md` (Verb 2 & `D2`),
`docs/gameplay/research/04-stalin-cpsu-and-splits.md`,
`docs/gameplay/research/05-lenin-witbd-and-vanguard.md`,
`docs/gameplay/research/06-mimp-and-mlm-tw-canon.md`,
`docs/gameplay/research/10-v3-electoralism-and-babylon.md`,
`docs/gameplay/research/11-v3-rea-electoralism-binary.md`,
`docs/gameplay/research/12-lenin-stalin-vanguard-party-threshold.md`,
`docs/gameplay/research/21-opportunist-zoo-adventurists-patsocs-wreckers-and-streamer-complex.md`,
`docs/gameplay/research/22-carceral-pipeline-prison-organizing-and-lumpen-solidarity.md`,
`docs/gameplay/research/23-revolutionary-metabolism-sinks-scarcity-and-cadre-reproduction.md`,
`docs/gameplay/research/25-erol-new-communist-movement-amerikan-examples.md`,
and `docs/gameplay/research/27-armed-group-endings-and-violence-logic.md`.

## 1. Intent and the why

In nearly every strategy game, external diplomacy is a merchant trade
screen with a green/red acceptance sum (`+15 Trust, -20 Base Reluctance`),
and internal politics is either a passive `Stability: 74%` bar or a
bourgeois parliament where you bribe faction leaders with pork. Both
turn politics into accounting.

In Babylon, **Negotiation & United-Front Play (#2)** and **Internal
Party Life & Congresses (#3)** are two sides of a single dialectical
fact established in `Porch 02` §2 and `research/04`: **the figurehead is
not the node.** Every collective entity on the map—whether UAW Local
600, a city-wide tenant coalition, a Pelican Bay prison yard pact, a
rival socialist sect, or your own Vanguard Party—has two distinct layers:
- **The Room (The Leading Body / Executive Board / Delegation):** The
  committee that holds the gavel, signs the checks
  (`PracticeInputAuthorityLedger`), negotiates deals, and collects the
  salaried staff payroll (`survival_interest`).
- **The Floor (The Rank-and-File Base):** The counted worker, tenant,
  prisoner, or cadre cohorts underneath, carrying their own material
  grievances (unpaid stipends, household exhaustion $E_i$, rent notices,
  shop-floor repression) and their own ideological line.

Because the Room and the Floor can diverge, both external negotiation
and internal party struggle play as a tense tug-of-war between **cutting
deals in the Room** and **organizing mandates on the Floor**.

## 2. Goals, non-goals, anti-goals

**Goals.**
- G1. Make external negotiation (`#2`, including `D2` unlocking a Union
  Local or Co-op treasury) a three-move game between the **Room** (trading
  dated `review_condition` promises on the *Promise Register*) and the
  **Floor** (going over the board's head to the rank-and-file via
  `Shift / Split / Flip`).
- G2. Make State, NGO, and corporate **Wedge Offers** (`Offer/Split`
  ledger) doubly dangerous: rejecting a buyout tests your internal
  `Conciliator / Consumer` nodes for a right-opportunist split, while
  accepting via a deceptive front-group counter-trap ("take the bait,
  burn the hook") pits your clandestine apparatus against federal fraud
  and legitimacy blowback.
- G3. Make **Party Congresses (#3)** high-stakes historical events that
  can be called voluntarily (at the cost of `Cadre Labor`, `Money`, and
  a **coalescing meeting leak surface** watched by `L_NSA`/`L_FBI`) or
  forced when an internal contradiction hits its barrier.
- G4. Give the Party Congress a hands-on **Mandate & Two-Front Floor
  Fight** mechanic built on the *Short Course*'s six powers: bypassing
  captured delegations (*Leningrad 1925*), separating real material
  grievances from wrong political lines (*The Military Opposition*), and
  concentrating fire on the **main danger** (*the deviation you stopped
  fighting*).
- G5. Make losing 20–30% of your headcount in a principled **Split or
  Purge** (*Prague 1912 / 1921 Purge*) feel like a thrilling structural
  breakthrough—not through fake morale buffs, but by resetting
  `survival_interest`, severing police informant edges attached to
  expelled opportunists, removing consent-refusal friction, and
  triggering **August-Bloc collapse** among your rivals (Key B
  recognition).

**Non-goals.**
- No numeric "Opinion / Trust: +45" diplomacy bars with rival orgs or
  unions.
- No instant, free tech-tree clicks on Screen #6 (`Line / Doctrine`)—major
  line turns and expulsions require a Congress.
- No temporary stat multipliers (`+20% Morale for 5 turns`) after a
  split or purge.

**Anti-goals (what makes this a failure even if it works).**
- A1. **Big-tent size worship:** Any mechanic where keeping 1,000
  undisciplined `Consumers`, `Conciliators`, and union bureaucrats in
  one bloated org is strictly stronger than purging down to 300 hardened
  cadres. *"Cohesion without clarification is rot with good manners."*
- A2. **One-dimensional "Loyalty" bars:** Modeling internal opposition
  as a loyalty float rather than the triple of **(Material Grievance +
  Political Line + Antagonism Stage)**.
- A3. **Risk-free national meetings:** Allowing delegates from every
  cell to convene in a Congress with zero exposure to the State's
  surveillance dragnet when clandestine *faux frais* (`Verb 3`) is
  unfunded.

## 3. Constraints (binding)

- C1. **Stalin 1906 Legal-Body Autonomy (`D2`):** A Union Local, Co-op,
  or legal coalition has its own budget, its own leading body, and its
  own congress (`PracticeInputAuthorityLedger`). Its treasury is never
  spendable by the Party without either a **Room Deal** (writing a
  binding `review_condition`) or a **Floor Resolution** (`Shift / Split / Flip`).
- C2. **The Four-Stage Antagonism State Machine (`research/04`):**
  Every internal or coalition tendency occupies one of four discrete
  states:
  $$\text{Fellow-Traveller} \longrightarrow \text{Conciliator / Buffer} \longrightarrow \text{Faction} \longrightarrow \text{Antagonist}$$
  The exact crossing into `Antagonist` is the period the minority stops
  appealing to the Party/Coalition and appeals to forces *outside* it
  (the bourgeois press, the courts, the employer, or the police).
- C3. **The Main Danger Law (*Short Course* Ch. 11 §3):** In two-line
  struggle (`Left-Adventurist` vs. `Right-Opportunist / Economist / Chauvinist`),
  the growth weight of a deviation is a function of **periods of
  attention withheld**, not its current headcount.
- C4. **Coalescing is the leak (`2026-10-26-combat-design.md` §4 & O4):**
  Gathering delegates for a Congress or coalition summit creates a
  coalescing signature across the edges used (`EdgeMedium::Digital` vs.
  `Courier | FaceToFace`). Without funded Clandestine *Faux Frais*
  (Peacetime Verb 3), `L_NSA` and `L_FBI` observe the delegate
  convergence (*Minsk 1898*).
- C5. **Visibility rule:** Never show "% chance of split," "faction
  loyalty: 62%," or "informant probability." Show delegate counts
  (`voting / members represented / voice`), named `review_condition`
  promises, the contradiction tension on Topology, and the chapter's
  actual grievances and slogans.

---

## 4. Part I (#2): Negotiation, United Fronts & Union Treasuries

Whenever the player interacts with an external collective node—unlocking
UAW Local 600's treasury (`D2`), forming a popular front, negotiating a
Pelican Bay **Prison Solidarity Pact** (`research/22`), or answering a
State/NGO **Wedge Offer**—play operates across **four concrete moves**.

### Move 1 — The Room Deal (Trading on the *Promise Register*)
You approach the external body's **Leading Body** (the union executive
board, the coalition steering committee, the yard shot-callers). Because
their executive board optimizes its own institutional survival
(`survival_interest`, grant renewal, or contract peace), a Room Deal is
always an **exchange of immediate capacity for a dated political
constraint**:

- **What you get immediately:** Authorization on
  `PracticeInputAuthorityLedger` to spend a tranche of the Local's cash
  on your strike larder or kitchen, access to their leased hall (`Space`),
  or joint `Supporter Labor` turnout for a demonstration.
- **What you sign away (`review_condition`):** A concrete, dated covenant
  written directly into your Wiki's **Promise Register**:
  - *"Local 600 releases $15,000 to the strike kitchen, provided the
    Party halts wildcat shop-floor leaflets at Dearborn Assembly through
    Period 22 and endorses the Local's slate for City Council."*
  - *"The Peace Coalition co-sponsors the port march, provided no
    speaker attacks the Democratic mayor by name and marshals turn over
    anyone carrying defensive gear."*
- **The enforcement cliff:** While the `review_condition` is active, any
  operation that violates it is flagged on the **Seal** screen as a
  covenant breach. If you breach it (or fail to deliver by the deadline),
  the partner edge flips to antagonistic on the spot, the treasury lock
  snaps shut, and the **Corporate Feed** prints your broken word to
  every fellow-traveller in the county.

### Move 2 — Going Over Their Heads to the Floor (*United Front from Below* $\rightarrow$ `Shift / Split / Flip`)
When a union executive board (`salaried_staff`) or coalition leadership
refuses to unlock its treasury—or demands a sellout `review_condition`
you refuse to sign—you do not have to accept "No." You can spend
`Cadre Labor` on **Floor Organizing** inside their rank-and-file cohorts
before their body's next general meeting.

At Period Close, when the floor vote is called, the clash between your
organized shop-floor edges and the board's `survival_interest` payroll
resolves across Babylon's three dialectical barrier outcomes (`Porch 02`
§2):

1. **Cave (`QualitativeShift` — The Board Bends):**
   Your floor support clears the vote threshold, but antagonism stays
   below the rupture point. To save their own chairs, the union brass
   caves, adopts your resolution, and releases the treasury tranche
   without a split—while keeping their offices and waiting for you to
   stumble.
2. **Breakaway (`AntagonisticSplit` — The DRUM / EROL Rupture):**
   When the entrenched bureaucracy uses parliamentary tricks or police
   guards to block a majority floor mandate (as the UAW bureaucracy did
   against Black auto workers at Eldon Avenue in `research/25`), the
   node literally **tears in two on the Topology canvas**: your militant
   cohorts walk out into a new, independent revolutionary node (e.g.,
   *Dodge Revolutionary Union Movement*), partitioning the membership
   and dues stream and drawing a hot antagonistic edge against the old
   union hall.
3. **Ouster (`WinnerTakeAllFlip` — Taking the Gavel):**
   In an indivisible chartered seat where your floor mandate overwhelms
   the board, you oust the old leadership outright and take the gavel,
   the building lease, and the entire `Legal Institution` book—which
   immediately triggers the bourgeois order's counter-move: the national
   union headquarters threatens **international trusteeship** to freeze
   the bank account, the employer files for an injunction, and the four
   inherited salaried staffers immediately begin ticking on *your*
   `survival_interest` clock!

### Move 3 — Inside the United Front (Lenin's Fellow-Traveller Law)
Once you are inside a United Front or electoral coalition (`research/04`
Part I, `research/10`–`11`), the coalition is never a static alliance—it
is an active contest over **who steers the mass energy (`SL`) and who
captures the base**. Each period, you set your **Coalition Polemic
Stance**:

- **Suspend Criticism ("Big-Tent Unity / Freedom of Criticism"):**
  Your newspaper holds its fire on your coalition partners' vacillations.
  **Immediate feel:** Smooth sailing—coalition treasury access stays
  open, State heat drops, and the Corporate Feed praises your "pragmatic
  maturity." **Material consequence:** Per Victoria 3's proven coalition
  law (`CParty::GetVotingPowerFor`, `research/11`), while your cadres do
  the legwork to bring out the votes and crowds, your wealthier liberal
  or union-bureaucracy partner's superior `Clout` pockets the seats, the
  media credit, and the unorganized `Supporter Labor`. You become the
  Democratic Party's unpaid ground game.
- **Strike Together, Criticise Unsparingly (Lenin's Legal-Marxist Rule):**
  You deliver full `Cadre Labor` on the joint strike or ballot line
  while using the *Liberated Signal* to relentlessly expose every
  hesitation, compromise, and grant-string of your partner's leadership.
  **Material consequence:** The partner's executive board fumes (raising
  Room friction), *but* every time their leadership flinches under State
  or employer pressure, their disillusioned rank-and-file cohorts defect
  across the graph edge directly into your chapters!

### Move 4 — Answering the Wedge Offer (`Offer/Split` Ledger: Split Test + Counter-Trap)
As established in `2026-10-26-combat-design.md` §5 and `research/27`,
the State's sharpest weapon in an upper-income country is
**classification**: splitting "reconcilables" from "irreconcilables" by
putting a generous **Wedge Offer** on the table (e.g., a foundation
grant, a seat on the Civilian Police Review Board, or dropped felony
charges for moderate defendants if the organization halts a strike or
disavows its militant wing).

When a Wedge Offer lands on your desk, you have **three playable
answers** (Director ruling, 2026-10-26):

1. **Accept on Their Terms:** You get the cash, the dropped charges, or
   the legal seat today. In exchange, the engine writes their
   pacification clause into your Promise Register, increments
   `salaried_staff` (`survival_interest`), and severs your edges to any
   militant node you disavowed.
2. **Reject Outright (The Internal Split Test):**
   - If your organization is ideologically consolidated (`Investor`
     cadres, rectified line), rejecting the bribe costs nothing and
     hardens class consciousness.
   - **The Split Test:** If your organization harbors unrectified
     `Conciliator / Buffer` nodes or a high ratio of Weinstein
     *Consumers* whose households are under economic pressure, rejecting
     the State's carrot advances those nodes **one stage up the
     Antagonism Ladder (`Fellow-Traveller -> Buffer -> Faction -> Antagonist`)**.
     Push an existing right-opportunist `Faction` with a rejected buyout,
     and they **split off on the spot** to sign the deal with the Mayor
     themselves!
3. **The Deceptive Counter-Trap ("Take the Bait, Burn the Hook"):**
   You instruct a disposable legal front or buffer node to sign the
   grant or settlement on paper while covertly siphoning the cash and
   supplies through `EdgeMedium::Courier` into your underground `c`
   apparatus or strike larder.
   - **How it resolves:** It pits your clandestine *faux frais* (`Verb 3`)
     directly against the donor/state agency's `Dossier` resolution. If
     your cutout holds, you fleece the bourgeoisie to fund the
     underground. If an informant or audited book exposes the diversion
     to `L_FBI` / `L_PD`, the State springs a felony fraud/conspiracy
     sweep, sequesters the front's assets, and prints the scandal across
     all three feeds.

---

## 5. Part II (#3): Internal Party Life, Two-Line Struggle & The Party Congress

### 5.1 What a Faction Actually Is (`Grievance + Line + Stage`)
Babylon abolishes the 1D "loyalty bar." Every internal tendency or
dissenting bloc inside your organization is a typed triple on the
collective nodes that carry it:

1. **A Material Grievance (Observed from Peacetime Economy):** Unpaid or
   pro-rata shorted stipends (`Verb 2`), unresolved household care hours
   hitting the 672-hour cliff (`Verb 1`), uneven arrest casualties across
   counties, or a union payroll (`salaried_staff`) whose livelihood is
   threatened by militant action.
2. **A Political Line Deviation (Screen #6 `Line / Doctrine`):** Which
   trunk or trap the bloc advocates—e.g., *Imperialist Economism ("30
   for 40")*, *Moralist Adventurism / Focoism*, *PatSoc / White
   Chauvinism*, *KKKommunities of KKKare Charity*, or *Liquidator
   Electoralism*.
3. **A Stage on the 4-Stage Antagonism Ladder (`research/04`):**
   - **Stage 1 (`Fellow-Traveller`):** Honest disagreement inside
     committee meetings; obeys discipline.
   - **Stage 2 (`Conciliator / Buffer`):** *"Worse than the deviation
     itself"* (*Short Course*): pleads for "unity," blocks rectification
     of Stage 3 nodes, and shields deviators from criticism.
   - **Stage 3 (`Faction`):** Secret internal platform, separate slate,
     informal whip, or separate dues book.
   - **Stage 4 (`Antagonist`):** Crosses the boundary by appealing to
     forces *outside* the organization (leaking to the Corporate Feed,
     holding a parallel demonstration, suing over a hall lease, or
     informing to police).

### 5.2 When a Party Congress Convenes (Voluntary vs. Barrier-Forced & The Meeting Leak)
A **Party Congress** is not a menu tab you click for free; it is a major
organizational convocation (Director ruling, 2026-10-26):

- **Voluntary Convocation:** The player schedules a Congress during the
  peacetime Decide step to **Constitute the Party (`Key A`)**, ratify a
  new ideological trunk on **Screen #6 (`Line / Doctrine`)**, rewrite
  membership rules (*1903 Rule 1*), or clean out accumulating
  `salaried_staff` and `Factions` before they cross into antagonism.
- **Barrier-Forced Convocation:** A Congress is forced onto the calendar
  when (a) a Stage-3 `Faction` captures enough chapter committees to
  demand a Special Congress, (b) `salaried_staff > cadre_count` triggers
  a payroll revolt over budget authority, or (c) a catastrophic
  strategic defeat (loss of a Base Area or decapitation sweep) requires
  an emergency conference (*Prague 1912* / *Zunyi 1935*).
- **The Coalescing Leak ("You Fear the Meeting"):**
  Convening a Congress requires delegates from every chapter to assemble
  or link up. Per `2026-10-26-combat-design.md` §4, **gathering is when
  the State sees you.**
  - If you convene a Congress on the cheap over surface/digital edges
    without funding Clandestine *Faux Frais* (`Verb 3` safe houses,
    couriers, and vetting), the Congress emits a massive coalescing
    signature into $L_{\text{NSA}}$ and $L_{\text{FBI}}$—risking the
    **Minsk 1898 outcome** where your newly elected Central Committee is
    arrested on the train ride home!
  - If you pay the *faux frais* to hold an underground/courier-vetted
    conference (*Prague 1912*), the gendarmes hear nothing until your
    resolutions hit the street.

### 5.3 Playing the Congress: The Mandate & Two-Front Floor Fight
When the Congress opens on Screen #6, the player is presented with the
**Congress Floor Ledger**, displaying each chapter's delegation in the
*Short Course*'s canonical format: **`Voting Delegates | Members Represented | Voice Delegates`**.

Crucially, because **a node's delegate is not the node** (*Leningrad
1925*, `research/04` Part II §3), a chapter whose local committee was
captured by a `Faction` or `Buffer` can arrive with **100% opposition
voting delegates even when 70% of that chapter's rank-and-file cadres
support the centre!**

Before calling the final roll-call vote, the player executes a
**three-action Congress Floor Fight**:

1. **Send Emissaries to a Captured Base (*The Leningrad 1925 Move*):**
   Instead of bribing a hostile delegation leader in the Congress hall,
   you dispatch trusted central cadres (`Cadre Labor`) straight back to
   the captured chapter's shop floors and kitchens to explain the draft
   resolution directly to the rank-and-file. If the base's material
   tie to the Party is intact, the base revokes the phony mandate and
   flips the delegation (`97% endorsement`) before the gavel falls.
2. **Settle the Material Grievance, Smash the Line (*The Military
   Opposition Move*):**
   Per *Short Course* Ch. 8 (`research/04`), an internal opposition bloc
   often combines a **real material grievance** (e.g., exhausted
   households, shorted stipends, reckless casualties) with a **wrong
   political line** (e.g., defending amateur circle-spirit or
   economism). If you address the material grievance (committing funds
   to a kitchen, fixing the stipend row, or replacing an abusive local
   commander) while refusing to compromise a millimeter on the political
   resolution, the honest rank-and-file workers peel away from the
   faction, leaving the ideological opportunists isolated with a tiny
   rump of votes.
3. **Concentrate Ideological Fire (*Fighting on Two Fronts*):**
   In the Main Political Report, you nominate the **Main Danger** (`Left
   Deviation`, `Right Deviation`, or the `Conciliator Buffer` shielding
   them). Per Stalin's law (*Short Course* Ch. 11 §3), whichever
   deviation you have *neglected* in recent periods has quietly grown in
   weight. Naming and exposing the true main danger strips the
   `Conciliator Buffer` of its cover and forces wavering delegates to
   choose sides.

### 5.4 The Six Powers of the Gavel & Why Purges/Splits Feel Great
Once the floor fight settles the delegate counts, the player bangs the
gavel on one or more of the **Six Congress Powers** (`research/04`):
1. **Ratify a Line Trunk** on Screen #6 (locking in the Three-Strand
   Class/Nation/Gender line and unlocking its practices).
2. **Rewrite Organizational Rules** (enforcing **1903 Rule 1**:
   membership requires personal participation in a cell, not Martov's
   loose "regular assistance").
3. **Dissolve All Factional Groups** (*10th Congress Resolution on Party
   Unity*: outlawing separate platforms and faction discipline on pain of
   immediate expulsion).
4. **Replace a Delinquent Regional Committee** (*Moscow / Transcaucasia
   1930*: removing a local leadership that refused to rectify chauvinist
   or economist errors).
5. **Expel Named Factions or Careerists (*Prague 1912* / *15th Congress*):**
   Drawing a hard organizational boundary and leaving the Liquidators,
   Trotskyists, or PatSocs outside it.
6. **Conduct an Open Cleansing Purge (*The 1921 Purge*):**
   Vetting the membership in open meetings with non-Party worker
   participation to expel careerists, consumers, and repainted
   Mensheviks—cutting total membership by 20–30%.

### Why Losing 25% of Your Headcount Feels Like a Triumph (Zero Fake Buffs)
In a bourgeois game, losing 25% of your units is a disaster. In Babylon,
executing a principled **Split (*Prague 1912*)** or **Cleanse (*1921
Purge*)** delivers **four immediate, visceral structural rewards** with
zero artificial stat multipliers (Director ruling, 2026-10-26):

1. **Slashing the `survival_interest` Calcification Clock:**
   Expelling careerist union/NGO staffers and Martov "fellow-travellers"
   immediately drops `salaried_staff` relative to `cadre_count`, pulling
   your Party back from the 260-period Kautskyite SPD calcification
   cliff (`Porch 02` §6).
2. **The Counter-Intelligence Cleanse (Severing `Malinovsky` Edges):**
   Because police informants, FBI provocateurs, and skimmers (`D1`)
   overwhelmingly lodge inside undisciplined `Consumer`, `Adventurist`,
   and `Faction` nodes, expelling those formations **physically severs
   the State's active informant and surveillance edges into your graph**—often
   blinding an FBI or City PD dossier ($L_c$) that was one period away
   from a raid, without you ever needing a "mole-hunt % bar."
3. **Removing Consent Friction (`operational_yield -> 1.00`):**
   A bloated organization of 1,000 Martov "assistants" constantly fails
   practices with `InsufficientCommittedTime`, `RefusedForConsent`, and
   `NoResponse` (`research/23` §3.3). Cutting down to 300 Rule-1 cadres
   eliminates internal vetoes and foot-dragging—so your smaller Party
   actually completes *more* operations per period with sharper
   discipline.
4. **August-Bloc Collapse & Key B Vanguard Recognition (*Lenin to Armand,
   1914*):**
   When you expel the Liquidators or split from an opportunist coalition,
   they do not form a stronger rival party. Within two to three periods
   on the **Topology** and **Ticker** screens, the player gets the
   ultimate payoff: watching the expelled "August Bloc" fracture against
   each other, take bourgeois foundation money, and lose their worker
   cohorts—who walk right back into your chapters, firing **Key B of the
   Vanguard Party Lock**!

---

## 6. Dramatic Decision Ceremonies

### Ceremony 6 — *The Local 600 Floor Fight (Negotiation #2 / `D2`)*

**Trigger.** Your strike larder in Wayne County is down to two periods
of food (`Verb 4`). UAW Local 600 holds `$42,000` in its strike and
education reserve (`Legal Institution` book, `salaried_staff = 14`). You
have asked the Local's executive board to release `$18,000` for the
communal kitchen.

**Pane left.**

> **UAW LOCAL 600 EXECUTIVE BOARD — Dearborn Hall, Sunday 4:00 PM**
>
> President Henderson and the fourteen salaried reps sit on the platform.
> The Local has forty-two thousand dollars in the credit union. Down in
> the stamping plant, your shop-floor cells hold six of the nine shift
> stewards, and four hundred workers are waiting in the parking lot to
> hear whether the kitchen stays open on Monday.
>
> Henderson pushes a typed one-page memorandum across the green baize
> table: the board will release nine thousand dollars—half of what you
> asked—if your committee signs a joint statement ending the stamping-plant
> slowdown and disavowing the wildcat stewards by noon tomorrow.

**Options.**

- **Sign Henderson's memorandum (The Room Deal).** *Nine thousand
  dollars clears into the kitchen account tonight. The Promise Register
  records your pledge to halt the stamping-plant slowdown through Period
  26. Two of the wildcat stewards in the parking lot tear up their cards
  when they read the leaflet on Monday morning.*
- **Take the microphone on the general-membership floor (Floor Fight —
  Push for a Shift or Flip).** *Bypass the platform and put the full
  eighteen-thousand-dollar kitchen appropriation to a standing vote of
  the four hundred members in the hall. If your shop-floor stewards hold
  the room, Henderson either signs the check to save his gavel or gets
  voted out of the chair tonight—at which point the International in
  Detroit will petition a judge to place the Local under trusteeship
  next month.*
- **Walk the stamping-plant stewards out of the hall (`AntagonisticSplit`
  — Form a Revolutionary Union Movement).** *Leave Henderson his
  building, his fourteen staffers, and his credit-union account. March
  the six shift stewards and the stamping-plant floor across the street
  to constitute an independent plant committee that answers only to the
  strikers—with zero cash in the bank and 100% control of the line.*

**The seal.**

> *Staked: eighteen thousand dollars, the stamping-plant stewards, and
> who speaks for Dearborn Assembly. Unknown: whether the second-shift
  machinists vote with the platform or with the parking lot, and how
  fast the International files for trusteeship if Henderson falls.*

---

### Ceremony 7 — *The Foundation Wedge (`Offer/Split` Ledger)*

**Trigger.** Period 32. The county prosecutor has indicted four of your
cadres after a rent-strike eviction blockade, while a major Ford/Soros-style
philanthropic foundation (`CulturalFront` / NGO rung) approaches your
tenant coalition's Moderate buffer wing.

**Pane left.**

> **THE CIVIC HARMONY INITIATIVE — Suite 1400, Downtown**
>
> The program officer has a check for eighty thousand dollars made out
> to the *Wayne County Tenant Resource Center*—a 501(c)(3) shell your
> coalition's legal clinic uses—and an informal assurance from the
> prosecutor's office that the trespassing charges against three of the
> four defendants will be dropped to misdemeanors.
>
> The fourth defendant—the cadre who threw the sheriff's padlock into
> the river—is excluded from the deal. The grant contract requires the
> Resource Center to adopt a "non-confrontational mediation charter" and
> hire two full-time grant administrators from the foundation's approved
> roster. Your `Conciliator` chapter in Midtown is already begging you
> to sign so the clinic doesn't lose its lease.

**Options.**

- **Reject the grant and the plea split in open session (The Split
  Test).** *All four defendants stand trial together and the eviction
  blockades continue. Your consolidated chapters close ranks—but the
  Midtown `Conciliator` committee, whose clinic lease is due on Friday,
  faces an immediate rupture test: if their household and lease claims
  are unresolved, they will split from the coalition tonight and sign
  the foundation charter on their own.*
- **Sign the charter through a cutout and siphon the eighty thousand into
  the cold ("Take the Bait, Burn the Hook").** *Have the Midtown clinic
  director sign the mediation charter on paper, cash the foundation
  check, and route sixty thousand dollars via analog couriers (`Verb 3`)
  into the bail and safe-house reserve while the fourth defendant goes
  underground. If the foundation's auditors or the FBI trace the courier
  handoff, the clinic board goes to federal prison for wire fraud.*
- **Accept the settlement on the foundation's terms.** *Three cadres walk
  free, the fourth goes to state prison alone, the clinic gets eighty
  thousand dollars and two salaried NGO administrators (`+2 salaried_staff`),
  and the Promise Register bars eviction blockades in the county for six
  periods.*

**The seal.**

> *Staked: the fourth defendant, eighty thousand dollars, and whether
> Midtown stays in the organization. Unknown: whether Midtown's
> committee obeys discipline if you refuse, and whether the prosecutor
> already has a wiretap on the clinic's bookkeeper if you siphon the
> check.*

---

### Ceremony 8 — *The Leningrad Mandate (The Party Congress)*

**Trigger.** The Second Party Congress convenes. Your Northside chapter
has 180 rank-and-file members who built the communal kitchen and held
the picket line—but its three-person chapter committee was captured four
periods ago by a Right-Opportunist `Faction` tied to the union payroll.
All 6 of Northside's voting delegates have arrived at the Congress
mandated to vote *against* 1903 Rule 1 and *against* dissolving factions.

**Pane left.**

> **THE CREDENTIALS & FLOOR FIGHT — Second Congress, Day One**
>
> Northside's six voting delegates sit in a tight block at the back of
> the hall. Their spokesman, Kellerman—who also draws a salary from the
> municipal clerks' union—announces that Northside will walk out of the
> Party if the Congress outlaws factions or touches the union staff
> payroll.
>
> Your social investigation (`Verify`) shows that seventy percent of
> Northside's one hundred and eighty members never saw the resolution
> Kellerman is waving: he called the chapter delegate vote on a Tuesday
> afternoon when the factory shifts were at work, and stacked the room
> with union office staff.

**Options.**

- **Send three central emissaries straight to the Northside night-shift
  kitchen before tomorrow's roll call (*The Leningrad 1925 Move*).**
  *Hold the Congress vote open for twenty-four hours and spend scarce
  `Cadre Labor` to convene an emergency rank-and-file meeting at the
  Northside kitchen tonight. If the shop-floor members endorse the
  Central Committee's line, Kellerman's six mandates are revoked from the
  floor tomorrow morning—leaving him to submit or walk out alone.*
- **Settle the Northside kitchen's fuel debt, then put the anti-faction
  resolution to an immediate vote (*The Military Opposition Move*).**
  *Pay off the Northside kitchen's twelve-hundred-dollar winter heating
  arrears from the central treasury so the two honest shop stewards in
  Kellerman's delegation have no material grievance left, then call the
  roll to dissolve Kellerman's faction and expel anyone who refuses.*
- **Compromise with Kellerman in the hallway (`Conciliator` Trap).**
  *Drop the 1903 Rule 1 enforcement clause and let the union staffers
  keep their separate caucus in exchange for Northside's six votes on
  the main political report. The Congress closes in "unanimous unity,"
  and Kellerman's faction keeps every lever it brought into the hall.*

**The seal.**

> *Staked: Northside's one hundred and eighty members, Rule 1 discipline,
> and whether the union payroll owns a veto over the Party. Unknown:
> whether the gendarmes spot the extra twenty-four hours of Congress
> session, and whether Kellerman already has a press release drafted for
> the Corporate Feed if he loses.*

---

## 7. Builder-check rulings (author calls, 2026-10-26)

A builder-check review (`deepseek/deepseek-flash#high`) returned nine
architectural questions; all nine are settled here from existing canon
or as author calls:

- **R1. Two-layer collective node composition (`Room` vs. `Floor`):**
  Every collective organization node (both Party chapters and external
  Union Locals / Coalitions) carries two layers: (a) `leading_body`
  (`line_stance`, `salaried_staff`, and default delegate mandate control)
  and (b) `member_cohorts` (counted cohorts partitioned by `Investor` vs.
  `Consumer` and line allegiance, plus `shop_floor_edges`). Voting
  delegates are apportioned from `member_cohorts`, while their initial
  mandate follows `leading_body` unless flipped by the *Leningrad 1925*
  emissary action.
- **R2. Typed `CovenantPredicate` under the Promise Register:** Per the
  LLM fence ("only the engine judges mechanics; the LLM narrates only"),
  every `review_condition` in the Promise Register is a closed typed
  predicate over engine-observable actions and states
  (`ForbidPracticeInCounty`, `RequirePracticeByPeriod`, `RequireTransfer`,
  `RequireCoalitionEndorsement`, `MaintainPolemicStance`), paired with
  authored/narrated prose. Speech or marshaling covenants in ceremonies
  are narrative renderings of `MaintainPolemicStance` and practice
  posture flags.
- **R3. Antagonism stage is derived, never stored (`no stage += 1`):**
  Consistent with `2026-10-26-combat-design.md` C4, the 4-stage
  antagonism ladder (`FellowTraveller`, `ConciliatorBuffer`, `Faction`,
  `Antagonist`) is derived from observable graph/book predicates (e.g.,
  separate caucus/dues book $\Rightarrow$ `Faction`; active edge or
  accepted offer with a state/employer/corporate node $\Rightarrow$
  `Antagonist`). When rejecting a Wedge Offer advances a tendency, the
  engine writes the concrete state transition (opening a separate caucus
  or accepting the external buyout edge) from which the new stage is
  derived. Main-danger neglect weight is computed from
  `t_current - t_last_rectified(deviation_kind)` in the journal.
- **R4. A Congress is a single Decide-step ceremony (`Seal` is final):**
  Consistent with `2026-10-26-peacetime-economic-verbs-design.md` R2, a
  Congress never suspends the tick mid-execution. The player commits
  pre-vote floor actions (emissaries, grievance settlement, main-danger
  report) and selects the resolution inside the Congress ceremony
  *before* pressing `Seal`; roll-call votes, splits, purges, and the
  coalescing surveillance leak resolve deterministically during
  **Reckoning**. Calling `ConstituteParty` (`Key A`) is executed as the
  Founding Congress resolution rather than a standalone button.
- **R5. How `salaried_staff` and Purges interact with the 260-period
  clock:** `salaried_staff` counts paid personnel across all `Legal
  Institution` books controlled by or affiliated with the Party. Whenever
  `salaried_staff > cadre_count`, the legal shell holds veto weight in
  the Room and can force a Congress. Executing the *1921 Purge* or
  *Sending Staff into the Shops* slashes `salaried_staff` back below
  `cadre_count` and satisfies the anti-calcification condition on the
  260-period window.
- **R6. Losing a Congress or suffering a *Minsk 1898* arrest never ends
  the run:** Per `Porch 02` §6 ("No Fukuyama End of History"), if an
  unshielded Congress is swept by police (*Minsk 1898*), the central
  committee is arrested, the organization is demoted back to disconnected
  local circles, and play continues from surviving cold (`c`) and
  dispersed cells. If an opportunist faction wins a Congress roll call,
  the player chooses between **submitting as the minority** (organizing
  to retake the next Congress, as Lenin did after 1903) or **splitting
  immediately (*1912 Bolshevik Split*)** with only the loyal chapters.
- **R7. Split-offs and expelled factions become autonomous
  `OpportunistCellKind` / `ReactionaryCellKind` nodes:** Expelled
  factions and breakaways instantiate or merge into the existing Wave 3
  (`Task 6`) cellular-automaton nodes (`ProtestCircuitTrotskyist`,
  `DoctrinalSect`, `DsaSocialFascistBuffer`, `StrasseriteGrifter`), so
  their subsequent *August-Bloc* fracture and foundation-grant capture
  emerge from `Capacity::allocate` with zero scripted timers.
- **R8. Floor Fight choice vs. engine resolution:** In Move 2 / Ceremony
  6, walking out to form a breakaway union (`AntagonisticSplit`) is an
  explicit player option, while calling a Floor Fight vote is a single
  player option that the engine resolves into `Cave (Shift)`, `Ouster
  (Flip)`, or `Blocked -> Split` based on `shop_floor_support` vs.
  `salaried_staff`.
- **R9. Scope boundary with the Electoral screen:** Move 3's polemic
  stance governs cohort and `Supporter Labor` flows across coalition
  edges every period; electoral seat division (`CParty::GetVotingPowerFor`)
  applies only when an election resolves on the Electoral screen (Wave 5).
