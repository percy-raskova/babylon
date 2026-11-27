# What brings the small economy back: round six

Measured 21 November 2026, on the branch at `a2b9a482b`. Round five's reading against the approved design (ADR314)
found that the design's first part had never been measured as the design asks: with a second seller of each product
on the bench, and buyers who take from the cheapest. Round six does that, and it isolates the gap that round five
found between the spare-money rule as built and its prototype. Three steps, each a throwaway prototype behind a
switch:

- **X**: one switch for each difference between the spare-money rule as built (F2, rule A6) and its prototype (f),
  with both ends proven.
- **T**: the bench with two of everything. Two utilities, two farms, two clinics, two shops, two of each household
  and two owners, with one fund in the taxed world. With buyers bound to their own copy, the doubled bench is the
  old bench twice, cell for cell.
- **A4**: a buyer takes from the cheapest seller first, at that seller's own price, and goes on to the next when it
  has no more. Sellers at one price share the buyers.

The other letters are the earlier rounds': **d2** owners' top-ups, **a** lent workers, **D** plans down the chain,
**R** a service cuts its price only when it performed under its plan, **e-kept** a goods price steps down on unsold
stock, **S** a goods price steps up on low stock, **W** larger steps for raw goods and power, **L** a merchant does
not buy above what it can resell for. "The engine's own prices" means none of R, e-kept, S and W. "The first part"
is F2, d2, a, D, R, e-kept, S and W.

The pushes are the old ones, on both copies alike: P2 a poor harvest for good, P4 higher pay at the clinic, P5 a cut
in the fund's taxes, P6 scarcer power, P8 a poor harvest for ten periods that then returns. Each but P5 also has a
form that strikes one copy only (P2a, P4a, P6a, P8a). Runs are 200 periods, and 400 for three sets, at the small
world's own figures and at the national figures. Hours are out of 480 and are the mean of the last 20 periods. A
double dagger (‡) marks a run in which a workplace stopped for good.

This file is written by the lead from the round's tables (`logs/r6-all-tables.json`), its rows (`out/r6-*`), its
structured result (`round6-wf_229abe59.output.json`) and its two independent checks: one reader recomputed the
claims from the rows, one read the prototypes. Where the measuring agents and a check disagreed, the lead recomputed
from the rows, and every count in sections 4 to 7 is the lead's own recomputation.

## 1. The answer

- **The gap between the rule as built and its prototype is one line.** The built rule counts a merchant's restocking
  in what it pays out in a period. The prototype did not. Turning that one line gives the prototype's rows in every
  realized column of every run, at both sets of figures and on the doubled bench.
- **Sellers compete, as the design says.** The cheaper seller wins the buyers at once. A service that loses them
  cuts its price.
- **Competition as built makes the bench worse.** A gap of one price step moves a whole market. Services leapfrog
  each other period after period. A goods seller that loses its buyers mostly does not cut: it pays idle hours, runs
  out of cash and stops, and nothing reopens it. A push on one copy often shuts the copy that was not struck.
- **The price rules of the first part, as built, still do not help.** With the engine's own prices the bench is
  better than with the first part in 15 of 17 runs at the small figures and 13 of 17 at the national when buyers are
  free, and in 13 and 8 of 17 when they are bound.
- **Nothing returns after a shock that ends.** Not one of the 136 runs of the returning harvest (four in each of 34
  sets) is back by period 76 and stays. In the best set the hours are back and the money is not: it sits in the
  farms and the shops, and the owners stay short (section 7).
- **The best set is still the plainest, with buyers bound:** the engine's own prices, the spare-money rule, lent
  workers, plans down the chain, and owners' top-ups. It closes no workplace at either set of figures.

## 2. The rule as built against its prototype

Round four's core, small figures, 200 periods, on the old bench (hours out of 240).

| Run | Rule as built | Prototype | Rule as built, restocking left out |
| --- | --- | --- | --- |
| Taxes and fund, poor harvest for good | 16.20 | 153.95 | 153.95 |
| Taxes and fund, harvest returns | 223.10 | 240 | 240 |
| No taxes, scarcer power | 121.35 | 207.75 | 207.75 |
| No taxes, harvest returns | 200.25 | 240 | 240 |
| No taxes, poor harvest for good | 199.20 | 185.30 | 185.30 |
| Taxes and fund, scarcer power | 219.90 | 212.50 | 212.50 |

- Five differences were found in the code, each given a switch. Both ends were proven: every switch off gives the
  built rule's rows byte for byte, and every switch on gives the prototype's rows in every column the two share.
- Only one switch moves anything that happens: restocking. The built rule counts a merchant's restocking orders in
  one period of what it pays out, so the shop has less spare money and adds no handling hours when households ask
  for more than they paid for. The prototype let the shop spend that money on hours.
- The other four change plans only, or nothing. The prototype's plan past a plant's full size shows in the plan
  columns and is gone before anyone works.
- At the national figures the two forms end within 11 hours of each other on the old bench. On the doubled bench at
  the national figures, with the engine's own prices, they are equal in every realized column of all 25 runs.
- Which form is better is not settled. The prototype's is better in more runs at the small figures and not at the
  national. That the shop's restocking money eats its spare money is read from the code; the rows show only where
  and when the two forms part.
- The approved design counts restocking in what a workplace pays out. The rule as built follows the design.

## 3. The doubled bench

- With buyers bound, the doubled bench equals the old bench twice: each copy's columns equal the old world's cell
  for cell, and every whole-world column is twice the old one, for every old run, with no rule on and with round
  five's sets on, at both sets of figures.
- With every switch off, the rows equal the base's byte for byte. Quiet runs are exactly still and total money is
  constant in every run of all 34 sets.
- With buyers bound, a push on one copy reaches the other only through the fund and the treasury.

## 4. Buyers who take from the cheapest

Hours out of 480, 200 periods, small figures.

| World | Push | Engine's prices, bound | Engine's prices, cheapest | First part, bound | First part, cheapest |
| --- | --- | --- | --- | --- | --- |
| No taxes | P2: poor harvest, for good | 480 | 480 | 398.4 | 81.3 ‡ |
| No taxes | P2a: poor harvest, for good, one copy | 480 | 125.3 ‡ | 442 | 114.1 ‡ |
| No taxes | P4: higher pay at the clinic | 480 | 480 | 480 | 480 |
| No taxes | P4a: higher pay at the clinic, one copy | 480 | 247.7 ‡ | 480 | 208.9 ‡ |
| No taxes | P6: scarcer power | 455 | 385.65 ‡ | 242.7 ‡ | 366 |
| No taxes | P6a: scarcer power, one copy | 465.7 | 214.8 ‡ | 388.95 ‡ | 3 ‡ |
| No taxes | P8: poor harvest for ten periods | 475.1 | 475.1 | 400.5 | 182.25 ‡ |
| No taxes | P8a: poor harvest for ten periods, one copy | 477.7 | 291.15 ‡ | 452.85 | 36.55 ‡ |
| Taxes and fund | P2: poor harvest, for good | 480 | 480 | 32.4 ‡ | 21.2 ‡ |
| Taxes and fund | P2a: poor harvest, for good, one copy | 454.15 | 297.25 | 456.6 | 9 ‡ |
| Taxes and fund | P4: higher pay at the clinic | 480 | 480 | 480 | 480 |
| Taxes and fund | P4a: higher pay at the clinic, one copy | 477.5 | 434.7 | 422.9 | 6 ‡ |
| Taxes and fund | P5: a cut in the fund's taxes | 480 | 480 | 454.8 | 348.15 |
| Taxes and fund | P6: scarcer power | 469.2 | 262.6 ‡ | 439.8 | 22.05 ‡ |
| Taxes and fund | P6a: scarcer power, one copy | 452.6 | 359.2 | 445.95 | 0 ‡ |
| Taxes and fund | P8: poor harvest for ten periods | 480 | 480 | 446.2 | 148.75 ‡ |
| Taxes and fund | P8a: poor harvest for ten periods, one copy | 480 | 416.75 | 391.5 | 114.6 ‡ |

National figures.

| World | Push | Engine's prices, bound | Engine's prices, cheapest | First part, bound | First part, cheapest |
| --- | --- | --- | --- | --- | --- |
| No taxes | P2: poor harvest, for good | 474 | 470.5 | 467.5 | 467.5 |
| No taxes | P2a: poor harvest, for good, one copy | 475.9 | 471.95 | 473.25 | 279.35 |
| No taxes | P4: higher pay at the clinic | 480 | 480 | 480 | 480 |
| No taxes | P4a: higher pay at the clinic, one copy | 480 | 480 | 480 | 480 |
| No taxes | P6: scarcer power | 462.4 | 450.55 | 462 | 462 |
| No taxes | P6a: scarcer power, one copy | 472.5 | 432.65 | 472.35 | 322.9 ‡ |
| No taxes | P8: poor harvest for ten periods | 480 | 480 | 449.3 | 384.45 ‡ |
| No taxes | P8a: poor harvest for ten periods, one copy | 480 | 480 | 464.3 | 217 ‡ |
| Taxes and fund | P2: poor harvest, for good | 396.9 | 423.35 | 428.1 | 231.5 |
| Taxes and fund | P2a: poor harvest, for good, one copy | 459.9 | 382.65 | 464.95 | 231.85 ‡ |
| Taxes and fund | P4: higher pay at the clinic | 480 | 480 | 425 | 435.9 |
| Taxes and fund | P4a: higher pay at the clinic, one copy | 454.05 | 414.95 | 457.8 | 358.85 ‡ |
| Taxes and fund | P5: a cut in the fund's taxes | 480 | 480 | 413.4 | 452.8 |
| Taxes and fund | P6: scarcer power | 436.1 | 424.35 | 424.8 | 424.8 |
| Taxes and fund | P6a: scarcer power, one copy | 461.4 | 413.3 | 465.4 | 318.95 ‡ |
| Taxes and fund | P8: poor harvest for ten periods | 480 | 480 | 397.1 | 411.85 |
| Taxes and fund | P8a: poor harvest for ten periods, one copy | 450 | 480 | 458 | 176.7 ‡ |

- **The cheaper seller wins at once.** When a pair's prices differ, the cheaper takes 53 to 98 of every 100 units
  the pair sells, and it sells out in most of those periods.
- **A service cuts, and the pair leapfrogs.** In the no-tax world with higher pay at one clinic, the two clinics'
  prices differ in 39 of the first 40 periods, the dearer cuts in 39, and they swap places 38 times. At the national
  figures they still swap 19 times in the last 20 periods.
- **A goods seller mostly does not cut.** With one farm's harvest poor for good and the engine's own prices, the
  dearer farm cut in 1 of 13 periods in which the prices differed. At period 20 the struck farm posts $25 against
  the other's $24, and the shops take 74 units from the other and none from it. Its cash falls from $1,324 at period
  16 to $292 at period 20. Its owner tops it up to $1,252, and by period 36 it holds $5.56. Its whole copy then
  shuts, and the other copy serves both at 125 hours of 480.
- **The untouched copy often shuts.** Under the first part with one farm's harvest poor, it is copy B, which was not
  struck, that closes workplace by workplace (clinic from period 27, shop from 60, utility from 81, farm from 99).
- **Against buyers bound.** Under the pushes on one copy, the engine's own prices with free buyers are worse than
  bound in 8 of 8 runs at the small figures and 5 of 8 at the national. Under the first part, bound is better in 14
  of 17 runs at the small figures and 9 of 17 at the national.
- **Runs in which a workplace stops for good,** of 17, bound against free. Engine's own prices: 0 against 6 at the
  small figures, 0 against 0 at the national. First part: 3 against 13, and 0 against 7.
- With the engine's own prices at the national figures nothing stops for good with free buyers, at 200 periods or at
  400. Every other set with free buyers closes workplaces.
- Under pushes on both copies alike, the rows with free buyers part from the bound rows only through rounding. Those
  runs show how sensitive the bench is, not what the rule does.

## 5. The price rules, with a second seller

Each rule taken away from the first part with free buyers. Runs of 17 that are better without it, then worse (a
difference above one hour counts).

| Rule taken away | Small figures | National figures |
| --- | --- | --- |
| S, the step up on low stock | 13 better, 2 worse | 12 better, 3 worse |
| W, larger steps for raw goods and power | 13 better, 2 worse | 9 better, 6 worse |
| e-kept, the step down on unsold stock | 12 better, 3 worse | 4 better, 10 worse |
| R, the rule for services | 13 better, 1 worse | 8 better, 7 worse |
| D, plans down the chain | 6 better, 9 worse | 8 better, 7 worse |

- These are differences inside a set that is mostly in ruin. No single removal reaches the bench with the engine's
  own prices.
- With buyers bound, where the bench is not in ruin, the verdict is the same: the engine's own prices are better
  than the first part in 13 of 17 runs at the small figures (worse in 1) and in 8 at the national (worse in 5).
- No price rule as built helps at both sets of figures. The step down on unsold stock harms at the small figures and
  helps at the national. Plans down the chain help at the small figures and are mixed at the national.
- **The shop's price still walks up at the national figures** where the loss lasts: from $38 to about $105 by period
  200, and to $107 by period 400. The step up on low stock is not what does it: it happens with the engine's own
  prices, with buyers bound or free, and in round five's own rows. What walks it is not isolated.
- The merchant's limit (L), with free buyers: better in 14 of 17 runs at the small figures and 9 at the national
  (worse in 5). At the national figures it ruins one run, one farm's poor harvest with no taxes: 279 hours to 8.

## 6. A shock that ends, and a loss that lasts

The returning harvest, 200 periods: periods from 76 to 200 (125 of them) in which the bench works under 456 of its
480 hours, which is nineteen twentieths.

| Set | No taxes, both copies | No taxes, one copy | Taxes and fund, both copies | Taxes and fund, one copy |
| --- | --- | --- | --- | --- |
| Engine's prices, buyers bound, small | 0 of 125 | 0 of 125 | 0 of 125 | 0 of 125 |
| Engine's prices, cheapest seller, small | 0 of 125 | 125 of 125 | 0 of 125 | 36 of 125 |
| First part, buyers bound, small | 114 of 125 | 105 of 125 | 48 of 125 | 104 of 125 |
| First part, cheapest seller, small | 125 of 125 | 125 of 125 | 118 of 125 | 125 of 125 |
| Engine's prices, buyers bound, national | 0 of 125 | 0 of 125 | 0 of 125 | 55 of 125 |
| Engine's prices, cheapest seller, national | 0 of 125 | 0 of 125 | 0 of 125 | 0 of 125 |
| First part, buyers bound, national | 61 of 125 | 18 of 125 | 116 of 125 | 40 of 125 |
| First part, cheapest seller, national | 77 of 125 | 115 of 125 | 94 of 125 | 124 of 125 |

Hours out of 480 at 400 periods, free buyers.

| World | Push | Engine's prices, small | First part, small | Engine's prices, national | First part, national |
| --- | --- | --- | --- | --- | --- |
| No taxes | P2: poor harvest, for good | 480 | 2 ‡ | 470.95 | 416.2 |
| No taxes | P2a: poor harvest, for good, one copy | 122.5 ‡ | 3 ‡ | 439 | 7 ‡ |
| No taxes | P4: higher pay at the clinic | 480 | 480 | 480 | 480 |
| No taxes | P4a: higher pay at the clinic, one copy | 260.8 ‡ | 38.85 ‡ | 480 | 480 |
| No taxes | P6: scarcer power | 180.8 ‡ | 295.3 | 417.95 | 461.8 |
| No taxes | P6a: scarcer power, one copy | 212.75 ‡ | 3 ‡ | 438.1 | 59.1 ‡ |
| No taxes | P8: poor harvest for ten periods | 471.5 | 3 ‡ | 480 | 190.6 ‡ |
| No taxes | P8a: poor harvest for ten periods, one copy | 139.75 ‡ | 2 ‡ | 480 | 2.8 ‡ |
| Taxes and fund | P2: poor harvest, for good | 480 | 8 ‡ | 443.45 | 25.05 ‡ |
| Taxes and fund | P2a: poor harvest, for good, one copy | 388.9 | 9 ‡ | 405.65 | 27.7 ‡ |
| Taxes and fund | P4: higher pay at the clinic | 480 | 480 | 480 | 292.5 |
| Taxes and fund | P4a: higher pay at the clinic, one copy | 329.25 ‡ | 6 ‡ | 428.75 | 367.85 ‡ |
| Taxes and fund | P5: a cut in the fund's taxes | 480 | 40.05 ‡ | 472.05 | 224.1 ‡ |
| Taxes and fund | P6: scarcer power | 292.85 ‡ | 0 ‡ | 430.75 | 446.3 |
| Taxes and fund | P6a: scarcer power, one copy | 298.5 ‡ | 0 ‡ | 409.45 | 8 ‡ |
| Taxes and fund | P8: poor harvest for ten periods | 480 | 56.75 ‡ | 480 | 135.3 ‡ |
| Taxes and fund | P8a: poor harvest for ten periods, one copy | 304.35 | 106.55 ‡ | 480 | 69.4 ‡ |

- **No run of the returning harvest is back by period 76 and stays.** The test reads hours and the needs met of each
  account. It fails in all 136 runs.
- With the engine's own prices and buyers bound, the hours are back in seven of the eight runs. What fails is needs,
  and in those seven it is the owners who go without. Over the last 20 periods of the taxed world at the small
  figures each owner is short of 6 units of power and 8 of care in a period, and holds $393 where the quiet run has
  $640. With no taxes each is short of about 9 of power, 10 of care and 1 of food.
- The eighth run is the taxed world at the national figures with one copy struck. There the struck copy's workers
  and its supported households go without food, power and care, while that copy's owner ends with about $3,560 where
  the quiet run has $640.
- Under the first part the hours themselves fail, with buyers bound or free.
- **Prices do not settle in most pushed runs, bound or free.** Runs of 17 in which a posted price still moves in the
  last 20 periods, small then national figures. Engine's own prices, buyers bound: 13 and 15; free: 14 and 16. First
  part, bound: 16 and 15; free: 13 and 16.
- Runs of 17 in which a workplace stops for good at 400 periods with free buyers, small then national figures:
  engine's own prices 8 and 0; first part 14 and 11; first part without the step up on low stock 11 and 8.

## 7. Where the money is when the harvest is back

The best set (engine's own prices, buyers bound), the returning harvest on both copies. Money in each account in the
quiet run, where nothing moves, and at period 200 after the shock. Accounts that end within $25 of the quiet run are
left out. Total money is the same in both.

| Account | Small, quiet | Small, at period 200 | National, quiet | National, at period 200 |
| --- | --- | --- | --- | --- |
| No taxes: each utility | 1200 | 1100 | 2400 | 2229 |
| No taxes: each farm | 880 | 1150 | 1760 | 2216 |
| No taxes: each shop | 1400 | 1560 | 2800 | 2800 |
| No taxes: each owner | 800 | 428 | 800 | 479 |
| Taxes and fund: each utility | 1200 | 1140 | 2400 | 2351 |
| Taxes and fund: each farm | 880 | 1662 | 1760 | 2539 |
| Taxes and fund: each owner | 640 | 393 | 640 | 364 |
| Taxes and fund: the public account | 320 | 288 | 320 | 287 |
| Taxes and fund: the fund | 1920 | 864 | 1920 | 860 |

Why the money stays there was traced after the round by a separate reader, from these rows and from the code that
made them. The lead checked its figures against the rows and its citations against the branch. What follows is the
taxed world at the small figures, which is exactly at rest from period 76: every workplace, both owners, the public
account and the fund hold the same money in each of the last 20 periods.

- **1. The shock moved the owners' money and the farm's stock into the farm's cash.** Each owner put $322 into its
  farm in periods 2 and 3 as top-ups. The farm sold its stock down from 40 units to 14 and has rebuilt it only to
  21. Its cash went from $880 to $1,662.
- **2. The farm cannot spend it.** It plans 60 hours and has four people and 40. Plans down the chain carry the
  farm's plan to the utility, which then plans for 134 units of power with 120 hours of its own, asks for all 120,
  sells 114 and pays 6 hours idle. Hands are lent only out of hours that nobody asked for, so those 6 hours never
  reach the farm, which is short of 20 in every period. A workforce can only shrink.
- **3. The farm never pays it out.** The engine pays an owner out of earnings. Money an owner put in is capital, and
  stock sold at what it cost is not profit, so neither is ever earnings. Nothing in the code returns capital.
- **4. The prices of power and care fell during the shock and did not come back.** Power went from $12 to $10 by
  period 5, care from $30 to $24 by period 10. The engine's own rule cuts a service's price while it runs under its
  capacity and earns more than its direct cost. Power stopped at $10, where the utility's sales equal the wages of
  the hours it uses. Care stopped at $24, where the clinic again sells all it can perform. Nothing raises either
  price, because nobody who still has money is turned away. The reason for each price move is not in the rows: this
  link is read from the code.
- **5. So each owner's income fell from $640 to $384 a period.** Wages did not change. The workers' pay now buys
  more: in each copy they buy as comforts the 8 units of care that the owner goes without.
- **6. The utility loses $60 a period** on those six idle hours. Its owner tops it up by $60 in every period, for
  good. A top-up is capital: nothing is owed and nothing comes back.
- **7. The owner's money runs out before care.** It pays the top-up, then food, then power, and has $8.66 left when
  care costs $24. It goes short of 6 units of power and 8 of care in every period.
- **8. The fund takes in less.** Taxes fall from $1,280 to $1,152 a period, and the fund pays $864 of the $960 it
  owes.

Nothing is still draining: the world has settled at these levels. At the national figures the same accounts hold
within a few dollars of fixed levels. With no taxes they move around fixed levels without settling. Two things are
not in the rows and were worked out from prices, quantities and the tax rates: what each workplace pays its owner,
and the value at which stock stands in the books.

What the approved design says to each link:

| Link | The design |
| --- | --- |
| 2, the farm cannot hire | People laid off look for work at every workplace of their place (A14), and a workplace that cannot fill its hours raises its pay and draws hands (A15). The third part. Its stand-in on the bench, lent hands, fails here |
| 3, capital is never paid out | Silent. The design has no top-ups: credit takes their place |
| 4, service prices fall and stay down | A1 takes away the price cut for running under full capacity, and A3 has a workplace lay off before it cuts its price. The bench's stand-in for A1 here is R; run alone on the best set after the round, it changes nothing (section 12) |
| 6, a loss covered for good | A loan to keep running is given only when what it pays for will sell above its cost, and it is repaid from sales before any profit is paid (A9). A business that is refused lays off (A3). The second and third parts |
| 5, 7 and 8 | Silent on the order in which a household spends and on the level of the fund |

## 8. What the checks corrected

The reader of the rows recomputed most tables exactly. This file follows the checks where they differ from the
measuring agents:

- **Plans down the chain** were reported as helping. They help at the small figures. At the national figures taking
  them away improves more runs than it harms.
- **Goods sellers do not swap places every period.** That pattern is the services'. In one followed run the farms'
  prices differ in 187 of 200 periods and the cheaper one changes 55 times.
- **The walk of the shop's price to $96 or more** was claimed for every run of every set with free buyers. It holds
  with the engine's own prices. Elsewhere the last price runs from $30 to $264, and a stopped farm's price ends very
  high or at $1.
- **Top-ups go on to the end under higher pay too,** under the price rules at the national figures. "None" was
  reported.
- **Who goes without.** In the taxed world at the national figures, with the engine's prices and one farm's harvest
  returning, the supported households of both copies go short of care in every period from 76, not only the owners.
- Several counts and ranges in step X were a few units off. The direction of every comparison stands.
- What the prototype's helpful behavior is could be read from the rows only as a time and a place. The reason rests
  on the code.

One line of the check did not hold either. It said that every pushed run with free buyers still has prices moving in
its last 20 periods. The rows show 3 or 4 runs of 17 at the small figures in which no posted price moves, some of
them because everything has stopped (section 6).

## 9. What the prototypes decided that the rules do not

The reader of the prototypes found all three honest: each behind its switch, no site, product or period named, no
floating point, money constant in all 1,799 runs. It also found choices that the rule as stated does not make, and
on which the results rest:

- Buyers split evenly between sellers at one price, and leftover units go to copy A's sellers first.
- Every buyer moves on a gap of one price step, at once, with nothing to slow it. Both copies stand in one place, so
  the design's freight between places does not come into it.
- What a cheaper seller had to turn away counts as that seller's own demand, for its price and its plan.
- The spare-money rule, the top-ups and plans down the chain still read the old binding of buyer to seller.
- In the taxed world with two copies, the treasury pays in proportion. That choice decides how a push on one copy
  reaches the other.

## 10. What this round did not do

- Most sets ran 200 periods. The design asks for 400.
- Nothing slows a buyer's move: no freight, no second place, no new seller, no work abroad.
- The design's order, "lays off before it cuts its price", is not on the bench. The engine does the reverse (section
  12). With free buyers and the best set, 12 workplaces stop for good at the small figures. Every one paid idle
  hours on the way, from 133 to 3,582 hours, and all 11 that ever cut a price cut it before they let anyone go.
- Nothing reopens or founds a workplace, and credit is not on the bench.
- A workplace under one period of what it pays out was not counted.
- The back test read hours and needs. It did not read output, or bands of households.

## 11. Read against the approved design

The design's tests (its section 8), for the first part:

| Test | Result |
| --- | --- |
| Still when quiet | Passes in every set: exactly still, money constant |
| Sellers compete | The cheaper seller wins buyers. A service that loses them cuts. A goods seller mostly does not |
| Back after a shock that ends | Fails in all 136 runs. In the best set the hours are back and the owners' needs are not |
| Settled after a lasting loss | Best set: no workplace closes, and one price walks slowly. First part: ruin in several runs |
| Exact money | Passes: constant in all 1,799 runs |

The design's rules of the first part, as measured on the bench in rounds four to six:

| Rule | As measured |
| --- | --- |
| A1, a price steps up when stock is under the buffer (S) | Harms at both sets of figures, with one seller or two |
| A1, a price steps down on unsold stock (e-kept) | Harms at the small figures, helps at the national |
| A1, a service's price (R) | Not needed at the small figures, mixed at the national |
| A2, raw goods and power swing (W) | Harms |
| A3, lay off before cutting the price | Not on the bench. The engine does the reverse: the price is cut first, people are let go later (section 12) |
| A4, a buyer takes from the cheapest seller | Does what it says. With nothing to slow buyers and no way back for a loser, it shuts workplaces |
| A5, plans through the chain (D) | In every best set. Helps at the small figures, mixed at the national |
| A6, spare money (F2) | In every best set. Equal to its prototype but for one line, where it follows the design |

## 12. After the round: the rule for service prices, alone on the best set

Section 7 names the fall of the two service prices as one link, and the first part has a rule for service prices (R:
a service cuts its price only when it performed under its plan). No round had run it alone on the best set. This run
did, with buyers bound, at both sets of figures, for 200 and for 400 periods. A control first reproduced round six's
best set byte for byte, in all 25 files.

- **The rule changes nothing in the returning harvest.** Where the harvest fails on both copies, the runs with the
  rule are the same in every realized column as the runs without it, at both sets of figures and both lengths. Power
  still falls from $12 to about $10 and care from $30 to $24, and they stay there.
- **Why.** In the shock both services do perform under their plans, so the rule's condition holds and the price is
  cut as before. In the taxed world at the small figures the utility plans 120 hours in every period and uses 112 to
  115 of them from period 3. The clinic plans 40 and uses 31 to 33 in periods 2 to 4.
- **Over all pushed runs the rule is no better.** Runs of 17 that are better with it, then worse, at 200 periods: 0
  and 5 at the small figures, 2 and 8 at the national. At 400 periods: 2 and 4, and 3 and 4. No workplace stops for
  good with it or without it.
- Of the 25 runs of a set, 19 at the small figures and 14 at the national are the same in every realized column with
  the rule and without it. The quiet runs are among them.
- The counts were made twice, from each set's summary and from the raw rows, and agree.

What it means. In the taxed run at the small figures nobody is let go, and the utility goes on planning for all 120
of its hours. Its plan does not fall because the farm's order is carried into it, and the farm orders for more than
its people can work (link 2 of section 7). And its owner's top-up pays for whatever it plans, where the design's
loan would be refused (A9).

The engine does let people go, but late. A workplace keeps the people for the larger of its last two requests, so it
sheds hands only when its plan has been lower for two periods running. A service's price steps down in every period
it runs under its capacity and still covers its direct cost. So the price goes first. The best set's 17 pushed runs
hold 68 cases of a service. At the small figures 20 of them both cut their price and let people go, and 19 of those
cut the price first; 32 more cut their price and never let anyone go. At the national figures the counts are 28, 28
and 29. The design asks for the reverse order (A3: a workplace lays off before it cuts its price). So this link
waits for the later parts, like the others.

## 13. What follows

- The design says of itself that no piece works alone (its section 7). These rows agree. What the best set lacks to
  come back after a shock is traced in section 7, and its links belong to later parts: a business that is lent money
  only when that pays, and repays it (the second part); a workplace that lets people go before it cuts its price,
  and one that can draw hands (the third); a way back for one that has shut (the fourth).
- The new price steps of the first part, as built, made the bench worse than the engine's own price rules in three
  rounds, together and one by one, and the rule for service prices alone changes nothing where it was hoped to help
  (section 12). They are not built now. They are measured again once a workplace lets people go before it cuts its
  price.
- A buyer who takes from the cheapest seller is not built now. It cannot be judged before a loser can shrink and
  come back.
- What stands is built: plans through the chain (A5), beside the spare-money rule that is built (A6). Its plan is
  `docs/superpowers/plans/2026-11-21-adjust-1b-plans-through-the-chain.md`. Its fifth task proves the built rule
  against the prototype's rows before the rule is called done.
- That plan keeps one thing from the prototype that link 2 of section 7 shows at work: a buyer orders for the plan
  it made, even past what its people can work. It is kept so that the built rule is the measured one, and a capped
  form is to be measured with a switch.
- Next on the bench, round seven: the second part. A bank as the design states it, in place of the owners' top-ups:
  it lends only when what the loan pays for sells above its cost, and is repaid before any profit. With it a cap on
  orders, so that a buyer orders only for what its people can work.
- After it the third part: people who look for work in their place, a workplace that raises its pay to draw hands,
  and the design's order of letting people go before a price is cut.
