# A small world in balance, and what the engine does to it

Probe of the material circuit's own rules, 2026-11-20, branch `codex/households-and-homes`. The
world and every run are the test binary `rust/crates/babylon-material-circuit/tests/small_world.rs`
(`small_world/support.rs` builds it, `quiet.rs` and `pushed.rs` pin what is reported here; the
ignored test `dump_every_run` prints every measure). No engine code was changed.

## The world and its numbers

One place, no foreign side, no routes but the local hand-over from farm to shop, no equipment
(capacity is a finite schedule of dated rows). Sites: a utility (1 hour makes 1 unit, no input), a
farm (a batch of 10 hours and 10 utility makes 10 food), a clinic (1 hour and 1 utility make 1
household service) and a shop (buys food from the farm, 1 handling hour per unit sold). Every
person needs 1 food (stored, bought at the shop), 1 utility and 1 service per period. Each site's
workforce is one household account paid by one employment row; one owner account holds one share
of every site; each site distributes 100% of its earnings. Prices follow the national opening's
rules: food quotes `Responsive` (step $1, target stock one period), services `ServiceResponsive`
(step $1). Hours follow plans through the engine's own staffing: each period the test closes the
period, takes `staffing_requests`, runs `advance_staffing` (one-period policy) and finishes with
the next labor. All cash floors are zero; the service-input caps are twice the need.

Derivation. Wage $10 an hour for everyone; prices utility $12, farm food $25, care $30, shop food
$38, so one person's basket is P = $80. Unit costs: utility 10; farm 10 + 12 = 22; clinic 10 + 12 =
22; shop 25 + 10 = 35. Per person consumed, the sites earn 3 x 2 + 3 + 8 + 3 = $20 and use 3 + 1 +
1 + 1 = 6 hours. (1) A worker's wages equal its need when it works P / w = 8 hours; then each site's
workforce is its hours / 8. (2) The owner's need costs the profits: owner persons x 80 = 20 x N.
(3) With N = 40 persons (a multiple of 8 and of the farm batch): utility 120 units, 15 workers;
farm 4 batches, 5 workers; clinic 40 units, 5 workers; shop 40 units, 5 workers; owner 10 persons.
Period receipts = wages + inputs + profit: utility 1440 = 1200 + 0 + 240; farm 1000 = 400 + 480 +
120; clinic 1200 = 400 + 480 + 320; shop 1520 = 400 + 1000 + 120; profits 800 = the owner's need.
(4) Stocks open at target: shop 40 food, farm 40 (its output buffer is one period's output, as in
the national opening), each household one period's food; carried at cost (22, 25, 38 a unit).
Cash: each site opens with what it pays out in a period (utility 1200, farm 880, clinic 880, shop
1400); workers open with 0 (wages are paid at the opening, before buying); the owner opens with
800 (distributions arrive at the close and are spent the next period). Capacity rows equal the
planned output for the two services (spare service capacity lowers their quote, rule R2) and are
twice the farm's batches. Everything is whole dollars; nothing is left over.

Variant with public money: wage tax 20% on each worker account, 20% on each site's positive
operating income, one $640 support payment to a household account of 8 persons who do not work.
Workers work 10 hours (10 x 10 x 0.8 = 80); N = 40 again: 12/4/4/4 workers, owner 8, supported 8.
Taxes 480 + 160 = 640 = support; the owner's 800 - 160 = 640 = its need; the public opens at 640.

## The quiet runs

Plain, taxed and under the market policy (`market_clearing`, order food, utility, household
services), 34 periods each: every measure equals its opening value in every period, exactly.
Cash by account, planned batches (120/4/40, shop 40 hours), hours asked and attended
(120/40/40/40), output, closing stock (farm 40, shop 40), posted prices, sales, each need's
requirement, purchase and consumption (40 each, unmet 0), public receipts and payments (640 and
640 in the taxed run) and total money. No transient: the opening is a fixed point of every rule.
One piece of history is needed and supplied: each staffing pool opens with its last request at
its opening hours (R5). Under the market policy no market is short, so households pay the
posted price and no clearing is recorded; restocking between businesses clears by the same rule
(`recurring/firms.rs` `replenish`) and is not short either.

| p | sites U/F/C/S | workers, owner | price U/F/C/S | out U/F/C | stock F/S | hours | unmet |
|--:|---|---|---|---|---|---|---|
| 1-34 | 1200/880/880/1400 | 0/0/0/0, 800 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 |

## The rules that move a pushed world

- R1 A service plans what was requested, and a household requests its need, funded or not
  (`services/admission.rs:127`, `services/market.rs:129`).
- R2 A service quote falls $1 when it performed less than its capacity and its direct cost was
  below its receipts; it rises on funded unmet demand or cost pressure (`services/market.rs:172-
  190`). The direct cost is what the performed units carried, without idle wages
  (`services/close.rs:181`).
- R3 A goods quote rises $1 when demand waited and stock is at or below target, falls $1 when
  nothing waited and stock is above target (`recurring/prices.rs:204`, `:216`).
- R4 The farm plans shipped + waiting + buffer - stock, rounded up to whole batches
  (`recurring/firms.rs:312-319`).
- R5 Staffing keeps the larger of this and the last request, in whole persons, at most the
  workforce (`staffing/transition.rs:70-74`).
- R6 Attended hours are the plan, at most the staffed hours and what the site's cash pays at its
  wage (`payments/attendance.rs:325`, `:368`), paid at the opening before any sale
  (`transition/state.rs:1343`). A wage rate never changes (`payments/attendance.rs:20`).
- R7 A household wants its need and no more (`recurring/households.rs:34-42`), bounded by its cash
  at the posted price (`:140`, `services/admission.rs:227`); food is bought before services
  (`transition/state.rs:1364`, `:1368`), utility before care (`services/admission.rs:135`).
- R8 A provider is paid only for what it performed, after it worked (`services/close.rs:251`).
- R9 A site distributes its earnings, never its cash beyond them (`financial/close.rs:200-204`).
- R10 The shop's next hours are what households were admitted to buy (`recurring/firms.rs:343-
  348`); under the market policy that is what it sold (`recurring/households.rs:369`) plus what
  buyers could pay for at the posted price and did not get (R11), and what it offers is bounded by
  its hours (`clearing/supply.rs:155-163`).
- R11 Under the market policy a seller plans from what was wanted: the quantity buyers could pay
  for at the posted price and did not get at the market's counts as waiting for a goods seller's
  plan, its hours and its quote (`recurring/firms.rs` `unshipped_quantities`, `handling_quantities`;
  `recurring/prices.rs` `update_prices`); a service quote with such buyers takes the reason
  `PricedOut` and steps up a step, also with spare capacity (`services/market.rs` `quote`).

## P1, less demand: runs away

The owner's cohort counts 5 persons instead of 10; cash, stock and purchase policy unchanged.

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|
|--:|---|---|---|---|---|---|---|
| 1 | 1200/770/880/1400 | 0/0/0/0, 910 | 11/24/29/38 | 115/40/35 | 45/40 | 120/40/40/40 | 0/0/0 |
| 2 | 1150/896/880/1435 | 9/26/18/18, 728 | 10/24/28/38 | 100/30/26 | 40/40 | 115/30/35/35 | 0/0/9 |
|3|1150/946/880/1439|29/56/16/26, 617|11/24/27/38|100/30/28|35/40|100/40/35/35|0/5/7|
| 5 | 1200/838/880/1439 | 6/106/19/3, 667 | 10/23/25/38 | 110/40/34 | 45/40 | 110/40/35/35 | 0/0/1 |
|8|1200/928/880/1479|43/131/18/3, 476|10/23/22/38|110/40/35|40/40|110/40/35/35|0/0/0|
|13|1180/832/665/1519|313/311/68/53, 217|10/21/20/38|108/40/30|45/40|110/40/35/35|0/2/5|
| 21 | 600/761/0/1570 | 440/854/6/616, 312 | 10/21/27/38 | 60/30/0 | 40/40 | 66/30/0/30 | 5/5/35 |
| 34 | 425/509/0/1545 | 8/1484/6/960, 222 | 12/23/40/39 | 32/20/0 | 30/40 | 40/30/0/23 | 10/24/35 |

Period 1: the services perform 5 less than capacity and quote $1 lower (R2); the farm ships 35,
keeps 45 above its target of 40 and quotes $1 lower (R3), and plans 3 batches (R4). From then the
farm's plan cycles 3, 4, 4, 4 (periods 1-12), then 3, 4: a period of 4, then 2, because whole
batches of 10 cannot make 35 (R4). Fewer hours pay less than the 15 utility workers' need, so care
goes unmet (R6, R7); lower prices leave the other workers with cash they have no use for (R7),
and the farm workers' cash grows to $1,484 because their wage never moves (R6). The clinic keeps
planning and staffing for requested care (R1, R5), sells less, pays idle hours its quote ignores
(R2), and its quote falls to $20 at period 13 while its cash falls to 0 at period 17. With less
than one wage it attends no hour, and with no performance it is never paid (R6, R8): its output
is 0 from period 17 to 34 while its quote climbs a step a period on funded unmet demand (R2).
End: care 35 of 40 unmet, food 10, utility 24. Stopped only by the clinic's empty account.

## P2, less supply: runs away

The farm's batch yields 9 food instead of 10.

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|
|--:|---|---|---|---|---|---|---|
| 1 | 1200/926/880/1400 | 0/0/0/0, 753 | 12/25/30/38 | 120/36/40 | 36/40 | 120/40/40/40 | 0/0/0 |
| 2 | 1200/998/880/1400 | 0/0/0/0, 681 | 12/25/29/38 | 120/36/38 | 32/40 | 120/40/40/40 | 0/0/2 |
| 3 | 1200/1084/880/1400 | 15/5/5/5, 565 | 12/25/28/38 | 120/36/36 | 28/40 | 120/40/40/40 | 0/0/4 |
|5|1200/1272/810/1400|90/30/30/30, 297|11/25/26/38|112/36/30|20/40|120/40/40/40|0/8/10|
|8|1079/1199/723/1400|280/130/130/30, 188|10/25/23/38|107/36/30|25/40|110/40/40/33|7/8/10|
|13|729/1004/5/1400|463/646/424/211, 277|10/25/24/41|72/36/0|34/40|83/40/22/35|4/8/40|
| 21 | 451/709/5/1466 | 6/1596/5/731, 190 | 10/22/32/41 | 45/27/0 | 47/40 | 51/30/0/29 | 10/25/40 |
| 34 | 126/5/5/865 | 365/1866/5/779, 50 | 10/32/45/46 | 12/0/0 | 0/0 | 12/0/0/17 | 40/28/40 |

Period 1: the farm plans 5 batches (asks 50 hours) but its 5 workers give 40 (R4, R5), makes 36
and ships 40 from its buffer. Its stock is below target with nothing waiting, so its quote holds
(R3). Selling stock it produced dearer cuts its earnings, so the owner receives $753 and is short
of care from period 2 (R9, R7); the farm keeps the rest of the sale as cash (R9). The clinic's
spare capacity lowers its quote (R2) while it staffs for full need (R1, R5); it stops at period 13
with $5 and never restarts (R6, R8). The farm's buffer and cash run down; it stops at period 30
with $5, and the shop has no food from period 33. End: food 40, care 40, utility 28 unmet.

## P3, less money: settles at once in a different steady state

The shop opens with $700. Every measure but the shop's cash equals the quiet run in every period
(the quiet table, shop cash 700). The shop pays its $400 of wages from 700 and buys food only after
selling (R6, `transition/state.rs` `dispatch_and_replenish`); distributions pay earnings and never
rebuild cash (R9). Total money is $700 lower and stays so.

## P4, higher pay: runs away

The clinic's wage is $11.

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|
|--:|---|---|---|---|---|---|---|
| 1 | 1200/880/880/1400 | 0/30/70/30, 670 | 11/25/31/38 | 116/40/36 | 40/40 | 120/40/40/40 | 0/0/4 |
|2|1200/900/880/1400|0/30/110/30, 610|11/25/30/38|120/40/35|40/40|120/40/40/40|0/0/5|
|3|1200/910/880/1400|15/35/155/35, 530|11/25/29/38|120/40/34|40/40|120/40/40/40|0/0/6|
|5|1200/917/840/1400|90/60/260/60, 332|10/25/27/38|114/40/30|40/40|120/40/40/40|0/6/10|
|8|1050/772/750/1475|150/150/470/100, 241|10/22/24/38|105/40/30|49/40|107/40/40/37|0/9/10|
| 13 | 610/727/6/1599 | 277/543/685/389, 323 | 10/20/25/39 | 61/30/0 | 31/40 | 67/40/0/36 | 4/9/40 |
| 21 | 160/4/6/1540 | 6/1548/4/1023, 176 | 10/23/33/41 | 16/0/0 | 0/8 | 28/23/0/23 | 20/24/40 |
| 34 | 282/4/6/4 | 1262/752/4/1909, 60 | 10/36/46/54 | 25/0/0 | 0/0 | 30/0/0/0 | 40/15/40 |

Period 1: after $440 of wages the clinic's $880 buys 36 utility, not 40 (`services/admission.rs:
227`), so it makes 36 and four accounts go without care; utility performs 116 and quotes lower
(R2). The clinic's workers keep $40 a period beyond their need (R6, R7), the owner's income falls,
and its care goes unmet. The clinic stops at period 12 with $6, the farm at period 21 with $4; the
shop is down to $4 at period 30 and works no hour after (R6, R8). The sites' cash ends in workers'
accounts.

## P2 under the market policy: runs away, the sellers planning from what was wanted

Identical to P2 through period 8. At period 9 the shop's hours (33, set by what it sold, R10) make
its food market short; it clears at $47.10, then $80.55 at period 10, drawing the workers' idle
cash to the shop and on to the owner ($1,644 at period 10). What buyers could pay for at the
posted price and did not get is now counted as wanted (R11): the shop's hours for period 10 are 34
and for period 11 are 40 (they were 33 and 33), and its posted price steps up to $39 and $40. The
shop's plan then follows what was wanted and sold, 38, 35, 35, ..., 25 at period 21, 15 at
period 30 and 30 at period 34 (it was held at 33 until period 23, fell to 0 by period 31). Its food
market is short again at periods 27, 28 and 30 to 34. The clinic stops at period 11 as before; its
buyers are priced out of an empty market, so its quote rises a step a period from $22 at period 11
to $45 at period 34 (R11), where it used to fall to the $1 minimum by period 30. The farm plans
more as buyers are priced out of its output, 9 batches from period 29, and stops at period 28 (it
stopped at period 29); its quote ends at $32. At period 34 the utility makes 30 (it made 25) and
food unmet is 40, utility 10 (15 before), care 40.

Moved by R11 and nothing else: every run without the market policy, and the market policy's quiet
run, are unchanged by one figure; of the market P2 run, periods 1 to 8 are unchanged and every
period from 9 differs.

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|
|--:|---|---|---|---|---|---|---|
| 13 | 759/1093/9/1400 | 120/460/0/383, 933 | 10/25/24/40 | 75/36/0 | 30/40 | 75/40/0/35 | 5/5/40 |
| 21 | 510/634/9/1463 | 4/1447/0/950, 140 | 10/24/32/40 | 46/27/0 | 43/40 | 55/30/0/26 | 13/24/40 |
| 34 | 300/8/9/1430 | 747/1/0/1070, 1591 | 10/32/45/47 | 30/0/0 | 0/0 | 30/0/0/30 | 40/10/40 |

## The other three pushes under the market policy: the engine before Task 6b

Added with Task 6b's first commit; the engine is as it stood after the plan for what buyers wanted
(R11) and before a service plans from what its buyers could pay for (rule P14). The tests are in
`pushed.rs`, built as the runs without a policy are, on the world with the policy.

### P1 under the market policy: runs away

Through period 2 it is P1's own run. The farm's plan climbs from period 16 to 8 batches, its stock
runs out at period 22, and the clinic, still planning and staffing for what households asked (R1),
is down to $9 at period 27 and makes nothing from then on. End: food 15, utility 20, care 35
unmet.

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|
|--:|---|---|---|---|---|---|---|
| 1 | 1200/770/880/1400 | 0/0/0/0, 910 | 11/24/29/38 | 115/40/35 | 45/40 | 120/40/40/40 | 0/0/0 |
| 2 | 1150/896/880/1435 | 9/26/18/18, 728 | 10/24/28/38 | 100/30/26 | 40/40 | 115/30/35/35 | 0/0/9 |
| 3 | 1200/916/712/1439 | 5/26/24/24, 813 | 11/24/27/38 | 100/30/24 | 35/40 | 100/40/35/35 | 0/0/11 |
| 5 | 1200/820/880/1439 | 9/76/1/1, 732 | 10/23/25/38 | 110/40/35 | 45/40 | 110/40/35/35 | 0/0/0 |
| 8 | 1200/909/817/1479 | 29/76/0/0, 649 | 10/23/22/38 | 110/40/35 | 40/40 | 110/40/35/35 | 0/0/0 |
| 13 | 1200/900/880/1559 | 26/43/11/11, 528 | 11/21/22/38 | 100/30/31 | 35/40 | 100/40/35/35 | 0/0/4 |
| 21 | 1012/740/880/1559 | 28/390/0/41, 507 | 10/21/21/38 | 92/30/27 | 5/40 | 103/40/35/35 | 0/0/8 |
| 34 | 458/704/9/1700 | 7/828/9/0, 1441 | 10/30/28/46 | 41/20/0 | 0/20 | 43/40/0/24 | 15/20/35 |

### P3 under the market policy: settles at once

Every period equals the first, as in P3: no market is ever short, so the rule has nothing to
price, and the shop holds its $700.

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|
|--:|---|---|---|---|---|---|---|
| 1 | 1200/880/880/700 | 0/0/0/0, 800 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 |
| 2 | 1200/880/880/700 | 0/0/0/0, 800 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 |
| 3 | 1200/880/880/700 | 0/0/0/0, 800 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 |
| 5 | 1200/880/880/700 | 0/0/0/0, 800 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 |
| 8 | 1200/880/880/700 | 0/0/0/0, 800 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 |
| 13 | 1200/880/880/700 | 0/0/0/0, 800 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 |
| 21 | 1200/880/880/700 | 0/0/0/0, 800 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 |
| 34 | 1200/880/880/700 | 0/0/0/0, 800 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 |

### P4 under the market policy: runs away

In period 1 the clinic's market clears at its posted price with four buyers priced out, and the
workers keep their surplus wage as in P4. The clinic stops at period 19 with $9, the farm makes
nothing from period 19, and the shop works no hour from period 26. End: food 40, utility 10, care
40 unmet.

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|
|--:|---|---|---|---|---|---|---|
| 1 | 1200/880/880/1400 | 29/29/39/29, 670 | 11/25/31/38 | 116/40/36 | 40/40 | 120/40/40/40 | 0/0/4 |
| 2 | 1200/900/880/1400 | 29/29/79/29, 610 | 11/25/30/38 | 120/40/35 | 40/40 | 120/40/40/40 | 0/0/5 |
| 3 | 1200/910/880/1400 | 44/34/124/34, 530 | 11/25/29/38 | 120/40/34 | 40/40 | 120/40/40/40 | 0/0/6 |
| 5 | 1200/917/840/1400 | 119/59/229/59, 332 | 10/25/27/38 | 114/40/30 | 40/40 | 120/40/40/40 | 0/6/10 |
| 8 | 1050/772/750/1475 | 179/149/439/99, 241 | 10/22/24/38 | 105/40/30 | 49/40 | 107/40/40/37 | 0/9/10 |
| 13 | 903/861/472/1599 | 8/69/659/16, 570 | 11/20/23/40 | 90/10/18 | 11/40 | 90/40/40/36 | 4/6/22 |
| 21 | 355/6/9/1320 | 811/1/268/952, 1435 | 10/27/29/46 | 35/0/0 | 0/0 | 35/0/0/35 | 40/5/40 |
| 34 | 305/6/9/0 | 3071/1/8/1622, 135 | 10/30/42/59 | 30/0/0 | 0/0 | 30/0/0/0 | 40/10/40 |

## What this means for an opening that is in balance

1. An opening balanced in whole numbers is exactly still for 34 periods, with or without taxes
   and under the market policy: the rules have a fixed point and no transient (quiet runs).
2. Away from it nothing pulls the world back: of four single pushes, three run away and one
   settles elsewhere; none returns (P1, P2, P4, P3).
3. Money that one rule moves out of circulation stays out: wages never change and households buy
   only their need, so a lower price or a higher wage leaves idle cash in workers' accounts
   (P1 farm workers $1,484, P4 shop workers $1,909) while sites run dry.
4. A site whose cash falls below one hour's wage never works again, because it pays wages before
   it sells and is paid only after it performs (P1 clinic, P2 clinic and farm, P4 all three).
5. Services plan and staff for what households need, not what they can pay, and their quotes
   ignore the idle wages this costs, so the clinic is the first site to fail in every runaway.
6. Whole batches with a one-period buffer make a farm whose demand is not a multiple of its batch
   cycle between two plans (P1: 3, 4, 4, 4, then 3, 4).
7. Cash held beyond a period's needs is never drawn on or rebuilt; halving it changes nothing
   else (P3).
8. Under the market policy a seller plans from what buyers were priced out of as well as what it
   sold, so a short shop asks for more hours and steps its quote up, and a stopped provider's quote
   rises with its priced-out buyers instead of falling to its minimum (P2 under the market policy).
