# The County Review: design

**Status:** Fourth draft, 19 November 2026, for the Director's approval. It replaces the third
draft, which three readers checked the same day and found wanting. The Director then ruled on the
two questions that were the Director's, and this draft applies both rulings. Nothing is built until
this document is approved.

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
- No action reaches a household outside the organization's own. The organizer's contact hours go to
  partner organizations.
- Only the player's organization decides. The partners follow a fixed script.

The County Review makes the county's relief roll the stake. Each four-week period the county reviews
its roll in open session. It lists every household that holds or asks for a unit of relief, in order
of the wage tax the household paid, and pays down the list until the money runs out. A household
that has been reached works out from its own accounts whether the matter is worth its time, and
comes or stays home. Every household that comes brings one more. The next period's receipts show who
gained, who lost, and who was in the room and ranked too low to be paid. A period the player spends
at the county is a period not spent running food to the aid partners.

## 2. What the Director has decided

| Date | Subject | Decision |
|---|---|---|
| 18 Nov | The first slice | The County Review: "Option A is decided" |
| 19 Nov | The county | "Defends its own, weighs by tax". Office and police money is off the table. The review moves relief only inside a fixed total. A household is weighed by the wage tax it pays the county, not as one head |
| 19 Nov | Spread | "Each one brings one". A household that came brings one more household in the same position to the next session |
| 19 Nov | Why a household comes | "Own money, if worth the time". It comes when the matter changes its own income by at least two hours at the wage ($48 today), and never for someone else's gain |
| 19 Nov | The second road | "Both roads". A household that gives its own hours to the aid partners' work also goes on that body's roll. Receiving aid never does |
| 19 Nov, after the re-check | The county's rule | "Rank by wage tax". The county lists every household holding or asking for a relief unit by the wage tax it paid, and pays down the list until the money runs out. A unit moves only to a household that pays strictly more |
| 19 Nov, after the re-check | The aid road's roll | "No roll until the kitchen". Food runs stay playable as they are today. No roll is written in this slice. The roll arrives with the next slice, where giving hours and receiving food are different acts |

The Director also ruled that the game's ideology sides with MIM, and that MCU and FRSO are settler
organizations opposed to MIM's line. Neither is a source for method here.

**Three things the author told the Director that were wrong**

1. *The ground for weighing by tax.* The author offered that option as the closest to MIM's sentence
   on ballot power and the financial power of capitalists. The sentence does not support it
   (Appendix B). The author said so before the Director ruled on the county's rule, and the Director
   kept the weighing. It stands as a Designed rule that the Director chose. It is not taken from a
   MIM text.
2. *How the weighing works.* The author first said the rule would be a refund of wage tax, then
   drafted a count of households for and against. Both were formulas of the author's own. Project
   law already gives the form for an organization that divides a budget (ADR184), and the Director
   has now ruled that form.
3. *The floor.* The author told the Director that under ranking the $48 floor "never keeps anyone
   home in this slice". That is true of a household that asks, because relief moves in whole $280
   units. It is not true of a household on the roll. Worked through, such a household comes only
   when its position has lost at least 48/280 of its units, a little over 17% (section 7.5).

**What changed since the last draft**

- The county ranks. It no longer counts households for and against, and turning out cannot defend a
  unit.
- Relief moves in whole units, from the households that pay least to households that pay more. A
  household never loses a unit to one that pays the same.
- The count, the netting of those for against those against, the shared-out pot and the equal cut
  are gone.
- When the county is short, the households that pay least lose first.
- Collective residence is outside the review.
- The aid road writes no roll. Food runs are unchanged.
- The class reading is shown beside each source of income, not as a label on a position.
- Sessions start in period 4. A contact chosen in one period is in the next period's session.
- Facts corrected: which wage tax is read, who can be charged hours today, how long turns take, and
  what the engine stores (Appendix A).

**The author's calls, for the Director to check while reading**

1. A household that asks comes only when a place is open for it. It is never sent away (section
   7.4).
2. Groups at the same place on the list lose in proportion to the units they hold, and an exact tie
   moves nothing (section 7.4).
3. A household on the roll reckons its stake as its position's loss per unit held. It comes when
   that reaches $48 (section 7.5). This is the third correction above.
4. A household that is ranked last still comes when it loses, and is recorded in the room (section
   7.5).
5. Relief won lasts one period. It is paid again only if the household comes again (section 7.1).
6. Collective residence is outside the review. Its line is cut only in proportion when the county is
   short (section 7.1).
7. The county reads the wage tax it collected in the period just closed, per household of each
   budget group (section 7.4).
8. Neither body has an organizer of its own. Nothing starts at the county unless the player starts
   it, and nothing the player starts can be called back (sections 7.3 and 7.6).
9. A household that came spends 2 more hours to bring the next one (section 7.6).
10. The county publishes its roll, the order of its list and its cash. A position's dollar figures
    are earned by contact (section 7.11).
11. Job-seekers are placed one to a household when positions are counted (section 7.2).
12. The first session is in period 4, and the review contact can be chosen from period 3 (section
    7.6).
13. MIM's reading is shown beside each source of income (section 7.10).

## 3. One period at the table

### The county's books

These figures come from the recorded run with seed 319. Appendix A names the files. A campaign that
a player starts also carries the City PD's $24 line in the first class.

| Line | Per period | In this slice |
|---|---|---|
| First class: grants to public administration sites | $151,969,750 | Off the table. No claim can touch it |
| Relief: household support | $20,094,200 | The only money the review can move. $216,160 of it is for collective residence and stays outside the review |
| Spending limit (the sum of the two) | $172,063,950 | Unchanged |

Household support is one **unit** for each job-seeking person at the opening. A unit is $280 a
period: one period of food at the opening price. The recorded run pays 71,765 units. The list of
those units is the county's **roll**.

The county's cash in that run starts at $344 million and peaks near $1,151 million after period 3.
From period 4 the county takes in less than it pays out. Its cash falls by $18 million in period 4,
by $34 million in period 10 and by $56 million in period 29. At the close of period 29 it holds
$149.5 million, which is less than its first class. From period 30 it pays its offices in part and
pays no relief at all. Nothing scripts this.

### Wayne's households

| Group (engine budget key) | Persons | Households | Units on the roll | Wage tax per household, period 4 | Place on the county's list |
|---|---|---|---|---|---|
| With earnings, with business ownership | 139,712 | about 53,300 | 2,669 | about $122 | First |
| With earnings, no business ownership | 1,196,610 | 456,528 | 38,837 | $78.29 | Second |
| No earner, no business ownership | 375,449 | about 143,200 | 26,538 | under 2 cents | Third |
| No earner, with business ownership | 41,720 | about 15,900 | 2,949 | $0 | Last |
| Collective residence | 19,084 | none, by an engine rule | 772 | it pays $2.4 million in all | Outside the review |

Persons, support and wages are recorded at period 4. Units are recorded support divided by $280.
Wage tax is 15% of recorded wages, computed by the author; the engine's own tax receipts are not in
the recorded files. The households of the second row are recorded. The other three are computed at
the same size, 2.62 persons a household; the engine holds the real numbers. The order of the list
would change only if those households were far smaller than assumed.

- The third group's wage tax is not zero. The whole group was paid $15,360 in wages in period 4,
  which is four full-time wages: 160 hours at $24, four times. Spread over about 143,200 households
  it is under two cents each. Section 12 says what follows from that.
- The fourth group lives on ownership income, $39.3 million in period 4, which the engine does not
  tax. It pays the county no wage tax and is last on the list.

The scenario also carves out three small named groups: relief claimants (2 households, 2 units), the
aid partners' households (4 households, no unit) and the organization's own households (4
households, 8 persons, no unit). The claimants are households with no earner. In the recorded
period-4 file the other two were paid no wage. All three pay no wage tax and stand at the bottom of
the list.

### The county's list

Each period the county writes a list. On it are every unit on the roll, and every household off the
roll that comes to ask for one. The list is in order of the wage tax each household paid in the
period just closed. The county pays from the top until the money for relief runs out. A unit moves
only to a household that pays strictly more than the household that held it. **[Director]**

On the figures above:

- A wage-earning household with no job-seeker can take a unit from a household with no earner. It
  cannot take one from a wage-earning household with a job-seeker in its own group, because the two
  pay the same.
- A household with earnings and business ownership can take a unit from any household below it.
- A household with no earner can take nothing from anyone above it. Whether it is in the room makes
  no difference.

### What the player does in a period

1. **Reads the county ledger.** It shows the money for relief the county has announced for next
   period, the county's cash, the roll by group, and the order of the list.
2. **Reads the roster and the session record.** The roster shows each household position: how it
   makes a living, whether it is on the roll, and, where the player has a contact, its dollar
   figures. The session record shows who came last period, who was paid and who was ranked too low.
3. **Chooses one practice,** as today. The new choice is a **review contact**: the organizer spends
   the period's two hours to reach one household in a named position. The existing choices remain:
   run food to the aid partners, collect, inquire, hold.
4. **Reads the preview** before choosing. It shows what the next session would do if one more
   household in that position were reached: whether a place is open for it, and whose unit it would
   take.
5. **Advances the period.** The accounts close and the county holds its session.
6. **Reads the session record.** It gives the county's list, who came and what each was paid or
   lost, and one reason for every reached household that stayed home.
7. **Reads next period's receipts.** They show which lines were paid, which positions gained and
   which lost.

### What the first two years look like on the recorded figures

This is a calculation from the recorded period-4 figures under the rules of section 7, made with a
short exact script (Appendix A). It is not a recorded result. It holds the period-4 order of the
list for the whole run.

Suppose the player chooses one review contact in period 3, for a household "with earnings, no
business ownership, no job-seeker", and does nothing else at the county.

| Session | Households that come and are paid a unit | Relief moved to them, per period | Whose units |
|---|---|---|---|
| 4 | 1 | $280 | No earner, with business ownership |
| 10 | 64 | $17,920 | The same group |
| 13 | 512 | $143,360 | The same group. Its units have now lost $48.61 each on average |
| 16 | 4,096 | $1,146,880 | All 2,949 units of that group, and 1,147 of the group with no earner and no business ownership |
| 17 | 8,192 | $2,293,760 | 5,243 units of that second group are gone: $55.32 a unit on average |
| 18 | 16,384 | $4,587,520 | 13,435 are gone |
| 19 to 28 | 29,487 | $8,256,360 | Every unit of both no-earner groups. Then it stops |
| 29 | The county announces no relief for period 30 | | |

- From session 19 the claim has taken everything below it. 32,768 households have been reached and
  29,487 have a place. The rest stay home, and so does every household reached after them.
- The 38,837 units held by wage-earning households with a job-seeker are untouched, because those
  households pay the same as the ones asking.
- Households that lose can come. A reached household "no earner, with business ownership, on the
  roll" comes from session 13, and one "no earner, no business ownership, on the roll" from session
  17. Each brings one more. They are in the room and ranked below every household that is paid.
- If the player also opens the position "with earnings, with business ownership, no job-seeker", its
  households go to the top of the list. Sixteen sessions later about 50,600 of them hold units. They
  take the no-earner groups' units first, then the places of the wage-earning households that asked,
  and last 21,146 units from wage-earning households with a job-seeker. Opened in period 3, that
  position holds 53,302 of the 70,993 household units by session 20.
- At session 29 the county holds less cash than its first class costs. It announces no relief, and
  every household on the roll loses its unit whatever its place.

The player has three choices at the county: which position to open, in what order, and when. There
is no counter-move. Section 12 says so.

### What a new player notices within ten minutes

- The county pays its own offices and police first, and no claim can touch that money.
- The county ranks a household by the wage tax it pays. A household that pays nothing is at the
  bottom, whether it is in the room or not.
- Relief only moves up the list.
- A household comes only when the matter is worth its time, and every absence has a reason.
- Relief won lasts only while the households keep coming.
- One contact becomes two households, then four, then eight.
- A period spent at the county is a period not spent running food.

## 4. Goals, non-goals and anti-goals

**Goals**

1. Any Wayne household that has been reached makes a real decision from its own accounts, and a
   receipt explains it. Households nobody has reached are counted as such.
2. Each period the player chooses between the county and the aid road, and sees the answer the next
   period.
3. The county is an actor with an interest of its own. It pays its first class first, and it ranks
   households by what they pay it.
4. A household's living is read from accounts. MIM's reading is shown as a reading. With nation
   absent, nothing in this slice is presented as MIM's base.
5. A body's roll is written only by a household's own hours in the county's room.
6. Every rule is exact and repeatable: whole numbers and exact fractions, and no random draws.

**Non-goals for this slice**

- Rival organizers. Only the player's organizer opens a new position.
- A roll for the aid road. It arrives with the kitchen (section 11). **[Director]**
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
| Households are the smallest deciding unit. Budget groups are a Designed allocation of county totals. They are not counts taken from a source, and not person agents | ADR269; ADR270 |
| "Partitions such as class position, core and periphery, or political alignment must emerge from composed material relations at a declared scale. Any claimed partition must include an invariance proof under its declared coarse-graining." | Constitution Article II |
| "An actor's material position and conceived interest remain distinct dimensions. Their gap is a terrain of political struggle." | Constitution Article II |
| "All material effects become next-period intents and enter only the next four-week causal interval." "Player and non-player actors act through the same declared causal machinery." | Constitution Article III |
| "Designed values and mechanics are legitimate. Creators must declare them and keep them causally coherent with the rest of the model." A design liberty "must not bypass the causal circuit to manufacture an intended conclusion." | Constitution Article IV |
| "aid itself creates no agreement, membership, consciousness or worker-hours." | ADR270 |
| "A shared income source provides no evidence that residents belong to a single political organization." | ADR299 |
| The player is not the state and cannot legislate | Game Design Standard §2 |
| "One practice executes per organization per period." Old formats get no compatibility path | ADR262 |
| "A union local and a political police force both rank what they could do by yield per unit spent and fund down the list until the money runs out. Neither side gets a privileged mechanic." The difference between a state and a movement is "never a special rule in the ranking". What is declined is recorded with what remained | ADR184 R3, R4, R9 |
| "The first state opponent must have its own authority, objective, resources, and partial knowledge". A state actor gets no "heat scalar, primitive or fixed political-response curve" | ADR291 |
| "NO functional form — sigmoid included — may be IMPOSED on mechanics; sigmoid-shaped behavior must EMERGE from P(revolution)/P(acquiescence) dynamics and the algebraic Lawverian operations." | ADR172 ruling 5 |
| "A rule cannot impose a sigmoid or a second fixed response curve." "Do not infer live authority from an old ADR." | AGENTS.md |
| "carriers carry distributions (dispersion-preserving summaries), never bare means, at every grain" | Game Design Standard, the Jensen guard |
| "A new or redefined mathematical primitive, a relaxed constitutional prohibition, or a change to the reserved theoretical line needs a constitutional amendment. New governed content vocabulary does not need an amendment when it uses the current mathematics. It needs the applicable Director ceremony, schema and conformance updates, and a recording ADR." | Constitution Article VIII |
| Random draws only through a finite kernel with a receipt | ADR248 |
| Sums are preserved when counts are pushed to a coarser scale | ADR296 |
| Attributed membership is ratified, but its payload is empty, unhashed and unread, and filling it is a separate Director act | ADR189; ADR198 R4; PER-44 |
| "STRUCTURE IS THE PREMISE; MAGNITUDES ARE EARNED". What the player knows never enters the turn's hash | ADR182 R2 |
| Every value is Observed, Derived, Calibrated or Designed, and says which | Constitution Article IV |
| "Any line is playable — including wrong ones — and the sim never editorializes mid-run." | Game Design Standard §2 |
| Every construct has a writer, a reader and a sentinel. A construct that lacks one gets a recorded disposition | Game Design Standard W.1, W.2 |
| Every view states its decision question, its signals and how sure they are, what is hidden, its actions, its receipts, its Archive links, and whether it is an administrative display | Constitution Article VII |
| "Emergence claims need redundant evidence. The evidence includes control and shock twins, counterfactuals, and mutation tests that sever causal links. It also includes geographic and sector variation, persistence after the event, deterministic replay, and a direct-write audit." | Constitution Article VIII |
| The game is proved by play: recorded playthroughs kept as seed, action log and result | Game Design Standard §6 |

**Where this design does not yet meet a rule**

- *The Jensen guard.* The engine's budget groups carry totals only, so every household in a group is
  given the group's average. A whole position therefore comes or stays as one, and a few wages can
  lift a whole group on the county's list (section 12). The rule cannot be met until groups carry
  their spread, which is an open decision of the Game Design Standard. Disposition: BLOCKED. Section
  8, record 3.
- *Geographic and sector variation.* The slice has one county. Disposition: BLOCKED until a second
  county is in play. Section 8, record 12.
- *The floor and ADR172 ruling 5.* The Director ruled the floor. Whether a decision record is enough
  for it, or the ruling needs an amendment, is the Director's to say. Section 8, record 3, sets out
  the question.

## 6. Approaches considered

### The first slice

- **A. The County Review (chosen).** **[Director]** Who gets relief, and who decides. It gives the
  player a decision in one period and an answer in the next.
- **B. The Labor Ledger.** Who can afford to stop looking for work. It is needed and honest, but no
  organization competes for a group, results build over years, and it adds work to every county's
  turn.
- **An election first.** Dropped as a first slice. Most groups would have nothing at stake and would
  abstain, and the repository holds no citizenship data to build the electorate.

### The county

The Director was shown three rules on 19 November and chose the second. **[Director]**

- *Defends its own, counts heads.* The author's recommendation. Not chosen.
- *Defends its own, weighs by tax (chosen).* A household is weighed by the wage tax it pays.
  Households that pay nothing in cannot move the county.
- *Counts heads, with office grants on the table.* The first draft. The county had no interest of
  its own, and reform always worked.

### How "weighs by tax" becomes a ruling

Four forms were worked through. The Director chose the first after the re-check. **[Director]**

- **Rank by wage tax (chosen).** The county lists every household holding or asking for a unit by
  the wage tax it paid, and pays down the list. This is the form ADR184 requires: an organization
  ranks what it could do by yield per unit spent and funds down the list. The county's yield from a
  unit is the wage tax the household pays it. The third draft set ranking aside for a reason that
  held only for a version in which a household on the roll had to be in the room to be listed. In
  the version adopted, every unit on the roll is on the list whether or not its household comes.
- **A tax-weighted count, for less against.** The third draft. A household counted by its share of
  wage tax. The county granted units equal to the counts for less the counts against, and cut every
  unit by the same share. The re-check found that its "against" side could never matter in play: the
  cut stayed under $48 a unit until those asking outnumbered any defense about a thousand to one. It
  was also the rule of a referee and not of an actor with books of its own, and it was not in
  ADR184's form.
- **A refund.** Each household gets back the wage tax it paid, up to one unit. This was the author's
  first statement to the Director. It fails in the recorded run. The largest group's wage tax per
  household is $401 in period 2, $78 in period 4 and $42 in period 14, and below $48 nobody comes.
- **Counting heads inside the fixed total.** Offered again after the correction on MIM's sentence.
  Not chosen.

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

The re-check then found that two rulings pull against each other on the aid road. A household acts
only for its own money. Giving hours puts a household on a body's roll, and receiving aid never
does. In the engine the aid partners have no kitchen, site or stock, so the only households that
would give hours are the four that receive the food. The Director was shown three ways out and chose
the first. **[Director]**

- *No roll until the kitchen (chosen).* Food runs stay as they are. The roll arrives with the next
  slice, where the organization runs production with members' hours.
- *Working for one's own parcel counts.* Not chosen.
- *The kitchen in this slice.* Not chosen.

### Two choices the engine forced

**Which households have a stake.** **[Call]**

- *Treat each large group as one bloc.* Rejected. The largest group has 38,837 units among 456,528
  households. As a bloc, every household in it would hold a twelfth of a unit, when in fact some
  hold a unit and the rest hold none and can ask.
- *Count positions inside each group (chosen).* A group's households are split by whether they are
  on the roll. Section 7.2. The split is the county's record. The engine pays a group's line into
  one pooled account (section 7.1).
- *Split Wayne's budgets into real sub-budgets.* Sounder, and the likely home of nation and legal
  status. It changes the opening economy and needs a rule for splitting every stock. It belongs to a
  later slice.

**What kind of proceeding.** **[Call]**

- *Stretch the ADR299 hearing to many seats.* Rejected. The two seats are fixed in ten places in the
  contract, and the hearing happens once.
- *Keep the founding hearing as it is and add a recurring session (chosen).*

## 7. The design

### 7.1 The unit, the roll and the money for relief

- A **unit** is the county's support for one person for one period. It is one period of food at the
  opening price, which is $280 in Wayne. The engine's own formula sets it. This design adds no
  amount of its own. The engine stores each group's support as an amount of money, so the county's
  record keeps the unit price and each group's units, copied once from the opening lines.
- The **roll** is the list of units the opening gives each group: one for each job-seeking person.
  The county keeps it for the whole run. Every session starts from it.
- The **first class** is every line on the county's account that is not household support: the
  provider grants and, in a player's campaign, the City PD's line. No claim, ruling or record in
  this slice changes a first-class line, the spending limit or a tax. **[Director]**
- **Relief** is the total of the roll: $20,094,200 on the recorded figures. The review moves money
  only inside it. One household's gain is another household's loss. **[Director]**
- **Collective residence is outside the review.** **[Call]** It has persons and no households, by an
  engine rule, so nothing in it can come, ask or be ranked per household. Its 772 units, $216,160,
  are paid as they are today. That leaves 70,993 units, $19,878,040, for the review.
- **When the county is short.** After each close the county knows its cash. The money it has for
  relief next period is its cash, or its spending limit if that is lower, less its first class. That
  figure is never below zero and never above the total of the roll. If it is less than that total,
  the collective-residence line is cut in the same proportion **[Call]**, and the county pays the
  household list from the top with what is left. The households that pay least lose first.
  **[Director]** Today the engine would pay the support lines one after another in identifier order
  and leave one part-paid. This rule replaces that order for household support only. On the recorded
  figures relief is whole through period 29 and nothing from period 30, with no period in between.
- **Relief won is a level, not an addition.** A household that asks and is paid holds its unit for
  one period. It is paid again only if it comes again. **[Call]**
- **What the engine pays.** County support is paid into a group's pooled account, as it is today.
  After each session the county sets each group's line to the units its households hold on the list,
  times $280. Lines are whole units, so nothing is rounded. A group left with no unit has its line
  removed, and restored when it holds one again. The engine does not know which household holds a
  unit. The split of a group into households on and off the roll is the county's record, kept by
  this design.

### 7.2 Positions

A **position** is the set of households in one budget group that stand the same way toward the roll.
Each group has two: households **on the roll**, which hold a unit, and households **off the roll**,
which hold none and may ask for one.

- **Counting.** The engine holds each group's households. The county's record holds its units.
  Households on the roll are the smaller of the two numbers. The rest are off the roll. This places
  one job-seeker in each household until households run out. **[Record needed]** The placement is
  Designed. It decides how many households can ask, so it changes outcomes. The other bound is to
  stack job-seekers into as few households as possible.
- Every household in a group has the same place on the county's list, because the engine holds one
  wage-tax figure for the group.
- The three small named groups are positions of their own: the claimants (2 households, on the
  roll), the aid partners' households (4, off the roll) and the organization's own households (4,
  off the roll). Their households do not spill into the large groups they were carved from.
  **[Call]**
- Collective residence has no position.

| Position | In plain words | Whose claim it stands behind |
|---|---|---|
| With earnings, on the roll | A household with a wage and a job-seeker | Claimants' Assembly |
| With earnings, off the roll | A household with a wage and no job-seeker | Aid partners |
| No earner, on the roll | A household with no wage and a job-seeker | Claimants' Assembly |
| No earner, off the roll | A household with no wage and no job-seeker, for example retired or disabled people | Aid partners |

Each of the four appears twice in the engine, with and without business ownership.

### 7.3 Bodies and the county

A **body** is an organization whose claim households can stand behind at the county.

| Body | Today | In this slice |
|---|---|---|
| Wayne Relief Claimants Assembly | A fixed actor with a captured mandate. Its claim: "Keep current claimants on the relief roll while the county reviews their cases." | Its claim stands at every session. Households on the roll that come are recorded behind it. Coming does not protect a unit |
| Wayne Local Aid Partners | Four households and a fixed script. Its claim: "Hear the cases of residents who received no county support." | Its claim stands at every session. Households off the roll that come to ask are recorded behind it. It still receives food runs, as today (section 7.8) |
| Wayne County administration | Does not exist | New state actor. It announces the money for relief, writes the list and pays down it |
| City PD | The state opponent | Unchanged. Its line is in the first class |
| Wayne Organizing Collective | The player's organization | Not a body at the session. Its organizer reaches households |

- **The two claims stand for the whole run.** No body withdraws or changes its claim in this slice.
  **[Call]**
- **Neither body has an organizer of its own.** Only the player's organizer opens a position.
  **[Call]** So nothing starts at the county unless the player starts it. Section 12 lists this as a
  risk.
- **The player never legislates.** The player reaches a household. The household decides whether to
  come. The county rules.
- **Nobody joins the player's own organization in this slice.**
- **Opening reach.** The households the scenario records as authorizing each delegate start as
  reached: the 2 claimant households, and 3 of the aid partners' 4. **[Call]** They pay no wage tax.
  The three can never have a place on the list, and the two cannot protect their units. So the
  opening reach moves no money in this slice. It is kept because ADR299's minutes name those
  households.

**The county administration.** **[Record needed]** It follows the form ADR291 set for the City PD,
and it spends by the rule ADR184 sets for every organization.

| | |
|---|---|
| Authority | It sets the household support lines of Wayne's county-scoped public account, inside the money for relief. It cannot change a first-class line, the spending limit or a tax |
| Objective | Pay its first class in full. With what is left for relief, pay the households that pay it most. Its yield from a unit is the wage tax the household pays it |
| Resources | The account's cash. Holding a session costs it nothing in this slice **[Call]** |
| Knowledge | Its own account, its roll, the wage tax each budget group paid it, and who came to ask, by position. It cannot tell households inside a group apart. It does not see who was reached and stayed home, what the organizer chose, or anything hidden |
| What it cannot do | Arrest, coerce, close a session, change its own rule, or act on anything that is not in its own room or its own books |
| Receipts | A statement of its cash and its money for relief, its list with what it paid and what it declined, and the payment receipts the engine already writes |

The county's rule is fixed for this slice. A county board that can change it is later work.

### 7.4 A session, step by step

The county holds one session each period from period 4, after the period's accounts close. The
session sets the lines that are paid when the next period closes. Every step runs on whole
households, whole units and exact fractions. The list is worked out once, from the top. No step is
repeated.

1. **The county announces its money for relief** for next period (section 7.1), and the number of
   household units it pays for.
2. **The county ranks.** For each budget group it divides the wage tax it collected from the group
   in the period just closed by the group's households. That figure is the **place** of every
   household in the group: the more a household paid, the higher it stands. **[Call]** The county
   reads the tax it collected, not the tax it assessed.
3. **The roll goes on the list.** Every unit on the roll is listed at its household's place, whether
   or not the household is in the room.
4. **Households ask.** A household off the roll that has been reached may ask for one unit, behind
   the aid partners' claim. It goes on the list at its own place, below every unit of the roll at
   the same place.
5. **The county pays down the list** from the top until the units it can pay run out.
6. **Who comes to ask.** A household that asked comes only if the county's money reaches it.
   **[Call]** Otherwise it stays home and is recorded "no place". Leaving it out changes nothing
   above it, which is why the list is worked out once. If a position has more reached households
   than places, as many come as there are places.
7. **Who comes from the roll.** A position's loss is the number of its units that the county will
   not pay. A reached household on the roll comes if its share of that loss is worth its time
   (section 7.5). It is recorded behind the Claimants' Assembly. Its coming does not change the
   list.
8. **The record.** The county publishes its list: each position's place, units paid and not paid,
   households that asked and were paid, and what it declined and why.
9. **Payment.** The lines are paid at the next period's close, by the engine's existing payment
   step. They hold for that period only. The next session starts again from the roll.
10. **The spread.** Each household that came, on either side, brings one more household of its own
    position, who is reached from the next session (section 7.6).

Six details complete the rule.

- **Ties keep the holder.** **[Director]** A unit is never moved between households that pay the
  same. So a group's households off the roll never take from the same group's households on the
  roll.
- **Groups at one place lose together.** **[Call]** When units are taken from several groups at the
  same place, each loses in proportion to the units it holds, by largest remainder. If two
  remainders are exactly equal, that unit is not moved and the household asking for it finds no
  place. Households that ask from two groups at one place share the open places the same way. No
  rule reads an identifier.
- **Only wage tax ranks.** The engine does not tax ownership income. The tax that sites pay ranks no
  household. **[Call]**
- **If no household paid wage tax,** all stand at one place and nothing moves.
- **When hours are short,** fewer households come than have places (section 7.5). The units they
  would have taken stay with the next on the list. Positions are settled from the top, so this too
  is worked out once.
- **A household with no place is declined in a typed way,** as ADR184 R9 requires. The record gives
  the units left below its place, which is none.

The households of a position cannot be told apart, so the record holds how many came, never which.
### 7.5 What a household does

Every rule below runs on counts of households, never on individuals.

| Step | What it reads | What happens |
|---|---|---|
| Is it reached? | Section 7.6 | An unreached household does nothing |
| What is at stake? | Its position and the county's list | Off the roll: the unit it would be paid, if the county's money reaches it. On the roll: its share of its position's loss |
| Is it worth the time? | The session's hours and the wage | It comes only if its stake is at least the **floor**: 2 hours at $24, which is $48 today |
| Can it come? | Its group's free hours from the period just closed | Each household in the room spends 2 hours. If a group's hours run short, as many come as the hours cover, and the rest are recorded "no time" |

A reached household that does not come is recorded with one reason: no place, nothing at stake, not
worth the time, or no time.

Seven things about this rule are stated on screen and in the record. **[Record needed]**

- **A household reads only its own money and hours.** No rule reads solidarity, consciousness,
  nation or a class label. Nobody comes for someone else's gain. **[Director]** Article II calls the
  gap between material position and conceived interest "a terrain of political struggle". This slice
  models only the first of the two.
- **A household that asks has a whole unit at stake, or nothing.** A unit is $280, which is over the
  floor. So the floor never keeps home a household that has a place.
- **A household on the roll shares its position's loss.** **[Call]** The county drops units from a
  position, and nothing in the engine says which household held them. So every household on the roll
  in that position reckons the same stake: the units the position loses, times $280, divided by the
  units it holds. It comes when that reaches $48, which is when the position has lost a little over
  17% of its units. Below that the loss is real and nobody comes.
- **The floor compares two amounts the engine already holds.** **[Director]** It has no coefficient
  of its own: the hours come from the scenario and the wage from the economy. Section 8, record 3,
  asks the Director whether a decision record is enough for it.
- **Households in the same position move together.** **[Director]** A household comes because the
  matter changes its own income, not because its coming tips the result. So households on the roll
  come although the county does not weigh who is in the room. The engine gives this slice no other
  choice: it holds one set of accounts for a budget group, so every household in a position has the
  same figures.
- **A household that is ranked last still comes.** **[Call]** A household on the roll with no wage
  loses its unit like any other. By the ruling it comes. The record shows it as "in the room; ranked
  below every household paid". The other reading is that it stays home because its coming changes
  nothing; then the households that lose would never appear at the county at all.
- **An hour is valued at the going wage for every household,** including one that cannot sell an
  hour. **[Director]**

On the recorded run time is not scarce. The largest group has 128 million free hours in period 2,
and the two claimant households have 256.

**How this meets Article III.** **[Record needed]** Money moves one period later: a session only
sets lines that the next close pays. Reach moves one period later: a household brought at one
session is reached from the next. The player's review contact is chosen in one period and carried
out when the next closes, like every practice. The hours a household spends in the room are charged
against the period that has just closed, which is the period the engine's own check on household
hours expects. The City PD's operation already decides and acts after a close in the same way.
Record 7 must state this in the record's own words.

### 7.6 Reach

- **The organizer's contact.** The new choice, a review contact, spends the period's two organizer
  hours to reach one household in a position the player names. It is the same two hours the
  organizer spends today on a partner organization. Like every practice it is chosen in one period
  and carried out when the next period closes. A contact chosen in period 3 is in the session of
  period 4, and the unit it wins is paid when period 5 closes. The contact can be chosen from period
  3, the period after the founding hearing. **[Call]** **[Record needed]** The record must also say
  that an organization the engine runs may make the same choice. In this slice none does.
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
- **When no places are left,** the households that came still bring others. Those find no place and
  stay home. The position's reach then grows by the same number each period, and no more money
  moves.
- **Nothing can be called back.** **[Call]** The player can reach households in another position.
  The player cannot un-reach a household or stop it bringing the next.

The rate is Designed. The engine's time accounts show far more free hours than organizing uses, so
they cannot fix how fast it spreads. One contact for two hours is the only rate the scenario already
has, and this design applies it to every household that came.

### 7.7 The county's list: worked numbers

All five cases use the recorded period-4 figures, the household size assumed in section 3 and the
order of the list given there. They come from the script named in Appendix A.

**A small room.** 1,024 households with earnings and no business ownership, off the roll, have been
reached. The lowest units on the list are the 2,949 of the group with no earner and with business
ownership. All 1,024 have a place. The county pays them $286,720 a period. Their group's line rises
from $10,874,360 to $11,161,080. The other group's line falls from $825,720 to $539,000. Its units
have lost $97.23 each on average, so its reached households on the roll come. They are ranked last.

**Nothing left below.** 32,768 such households have been reached. Below their place are 29,487
units: every unit of both no-earner groups. 29,487 come and are paid. 3,281 stay home, "no place".
Their group's line is now $19,130,720, and both no-earner groups' lines are removed. The 38,837
units of the group's own households on the roll are untouched. The claim cannot grow further.

**A higher group asks.** Every household with earnings and business ownership that is off the roll,
about 50,600, has been reached. They stand first on the list. They take all 29,487 units of the
no-earner groups, and 21,146 of the 38,837 units held by wage-earning households with a job-seeker.
Those lose $152.45 a unit on average, and their reached households come. A wage-earning household
without business ownership that asks now finds no place. The business-owning group holds 53,302 of
the 70,993 units, $14,924,560 a period. The other wage-earning group's line falls to $4,953,480.

**The county is short.** Suppose the county can pay 40,000 household units and nobody asks. It pays
the list from the top: all 2,669 units of the group with earnings and business ownership, and 37,331
of the next group's 38,837. Neither no-earner group is paid anything.

**A tie.** In a player's campaign the two claimant households hold 2 units and pay no wage tax, the
same as the 2,949 units of the group with no earner and with business ownership. When 1,475 units
are taken at that place, the larger group loses 1,474 and the claimants lose 1. Half of the
claimants' units are gone, $140 a unit, and both claimant households come.

**What this shows.** Relief moves up the county's list and never down it. A household with no earner
loses first and can take nothing back. Among wage-earning households, those with a job-seeker are
safe from those without, and both lose to households that also own a business.

### 7.8 The second road: food runs

In this slice the aid road writes no roll. **[Director]**

**What exists today, and stays.** A local aid run moves up to 4 food parcels in a period from the
organization's own households to the aid partners' 4 households. The giving side spends 2 hours a
parcel. The run completes when the aid partners' households have eaten some of the food. The
organizing side is then charged 2 hours for coordination, and the aid partners 2 hours for their
response when they took part. Nothing records who took part.

**What this slice changes.** Nothing in the run itself. The organization has one practice a period,
so each period the player chooses between a review contact and a food run. The food run view shows
what the engine already records: the parcels the organization's households can spare, the parcels
delivered and eaten, and the hours each side was charged.

**Why no roll.** The Director ruled that giving hours to a body's work puts a household on its roll,
that receiving aid never does, and that a household acts only for its own money. On this road the
three cannot all hold today. The aid partners have no kitchen, site or stock. Their only work is
receiving the parcels. The only households that would give hours are the four that receive the food,
and a roll of them would be a roll of who received aid. So the roll waits for the kitchen: a site
the organization runs, staffed by members' own hours, where giving hours and receiving food are
different acts (section 11). Under the Game Design Standard its disposition is CHARTER, to that
slice. **[Record needed]**

**What limits the road today.** Food, not hours. The engine moves at most four parcels a run, one
run a period, and only food the organization's own households have left after they have eaten. In
the recorded run those households bought 8, 7, 4 and then 0 parcels in the first four periods, and
from period 4 the shops are empty for everyone. Food runs would stop there. That is the economy
running down, not a rule of this slice (section 12).

### 7.9 Rolls

- A household is on a body's roll for a period if it gave its own hours in the county's room behind
  that body's claim in that period. Nothing else writes a roll: not receiving aid, not a food run,
  not service use, not a shared income source, not being reached. **[Director]** **[Record needed]**
- A roll is a level. It is written afresh every period, from that period's hours.
- A roll says who came. It says nothing about what a household agrees with, and no rule reads it as
  agreement.
- Two things read it. The spread reads who came, to reach the next households. The views show it.
- For each body, position and period the record holds: households on the roll, hours given, what
  each was paid or lost, and households brought.
- A large roll does not make a body strong at the county. The county weighs what a household pays,
  not who is in the room.

**Where the record lives.** The session records are the first home of the rolls. They are hashed
with the rest of the turn's records. Writing the same counts onto membership links in the graph is
the hypergraph step the Director asked for: a body is one link over many positions, with the
households and hours on it. That step waits on two things outside this slice: the Director's act to
fill the membership payload (ADR198 R4; PER-44) and an accessor in the upstream graph library
(hypergraph-rs issue 2). Until then the graph payload is recorded as blocked on those two, which is
the disposition the Game Design Standard requires. **[Record needed]**

### 7.10 Class reading

- Each position shows a **livelihood profile**, Derived from its group's accounts for the period
  just closed: wages, ownership income, county support, mutual aid, and hours sold, owed at home and
  free.
- **MIM's reading is shown beside each source of income,** not as a label on the position.
  **[Call]** **[Record needed]** The amounts are Derived. The words are Designed and are marked so.
  - Beside wages: "MIM reads wage and salary income inside U.S. borders as labor-aristocracy income
    or higher, unless the earner is undocumented. Legal status and the wage-against-value term are
    not in this slice."
  - Beside ownership income: "MIM reads access to means of production as bourgeois or
    petty-bourgeois position. The accounts hold only income received from ownership, not access to
    credit."
  - Beside county support and mutual aid: no reading.
  - Where a position has neither wages nor ownership income: "No wage in this period. MIM's reading
    here turns on nation and legal status, which are not in this slice."
- The reading follows each dollar of income. It does not sort households into classes, and it is the
  same however households are grouped. No partition is claimed by it, so Article II's proof is owed
  only for the positions (section 7.14).
- No position is called "workers", "proletariat" or "the base".
- Nation shows as "pending" on every position.
- One line is on screen in every view of this slice: "This slice has no nation, no solidarity and no
  consciousness. Households act on their own money only." **[Director]**
- The class reading is displayed. No rule in this slice takes it as an input.
- Nothing in this slice is presented as MIM's base, and neither road is presented as MIM's road. MIM
  holds that "The principal contradiction inside the U$A is nation.", and nation is not in the
  slice.

### 7.11 What the player sees

Each view is a decision surface and carries the contract Article VII requires: its question, its
signals and how sure they are, what is hidden, what the player can do, what comes back, its Archive
links, and a statement that it is not an administrative display.

| View | The question it answers | What it shows | What the player can do from it | What comes back |
|---|---|---|---|---|
| County ledger | Is there relief money to move, for how long, and who is first in line for it? | The lines in pay order, the money for relief announced for next period, the county's cash, the roll by group, the order of the list | Nothing directly | Next period's payment receipts |
| Roster | Who lives here, how do they make a living, and where do they stand toward the roll? | Each position's sources of income with MIM's reading beside each, its units, its place on the list and, where earned, its dollar figures and how many are reached | Choose a position for a review contact | The contact's receipt |
| Preview | What would the next session do if I reached one more household here? | Whether a place is open, whose unit would be taken, and who would then have enough at stake to come | Confirm or cancel the contact | The session record |
| Session record | Who came, who was paid, who was ranked too low, and who stayed home and why? | The county's list, each position's choice and reason, each body's roll | Nothing directly | Next period's receipts |
| Food run | Is a food run worth this period's practice? | Parcels the organization's households can spare, parcels delivered and eaten last run, hours each side was charged | Choose a local aid run | The run's receipt |

**What is public and what is earned** (ADR182 R2). **[Call]**

- Public record: the county's lines, its money for relief, its cash balance, the two claims, the
  roll by group, the order of the list, and every session's list.
- Structure, shown for every position: which sources of income it has, and whether it is on the
  roll.
- Earned: a position's dollar figures (its wage tax per household, its income by source, its stake)
  and how many of its households are reached. The player sees these only for a position where the
  player has made a contact. For any other position the views show the structure, hide the amounts,
  and state the remedy: reach a household there.
- The preview needs only the public record: the order of the list and the units held below a place.
- The preview is something the player knows. It is never part of the turn's hash. It uses the last
  period the player has seen close, and says so. The session itself uses the period that has just
  closed, so the two can differ if wages or the county's cash moved in between.

### 7.12 State, order in the turn, and where the rules live

**New records,** all hashed with the turn except the preview:

- the county administration's configuration, with the roll and the unit price it keeps;
- for each position: households reached;
- for each session: the money for relief, each group's place, the list with units paid and not paid,
  each position's choice with its reason and hours, and what was declined;
- the support lines for the next period;
- each body's roll for the period;
- the organizer's review contact and its receipt.

**Order in the turn.** The period's accounts close. The organizer's practice is carried out, which
is where a review contact lands and a food run completes. Then the session runs: the list, household
choices, hours and the lines. The lines are paid in the next period's close. The engine already
stores the support lines in the turn's state. It accepts a new line, a changed amount and a removed
line, and requires every amount to be positive. Nothing writes them today.

**What the engine lacks for this,** as the readers reported it:

- A way to charge hours to a large budget group. The organizer's time layer charges only household
  groups bound to the organization and refuses any other. The layer below it accepts a use of hours
  from any group that has a time receipt. The session needs its own path.
- A way for an operation that runs after the close to change the support lines of the closed state.
  Today such operations rebuild only their own sections.
- A guard in the turn runner for a second operation after the close. Today it names the City PD's
  alone.

**Where the rules live.** Each new rule is a rule entry that calls a native operation, as the
organizer and City PD rules do, with its role, its evidence class and its attribution row. The
engine's list of native operations is closed, so the session needs a new one. Its allowance and
attribution rows arrive with the code, not before. The numbers stay in the scenario's defines file.

**Evidence classes.**

- Existing Designed values that this slice reuses: the unit ($280), the session's 2 hours, the
  contact's 2 hours, the $24 wage, the 15% wage tax, the budget groups themselves.
- Derived: wage tax per household, places on the list, the money for relief, units paid and not
  paid, stakes, rolls, the livelihood profile.
- New Designed rules, each needing a record (section 8): relief as a fixed total; ranking by wage
  tax collected per household; ties keeping the holder; groups at one place losing in proportion;
  paying from the top when short; collective residence outside the review; relief lasting one
  period; one session a period from period 4; the floor; a household on the roll sharing its
  position's loss; households in a position moving together; each one brings one, at 2 hours; one
  job-seeker to a household; the opening reach; the session roll; the words of the class reading.
- Observed: none directly. Calibrated: none.

### 7.13 Quantities that must balance

- For each position and session: households reached = households that came + households that stayed
  home, each with a reason. Unreached households are untouched.
- Hours charged = 2 for each household that came, plus 2 for each household brought. They are never
  more than the group's free hours.
- Places on the list are worked out from tax receipts and household counts. No number is written in.
- Units paid = the units the county's money covers, or every unit listed if that is fewer. Each unit
  paid to a household off the roll is a unit not paid to a household on it.
- No unit moves between households at the same place.
- Money: each group's line is whole units at $280. The household lines and the collective-residence
  line sum to no more than the money for relief. What is left over is less than one unit, and it
  stays with the county.
- The lines the county announces are the lines the next close pays, in full.
- First-class amounts, the spending limit and tax rates are the same as in a run with no sessions.
  Tax receipts and the county's cash need not be: relief paid to different households is spent
  differently, and that changes what the county collects. The difference is a result to report, not
  an error.
- Households reached in a position are never more than its households. Positions of a group sum to
  the group's households.
- A roll is never more than the households that gave hours that period.
- Persons, employment and the household lifecycle are untouched.
- No random draw anywhere. The same inputs give the same receipts and the same hash.

### 7.14 Why the grouping survives splitting and merging

Article II asks for a proof that a grouping does not change the result. The declared scale is the
county. The declared grouping is the position: budget group by whether a household is on the roll.

- **Relabeling changes nothing.** No rule reads an identifier. Ties keep the holder, groups at one
  place lose in proportion, and an exact tie between remainders moves nothing.
- **Splitting a group changes nothing beyond one unit.** Every figure a rule uses is the same for
  each household in a position: its place, what it asks, its share of its position's loss. If a
  group is split into parts with the same figures per household, the parts stand at one place, they
  gain and lose in proportion, and the totals of the original group are the same. The one exception
  is the exact tie: two equal parts can leave one unit unmoved in a session. Money is never rounded,
  because lines are whole units.
- **Merging changes the result.** Two groups that pay differently would be given one average place
  that neither has, so the list cannot be coarser than the budget groups. Merging the two positions
  of one group changes it as well: households on the roll would be treated as asking.
- **The limit of the proof.** It holds for the accounts the engine has. A budget group is itself a
  Designed allocation, and the engine gives every household in it the group's average. Households
  inside a group differ in ways the accounts do not show (section 12). Finer groups are later work.

Section 9 turns these statements into tests.
## 8. Decision records needed

The Director has made the seven decisions in section 2. Project law requires each to be written into
a decision record before it is built, and several of the author's calls need the same. The plan will
say how many records these become. The list is what must be decided and written down.

| # | Subject | What the record must say | Why it needs a record |
|---|---|---|---|
| 1 | The county administration, a second state actor | Its authority, objective, resources and knowledge, as in section 7.3. Only its list changes a household support line. The first class, the spending limit and taxes are closed to it. This partly supersedes ADR299's sentence "The county's ordinary fiscal accounts continue to determine payments." | ADR291 approved the City PD by name as the first state opponent. ADR184 requires a budget to have an owner |
| 2 | The county's rule | Ranking by wage tax paid, as the Director ruled. It is an ADR184 allocation: the county's yield from a unit is the wage tax the household pays, and every unit costs the same. The details the ruling left open: tax collected, per household of the budget group; groups at one place lose in proportion; an exact tie moves nothing; a household that asks comes only when a place is open; relief won lasts one period. The record must also say that a ranking by yield with no threshold is not a "fixed political-response curve" | ADR184 R3, R4, R9; ADR291 |
| 3 | The household's rule | Own money only. The $48 floor, as the Director ruled. A household on the roll shares its position's loss. Households in a position move together. A household ranked last still comes. An hour valued at the wage for every household. **A question for the Director.** ADR172 ruling 5 says "NO functional form — sigmoid included — may be IMPOSED on mechanics". AGENTS.md has the narrower "A rule cannot impose a sigmoid or a second fixed response curve." and says not to infer live authority from an old ADR. Article IV says "Designed values and mechanics are legitimate" when declared. The author reads the floor as a declared comparison of two amounts the engine holds, with no coefficient and no curve, for which a record is enough. If the Director holds that ruling 5 binds as written, the floor needs a constitutional amendment under Article VIII before it is built. The record also gives the Jensen guard's disposition: BLOCKED on the open decision about how groups carry their spread | AGENTS.md; ADR172; Constitution Articles IV and VIII; Game Design Standard |
| 4 | When the county is short | The list is paid from the top. Collective residence is outside the review and is cut only in proportion. The county publishes its cash, its roll and the order of its list at each session | It replaces the engine's identifier order for household support |
| 5 | Each one brings one | A Designed rate, the Director's. Two hours for each household brought. Nothing can be called back | It sets how fast anything spreads |
| 6 | The session roll | A household's own hours in the county's room put it on a body's roll for that period. The roll records who came, not agreement. Any Wayne household may be charged hours on its own recorded choice. This amends, for this one act, ADR262's "Neither operation writes solidarity, membership" and ADR270's rule on what creates membership | ADR270; ADR262; ADR299 |
| 7 | The review contact, and where the session sits in the turn | A new organizer choice, open to any organization. It is new content vocabulary, so it needs the Director's ceremony, schema and conformance updates and a recording record. The record says how it sits with the nine verbs of ADR177. It also states the Article III reading of section 7.5 | Constitution Articles III and VIII |
| 8 | Placing job-seekers into households | One to a household until households run out, declared on screen | It is Designed and changes outcomes |
| 9 | The class and nation text on screen | As in section 7.10: a reading beside each source of income, and no label on a position | The ideological line is the Director's |
| 10 | The aid road's roll | CHARTER: no roll in this slice. It arrives with the kitchen | The Director's ruling; Game Design Standard W.2 |
| 11 | The graph payload | Either "blocked on PER-44 and hypergraph-rs issue 2", or the Director opens the payload ceremony in this lane | ADR198 R4; Game Design Standard W.2 |
| 12 | Opening conditions and evidence gaps | The first session in period 4. The opening reach of 2 and 3 households, which moves no money. The two standing claims. No organizer for either body. Geographic and sector variation recorded as BLOCKED, because the slice is one county | They are Designed; Constitution Article VIII |

## 9. Build order and proof

The engine has no recurring proceeding, no action that reaches a household outside the organization,
no change to a budget line after the opening, and no state actor that rules on anything. Each piece
below can be played or checked on its own.

| Piece | What it adds | How it is proven |
|---|---|---|
| 1. The ledger and the roster | The county ledger with the money for relief, the county's cash, the roll and the order of the list. The roster of positions. The food run view of the hours the engine already records. Read-only: no rule and no stored state changes | Every figure equals the engine's own receipts. Positions sum to each group's households. No existing hash moves |
| 2. The session | The review contact, the list, household choices, the lines, the rolls, the spread, the session record and the preview | The proof list below |
| 3. Rolls in the graph | The rolls written onto membership links, with their hash section. Only after record 11 opens it | The graph counts equal the session records every period. The new hash section is absent when empty, so no existing hash moves |

**The proof list for piece 2.** Each line is a test or a recorded run, written before the code it
proves.

- **Balances.** Every line of section 7.13 as a property test.
- **Twins.** The same opening run twice: once with the player's first contact and once without.
  Without it no unit moves: every line the county sets is the roll's own, and the session records
  hold only the households reached at the opening, each staying home with its reason. On the
  recorded opening every payment equals today's run.
- **What the review cannot touch.** In every run, with or without sessions, every first-class
  amount, the spending limit and every tax rate are identical. The differences in tax receipts and
  county cash between the twins are measured and reported.
- **The county keeps its word.** In every period the lines the county announced are the lines it
  paid.
- **Counterfactuals.** Give every group the same wage tax per household, and nothing moves. Swap the
  wage tax of two groups, and relief moves the other way. Set a position's loss per unit one dollar
  under the floor and one dollar over: its reached households stay home, then come. Set the money
  for relief to nothing: nobody is paid.
- **Sever tests.** Each of these links is cut in turn by a deliberate fault, and a test must fail:
  tax receipts to places on the list; places to who is paid; the list to next period's lines; the
  lines to the payments; a position's loss to who comes; coming to the roll; the roll to who is
  reached next; the contact to who is reached.
- **Direct-write audit.** Only the county's list writes a household support line. Only a household's
  recorded choice charges its hours. Only the session writes a roll. The scenario writes none of the
  results.
- **Replay.** Replaying and reopening a campaign gives the same receipts and the same hash, byte for
  byte.
- **The grouping.** The four statements of section 7.14.
- **Persistence after the event.** The player makes one contact and never returns to the county. The
  claim must keep itself going, stop when nothing is left below it, and end when the county's money
  for relief ends.
- **A witness for every outcome.** Each outcome the records can name is reached in at least one
  committed opening, by changing opening conditions only: paid a unit; no place; a group's
  households on the roll untouched by the same group's households that ask; a higher group taking
  from a lower one; in the room and ranked last; a loss under the floor; no time; no money for
  relief; the county short and paying from the top; an exact tie; a position with nobody left to
  reach.
- **Ceremonies.** Baseline changes carry the required trailer. Schema and conformance contracts
  change with the code. The allowance and attribution rows for the new operation arrive with it.

**What cannot be shown yet.** Article VIII also asks for geographic and sector variation. The slice
has one county, so that evidence is recorded as BLOCKED (record 12).

**Play proof for the whole slice.** Four recorded playthroughs from the same seed, each run past the
period in which the county runs short, each driven through the real client with no screen, and each
kept as seed, action log and result. They differ only in the player's line: no contact at all;
opening the wage-earning position; opening the business-owning position; food runs only. They must
give four different records that the receipts explain. The tutorial chapter that walks a new player
through the first session is the acceptance script.

**Views.** Each view of section 7.11 ships with its decision-surface contract and its links into the
Archive.

## 10. Left to the builder

- The names and shapes of the new records and of the review contact, within ADR262's rule of one
  practice a period.
- Whether the county administration is a graph node, as the City PD's agency is, or a register only.
  ADR184 requires the money for relief to have an organization as its owner.
- How the list is worked out exactly. The existing allocator ranks by a floating-point ratio and
  breaks ties by identifier. The session needs an exact ranking with the tie rules of section 7.4,
  as a version of the allocator or beside it, with the same typed result.
- Whether the session is one native operation or two: the households' choices, and the county's
  list.
- How the session charges hours to the large budget groups (section 7.12).
- How an operation after the close changes the support lines of the closed state, and the guard the
  turn runner needs for it.
- How the county's figure for its money for relief is made to match the engine's payment step
  exactly. Section 9 holds the proof.
- How a group's line is removed when the group holds no unit, and restored.
- Where the views sit in the client, and the projection that feeds them.
- Whether the existing collection choice, which names a household and carries a class target field,
  falls under the anti-goal on class labels.
- Version bumps. The organizer format is version 12 today and has no compatibility path.
- The exact wording of on-screen text, within section 7.10.

## 11. After this slice

- **The kitchen.** A site owned by an organization, staffed by members' own hours, whose output goes
  to those who worked. It is where the aid road gets its roll. **[Director]** It needs a production
  rule and the Director's rulings on it.
- **Who can show up.** Wayne's budgets split into real sub-budgets, so that a position has accounts
  of its own and households inside a group can differ. Labor status as a group decision. Nation,
  legal status and the wage-against-value term.
- **Rivals and masses.** A second organizer that opens positions for itself. Businesses as a body at
  the county, ranked by the tax their sites pay. Organizing that spreads through workplaces. Opening
  rolls from observed union membership.
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
  county alone sees the roll paid unchanged until period 30. The loss a claim causes is a loss the
  player chose.
- **There is no counter-move at the county.** Turning out cannot protect a unit, and nothing the
  player starts can be called back. The player chooses which position to open, in what order and
  when, and then watches. This follows from the Director's rulings, and it is what the slice shows.
  It leaves the player a few large decisions at the county, not a contest every period.
- **The first year is slow.** One household becomes 8,192 over fourteen sessions. Little money moves
  until late.
- **Places rest on group totals.** The engine holds one set of accounts for a budget group, so every
  household in it is given the group's average. Four wages in the group with no earner and no
  business ownership put all of its 143,200 households above the group with no earner and with
  business ownership. A player who opens that position moves 2,949 units to it on the strength of
  those four wages. The Game Design Standard's rule against bare averages is not met, and cannot be
  until groups carry their spread.
- **Whole positions come or stay as one,** for the same reason.
- **Households that are ranked last keep coming.** By the rule they come every period that their
  position's loss is worth $48, and it changes nothing for them. Their rooms double each period.
  When the county stops paying relief altogether, every reached household on the roll comes each
  period for as long as that lasts. Section 7.5 gives the other reading.
- **Some households can never be paid at the county.** These are the households that pay no wage
  tax: the claimants, the aid partners' own four, the organization's own four in the recorded file,
  and every household in the group with no earner and with business ownership. The aid partners'
  claim speaks of "residents who received no county support". In practice only households with a
  wage can carry it.
- **The floor does little here.** It never keeps home a household that asks. It only delays
  households on the roll.
- **The second road writes no roll in this slice,** moves at most four parcels a period, and in the
  recorded run ends by period 4.
- **The worked figures rest on an assumed household size** for three of the four large groups. The
  engine holds the real numbers.
- **Money is pooled.** A unit is paid into a group's account. The engine cannot say which household
  received it. Every figure for a household is the county's record laid over a pooled account.
- **The order of the list can change.** The worked figures hold the period-4 order for two years. In
  the recorded run the largest group's wage tax per household falls from $401 in period 2 to $42 in
  period 14. If a group's wages stop, its households fall to the bottom of the list.
- **Moving relief changes the county's own income** (section 7.13). How much has not been measured.
- **The preview can be one period stale.**
- **The floor's standing in law is the Director's to settle.** Section 8, record 3.
- **Turn time.** On the recorded runs the organizer's turns took 11 to 16 seconds, and the
  qualification report records several turns over the 30-second budget. The session adds work to
  every Wayne turn, and that work has not been measured.
- **The recorded figures come from one seed and an older world format.** That run has no City PD and
  no claimant group. A player's campaign has both.
- **The format has no compatibility path.** Changing the organizer records resets saved campaigns,
  as ADR262 intends.
- **This draft's rules have been run, not re-read.** The rule sections were rewritten after the
  re-check. The author checked them by running the rules in a short exact script on the recorded
  figures. No fresh reader has read this draft.

## Appendix A: Engine facts

**Read by the author in the code or the recorded data.**

- County payments: for each public account the amount available is the lower of the spending limit
  and the cash above the floor. Each line is paid the lower of its amount and what remains, in list
  order (`rust/crates/babylon-material-circuit/src/financial/close.rs:100-134`).
- Household support is job-seeking persons times one period of food at the opening price
  (`rust/crates/babylon-persistence/src/national_economy/opening/financial.rs:126-145`). The engine
  stores the result as an amount for each group. It stores no count of units.
- The engine's state holds households and persons for every budget group. An ordinary group must
  have at least one household. A collective residence must have none
  (`rust/crates/babylon-material-circuit/src/recurring/model.rs:23-45`).
- The allocator of ADR184 ranks whole candidates by a floating-point ratio of yield to cost, breaks
  ties by the candidate's own fields, and records each one it could not afford with what was left
  (`rust/crates/babylon-graph/src/capacity.rs`).
- A use of household hours is accepted only for the period before the state's own
  (`rust/crates/babylon-material-circuit/src/household_time.rs:594-601`). The organizer's time layer
  refuses a contributor that is not bound to the organization
  (`rust/crates/babylon-tick/src/material_world/organizer_time.rs`).
- Scenario numbers (`content/scenarios/national/defines.toml`): wage $24 an hour; 160 working hours
  a person a period; wage tax 15%; one period of food support; `contact_hours = 2`;
  `contributor_hours_cap = 8`; aid of at most 4 parcels at 2 hours each; the hearing in period 2,
  the review in period 3, `attendance_hours = 2`, authorizing households 2 and 3; the two claims
  quoted in section 7.3.
- The player's choices are `Inquiry`, `Collect`, `LocalAid`, `RemoteAid`, `Reinforce`, `Hold`,
  `PauseStanding`, `ResumeStanding` and `InviteToHearing`
  (`rust/crates/babylon-practice-contract/src/organizer/types.rs:121-131`). The organizer format is
  version 12.
- Recorded data, campaign `5efafb84`, seed 319, in
  `reports/economic-flows-qualification-2026-11-14-assets/`: the county's lines, cash and first
  unfunded period (`wayne-public-allocations.json`); group persons, support, wages and ownership
  income at period 4 (`wayne-p4-households.json`); the largest group's households and its wages at
  periods 2 and 14 (`wayne-household-period-2-v10.json`,
  `national-demographic-financial-horizons-v10.json`). The period-4 file lists seven groups: the
  five of section 3, and an 8-person and a 4-person group with no wage and no support.
- Turn times are from `reports/economic-flows-qualification-2026-11-14.md`.
- The claimant and aid figures come from a second recorded campaign, `e841f4b2`.
- The worked figures of sections 3 and 7.7 come from a short exact script that the author ran with
  `python3 -I` on the figures above. It applies the rules of section 7.4 in whole units and
  fractions, and checks that the lines sum to the money for relief in every session. The script is
  not in the repository.

**Reported by read-only readers on 18 and 19 November 2026, and not all re-read by the author.**

- The organizer has 2 committed hours a period. No existing choice reaches a household outside the
  organization's own. The collection choice names one of the organization's own households.
- Every household group pays wage tax at 15% on wages accrued in the period, out of the cash it has
  left after its purchases. The receipt holds the amount assessed, the amount collected and the
  difference. Ownership income is not taxed. Sites pay a separate tax on operating income. All of it
  goes into the one county account that pays grants, support and the City PD.
- Tax receipts are written each period and can be read by an operation that runs after the close in
  the same turn. They are not kept in the turn's state afterwards.
- Paying grants and support is the first money step of each close. Nothing moves the county's cash
  between the end of one close and that step of the next.
- The engine accepts a new household support line, a changed amount and a removed line. Every amount
  must be positive. Nothing checks support against job-seekers after the opening. A changed line
  takes effect at the next close.
- When cash is short, lines are paid one after another in list order and one is part-paid. In the
  recorded run the grants take all the cash from period 30 and household support is paid nothing.
- The City PD's contract, its native operation and its allowance and attribution rows, as the form
  for a second state actor. No record bars a second one. The turn runner's guard names the City PD's
  operation alone.
- The engine's native operations are a closed list of four.
- An operation after the close can rebuild its own sections of the closed state. None changes the
  support lines today.
- Local aid: food comes from the giving households' own surplus, at most 4 parcels a run and one run
  a period, at 2 hours a parcel. Coordination is charged when the run completes, and the partner's
  response when the partner took part. The aid partners in the engine are four households with a
  script. They have no site, no stock and no roll.
- The food shortage from period 4 is a shortage on the shelves. The largest group had money for
  every parcel it asked for, and the shop delivered 23.
- The hearing's two seats are fixed in ten places, by one reader's count. One hearing per campaign.
  The review only writes a record.
- The membership payload is an empty marker. The upstream gap is hypergraph-rs issue 2.
- The client has no ledger, roster or roll view.

## Appendix B: MIM's line on the points this design touches

All from the fact-checked findings in `docs/gameplay/research/40-class-agents-evidence.jsonl`. Each
quotation is exact. None of them is the ground for a rule of this slice. The rules are Designed, and
the Director chose them. The quotations say where MIM's line bears on what the slice shows, and
where the slice cannot yet show it.

- On money and ballots: "The ballot power of the oppressed is not greater than the financial power
  of the capitalists." (mim-on-other-lines F10). MIM says this of electoral socialism. It sets the
  oppressed against capitalists. Neither is in the county's room: the rule of this slice ranks
  wage-earning households above households with no earner. The sentence is not a ground for that
  rule.
- Who counts as labor aristocracy: "salary and wage-receiving people within U$ borders are
  labor-aristocracy or higher, unless they are undocumented." (mim-class-structure MC-02). Legal
  status is not in this slice, and the text on screen says so.
- On the public sector: "In some ways, the government sector is the ultimate expression of the
  imperialists' loyalty to the oppressor nation working class, since it is difficult to ship
  government service jobs overseas." (mim-class-structure MC-21). MIM is speaking of nation and of
  government jobs. This slice has no nation, and its first class is grants to public sites, not a
  payroll. The sentence grounds nothing here. It is a reason for a later slice to look at whom the
  county's money employs.
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
  (mim-practice F01). This task is not modelled in the slice. A food run is aid, which MIM ranks
  below that task, and nothing here is an institution of the oppressed.
- Relief is limited: MIM "believes that as a strategy charity can never provide more than temporary
  and limited relief." (mim-practice F07).
- Nation comes first: "7. The principal contradiction inside the U$A is nation." (mim F09). Nation
  is not in this slice, so nothing in it is presented as MIM's base.
- Two findings bear on a later slice with elections, and on nothing here: "The majority of white
  Amerikans support or participate in the electoral system." (mim F15), and "It is possible that in
  elections to city hall, some small battles can be won locally" (mim F14).

## Appendix C: What the reviews found, and where this draft answers them

The second draft was reviewed on 19 November 2026 by four readers, and a second reader challenged
each serious finding (workflow journal `wf_f30fdb94-a47`). The third draft was re-checked the same
day by three readers (`wf_e6abc7ce-3a0`).

**The review of the second draft**

| Finding | Answer |
|---|---|
| The organizer has 2 hours a period, not 8, and no operation contacts a household | Section 7.6: one review contact a period, as a new choice |
| Collective residence has no households | Sections 7.1 and 7.2: it has no position and is outside the review |
| "Pay first" cannot be built | Removed |
| The recorded run has no City PD and no claimant group | Sections 3 and 12 say so |
| Provider grants go to every public administration site | Section 7.1: the whole first class is off the table |
| The ruling needs a new native operation | Section 7.12 |
| Group persons and households are Designed, not Observed | Sections 5 and 7.12 |
| Units only ever grow | Section 7.1: relief won lasts one period |
| The stake was defined twice | Section 7.5 |
| Objectors saw only one session's increment | Section 7.5: a household on the roll reckons its position's whole loss |
| The placement rule was said not to move money | Section 7.2 says it changes outcomes, and it needs a record |
| The grouping proof showed signs, not outcomes | Section 7.14 and the tests in section 9 |
| "Restore" was circular, and choices came down to identifier order | "Restore" is removed. No rule reads an identifier (sections 7.4 and 9) |
| No rule read the membership roll | Section 7.9: the spread reads it |
| The county had no interest of its own | Sections 7.3 and 7.4: it ranks by what it is paid |
| The $48 floor is a step and needs a ruling | Section 7.5 and section 8, record 3 |
| A new organizer choice needs a ceremony and a record | Section 8, record 7 |
| The preview showed a site's cash before any contact | Section 7.11: no site figures are shown, and a position's figures are earned by contact |
| The build plan lacked sever tests, the direct-write audit, ceremonies, decision-surface contracts and archived playthroughs | Section 9 |
| The reason for withdrawing tax weighting was wrong | Section 6 and Appendix B |
| Two quotations were bent | Appendix B gives them exactly and claims less for them |
| A county that always concedes makes reform always work | Sections 7.1 and 7.7: the county gives up nothing of its own, relief only moves up its list, and it ends when the county's cash does |
| Only the county session wrote membership | Still so, by the Director's ruling. The aid road's roll waits for the kitchen (section 7.8) |
| No line here can be called MIM's base | Sections 4 and 7.10 |
| "Labor aristocracy" was too narrow for owner groups | Section 7.10: the reading follows each source of income |

**The re-check of the third draft**

| Finding | Answer |
|---|---|
| The food-run roll was written by the households that receive the food | Removed by the Director's ruling. Section 7.8 and section 8, record 10 |
| ADR172 ruling 5 was cited through a weaker sentence, and Article VIII's amendment clause was passed over | Section 5 quotes both. Section 8, record 3, puts the question to the Director |
| The count by share of tax was the Director's to decide, and was not in ADR184's form | The Director ruled the ranking. Sections 6 and 7.4 |
| The defense could never matter | The county no longer counts a defense. Sections 7.4 and 12 |
| A household's stake was not money the engine moves | Section 7.1 says what the engine pays. Ties keep the holder, so a group never pays for its own gain. Section 7.5 gives the stake of a household on the roll |
| Tax receipts cannot be identical with and without sessions | Sections 7.13 and 9 |
| The order of the claim and the defense left two readings | Section 7.4: the list is worked out once |
| A fixed tie order reads identifiers | Section 7.4: no rule reads an identifier |
| The count left out collective residence's tax, and did not say collected or assessed | The count is gone. Sections 7.1 and 7.4 |
| Two places disagreed on when a contact first counts | Sections 7.4 and 7.6 |
| Some positions can never act | Section 12 says which |
| Rules clashed when more households asked than the roll held | Section 7.4: a household comes only when a place is open |
| The second road was presented as MIM's road | Sections 7.8 and 7.10, and Appendix B |
| Two quotations were made to carry more than they say | Appendix B |
| The class reading was a label by budget group | Section 7.10: a reading beside each source of income |
| Article VIII's sentence was cut | Section 5 quotes it whole. Section 9 adds persistence and records the gap |
| Amounts were shown for positions the player had not reached | Section 7.11 |
| Article III was not shown for households' acts | Section 7.5 and section 8, record 7 |
| No path charges hours to a large group | Sections 7.12 and 10 |
| Turn time was understated | Section 12 |
| "No operation contacts a household" was too broad | Sections 1 and 10, and Appendix A |
| The engine stores amounts, not units | Section 7.1 and Appendix A |
| The allocator ranks by a floating-point ratio | Section 10 |
| "Wayne City PD" is not the engine's name | Section 7.3 |
