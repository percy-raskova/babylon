# The County Review: design

**Status:** Sixth draft, 19 November 2026. The Director read the fourth draft, said it "looks good
elsewise", and gave three instructions. The fifth draft applied them and was checked by three
readers. This draft fixes what they found. The Director then said to write the plan and begin
building. The plan is `docs/superpowers/plans/2026-11-19-county-review.md`. Later that day the
Director said that one part of the rule of thirds belongs in this slice: who works and who does not.
Sections 2, 3, 7.2, 7.10, 7.11, 7.13, 8, 11 and 12 and Appendix D.3 were amended for it. Building
had begun, and no built task was changed by it.

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
of the wage tax that household itself paid, and pays down the list until the money runs out. A
household that has been reached comes when its own money is at stake and the matter is worth its
time. Every household that comes brings one more. The next period's receipts show who gained, who
lost, and who was in the room and ranked too low to be paid. A period the player spends at the
county is a period not spent running food to the aid partners.

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
| 19 Nov, on reading the fourth draft | The police budget | "the police having a $24 budget is ridiculous and not at all realistic" |
| 19 Nov, on reading the fourth draft | How populations are counted | "we should use Lawvere's to aggregate/deaggregate the agent-populations in a principled way" |
| 19 Nov, on reading the fourth draft | Ruling 5 of ADR172 | "ruling 5 also survives as written about laws, modify the constitution" |

The last three rows give the Director's words with the spelling corrected. The Director also ruled
that the game's ideology sides with MIM, and that MCU and FRSO are settler organizations opposed to
MIM's line. Neither is a source for method here.

**How this draft reads the three new decisions**

- *The police budget.* The force is already employed and paid inside the county's public workplaces.
  The books showed only the price of one visit. The City PD's payroll is now named in the county's
  books, sized from a named count of positions at the engine's own hours and wage. The engine's
  lines and the county's total do not change. Section 7.3.
- *How populations are counted.* Lawvere's rules for quantities are applied to every count in this
  slice. Counts and money add up. A rate is one total divided by another. A group is split only by a
  declared rule that adds back exactly. No rule decides for a household from a group's average.
  Sections 7.2 and 7.14, and Appendix D.
- *Ruling 5.* The fourth draft had said that if ruling 5 of ADR172 binds as written, the $48 floor
  needs a constitutional amendment before it is built. The Director's answer is read as two
  instructions. Ruling 5 is live law as written, so the Constitution must carry it. And the
  amendment that the floor needs is to be made. Amendment AM does both, and says so (Appendix E). It
  writes the ruling into Article III in its own words. It then states that a rule may decide for one
  member of a population by comparing material amounts that the engine holds for that member, and it
  bars a constant placed to set where a response turns. That second part is the author's wording,
  and its record stays proposed until the Director accepts it.

**The Director's direction after the fifth draft** (19 November 2026)

- *Build.* "Check what you have to check one more time, then write the plan out and begin
  implementing it." The stopping point is a playable first slice.
- *The rule of thirds.* "lets also consider as an anchoring law the generalized rule of thirds: 1%
  of the pops owns 1/3 of the wealth, 1-10% own next third, 10-50% own last third, >50% have net
  zero wealth". It is the lane's law for the opening split of household wealth. This slice holds no
  household wealth, so the shares of wealth bind the next slice (section 11, and section 8, record
  15).
- *Who works.* The author then told the Director that the law changes nothing in this slice. The
  Director answered: "the rule of thirds is relevant, not in its entirety right now, but we know
  that roughly 40% of the population makes its living from selling wage labor so that's 40% of the
  population at least who must work, the top 1% do not work they live entirely off investments, the
  next top 10% some work some live off investments or they are retired, the bottom 50% work but are
  more likely to receive welfare and require aid and they don't own homes, i think the proportions
  of populations who aren't and are working are relevant to this point in the game at least". So the
  four bands of the law are on the roster in this slice, and the opening obeys what the Director
  said of the work of each band (section 7.2).
- *Unemployment in the next 40%.* The author's first form of that amendment kept every job-seeker
  out of the next 40%. The Director answered: "yes but the next 40% can have unemployment too, so
  they can be looking. i think this is a good start though. lets work on actually getting it made".
  So the next 40% is filled by the number of people at work alone, and it takes its share of
  job-seekers and units with it (section 7.2).

**Things the author told the Director that were wrong**

1. *The ground for weighing by tax.* The author offered that option as the closest to MIM's sentence
   on ballot power and the financial power of capitalists. The sentence does not support it
   (Appendix B). The author said so before the Director ruled on the county's rule, and the Director
   kept the weighing. It stands as a Designed rule that the Director chose. It is not taken from a
   MIM text.
2. *How the weighing works.* The author first said the rule would be a refund of wage tax, then
   drafted a count of households for and against. Both were formulas of the author's own. Project
   law already gives the form for an organization that divides a budget (ADR184), and the Director
   has ruled that form.
3. *The floor.* When the Director ruled the ranking, the author said the $48 floor "never keeps
   anyone home in this slice". The fourth draft then withdrew that, and said a household on the roll
   comes only when its position has lost a little over 17% of its units. The fourth draft was the
   one in error. It applied the floor to a position's average loss. That is the form the Director's
   ruling in ADR173 replaced: a rule applied to a class's average in place of its members. Each
   household either loses its whole $280 unit or loses nothing, and $280 is over the floor. The
   first statement stands (section 7.5).
4. *Household counts.* The fourth draft worked out three groups' households at 2.62 persons each and
   got about 53,300, 143,200 and 15,900. A replica of the engine's opening allocation gives 50,726,
   173,995 and 19,334 (Appendix A says what was checked against a run). The two groups with no
   earner have 2.16 persons a household.
5. *The rule on bare averages.* The fourth draft called it "an open decision of the Game Design
   Standard" how a group carries its spread. The Director ruled that in July (ADR176, ruling 17;
   ADR194, ruling R1).
6. *The fifth draft's worked tables.* They counted wage earners as full-time, which the design's own
   rule for a place does not do. They also spread the units of the group with business ownership
   over households of working owners, who cannot hold one. The tables are withdrawn. Section 3 says
   what is known without them.
7. *The rule of thirds.* The author told the Director that the law "changes nothing in this first
   slice", because the slice holds no household wealth. The Director corrected it: the law also says
   who works and who does not, and those proportions belong here. The sixth draft was amended for
   it. The amendment's first form then gave the next 40% no household that was looking for work. The
   Director corrected that as well: the next 40% can have unemployment too.

**What changed since the last draft**

- A household's place on the county's list is the wage tax on its own wage. It is no longer its
  budget group's average.
- The households of a budget group are counted into positions by the workplace their people are
  bound to, and by how many of them are at work. The roster of positions is kept in whole numbers
  and adds back to the engine's counts every period.
- A household on the roll comes when its own unit is not paid. The rule that it shared its
  position's average loss is withdrawn.
- Relief moves from households with no wage to households with a wage, in every budget group. It no
  longer moves from one budget group to another.
- The group "with earnings, with business ownership" is no longer first on the list. A household
  that lives on ownership income and has no wage pays no wage tax, and stands at the bottom.
- The City PD's payroll is in the county's books.
- Ruling 5 is in the Constitution, as Amendment AM, with a stated limit on what a household's rule
  may compare.
- The roster's rules now cover every case the engine produces: a household with three people at
  work, working owners, and people who leave the labor force by age.
- The worked tables of the fifth draft are withdrawn (section 3).
- Facts corrected: household counts, how wages are paid, what the engine holds for each budget
  group, where the $24 comes from, and who is paid for the City PD's hour (Appendix A).
- Amended after the sixth draft: every position carries its band in the rule of thirds, the opening
  obeys the Director's statement of who works in each band, and the views count who works in each
  band every period.

**The author's calls, for the Director to check while reading**

1. A household that asks comes only when a place is open for it. It is never sent away (section
   7.4).
2. Positions at the same place on the list lose in proportion to the units they hold, and an exact
   tie moves nothing (section 7.4).
3. A position is one budget group's households bound to one workplace and one way of being paid
   there, by how many of their people are at work, how many are looking for work, and how many units
   they hold (section 7.2).
4. A household's place is its people at work, times what its crew was paid for each person at work,
   times the wage tax rate, times the share of its group's wage tax that the county in fact
   collected. The list is strict, so cents can decide between two workplaces (section 7.4).
5. Six placements are declared, because the engine holds people by workplace and holds no household.
   Households are bound to crews by their people. People at work are spread evenly. Job-seekers at
   the opening go to the households with the fewest people. A hire takes a job-seeker from the
   households with the fewest at work. A layoff takes from the households with the most. Equals
   share in proportion (section 7.2 and Appendix D).
6. Units a position is not paid fall on its reached and unreached households in proportion (section
   7.5).
7. A household that is ranked last still comes when its unit is not paid, and is recorded in the
   room (section 7.5).
8. A household that came brings one more household of its own position, so one bound to the same
   workplace (section 7.6).
9. Relief won lasts one period. It is paid again only if the household comes again (section 7.1).
10. Collective residence is outside the review. Its line is cut only in proportion when the county
    is short (section 7.1).
11. Neither body has an organizer of its own. Nothing starts at the county unless the player starts
    it, and nothing the player starts can be called back (sections 7.3 and 7.6).
12. A household that came spends 2 more hours to bring the next one (section 7.6).
13. The county publishes its roll, the order of its list and its cash. It does not publish the wage
    tax behind a rank. A position's dollar figures and its number of households are earned by
    contact (section 7.11).
14. The first session is in period 4, and the review contact can be chosen from period 3 (section
    7.6).
15. MIM's reading is shown beside each source of income (section 7.10).
16. The City PD's payroll is sized at the engine's own hours and wage, from the City of Detroit's
    adopted position count. The department's whole budget is about two and a half times that wage
    bill (section 7.3).
17. The amendment is lettered AM and takes the Constitution to version 4.4.0. Its scope sentence,
    its general construct and its three prohibitions are the author's wording. Its record stays
    proposed until the Director accepts it (Appendix E).
18. The roster is a table of counts over a finer split of the same households. The author treats it
    as current mathematics. ADR176 ruling 17 named moments or a fixed-size sketch, and an exact
    table is neither, so section 5 puts the question to the Director.
19. The City PD pays its investigator-hour as a wage to one of the aid partners' households, by an
    engine binding. That wage is not counted toward a place (section 7.4).
20. A household asks only if its budget group has two free hours for it, and hours are set aside in
    order of place (section 7.4).
21. A review contact names a position by its answers. Which positions exist is public (sections 7.6
    and 7.11).
22. The City PD's payroll is named on the public workplace that employs the force. No workplace is
    carved out for it (section 7.3).
23. The bands of the rule of thirds are on the roster, and the opening obeys the Director's
    statement of who works in each. The law's shares of wealth bind the next slice (sections 7.2 and
    11).
24. All of a household's people in the labor force belong to one crew (section 7.2).
25. The engine's households with business ownership are taken as the top tenth. The top 1% is one
    tenth of them, and the next 40% is four ninths of the other households (section 7.2).
26. The top 1% are owner households with nobody in the labor force. The next 40% are the other
    households in the labor force, those with the most people at work first. Job-seekers and units
    are not read, so the next 40% has unemployment too (section 7.2).
27. An opening that cannot obey the Director's statement of who works is refused by name. It is not
    bent quietly (section 7.2).
28. Who works in each band is a public county total. A position's own number of households stays
    earned (section 7.11).

## 3. One period at the table

### The county's books

These figures come from the recorded playthroughs of this slice (seed 319, in
`reports/county-review-2026-11-19/`), in a Wayne campaign that has the City PD and the claimant
group. Appendix A names the older files.

| Line | Per period | In this slice |
|---|---|---|
| First class: $151,969,750 of grants to public administration sites plus a $24 agency appropriation | $151,969,774 | Off the table. No claim can touch it |
| of which the City PD's payroll, under this design | $13,551,360 | Taken out of the line above, not added to it (section 7.3) |
| Relief: household support | $20,094,200 | The only money the review can move. $216,160 of it is for collective residence and stays outside the review |
| Spending limit (the first class and relief) | $172,063,974 | Unchanged |

Household support is one **unit** for each job-seeking person at the opening. A unit is $280 a
period: one period of food at the opening price. The recorded run pays 71,765 units. The list of
those units is the county's **roll**.

The county's cash in the recorded playthroughs is $747 million after period 1 and peaks at
$1,150.9 million after period 3. From period 4 the county takes in less than it pays out. Its cash
falls by $18.0 million in period 4, by $33.8 million in period 10 and by $56.3 million in period
29. At the close of period 29 it holds $149.5 million, which is less than its first class of
$151.97 million. The session of period 29 announces no relief, and from period 30 the county pays
no household unit. Nothing scripts this: it is the same in all four playthroughs.

### Wayne's households

The engine holds Wayne's households as four budget groups and one group for collective residence. A
group's name says whether its households had earnings in the year before the opening, and whether
they own a share of a business. It does not say who has a wage now.

| Budget group | Households | Units on the roll | People at work at the opening | Paid hours in period 4 |
|---|---|---|---|---|
| With earnings, no business ownership | 456,528 | 38,837 | 646,987 | 9,928,626 |
| With earnings, with business ownership | 50,726 | 2,669 | 101,931, of whom 57,474 are working owners | 1,806,192 |
| No earner, no business ownership | 173,995 | 26,538 | none | 640 |
| No earner, with business ownership | 19,334 | 2,949 | none | none |
| Collective residence | none, by an engine rule | 772 | | Outside the review |
| All households | 700,583 | 70,993 | | |

- Households and people at work come from a replica of the engine's opening allocation (Appendix A).
  Units are recorded support divided by $280. Paid hours are recorded wages divided by $24.
- The engine pays wages by the hour worked. In period 4 the first group was paid for 9,928,626
  hours. A person at work for a full period works 160 hours, so that is the work of about 62,000
  persons, in a group of 456,528 households. Wages had fallen by four fifths since period 2.
- The older recorded files do not hold the people at work in each period, or wages for each
  workplace. The playthroughs of this slice do. In period 4, 226,213 households have someone at
  work, against 505,963 at the opening, and 296,817 people are at work, against 748,922.
- The four persons at work in the third group had been job-seekers, so their households are on the
  roll.
- The second and fourth groups also receive ownership income: $103.1 million and $39.3 million in
  period 4. The engine does not tax it. A working owner is at work and is paid no wage.

**Who works.** **[Director]** The Director's law names four bands and says who works in each
(section 2). The roster the campaign captures counts Wayne's households into them by the rules of
section 7.2. At the opening it holds:

| Band | Households | At work | Only looking | None in labor force | People at work | Looking | Units |
|---|---|---|---|---|---|---|---|
| Top 1% | 7,006 | 0 | 0 | 7,006 | 0 | 0 | 0 |
| Next 9% | 63,054 | 49,431 | 4,244 | 9,379 | 101,931 | 5,618 | 5,618 |
| Next 40% | 280,236 | 280,236 | 0 | 0 | 470,695 | 13,105 | 13,105 |
| Bottom 50% | 350,295 | 176,296 | 26,538 | 147,461 | 176,296 | 52,270 | 52,270 |
| All households | 700,591 | 505,963 | 30,782 | 163,846 | 748,922 | 70,993 | 70,993 |

"At work" counts households with someone at work, and "Only looking" households with nobody at work
and someone looking. In the no-contact playthrough the counts move as the engine's wages do. The
households with someone at work, and the people looking for work, in the first session and in the
first short session:

| Band | Households | Work, opening | Work, period 4 | Work, period 29 | Looking, 0 | Looking, 4 | Looking, 29 |
|---|---|---|---|---|---|---|---|
| Top 1% | 7,006 | 0 | 0 | 0 | 0 | 0 | 0 |
| Next 9% | 63,054 | 49,431 | 10,185 | 10,185 | 5,618 | 96,257 | 96,246 |
| Next 40% | 280,236 | 280,236 | 129,732 | 135,781 | 13,105 | 284,585 | 278,536 |
| Bottom 50% | 350,295 | 176,296 | 86,296 | 90,330 | 52,270 | 142,256 | 138,222 |

No household left Wayne in 34 periods: every band holds its opening households throughout. The
count for every period of every run is in the records.

- The top 1% come from the fourth group: owners with no earner. The engine holds 16,385 such
  households with nobody in the labor force, more than twice the 7,006 the law needs.
- The next 9% are the other owners: 49,431 households that work, 4,244 that are looking for work
  and 9,379 that live on ownership income.
- The next 40% come from the first group, which is 65 of every 100 households in Wayne. So "at
  least" holds with room. The band has unemployment: 13,105 of its people are looking for work,
  about 3 of every 100 of its people in the labor force. At the opening each of them shares a
  household with someone at work.
- The bottom 50% are the rest of the first group and all of the third. Half of its households have
  someone at work. Of its people in the labor force 23 of every 100 are looking for work. It holds
  74 of every 100 units that households hold, and the claimants and the aid partners' households are
  in it.
- So the engine's opening and the Director's law agree in shape. The law adds the names of the bands
  and two checks at the opening. By period 3 the engine's wages have fallen, and with them the
  households with someone at work: the next 40% have 127,432 of them, not 280,236.

In a player's campaign the scenario also carves out three small named groups. The aid partners'
households (4 households, nobody in the labor force, no unit) come out of the third group, and the
organization's own households (4 households, 8 persons, 4 of them at work, no unit) come out of the
first. The table's figures are after both. The relief claimants (2 households, each with a
job-seeker) come out of the third group as well, and hold 2 of its 26,538 units. The recorded
playthroughs were made with all three groups and the City PD.

### The county's list

Each period the county writes a list. On it are every unit on the roll, and every household off the
roll that comes to ask for one. The list is in order of the wage tax each household paid in the
period just closed. The county pays from the top until the money for relief runs out. A unit moves
only to a household that pays strictly more than the household that held it. **[Director]**

- A household's wage tax follows its workplace. A full period at the $24 wage is $3,840 of wages and
  $576 of wage tax. A workplace that ran for half the period pays each worker for half the hours,
  and its households stand below those of a workplace that ran in full. A household with two people
  at work stands at twice its workplace's figure.
- The list is strict. Two workplaces that paid each worker a cent apart are ranked apart.
- A household with a wage and no unit can take a unit from a household with no wage. It makes no
  difference which budget group either is in.
- A household with a wage cannot take a unit from another household that pays the same.
- A household with no wage can take nothing from anyone. Whether it is in the room makes no
  difference.

### What the player does in a period

1. **Reads the county ledger.** It shows the money for relief the county has announced for next
   period, the county's cash, the City PD's line, the roll, and the order of the list.
2. **Reads the roster and the session record.** The roster shows each household position: where its
   wage comes from, how many of its people are at work and looking for work, the units it holds,
   and, where the player has a contact, its dollar figures. The session record shows who came last
   period, who was paid and who was ranked too low.
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

### What a claim does

The fifth draft gave a table of sessions here. It is withdrawn (section 2), and the recorded
playthroughs replace it below. The rules fix this much without them.

- One review contact reaches one household. If that household has a wage and no unit, it asks. The
  county pays it a unit, and stops paying one unit held by a household with no wage.
- Every household that came brings one more of its own position, so a claim doubles each session: 1,
  2, 4, 8. Ten sessions make 1,024 households and sixteen make 65,536. The first year is slow.
- A claim stops when every household of its position has been reached, or when no unit is left with
  a household that pays less. To go further the player opens another position.
- The households that lose are the ones that pay least, in every budget group. They can come. They
  are in the room and ranked below every household that is paid.
- A household with no wage that asks finds no place, in any budget group. It stays home and brings
  nobody.
- When the county's cash falls below its first class, it announces no relief. Every household on the
  roll loses its unit whatever its place. In the recorded run that is at the close of period 29.

The player has three choices at the county: which position to open, in what order, and when. There
is no counter-move. Section 12 says so.

The recorded sessions of two claims, from `reports/county-review-2026-11-19/` (the first contact is
chosen from the period-3 snapshot, the second from the period-10 snapshot; "came" is households
that asked and were paid):

| Contact | Session | Reached | Came | Brought | Asked, no place |
|---|---|---|---|---|---|
| First: Bottom 50%, "Wayne County: extraction (5)" | 4 | 1 | 1 | 1 | 0 |
| | 5 and every session to 34 | 2 | 0 | 0 | 2 |
| Second: Next 40%, "Wayne County: food (5)" | 11 | 1 | 1 | 1 | 0 |
| | 12 | 2 | 2 | 2 | 0 |
| | 13 | 4 | 4 | 4 | 0 |
| | 14 | 8 | 8 | 8 | 0 |
| | 15 | 16 | 16 | 16 | 0 |
| | 16 and every session to 34 | 32 | 0 | 0 | 32 |

Both claims doubled while a place was open, and both stopped for the same reason: the workplace
stopped paying a wage. "Wayne County: extraction (5)" paid $2,273,280 a period through period 3,
$242,304 in period 4 and nothing from period 5. "Wayne County: food (5)" paid $20,947,200 a period
through period 14, $6,918,672 in period 15 and nothing from period 16. A household whose workplace
pays nothing is ranked last, and a household that is ranked last finds no place. The first claim
moved one unit and stopped at 2 of its family's 185 households. The second moved 31 units (1, 2, 4,
8 and 16) and stopped at 32 of 2,434. Neither reached the edge of its position.

### What a new player notices within ten minutes

- The county pays its own offices and police first, and no claim can touch that money. The police
  line alone is two thirds the size of all relief.
- The county ranks a household by the wage tax it pays. A household that pays nothing is at the
  bottom, whether it is in the room or not.
- Relief only moves up the list: from households with no wage to households with one.
- A household comes only when its own money is at stake, and every absence has a reason.
- Relief won lasts only while the households keep coming.
- One contact becomes two households, then four, then eight, and stops at the edge of its own
  workplace.
- A period spent at the county is a period not spent running food.

## 4. Goals, non-goals and anti-goals

**Goals**

1. Any Wayne household that has been reached makes a real decision from its own figures, and a
   receipt explains it. Households nobody has reached are counted as such.
2. Each period the player chooses between the county and the aid road, and sees the answer the next
   period.
3. The county is an actor with an interest of its own. It pays its first class first, and it ranks
   households by what they pay it.
4. A household's living is read from accounts. MIM's reading is shown as a reading. With nation
   absent, nothing in this slice is presented as MIM's base.
5. A body's roll is written only by a household's own hours in the county's room.
6. Every rule is exact and repeatable: whole numbers and exact fractions, and no random draws.
7. Every count adds back to the engine's own count, at every grouping, every period.

**Non-goals for this slice**

- Rival organizers. Only the player's organizer opens a new position.
- A roll for the aid road. It arrives with the kitchen (section 11). **[Director]**
- Production by an organization: a kitchen or garden staffed by members' hours.
- Labor-force choices (keep looking, stop, start).
- Nation, legal status and the wage-against-value term on household groups.
- Solidarity, consciousness, hardening of class position, and the failure-mode readings. No
  household acts for another's gain.
- Businesses as a body at the county, tax motions, elections, other counties.
- Real sub-budgets. A position has no account of its own. The engine still pays a budget group as
  one pooled account.
- What the City PD does with its payroll. It still makes at most one visit a period.

**Anti-goals: the slice has failed if it contains any of these**

- An approval bar, a mood meter or a heat map standing in for a decision.
- A class label that is assigned by hand and then drives behavior.
- A rule that decides for a household from the average of its group.
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
| "Joint person, workforce and ownership placement and proportional rounding are Designed. No synthetic joint household is presented as a source observation." | ADR269 |
| "Partitions such as class position, core and periphery, or political alignment must emerge from composed material relations at a declared scale. Any claimed partition must include an invariance proof under its declared coarse-graining." | Constitution Article II |
| "An actor's material position and conceived interest remain distinct dimensions. Their gap is a terrain of political struggle." | Constitution Article II |
| "All material effects become next-period intents and enter only the next four-week causal interval." "Player and non-player actors act through the same declared causal machinery." | Constitution Article III |
| "No functional form — sigmoid included — may be imposed on mechanics; sigmoid-shaped behavior must emerge from P(revolution)/P(acquiescence) dynamics and the algebraic Lawverian operations." | Constitution Article III, as Amendment AM adds it; ADR172 ruling 5 |
| The lawful form of a response is "the measure of class members whose wealth clears subsistence", with the curve "derived as a THEOREM from within-class wealth dispersion integrated against the threshold". The confirmed fault was a rule "applied to the class MEAN" | ADR173, ruling 1 and its context |
| "carriers carry distributions (dispersion-preserving summaries), never bare means, at every grain" | Game Design Standard, the Jensen guard |
| "Coarse carriers hold KINDED DISPERSION FIELDS (moments or a fixed-size quantile sketch), amendment-recorded if new mathematics under AE(ii)." | ADR176, ruling 17 |
| The rate of a coarser group is weighted, "never an unweighted mean" | ADR189, clause (ii); Constitution Article V |
| "For finite source-to-representative assignment q, additive pushforward preserves sums and composition. These are tested accounting laws, not old/new transition congruence or an invented aggregation adjunction." | ADR296 |
| "splits use largest-remainder integer apportionment on absolutes, so conservation is exact by arithmetic." | Game Design Standard |
| "Designed values and mechanics are legitimate. Creators must declare them and keep them causally coherent with the rest of the model." A design liberty "must not bypass the causal circuit to manufacture an intended conclusion." | Constitution Article IV |
| "aid itself creates no agreement, membership, consciousness or worker-hours." | ADR270 |
| "A shared income source provides no evidence that residents belong to a single political organization." | ADR299 |
| The player is not the state and cannot legislate | Game Design Standard §2 |
| "One practice executes per organization per period." Old formats get no compatibility path | ADR262 |
| "A union local and a political police force both rank what they could do by yield per unit spent and fund down the list until the money runs out. Neither side gets a privileged mechanic." The difference between a state and a movement is "the SIZE of the budget and the RELIABILITY of its sources", "never a special rule in the ranking". What is declined is recorded with what remained | ADR184 R3, R4, R9 |
| "The first state opponent must have its own authority, objective, resources, and partial knowledge". A state actor gets no "heat scalar, primitive or fixed political-response curve". Its values are "Designed unless separately backed by named sourced wage or service data" | ADR291 |
| "A new or redefined mathematical primitive, a relaxed constitutional prohibition, or a change to the reserved theoretical line needs a constitutional amendment. New governed content vocabulary does not need an amendment when it uses the current mathematics. It needs the applicable Director ceremony, schema and conformance updates, and a recording ADR." | Constitution Article VIII |
| "Existing deterministic mechanics embed as one-outcome Dirac kernels". A choice receipt is owed by "Every finite-kernel choice", which consumes "one exact integer ticket draw" | Constitution Article V and Amendment AJ; ADR248 |
| Attributed membership is ratified, but its payload is empty, unhashed and unread, and filling it is a separate Director act | ADR189; ADR198 R4; PER-44 |
| "STRUCTURE IS THE PREMISE; MAGNITUDES ARE EARNED". What the player knows never enters the turn's hash | ADR182 R2 |
| Every value is Observed, Derived, Calibrated or Designed, and says which | Constitution Article IV |
| "Any line is playable — including wrong ones — and the sim never editorializes mid-run." | Game Design Standard §2 |
| Every construct has a writer, a reader and a sentinel. A construct that lacks one gets a recorded disposition | Game Design Standard W.1, W.2 |
| Every view states its decision question, its signals and how sure they are, what is hidden, its actions, its receipts, its Archive links, and whether it is an administrative display | Constitution Article VII |
| "Emergence claims need redundant evidence. The evidence includes control and shock twins, counterfactuals, and mutation tests that sever causal links. It also includes geographic and sector variation, persistence after the event, deterministic replay, and a direct-write audit." | Constitution Article VIII |
| The game is proved by play: recorded playthroughs kept as seed, action log and result | Game Design Standard §6 |

**How far this design meets the rule on averages**

- *What is met.* No rule in this slice decides for a household from a group's average. The county's
  list reads the wage tax on the household's own wage. A household comes on its own stake. Section
  7.14 gives the proof Article II asks for.
- *The floor of the grain.* The engine pays one budget group's workers at one workplace as a single
  amount. Below that it holds nothing, so those workers are taken as paid alike. This is declared,
  and it is the finest figure that exists.
- *What is declared and not observed.* The engine binds people to workplaces and holds no household.
  The placements of section 7.2 say how those people fall into households. They are Designed. They
  decide who holds a unit and who can ask, so they change outcomes. Section 11 names the census
  tables that would replace the first three.
- *The roster and the law on new fields.* ADR176 says a group's spread is carried as a field,
  "amendment-recorded if new mathematics". The roster is a table of whole-number counts over a finer
  split of the same households. It uses sums, ratios of sums and exact splits, all of which the
  engine and its records use today. The author treats it as current mathematics. **[Call]** ADR176
  named moments or a fixed-size sketch, and an exact table is neither. Section 12 puts the question
  to the Director.
- *No draw, so no kernel receipt.* Every split here is exact arithmetic. Amendment AJ owes a choice
  receipt to a draw. The session's own record holds every split it makes. **[Call]** The research
  for this lane flagged that as a point for the Director to confirm.
- *What Amendment AM allows here.* The floor compares a household's own stake with its own cost of
  time. Both are amounts the engine holds for that household. The cost of time is the cost of an
  act, which Article IV counts among declared Designed quantities. It is not a constant placed to
  set where a response turns: change the wage or the session's hours and it moves with them.
- *Geographic and sector variation.* The slice has one county. Disposition: BLOCKED until a second
  county is in play. Section 8, record 12.

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
  unit is the wage tax the household pays it.
- **A tax-weighted count, for less against.** The third draft. The re-check found that its "against"
  side could never matter in play. It was the rule of a referee and not of an actor with books of
  its own, and it was not in ADR184's form.
- **A refund.** Each household gets back the wage tax it paid, up to one unit. This was the author's
  first statement to the Director.
- **Counting heads inside the fixed total.** Offered again after the correction on MIM's sentence.
  Not chosen.

### How households are counted

The Director ruled that populations are joined and split in a principled way, after Lawvere.
**[Director]** Five ways of counting Wayne's households were weighed against that.

- **Every household is given its budget group's average.** The fourth draft. Withdrawn. In period 4
  six of every seven households in the largest group had no wage, and each was ranked as if it had
  paid $78. Four wages put a whole group of 174,000 households above the group below it.
- **Each group split into "has a wage" and "has no wage".** It removes the worst of the error. It
  leaves the same error one level down: workers at a workplace that ran in full and workers at one
  that stood idle would share one average.
- **Positions by workplace (chosen).** **[Call]** A position is one budget group's households bound
  to one workplace, by how many of their people are at work. This is the engine's own grain. It
  binds every worker and job-seeker of a budget group to a workplace, pays the group's workers there
  as one amount, and holds nothing finer.
- **A summary of the spread.** ADR194 ruled this form for a class's wealth: brackets taken from
  data, carried as a field. Here the engine holds an exact count for every workplace, so the exact
  table is used and nothing is summarized.
- **Real sub-budgets.** Each position with its own cash, stock and policies. Sounder, and the likely
  home of nation and legal status. It changes the opening economy and needs a rule for splitting
  every stock. It belongs to a later slice.

### Spread

- *Each one brings one (chosen).* **[Director]** The rate is Designed.
- *Organizer only.* One new household a period. Not chosen.

### Why a household comes

- *Its own money, if worth the time (chosen).* **[Director]**
- *Its own money, either way.* The author's recommendation. Not chosen.
- *Not until consciousness is ruled.* It would stop the lane. Not chosen.

### Ruling 5 and the floor

The fourth draft said: "The author reads the floor as a declared comparison of two amounts the
engine holds, with no coefficient and no curve, for which a record is enough. If the Director holds
that ruling 5 binds as written, the floor needs a constitutional amendment under Article VIII before
it is built." The Director answered: "ruling 5 also survives as written about laws, modify the
constitution" (spelling corrected).

- *A decision record for the floor.* The author's reading in the fourth draft. Not chosen.
  **[Director]**
- *The ruling's sentence alone.* It would put ruling 5 back in the Constitution and leave the floor
  with no stated ground. The fourth draft had said the floor needs one.
- *A named exception for the floor.* It would relax a prohibition for one rule of one slice, and say
  nothing about the next household rule.
- *The ruling's sentence, with a stated limit on how a rule may decide for one member (chosen, as
  the author reads the Director's answer).* Amendment AM. It says a rule may compare material
  amounts held for one member, and it bars a constant placed to set where a response turns. Appendix
  E gives the text, says whose words are whose, and sets out the other readings for the Director.

### The police budget

The Director ruled that $24 a period is not realistic. **[Director]** Four forms were weighed.

- *Real pay, added on top.* The department's budget is about $34 million a period. Adding it would
  pay the same jobs twice, because the county's public workplaces already employ every government
  worker in the county. It would also pay police two and a half times what the engine pays any other
  worker.
- *The engine's hours and wage, named inside a public workplace's grant (chosen).* **[Call]**
  $13,551,360 a period for 3,529 positions. The force is already employed and paid there. The books
  now say so, and the engine's lines and the economy do not change.
- *A workplace of its own for the force.* The fifth draft's form. It moves 3,529 people out of a
  public workplace at the opening, so the whole opening economy and its recorded baselines move. It
  is left to the opponent's lane, where the question of what the force does is also decided.
- *A share of the public workplaces' grants set by a federal count of police jobs.* Not possible
  today. The federal files on the data drive report local police inside general government (Appendix
  A).

### The second road

- *Both roads (chosen).* **[Director]**
- *County review only, labelled as the reform road.* Not chosen.

The re-check of the third draft found that two rulings pull against each other on the aid road. A
household acts only for its own money. Giving hours puts a household on a body's roll, and receiving
aid never does. In the engine the aid partners have no kitchen, site or stock, so the only
households that would give hours are the four that receive the food. The Director was shown three
ways out and chose the first. **[Director]**

- *No roll until the kitchen (chosen).* Food runs stay as they are. The roll arrives with the next
  slice, where the organization runs production with members' hours.
- *Working for one's own parcel counts.* Not chosen.
- *The kitchen in this slice.* Not chosen.

### What kind of proceeding

**[Call]**

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
  grants to public sites and the City PD's line. No claim, ruling or record in this slice changes a
  first-class line, the spending limit or a tax. **[Director]**
- **Relief** is the total of the roll: $20,094,200 on the recorded figures. The review moves money
  only inside it. One household's gain is another household's loss. **[Director]**
- **Collective residence is outside the review.** **[Call]** It has persons and no households, by an
  engine rule, so nothing in it can come, ask or be ranked as a household. Its 772 units, $216,160,
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
- **What the engine pays.** County support is paid into a budget group's pooled account, as it is
  today. After each session the county sets each group's line to the units its positions hold on the
  list, added up, times $280. Lines are whole units, so nothing is rounded. A group left with no
  unit has its line removed, and restored when it holds one again.

### 7.2 Positions and the roster

**The method.** **[Director]** Every count in this slice follows four rules. The first three are
Lawvere's account of quantities. The fourth is the Director's ruling in ADR173. Appendix D gives the
words of both, and the project records that already bind each rule.

1. **Totals add.** Households, persons, units, hours and dollars are totals. The total for a group
   is the sum over its parts, at every level, exactly.
2. **A rate is one total divided by another.** Wage tax for each household and paid hours for each
   worker are rates. The rate of a group is never the average of its parts' rates. A rate says
   something about one household only when the households it was worked out for do not differ in it.
3. **A split is declared.** Nothing in a total says how it divides. Every division of a group into
   parts is a named rule, marked Designed, made in whole numbers, that adds back to the total
   exactly. A split is a choice. It is not the reverse of adding up, and this design calls nothing
   here an adjunction.
4. **A rule decides for a household from that household's own figures.** The number that act is the
   count of households the rule admits. A group may be decided as one only when its households do
   not differ in anything the rule reads.

**What the engine holds.** The engine's finest real figures are for one budget group's people at one
workplace.

- A **workplace** is a site's body of workers of one kind, as the engine holds it. The map of the
  recorded run shows 18 groups of producers, three shops and two utilities in Wayne.
- The engine binds every person in the labor force to one workplace, whether that person is at work
  or looking for work. Nobody changes workplace. A workplace hires from its own job-seekers, and
  lays off into them.
- For each budget group at each workplace the engine holds, every period: the people at work, the
  people looking for work, the hours planned and paid, and the wages paid. It pays that group's
  workers there as one amount.
- For each budget group it holds the households, the persons, one pooled account, the wage tax
  assessed and collected, and the support line.
- It holds no household. Nothing says which people share one.

So one budget group's workers at one workplace are taken as paid alike. This is the floor of the
grain. **[Call]**

**Positions.** A **position** is a set of households that no rule in this slice can tell apart. A
position answers six questions.

| Question | Answers |
|---|---|
| Which budget group? | One of the engine's household groups in the county: the four large ones and the three small named ones |
| Which crew are its people bound to? | One workplace and one way of being paid there (a wage, as a working owner, or as an unpaid family worker). Or none: nobody in the household is in the labor force |
| How many of its people are at work now? | Any whole number |
| How many of its people are looking for work now? | Any whole number |
| How many units does it hold? | One for each job-seeker it had at the opening: none, one, or more |
| Which band was it in at the opening? | The top 1%, the next 9%, the next 40% or the bottom 50% of the county's households |

- A **crew** is one budget group's people at one workplace, paid in one way. The engine calls it a
  staffing member. All of a household's people in the labor force belong to one crew. **[Call]** No
  household here mixes an owner and a wage earner, or two workplaces. That is declared, and it is
  not true of Wayne.
- A household is **on the roll** if it holds a unit. The roll is fixed at the opening. A person laid
  off later is looking for work and brings no new unit.
- A household's wage is what its people at work were paid in the period just closed. A working owner
  and an unpaid family worker are at work, and the engine pays them no wage.
- A household on the roll that comes stands behind the Claimants' Assembly's claim. A household off
  the roll that asks stands behind the aid partners' claim.
- A household with nobody in the labor force is retired, disabled, or not looking for work. It is
  never hired.
- A view may fold positions for reading (section 7.11). No rule folds them.

**The bands, and who works.** **[Director]** The rule of thirds divides a population into the top
1%, the next 9%, the next 40% and the bottom 50%. Its shares of wealth are for the next slice. Its
bands are in this one, because the Director said who works in each (section 2).

| Band | The Director's words |
|---|---|
| Top 1% | "do not work they live entirely off investments" |
| Next 9% | "some work some live off investments or they are retired" |
| Next 40% | "makes its living from selling wage labor"; "at least who must work"; "can have unemployment too, so they can be looking" |
| Bottom 50% | "work but are more likely to receive welfare and require aid and they don't own homes" |

- A household's band is set once, at the opening, and the household keeps it. A band is a place in
  the opening order of the county's households. It is not a class, and no view calls it one.
- No rule of this slice decides by a band. The county ranks by wage tax alone. A band settles only
  the last exact tie of a split (below). Bands are shown on every position and counted every period
  (section 7.11).
- After the opening nothing holds a band to the law. Hires, layoffs and departures move its
  households between positions, and the count of who works in each band is a measurement. The owner
  ruled this form in July for an empirical law: the opening obeys it without condition, and a run
  only measures it (section 11).
- The engine holds no home and no household wealth in this slice. So "they don't own homes" is shown
  as the Director's law. It is not a figure.

**The roster** is the table of positions. For each position it holds the number of households and,
of those, the number reached. Every entry is a whole number. The roster adds back every period:

- the positions of a budget group sum to the group's households;
- the people at work in a crew's positions are the people the engine holds at work in that crew, and
  the same holds for its people looking for work;
- the units in a group's positions are its units on the roll, less any that left with a household
  (rule 6);
- the positions of a band sum to the band's households at the opening, less households that left,
  and no household of the top 1% is in the labor force.

**The declared placements.** **[Call]** **[Record needed]** The engine holds people by crew and
holds no household. The sources give Wayne's households, workers and job-seekers as separate totals,
and none says how they fall together (Appendix A). So each rule below is Designed. Each decides who
holds a unit or who can ask, so each changes outcomes.

1. *Households are bound to crews by their people.* A budget group with fewer people in the labor
   force than households gives each of those people a household, and its other households have
   nobody in the labor force. A group with more gives every crew one household, and shares the rest
   among its crews in proportion to the people bound there, less one. So no crew has more households
   than people.
2. *People at work are spread evenly at the opening.* The people at work in a crew are spread over
   its households as evenly as whole numbers allow.
3. *Job-seekers at the opening go to the households with the fewest people at work,* one to a
   household, and round again if there are more job-seekers than households. A household holds one
   unit for each.
4. *A hire takes a job-seeker.* It falls on a household that has someone looking for work, and first
   on those with the fewest at work.
5. *A layoff falls first on the households with the most at work.* The person laid off is then
   looking for work, in the same household.
6. *A person who leaves the labor force is taken from the households with the most people of that
   kind.* When the engine lowers a budget group's households, households with nobody in the labor
   force leave. A unit that leaves with a household stays in the money for relief and is held by
   nobody.
7. *The bands are sized from the engine's own top tenth.* The engine gives business ownership to one
   tenth of the households of each earnings group, by a Designed setting (Appendix A). Those
   households are taken as the top tenth. The top 1% is one tenth of them, and the next 9% is the
   rest. The next 40% is four ninths of the other households, and the bottom 50% is the rest.
8. *The bands are filled by the Director's words.* The top 1% are owner households with nobody in
   the labor force. The next 40% are households without ownership that are in the labor force, taken
   by the number of their people at work, most first. Households that are only looking for work come
   last. A household with nobody in the labor force is never taken. Job-seekers and units are not
   read, and a household brings its own with it, so the next 40% has unemployment too. Where a
   band's line falls inside a set of like households, it takes from each position in proportion.

Rules 7 and 8 run once, at the opening, after rules 1 to 3. They decide which households carry which
band. They move no unit and no person.

**Two checks at the opening.** **[Call]** If the owners have fewer households with nobody in the
labor force than the top 1% needs, the build refuses the campaign. If the other households have
fewer in the labor force than the next 40% needs, the build refuses the campaign. Each refusal names
the band. The law is an opening condition. An opening that cannot meet it shows a fault in the data
or in this reading, and it is not bent quietly. Wayne meets both with room (section 3).

Among households that a rule treats alike, it falls on positions in proportion to their households,
and inside a position on reached and unreached households in proportion.

- **Why evenly.** It needs no number of its own. The other bound is to stack people into as few
  households as possible, and that needs a limit on how many can share a household, which would be
  one more Designed number.
- **The other bounds of rules 4 to 6** are that a hire, a layoff or a departure falls first on
  households that hold a unit, or last.
- **Why the owners are the top tenth.** MIM counts net worth as means of production (Appendix B).
  The engine's households hold no net worth yet, but two budget groups draw income from a share of a
  business, and those are the groups taken here. The setting that makes owners one tenth of
  households is Designed, and its own comment says it is "not observed wealth/class". So this is a
  reading. The next slice tests it against the two thirds the law gives the top tenth (section 11).
- **Why by the number at work.** The next 40% live by selling wage labor, so a household with more
  wages stands higher. Nothing else orders them. Job-seekers and units are not read, because the
  Director said the next 40% can have unemployment too. Relief still sits mostly with the bottom
  50%, because every household with no earner is there (section 3).
- **The other bound of rule 8** fills the next 40% without regard to the number at work. It changes
  which households carry the name. It changes no outcome beyond an exact tie, because no rule
  decides by a band and two positions that differ only in band stand at one place on the list
  (section 7.14).
- **Every split is exact.** Each is made by largest remainder on whole numbers, as the Game Design
  Standard requires. An exact tie between positions is settled by a fixed order of their answers:
  fewer units first, then fewer people looking for work, then fewer at work, then the lower band.
  Between reached and unreached households it goes to the unreached. No split reads an identifier.
  Appendix D gives each rule step by step.

**What is not split.** Money and stock. A position has no account. The engine pays a group's support
into one pooled account and collects its wage tax from that account. The roster is the county's
record of whose units and whose tax those are.

**The small named groups** are budget groups of their own in the engine: the claimants (2
households, each with a job-seeker and a unit), the aid partners' households (4, nobody in the labor
force) and the organization's own households (4, with 4 people at work). The same rules place their
households. None of them owns a business. The aid partners' households have nobody in the labor
force, so they are in the bottom 50%. The claimants are only looking for work. In Wayne the line of
rule 8 is reached long before them, so they are in the bottom 50% too. The organization's own
households fall in the next 40% or the bottom 50% as that line gives them.

**Collective residence** has no position.

### 7.3 Bodies and the county

A **body** is an organization whose claim households can stand behind at the county.

| Body | Today | In this slice |
|---|---|---|
| Wayne Relief Claimants Assembly | A fixed actor with a captured mandate. Its claim: "Keep current claimants on the relief roll while the county reviews their cases." | Its claim stands at every session. Households on the roll that come are recorded behind it. Coming does not protect a unit |
| Wayne Local Aid Partners | Four households and a fixed script. Its claim: "Hear the cases of residents who received no county support." | Its claim stands at every session. Households off the roll that come to ask are recorded behind it. It still receives food runs, as today (section 7.8) |
| Wayne County administration | Does not exist | New state actor. It announces the money for relief, writes the list and pays down it |
| City PD | The state opponent, shown with $24 a period | Its payroll is named in the county's books. What it does is unchanged |
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
| Knowledge | Its own account, its roll, the wage tax each budget group paid it, the wages each workplace paid on which that tax was assessed, and who came to ask, by position. It cannot tell the households of a position apart. It does not see who was reached and stayed home, what the organizer chose, or anything hidden |
| What it cannot do | Arrest, coerce, close a session, change its own rule, or act on anything that is not in its own room or its own books |
| Receipts | A statement of its cash and its money for relief, its list with what it paid and what it declined, and the payment receipts the engine already writes |

The county's rule is fixed for this slice. A county board that can change it is later work.

**The City PD's budget.** **[Director]** **[Record needed]** The Director ruled that a police budget
of $24 a period is not realistic.

- **Where the $24 comes from.** One number in the engine does three jobs. It is the hourly wage, the
  price of one visit and the whole appropriation. So the City PD's line pays for one
  investigator-hour a period. The county's spending limit is raised by the same $24, so the line
  competes with nothing. ADR291 called the appropriation "a Designed fiscal proxy" and left its size
  to "named sourced wage or service data".
- **What was wrong.** The $24 was never the cost of the police. The engine builds the county's
  public workplaces from every government job in the county, police included. The force is already
  employed there, and already paid inside the $151,969,750 that the county grants its public
  workplaces. The books showed the price of one visit and called it the City PD.
- **The size.** **[Call]** The City PD's payroll is worked out as the engine works out every public
  workplace's payroll: positions, times a period's hours, times the wage. The City of Detroit's
  adopted budget for its 2025 fiscal year gave its police department 3,529 positions and $441.9
  million. At the engine's 160 hours and $24 wage, 3,529 positions cost $13,551,360 a period. The
  department's whole budget comes to about $34 million a period, which is two and a half times that
  wage bill. The design uses the first figure, because the engine pays every worker $24 an hour.
- **How the books carry it.** **[Call]** The City PD's record names the public workplace that
  employs the force, its positions and its payroll. The county ledger shows that payroll as the City
  PD's, and shows the workplace's grant less the payroll. The engine's lines do not change: the
  payroll is paid inside the workplace's grant, as it is today. Nobody is employed twice, and the
  county's first class is $151,969,750 and the $24. The build refuses a campaign in which the named
  workplace has fewer people than the positions, or a grant smaller than the payroll.
- **Three numbers.** The wage is the scenario's wage. The price of a visit is one hour at that wage.
  The appropriation for visits is the price of the visits allowed in a period, which is one. The
  build no longer refuses a campaign whose wage is not $24.
- **What was not done.** **[Call]** The force is not a workplace of its own with its own account.
  That would move 3,529 people at the opening and change the whole opening economy. It belongs to
  the opponent's own lane (PER-355), with the question of what a force of this size does.
- **What does not change.** How much the City PD watches. It still makes at most one visit a period.
- **What the player sees.** The county pays its police about two thirds of what it pays in relief,
  and that money cannot be claimed.
- **The source.** The repository holds no police figure. The federal employment files on the data
  drive count 2,168 federal and 323 state police jobs in Wayne County in 2024. They report local
  police inside general government: only 242 local jobs appear under justice and public safety. The
  position count is from the City of Detroit's council budget analysis of 21 March 2025. It is
  Designed, with its source named, until the reference pipeline captures it. The body keeps the name
  City PD.

### 7.4 A session, step by step

The county holds one session each period from period 4, after the period's accounts close. The
session sets the lines that are paid when the next period closes. Every step runs on whole
households, whole units and exact fractions. The list is worked out once, from the top. No step is
repeated.

1. **The contact lands.** The household the organizer reached in this period is counted as reached
   in its position (section 7.6).
2. **The county announces its money for relief** for next period (section 7.1), and the number of
   household units it pays for.
3. **The county ranks.** A household's **place** is the wage tax it paid on its own wage in the
   period just closed. The roster still holds the households as they stood during that period, so
   the people at work are the people who earned.
4. **The roll goes on the list.** Every unit on the roll is listed at its household's place, whether
   or not the household is in the room.
5. **Households ask.** A reached household that holds no unit asks for one, behind the aid partners'
   claim, if its budget group has two free hours to set aside for it. Hours are set aside in order
   of place. A household left without them is recorded "no time" and does not ask. An asking
   household goes on the list at its own place, below every unit of the roll at the same place.
6. **The county pays down the list** from the top until the units it can pay run out.
7. **Who comes to ask.** A household that asked comes only if the county's money reaches it.
   **[Call]** Otherwise it stays home and is recorded "no place", and the hours set aside for it are
   not spent. Leaving it out changes nothing above it, which is why the list is worked out once.
8. **Who comes from the roll.** The county does not pay some units. A reached household on the roll
   comes if a unit of its own is one of them (section 7.5), and if its budget group still has two
   free hours for it. It is recorded behind the Claimants' Assembly. Its coming does not change the
   list.
9. **The record.** The county publishes its list: the order of the positions, units paid and not
   paid, households that asked and were paid, and what it declined and why. It does not publish the
   wage tax behind a rank (section 7.11).
10. **Payment.** The lines are paid at the next period's close, by the engine's existing payment
    step. They hold for that period only. The next session starts again from the roll.
11. **The spread.** Each household that came, on either side, brings one more household of its own
    position, who is reached from the next session (section 7.6).
12. **The roster is brought up to date** with the period's hires, layoffs and departures (section
    7.2). It then shows the households as they stand for the next period.

Seven details complete the rule.

- **Ties keep the holder.** **[Director]** A unit is never moved between households that pay the
  same. So a household never takes from a workmate's household with as many people at work.
- **Positions at one place lose together.** **[Call]** When units are not paid at a place, each
  position there loses in proportion to the units it holds, by largest remainder. If two remainders
  are exactly equal, the county may not prefer one position to the other, and that unit is paid to
  nobody. Households that ask from two positions at one place share the open places the same way. So
  what the county keeps back can be more than one unit. No rule reads an identifier.
- **Only wage tax ranks.** The engine does not tax ownership income, and it pays a working owner no
  wage. The tax that sites pay ranks no household. **[Call]**
- **A place is a rate, worked out from totals.** **[Call]** It is the household's people at work,
  times the wages its crew was paid in the period, divided by the crew's people at work, times the
  share of its budget group's taxed wages that the county in fact collected as tax. So tax a group
  could not pay is shared among its households in proportion to their wages. A crew's hours are
  pooled: its people at work are taken as paid alike, because the engine holds nothing finer. Places
  are compared as exact fractions, so a cent can rank one workplace above another. A place only
  orders the list. No money is worked out from it.
- **A wage from an agency shift is not counted.** **[Call]** The City PD pays its investigator-hour
  as a wage to one of the aid partners' households, by an engine binding (Appendix A). That wage is
  in the group's taxed wages. It gives no household a place, because no household of that group has
  anyone at work in a crew.
- **If no household paid wage tax,** all stand at one place and nothing moves.
- **A household with no place is declined in a typed way,** as ADR184 R9 requires. The record gives
  the units left below its place, which is none.

The households of a position cannot be told apart, so the record holds how many came, never which.

### 7.5 What a household does

Every rule below decides for a household from that household's own figures. The engine holds no
single household, so each rule is run once for a position and its answer is a count.

| Step | What it reads | What happens |
|---|---|---|
| Is it reached? | Section 7.6 | An unreached household does nothing |
| What is at stake? | Its own unit and the county's list | Off the roll: the unit it would be paid, if the county's money reaches it. On the roll: its own unit, if the county will not pay it. Otherwise nothing |
| Is it worth the time? | The session's hours and the wage | It comes only if its stake is at least the **floor**: 2 hours at $24, which is $48 today |
| Can it come? | Its budget group's free hours from the period just closed | Each household in the room spends 2 hours. If a group's hours run short, as many come as the hours cover, from the top of the list, and the rest are recorded "no time" |

A reached household that does not come is recorded with one reason: no place, nothing at stake, not
worth the time, or no time.

Eight things about this rule are stated on screen and in the record. **[Record needed]**

- **A household reads only its own money and hours.** No rule reads solidarity, consciousness,
  nation or a class label. Nobody comes for someone else's gain. **[Director]** Article II calls the
  gap between material position and conceived interest "a terrain of political struggle". This slice
  models only the first of the two.
- **A stake is one whole unit, or nothing.** A household that asks is paid a unit or finds no place.
  A household on the roll is paid its unit or is not. A unit is $280, which is over the floor. So
  today the floor keeps nobody home. It would if two hours' wages came to more than a unit, which is
  a wage above $140 an hour. This is the third correction of section 2.
- **Which households of a position lose is a declared split.** **[Call]** The county does not pay
  some of a position's units, and nothing says whose. Unpaid units are taken a household at a time:
  a household that holds two loses both before the next loses one. The households that lose are
  reached and unreached households in proportion to their numbers, by largest remainder. An exact
  tie falls on the unreached household. So one reached household among many is counted among the
  losers only when more than half the position's households lose. The other bounds are that the
  reached lose first, or last.
- **How many come is a count.** The number that come is the count of reached households whose own
  stake covers their own time. Here a stake is a whole number of units or nothing, so the answer to
  a change in the unit, the wage or the hours is a step at the price of a unit. One declared rule
  shapes that count: the split above sets how many of the losers are reached households. The fifth
  draft said that nobody chooses the shape. That was too strong, and it is withdrawn. The count is
  still the form Amendment AM and ADR173 require: a rule for one household, and a measure of the
  households it admits.
- **The floor compares two amounts the engine already holds.** **[Director]** It has no coefficient
  of its own: the hours come from the scenario and the wage from the economy.
- **Households with the same figures decide alike.** **[Director]** The ruling said that households
  in the same position move together. That holds for the households of a position that have the same
  thing at stake. It no longer means that a whole budget group comes or stays as one.
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
out when the next closes, like every practice. The roster is brought up to date from the employment
records of the period that has just closed. The hours a household spends in the room are charged
against that same period, which is the period the engine's own check on household hours expects. The
City PD's operation already decides and acts after a close in the same way. Record 7 must state this
in the record's own words. Whether the hours in the room belong to the period just closed or to the
next is put to the Director (section 12).

### 7.6 Reach

- **The organizer's contact.** The new choice, a review contact, spends the period's two organizer
  hours to reach one household in a position the player names by its answers (section 7.2). Which
  positions exist is public (section 7.11). It is the same two hours the organizer spends today on a
  partner organization. Like every practice it is chosen in one period and carried out when the next
  period closes. A contact chosen in period 3 is in the session of period 4, and the unit it wins is
  paid when period 5 closes. The contact can be chosen from period 3, the period after the founding
  hearing. **[Call]** **[Record needed]** The record must also say that an organization the engine
  runs may make the same choice. In this slice none does.
- **Each one brings one.** **[Director]** Every household that came to a session brings one more
  household of its own position, who is reached from the next session on. That is a household with
  the same six answers, the band among them. **[Call]**
- **Bringing one costs two hours.** **[Call]** The household that brings spends 2 hours of its own
  on it, the same as the organizer's contact. So a household that comes gives 4 hours in the period:
  2 in the room and 2 bringing the next. The floor still compares the stake with the 2 hours in the
  room, as the Director ruled.
- **A reached household stays reached.** It decides afresh each period whether to come. If it loses
  its wage or finds one, it is counted as reached in its new position (section 7.2). Only households
  that came bring another. If a group's free hours do not cover the bringing, fewer are brought, and
  the record says so.
- **A position cannot grow past its households.** When every household in it has been reached,
  nobody is brought and no hours are spent on it. A claim therefore stops at the edge of its own
  position. To go further the player opens another position.
- **When no places are left,** the households that came still bring others. Those find no place and
  stay home. The position's reach then grows by the same number each period, and no more money
  moves.
- **Nothing can be called back.** **[Call]** The player can reach households in another position.
  The player cannot un-reach a household or stop it bringing the next.

The rate is Designed. The engine's time accounts show far more free hours than organizing uses, so
they cannot fix how fast it spreads. One contact for two hours is the only rate the scenario already
has, and this design applies it to every household that came.

### 7.7 The county's list: a worked example

The fifth draft gave seven cases on Wayne's recorded figures. They are withdrawn (section 2). The
example below is small enough to check by hand. Two sessions of the recorded playthroughs follow
it, in place of the withdrawn cases.

A county can pay 5 units. Its roll holds 5.

| Position | Households | Wage tax each paid | Units held | Reached |
|---|---|---|---|---|
| A: one at work, a full period | 2 | $576 | 2 | none |
| B: one at work, half a period | 1 | $288 | 1 | none |
| C: no wage | 2 | nothing | 2 | none |
| D: one at work, a full period, off the roll | 1 | $576 | none | 1 |

- The list, from the top: A's two units at $576; D's request at $576, below A because ties keep the
  holder; B's unit at $288; C's two units at nothing.
- The county pays five: A's two, D's one, B's one, and one of C's two.
- One household of C loses its unit. Neither was reached, so nobody comes from the roll.
- D's household comes, behind the aid partners' claim, and is paid $280 when the next period closes.
  It brings one more household of D, if there is one.
- Next period C's line is $280 and not $560, and the line of D's budget group is $280 higher.
- The session after that starts again from the roll. D's household is paid again only if it comes
  again.

**What this shows.** Relief moves up the county's list and never down it. A household with no wage
loses first and can take nothing back. The county does not weigh which budget group a household is
in. It weighs whether the household has a wage, and how much.

**Two recorded sessions.** In the session of period 4 the county could pay all 70,993 household
units and held 70,993. One reached household of "Wayne County: extraction (5)" (Bottom 50%, one at
work, no unit) asked and was paid. The unit it took was held by a household of the group with no
earner that was looking for work. The lines for period 5 were one unit more for the group of
households with earnings and no business share, 38,838, and one fewer for the group with no earner,
26,535. The household had spent 2 hours in the room and 2 hours bringing one more.

In the session of period 11 a reached household of "Wayne County: food (5)" (Next 40%, two at work,
no unit) asked and was paid. This time the lines of every group equal those of the no-contact run.
The contact's preview had named, as the household that would lose its unit, one of the same budget
group with a person at work and a person looking, and a line moves only when the two households are
in different groups. From session 12 the claim doubled: two households asked and were paid, then
four, eight and sixteen. Against the no-contact run the line of the group with earnings rose by 1,
1 and 3 units in sessions 12 to 14, and the line of the group with no earner fell by the same.

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

**Where the record lives.** The session records are the first home of the rolls and of the roster.
They are hashed with the rest of the turn's records. Writing the same counts onto membership links
in the graph is the hypergraph step the Director asked for: a body is one link over many positions,
and a workplace is one link over the households that earn there, each with its households and hours
on it. That step waits on two things outside this slice: the Director's act to fill the membership
payload (ADR198 R4; PER-44) and an accessor in the upstream graph library (hypergraph-rs issue 2).
Until then the graph payload is recorded as blocked on those two, which is the disposition the Game
Design Standard requires. **[Record needed]**

### 7.10 Class reading

- Each position shows a **livelihood profile**, Derived for the period just closed. The wage is the
  position's own. Ownership income, county support and mutual aid are held by the engine only for
  the whole budget group, so they are shown as the group's totals and labelled so. They are never
  shown as a household's.
- **MIM's reading is shown beside each source of income,** not as a label on the position.
  **[Call]** **[Record needed]** The amounts are Derived. The words are Designed and are marked so.
  - Beside wages: "MIM reads wage and salary income inside U.S. borders as labor-aristocracy income
    or higher, unless the earner is undocumented. Legal status and the wage-against-value term are
    not in this slice."
  - Beside ownership income, MIM's own sentence and then the game's note: "What is important is not
    the literal ownership of means of production but access" (MIM, on the bourgeoisie). "The
    accounts hold only income received from ownership. They hold no access to credit and no net
    worth."
  - Beside county support and mutual aid: no reading.
  - Where a position has neither wages nor ownership income: "No wage in this period. MIM's reading
    here turns on nation and legal status, which are not in this slice."
- The reading follows each dollar of income. It does not sort households into classes, and it is the
  same however households are grouped. No partition is claimed by it, so Article II's proof is owed
  only for the positions (section 7.14).
- No position is called "workers", "proletariat" or "the base".
- Each position shows its **band** at the opening, with the Director's words for that band beside
  it, marked Designed. **[Director]** A band is not called a class. MIM's reading stays beside each
  source of income.
- Beside the bottom 50% the words "they don't own homes" are shown as the law's. The view adds:
  "Homes and wealth are not in this slice."
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
| County ledger | Is there relief money to move, for how long, and who is first in line for it? | The lines in pay order with the City PD's line, the money for relief announced for next period, the county's cash, the roll by budget group, the order of the list | Nothing directly | Next period's payment receipts |
| Roster | Who lives here, where does their wage come from, and where do they stand toward the roll? | Above the positions, who works in each band this period. Then each position in the order of the list: its band, its budget group, its workplace or "no wage", its units, its sources of income with MIM's reading beside each and, where earned, its dollar figures and how many are reached | Choose a position for a review contact | The contact's receipt |
| Preview | What would the next session do if I reached one more household here? | Whether a place is open, whose unit would be taken, and who would then have a unit at stake | Confirm or cancel the contact | The session record |
| Session record | Who came, who was paid, who was ranked too low, and who stayed home and why? | The county's list, each position's count and reason, each body's roll | Nothing directly | Next period's receipts |
| Food run | Is a food run worth this period's practice? | Parcels the organization's households can spare, parcels delivered and eaten last run, hours each side was charged | Choose a local aid run | The run's receipt |

**Folding for reading.** The roster can have a hundred positions or more. A view may fold
neighbouring positions into one line. A folded line shows counts and money added up. It shows a rate
as one total over another, with the lowest and highest rate inside it, and says that it is folded.
No rule reads a folded line.

**What is public and what is earned** (ADR182 R2). **[Call]**

- Public record: the county's lines, its money for relief, its cash balance, the two claims, the
  roll by budget group, the order of the list, and every session's list. A list shows each
  position's rank and its units paid and not paid. It does not show the wage tax behind a rank.
- Who works in each band: the households of the band, those with someone at work, those only looking
  for work, those with nobody in the labor force, its people at work, its people looking for work,
  and the units it holds. These are county totals, like the roll by budget group, and they are
  public. They are worked out again every period.
- Structure, shown for every position: its six answers (section 7.2) and which sources of income it
  has. The player names a position by its structure, so a contact needs nothing that is earned.
- Earned: a position's dollar figures (its wage tax, its wage, its stake), how many households it
  has, and how many of them are reached. The player sees these only for a position where the player
  has made a contact. For any other position the views show the structure, hide the amounts, and
  state the remedy: reach a household there.
- The preview needs only the public record: the order of the list and the units held below a place.
- The preview is something the player knows. It is never part of the turn's hash. It uses the last
  period the player has seen close, and says so. The session itself uses the period that has just
  closed, so the two can differ if wages or the county's cash moved in between.

### 7.12 State, order in the turn, and where the rules live

**New records,** all hashed with the turn except the preview:

- the county administration's configuration, with the roll and the unit price it keeps;
- the roster: for each position, its households and its reached households, with each split made in
  the period;
- for each session: the money for relief, each position's place, the list with units paid and not
  paid, each position's count with its reason and hours, and what was declined;
- the support lines for the next period;
- each body's roll for the period;
- the organizer's review contact and its receipt;
- the City PD's three numbers, which are one number today: its appropriation, its hourly wage and
  the price of a visit. With them, its payroll record: the workplace, the positions and the amount.

**Order in the turn.** The period's accounts close. The organizer's practice is carried out, which
is where a review contact lands and a food run completes. Then the session runs: the roster, the
list, household counts, hours and the lines. The lines are paid in the next period's close. The
engine already stores the support lines in the turn's state. It accepts a new line, a changed amount
and a removed line, and requires every amount to be positive. Nothing writes them today.

**What the engine lacks for this,** as the readers reported it:

- A fact about each budget group's labor that survives the close. While the accounts close, the
  engine holds for each budget group at each workplace the workers and job-seekers at the start and
  end of the period, the hires and separations, the hours planned and paid, and the wages. It also
  holds the wage tax assessed and collected for the group. None of this is handed to an operation
  that runs after the close. The organizer's own facts are built at the same point and kept, and
  this needs the same.
- A way to charge hours to a large budget group. The organizer's time layer charges only household
  groups bound to the organization and refuses any other. The layer below it accepts a use of hours
  from any group that has a time receipt. The session needs its own path.
- A way for an operation that runs after the close to change the support lines of the closed state.
  Today such operations rebuild only their own sections.
- A guard in the turn runner for a second operation after the close. Today it names the City PD's
  alone.
- Separate numbers for the City PD. Today one constant is the appropriation, the wage and the price
  of a visit, and the build refuses a campaign in which the wage differs from it. The City PD also
  has no workers of its own: it pays one named household for one hour.

**Where the rules live.** Each new rule is a rule entry that calls a native operation, as the
organizer and City PD rules do, with its role, its evidence class and its attribution row. The
engine's list of native operations is closed, so the session needs a new one. Its allowance and
attribution rows arrive with the code, not before. The numbers stay in the scenario's defines file.

**Evidence classes.**

- Existing Designed values that this slice reuses: the unit ($280), the session's 2 hours, the
  contact's 2 hours, the $24 wage, the 15% wage tax, the budget groups themselves.
- Derived: places on the list, the money for relief, units paid and not paid, stakes, rolls, the
  roster's counts, the livelihood profile.
- New Designed rules, each needing a record (section 8): relief as a fixed total; ranking by the
  wage tax on a household's own wage; positions by workplace; the placements of section 7.2 and
  their tie order; one crew for each household; the sharing of unpaid tax; ties keeping the holder;
  positions at one place losing in proportion; unpaid units falling on reached and unreached
  households in proportion; paying from the top when short; collective residence outside the review;
  relief lasting one period; one session a period from period 4; the floor; each one brings one, at
  2 hours, within a position; the opening reach; the session roll; the words of the class reading;
  the size of the City PD's line.
- Observed: none directly. The City PD's position count becomes Observed when the reference pipeline
  captures its source. Calibrated: none.

### 7.13 Quantities that must balance

- The roster: the positions of a budget group sum to the group's households. The people at work and
  the people looking for work in a crew's positions are the people the engine holds there. The units
  in a group's positions are its units on the roll, less any that left with a household. Reached
  households in a position are never more than its households.
- The bands: the households of a band are its households at the opening, less those that left. In
  each band, the households with someone at work, those only looking for work and those with nobody
  in the labor force add to the band's households. No household of the top 1% is in the labor force.
  At the opening every household of the next 40% is in the labor force.
- Every split moves whole households and adds back exactly. A household that changes position is
  counted once, before and after.
- For each position and session: households reached = households that came + households that stayed
  home, each with a reason. Unreached households are untouched.
- Hours charged = 2 for each household that came, plus 2 for each household brought. They are never
  more than the group's free hours.
- Places on the list are worked out from the period's wages, workers and tax receipts. No number is
  written in.
- Units paid = the units the county's money covers, or every unit listed if that is fewer. Each unit
  paid to a household off the roll is a unit not paid to a household on it.
- No unit moves between households at the same place.
- Money: each group's line is whole units at $280. The household lines and the collective-residence
  line sum to no more than the money for relief. What is left over is less than one unit, plus any
  unit an exact tie left unpaid, and it stays with the county.
- The lines the county announces are the lines the next close pays, in full.
- First-class amounts, the spending limit and tax rates are the same as in a run with no sessions.
  Tax receipts and the county's cash need not be: relief paid to different households is spent
  differently, and that changes what the county collects. The difference is a result to report, not
  an error.
- The City PD: its payroll is its positions times a period's hours times the wage. The grant of the
  workplace that employs the force is never smaller than that payroll. Every line, grant and worker
  is what it was before.
- A roll is never more than the households that gave hours that period.
- Persons, employment and the household lifecycle are untouched.
- No random draw anywhere. The same inputs give the same receipts and the same hash.

### 7.14 Why the grouping survives splitting and merging

Article II asks for a proof that a grouping does not change the result. The declared scale is the
county. The declared grouping is the position.

**The statement.** A rule of this slice reads only a household's answers and figures worked out from
them. Of the six answers the band is the one no rule decides by: it only settles the last exact tie
of a split. So it treats households with the same answers alike. Deciding once for a position and
multiplying by its count gives the same number as deciding for each household and counting. A
simulation that carried every household one by one, under the same rules, must give the same count
in every position. Split a position into two with the same answers, merge them again, or rename
them, and every count is the same. In Lawvere's terms the rule is pulled back from the position and
the count is pushed forward; Appendix D gives the words.

**Each rule of this slice reads only such figures.**

| Rule | What it reads | Why every household of a position shares it |
|---|---|---|
| The county's list | A household's place, and the units it holds | A position is one budget group, one crew, one number of people at work and one number of units |
| Whether a household comes | Its own stake, which is a unit or nothing, and the floor | The households of a position that lose, and those that do not, are counted apart |
| The hours | Its budget group's free hours | Hours are a total for the group, and the charge is a sum |
| The spread | The position of a household that came | By definition |

**Where a count can differ by one.** Whole units and whole households cannot always be shared in
exact proportion. Largest remainder gives every part its exact share to within one, and the totals
exactly. Two declared rules settle exact ties: a unit in an exact tie between positions is not
moved, and a household in an exact tie between kinds goes by the fixed order of kinds. A different
grouping can therefore move a result by at most one unit or one household for each split it makes.
The bands are such a split: two positions that differ only in band stand at one place on the list,
and the tie rules of section 7.4 apply to them as to any two positions. Money is never rounded,
because lines are whole units.

**Merging positions with different figures changes the result, and must.** Two workplaces that pay
differently would be given one average place that neither has. That was the error of the fourth
draft. The list cannot be coarser than the positions.

**The limits of the proof.**

- It holds down to the floor of the grain. One budget group's workers at one workplace are taken as
  paid alike, because the engine holds nothing finer.
- It holds for the placements as declared. A different placement is not another grouping of the same
  households. It is a different statement of who the households are, and it gives a different roster
  and a different result. Section 9 runs each placement at its other bound.

Section 9 turns these statements into tests.

## 8. Decision records needed

The Director has made the ten decisions in section 2. Project law requires each to be written into a
decision record before it is built, and several of the author's calls need the same. The plan will
say how many records these become. The list is what must be decided and written down.

| # | Subject | What the record must say | Why it needs a record |
|---|---|---|---|
| 1 | The county administration, a second state actor | Its authority, objective, resources and knowledge, as in section 7.3. Only its list changes a household support line. The first class, the spending limit and taxes are closed to it. This partly supersedes ADR299's sentence "The county's ordinary fiscal accounts continue to determine payments." | ADR291 approved the City PD by name as the first state opponent. ADR184 requires a budget to have an owner |
| 2 | The county's rule | Ranking by wage tax paid, as the Director ruled. It is an ADR184 allocation: the county's yield from a unit is the wage tax the household pays, and every unit costs the same. The details the ruling left open: a household's place is the tax on its own wage, as section 7.4 defines it; positions at one place lose in proportion; an exact tie moves nothing; a household that asks comes only when a place is open; relief won lasts one period. The record must also say that a ranking by yield with no threshold is not a "fixed political-response curve" | ADR184 R3, R4, R9; ADR291 |
| 3 | The household's rule | Own money only. The floor, as the Director ruled, written in the form Amendment AM requires: the number that come is the count of reached households whose own stake is at least their own cost of time. A stake is a whole unit or nothing. Unpaid units fall on reached and unreached households in proportion. A household ranked last still comes. An hour is valued at the wage for every household. The record states that the step at $280 is the real spread of stakes, and names what would change it | Constitution Article III as amended; ADR173; AGENTS.md |
| 4 | When the county is short | The list is paid from the top. Collective residence is outside the review and is cut only in proportion. The county publishes its cash, its roll and the order of its list at each session | It replaces the engine's identifier order for household support |
| 5 | Each one brings one | A Designed rate, the Director's. One household of the same position. Two hours for each household brought. Nothing can be called back | It sets how fast anything spreads, and how far |
| 6 | The session roll | A household's own hours in the county's room put it on a body's roll for that period. The roll records who came, not agreement. Any Wayne household may be charged hours on its own recorded choice. This amends, for this one act, ADR262's "Neither operation writes solidarity, membership" and ADR270's rule on what creates membership | ADR270; ADR262; ADR299 |
| 7 | The review contact, and where the session sits in the turn | A new organizer choice, open to any organization, that names a position. It is new content vocabulary, so it needs the Director's ceremony, schema and conformance updates and a recording record. The record says how it sits with the nine verbs of ADR177. It also states the Article III reading of section 7.5 | Constitution Articles III and VIII |
| 8 | The roster and how households are counted | The four rules of section 7.2. Positions by workplace, with the floor of the grain. The declared placements, each with its other bound, and the order that settles ties. That all of a household's people in the labor force belong to one crew. The bands of the rule of thirds on the roster, how they are sized and filled, and the two checks at the opening. How unpaid tax is shared. That the roster is a table of counts and not a new kind of field. That an exact split with no draw owes no kernel receipt | ADR269; ADR296; ADR176 ruling 17; the Game Design Standard; Amendment AJ |
| 9 | The class and nation text on screen | As in section 7.10: a reading beside each source of income, and no label on a position. A figure held only for a budget group is shown as the group's | The ideological line is the Director's |
| 10 | The aid road's roll | CHARTER: no roll in this slice. It arrives with the kitchen | The Director's ruling; Game Design Standard W.2 |
| 11 | The graph payload | Either "blocked on PER-44 and hypergraph-rs issue 2", or the Director opens the payload ceremony in this lane. It covers a body's link and a workplace's link | ADR198 R4; Game Design Standard W.2 |
| 12 | Opening conditions and evidence gaps | The first session in period 4. The opening reach of 2 and 3 households, which moves no money. The two standing claims. No organizer for either body. Geographic and sector variation recorded as BLOCKED, because the slice is one county | They are Designed; Constitution Article VIII |
| 13 | The City PD's budget | Three numbers in place of one. The payroll: positions, hours and the wage, from a named count, carried as a record on the public workplace that employs the force. The engine's lines and the opening economy do not change. One visit a period, as before. It amends ADR291's sizing of the proxy and leaves the rest of that record standing | The Director's ruling; ADR291; ADR184 R4 |
| 14 | Amendment AM | Article III carries ruling 5 in its own words, and the amendment says how the rule is applied: a rule may decide for one member by comparing material amounts held for that member, and three forms stay prohibited. It is written as ADR300 on this branch, with the status proposed (Appendix E). The Director's acceptance of the wording accepts it. The branch must not merge while it is proposed | Constitution Article VIII |
| 15 | The rule of thirds | The Director's anchoring law: the top hundredth of a population holds a third of the wealth, the next nine hundredths a third, the next two fifths a third, and the lower half nothing. With it, the Director's statement of who works in each band. The bands and that statement bind the opening roster of this slice (section 7.2). The shares of wealth bind the opening split when positions hold accounts of their own (section 11). After the opening both are measured and never enforced | The Director's direction of 19 November; the owner's ruling of 16 July on empirical laws |

## 9. Build order and proof

The engine has no recurring proceeding, no action that reaches a household outside the organization,
no change to a budget line after the opening, no state actor that rules on anything, and no count of
households finer than a budget group. Each piece below can be played or checked on its own.

| Piece | What it adds | How it is proven |
|---|---|---|
| 0. The City PD's books | Three numbers in place of one. The City PD's payroll, named on the public workplace that employs the force | The balances of section 7.13. Every line, grant and worker at the opening is what it was. The City PD's existing tests pass on the new numbers. A campaign with another wage is accepted |
| 1. The roster, the ledger and the views | The labor fact that survives the close. The roster, built at the opening and brought up to date each period. The county ledger, the roster view and the food run view. No rule reads them yet | The roster adds back to the engine's counts in every period of a long run. Every figure on the ledger equals the engine's own receipts. Every existing section of the turn keeps its bytes |
| 2. The session | The review contact, the list, household counts, the lines, the rolls, the spread, the session record and the preview | The proof list below |
| 3. Rolls and workplaces in the graph | The rolls and the roster written onto membership links, with their hash section. Only after record 11 opens it | The graph counts equal the session records every period. The new hash section is absent when empty |

**The proof list for piece 2.** Each line is a test or a recorded run, written before the code it
proves.

- **Balances.** Every line of section 7.13 as a property test.
- **No rule reads an average.** Two workplaces of one budget group swap their paid hours. The
  group's totals and averages do not change. The county's list must. A second test replaces each
  position's place with its group's average, and the session's result must change. This is the test
  Amendment AM asks of an emergence claim.
- **The grouping.** The statements of section 7.14: split a position in two, merge two positions
  with the same figures, rename a position. Every count is the same, to within one unit or one
  household for each split.
- **The other bounds.** Each declared placement is run at its other bound, and the difference in who
  holds and who loses is reported. This is a report for the Director, not a pass or a fail.
- **Twins.** The same opening run twice: once with the player's first contact and once without.
  Without it no unit moves: every line the county sets is the roll's own, and the session records
  hold only the households reached at the opening, each staying home with its reason. On the
  recorded opening every payment equals today's run.
- **What the review cannot touch.** In every run, with or without sessions, every first-class
  amount, the spending limit and every tax rate are identical. The differences in tax receipts and
  county cash between the twins are measured and reported.
- **The county keeps its word.** In every period the lines the county announced are the lines it
  paid.
- **Counterfactuals.** Give every household the same wage tax, and nothing moves. Swap the paid
  hours of two workplaces, and relief moves the other way. Set the unit below the floor in a test
  scenario, and nobody comes. Set the money for relief to nothing, and nobody is paid.
- **Sever tests.** Each of these links is cut in turn by a deliberate fault, and a test must fail:
  employment records to the roster; wages and tax receipts to places on the list; places to who is
  paid; the list to next period's lines; the lines to the payments; a household's own unpaid unit to
  whether it comes; coming to the roll; the roll to who is reached next; the contact to who is
  reached.
- **Direct-write audit.** Only the county's list writes a household support line. Only a household's
  recorded choice charges its hours. Only the session writes a roll. Only the engine's own hires and
  layoffs, through the declared placements, move a household between positions. The scenario writes
  none of the results.
- **Replay.** Replaying and reopening a campaign gives the same receipts and the same hash, byte for
  byte.
- **Persistence after the event.** The player makes one contact and never returns to the county. The
  claim must keep itself going, stop at the edge of its position, and end when the county's money
  for relief ends.
- **A witness for every outcome.** Each outcome the records can name is reached in at least one
  committed opening, by changing opening conditions only: paid a unit; no place; workmates off the
  roll not taking from workmates on it; a household at a better-paid workplace taking from one at a
  worse-paid workplace; in the room and ranked last; a stake under the floor; no time; no money for
  relief; the county short and paying from the top; an exact tie; a position with nobody left to
  reach; a household that loses its wage and stays reached.
- **Ceremonies.** Baseline changes carry the required trailer. Schema and conformance contracts
  change with the code. The allowance and attribution rows for the new operation arrive with it.

**What cannot be shown yet.** Article VIII also asks for geographic and sector variation. The slice
has one county, so that evidence is recorded as BLOCKED (record 12).

**Play proof for the whole slice.** Four recorded playthroughs from the same seed, each run past the
period in which the county runs short, each driven through the real client with no screen, and each
kept as seed, action log and result. Each also records who works in each band, period by period.
They differ only in the player's line: no contact at all; opening one workplace's households with a
wage; opening two; food runs only. They must give four different records that the receipts explain.
The tutorial chapter that walks a new player through the first session is the acceptance script.

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
- Whether the session is one native operation or two: the households' counts, and the county's list.
- Where the labor fact is built and what it holds, within section 7.12.
- How the roster follows a budget group whose households fall below its households with people in
  the labor force. Appendix D refuses that case with a typed error, and no run of this slice reaches
  it.
- How the session charges hours to the large budget groups (section 7.12).
- How the roster's exact split is built. The engine's own split settles ties by the caller's order,
  and the roster needs the tie rules of Appendix D.
- How an operation after the close changes the support lines of the closed state, and the guard the
  turn runner needs for it.
- How the county's figure for its money for relief is made to match the engine's payment step
  exactly. Section 9 holds the proof.
- How a group's line is removed when the group holds no unit, and restored.
- How the named police count is captured through the reference pipeline. The force as a workplace of
  its own is left to the opponent's lane (section 7.3).
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
  of its own. Labor status as a household decision. Nation, legal status and the wage-against-value
  term.
- **Wealth, anchored on the rule of thirds.** **[Director]** On 19 November the Director gave the
  lane an anchoring law: "1% of the pops owns 1/3 of the wealth, 1-10% own next third, 10-50% own
  last third, >50% have net zero wealth". It "can eventually of course fluctuate due to
  stochasticity or class struggle". The project already holds the evidence. United States wealth
  shares in 2024 were 34.8%, 34.8%, 29.5% and 1.0%, and the lower half held between −1.8% and 3.7%
  of all wealth from 1913 to 2024 (`reports/test-estate-audit-2026-07-16.md`). This slice holds no
  household wealth and no rule that reads it. The Director then said that one part of the law
  belongs here all the same: who works in each band (section 2). So the bands are on the roster now,
  with the two opening checks of section 7.2, and the shares of wealth wait for the next slice. When
  positions hold accounts of their own, the opening split of a county's household wealth follows the
  thirds, band by band, as a declared split with its source named. After the opening the split moves
  only by what households earn, spend, win and lose. It is measured each period and never pulled
  back. The owner ruled that form in July: an opening contract without condition, and during a run
  only the reverse test, that a distribution outside the band has a rupture in its history. In Wayne
  the two budget groups with business ownership are 70,060 of 700,583 households, which is one
  tenth. This slice already takes them as the top tenth (section 7.2). So the share of household
  wealth they hold can be measured from the engine's accounts as they are, and set beside the two
  thirds the law gives the top tenth. That measurement is the first task of the next slice, and it
  tests the reading. **[Call]**
- **Homes.** The Director's law says the bottom 50% do not own homes. The engine holds no housing
  tenure. It enters with household wealth.
- **Households as the sources count them.** A census table of households by number of workers, and
  one by the work status of their members, would replace the first three declared placements with
  observed counts.
- **Rivals and masses.** A second organizer that opens positions for itself. Businesses as a body at
  the county, ranked by the tax their sites pay. Organizing that spreads through workplaces, which
  the roster now makes possible. Opening rolls from observed union membership.
- **The City PD with a real budget.** What a paid force does with its hours, in the opponent's lane.
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
- **The first year is slow.** One household becomes 8,192 over fourteen sessions. Little money moves
  until late.
- **The declared placements decide who loses.** No source says whether the households that hold a
  unit are the ones that kept a wage. The placements send a hire to a household with a job-seeker,
  and at the opening those are the households on the roll. They take a layoff from the households
  with the most at work. How many units end with households that have no wage has not been counted.
  That needs the people at work in each crew in each period, which no recorded file holds. Section 9
  runs each placement at its other bound and reports the difference. The choice is the author's, and
  it is open to the Director.
- **When work is plentiful, the top of the list is households with two wages.** At the opening the
  largest group has more people at work than households. A household with two people at work pays
  twice the wage tax of a workmate's household with one, and can take its unit. In the recorded run
  this does not arise in the sessions. By period 4 the largest group is paid for a tenth of the
  hours its people at work at the opening could give.
- **A workplace that cannot pay all its wages pays its budget groups in the order of their
  identifiers.** That is the engine's rule today. A group paid short stands lower on the county's
  list. This slice reads that result and does not change it.
- **Most households can never take a unit.** A household with no wage pays no wage tax and stands at
  the bottom. That includes every household that lives on ownership income alone, because the engine
  does not tax it. In period 4 the two groups with business ownership received $142 million in
  ownership income. How many households have no wage in a period has not been counted (section 3).
- **A claim takes from its own budget group too.** Relief moves from households with no wage to
  households with a wage, whatever their budget group. The Director ruled the ranking on a preview
  in which "job-seekers in wage-earning households keep their units". That is true of a household
  that has a wage now. It is not true of every household in the group named "with earnings": in
  period 4 that group was paid for a tenth of the hours its people at work at the opening could
  give.
- **Positions are large.** The map of the recorded run shows 18 groups of producers, three shops and
  two utilities in Wayne. A workplace in the engine is a whole branch of the county's work, not a
  firm. So a single contact can still reach tens of thousands of households.
- **The worked tables are replaced.** The older recorded files hold wages for each budget group and
  not for each crew, and they do not hold the people at work or the wage tax collected. The
  recorded playthroughs of this slice hold all three, and sections 3 and 7.7 take their figures.
- **Households that are ranked last keep coming.** By the rule they come every period in which their
  own unit is not paid, and it changes nothing for them. When the county stops paying relief
  altogether, every reached household on the roll comes each period for as long as that lasts.
  Section 7.5 gives the other reading.
- **The floor binds nobody today.** Every stake is a whole unit or nothing. The Director chose the
  floor over the author's recommendation. With today's numbers the two give the same result.
- **The second road writes no roll in this slice,** moves at most four parcels a period, and in the
  recorded run ends by period 4.
- **Money is pooled.** A unit is paid into a budget group's account. The engine cannot say which
  household received it. The roster is the county's record laid over a pooled account.
- **The order of the list changes as wages change.** A household that wins a unit while it has a
  wage loses it when the wage goes. In the recorded run the largest group's paid hours fall by four
  fifths between periods 2 and 4. The worked figures hold period 4 for two years.
- **Moving relief changes the county's own income** (section 7.13). How much has not been measured.
- **The preview can be one period stale.**
- **The City PD's payroll rests on one city's count,** and on the reading that the force is employed
  in the county's public workplace for local government. The federal files do not show local police.
  The engine pays the force from a county account, which ADR291 calls a proxy.
- **A payroll on the books does not make the City PD do more.** It still makes one visit a period. A
  player may read a $13.6 million line as a force that acts on that scale.
- **Amendment AM binds every mechanic, not only this slice.** The July audit covered the live rules
  of that time, and ADR173 left three findings open. This design did not audit the rest of the game
  again. The amendment's scope sentence, its general construct and its three prohibitions are the
  author's wording. The Director has not read them. Its record is proposed, and the branch must not
  merge while it is.
- **Three questions are open for the Director.** Whether Amendment AM's wording is accepted. Whether
  an exact table of counts is a lawful way to carry a group's spread under ADR176 ruling 17, which
  named moments or a fixed-size sketch. Whether the hours a household spends in the county's room
  belong to the period just closed, as the engine's check on household hours expects, or to the next
  under Article III.
- **Only part of the rule of thirds is in this slice.** The bands and the Director's statement of
  who works are on the roster. Nothing here holds household wealth, so the shares of wealth are
  recorded and bind the next slice (section 11). Three things in the banding are the author's
  reading and are open to the Director: that the engine's business owners are the top tenth; that
  the next 40% is filled by the number of people at work; and that an opening which cannot obey the
  law is refused.
- **The engine gives relief to owners who are looking for work.** At the opening 5,618 units are
  held by households of the next 9%. The Director's law puts welfare with the bottom 50%. Those
  units were not moved, because that would change the opening economy and every recorded figure that
  follows from it. The views show them as they are.
- **Turn time.** On the recorded runs the organizer's turns took 11 to 16 seconds, and the
  qualification report records several turns over the 30-second budget. The session adds work to
  every Wayne turn. In the headless playthroughs a close took 8.4 to 10.3 seconds (mean 9.0 over
  136 closes) with the session held, on the build machine.
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
  (`rust/crates/babylon-persistence/src/national_economy/opening/financial.rs:126-145`). The engine
  stores the result as an amount for each group. It stores no count of units.
- The engine's state holds households and persons for every budget group. An ordinary group must
  have at least one household. A collective residence must have none
  (`rust/crates/babylon-material-circuit/src/recurring/model.rs:23-45`).
- People are bound to workplaces. A staffing member is one budget group's people at one workplace.
  Its labor force is fixed and can only fall. Each period it is split into people at work and a
  reserve of people looking for work. A workplace's hires are shared among its members in proportion
  to their reserves, and its layoffs in proportion to their people at work. A member never hires and
  lays off in the same period (`rust/crates/babylon-material-circuit/src/staffing/members.rs`).
- At the opening, workplaces take their workers and job-seekers from the budget groups' totals one
  after another, working owners first. The engine does not spread every group over every workplace
  (`rust/crates/babylon-persistence/src/national_resident_allocation/households.rs`).
- A workplace's planned hours are shared among its members in proportion to their available hours,
  by largest remainder. Each member is paid for its attended hours at its own hourly rate, into its
  budget group's account. A working owner and an unpaid family worker attend and are paid nothing.
  When a site's cash runs short, its members are paid in the order of their identifiers
  (`rust/crates/babylon-material-circuit/src/payments/attendance.rs:276-400`).
- The engine's exact split gives each part the whole part of its share, and hands the units left
  over to the largest remainders. Equal remainders go by the caller's order
  (`rust/crates/babylon-material-circuit/src/staffing/members.rs:178-209`).
- The allocator of ADR184 ranks whole candidates by a floating-point ratio of yield to cost, breaks
  ties by the candidate's own fields, and records each one it could not afford with what was left
  (`rust/crates/babylon-graph/src/capacity.rs`).
- A use of household hours is accepted only for the period before the state's own
  (`rust/crates/babylon-material-circuit/src/household_time.rs:594-601`). The organizer's time layer
  refuses a contributor that is not bound to the organization
  (`rust/crates/babylon-tick/src/material_world/organizer_time.rs`).
- The City PD's $24. One constant of 24,000,000 millionths is the City PD's hourly wage, the price
  of a visit and its appropriation. The build refuses a campaign whose wage is not that amount,
  raises the county's spending limit by it, and pays one named household for one hour. The City PD
  ranks one candidate with a fixed yield of 1 and funds at most one visit
  (`rust/crates/babylon-persistence/src/national_economy/city_pd.rs:25,104,184-188,236-243`;
  `rust/crates/babylon-tick/src/state_opponent.rs:88-99,236-250`).
- A grant is paid to each site whose function is public provisioning
  (`rust/crates/babylon-persistence/src/national_economy/opening/financial.rs:68-90`).
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
- The map of the recorded run shows 18 groups of producers, three shops and two utilities in Wayne.
  Turn times are from the same report (`reports/economic-flows-qualification-2026-11-14.md`).
- The claimant and aid figures come from a second recorded campaign, `e841f4b2`.
- Police figures from outside the repository. The federal employment files for 2024 on the data
  drive (BLS QCEW, annual, by industry) give for Wayne County: police protection, federal 2,168 jobs
  and state 323, with no row for local government; justice, public order and safety, local
  government 242 jobs; public administration, local government 24,286 jobs. No loader in the
  repository reads these files. The City of Detroit's council budget analysis of 21 March 2025 gives
  its police department 3,529 positions and $441.9 million in the adopted budget for the 2025 fiscal
  year. From these: 3,529 positions at 160 hours and $24 are $13,551,360 a period, and $441.9
  million a year is $33.9 million for 28 days.
- The worked tables of the fifth draft came from a short script that counted wage earners as
  full-time. They are withdrawn (section 2).
- A budget group's wage tax is assessed on its wage income for the period
  (`rust/crates/babylon-material-circuit/src/valuation/financial.rs:16`). The tax receipt holds the
  taxed amount, the tax assessed and the tax collected (`financial/model.rs:133-143`). A crew's
  labor record holds the wages accrued to it in the period (`payments/attendance.rs:62-86`).
- The City PD's investigator is bound to the second of the aid groups, the Wayne aid recipients, and
  the investigator-hour is paid to that group as a wage
  (`rust/crates/babylon-persistence/src/national_economy/city_pd.rs`;
  `rust/crates/babylon-tick/src/material_world/agency_paid_receipt.rs`).
- In a period the engine first removes the people who left the labor force, and then hires or lays
  off (`rust/crates/babylon-tick/src/material_staffing/composition.rs`). People who left are taken
  from a group's people at work and people looking for work in proportion
  (`rust/crates/babylon-material-circuit/src/household_lifecycle/workforce.rs`). A crew's record for
  the period holds its people at work and looking for work at the start and at the end, its hires
  and its separations (`staffing/members.rs:136-153`).
- A group's households fall only when its persons fall below them
  (`household_lifecycle/advance.rs:222`).
- The claimants are 2 households and 2 job-seekers, carved from the group with no earner and no
  business ownership (`opening/claimant.rs`; `defines.toml`). The aid groups are 4 households each:
  the givers have 4 people at work, and the receivers have nobody in the labor force
  (`opening/aid.rs`).

**Reported by read-only readers on 18 and 19 November 2026, and not all re-read by the author.**

- Opening counts for each budget group come from one reader's replica of the engine's opening
  allocation, run on Wayne's census controls. It gives: with earnings and no business ownership,
  456,532 households, 646,991 people at work and 38,837 job-seekers; with earnings and business
  ownership, 50,726 households, 101,931 at work (57,474 working owners and 44,457 employees) and
  2,669 job-seekers; no earner and no business ownership, 173,999 households, nobody at work and
  26,538 job-seekers; no earner with business ownership, 19,334 households, nobody at work and 2,949
  job-seekers; collective residence, 8,151 at work and 772 job-seekers. The aid groups take 4
  households each from the first and third groups, and the claimants take 2 from the third. The
  replica reproduces the recorded job-seekers of all five groups and the recorded households of the
  largest. Its other household counts were not checked against a run.
- Business ownership is given to one tenth of the households of each earnings group by a Designed
  setting: `private_owner_households_bps = 1000` in `content/scenarios/national/defines.toml`. Its
  comment reads: "Designed exposure within each historical earnings margin; not observed
  wealth/class."
- A workplace sets its people at work for the next period from the hours it asks for, or the hours
  it asked for in the last period if that is more, divided by 160 and rounded up, and never above
  its labor force.
- No recorded file holds the people at work in a budget group after the opening, or the wage tax
  collected.
- The reference data holds households by type, by income and by earnings in the last year. It holds
  no table of households by number of workers or by the work status of their members.
- Nothing moves a household from one budget group to another. A group's households can only fall,
  and only when its persons fall below them.
- The receipts of a close for staffing, hours, wages and tax are used while the close is prepared.
  An operation after the close is handed typed facts for the organizer and the encoded bytes of the
  receipts, and no typed fact for a budget group's labor.
- The organizer has 2 committed hours a period. No existing choice reaches a household outside the
  organization's own. The collection choice names one of the organization's own households.
- Every household group pays wage tax at 15% on wages accrued in the period, out of the cash it has
  left after its purchases. The receipt holds the amount assessed, the amount collected and the
  difference. Ownership income is not taxed. Sites pay a separate tax on operating income. All of it
  goes into the one county account that pays grants, support and the City PD.
- Paying grants and support is the first money step of each close. Nothing moves the county's cash
  between the end of one close and that step of the next.
- The engine accepts a new household support line, a changed amount and a removed line. Every amount
  must be positive. Nothing checks support against job-seekers after the opening. A changed line
  takes effect at the next close.
- When cash is short, lines are paid one after another in list order and one is part-paid. In the
  recorded run the grants take all the cash from period 30 and household support is paid nothing.
- A public site's grant is its payroll, which is its people times 160 hours times the wage, plus its
  inputs, less its fees. Police jobs are inside the public sites' people. The recorded run was made
  without the City PD's line.
- The $24 is pinned in the City PD's row check, in the practice contract and in at least nine test
  files. No conformance vector, baseline or client text carries it.
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
  households with a wage above households with none. The sentence is not a ground for that rule.
- Who counts as labor aristocracy: "salary and wage-receiving people within U$ borders are
  labor-aristocracy or higher, unless they are undocumented." (mim-class-structure MC-02). Legal
  status is not in this slice, and the text on screen says so.
- On the public sector: "In some ways, the government sector is the ultimate expression of the
  imperialists' loyalty to the oppressor nation working class, since it is difficult to ship
  government service jobs overseas." (mim-class-structure MC-21). MIM is speaking of nation and of
  government jobs. This slice has no nation. Its first class is grants to public sites and a police
  line, and no claim can touch either. The sentence grounds nothing here. It is a reason for a later
  slice to look at whom the county's money employs.
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
- On ownership: "What is important is not the literal ownership of means of production but access"
  (mim F06). The text beside ownership income quotes it (section 7.10). The engine's accounts hold
  income from ownership and no access to credit.
- On wealth: "net worth is means of production, in which home equity and pension funds have to be
  counted." (mim-class-structure MC-05). MIM also writes that "the capitalist class can be estimated
  at one percent" (mim F06). This slice holds no household wealth. It carries the bands of the rule
  of thirds and who works in each (section 7.2). The shares of wealth enter in the next slice
  (section 11).
- Two findings bear on a later slice with elections, and on nothing here: "The majority of white
  Amerikans support or participate in the electoral system." (mim F15), and "It is possible that in
  elections to city hall, some small battles can be won locally" (mim F14).

## Appendix C: What the reviews found, and where this draft answers them

The second draft was reviewed on 19 November 2026 by four readers, and a second reader challenged
each serious finding (workflow journal `wf_f30fdb94-a47`). The third draft was re-checked the same
day by three readers (`wf_e6abc7ce-3a0`). The Director read the fourth draft, and three readers then
gathered the facts for the fifth (`wf_26a4cd94-6e6`). Three more readers checked the fifth draft
(`wf_5c243193-5f2`), and this draft answers them.

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
| Objectors saw only one session's increment | Section 7.5: a household on the roll comes when its own unit is not paid |
| The placement rule was said not to move money | Section 7.2 says it changes outcomes, and it needs a record |
| The grouping proof showed signs, not outcomes | Section 7.14 and the tests in section 9 |
| "Restore" was circular, and choices came down to identifier order | "Restore" is removed. No rule reads an identifier (sections 7.4 and 9) |
| No rule read the membership roll | Section 7.9: the spread reads it |
| The county had no interest of its own | Sections 7.3 and 7.4: it ranks by what it is paid |
| The $48 floor is a step and needs a ruling | Section 7.5, section 8, record 3, and Amendment AM |
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
| ADR172 ruling 5 was cited through a weaker sentence, and Article VIII's amendment clause was passed over | Section 5 quotes both. The Director ruled, and Amendment AM writes the ruling into the Constitution (Appendix E) |
| The count by share of tax was the Director's to decide, and was not in ADR184's form | The Director ruled the ranking. Sections 6 and 7.4 |
| The defense could never matter | The county no longer counts a defense. Sections 7.4 and 12 |
| A household's stake was not money the engine moves | Section 7.1 says what the engine pays. Section 7.5 gives each household's stake as a whole unit or nothing |
| Tax receipts cannot be identical with and without sessions | Sections 7.13 and 9 |
| The order of the claim and the defense left two readings | Section 7.4: the list is worked out once |
| A fixed tie order reads identifiers | Sections 7.2 and 7.4, and Appendix D: no rule reads an identifier |
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

**The Director's review of the fourth draft**

| Finding | Answer |
|---|---|
| A police budget of $24 a period is not realistic | Section 7.3: the force's payroll is named in the county's books, at a size worked out from a named count. Section 8, record 13 |
| Populations must be joined and split in a principled way, after Lawvere | Sections 7.2, 7.4, 7.5 and 7.14, and Appendix D |
| Ruling 5 survives as written, and the Constitution is to be modified | Amendment AM, applied on this branch. Appendix E, and section 8, records 3 and 14 |

**What three readers found for the fifth draft**

| Finding | Answer |
|---|---|
| The fourth draft applied the floor to a position's average loss, which is the form ADR173 replaced | Withdrawn. Sections 2 and 7.5 |
| How a group carries its spread was ruled in July | Section 5 |
| Three of the fourth draft's household counts were wrong | Section 3 and Appendix A |
| Wages are paid by the hour worked, for each budget group at each workplace, and not by the person | Sections 3 and 7.2 |
| The engine binds workers and job-seekers to workplaces, and nobody changes workplace | Section 7.2 and Appendix D |
| The close's labor and tax receipts are not handed to later operations | Section 7.12 |
| One constant is the City PD's wage, its visit price and its whole budget | Section 7.3 |
| A split in proportion is a chosen section, not an adjoint | Section 7.2, rule 3, and Appendix D |
| No joint table of households by workers is captured | Sections 7.2, 11 and 12 |

**What three readers found in the fifth draft**

| Finding | Answer |
|---|---|
| Amendment AM let a rule compare a member's amounts with no bound, and said it relaxed no prohibition | Redrafted: a stated construct, three prohibited forms, and the point it settles, said openly. Appendix E |
| The amendment did not cite ADR175, which extended the construct to every confirmed site | Cited. Appendix E |
| The table of whose words are whose gave the author's sentences to the Director | Redone sentence by sentence. Appendix E |
| The Director's answer was read as needing no exception | Section 6 and Appendix E give the fourth draft's own sentence, the answer as typed, and three ways to rule |
| A crew can have three people at work for each household | Section 7.2: any whole number |
| A working owner and a wage earner at one workplace were one position | Section 7.2: a crew is one way of being paid |
| A household can have two job-seekers at the opening | Section 7.2: a household holds one unit for each |
| People leave the labor force by age, and the roster did not follow them | Section 7.2, rule 6, and Appendix D |
| A household was placed by full-time pay, and the worked tables by the same | Section 7.4: the place is worked out from the wages a crew was in fact paid. The tables are withdrawn |
| A tie under shortage could not be settled without an identifier | Section 7.4: the unit is paid to nobody |
| A household that asked could be paid and then have no time to come | Section 7.4, step 5: hours are set aside before it asks |
| The place read the people at work after the period's hires and layoffs | Section 7.4, steps 3 and 12: the roster is brought up to date after the session |
| The published list showed wage tax, which is an earned figure | Sections 7.4 and 7.11: the list shows rank and units only |
| The contact named several positions at once | Sections 7.6 and 7.11: it names one, by its answers |
| The City PD's investigator-hour is paid as a wage to an aid household | Section 7.4: that wage gives no place |
| The claimants were shown beside the third group and inside it | Section 3 |
| "Nobody chooses its shape" was too strong | Section 7.5: withdrawn |
| Lawvere's page 22 was cited for how totals divide | Appendix D.1: it is about rates, and the text now says so |
| One on-screen sentence was given as MIM's and is not in the evidence file | Section 7.10 quotes MIM's own sentence. Appendix B |
| Household counts were said to come from a recorded file | Section 3 and Appendix A: they come from a reader's replica |

## Appendix D: How households are counted

Sections 7.2 and 7.14 state the method. This appendix gives its sources and its exact steps.

### D.1 The four rules and their sources

The page numbers are the printed ones. The texts are on the data drive (`lawvere-master/pdfs/`).

**Rule 1. Totals add.** Lawvere, "Categories of Space and Quantity" (1992), page 19:

> if a space is a sum of two smaller spaces, then a distribution of the given type on it should be
> determined by an arbitrary pair of distributions, one on each of the smaller spaces

> if I project my room onto the floor, the quantity of smoke is transformed into the quantity of
> smoke over the floor.

Every regrouping carries a total forward by adding, and the last regrouping, into one cell, gives
what he calls "its total, which is a constant." Project law already binds this. ADR296: "For finite
source-to-representative assignment q, additive pushforward preserves sums and composition."

**Rule 2. A rate is one total divided by another.** The same paper, pages 18 and 21:

> the extensive quantities are "quantity of space" and the intensive quantities are "ratios" between
> extensive ones. For example, mass and volume are extensive (measures), while density is intensive
> (function).

> the intensives act on the extensives. For example, a particular density function acts on a
> particular volume distribution to produce a resulting mass distribution.

A rate does not add. It comes back along a regrouping: each part has the rate of the whole it sits
in. A rate times a count is a total, and that total is what is carried forward. ADR189 binds the
consequence: the rate of a coarser group is weighted, "never an unweighted mean".

**Rule 3. A split is declared.** Totals do not say how they divide. That is plain arithmetic, and
Lawvere is not its source. Page 22 of the same paper makes a nearby point, about rates:

> a given mass or charge distribution may not admit a density, with respect to volume, and not only
> the existence but also the uniqueness of such ratios may require serious study

The passage says that a ratio between two totals need not exist or be unique. For a split the point
is simpler: many rosters add up to the same budget group. Choosing one is a choice with one law: it
adds back. The repository's review of an earlier design said the same of a split in proportion. It
called it a "section of a split epi, not an adjunction"
(`docs/superpowers/specs/2026-07-22-mirror-typed-core-spec.md`, a review and not a binding record).
ADR296 binds the point for its own folds: "These are tested accounting laws, not old/new transition
congruence or an invented aggregation adjunction."

**Rule 4. A rule decides for a household.** Lawvere, "Adjointness in Foundations" (1969), page 13 of
the 2006 reprint:

> take substitution as the inverse image operator, which forces existential quantification to be the
> direct image operator.

A rule about positions becomes a rule about households by substitution: a household passes if its
position does. Going the other way there are two operations, and they answer two questions. Does
some household of the position pass? Does every household pass? When the two answers agree, the
position can be decided as one. When they differ, the position is too coarse for that rule and is
split until they agree. The number that act is then the count of households that pass. That is the
Director's construct in ADR173: "the measure of class members whose wealth clears subsistence".

### D.2 Why the count does not depend on the grouping

Lawvere names the law that ties a rate brought back to a total carried forward (1992, page 22):

> in algebraic topology this homogeneity is called the "projection formula", in group representation
> theory it lies at the base of "Frobenius reciprocity"

In this slice the law says one thing. Counting the households that pass a rule position by position
gives the same number as counting them one by one, whenever the rule reads only what the households
of a position share. Section 7.14 is that statement for each rule of the slice, and section 9 tests
it.

### D.3 The placements, step by step

A **crew** is one budget group's people at one workplace, paid in one way. A position is written
(crew, k, s, u): k people at work, s looking for work, u units held. A household with nobody in the
labor force has no crew and is written (none, 0, 0, u). A position also carries its band, which is
written in front where it matters.

**At the opening.** Take one budget group with H households. For each of its crews the engine gives
E people at work and S people looking for work. L is E + S.

1. **Binding.** Add up L over the group's crews. If the sum is less than H, every person in the
   labor force has a household of their own: a crew has E households at (1, 0, 0) and S households
   at (0, 1, 1), and the group's other households have nobody in the labor force. Otherwise every
   crew gets one household, and the remaining households are shared among the crews in proportion to
   L − 1, by largest remainder. A crew then has at least one household and no more households than
   people. If two crews' remainders are exactly equal, the households in question are bound to no
   crew, and are counted with the households that have nobody in the labor force. If a group has
   more crews than households, the build refuses the campaign.
2. **People at work.** In a crew with h households, each household has the whole part of E ÷ h
   people at work, and as many households as the remainder of that division have one more.
3. **Job-seekers and units.** The crew's S job-seekers are placed one to a household, starting with
   the households that have the fewest people at work. If S is more than h, a second round starts in
   the same order. A household holds one unit for each job-seeker placed in it.

**Bands.** This step runs once, over the whole county, after steps 1 to 3 have placed every budget
group.

- *Sizes.* O is the households of the groups with business ownership, and N the households of the
  other groups. The top 1% is O ÷ 10, and the next 9% is the rest of O. The next 40% is 4 × N ÷ 9,
  and the bottom 50% is the rest of N. Each division is by largest remainder, and an exact tie goes
  to the lower band.
- *The top 1%* is taken from the owners' positions with nobody in the labor force, in proportion to
  their households. If those positions hold fewer households than the top 1% needs, the build
  refuses the campaign.
- *The next 40%* is taken from the other groups' positions in the labor force. The positions are
  ranked by the number of people at work, most first, so positions that are only looking for work
  come last. Job-seekers and units are not read. Whole ranks are taken while they fit. The first
  rank that does not fit gives its share in proportion to households. If the positions in the labor
  force hold fewer households than the next 40% needs, the build refuses the campaign.
- Where two remainders are exactly equal at a band's line, those households stay in the lower band.
  So a band can open a few households short of its size.

**Each period,** for each crew.

4. **Departures.** The engine reports how many of the crew's people at work and how many of its
   job-seekers left the labor force. Each person at work who left is taken from the households with
   the most at work. Each job-seeker who left is taken from the households with the most looking for
   work. The household keeps its units.
5. **Hires or layoffs.** The engine reports one or the other, never both. A hire is taken from the
   households that have someone looking for work, fewest at work first: (k, s, u) becomes (k + 1, s
   − 1, u). A layoff is taken from the households with the most at work: (k, s, u) becomes (k − 1, s
   + 1, u).
6. **Households.** If the engine lowers the group's households, households leave its positions that
   have nobody in the labor force, in proportion. A unit that leaves with a household is held by
   nobody. If the group has too few such households, the roster cannot follow it, and the session
   refuses with a typed error. Following it would need a rule for merging households. No run of this
   slice reaches that case.

**Equals.** A step that takes n households "first" from one kind takes them from the positions of
that kind in proportion to their households, by largest remainder. Inside a position it takes
reached and unreached households in proportion, by largest remainder. A household that moves stays
reached or unreached.

**The place.** A household's place is k × W × C ÷ (E × T). W is the wages accrued to its crew in the
period just closed. E is the crew's people at work in that period, which the roster holds. T is the
budget group's taxed wages in the period. C is the wage tax the county collected from the group. The
place is nothing when k, W, E or T is nothing. Places are compared as exact fractions. No place is
rounded.

**Unpaid units.** When the county does not pay some of a position's units, they are taken a
household at a time: a household with u units loses all of them before the next household loses one.
The households that lose are reached and unreached households in proportion to their numbers, by
largest remainder.

**Ties.** A split by largest remainder leaves a tie only when two remainders are exactly equal.
Between positions of one crew the tie goes by a fixed order of their answers: fewer units first,
then fewer people looking for work, then fewer at work, then the lower band. Between reached and
unreached households it goes to the unreached. Between crews in step 1, and between positions at one
place on the county's list, there is no such order: the household is bound to no crew, and the unit
is paid to nobody (section 7.4). No tie is settled by an identifier.

The engine's own exact split settles ties by the caller's order. The roster needs the tie rules
above, so it cannot call that split as it is.

### D.4 What this appendix does not claim

- That the placements are true of Wayne. They are Designed, and section 9 runs each at its other
  bound.
- An adjunction between adding up and splitting.
- A new kind of mathematical object. Counts, sums, ratios of sums and exact splits are in use in the
  engine today. **[Call]**
- A draw. Lawvere's 1962 handout treats a mapping that gives each point a probability measure, with
  ordinary mappings as the special case that has no chance in it. Its scan has no text layer, so the
  repository's reading notes carry its words
  (`docs/gameplay/research/32-lawvere-1962-probabilistic-mappings.md`). Every split in this slice is
  of the special kind.
- That Lawvere's texts are a source for any number, or for any rule of the county or the household.
  They are the source of the method of counting.

## Appendix E: Amendment AM

**What the fourth draft asked.** "The author reads the floor as a declared comparison of two amounts
the engine holds, with no coefficient and no curve, for which a record is enough. If the Director
holds that ruling 5 binds as written, the floor needs a constitutional amendment under Article VIII
before it is built."

**What the Director answered.** As typed: "ruling 5 also survives as writetna bout laws, modify the
constitution". With the spelling corrected: "ruling 5 also survives as written about laws, modify
the constitution" (19 November 2026).

**How the author reads it.** Ruling 5 is live law as written, so the Constitution must carry it. The
floor therefore needs the amendment the fourth draft named, and the Director said to make it.
Amendment AM does both.

**What was changed,** on this branch. It is not pushed.

Article III has a new second paragraph:

```text
No functional form — sigmoid included — may be imposed on mechanics;
sigmoid-shaped behavior must emerge from P(revolution)/P(acquiescence)
dynamics and the algebraic Lawverian operations. Amendment AM records this
rule and states how it is applied.
```

The Constitution has a new section at its end:

```text
### Amendment AM — No Imposed Functional Form

On 2026-07-29 the Director ruled, as ruling (5) of
`ai/decisions/ADR172_amendment_ae_refoundation_ratified.yaml`:

> NO functional form — sigmoid included — may be IMPOSED on mechanics;
> sigmoid-shaped behavior must EMERGE from P(revolution)/P(acquiescence)
> dynamics and the algebraic Lawverian operations.

The v4 text did not carry that sentence. Agent guidance carried a narrower
form that named only a sigmoid and a fixed response curve. On 2026-11-19 the
Director ruled that ruling (5) survives as written and directed that the
Constitution be modified. Amendment AM adds the ruling to Article III in its
own words, and states how the rule is applied.

In this rule a functional form is a response shape that a designer
stipulates: a curve, or a constant placed to set where or how steeply a
response turns. Accounting identities, conservation, and the declared
Designed quantities of Article IV, such as a price, a tax rate, a recipe, or
the cost of an act, are not response shapes. Article IV stays in force. It
already forbids historical data to silently set a mechanic's response shape.

A response shape is lawful only as a result. ADR173 ruling (1) set the
construct for the survival curve: the response of a class is the measure of
its members whose wealth clears subsistence, and the steepness of the curve
is the class's actual wealth dispersion. ADR175 ruling (1) extended that
treatment to every confirmed imposed-form site. Amendment AM states the
construct in general. A rule decides for one member of a population by
comparing material amounts that the causal circuit holds for that member:
what it has, what it needs, what it stands to gain or lose, and what an act
costs it. The response of the population is the measure of its members that
the rule admits. The shape of that response then follows from how those
amounts are spread across the members.

Three forms stay prohibited. A rule must not compare a member's amount with a
constant placed to set where the response turns. A rule must not apply a
comparison, a curve, or a shape parameter to the mean or another bare summary
of a population. A rule must not carry a parameter whose only role is the
steepness, midpoint, or curvature of a response. ADR176 ruling (17) already
requires coarse carriers to hold dispersion, and it stays in force.

Amendment AM settles one point that ruling (5) left open. A comparison of
material amounts for one member is one of the algebraic operations from which
a response can emerge. It is not an imposed form. This amendment adds no
mathematical primitive.

The compact in `AGENTS.md` and the restatement in `NORTH_STAR.md` take the
ruling's wording. Article IV and Amendment AJ are unchanged. Historical
records keep their bytes. The dispositions of ADR173 and the posture of
ADR175 stand. The derivations that ADR175 requires for each family remain
owed, and each is presented to the Director before it lands. No campaign
format, state, or stored data changes.

A design that claims an emergent response must show the rule for one member,
the amounts that the rule compares, and the population that the rule is
measured over. It must include a mutation test in which removing the
dispersion changes the response. Review must refuse a rule that takes a
prohibited form. The Constitution header and footer, the live pins of its
version, and the governance tests state v4.4.0. This amendment records the
law. It is not a report that existing rules were audited again.

AM advances the Constitution from v4.2.0 to v4.4.0. Amendment AL and v4.3.0
name a change that ADR289 repealed, and they are not reused. The transition
record is `ai/decisions/ADR300_amendment_am_no_imposed_functional_form.yaml`.
```

- The version goes from 4.2.0 to 4.4.0, and "Last amended" to 2026-11-19.
- The files that name the Constitution's version now say 4.4.0: `AGENTS.md`, `NORTH_STAR.md`,
  `README.md`, `docs/agents/governance.md`, three pages under `docs/concepts/`, four files under
  `ai/`, and one governance test. Historical records, plans and the interval contract keep the
  versions they cite.
- The compact line in `AGENTS.md` now reads: "No functional form — sigmoid included — may be imposed
  on mechanics. A response shape must emerge." The sentence in `NORTH_STAR.md` now reads: "No game
  rule can impose a functional form, sigmoid included."
- Two documents state the rule in older words and are left as they were before this branch:
  `ai/bsl-architecture-standard.md` and `docs/concepts/survival-calculus.rst`.
- The transition record is `ai/decisions/ADR300_amendment_am_no_imposed_functional_form.yaml`. Its
  status is proposed, because the Director has not read this wording. The branch must not merge to
  dev or main while it is proposed.
- Checked on 19 November, after the redraft: the decision catalog and the governance mass check
  pass, and so do the governance unit tests.

**Whose words are whose.**

| Part of the amendment | Whose |
|---|---|
| The sentence added to Article III, and the ruling quoted in the section | The Director's, from ADR172 ruling 5. Article III sets the emphasis capitals in sentence case |
| "In this rule a functional form is a response shape that a designer stipulates", and the rest of that paragraph | The author's reading of the ruling's scope. Its list of what is not a response shape leans on Article IV |
| "A response shape is lawful only as a result." | The author's restatement of the ruling's second half |
| The construct for the survival curve, and its extension to every confirmed site | The Director's, from ADR173 ruling 1 and ADR175 ruling 1 |
| "A rule decides for one member of a population by comparing material amounts that the causal circuit holds for that member", and the two sentences after it | The author's general statement of that construct. The audit of 29 July described the lawful form in the same way (`reports/p27-proscription-audit-2026-07-29.md`, section 2.1) |
| The three prohibited forms | The author's wording. The first and third follow that audit's section 4.2. The second is the fault ADR173 confirmed |
| "A comparison of material amounts for one member is one of the algebraic operations from which a response can emerge. It is not an imposed form." | The author's. It is the sentence that makes a household's own comparison lawful, and with it the floor. It is new constitutional text |
| The duties of proof and of review | The author's |
| The letter AM and the version 4.4.0 | The author's call. ADR287 used AL and 4.3.0, and ADR289 repealed them |

**Three ways to rule on it.**

1. *The sentence only.* Keep the new second paragraph of Article III, and strike the section's
   statement of how the rule is applied. Ruling 5 is then law as written. The floor has no stated
   ground, and by the fourth draft's own reading it could not be built.
2. *As drafted.* The sentence, the scope, the general construct, the three prohibitions and the
   point settled. A household rule that compares the household's own amounts is lawful. A rule that
   compares with a placed constant, or that reads a mean, is not.
3. *A named exception.* The sentence, and one line that excepts this slice's floor. It is the
   narrowest, and it says nothing about the next household rule.

The author recommends the second. The Director's acceptance of ADR300 chooses it.

**What the amendment does not do.** It does not audit the rest of the game against ruling 5. ADR173
left three audit findings open, and they stay open. The derivations that ADR175 requires for each
family are still owed.
