# The County Review: design

**Status:** Draft for the Director's approval, 19 November 2026. The Director chose this approach on
18 November 2026 ("Option A is decided"). Nothing is built until this document is approved.

**Scope:** PER-366, the first playable slice of the class-agents lane. Wayne County only (county
geoid 26163).

**How to read the marks.** **[Director]** records a decision already made. **[Call]** is a choice
the author made that the Director can overrule. **[Ruling needed]** is a choice only the Director
can make; section 7 lists them with a recommended answer. Money is in game currency units and is
written with a dollar sign.

## 1. What this slice is for

The Director asked for the population to act: "I want to start factoring in the population of people
as classes, labor supply, hypergraphs", in order to "make this simulation very interesting and
entertaining, turn it into a game". Three rulings frame the work. The game is a politics simulation
built on an economic base. It is a class-based game. Its ideology sides with MIM.

Today nobody in Wayne County decides anything. The engine facts behind that sentence are in Appendix
A:

- The relief hearing of ADR299 happens once per campaign and has two fixed seats.
- The number of households behind each delegate is written into the scenario file. It is printed in
  the minutes and changes nothing.
- The county review in the following period only writes a record. No money moves.
- Nothing changes a county budget line after the opening.
- Only households the player's organizer has bound can spend hours on politics.
- Only the player's organization decides. The partners follow a fixed script.

The County Review makes the county's relief roll the stake. Each four-week period the county reviews
its roll in open session. Organizations bring motions. Each household that an organization has
reached works out from its own accounts whether the matter is worth its time, and comes or stays
home. The county then moves one household's worth of relief for each household that came, less those
who came to object, as far as its books allow. The next period's receipts show who gained, who paid,
who joined and who left.

## 2. One period at the table

### The county's books today

These figures come from the recorded run with seed 319. Appendix A names the files.

| Line | Per period | Paid |
|---|---|---|
| Provider grants (county-funded public administration sites) | $151,969,750 | First |
| Household support | $20,094,200 | Second |
| Spending limit (the sum of the two) | $172,063,950 | |

Household support is one **unit** for each job-seeking person. A unit is $280 a period: one period
of food at the opening price. That run pays 71,765 units.

In that run the county first runs short of cash in period 30. From then on household support is paid
nothing and the grants are only partly paid. Nothing scripts this.

### Wayne's household groups today

| Group (engine budget key) | Persons | Units of support | County support per period | Wages per period |
|---|---|---|---|---|
| Earning, nonowner | 1,196,610 | 38,837 | $10,874,360 | $238.3M |
| Earning, owner | 139,712 | 2,669 | $747,320 | $43.3M |
| No earner, nonowner | 375,449 | 26,538 | $7,430,640 | $0.02M |
| No earner, owner | 41,720 | 2,949 | $825,720 | $0 |
| Collective residence | 19,084 | 772 | $216,160 | $16.0M |

Persons, support and wages are recorded at period 4. Units are Derived here by dividing recorded
support by $280. The two earning groups receive 58% of the relief line.

The hearing scenario carves three small named groups out of these: relief claimants (2 households, 2
units, $560 a period), aid recipients (4 households, no county support) and aid donors (8 persons).

### What the player does in a period

1. **Reads the ledger and the roster.** The ledger shows the county's lines in the order they are
   paid, with what went unpaid last period. The roster shows the household groups.
2. **Chooses review work** as this period's practice, in place of aid or inquiry.
3. **Proposes a motion to the Claimants' Assembly.** A motion says which households it speaks for,
   what each of them asks, and where the money comes from. For example: "a unit for each no-earner
   household that has none, taken from all provider grants in proportion".
4. **Reads the preview.** For any number of households it shows who would gain, which lines would
   pay, which sites' staff would lose wages, and how much each household would lose.
5. **Spends organizer hours contacting households**: 2 hours each, out of 8.
6. **Advances the period.** Other bodies do the same by rule. Each reached household decides whether
   its stake is worth the time.
7. **Reads the ruling.** It gives the households for, the households against, the units moved, and a
   reason for every reached household that did not come.
8. **Reads next period's receipts.** They show which lines moved, which groups gained, which paid,
   and who joined, stayed or left each body.

The player's real choices are four. Whom to organize decides who gains. Where the money comes from
decides who pays, and whether the cost is spread thinly or lands on one office. When the county runs
short, the choice is whether to ask that the organized be paid first. Every period spent on review
work is a period not spent on aid.

### What a new player notices within ten minutes

- The county pays its own offices first and relief second.
- 58% of relief goes to groups that also have wages.
- A household comes only when the matter is worth its time, and every absence has a reason: not
  contacted, nothing at stake, not worth the time, no time, or a better offer.
- A cost spread thinly brings nobody out to object. A cost that lands on one office brings out its
  staff.

## 3. Goals, non-goals and anti-goals

**Goals**

1. Any Wayne household that a body reaches makes a real decision from its own accounts, and a
   receipt explains it. Households nobody reaches are counted as such.
2. The player has one consequential decision each period and sees the answer the next period.
3. Other organizations act on the same rules as the body the player leads. None is weakened or
   strengthened by hand.
4. Class position is read from accounts. MIM's reading is shown as a reading.
5. Membership becomes a record that only a household's own act can write.
6. Every rule is exact and repeatable: whole numbers, no random draws, no tuned cut-offs.

**Non-goals for this slice**

- Mass turnout. Organizing spreads only as fast as organizer hours allow. Section 6.7 gives the
  reason.
- Labor-force choices (keep looking, stop, start). Slice 2.
- Nation, legal status and the wage-against-value term on household groups. Slice 2.
- Solidarity, consciousness, hardening of class position, and the failure-mode readings.
- Tax motions, elections, other counties, coalition motions between bodies.

**Anti-goals: the slice has failed if it contains any of these**

- An approval bar, a mood meter or a heat map standing in for a decision.
- A class label that is assigned by hand and then drives behavior.
- Membership, agreement or consciousness inferred from aid, service use or a shared income source.
- An individual person simulated as an agent.
- An outcome decided by a label, or a rival made weaker or stronger by hand.
- A county that is only a scorekeeper with no accounts of its own.
- The game commenting on the player's line while play is under way.
- A rival that carries a real organization's name.

## 4. Rules this design must obey

| Rule | Source |
|---|---|
| Households are the smallest deciding unit. Groups are counted budget cohorts, "not source household counts or person agents" | ADR269 |
| "Partitions such as class position, core and periphery, or political alignment must emerge from composed material relations at a declared scale. Any claimed partition must include an invariance proof under its declared coarse-graining." | Constitution Article II |
| "An actor's material position and conceived interest remain distinct dimensions." | Constitution Article II |
| "aid itself creates no agreement, membership, consciousness or worker-hours." Agreement is "a separate explicit relation" | ADR270 |
| "A shared income source provides no evidence that residents belong to a single political organization." | ADR299 |
| The player is not the state and cannot legislate | Game Design Standard §2 |
| The player's choices are a closed list. ADR299 added the hearing invitation by ruling. One practice executes per organization per period, and old formats get no compatibility path | ADR262; ADR299 |
| Choices are a rank order under a budget. No threshold constant and no response curve | ADR184; AGENTS.md |
| Counts are split exactly, by largest remainder with a fixed tie order | staffing precedent (`proportional_shares`) |
| Random draws only through a finite kernel with a receipt | ADR248 |
| Sums are preserved when counts are pushed to a coarser scale | ADR296 |
| Attributed membership is ratified, but its payload is "Carried, empty, unhashed" and adding fields is a separate Director act | ADR189; ADR198 R4 |
| "Structure is the premise; magnitudes are earned." What the player knows never enters the turn's hash | ADR182 R2 |
| Every value is Observed, Derived, Calibrated or Designed, and says which | Game Design Standard, v4 addendum |
| "Any line is playable — including wrong ones — and the sim never editorializes mid-run." | Game Design Standard §2 |
| The game is proved by play, and every construct has a writer, a reader and a witness | Game Design Standard §6 and §9 |
| New decision rules get a rule entry with a role, an evidence class and an attribution row | AGENTS.md; `GOVERNED_RULE_ATTRIBUTIONS` |

## 5. Approaches considered

### The first slice

- **A. The County Review (chosen).** **[Director]** Who pays for relief. It gives the player a
  decision in one period and an answer in the next.
- **B. The Labor Ledger.** Who can afford to stop looking for work. It is needed and honest, but no
  organization competes for a group, results build over years, and it adds work to every county's
  turn. It becomes part of slice 2.
- **An election first.** Dropped as a first slice. Most groups would have nothing at stake and would
  abstain, and the repository holds no citizenship data to build the electorate. It becomes slice 4.

### Four choices inside A that the engine forced

Reading the engine after the Director's choice changed four things. Each is listed with what was
rejected.

**How the county decides.**

- *Each household present moves one unit, less the households present against, within what the
  county's books can carry (recommended).* **[Ruling needed]**
- *The side with more households present wins a motion for a named amount.* Rejected. The player's
  organizer reaches about four households a period. Four households could then move a million
  dollars. Stopping that would need a quorum, which is a tuned cut-off.
- *Weigh each side by the taxes its backers pay.* The author proposed this on 18 November and
  withdraws it. MIM's argument is that the majority supports the system because it represents the
  majority's interests (Appendix B). A tax-weighted county would say the majority wins because the
  scale is rigged, which is the position MIM rejects.
- *Move no money in this slice.* Smallest, but the player's decision would have no price.

**Which households have a stake.**

- *Treat each of the five large groups as one bloc.* Rejected. Every household in a group would get
  the group's average. The earning nonowner group has 38,837 units among 1,196,610 persons.
  Averaging would make the whole group act as if it were on relief. The sign of the average is not
  the sign for the households concerned, so the grouping fails Article II.
- *Count stake cells inside each group from the lines that pay its people (recommended).* **[Call]**
- *Split Wayne's five budgets into real sub-budgets.* Sounder, and the likely home of nation and
  legal status. It changes the opening economy and needs a rule for splitting every stock. It is
  slice 2.

**What kind of proceeding.**

- *Stretch the ADR299 hearing to many seats.* Rejected. The two seats are fixed in ten places in the
  contract (Appendix A), and the hearing happens once.
- *Keep the founding hearing as it is and add a recurring review session (recommended).* **[Call]**

**How far organizing reaches.**

- *Only organizer hours reach households (recommended for this slice).* **[Ruling needed]**
- *A member household also brings in the households it shares a workplace with.* Truer to how
  concentrated workers combine, and it would put thousands of households in the room. Section 6.7
  explains why it should wait.

## 6. The design

### 6.1 The unit and the roll

- A **unit** is the county's support for one person for one period. It is one period of food at the
  opening price, which is $280 in Wayne. The engine's own formula sets it. This design adds no
  amount of its own.
- The **roll** is the set of units the county pays. A **formula unit** is the one the opening gives
  each job-seeking person. A **won unit** is one a session adds.
- A household holds at most one won unit, and none if it already holds a formula unit. **[Call]**
- A motion never names an amount. The households present decide how many units move.
- County support is paid into a group's pooled budget, as it is today. The engine counts a group's
  won units. It does not track which household holds one.

### 6.2 Sessions

- The founding hearing of period 2 stays exactly as ADR299 built it, authored counts included.
  **[Call]** Rebuilding its two seats on the rules below would touch the contract in ten places for
  a number that changes nothing in play.
- The households the scenario records as authorizing each delegate (2 and 3 today) open as members
  of those two bodies. This is a Designed opening condition. No rule below reads the authored
  numbers again.
- Period 3 holds the first review session. Only the bodies that the signed minutes name as speakers
  may bring a motion to it, as ADR299 requires. If no minutes were signed, the first session is in
  period 4.
- From period 4 the county holds one session every period, and any body may bring one motion.
- A motion stands until its sponsor withdraws it.

### 6.3 Bodies and the county

A **body** is an organization that households can stand behind at a session.

| Body | Exists today | In this slice |
|---|---|---|
| Wayne Relief Claimants Assembly | Yes, a fixed actor with a captured mandate | The mass body the player leads. The player proposes its motion; reached households decide whether to stand behind it |
| The aid partners' delegation | Yes, a fixed script | Decides by rule. Its program is its existing claim: "Hear the cases of residents who received no county support." |
| A public-payroll council | No | A generic body, added in build piece 3. Its program is to object to motions that cost its members wages, and to ask for grants to be restored when they have lost wages. It carries no real organization's name |
| Wayne City PD | Yes, the state opponent | Unchanged. Its $24 line is not on the motion menu |
| Wayne County administration | No | New state actor. It rules on motions and pays by its books. It follows the City PD's pattern of configuration, decision receipt and outcome receipt |

**The player's seat does not change.** The player's organization, the Wayne Organizing Collective,
is not a body at the session. It leads the assembly: it proposes the assembly's motion and spends
its own organizer hours on contact. Households join the assembly, which is a mass body. Nobody
becomes a member of the player's own organization in this slice.

**The player never legislates.** The player proposes to a body, households decide whether to come,
and the county rules.

**Each body holds at most one motion and one standing objection**, and may not sponsor a motion that
its own objection covers.

### 6.4 Motions

A motion names three things: the households it speaks for, what each of them asks, and the lines the
money comes from. The menu is generated from the county's own table of lines.

| Form | Speaks for | Each household that comes asks | Money comes from |
|---|---|---|---|
| Enroll | Households of a named group that hold no unit | One unit added to the group's support line | All provider grants in proportion, one named grant, or all household support lines in proportion |
| Pay first | Households of a named group that hold a unit | Its unit paid in the county's first class, beside its offices | No line changes. When cash is short the cost falls on whatever the county then pays last |
| Restore | Households with a person employed at a grant-funded site that paid short last period | One unit returned to that site's grant | A named support line |
| Object (standing) | Households a motion would cost | Nothing. It comes to cancel | |

Two limits apply. No line may be reduced to zero or below, because the engine requires positive
amounts. The City PD's line is left alone, because the engine checks that exact row every period.

### 6.5 Who has a stake, and the preview

**The preview.** The preview takes a motion and a number of households. It replays the last closed
period's county payments, and the payroll of every site whose grant would change, with the motion in
force at that size. The difference from what really happened is each group's stake in money. It is
exact for the rules that exist: the county pays its lines in order until its limit or its cash runs
out, and a site pays each wage member only for the whole hours its cash covers.

Four limits are declared on screen. **[Call]**

- It looks at one period.
- It takes each motion alone.
- It counts money income only. It does not count county services a household would lose if an office
  cut its hours.
- The player sees the preview for the last period the player has seen close. Households decide on
  the period that has just closed when the session meets. The two agree unless the county's cash
  position changed in between.

The preview is something the player knows. It is never part of the turn's hash. No estimate is used:
a grant cut that a site's cash can absorb costs its staff nothing, and the preview says so.

**Stake cells.** A group's money stake is exact, but households inside a group differ in which
county line pays them. The engine holds, for each group, its households, its job-seeking persons,
and its persons employed through each staffing record. Each session sorts a group's households into
cells by two questions. Does the household hold a formula unit, a won unit or none? Is one of its
people employed at a grant-funded site, and which?

**The placement rule.** The engine counts persons, not which household each person lives in. This
slice places one such person per household until households run out, so two of them share a
household only when they must. This is Designed and declared on screen. It affects how many
households are counted, never how much money moves. **[Ruling needed]**

**Why this survives merging and splitting.** A cell contains only households paid by the same lines,
so every household in it has the same sign of stake. Splitting a cell changes no sign. Two cells
with different signs are never merged.

### 6.6 What a household does

Every rule below runs on counts of households, never on individuals.

| Step | What it reads | What happens | Rule |
|---|---|---|---|
| Is it reached? | Section 6.7 | An unreached household does nothing | Bodies decide whom to reach |
| What is at stake? | The motion, or the preview for its cell | For a sponsor's motion: what the motion asks for the household. For an objection: what the motion would cost the household, previewed at the size the sponsor's own supporters ask | Exact money |
| Is it worth the time? | The attendance hours and the wage | The household comes only if its stake is at least the attendance hours valued at the wage: 2 hours at $24, or $48 a period today | Derived from two existing numbers |
| Whom does it stand behind? | The stake under every body that reached it | The body whose position is worth most. On a tie, the body it stood behind last; failing that, the lower body identifier | Rank order |
| Can it come? | Its group's free hours from the period just closed | Each household present spends the attendance hours. If a group's hours run short, places are shared out and the rest are recorded "no time" | Exact largest-remainder split |

A household that does not come is recorded with one reason: not contacted, nothing at stake, not
worth the time, no time, or a better offer.

Four limits are declared, and each is the Director's to rule on.

- **A reached household does not free-ride.** A household gains from a motion whether or not it
  comes. This slice assumes that a household a body has reached treats the matter as its own.
  **[Ruling needed]**
- **A household reads only its own money and hours.** No rule here reads solidarity, consciousness,
  nation or a class label. Nobody comes for someone else's gain. Article II calls the gap between
  material position and conceived interest "a terrain of political struggle"; this slice models only
  the first of the two. **[Ruling needed]**
- **An hour is valued at the going wage for every household**, including a household that cannot
  sell one. **[Ruling needed]**
- **A household's own choice is the agreement ADR270 requires** before its hours are consumed.
  Charging any Wayne household on its own recorded choice needs a new path, because today only
  households bound to the player's organizer can be charged. **[Ruling needed]**

On the recorded run time is not scarce. The earning nonowner group has 128 million free hours in
period 2, and the two claimant households have 256. Reach is the scarce thing.

### 6.7 Reach

- **Contact.** A body spends organizer hours to contact households of a named cell. Each contact
  costs 2 hours, the scenario's existing contact cost.
- **Standing.** A household that stood behind a body at the last session is reached again at no
  cost.
- **Hours.** The player's organization has at most 8 hours a period from each contributor, as it
  does today. Each non-player body has 8 hours a period. **[Call]**
- **Non-player bodies choose by rank.** Each ranks the cells it could contact by what its position
  is worth to a household there, and contacts them in that order until its hours run out. Ties go to
  the lower identifier.

**What this means for scale.** A body reaches about four new households a period. A session in the
first year has tens of households in the room and moves thousands of dollars a period, out of a
county budget of $172 million. The five large groups are on the roster and in the ledger. Their
households act as they are reached. This slice is small on purpose.

**Why organizing does not spread through workplaces yet.** **[Ruling needed]** The alternative rule
is that a member household brings in the households it shares a workplace with. That is how
concentrated workers combine, and it would fill the room. It should wait for two reasons.

- A household here reads only its own money income for one period. At mass scale that rule would
  have the majority vote the county's office grants into payments to itself, because nothing in this
  slice counts what households would lose in county services.
- The county here has no interest of its own. It concedes whatever its books can carry. A county
  that defends its offices is slice 3 and slice 4 work.

At the scale of organizer hours neither gap can do damage. At mass scale both would decide the game.

### 6.8 How the county rules

At the end of the period the county administration rules on every motion on the table.

1. **It counts the households for.** These are the households present behind the sponsor that the
   motion speaks for.
2. **It previews the motion at that size.** That fixes what the motion would cost each cell, and so
   which reached households come to object.
3. **It counts the households against.** These are the households present behind a body whose
   standing objection covers the motion.
4. **It moves the difference.** If more came for than against, the county moves one unit for each
   household of the difference, as far as its books allow. If its books allow fewer, the receipt
   says how many and why. If no more came for than against, nothing moves.
5. **It takes motions in order of that difference,** larger first, with ties going to the lower
   motion identifier. Each is ruled on the table as the earlier ones left it.

When cash is short the county pays in its own order, exactly as the engine does today. There is no
special shortfall rule.

Changes rewrite the table at the end of the period and are paid from the next period's close.

This rule is Designed and provisional until the county board office arrives in slice 4. **[Ruling
needed]**

### 6.9 Membership

- A household becomes a member of a body by standing behind it at a session and spending the hours.
  Nothing else writes membership: not aid, not service use, not a shared income source. The two
  authored opening rolls of section 6.2 are the one exception.
- A member household that stands behind a different body at a later session moves to that body.
- A member household that does not come stays on the roll and is shown as absent. No timer expires
  membership, so there is no lapse threshold.
- The record for each group and body holds: member households, households present this session,
  hours spent, periods since joining, and the period's movement (joined, stayed, moved away,
  absent).
- A body's strength at a session is the households present, never the size of its roll.

**Where the record lives.** The session receipts are the first home of the roll. They are hashed
with the rest of the turn's records. Writing the same counts onto the membership links in the graph
is the hypergraph step the Director asked for. It is its own build piece, because it needs a
Director act (ADR198 R4 calls adding payload fields "a SEPARATE, LATER CEREMONY") and an accessor in
the upstream graph library (hypergraph-rs issue 2). **[Ruling needed]**

### 6.10 Class reading

- Each group shows a **livelihood profile**, Derived from its accounts: wages, ownership income,
  public support, mutual aid, and hours sold, protected, unpaid and free.
- Each group shows **MIM's reading** as a reading, marked Designed and never shown as Derived. A
  wage-earning group reads "labor aristocracy (MIM reading; value term pending)". A group with no
  earner shows its labor counts and is never called "workers". The owner split stays a provenance
  note, as ADR269 requires.
- Nation shows as "pending" on every group. **[Ruling needed]**
- The class reading is displayed. No rule in this slice takes it as an input.

### 6.11 What the player sees

Four views, none of which exists in the client today.

| View | Answers | Source |
|---|---|---|
| County ledger | Which lines are paid first, and what went unpaid? | Public budget receipts, which exist |
| Group roster | Who lives here, how do they make a living, how many units do they hold? | Household period reports, which exist |
| Who gains, who pays | What would this motion do at this size, and to whom? | The new preview |
| Session record and membership roll | Who came, for whom, who did not and why, what did the county move, who joined and left? | The new session receipts |

**Structure is public; magnitudes are earned** (ADR182 R2). The county's lines, the motions and the
ruling are public record. For a cell the player's organization has not contacted, the views show
which side of a motion the cell is on but not the amounts or the hours, and state the remedy:
contact them. **[Call]**

### 6.12 State, order in the turn, and where the rules live

**New records**, all hashed with the turn except the preview:

- the session: motions on the table, each with its sponsor, and each body's standing objection;
- each body's contacts and the organizer hours spent;
- each cell's choice: reached, standing behind which body, present, or the reason it did not come,
  with hours charged;
- the county's ruling: households for and against each motion, units moved, and what the books
  refused;
- the amended table and each group's won units. The engine already stores the table in the turn's
  state and has room for it to change; nothing writes it today.

**Order in the turn.** Posting, contact, choices and attendance run in the organizer step, where the
hearing runs today, after the period's financial close. The ruling runs in the schedule's reserved
policy slot, which nothing uses yet. Payment under the amended table happens in the next period's
close.

**Where the rules live.** Each new rule is a thin rule entry that calls a native operation, as the
organizer and City PD rules do today, with its role, evidence class and attribution row. The numbers
stay in the scenario's defines file.

**Evidence classes.**

- Observed: group persons and households.
- Derived: the unit ($280), the worth-the-time floor ($48), stakes, cells, the livelihood profile,
  counts present.
- Designed: one session each period; the unit as the measure of what the county concedes; one won
  unit per household; valuing an hour at the wage; no free riding; the placement rule; non-player
  bodies' 8 hours; tie orders; the county's ruling rule; the two opening rolls; the MIM reading
  text. The attendance hours and the contact hours are existing Designed values.
- Calibrated: none.

### 6.13 Quantities that must balance

- For each group and session: households reached = households standing behind some body + households
  that declined, each with a reason. Standing behind = present + no time. Unreached households are
  untouched.
- Hours charged = households present x attendance hours, and never more than the group's free hours.
- For each motion: for and against are sums of households present, never written-in numbers.
- Units moved = the smaller of (for less against, or zero) and what the books allow.
- Money: units moved x the unit leaves the source lines and enters the target line, to the last
  millionth. The total of the table does not change.
- Every line stays above zero, and the total is no higher than the spending limit.
- A group's won units are never more than its households that hold no formula unit.
- For each body: members next session = members + joined - moved away, and never more than the
  households in the group.
- Persons, employment and the household lifecycle are untouched.
- No random draw anywhere. The same inputs give the same receipts and the same hash.

## 7. Rulings needed

Each needs a decision record. The recommended answer is the author's.

| # | Question | Recommended answer |
|---|---|---|
| 1 | By what rule does the county decide? | Each household present moves one unit, less the households present against, within what its books can carry. Provisional until the county board office |
| 2 | May a county review session change the county's budget lines? ADR299 says "The county's ordinary fiscal accounts continue to determine payments." | Yes, through a record that partly supersedes ADR299: only the county administration's ruling changes a line, only within the spending limit, only through a motion on the table |
| 3 | What does a household's choice read? | Only its own money and its own hours. No solidarity, consciousness, nation or class term in this slice |
| 4 | When does a reached household come? | When its stake is worth at least the attendance hours at the going wage ($48 today). It does not free-ride |
| 5 | How far does organizing reach? | Organizer hours only in this slice. Spread through workplaces waits until households count lost services and the county defends its offices |
| 6 | May any Wayne household be charged attendance hours on its own recorded choice? | Yes. The choice receipt is the independent agreement ADR270 requires |
| 7 | May the organizer gain one new choice, review work? | Yes, by a record in the manner of ADR299. It is one practice in the period, in place of aid or inquiry |
| 8 | May a household's own act write membership, and will the Director open the payload ceremony in this lane? | Yes to both. Fields: member households, households present, hours, periods since joining, movement |
| 9 | How are persons placed into households when cells are counted? | One per household until households run out, declared on screen. Stacking them into as few households as possible is the other bound |
| 10 | What class text and nation text appear on screen? | "labor aristocracy (MIM reading; value term pending)", marked as a reading; nation "pending". Naming the settler nation (ADR171 open question 8) can wait for slice 2 |
| 11 | Approve the Designed values of section 6.12 and the generic public-payroll council | As listed |

## 8. Build order and proof

The slice is larger than the sketch the Director chose from. The engine has no recurring proceeding,
no attendance by households the organizer has not bound, no change to a budget line after the
opening, and no organization that decides besides the player. Each piece below can be played or
checked on its own.

| Piece | What it adds | How it is proven |
|---|---|---|
| 1. The ledger and the preview | The county ledger, the group roster, and "who gains, who pays" for motions that draw on support lines. Read-only: no rule and no stored state changes | The preview for a motion at a given size equals the difference between two real closes of the same period, one with the amended table and one without |
| 2. Review sessions | Recurring sessions, Enroll motions that draw on support lines, contact, household choices, the county's ruling, the amended table, the roll. Bodies: the assembly and the aid partners | The balances of section 6.13 as property tests. Three witness openings that differ only in starting conditions: units moved in full, units cut back by the books, units cancelled by objectors. Replay and reopen give the same hash |
| 3. Grants on the table | Motions that draw on provider grants, the payroll preview, Pay first, Restore, and the public-payroll council | A draw spread across every grant costs no household $48 and brings no objector. The same draw on one small office does. Nothing in the council's rules differs from the assembly's |
| 4. Membership in the graph | The roll written onto membership links, with its hash section | The graph counts equal the session receipts every period. The new hash section is absent when empty, so no existing hash moves |

**Play proof for the whole slice.** Three recorded playthroughs from the same seed, each run past
the period in which the county runs short. They differ only in the player's line: organizing
no-earner households that hold no unit, organizing earning households, and aid with no motions. They
must produce three different records that the receipts explain. The tutorial chapter that walks a
new player through the first session is the acceptance script.

## 9. Left to the builder

- The names and shapes of the new records and of the review-work practice, within ADR262's rule of
  one practice per period.
- Whether the county administration is a graph node like the City PD or a register only.
- How the preview is factored out of the public funding loop and the payroll rule, and whether it
  replays a whole close or only the parts a motion touches. The proof in section 8 holds either way.
- How a Pay first unit is stored as a line in the county's first class.
- Where the four views sit in the client, and the projection that feeds them. Single Wayne reads
  take 9 to 12 seconds today, so the views need their own projection.
- Version bumps for the organizer formats.
- The exact wording of on-screen text, within section 6.10.

## 10. After this slice

- **Slice 2: who can show up.** Wayne's budgets split into real sub-budgets, so that a cell has
  accounts of its own. Labor status as a group decision. Nation, legal status and the
  wage-against-value term on groups.
- **Slice 3: masses and rivals.** Organizing that spreads through workplaces. Households that count
  the county services they would lose. Tax motions, where a ratepayers' body can offer the majority
  a gain paid for by claimants. Opening rolls from observed union membership. The settler reading
  taken from each organization's record. Coalition motions.
- **Slice 4: the county board.** An office whose decisions are these same budget lines, a county
  with an interest of its own, an electorate with its exclusions counted, and "Don't vote, organize"
  as a playable stance.
- **Slice 5: beyond Wayne.**

## 11. Known risks

- **The slice may feel small.** Tens of households and thousands of dollars, beside groups of a
  million. That is the honest scale of 8 organizer hours. The large groups show on the roster and
  ledger; they do not yet move as masses.
- **Rivalry is thin while the county is flush.** Two bodies can offer the same unit, and a household
  then stays with whoever reached it first. The staff of county offices have no stake until a motion
  costs them wages worth the time. Opposition appears when a cost is concentrated, and when the
  county runs short.
- **Every body opens with almost no members.** That is even-handed and unlike life, where public
  payroll is already organized. Opening rolls from observed union data are slice 3.
- **Money is pooled, and may not buy food.** A won unit is paid into the group's pooled budget. In
  the recorded run about half of every group's food need goes unmet in period 4, in the same
  proportion in every group, so that shortage is not one that relief money alone would fix. This
  slice changes who is paid. What the money buys depends on the rest of the economy, and the
  receipts must report it without flattering the player.
- **Stakes are short-sighted.** A grant cut that a site's cash absorbs this period may cost wages
  some periods later, and the one-period preview will not show it.
- **The cash-short pay order is arbitrary.** When the county is short it pays grant-funded sites in
  identifier order, each in full, until the cash runs out. Which site's staff lose wages therefore
  depends on an identifier. This slice previews that rule faithfully and does not change it.
- **Household counts rest on the placement rule.** Money is exact. Counts of households in a cell
  are Designed until slice 2.
- **Turn time.** A national turn already takes 7 to 19 seconds, with a budget of 30. The Wayne-only
  work is small, but it has not been measured.
- **The recorded figures come from one seed.**
- **The format has no compatibility path.** Changing the organizer records resets saved campaigns,
  as ADR262 intends.

## Appendix A: Engine facts

Verified by the author by reading the code or the recorded data:

- County payments: for each public account the limit is the lower of the spending limit and cash
  above the floor, and each line is paid the lower of its amount and what remains, in list order
  (`rust/crates/babylon-material-circuit/src/financial/close.rs:100-134`).
- Payroll under scarce cash: a wage member attends the lower of planned hours and the whole hours
  the site's cash covers, and is paid at once
  (`rust/crates/babylon-material-circuit/src/payments/attendance.rs:365-388`).
- Household support is job-seeking persons times one period of food at the opening price
  (`rust/crates/babylon-persistence/src/national_economy/opening/financial.rs:126-145`).
- A staffing member is a part of a household group with a labor force that is the sum of its
  employed and job-seeking persons
  (`rust/crates/babylon-material-circuit/src/staffing/members.rs:15-116`).
- The household flow holds opening and closing households for each group
  (`rust/crates/babylon-persistence/src/observer_reader/household.rs:82-83`).
- Scenario numbers (`content/scenarios/national/defines.toml`): wage $24 an hour; wage tax and
  operating-income tax 15%; `contributor_hours_cap = 8`; `contact_hours = 2`; the hearing's
  `attendance_hours = 2`, period 2, review period 3, authorizing households 2 and 3.
- The player's choices are `Inquiry`, `Collect`, `LocalAid`, `RemoteAid`, `Reinforce`, `Hold`,
  `PauseStanding`, `ResumeStanding` and `InviteToHearing`
  (`rust/crates/babylon-practice-contract/src/organizer/types.rs:121-131`).
- The City PD line is `AMOUNT = 24_000_000` millionths, in the first class, and raises the limit of
  the public account it is attached to by the same amount
  (`rust/crates/babylon-persistence/src/national_economy/city_pd.rs:25`, `:197-258`). The recorded
  limit above is exactly the sum of the two lines shown, so it does not include that line.
- The Game Design Standard's v4 addendum lists "Article V vocabulary authority status: superseded"
  (`docs/superpowers/specs/2026-07-29-game-design-standard-design.md:34`).
- Recorded data, all from campaign `5efafb84`, seed 319, in
  `reports/economic-flows-qualification-2026-11-14-assets/`: the county's figures
  (`wayne-public-allocations.json`); group persons, support, wages and unmet food at period 4
  (`wayne-p4-households.json`); free hours of the earning nonowner group at period 2
  (`wayne-household-period-2-v10.json`). Units were computed with `python3 -I` as
  `household_income_support_micros / 280000000`; every quotient is a whole number and they sum to
  71,765. Unmet food is 50.8% of persons in each of the five large groups.
- The claimant and aid-recipient figures come from `wayne-hearing-three-choices.json` in the same
  directory, which names no campaign.

Reported by five read-only readers on 18 November 2026 and not all re-read by the author:

- The hearing's two seats are fixed in ten places in
  `rust/crates/babylon-practice-contract/src/organizer/hearing.rs` and its callers. One hearing per
  campaign. The review only writes a record.
- Only a household bound to the organizer and listed in a participant's commitments can be charged
  hours (`rust/crates/babylon-tick/src/material_world/organizer_time.rs`).
- The organizer contract has one controlled actor and fixed partners with scripted responses.
- Provider grants go only to public administration sites, are set once at the opening, and reach a
  site before payroll in the same close.
- No code changes a budget line after the opening. The City PD check requires its exact row every
  period.
- The only state actor today is the City PD. No county administration exists.
- The schedule has reserved slots named electoral and policy that no rule uses
  (`rust/crates/babylon-tick/src/phase_order.rs`). The organizer step runs after the period's
  financial close.
- The membership payload is an empty marker. The upstream gap is hypergraph-rs issue 2.
- The client has no ledger, roster or membership view.
- Turn times and Wayne read times are in `reports/economic-flows-qualification-2026-11-14.md`.

## Appendix B: MIM's line on the points this design leans on

All from the fact-checked findings in `docs/gameplay/research/40-class-agents-evidence.jsonl`.

- The majority backs the system because it pays them: "The majority of white Amerikans support or
  participate in the electoral system." (finding mim F15)
- Small local wins are possible: "It is possible that in elections to city hall, some small battles
  can be won locally" (mim F14).
- Public payroll anchors the labor aristocracy: "the government sector is the ultimate expression of
  the imperialists' loyalty to the oppressor nation working class" (mim-class-structure MC-21).
- What the majority wants back: "They just want their goodies back like in the old days of
  imperialism." (mim-on-other-lines F05)
- Reform at its most effective: "it turns the oppressed into oppressor instead of abolishing both"
  (mim-class-structure MC-24).
- The main danger: "This 'right opportunism' is the main danger in the party-building process in the
  world." and "if you're an organization in the First World and have a large following you stand for
  bourgeois ideals." (mim-practice F21)
- Relief is subordinate: MIM "believes that as a strategy charity can never provide more than
  temporary and limited relief." (mim-practice F07)
- People nobody has organized do not act: "They cannot represent themselves, they must be
  represented." (Marx, Eighteenth Brumaire ch. 7, quoted in research note 40, section 4)
