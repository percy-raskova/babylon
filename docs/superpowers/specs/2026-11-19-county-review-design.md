# The County Review: design

**Status:** Third draft, 19 November 2026, for the Director's approval. It replaces the draft that
failed review earlier the same day. Nothing is built until this document is approved.

**Scope:** PER-366, the first playable slice of the class-agents lane. Wayne County only (county
geoid 26163).

**How to read the marks.** **[Director]** records a decision the Director has made. **[Call]** is a
choice the author made that the Director can overrule. **[Record needed]** marks a choice that must
be written into a decision record before it is built; section 8 lists them. Money is in game
currency units and is written with a dollar sign.

## 1. What this slice is for

The Director asked for the population to act: "I want to start factoring in the population of people
as classes, labor supply, hypergraphs", in order to "make this simulation very interesting and
entertaining, turn it into a game". Three rulings frame the work. The game is a politics simulation
built on an economic base. It is a class-based game. Its ideology sides with MIM.

Today nobody in Wayne County decides anything. The engine facts behind that sentence are in Appendix
A.

- The relief hearing of ADR299 happens once per campaign and has two fixed seats.
- The number of households behind each delegate is written into the scenario file. It is printed in
  the minutes and changes nothing.
- The county review in the following period only writes a record. No money moves.
- Nothing changes a county budget line after the opening.
- No action reaches a household. The organizer's contact hours go to partner organizations.
- Only the player's organization decides. The partners follow a fixed script.

The County Review makes the county's relief roll the stake. Each four-week period the county reviews
its roll in open session. A household that has been reached works out from its own accounts whether
the matter is worth its time, and comes or stays home. The county counts each household in the room
by the wage tax it pays, and moves relief inside a fixed pot. Every household that comes brings one
more. Outside the county's room, the aid partners run food with their own hours. The next period's
receipts show who gained, who paid, who gave hours to which body, and who was in the room and not
counted.

## 2. What the Director has decided

| Date | Subject | Decision |
|---|---|---|
| 18 Nov | The first slice | The County Review: "Option A is decided" |
| 19 Nov | The county | "Defends its own, weighs by tax". Office and police money is off the table. The review moves relief only inside a fixed pot. A household counts by the wage tax it pays the county, not as one head |
| 19 Nov | Spread | "Each one brings one". A household that came brings one more household in the same position to the next session |
| 19 Nov | Why a household comes | "Own money, if worth the time". It comes when the matter changes its own income by at least two hours at the wage ($48 today), and never for someone else's gain |
| 19 Nov | The second road | "Both roads". A household that gives its own hours to the aid partners' work also goes on that body's roll. Receiving aid never does |

The Director also ruled that the game's ideology sides with MIM, and that MCU and FRSO are settler
organizations opposed to MIM's line. Neither is a source for method here.

**What changed since the last draft**

- The county no longer counts heads, and no claim can reach the money for its offices or its police.
- Relief won lasts one period. It is paid again only if the households come again.
- The organizer has 2 hours a period, which is one contact. Growth comes from each household that
  came bringing one more.
- "Pay first", "Restore" and the public-payroll council are gone.
- A household's stake is always money it would actually be paid, or actually lose.
- The aid partners have a roll of their own, written by hours given on food runs.
- Collective residence takes no part, because the engine gives it no households.

**The author's calls, for the Director to check while reading**

1. How "weighs by tax" becomes a rule: a household's count is its wage tax divided by the average
   household's (sections 6 and 7.4). On 19 November the author told the Director a different rule.
   Section 6 says why it changed.
2. A household that pays no wage tax still comes when the matter costs it $48, and is in the room
   uncounted (section 7.5).
3. When the county cannot pay the whole pot, every unit is cut by the same share (section 7.1).
4. Neither body has an organizer of its own. Nothing starts at the county unless the player starts
   it, and nothing the player starts can be called back (sections 7.3 and 7.6).
5. Each household that came spends 2 more hours to bring the next one, the same cost as the
   organizer's contact (section 7.6).
6. The second road is the smallest true version: at most four households a period (section 7.8).
7. The county publishes its cash balance at each session (section 7.11).
8. Job-seekers are placed one to a household when positions are counted (section 7.2).

## 3. One period at the table

### The county's books

These figures come from the recorded run with seed 319. Appendix A names the files. A campaign that
a player starts also carries the City PD's $24 line in the first class.

| Line | Per period | In this slice |
|---|---|---|
| First class: grants to public administration sites | $151,969,750 | Off the table. No claim can touch it |
| Relief pot: household support | $20,094,200 | The only money the review can move |
| Spending limit (the sum of the two) | $172,063,950 | Unchanged |

Household support is one **unit** for each job-seeking person at the opening. A unit is $280 a
period: one period of food at the opening price. The recorded run pays 71,765 units. This document
calls that list of units the **old roll**.

The county's cash in that run starts at $344 million and peaks near $1,151 million after period 3.
From period 4 the county takes in less than it pays out. Its cash falls by $18 million in period 4,
$34 million in period 10 and $56 million in period 29. At the close of period 29 it holds $149.5
million, which is less than its first class. From period 30 it pays its offices in part and pays no
relief at all. Nothing scripts this.

### Wayne's households

| Group (engine budget key) | Persons | Households | Units on the old roll | Wage tax per household, period 4 |
|---|---|---|---|---|
| With earnings, no business ownership | 1,196,610 | 456,528 | 38,837 | $78.29 |
| With earnings, with business ownership | 139,712 | held by the engine, not in the recorded files | 2,669 | about $122, if households are the size of the first group's |
| No earner, no business ownership | 375,449 | as above | 26,538 | about one cent |
| No earner, with business ownership | 41,720 | as above | 2,949 | $0 |
| Collective residence | 19,084 | none, by an engine rule | 772 | takes no part |

Persons, support and wages are recorded at period 4. Units are recorded support divided by $280.
Wage tax is 15% of recorded wages, computed by the author; the engine's own tax receipts are not in
the recorded files.

The scenario also carves out three small named groups: relief claimants (2 households, 2 units), the
aid partners' households (4 households, no unit, no wages, no cash), and the organization's own
households (4 households, 4 of 8 persons employed, no unit).

A household's **count** at the county is its wage tax divided by the average Wayne household's wage
tax. On the figures above a household in the first group counts as about 1.2 and one in the second
as about 1.9. Both figures rest on the household-size assumption in the table. A household in either
no-earner group counts as nothing.

### What the player does in a period

1. **Reads the county ledger.** It shows the pot the county has announced for next period, the
   county's cash, and what went unpaid last period.
2. **Reads the roster and the rolls.** The roster shows each household position: how it makes a
   living, whether it is on the old roll, and what it counts for if the player has a contact there.
   The rolls show who gave hours to each body last period.
3. **Chooses one practice,** as today. The new choice is a **review contact**: the organizer spends
   the period's two hours to reach one household in a named position. The existing choices remain:
   run food to the aid partners, collect, inquire, hold.
4. **Reads the preview** before choosing. For a position where the player already has a contact, it
   shows what the next session would do if one more household there were reached.
5. **Advances the period.** The accounts close and the county holds its session.
6. **Reads the session record.** It gives who came for and against, what each counted for, what the
   county granted and refused, and a reason for every reached household that stayed home.
7. **Reads next period's receipts.** They show which lines were paid, which positions gained and
   which paid.

### What the first two years look like on the recorded figures

This is a calculation from the recorded figures under the rules of section 7. It is not a recorded
result.

Suppose the player reaches one household "with earnings, no business ownership, no job-seeker" in
period 3, and does nothing else at the county. Such a household counts as more than 1 on the figures
above, so each asks for a whole unit.

| Session | Households in the room for the claim | Relief moved to them, per period | What each unit on the old roll loses |
|---|---|---|---|
| 4 | 1 | $280 | less than a cent |
| 10 | 64 | $17,920 | $0.25 |
| 14 | 1,024 | $286,720 | $4.00 |
| 17 | 8,192 | $2,293,760 | $31.96 |
| 18 | 16,384 | $4,587,520 | $63.92 |
| 20 | 65,536 | $18,350,080 | $255.70 |
| 21 | 131,072 | $20,094,200, the whole pot | $280, all of it |
| 23 to 28 | 417,691, every such household | $20,094,200 | $280 |
| 29 | The county announces no relief for period 30 | | |

- Through session 17 nobody on the old roll loses as much as $48, so nobody comes to defend it.
- At session 18 each unit would lose $63.92. Households on the old roll that have been reached start
  to come. Those with no wage are in the room and count as nothing.
- From session 21 there are more households in the room than the roll has units, and they share the
  pot. At session 23 each of 417,691 households is paid $48.11 a period. The job-seekers the pot was
  for are paid nothing.
- At session 29 the county holds less cash than its first class costs. It announces a pot of zero.
  Nobody has anything at stake, and the room empties.

The player can change this course in three ways: by never opening that position, by opening a
different one, or by reaching households on the old roll before the claim grows. Section 7.7 shows
how little the third can do once the claim is large.

### What a new player notices within ten minutes

- The county pays its own offices and police first, and no claim can touch that money.
- The county counts a household by the wage tax it pays. A household with no wage counts as nothing,
  whether it is in the room or not.
- A household comes only when the matter is worth its time, and every absence has a reason.
- Relief won lasts only while the households keep coming.
- One contact becomes two households, then four, then eight.
- The aid partners can feed four households a period, and the ones who turn out for the food are on
  its roll.

## 4. Goals, non-goals and anti-goals

**Goals**

1. Any Wayne household that has been reached makes a real decision from its own accounts, and a
   receipt explains it. Households nobody has reached are counted as such.
2. The player has one consequential decision each period and sees the answer the next period.
3. The county is an actor with an interest of its own. It protects its first class, and it counts
   those who pay in.
4. Class position is read from accounts. MIM's reading is shown as a reading. With nation absent,
   nothing in this slice is presented as MIM's base.
5. A body's roll is written only by a household's own hours: at the county's session, or on a food
   run.
6. Every rule is exact and repeatable: whole numbers and exact fractions, and no random draws.

**Non-goals for this slice**

- Rival organizers. Only the player's organizer opens a new position.
- Production by an organization: a kitchen or garden staffed by members' hours.
- Labor-force choices (keep looking, stop, start).
- Nation, legal status and the wage-against-value term on household groups.
- Solidarity, consciousness, hardening of class position, and the failure-mode readings. No
  household acts for another's gain.
- Businesses as a body at the county, tax motions, elections, other counties.

**Anti-goals: the slice has failed if it contains any of these**

- An approval bar, a mood meter or a heat map standing in for a decision.
- A class label that is assigned by hand and then drives behavior.
- Membership, agreement or consciousness inferred from receiving aid, from service use or from a
  shared income source.
- An individual person simulated as an agent.
- An outcome decided by a label or by the order of identifiers.
- A claim that reaches the money for the county's offices or police.
- A county that is only a scorekeeper with no accounts of its own.
- The game commenting on the player's line while play is under way.
- A body that carries a real organization's name.

## 5. Rules this design must obey

| Rule | Source |
|---|---|
| Households are the smallest deciding unit. Budget groups are a Designed allocation of county totals. They are not counts taken from a source, and not person agents | ADR269; ADR298 |
| "Partitions such as class position, core and periphery, or political alignment must emerge from composed material relations at a declared scale. Any claimed partition must include an invariance proof under its declared coarse-graining." | Constitution Article II |
| "An actor's material position and conceived interest remain distinct dimensions. Their gap is a terrain of political struggle." | Constitution Article II |
| "All material effects become next-period intents and enter only the next four-week causal interval." | Constitution Article III |
| "aid itself creates no agreement, membership, consciousness or worker-hours." | ADR270 |
| "A shared income source provides no evidence that residents belong to a single political organization." | ADR299 |
| The player is not the state and cannot legislate | Game Design Standard §2 |
| "One practice executes per organization per period." Old formats get no compatibility path | ADR262 |
| An organization owns its budget. It ranks what it could do "by yield per unit spent" and funds "down the list until the money runs out". What it declines is recorded with the shortfall | ADR184 |
| "The first state opponent must have its own authority, objective, resources, and partial knowledge". A state actor gets no "heat scalar, primitive or fixed political-response curve" | ADR291 |
| "A rule cannot impose a sigmoid or a second fixed response curve." | AGENTS.md; ADR172 ruling 5 |
| New content vocabulary needs "the applicable Director ceremony, schema and conformance updates, and a recording ADR". It needs no amendment | Constitution Article VIII |
| Counts are split exactly, by largest remainder with a fixed tie order | staffing precedent (`proportional_shares`) |
| Random draws only through a finite kernel with a receipt | ADR248 |
| Sums are preserved when counts are pushed to a coarser scale | ADR296 |
| Attributed membership is ratified, but its payload is empty, unhashed and unread, and filling it is a separate Director act | ADR189; ADR198 R4; PER-44 |
| "STRUCTURE IS THE PREMISE; MAGNITUDES ARE EARNED". What the player knows never enters the turn's hash | ADR182 R2 |
| Every value is Observed, Derived, Calibrated or Designed, and says which | Constitution Article IV |
| "Any line is playable — including wrong ones — and the sim never editorializes mid-run." | Game Design Standard §2 |
| Every construct has a writer, a reader and a sentinel. A construct that lacks one gets a recorded disposition | Game Design Standard W.1, W.2 |
| Every view states its decision question, signals, fog, actions, receipts and Archive links | Constitution Article VII |
| Claims of emergence are proved with "control and shock twins, counterfactuals, and mutation tests that sever causal links", "deterministic replay, and a direct-write audit" | Constitution Article VIII |
| The game is proved by play: recorded playthroughs kept as seed, action log and result | Game Design Standard §6 |

## 6. Approaches considered

### The first slice

- **A. The County Review (chosen).** **[Director]** Who gets relief, and who decides. It gives the
  player a decision in one period and an answer in the next.
- **B. The Labor Ledger.** Who can afford to stop looking for work. It is needed and honest, but no
  organization competes for a group, results build over years, and it adds work to every county's
  turn.
- **An election first.** Dropped as a first slice. Most groups would have nothing at stake and would
  abstain, and the repository holds no citizenship data to build the electorate.

### The county's rule

The Director was shown three rules on 19 November and chose the second. **[Director]**

- *Defends its own, counts heads.* The author's recommendation. Not chosen.
- *Defends its own, weighs by tax (chosen).* A household counts by the wage tax it pays. Households
  that pay nothing in cannot move the county. This is the closest of the three to MIM's "The ballot
  power of the oppressed is not greater than the financial power of the capitalists." (Appendix B).
- *Counts heads, with office grants on the table.* The first draft. The county had no interest of
  its own, and reform always worked.

### How "weighs by tax" becomes a rule

The ruling says a household counts by its wage tax. It does not say how a count turns into relief.
Three readings were worked through. **[Call]** **[Record needed]**

- **Count by share of tax (chosen by the author).** A household's count is its wage tax divided by
  the average Wayne household's wage tax. A household that pays the average counts as one head.
  Everything else is the head-count rule the Director was shown: each household in the room moves
  one unit, less those against. If every household paid the same tax, this would be the head-count
  rule exactly. It depends on shares of tax, not on amounts, so it still works when wages fall.
- **Refund.** Each household in the room gets back the wage tax it paid, up to one unit. On 19
  November the author told the Director the rule would be this one. Worked through, it fails. In the
  recorded run the largest group's wage tax per household is $401 in period 2, $78 in period 4 and
  $42 in period 14. Below $48 nobody comes. The review would empty within about a year, with a few
  thousand households in the room and about 1% of the pot moved. It also ties a relief dollar to a
  tax dollar, which the ruling did not say.
- **Rank.** The county fills the roll in order of wage tax paid. Rejected. A household that pays one
  cent would outrank every household that is absent, and the engine's pooled averages give the
  no-earner group about a cent a household.

### Spread

- *Each one brings one (chosen).* **[Director]** The rate is Designed.
- *Organizer only.* One new household a period. Not chosen.

### Why a household comes

- *Its own money, if worth the time (chosen).* **[Director]**
- *Its own money, either way.* The author's recommendation. Not chosen.
- *Not until consciousness is ruled.* It would stop the lane. Not chosen.

### The second road

- *Both roads (chosen).* **[Director]**
- *County review only, labelled as the reform road.* Not chosen.

### Two choices the engine forced

**Which households have a stake.** **[Call]**

- *Treat each large group as one bloc.* Rejected. Every household in a group would get the group's
  average. The first group has 38,837 units among 456,528 households. Averaging would make every
  household in it act as if it held a twelfth of a unit, when in fact some hold a unit and can only
  lose, and the rest hold none and can only gain.
- *Count positions inside each group (chosen).* A group's households are split by whether they are
  on the old roll. Section 7.2.
- *Split Wayne's budgets into real sub-budgets.* Sounder, and the likely home of nation and legal
  status. It changes the opening economy and needs a rule for splitting every stock. It belongs to a
  later slice.

**What kind of proceeding.** **[Call]**

- *Stretch the ADR299 hearing to many seats.* Rejected. The two seats are fixed in ten places in the
  contract, and the hearing happens once.
- *Keep the founding hearing as it is and add a recurring session (chosen).*

## 7. The design

### 7.1 The unit, the old roll and the pot

- A **unit** is the county's support for one person for one period. It is one period of food at the
  opening price, which is $280 in Wayne. The engine's own formula sets it. This design adds no
  amount of its own.
- The **old roll** is the list of units the opening gives each group: one for each job-seeking
  person. The county keeps this list for the whole run. Every session starts from it.
- The **first class** is every line on the county's account that is not household support: the
  provider grants and, in a player's campaign, the City PD's line. No claim, ruling or record in
  this slice changes a first-class line, the spending limit or a tax. **[Director]**
- The **pot** is the total of the old roll: $20,094,200 on the recorded figures. The review moves
  money only inside it. One household's gain is another household's loss. **[Director]**
- **When the county is short.** After each close the county knows its cash. What it can pay in
  relief next period is its cash, or its spending limit if that is lower, less its first class. That
  figure is never below zero and never above the pot. If it is less than the pot, every unit is cut
  by the same share. **[Call]** Today the engine would pay the support lines one after another in
  identifier order and leave one of them part-paid. This rule replaces that order for household
  support only. On the recorded figures the pot is whole through period 29 and zero from period 30,
  with no period in between.
- **Relief won is a level, not an addition.** A grant lasts one period. It is paid again only if the
  households come again. **[Call]**
- County support is paid into a group's pooled budget, as it is today. The engine counts households.
  It does not know which household holds a unit.

### 7.2 Positions

A **position** is the set of households in one budget group that stand the same way toward the roll.
Each group has two: households **on the roll**, which hold a unit of the old roll, and households
**off the roll**, which hold none.

- **Counting.** A group has a number of households and a number of units, both held by the engine.
  Households on the roll are the smaller of the two numbers. The rest are off the roll. This places
  one job-seeker in each household until households run out. **[Record needed]** The placement is
  Designed. It decides how many households can defend the roll and how many can claim, so it changes
  outcomes. The other bound is to stack job-seekers into as few households as possible.
- The three small named groups are positions of their own: the claimants (2 households, on the
  roll), the aid partners' households (4, off the roll) and the organization's own households (4,
  off the roll). Their households do not spill into the large groups they were carved from.
  **[Call]**
- Collective residence has persons and no households, by an engine rule. It has no position. Its 772
  units stay on the old roll and are cut like the rest.

| Position | In plain words | Who stands for it at the county |
|---|---|---|
| With earnings, on the roll | A household with a wage and a job-seeker | Claimants' Assembly |
| With earnings, off the roll | A household with a wage and no job-seeker | Aid partners |
| No earner, on the roll | A household with no wage and a job-seeker | Claimants' Assembly |
| No earner, off the roll | A household with no wage and no job-seeker, for example retired or disabled people | Aid partners |

Each of the four appears twice in the engine, with and without business ownership.

### 7.3 Bodies and the county

A **body** is an organization that households can give hours to.

| Body | Today | In this slice |
|---|---|---|
| Wayne Relief Claimants Assembly | A fixed actor with a captured mandate. Its claim: "Keep current claimants on the relief roll while the county reviews their cases." | Carries the defense of the old roll at every session. Households on the roll stand behind it |
| Wayne Local Aid Partners | Four households and a fixed script. Its claim: "Hear the cases of residents who received no county support." | Carries the claim at every session. Households off the roll stand behind it. It also runs food with its own hours (section 7.8) |
| Wayne County administration | Does not exist | New state actor. It announces the pot, counts the room and rules |
| Wayne City PD | The state opponent | Unchanged. Its line is in the first class |
| Wayne Organizing Collective | The player's organization | Not a body at the session. Its organizer reaches households |

- **The two claims stand for the whole run.** No body withdraws or changes its claim in this slice.
  **[Call]**
- **Neither body has an organizer of its own.** Only the player's organizer opens a position.
  **[Call]** So nothing starts at the county unless the player starts it. Section 12 lists this as a
  risk.
- **The player never legislates.** The player reaches a household. The household decides whether to
  come. The county rules.
- **Nobody joins the player's own organization in this slice.** Households give hours to the two
  bodies.
- **Opening reach.** The households the scenario records as authorizing each delegate start as
  reached: the 2 claimant households, and 3 of the aid partners' 4. **[Call]** This is a Designed
  opening. No rule reads the authored numbers again.

**The county administration.** **[Record needed]** It follows the form ADR291 set for the City PD.

| | |
|---|---|
| Authority | It rules on the household support lines of Wayne's county-scoped public account. It cannot change a first-class line, the spending limit or a tax |
| Objective | Pay its first class in full. Keep relief inside the pot. Among households, count those in the room by what they pay in |
| Resources | The account's cash. Holding a session costs it nothing in this slice **[Call]** |
| Knowledge | Its own account, the old roll, the wage tax each group paid it, and who is in the room, by position. It does not see who was reached and stayed home, what the organizer chose, or anything hidden |
| What it cannot do | Arrest, coerce, close a session, change its own rule, or act on anything it has not seen in its own room or its own books |
| Receipts | A statement of the pot and its cash, a ruling, and the payment receipts the engine already writes |

The county's rule is fixed for this slice. A county board that can change it is later work.

### 7.4 A session, step by step

The county holds one session each period, after the period's accounts close. Every step runs on
counts of households and exact fractions.

1. **The county announces its pot** for next period (section 7.1). If the pot is zero nobody has
   anything at stake, and nothing below happens.
2. **The county works out each household's count.** For each group it divides the wage tax the group
   paid this period by the group's households. A household's **count** is that figure divided by the
   same figure for all Wayne households together. A household that pays the average counts as 1. A
   household that pays no wage tax counts as 0. If no household paid wage tax, every count is 0.
3. **The claim.** Households off the roll that have been reached may stand behind the aid partners'
   claim. Each asks for one unit, or for its count of a unit if its count is below 1. Its stake is
   the money that would pay it next period. It comes if that is at least the floor of section 7.5.
4. **The defense.** The county adds up the units asked. If they were granted in full, every unit on
   the old roll would be cut by the same share. That cut is the stake of a household on the roll.
   Those that have been reached come behind the Claimants' Assembly if the cut is at least the
   floor.
5. **The ruling.** The county adds the counts of the households for, and the counts of the
   households against. It grants units equal to the difference: never fewer than zero, and never
   more than were asked. Every line of the old roll is cut by the same share to pay for what is
   granted. The total does not change.
6. **The record.** The county publishes the ruling: households for and against in each position,
   what they counted for, units asked, units granted, and what was refused and why.
7. **Payment.** The amended lines are paid at the next period's close, by the engine's existing
   payment step. They hold for that period only. The next session starts again from the old roll.
8. **The roll and the spread.** Every household that came is on its body's roll for the period. Each
   brings one more household of its own position, who is reached from the next session (section
   7.6).

Three details complete the rule.

- **Only wage tax counts.** The engine does not tax ownership income. The tax that sites pay gives
  no household a count. **[Call]**
- **When the roll cannot hold everyone who asks.** Positions are served in order of count, highest
  first. In the last position served, only as many households come as can each be paid the floor,
  and they share what is left equally. Positions with the same count share in proportion to their
  households. No result depends on the order of identifiers.
- **When the county grants fewer units than were asked,** the position with the lowest count loses
  first, and households with the same count lose equally. The receipt records the shortfall for each
  position.

### 7.5 What a household does

Every rule below runs on counts of households, never on individuals.

| Step | What it reads | What happens |
|---|---|---|
| Is it reached? | Section 7.6 | An unreached household does nothing |
| What is at stake? | Its position, the pot and the claim | Off the roll: the money that would pay it next period. On the roll: the money its unit would lose if the claim were granted in full |
| Is it worth the time? | The session's hours and the wage | It comes only if its stake is at least the **floor**: 2 hours at $24, which is $48 today |
| Can it come? | Its group's free hours from the period just closed | Each household in the room spends 2 hours. If a group's hours run short, the places are shared between its positions in proportion, and the rest are recorded "no time" |

A reached household that does not come is recorded with one reason: nothing at stake, not worth the
time, or no time.

Five things about this rule are stated on screen and in the record. **[Record needed]**

- **A household reads only its own money and hours.** No rule reads solidarity, consciousness,
  nation or a class label. Nobody comes for someone else's gain. **[Director]** Article II calls the
  gap between material position and conceived interest "a terrain of political struggle". This slice
  models only the first of the two.
- **The floor is a step.** **[Director]** It compares two amounts the engine already holds, and has
  no coefficient of its own. Project law forbids a rule from imposing a second fixed response curve,
  so the record must name it as a Designed step that the Director chose.
- **Households in the same position move together.** **[Director]** A household comes because the
  matter changes its own income, not because its own attendance tips the result. So a household on
  the roll comes to defend its unit even when it is one of thousands.
- **A household that counts as nothing still comes.** **[Call]** A household on the roll with no
  wage loses the same $48 as one with a wage. By the ruling it comes. The county does not count it.
  The record shows it as "in the room, not counted". The other reading is that it stays home because
  its coming changes nothing; then the poorest would never appear at the county at all.
- **An hour is valued at the going wage for every household,** including one that cannot sell an
  hour. **[Director]**

On the recorded run time is not scarce. The first group has 128 million free hours in period 2, and
the two claimant households have 256.

### 7.6 Reach

- **The organizer's contact.** The new choice, a review contact, spends the period's two organizer
  hours to reach one household in a position the player names. It is the same two hours the
  organizer spends today on a partner organization. Like every practice it is chosen in one period
  and takes effect in the next. **[Record needed]**
- **Each one brings one.** **[Director]** Every household that came to a session brings one more
  household of its own position, who is reached from the next session on.
- **Bringing one costs two hours.** **[Call]** The household that brings spends 2 hours of its own
  on it, the same as the organizer's contact. So a household that comes gives 4 hours in the period:
  2 in the room and 2 bringing the next. The floor still compares the stake with the 2 hours in the
  room, as the Director ruled.
- **A reached household stays reached.** It decides afresh each period whether to come. Only
  households that came bring another. If a group's free hours do not cover the bringing, fewer are
  brought, and the record says so.
- **A position cannot grow past its households.** When every household in it has been reached,
  nobody is brought and no hours are spent on it.
- **Nothing can be called back.** **[Call]** The player can reach households in another position.
  The player cannot un-reach a household or stop it bringing the next.

The rate is Designed. The engine's time accounts show far more free hours than organizing uses, so
they cannot fix how fast it spreads. One contact for two hours is the only rate the scenario already
has, and this design applies it to every household that came.

### 7.7 The county's count: worked numbers

All three cases use the recorded period-4 figures and a count of 1.24 for a household with earnings
and no business ownership. That count rests on the household-size assumption in section 3. A
household with no wage counts 0.

**A small room.** 1,024 households with earnings, off the roll, are in the room for the claim. They
ask for 1,024 units. Granted in full, that would cut each unit on the old roll by $4.00, which is
below the floor, so nobody defends. They count 1,270 for and nobody counts against. The county
grants 1,024 units: $286,720 a period. The first group's line rises from $10,874,360 to $11,005,916.
The no-earner group's line falls from $7,430,640 to $7,324,614.

**A room with a defense.** 16,384 households ask for 16,384 units. That would cut each unit by
$63.92, so reached households on the roll come. Suppose 6,000 with earnings and 5,000 with no wage
are in the room against. The 5,000 count nothing. The 6,000 count 7,440. The claim's side counts
20,316. The difference is 12,876, so the county grants 12,876 units of the 16,384 asked, and records
3,508 refused. Had only 2,000 with earnings come against, they would have counted 2,480, the
difference would have been 17,836, and the claim would have been granted in full: a household that
counts more than 1 has count to spare.

**A full room.** 131,072 households ask. The roll has 71,765 units. They count 162,529. Every
household on the roll with earnings, all 38,837, would count 48,158 against. The difference is
larger than the whole roll, so the county grants all 71,765 units and the old roll is paid nothing.
Each household in the room is paid $153. When all 417,691 such households are in the room, each is
paid $48.11.

**What this shows.** Households with a wage and no job-seeker outnumber households with a wage and a
job-seeker by ten to one. Once the first position moves, the second cannot stop it. Households with
no wage cannot slow it at all.

### 7.8 The second road: food runs

The Director ruled that a household which gives its own hours to the aid partners' work goes on that
body's roll, and that receiving aid never does. **[Director]**

**What exists today.** A local aid run moves up to 4 food parcels in a period from the
organization's own households to the aid partners' 4 households. The giving side spends 2 hours a
parcel. If the aid partners eat any of the food, the run counts as complete and each side is charged
2 hours for meeting. Nothing records who took part.

**What this slice adds.** **[Call]**

- On a local aid run, a household of the aid partners may turn out to receive the food and share it
  out. It gives 2 hours. One household may turn out for each parcel delivered. The 2 hours the aid
  partners are charged today become the first household's.
- It turns out only if the parcel is worth those hours to it: the parcel, at the current food price,
  is worth at least 2 hours at the wage. This is the Director's rule for the county session, applied
  to food. At the opening price a parcel is $280.
- A household that turned out is on the aid partners' roll for that period. A household that only
  received is not. If nobody turns out, the run still delivers, as it does today, and nobody joins.
- Any of the aid partners' 4 households may turn out. They need no contact, because the body is
  their own. So this roll cannot pass 4, and each one brings one has nowhere to go on this road
  until a later slice widens it.

**What limits it.** Food, not hours. The engine moves at most four parcels a run, one run a period,
and only food the organization's own households have left after they have eaten. In the recorded run
those households bought 8, 7, 4 and then 0 parcels in the first four periods, and from period 4 the
shops are empty for everyone. Food runs would stop there. That is the economy running down, not a
rule of this slice (section 12). The view states how many parcels there are and how many households
would turn out.

**Why it is this small.** A household in this slice acts only for its own gain, so nobody gives food
away. The aid partners' road can hand out only what the organization's own four households can
spare. MIM says the same of charity as a strategy (Appendix B). What would let this road grow is
production: a kitchen or a garden staffed by members' own hours, whose output goes to those who
worked. The engine has no site owned by an organization today. Section 11 puts that first among the
next slices.

**The aid partners' roll has two parts,** shown apart: households that came to the county session
behind its claim, and households that turned out on a food run. On the recorded figures the first
part can reach hundreds of thousands of households with a wage. The second cannot pass four
households with none. The view shows both numbers and says nothing more.

### 7.9 Rolls

- A household is on a body's roll for a period if it gave its own hours to that body's work in that
  period: 2 hours in the county's room behind the body's claim, or 2 hours on a food run. Nothing
  else writes a roll: not receiving aid, not service use, not a shared income source, not being
  reached. **[Director]** **[Record needed]**
- A roll is a level. It is written afresh every period, from that period's hours.
- Three things read the session's part of it. The spread reads who came, to reach the next
  households. The county's count reads who is in the room. The views show it. The food run's part is
  read by the hours charged for the run and by the food run view.
- For each body, position and period the record holds: households on the roll, how they came to be
  on it (session or food run), hours given, what the county counted them for, and households
  brought.
- A body's strength in the county's room is the count of the households in the room. The size of its
  roll is not its strength.

**Where the record lives.** The session records are the first home of the rolls. They are hashed
with the rest of the turn's records. Writing the same counts onto membership links in the graph is
the hypergraph step the Director asked for: a body is one link over many positions, with the
households and hours on it. That step waits on two things outside this slice: the Director's act to
fill the membership payload (ADR198 R4; PER-44) and an accessor in the upstream graph library
(hypergraph-rs issue 2). Until then the graph payload is recorded as blocked on those two, which is
the disposition the Game Design Standard requires. **[Record needed]**

### 7.10 Class reading

- Each position shows a **livelihood profile**, Derived from its group's accounts: wages, ownership
  income, county support, mutual aid, and hours sold, owed at home and free.
- Each position shows **MIM's reading** as a reading, marked Designed and never shown as Derived.
  **[Record needed]**
  - With earnings: "labor-aristocracy or higher (MIM's default reading; value and legal-status terms
    pending)".
  - With business ownership: the same line, with "holds business ownership" and the ownership income
    shown beside it.
  - No earner: "no earner in the household; includes retired, disabled and dependent people. MIM's
    reading needs nation and legal status, which are pending."
- No position is called "workers", "proletariat" or "the base".
- Nation shows as "pending" on every position.
- One line is on screen in every view of this slice: "This slice has no nation, no solidarity and no
  consciousness. Households act on their own money only." **[Director]**
- The class reading is displayed. No rule in this slice takes it as an input.
- Nothing in this slice is presented as MIM's base. MIM holds that "The principal contradiction
  inside the U$A is nation.", and nation is not in the slice.

### 7.11 What the player sees

Each view is a decision surface and carries the contract Article VII requires.

| View | The question it answers | What it shows | What the player can do from it | What comes back |
|---|---|---|---|---|
| County ledger | Is there relief money to move, and for how long? | The lines in pay order, the pot announced for next period, the county's cash, what went unpaid | Nothing directly | Next period's payment receipts |
| Roster | Who lives here, how do they make a living, and where do they stand toward the roll? | Each position's livelihood profile, class reading, units, and, where earned, its count and how many are reached | Choose a position for a review contact | The contact's receipt |
| Preview | What would the next session do if I reached one more household here? | Who would come, for and against, what they would count for, what the county would grant, who would pay | Confirm or cancel the contact | The session record |
| Session record and rolls | Who came, who was counted, who stayed home and why, and what did the county do? | The ruling, each position's choice and reason, each body's roll in its two parts | Nothing directly | Next period's receipts |
| Food run | How many parcels are there, and who would turn out? | Parcels the organization can spare, households that would turn out, last run's roll | Choose a local aid run | The run's receipt |

**What is public and what is earned** (ADR182 R2). **[Call]**

- Public record: the county's lines, the pot, the county's cash balance, the two claims, the old
  roll by group, and every ruling.
- Earned: a position's count, its stake and how many of its households are reached. The player sees
  these only for a position where the player has made a contact. For any other position the views
  show its name and its profile, and state the remedy: reach a household there.
- The preview is something the player knows. It is never part of the turn's hash. It uses the last
  period the player has seen close, and says so. The session itself uses the period that has just
  closed, so the two can differ if wages or the county's cash moved in between.

### 7.12 State, order in the turn, and where the rules live

**New records,** all hashed with the turn except the preview:

- the county administration's configuration and the old roll it keeps;
- for each position and each side: households reached;
- for each session: the pot, each group's count, each position's choice with its reason and hours,
  the ruling, and what was refused;
- the amended support lines for the next period;
- each body's roll for the period, in its two parts;
- the organizer's review contact and its receipt.

**Order in the turn.** The period's accounts close. The organizer's practice resolves, which is
where a review contact lands and a food run completes. Then the session runs: household choices,
hours, the count and the ruling. The amended lines are paid in the next period's close. The engine
already stores the support lines in the turn's state and accepts new and changed lines; nothing
writes them today.

**Where the rules live.** Each new rule is a rule entry that calls a native operation, as the
organizer and City PD rules do, with its role, its evidence class and its attribution row. The
engine's list of native operations is closed, so the session needs a new one. Its allowance and
attribution rows arrive with the code, not before. The numbers stay in the scenario's defines file.

**Evidence classes.**

- Existing Designed values that this slice reuses: the unit ($280), the session's 2 hours, the
  contact's 2 hours, the $24 wage, the 15% wage tax, the budget groups themselves.
- Derived: wage tax per household, the count, the pot, stakes, the cut to the old roll, rolls.
- New Designed rules, each needing a record (section 8): the fixed pot; counting by share of wage
  tax; one unit at most for a household; netting those for against those against; cutting the old
  roll by one share; one session a period; the floor; households in a position moving together; each
  one brings one, at 2 hours; one job-seeker to a household; the equal cut when the pot is short;
  rolls by own hours; turning out on a food run; the opening reach; the class text.
- Observed: none directly. Calibrated: none.

### 7.13 Quantities that must balance

- For each position and session: households reached = households that came + households that stayed
  home, each with a reason. Unreached households are untouched.
- Hours charged = 2 for each household that came, plus 2 for each household brought. They are never
  more than the group's free hours.
- Counts for and against are sums over households in the room. No number is written in.
- Units granted = the difference of the counts, held between zero and the units asked. Units asked
  are never more than the old roll holds.
- Money: what is granted leaves the old roll's lines by one common share and enters the lines of the
  positions that asked. The lines sum to the pot the county announced, to the last millionth.
- The pot the county announces equals the support it then pays. No first-class line, limit or tax
  differs from a run with no sessions.
- Households reached in a position are never more than its households. Positions of a group sum to
  the group's households.
- A roll is never more than the households that gave hours that period.
- Persons, employment and the household lifecycle are untouched.
- No random draw anywhere. The same inputs give the same receipts and the same hash.

### 7.14 Why the grouping survives splitting and merging

Article II asks for a proof that a grouping does not change the result. The declared scale is the
county. The declared grouping is the position: budget group by whether a household is on the old
roll.

- **Splitting changes nothing.** Every figure a rule uses is the same for each household in a
  position: its count, what it asks, what it would lose. Every total is a sum over households. So if
  a position is split into parts in any way, each part makes the same choice, the sums are the same,
  and the ruling, the lines and the rolls are the same. Money is rounded once, for each support
  line, after the sums.
- **Merging two positions changes the result.** Households on the roll can only lose from the claim,
  and households off it can only gain. Averaged together they would act on a stake neither has. That
  is why the grouping cannot be coarser.
- **Relabeling changes nothing.** No rule orders positions or groups by identifier.
- **The limit of the proof.** It holds for the accounts the engine has. A budget group is itself a
  Designed allocation, and households inside it may differ in ways the accounts do not show. Finer
  groups are later work.

Section 9 turns these four statements into tests.

## 8. Decision records needed

The Director has made the five decisions in section 2. Project law requires each to be written into
a decision record before it is built, and several of the author's calls need the same. The plan will
say how many records these become. The list is what must be decided and written down.

| # | Subject | What the record must say | Why it needs a record |
|---|---|---|---|
| 1 | The county administration, a second state actor | Its authority, objective, resources and knowledge, as in section 7.3. Only its ruling changes a household support line. The first class, the spending limit and taxes are closed to it. This partly supersedes ADR299's sentence "The county's ordinary fiscal accounts continue to determine payments." | ADR291 approved the City PD as "the first state opponent" by name. ADR184 requires a budget to have an owner |
| 2 | Whether the county's rule is a response curve | The rule is a Designed rule of an institution. It is a sum and a difference with no coefficient. The record must say whether the Director holds it to be outside the ban on a "fixed political-response curve", or grants it as an exception | ADR291; AGENTS.md. Only the Director can say |
| 3 | How the count is computed | Count by share of wage tax. One unit at most for a household. Those for less those against. The old roll cut by one share. The order when the roll is full | The ruling of 19 November left it open. Section 6 gives the three readings |
| 4 | The pot when the county is short | Every unit cut by the same share. The county publishes its cash at each session | It replaces the engine's identifier order for household support |
| 5 | The household's rule | Own money only. The floor, named as a Designed step that the Director chose, with no coefficient. Households in a position move together. A household that counts as nothing still comes. An hour valued at the wage for every household | AGENTS.md: "A rule cannot impose a sigmoid or a second fixed response curve." It also touches the reserved theory line |
| 6 | Each one brings one | A Designed rate, the Director's. Two hours for each household brought. Nothing can be called back | The same |
| 7 | Rolls by own hours | A household's own hours, at the session or on a food run, put it on a body's roll for that period. Any Wayne household may be charged hours on its own recorded choice. This amends, for these two acts only, ADR262's "Neither operation writes solidarity, membership" and ADR270's rule on what creates membership | ADR270; ADR262 |
| 8 | The review contact | A new organizer choice. It is new content vocabulary, so it needs the Director's ceremony, schema and conformance updates and a recording record. The record says how it sits with the nine verbs of ADR177 | Constitution Article VIII |
| 9 | Placing job-seekers into households | One to a household until households run out, declared on screen | It is Designed and changes outcomes |
| 10 | The class and nation text on screen | As in section 7.10 | The ideological line is the Director's |
| 11 | The graph payload | Either "blocked on PER-44 and hypergraph-rs issue 2", or the Director opens the payload ceremony in this lane | ADR198 R4; Game Design Standard W.2 |
| 12 | Opening conditions | The opening reach of 2 and 3 households. The two standing claims. No organizer for either body | They are Designed |

## 9. Build order and proof

The engine has no recurring proceeding, no action that reaches a household, no change to a budget
line after the opening, and no state actor that rules on anything. Each piece below can be played or
checked on its own.

| Piece | What it adds | How it is proven |
|---|---|---|
| 1. The ledger and the roster | The county ledger with the pot and the county's cash. The roster of positions with their counts. Read-only: no rule and no stored state changes | Every figure equals the engine's own receipts. Positions sum to each group's households. No existing hash moves |
| 2. The session | The review contact, household choices, the count, the ruling, the amended lines, the rolls, the spread, the session record and the preview | The proof list below |
| 3. Food runs | Turning out, its hours, and the aid partners' second roll | A household that only received is never on the roll. With no food to spare, nobody turns out and the receipt says why |
| 4. Rolls in the graph | The rolls written onto membership links, with their hash section. Only after record 11 opens it | The graph counts equal the session records every period. The new hash section is absent when empty, so no existing hash moves |

**The proof list for piece 2.** Each line is a test or a recorded run, written before the code it
proves.

- **Balances.** Every line of section 7.13 as a property test.
- **Twins.** The same opening run twice: once with the player's first contact and once without.
  Without it, every payment equals today's run, and the session records are empty.
- **The fixed pot.** In every run, with or without sessions, every first-class line, the spending
  limit and every tax receipt are identical.
- **The county keeps its word.** In every period the pot the county announced equals the support it
  paid.
- **Counterfactuals.** Count every household as 1, and the no-earner positions are granted units:
  the real count must refuse them. Set the stake one dollar under the floor and one dollar over: the
  household stays home, then comes. Set the pot to zero: nobody comes.
- **Sever tests.** Each of these links is cut in turn by a deliberate fault, and a test must fail:
  wage tax to count; who is in the room to the ruling; the ruling to next period's lines; the lines
  to the payments; the payment to the stake; coming to the roll; the roll to who is reached next;
  the contact to who is reached.
- **Direct-write audit.** Only the county's ruling writes a household support line. Only a
  household's recorded choice charges its hours. Only the session and the food run write a roll. The
  scenario writes none of the results.
- **Replay.** Replaying and reopening a campaign gives the same receipts and the same hash, byte for
  byte.
- **The grouping.** Split any position into parts, and every result is the same. Merge the two
  positions of a group, and the result differs. Relabel every identifier, and every result is the
  same.
- **A witness for every outcome.** Each outcome the records can name is reached in at least one
  committed opening, by changing opening conditions only: granted in full; cut back by the defense;
  refused outright; shared out because the roll is full; in the room and not counted; not worth the
  time; no time; no pot; a position with nobody left to reach.
- **Ceremonies.** Baseline changes carry the required trailer. Schema and conformance contracts
  change with the code. The allowance and attribution rows for the new operation arrive with it.

**Play proof for the whole slice.** Four recorded playthroughs from the same seed, each run past the
period in which the county runs short, each driven through the real client with no screen, and each
kept as seed, action log and result. They differ only in the player's line: no contact at all;
opening the claim; opening the claim and then the defense; food runs only. They must give four
different records that the receipts explain. The tutorial chapter that walks a new player through
the first session is the acceptance script.

**Views.** Each view of section 7.11 ships with its decision-surface contract and its links into the
Archive.

## 10. Left to the builder

- The names and shapes of the new records and of the review contact, within ADR262's rule of one
  practice a period.
- Whether the county administration is a graph node, as the City PD's agency is, or a register only.
  ADR184 requires the pot to have an organization as its owner.
- Whether the order of grants when the roll is full uses the existing allocator, which funds whole
  candidates, or a version beside it that can divide a position. Either way no result may depend on
  identifier order.
- Whether the session is one native operation or two: the households' choices, and the county's
  ruling.
- How the county's figure for the pot is made to match the engine's payment step exactly. Section 9
  holds the proof.
- How a support line that falls to zero is left out and restored. The engine requires positive
  amounts.
- How the 2 hours for turning out on a food run replace the flat 2 hours the aid partners are
  charged today.
- Where the views sit in the client, and the projection that feeds them. Single Wayne reads take 9
  to 12 seconds today, so the views need their own projection.
- Version bumps. The organizer format is version 12 today and has no compatibility path.
- The exact wording of on-screen text, within section 7.10.

## 11. After this slice

- **The kitchen.** A site owned by an organization, staffed by members' own hours, whose output goes
  to those who worked. This is what lets the independent road grow past four households. It needs a
  production rule and the Director's rulings on it.
- **Who can show up.** Wayne's budgets split into real sub-budgets, so that a position has accounts
  of its own. Labor status as a group decision. Nation, legal status and the wage-against-value
  term.
- **Rivals and masses.** A second organizer that opens positions for itself. Businesses as a body at
  the county, counted by the tax their sites pay. Organizing that spreads through workplaces.
  Opening rolls from observed union membership.
- **The county board.** An office that can change the county's rule, an electorate with its
  exclusions counted, and "Don't vote, organize" as a playable stance.
- **Beyond Wayne.**

## 12. Known risks

- **The recorded economy runs down.** In the recorded run food is off the shelves from period 4.
  Wages in the largest group fall from $1,221 million in period 2 to $238 million in period 4 and
  $129 million in period 14. The county is short from period 30. This slice reads the engine's
  accounts and will be only as alive as the economy is. Relief money moves, but from period 4 it
  buys little, and food runs stop when the organization's households have nothing to spare.
  Repairing the economy is outside this slice.
- **Nothing starts unless the player starts it.** No rival opens a position. A player who leaves the
  county alone sees the old roll paid unchanged until period 30. The harm the claim does to the old
  roll is harm the player chose.
- **Once large, the claim cannot be stopped.** Section 7.7. The defense matters in a narrow window.
  This follows from the Director's rulings and the sizes of the groups, and it is what the slice
  shows. It also leaves the player one large decision at the county, not a contest every period.
- **The first year is slow.** One household becomes 8,192 over fourteen sessions. The player can
  watch the room double each period, but little money moves until late.
- **The second road is capped at four households,** and in the recorded run it ends by period 4
  (section 7.8).
- **Households that count as nothing keep coming.** By the rule they come every period that the
  matter costs them $48, and it changes nothing for them. Section 7.5 gives the other reading.
- **Counts rest on a placement rule and on household numbers the recorded files lack.** The worked
  figures use an assumption for three of the four large groups. The engine holds the real numbers.
- **Money is pooled.** A grant is paid into a group's budget. The engine cannot say which household
  received it. Every figure for a household is a figure by count.
- **The preview can be one period stale.**
- **The county's rule may be read as a response curve.** Record 2 in section 8 must settle it before
  anything is built.
- **Turn time.** A national turn already takes 7 to 19 seconds, with a budget of 30. The Wayne-only
  work is small, but it has not been measured.
- **The recorded figures come from one seed and an older world format.** That run has no City PD and
  no claimant group. A player's campaign has both.
- **The format has no compatibility path.** Changing the organizer records resets saved campaigns,
  as ADR262 intends.

## Appendix A: Engine facts

**Read by the author in the code or the recorded data.**

- County payments: for each public account the amount available is the lower of the spending limit
  and the cash above the floor. Each line is paid the lower of its amount and what remains, in list
  order (`rust/crates/babylon-material-circuit/src/financial/close.rs:100-134`).
- Household support is job-seeking persons times one period of food at the opening price
  (`rust/crates/babylon-persistence/src/national_economy/opening/financial.rs:126-145`).
- The engine's state holds households and persons for every budget group. An ordinary group must
  have at least one household. A collective residence must have none
  (`rust/crates/babylon-material-circuit/src/recurring/model.rs:23-45`).
- The allocator of ADR184 ranks whole candidates by yield per unit of cost and records each one it
  could not afford with what was left (`rust/crates/babylon-graph/src/capacity.rs`).
- Scenario numbers (`content/scenarios/national/defines.toml`): wage $24 an hour; wage tax 15%; one
  period of food support; `contact_hours = 2`; `contributor_hours_cap = 8`; aid of at most 4 parcels
  at 2 hours each; the hearing in period 2, the review in period 3, `attendance_hours = 2`,
  authorizing households 2 and 3; the two claims quoted in section 7.3.
- The player's choices are `Inquiry`, `Collect`, `LocalAid`, `RemoteAid`, `Reinforce`, `Hold`,
  `PauseStanding`, `ResumeStanding` and `InviteToHearing`
  (`rust/crates/babylon-practice-contract/src/organizer/types.rs:121-131`). The organizer format is
  version 12.
- Recorded data, campaign `5efafb84`, seed 319, in
  `reports/economic-flows-qualification-2026-11-14-assets/`: the county's lines, cash and first
  unfunded period (`wayne-public-allocations.json`); group persons, support and wages at period 4
  (`wayne-p4-households.json`); the first group's households and its wages at periods 2 and 14
  (`wayne-household-period-2-v10.json`, `national-demographic-financial-horizons-v10.json`). Units,
  wage tax and every figure in sections 3 and 7.7 were computed from these with `python3 -I`.
- The claimant and aid figures come from a second recorded campaign, `e841f4b2`.

**Reported by read-only readers on 18 and 19 November 2026, and not all re-read by the author.**

- The organizer has 2 committed hours a period. No existing operation contacts a household.
- Every household group pays wage tax at 15% on wages accrued in the period, out of the cash it has
  left. Ownership income is not taxed. Sites pay a separate tax on operating income. All of it goes
  into the one county account that pays grants, support and the City PD.
- Tax receipts are written each period and can be read by an operation that runs after the close in
  the same turn. They are not kept in the turn's state afterwards.
- The engine accepts a new household support line, and a changed amount on an existing one, as long
  as the amount is positive. Nothing checks support against job-seekers after the opening. A changed
  line takes effect at the next close.
- When cash is short, lines are paid one after another in list order and one is part-paid. In the
  recorded run the grants take all the cash from period 30 and household support is paid nothing.
- The City PD's contract, its native operation and its allowance and attribution rows, as the form
  for a second state actor. No record bars a second one.
- The engine's native operations are a closed list of four.
- Local aid: food comes from the giving households' own surplus, at most 4 parcels a run and one run
  a period, at 2 hours a parcel. The aid partners in the engine are four households with a script.
  They have no site, no stock and no roll.
- The food shortage from period 4 is a shortage on the shelves. The largest group had money for
  every parcel it asked for, and the shop delivered 23.
- The hearing's two seats are fixed in ten places. One hearing per campaign. The review only writes
  a record.
- The membership payload is an empty marker. The upstream gap is hypergraph-rs issue 2.
- The client has no ledger, roster or roll view.

## Appendix B: MIM's line on the points this design leans on

All from the fact-checked findings in `docs/gameplay/research/40-class-agents-evidence.jsonl`. Each
quotation is exact.

- Money outweighs numbers: "The ballot power of the oppressed is not greater than the financial
  power of the capitalists." (mim-on-other-lines F10). This is the ground for a county that counts
  by what a household pays in. The capitalists themselves are not a body in this slice; section 11
  names that gap.
- On the white majority and elections: "The majority of white Amerikans support or participate in
  the electoral system." (mim F15). MIM is speaking of the white majority, not of all households.
- Small local wins are possible: "It is possible that in elections to city hall, some small battles
  can be won locally" (mim F14).
- On public payroll: "In some ways, the government sector is the ultimate expression of the
  imperialists' loyalty to the oppressor nation working class, since it is difficult to ship
  government service jobs overseas." (mim-class-structure MC-21). This is the ground for a county
  that pays its own offices first.
- Who counts as labor aristocracy: "salary and wage-receiving people within U$ borders are
  labor-aristocracy or higher, unless they are undocumented." (mim-class-structure MC-02). Legal
  status is not in this slice, so the text on screen says the term is pending.
- Which way they go: "Conditions determine which way they go as a group, and in imperialist
  countries today their material interests are allied with the bourgeoisie" (mim-practice F09).
- What the majority wants back: "They just want their goodies back like in the old days of
  imperialism." (mim-on-other-lines F05).
- Reform at its most effective: "The work of social-democrats never succeeds, but when it is most
  effective it turns the oppressed into oppressor instead of abolishing both" (mim-class-structure
  MC-24).
- What reform work teaches: "Revolutionaries work on reforms because some do improve the lives of
  people on a small scale, yet more often our work on reform battles further confirms that reforms
  do not work" (mim-practice F18).
- The main danger: "This "right opportunism" is the main danger in the party-building process in the
  world." and "if you're an organization in the First World and have a large following you stand for
  bourgeois ideals." (mim-practice F21).
- The principal task: "The principal task is to "create public opinion and the independent
  institutions of the oppressed to seize power." That means discrediting the state as it exists."
  (mim-practice F01). This is the ground for the second road.
- Relief is limited: MIM "believes that as a strategy charity can never provide more than temporary
  and limited relief." (mim-practice F07).
- Nation comes first: "7. The principal contradiction inside the U$A is nation." (mim F09). Nation
  is not in this slice, so nothing in it is presented as MIM's base.

## Appendix C: What the review found, and where this draft answers it

The second draft was reviewed on 19 November 2026 by four readers, and a second reader challenged
each serious finding. The full review is in the workflow journal `wf_f30fdb94-a47`.

| Finding | Answer |
|---|---|
| The organizer has 2 hours a period, not 8, and no operation contacts a household | Section 7.6: one review contact a period, as a new choice |
| Collective residence has no households | Section 7.2: it has no position |
| "Pay first" cannot be built | Removed |
| The recorded run has no City PD and no claimant group | Sections 3 and 12 say so |
| Provider grants go to every public administration site | Section 7.1: the whole first class is off the table |
| The ruling needs a new native operation | Section 7.12 |
| Group persons and households are Designed, not Observed | Sections 5 and 7.12 |
| Units only ever grow | Section 7.1: relief won is a level that lasts one period |
| The stake was defined twice | Section 7.5: always money actually paid or lost |
| Objectors saw only one session's increment | Section 7.4: the defense reads the whole claim |
| The placement rule was said not to move money | Section 7.2 says it changes outcomes, and it needs a record |
| The grouping proof showed signs, not outcomes | Section 7.14 and the tests in section 9 |
| "Restore" was circular, and choices came down to identifier order | "Restore" is removed. No result depends on identifier order (sections 7.4 and 9) |
| No rule read the membership roll | Section 7.9: the spread and the count read it |
| The county had no interest of its own | Sections 7.1 and 7.3, by the Director's ruling |
| The $48 floor is a step and needs a ruling | Sections 7.5 and 8 |
| A new organizer choice needs a ceremony and a record | Section 8, record 8 |
| The preview showed a site's cash before any contact | Section 7.11: no site figures are shown, and a position's figures are earned by contact |
| The build plan lacked sever tests, the direct-write audit, ceremonies, decision-surface contracts and archived playthroughs | Section 9 |
| The reason for withdrawing tax weighting was wrong | Section 6 and Appendix B |
| Two quotations were bent | Appendix B gives them exactly |
| A county that always concedes makes reform always work | Sections 7.1 and 7.7: the county gives up nothing of its own, and relief ends when its cash does |
| Only the county session wrote membership | Sections 7.8 and 7.9 |
| No line here can be called MIM's base | Sections 4 and 7.10 |
| "Labor aristocracy" was too narrow for owner groups | Section 7.10 |
