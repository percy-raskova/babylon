# Restoring forces, round nine: a bound on hiring, a loan with a term, and the restart

Measured on 22 November 2026 on the small test economy, from head `008a819b5` of the branch. Round nine put on the
bench, together, the three things round eight found missing: a workplace asks for hands only for the hours it can work
(step B); a loan to keep running stands for a term, as ruled on 22 November (ADR318; step L); and a stopped workplace's
price rests while a buyer restarts it (rules A17 and A19 of the approved design,
`docs/superpowers/specs/2026-11-21-how-the-economy-adjusts-design.md`; step R).

All of it is throwaway code behind switches, on the scratch branches `spike/r9-B` (`6061df478`), `spike/r9-L`
(`2d4b499a6`) and `spike/r9-R` (`a4199aacc`), and together on `spike/r9-all` (`0dffbd321`). Nothing of this round is in
the engine.

**How the round is judged.** While it ran, the Director ruled on what counts as failure (ADR319): "not every shock is a
failure. capitalism is inherently unstable. what we want is to ensure the gameplay is interesting and well paced". The
test is *slumps end, scars stay* (section 2). A swing, a cycle, a workplace that shuts and is mended, a change of owner
and a household that ends poorer are what a player sees. They are reported and not scored. Step B had been built and
measured under my first, stricter reading; the steps after it, the final sets and the check of the rows carried the
Director's test. My first reading stands beside it in section 11.

**How to read the figures.** A set is 25 runs of the test economy: 8 calm and 17 pushed. Every run is 400 periods, about
31 years (a period is four weeks, 13 to the year). Each final set was run at the small figures and at the national
figures, and two figures side by side are always in that order. *Stops* is the number of pushed runs, of 17, in which a
workplace made or sold nothing in each of the last ten periods. *Hours* are the hours people attended and were paid for,
of 480 a period: the mean of the last 20 periods over the 17 pushed runs. The credits are: none; the bank as the design
worded it before 22 November (round 7b); and the bank of the ruling with a term of 3, 6, 13 or 26 periods.

Every figure was counted from the rows by my own scripts, one run in memory at a time, except where a sentence names the
measuring agent, a reader or an earlier record. The round wrote 85 whole sets of 400 periods: 35 in the three steps and
50 final sets, 25 pairs of a form and a credit at both sets of figures.

## 1. The answer

- **No form passes the Director's test.** Not one of the 50 final sets passes it, at the small figures or at the
  national, under any credit. A calm world stays still, and money and people are exact in every period of every run, in
  all 85 sets of the round.
- **The test economy is far better than in round eight.** With the three steps on and the whole third part, a workplace
  stops for good in 3 and 0 of the 17 pushed runs with no credit. Round eight had 15 and 14 with the same rules and
  nobody looking for work at the opening, and the economy without any rule of rounds eight or nine has 9 and 7. Hours
  attended are 386 and 429, against 316 and 396 without any rule.
- **The bound on hiring matters most.** Take it away and the same form has 15 stops at both sets of figures (section 9).
- **The restart works with the owners' own money.** With no credit there are 28 restarts at 20 workplaces at the small
  figures ($14,461 put in) and 10 at 8 at the national ($11,614). All but 1 of those 28 workplaces are working at the
  end. Under credit most restarts change nothing, because the workplace lacked inputs or a working supplier, not money
  (section 8).
- **The loan with a term carries a slump better than the bank as first worded only when the term is short.** With the
  three steps on, a term of 3 has 2 and 1 stops and the bank as first worded 5 and 0. Terms of 13 and 26 end worse at
  the small figures (section 7).
- **What a player would see** (section 5; reported, not scored). With the three steps on and no credit, 12 of the 17
  pushed runs slump at the small figures and 10 at the national. The first low comes after a median of 1.2 and 1.9
  years, at 85% and 92% of the hours, and every one of those slumps is back at nineteen twentieths of the hours within
  five years of it. Then many slide again: the hours at the end are 87% and 94% of the opening on the median, and 49%
  and 61% in the worst run. Workplaces shut and come back: 5 and 8 reopened after ten or more periods shut, and all of
  them are working at the end. The economy still swings at the end in 9 and 10 runs, by a median of 127 and 154 hours of
  480.
- **Who ends poorer.** Where the loss lasts, the owners end with 87% and 97% of their needs met on the median, the
  workers with 52% and 45%, and the households that live on benefits with 38% and 44%. The owners hold 1.7 and 2.3 times
  the money they hold in the calm run.
- **One run fails in every set, old and new** (section 10): the harvest that fails in one place for ten periods and
  returns, at the national figures. Every workplace is back at its opening output from period 11. Three years later a
  rise in the cost of living begins that nothing ends. Nothing can make more than it made at the opening, a shop's price
  only ever steps up, and the money ends with the owners.
- **Two faults of mine** (section 12): my first stop test scored swings and scars as failures, which the design itself
  asks for; and I told the Director the figures of step B from rows of a form its builder then replaced.
- **What follows** (section 13): round ten, the last. It puts on the bench what the rows of this round show is missing:
  a goods price that comes down, capacity added where buyers who could pay went unserved, idle money taken out of a
  workplace, and a restart that asks whether the workplace can work.

## 2. How the round is judged

The Director chose the stop test on 22 November 2026 (ADR319), in these words: "PASSES WHEN (small and national figures,
400 periods) 1. A calm world stays still. Money and people are exact. 2. The harvest fails for ten periods, then
returns: work and output are back within five years. 3. A loss that lasts (poor harvest, scarce power): no place is left
without a product for good, and no price climbs without end." Reported and not scored: swings and cycles, how wide and
how long; what shut, what reopened, what changed hands; who ends up poorer; the pace, years down and years back.

My readings of the three lines were fixed before the rows of this round were read, and they stand in ADR319 for the
Director to check:

- **R1.** In the quiet run of each world the hours attended are the same in every period and no posted price, standing
  rate or going rate moves. In every period of all 25 runs the money is exact and each copy has the people it opened
  with.
- **R2.** In each of the four runs where the harvest returns: there is a period from 11 to 76 in which the hours
  attended, and every workplace's output (a shop's sales), are at nineteen twentieths of the quiet run's or more; and
  the same two hold on the mean of the last 20 periods. Whether every need is met is not part of it. The second half,
  still back at the end, is my reading.
- **R3.** In each of the eight runs where the loss lasts: no workplace made or sold nothing in each of the last ten
  periods; and no posted price ended each of the last five spans of 20 periods higher than the span before.
- The other five pushed runs are held to the two lines of R3 and reported beside it. A form passes under a credit when
  its small set and its national set both pass.

## 3. What was on the bench

| Step | Switch | What it does |
| --- | --- | --- |
| B | `SPIKE_BOUND` | At the close a workplace asks for no more hours than its capacity can run, its inputs can feed and its money can pay for, wages first. Every reader of the request takes the capped figure. Its plan and its orders are not cut |
| L | `SPIKE_B_TERM=<n>` | A loan to keep running is no longer bounded by last sales. It stands for n periods; interest is paid at each close; no profit is paid out while principal is owed; what is unpaid at the due date is overdue, and after three closes overdue the bank takes the business |
| R | `SPIKE_REST`, `SPIKE_RESTART` | A workplace that employs nobody and offers nothing does not move its price. One that has stopped for three periods is restarted by an owner with spare money when buyers who could pay went unserved and one batch would sell above its cost; a business the bank holds is bought from it |

The forms. *The whole third part* is round eight's: people who look for work belong to their place, pay by steps,
letting people go at once with the service price rule, a workplace with no money stops, and plans down the chain. Nobody
looks for work at the opening unless a row says so. *The light form* has only seekers of the place, the stop rule, the
bound, the resting price and the restart. Two faults of the code that the builders reported and did not mend: a
restarted workplace has one idle period, because its bound was reckoned before the money came in; and under the bank
most restarts put in $0 (section 8).

## 4. The Director's test, form by form

For each set: the returning-harvest runs that fail R2, of 4; the lasting-loss runs that fail R3, of 8; the other pushed
runs that fail the lines of R3, of 5 (reported); stops; hours attended.

| Form | Credit | Small: R2, R3, other | stops | hours | National: R2, R3, other | stops | hours |
| --- | --- | --- | --- | --- | --- | --- | --- |
| All three steps, the whole third part | no credit | 3, 2, 0 | 3 | 386 | 1, 1, 0 | 0 | 429 |
| All three steps, the whole third part | the bank as first worded | 3, 5, 1 | 5 | 343 | 1, 0, 1 | 0 | 443 |
| All three steps, the whole third part | a term of 3 | 3, 1, 0 | 2 | 424 | 1, 0, 1 | 1 | 434 |
| All three steps, the whole third part | a term of 6 | 3, 2, 1 | 5 | 356 | 1, 1, 1 | 2 | 402 |
| All three steps, the whole third part | a term of 13 | 3, 3, 1 | 6 | 322 | 1, 1, 1 | 1 | 427 |
| All three steps, the whole third part | a term of 26 | 3, 2, 1 | 3 | 369 | 1, 0, 1 | 0 | 455 |
| The same, two people looking at the opening | no credit | 2, 0, 0 | 0 | 409 | 1, 2, 0 | 1 | 423 |
| The same, two people looking at the opening | a term of 13 | 2, 3, 0 | 4 | 344 | 1, 1, 0 | 1 | 429 |
| Without the restart | no credit | 3, 5, 1 | 9 | 344 | 1, 5, 0 | 4 | 411 |
| Without the restart | a term of 13 | 3, 4, 1 | 7 | 299 | 1, 2, 1 | 2 | 403 |
| Without the bound | no credit | 4, 8, 3 | 15 | 306 | 4, 8, 3 | 15 | 181 |
| Without the bound | a term of 13 | 4, 8, 2 | 14 | 169 | 4, 4, 0 | 5 | 336 |
| Without pay by steps | no credit | 3, 4, 0 | 4 | 365 | 1, 2, 1 | 2 | 377 |
| Without pay by steps | a term of 13 | 3, 4, 1 | 6 | 315 | 1, 2, 1 | 4 | 346 |
| Without the cut of pay | no credit | 3, 4, 1 | 6 | 325 | 1, 0, 0 | 0 | 419 |
| Without the cut of pay | a term of 13 | 3, 3, 1 | 5 | 335 | 1, 0, 0 | 1 | 422 |
| Without plans down the chain | a term of 13 | 3, 4, 1 | 3 | 369 | 1, 0, 1 | 0 | 428 |
| Seekers of the place and the bound, nothing else | no credit | 0, 5, 2 | 7 | 346 | 1, 6, 1 | 8 | 372 |
| Seekers of the place and the bound, nothing else | the bank as first worded | 1, 3, 1 | 4 | 395 | 1, 2, 0 | 2 | 414 |
| No rule of rounds eight or nine | a term of 3 | 1, 4, 1 | 5 | 359 | 1, 4, 1 | 6 | 372 |
| No rule of rounds eight or nine | a term of 6 | 1, 4, 1 | 5 | 377 | 1, 3, 1 | 5 | 344 |
| No rule of rounds eight or nine | a term of 13 | 1, 4, 0 | 4 | 402 | 1, 3, 0 | 3 | 419 |
| No rule of rounds eight or nine | a term of 26 | 1, 5, 2 | 6 | 401 | 1, 3, 1 | 4 | 399 |
| The light form | no credit | 0, 2, 0 | 1 | 396 | 1, 1, 0 | 0 | 402 |
| The light form | a term of 13 | 1, 0, 0 | 0 | 438 | 1, 0, 1 | 0 | 418 |
| No rule of rounds eight or nine | no credit | 1, 6, 3 | 9 | 316 | 1, 6, 1 | 7 | 396 |

The forms that come closest, with what fails (`clinic_a` is the clinic of place A, as the rows name it; hours at the end
count as back from 456 of 480):

- **The light form, a term of 13.** Small figures: R2 in plain-P8a: output short at the end at clinic_a. National
  figures: R2 in fund-P8a: hours at the end 338 of 480; output short at the end at all eight workplaces.
- **The light form, no credit.** Small figures: R3 in fund-P6: a price climbs without end (shop_a, shop_b); R3 in
  fund-P6a: nothing made or sold for good at farm_a, clinic_a, farm_b, clinic_b, shop_b. National figures: R2 in
  fund-P8a: hours at the end 284 of 480; output short at the end at all eight workplaces; R3 in fund-P6a: a price climbs
  without end (shop_b).
- **All three steps, the whole third part, no credit.** Small figures: R2 in plain-P8: hours at the end 243 of 480;
  output short at the end at utility_a, farm_a, shop_a, utility_b, farm_b, shop_b; R2 in plain-P8a: never back by period
  76; hours at the end 393 of 480; output short at the end at utility_a, farm_a, clinic_a, shop_a; R2 in fund-P8a: never
  back by period 76; hours at the end 342 of 480; output short at the end at all eight workplaces; R3 in plain-P2a:
  nothing made or sold for good at farm_a, clinic_a, shop_a; R3 in plain-P6: nothing made or sold for good at farm_a,
  shop_a, farm_b, shop_b. National figures: R2 in fund-P8a: hours at the end 408 of 480; output short at the end at all
  eight workplaces; R3 in fund-P6a: a price climbs without end (shop_b).
- **All three steps, the whole third part, a term of 3.** Small figures: R2 in plain-P8: never back by period 76; hours
  at the end 344 of 480; output short at the end at all eight workplaces; R2 in plain-P8a: never back by period 76;
  hours at the end 306 of 480; output short at the end at utility_a, farm_a, clinic_a, shop_a, clinic_b; R2 in fund-P8a:
  never back by period 76; hours at the end 379 of 480; output short at the end at all eight workplaces; R3 in
  plain-P6a: nothing made or sold for good at clinic_a. National figures: R2 in fund-P8a: hours at the end 414 of 480;
  output short at the end at utility_a, farm_a, clinic_a, shop_a, utility_b, clinic_b, shop_b.

The light form under a term of 13 fails in one run at each set of figures. In it no workplace ever stops for three
periods, so nothing is restarted and no price rests: what it measures is the bound with seekers of the place under that
loan.

## 5. What a player would see

Reported, not scored. A slump is a run whose hours fall under nineteen twentieths of the quiet run's. The first low is
the first period under that line that is not undercut in the year after it. The design's pace is "A slump takes one to
two years to its low and up to five back".

**Small figures**, over the 17 pushed runs.

| Form | Slumps | First low, years (median) | Hours at it | Back within five years | Hours at the end: median, least | Still swinging: runs, median width | Shut at the end: workplaces (runs) | Reopened (working at the end) | Taken by the bank | Bought |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| No rule of rounds eight or nine, no credit | 9 | 2.9 | 78% | 2 | 71%, 6% | 14, 28 | 37 (9) | 0 (0) | 0 | 0 |
| The light form, no credit | 8 | 1.7 | 77% | 6 | 98%, 15% | 13, 74 | 5 (1) | 5 (5) | 0 | 0 |
| The light form, a term of 13 | 7 | 1.2 | 80% | 6 | 99%, 67% | 12, 26 | 0 (0) | 0 (0) | 0 | 0 |
| All three steps, no credit | 12 | 1.2 | 85% | 12 | 87%, 49% | 9, 127 | 11 (3) | 5 (5) | 0 | 0 |
| All three steps, the bank as first worded | 12 | 1.2 | 86% | 12 | 80%, 0% | 12, 310 | 25 (5) | 2 (0) | 8 | 3 |
| All three steps, a term of 3 | 13 | 1.1 | 87% | 13 | 90%, 64% | 12, 196 | 3 (2) | 0 (0) | 0 | 0 |
| All three steps, a term of 6 | 13 | 1.1 | 87% | 13 | 91%, 0% | 11, 72 | 26 (5) | 4 (2) | 8 | 4 |
| All three steps, a term of 13 | 13 | 1.1 | 88% | 13 | 91%, 0% | 9, 178 | 40 (6) | 5 (2) | 11 | 2 |
| All three steps, a term of 26 | 13 | 1.1 | 88% | 13 | 86%, 0% | 10, 192 | 20 (3) | 4 (0) | 8 | 2 |

**National figures**, over the 17 pushed runs.

| Form | Slumps | First low, years (median) | Hours at it | Back within five years | Hours at the end: median, least | Still swinging: runs, median width | Shut at the end: workplaces (runs) | Reopened (working at the end) | Taken by the bank | Bought |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| No rule of rounds eight or nine, no credit | 10 | 2.5 | 89% | 8 | 92%, 18% | 9, 62 | 20 (7) | 0 (0) | 0 | 0 |
| The light form, no credit | 10 | 1.3 | 85% | 9 | 81%, 53% | 10, 180 | 0 (0) | 7 (7) | 0 | 0 |
| The light form, a term of 13 | 10 | 1.3 | 85% | 10 | 87%, 70% | 10, 128 | 0 (0) | 0 (0) | 0 | 0 |
| All three steps, no credit | 10 | 1.9 | 92% | 10 | 94%, 61% | 10, 154 | 0 (0) | 8 (8) | 0 | 0 |
| All three steps, the bank as first worded | 10 | 1.9 | 90% | 10 | 96%, 73% | 10, 170 | 0 (0) | 0 (0) | 0 | 0 |
| All three steps, a term of 3 | 10 | 1.9 | 92% | 10 | 96%, 40% | 10, 170 | 4 (1) | 0 (0) | 1 | 0 |
| All three steps, a term of 6 | 10 | 1.9 | 92% | 10 | 95%, 0% | 10, 190 | 16 (2) | 0 (0) | 4 | 1 |
| All three steps, a term of 13 | 10 | 1.9 | 92% | 10 | 95%, 0% | 10, 124 | 8 (1) | 0 (0) | 3 | 1 |
| All three steps, a term of 26 | 10 | 1.9 | 92% | 10 | 96%, 87% | 10, 135 | 0 (0) | 0 (0) | 0 | 0 |

**Who ends poorer**, in the eight runs where the loss lasts: the share of needs met on the mean of the last 20 periods
(median of the runs), and the owners' money at the end as a multiple of what they hold in the calm run.

| Form | Small: owners, workers, on benefits | owners' money | National: owners, workers, on benefits | owners' money |
| --- | --- | --- | --- | --- |
| No rule of rounds eight or nine, no credit | 27%, 51%, 43% | 0.3 | 67%, 54%, 50% | 3.7 |
| The light form, no credit | 82%, 58%, 23% | 1.4 | 98%, 41%, 36% | 2.7 |
| The light form, a term of 13 | 91%, 66%, 35% | 1.9 | 100%, 39%, 39% | 3.3 |
| All three steps, no credit | 87%, 52%, 38% | 1.7 | 97%, 45%, 44% | 2.3 |
| All three steps, the bank as first worded | 79%, 42%, 40% | 1.1 | 99%, 42%, 40% | 3.3 |
| All three steps, a term of 3 | 100%, 58%, 39% | 2.0 | 100%, 42%, 41% | 3.2 |
| All three steps, a term of 6 | 97%, 47%, 39% | 2.0 | 100%, 40%, 42% | 2.6 |
| All three steps, a term of 13 | 96%, 44%, 38% | 1.8 | 100%, 46%, 40% | 3.2 |
| All three steps, a term of 26 | 87%, 37%, 18% | 1.9 | 100%, 44%, 43% | 3.9 |

- **The pace of the first slump is near the design's.** With the three steps on, the first low of a lasting loss comes
  after about a year (1.1 and 1.1 years on the median with no credit), and all of them are back within five. Without any
  rule the first low comes later (2.9 and 2.5 years over all pushed runs) and 7 and 1 slumps are never back.
- **It does not stay back.** The hours of a lasting loss stand at 74% and 82% of the opening at the end on the median
  with no credit. The first slump ends; later ones follow, and the last 100 periods still swing in most runs.
- **A harvest that returns sets off a late crisis at the national figures.** Three of those four runs never slump. The
  fourth, where the harvest failed in one place only, slumps 14.4 years in with the three steps on and 5.6 and 5.8 years
  in without any rule and in the light form (section 10).
- **Nothing that shut came back before this round.** Without any rule no workplace reopens after ten periods shut, at
  either set of figures. With the restart they do, and under no credit every one of them is working at the end.
- **Workers and the households on benefits end poorer; owners end richer.** Where the loss lasts, with the rules of this
  round on, between 37% and 66% of the workers' needs and between 18% and 44% of the needs of those on benefits are met
  at the end, while in every one of those forms the owners hold more money than in the calm run. Nothing on the bench
  raises pay when prices rise, and the fund that pays the benefits drains (section 10).

## 6. Step B: a workplace asks for hands only for the hours it can work

**The limit, as the builder found it in round eight's rows** (the measuring agent's trace, with file and line in its
result): the farm's limit is its power. It pays wages first and buys power after, out of the money left, so a farm that
took on hands had no money for the power to use them. The shop's limit is the food it holds: it sells only from stock,
and its call for hands counted what buyers asked for, not what it held. Capacity never bound.

**Two forms.** The first form read "what the supplier plans to make" as the supplier's plan as it stood. The builder
found in its own rows that a utility then planned 130 to 160 units against a capacity of 120, and that farms took on
hands for power that did not exist. The committed form caps a supplier's plan at its capacity and at its own bound. Both
forms were measured in full; the first form's rows are kept.

Stops, with hours attended in brackets, at the small figures: no credit, then the bank as first worded.

| Set | Round eight, without the bound | The first form | The committed form |
| --- | --- | --- | --- |
| The bound alone | 9 (316) / 9 (286) | 8 (340) / 6 (345) | 8 (318) / 5 (382) |
| Seekers of the place and the bound | 13 (214) / 13 (220) | 8 (345) / 5 (372) | 7 (346) / 4 (395) |
| The same, two looking at the opening | 14 (200) / 14 (207) | 6 (366) / 7 (327) | 8 (317) / 3 (393) |
| The whole third part and the bound | 15 (254) / 15 (266) | 8 (361) / 13 (217) | 9 (344) / 6 (357) |
| The same, two looking at the opening | 15 (244) / 15 (222) | 7 (359) / 11 (259) | 7 (351) / 2 (403) |

- **With seekers of the place, the committed form has fewer stops than round eight in every pair**, most of all under
  the bank.
- **Fewer farms take on hands they cannot use, and fewer of those are lost.** In periods 1 to 10 of the final sets with
  no credit, 12 of the 34 farms take on more people than they opened with at the small figures and 5 of them have
  stopped at the end; without the bound 24 do and 24 have stopped. No shop takes on hands with the bound; without it 23
  do. Hours paid and not worked in those ten periods: 2,240 against 11,600 at the small figures, 2,579 against 6,121 at
  the national.
- **Which limit binds** (closes at which the request was cut, all pushed runs of the final set with no credit, small
  figures): the farm by its inputs in 6,414 closes and by its money in 445; the shop by what it holds in 3,421 and by
  its money in 547; the clinic by its inputs in 988 and by its money in 405; the utility by its money in 2,990. Capacity
  never binds.
- **The calm runs are untouched by the bound**: every column equals the reference in every set, as the builder proved
  and the check of the code confirmed.

## 7. Step L: a loan to keep running stands for a term

Stops and hours attended, small / national. *The term alone* has no rule of rounds eight or nine beside it.

| Credit | The term alone: stops | hours | R2, R3 | All three steps: stops | hours | R2, R3 |
| --- | --- | --- | --- | --- | --- | --- |
| The bank as first worded | 9 / 6 | 286 / 382 | 1, 6 / 1, 4 | 5 / 0 | 343 / 443 | 3, 5 / 1, 0 |
| A term of 3 | 5 / 6 | 359 / 372 | 1, 4 / 1, 4 | 2 / 1 | 424 / 434 | 3, 1 / 1, 0 |
| A term of 6 | 5 / 5 | 377 / 344 | 1, 4 / 1, 3 | 5 / 2 | 356 / 402 | 3, 2 / 1, 1 |
| A term of 13 | 4 / 3 | 402 / 419 | 1, 4 / 1, 3 | 6 / 1 | 322 / 427 | 3, 3 / 1, 1 |
| A term of 26 | 6 / 4 | 401 / 399 | 1, 5 / 1, 3 | 3 / 0 | 369 / 455 | 3, 2 / 1, 0 |

The bank's books with all three steps on, over the 17 pushed runs, small / national.

| Credit | Lent | Repaid early | Repaid at or after the due date | Written off | Workplaces taken | Owed at the end | Periods with the bank's money at or under $0 | Debts still growing at the end |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| The bank as first worded | $1,415,945 / $312,584 | from sales | from sales | $2,327 / $0 | 8 / 0 | $0 / $0 | 0 / 0 | 0 / 0 |
| A term of 3 | $734,685 / $178,317 | $498,514 / $52,591 | $234,875 / $124,846 | $0 / $74 | 0 / 1 | $1,295 / $807 | 0 / 0 | 7 / 1 |
| A term of 6 | $764,455 / $186,260 | $614,528 / $66,825 | $145,356 / $115,401 | $1,936 / $2,170 | 8 / 4 | $2,636 / $1,864 | 0 / 0 | 8 / 7 |
| A term of 13 | $680,960 / $162,592 | $569,296 / $78,481 | $102,570 / $74,420 | $4,256 / $3,360 | 11 / 3 | $4,837 / $6,339 | 0 / 81 | 9 / 10 |
| A term of 26 | $707,178 / $161,826 | $622,485 / $89,801 | $73,549 / $56,798 | $7,522 / $0 | 8 / 0 | $3,629 / $15,227 | 137 / 0 | 8 / 8 |

- **A term of 3 measured best with the three steps on**: the fewest stops at the small figures, nothing written off and
  nothing taken there, and the bank never without money. It is not clean: 7 debts still grow at the end at the small
  figures and 1 at the national, and it has 1 stop at the national figures where the bank as first worded has none.
- **Longer terms end worse at the small figures.** Under terms of 13 and 26 the bank takes 11 and 8 workplaces and is
  without money in 137 periods under a term of 26. As the measuring agent traced it, whole copies of the economy die 15
  to 25 years in, after the bank has taken a utility.
- **Every term moves a calm run.** The calm run P3 borrows in the reference. As the measuring agent counted, under a
  term the bank takes workplaces in it: 2 under a term of 3, 4 under 13 and 4 under 26. With the restart on I count 4
  restarts with money in the calm runs under a term of 13 and 4 under 26 at the small figures, and none under a term of
  3; the agent counted 258 and 130 closes marked as a restart there, most of them with $0. The quiet run of each world
  stays still under every term.
- **The loan of round 7b without its bound by last sales, repaid from sales and with no term, has 0 stops and 438
  hours** at the small figures with no other rule on. It was run in step L for comparison, at the small figures only. It
  is not the Director's ruling, which gives the loan a due date.
- **What the builder chose where my text left a choice**: at the due date a workplace repays with all its money, which
  empties it; the oldest loan is repaid first and strictly; interest is paid from the money held; the bank does not sell
  what it takes unless a buyer comes (step R).

## 8. Step R: a stopped workplace's price rests, and a buyer restarts it

- **The price of a stopped workplace now rests.** Stopped workplaces whose posted price still moved in the last ten
  periods, over the pushed runs at the small figures with no credit: 20 before the step, 1 with the resting price, none
  with the restart as well. Without any rule there are 23 and 12 (small, national): a stopped shop's price climbed a
  step every period.

Restarts that put money in, over the 17 pushed runs, small / national.

| Credit | Restarts | Workplaces | Of them stopped at the end | Money put in | Paid to the bank for a business |
| --- | --- | --- | --- | --- | --- |
| No credit | 28 / 10 | 20 / 8 | 1 / 0 | $14,461 / $11,614 | $0 / $0 |
| The bank as first worded | 27 / 0 | 8 / 0 | 3 / 0 | $13,183 / $0 | $383 / $0 |
| A term of 3 | 2 / 5 | 2 / 5 | 1 / 1 | $791 / $3,369 | $0 / $0 |
| A term of 6 | 12 / 6 | 8 / 6 | 1 / 3 | $3,574 / $4,243 | $947 / $3 |
| A term of 13 | 17 / 3 | 7 / 3 | 5 / 2 | $3,569 / $1,374 | $19 / $416 |
| A term of 26 | 7 / 0 | 7 / 0 | 4 / 0 | $2,906 / $0 | $858 / $0 |

- **With no credit the restart mends what shut.** Stops fall from 9 and 4 without it to 3 and 0 with it.
- **Under credit it mostly does not.** The measuring agent counted the closes marked as a restart: under the bank as
  first worded 108 of 135 put in $0, and under a term of 13, 514 of 531. As the agent traced them, those workplaces held
  money and were stopped for another reason: no inputs, or a supplier that had itself stopped. Such a workplace was
  marked as restarted again every third period. A utility whose price had come to rest under its cost never passed the
  test.
- **Without the bound the restart wastes the owners' money**: 1,127 restarts with $802,071 put in at the small figures,
  and still 15 stops.
- **What the reader of the code found unspelled**: restart money can be pulled into repaying the bank; a business bought
  with debt left on it would be taken again; and the bound is reckoned before the restart money arrives, which gives
  every restart one idle period.

## 9. The pieces taken away

Each against all three steps with the whole third part, under no credit and under a term of 13: stops and hours
attended, small / national.

| Form | No credit: stops | hours | A term of 13: stops | hours |
| --- | --- | --- | --- | --- |
| All three steps, the whole third part | 3 / 0 | 386 / 429 | 6 / 1 | 322 / 427 |
| Without the bound | 15 / 15 | 306 / 181 | 14 / 5 | 169 / 336 |
| Without the restart | 9 / 4 | 344 / 411 | 7 / 2 | 299 / 403 |
| Without pay by steps | 4 / 2 | 365 / 377 | 6 / 4 | 315 / 346 |
| Without the cut of pay | 6 / 0 | 325 / 419 | 5 / 1 | 335 / 422 |
| Without plans down the chain | not run | not run | 3 / 0 | 369 / 428 |
| The same, two people looking at the opening | 0 / 1 | 409 / 423 | 4 / 1 | 344 / 429 |

- **The bound**: without it the form is in ruin under both credits.
- **The restart**: without it more workplaces are lost under both credits.
- **Pay by steps** helps a little with no credit: without it there are 4 / 2 stops against 3 / 0.
- **The cut of pay** is mixed: without it there are 6 / 0 stops with no credit and 5 / 1 under a term of 13, against 3 /
  0 and 6 / 1.
- **Plans down the chain** harm under a term of 13 at the small figures: without them 3 / 0 stops against 6 / 1.
- **Two people looking for work at the opening** help at the small figures with no credit: 0 / 1 stops against 3 / 0.
- **The light form does as well as the whole third part or better** (section 4): with no credit it has 1 / 0 stops and
  396 / 402 hours. The rules of work and pay add failures of R2 at the small figures: with them three of the four
  harvests that return do not have their output back.

## 10. The run that fails in every set

The harvest fails in one of the two places for ten periods and then returns, at the national figures (run fund-P8a). It
fails R2 in all 25 final forms and in round eight's reference. I traced it period by period in three sets: with all
three steps and no credit, without any rule of rounds eight or nine, and in the light form. The three run the same
course until period 40. Figures are for the place where the harvest failed.

1. **Periods 1 to 10.** The farm makes 36 units a period against 40. It sells its stock down from 40 to 2, and its money
   rises from $1,760 to about $2,590: money from stock sold is not paid out. The clinic and the utility run under their
   capacity and cut their prices, the clinic from $30 to $25 or $26 and the utility from $12 to $10.50. The fund that
   pays the benefits pays them in full while its taxes fall, and goes from $1,920 to about $1,370.
2. **Periods 11 to 40.** The harvest is back and every workplace makes what it made at the opening. All 480 hours are
   worked. Care is cheap, so households ask for 41 to 44 units of it where the clinic can make 40. Its price steps up,
   past its opening $30, to $39 by periods 42 to 44. The clinic's profit goes to the owners of the place, whose money
   rises from under $400 to between $850 and $950 by period 40; in the calm run they hold $640. The farm keeps its
   $2,580 and its stock stays at 3.
3. **Periods 40 to 55.** Needs cost more. The wage tax is collected after needs, so the taxes fall from $1,280 to under
   $1,000, and the fund pays as little as $655 to $669 of the $960 it owes. The owners now want 8 more units of food
   than the 40 the shop stocks. The shop does not stock more, so the market for food is short and clears at $64 to $112
   a unit against a posted $40 to $51. Households go without care: the clinic sells 24 to 30 units in period 45 and 17
   or 18 in period 50.
4. **To the end.** With all three steps the shop's posted price ends at $118.75 against $38, it sells 30 units of 40,
   and 33 of the 80 needs of food in the two places go unmet. The wage bill is $3,050 against $4,800 and 426 of 480
   hours are worked. Without any rule the hours end at 432; in the light form, where a workplace asks only for the hours
   it can work, at 231.

What the rows show is missing, as I read them:

- **Nothing can make more than it made at the opening.** The clinic's and the utility's capacity is their opening
  output, and the shop orders up to a stock that buyers' wants never raise. So more money wanting goods only moves
  prices. The design has the answer, and it has never been on the bench: a workplace is added to where buyers who could
  pay went unserved (A18, A19).
- **A shop's price is a ratchet.** Every step up of that shop's posted price came in a period when buyers who could pay
  were turned away: 85 of 85 steps with all three steps, 77 of 77 without any rule, 131 of 131 in the light form. It did
  not step down once in 400 periods, in any of the three. Yet in 168, 268 and 204 of the last 300 periods it had goods
  unsold with nobody turned away, and needs of food went unmet in its place in every one of the 300. The design's rule
  for it (A1: a price steps down when goods it offered went unsold and nobody was turned away) was built in round four
  and has not been on the bench since round six.
- **Money that leaves circulation into a workplace is slow to come back.** A workplace pays out earnings only. The farm
  held about $820 more than it opened with from period 10 to period 40 in all three sets.
- **Nothing raises pay when prices rise, and the fund never refills.** It opened with $1,920 and never holds $1,400
  again after period 10, in any of the three sets. The design has organized workers answer a squeeze (A16). That rule
  has never been on the bench, and round ten does not put it there.

This is a rise in the cost of living three years after a local crop failure, in which owners grow rich and workers go
without. Whether it is a fault to mend or play to keep is the Director's to say. By my reading of R2 it fails, because
work and output are not back at the end.

## 11. Calm runs, exactness, and my first reading beside

- **Still when nothing pushes.** In all 85 sets the quiet run of each world has the same hours in every period and no
  price or rate of pay moves.
- **Exact.** In every period of every run of all 85 sets the money is exact and each place has the people it opened
  with.
- **My first reading** had four tests: the two above; back after a shock that ends, read as every period from 76 on with
  the hours and every account's every need at nineteen twentieths; and at rest after a lasting loss, read as the hours
  of the last 20 periods within 5 hours of one another and no rate of pay moving. Every one of the 85 sets fails the
  last two, round eight's references among them: the last fails in 2 to 8 of the 8 lasting-loss runs of a final set. It
  scored a swing as a failure. The design asks for swings and for marks that stay, and the Director replaced it.

## 12. What the readers corrected, and two faults of mine

Two readers checked the round. One recounted the rows with its own script; the other read the code of the three steps
against their builders' claims.

- **The recount of the rows** gave 23 findings: 15 of the measuring agent's claims hold, 6 were refuted and 2 are
  unclear. Every verdict by set, every count of stops, every figure of hours and every figure of the bank's books
  matched. Refuted: that one harvest run passed my first reading at the small figures (it fails on output); that all
  four harvests slump at the small figures (three do); that the calm restarts under a term of 13 were at one farm (they
  are spread over six workplaces); the counts of debts still growing (they are 7, 8, 9 and 8 at the small figures and 1,
  7, 10 and 8 at the national for terms of 3, 6, 13 and 26, as counted here); that the closest form shows the restart at
  work (under a term of 13 it never restarts anything); and one list of failing runs. Unclear: reading a seller's price
  from the price it quoted in the period, not from the price posted for the next, changes R3 in three national sets; and
  how many restarted workplaces stop again depends on how a stop is read.
- **The reader of the code** gave 23 findings: 21 hold and 2 are unclear. All three prototypes, and the runner of the
  final sets, do what their builders say. What it found unspelled is in section 8.
- **Fault one: my first stop test.** I took four of the design's eleven tests and read two of them more strictly than
  the design words them. That scored swings and scars as failures. The Director corrected it while the round ran. The
  lesson, now in my notes: when I turn a design's tests into a pass bar I take all of them and keep their wording.
- **Fault two: figures told too early.** While step B was still being built I counted the rows of its first form and
  told the Director that the whole third part under the bank still had 13 stops. The committed form has 6. I corrected
  it with a table as soon as the step returned. The lesson: I do not count a step's rows before the step returns.

## 13. What follows

Round ten is the last round: the effort ends with it, whatever it shows. It keeps two credits, none and a term of 3, and
two forms, the light form and the whole third part, and it puts four things on the bench.

1. **The restart, mended.** Its test asks whether the workplace can work: the inputs of one batch can be had. A resting
   price is raised to its cost. The bound sees the money put in.
2. **A goods price comes down** when goods went unsold and nobody who could pay was turned away: round four's rule,
   measured again at 400 periods with the bound and the restart beside it.
3. **Capacity is added** where buyers who could pay went unserved for three periods, with the owner's own money, ranked
   with the restart by what each would earn (A18, A19). Founding a new workplace is not built.
4. **An owner takes idle money out of a workplace.** This is my reading of the ruling on who carries a loss (ADR318),
   turned round; the Director has not ruled on it.

Whatever round ten shows, three things wait for the Director: whether my reading of "still back at the end" stands;
whether the rise in the cost of living of section 10 is a fault or play; and the rules the design names that the bench
never reached, organized workers (A16) and founding (A18) first among them.

