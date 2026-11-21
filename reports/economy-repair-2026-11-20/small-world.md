# A small world in balance, and what the engine does to it

Probe of the material circuit's own rules, 2026-11-20, branch `codex/households-and-homes`. The
world and every run are the test binary `rust/crates/babylon-material-circuit/tests/small_world.rs`
(`small_world/support.rs` builds it, `quiet.rs`, `pushed.rs` and `tiers.rs` pin what is reported here; the
ignored test `dump_every_run` prints every measure). No engine code was changed to make these runs; Task 6b
later changed the runs under a market policy, and its tables are at the end of the runs.

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

- R12 Under the market policy a service in the order of paying plans what the buyers of its stage market could
  pay for at the posted price plus the orders funded earlier for the period, and staffs for that, not for what
  was asked (`services/market.rs` `planned_quantity`); the receipt keeps what was asked.

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

## P2 under the market policy, before Task 6b: runs away, the sellers planning from what was wanted

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

## The pushes under the market policy after Task 6b: a service plans from what its buyers could pay for

Task 6b adds rule R12 (spec rule P14, `services/market.rs` `planned_quantity`): under a market policy a
service in the order of paying plans, and so staffs, for what the buyers of its stage market could pay
for at the posted price, with the orders funded earlier for the period, and not for what was asked; the
receipt still records what was asked. The runs without a market policy and the market policy's quiet run
and P3 are unchanged by one figure. Every period of the other three differs from the tables above, from
period 2 in P1 and P2 and from period 1 in P4 (the plan for the next period). Before, a provider that
staffed for need it was not paid for paid idle hours until its cash was gone; now none of them does.

### P1 under the market policy, after: slides down, nothing stops

R12 changed it: the clinic no longer pays idle hours, so its cash stays above $719 where it ran out at
period 27, and its output slides from 35 to 12 units as care goes unfunded (care unmet 23, was 35).

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|
|--:|---|---|---|---|---|---|---|
| 1 | 1200/770/880/1400 | 0/0/0/0, 910 | 11/24/29/38 | 115/40/35 | 45/40 | 120/40/40/40 | 0/0/0 |
| 2 | 1150/896/880/1435 | 9/26/18/18, 728 | 10/24/28/38 | 100/30/26 | 40/40 | 115/30/35/35 | 0/0/9 |
| 3 | 1200/852/880/1439 | 0/33/25/3, 723 | 11/24/27/38 | 100/30/23 | 35/40 | 100/40/26/35 | 0/0/12 |
| 5 | 1200/851/880/1439 | 19/66/4/18, 679 | 11/24/27/38 | 98/30/22 | 35/40 | 98/40/24/35 | 0/0/13 |
| 8 | 1200/851/880/1439 | 17/80/1/30, 658 | 10/24/28/38 | 93/40/21 | 40/40 | 99/40/21/35 | 0/3/14 |
| 13 | 1200/852/880/1439 | 1/113/4/20, 648 | 11/24/27/38 | 91/30/20 | 35/40 | 91/40/22/35 | 0/2/15 |
| 21 | 1200/852/880/1439 | 25/116/11/20, 613 | 11/24/27/38 | 89/30/18 | 35/40 | 89/40/22/35 | 0/3/17 |
| 34 | 1116/760/880/1479 | 8/27/1/2, 883 | 10/23/28/43 | 62/30/12 | 2/40 | 66/40/12/33 | 2/19/23 |

### P2 under the market policy, after: settles in a depressed band, nothing stops

R12 changed it: the clinic staffs only what its buyers can pay for, so it makes between 5 and 11 units
from period 16 with its cash over $755 where it stopped at period 11, the farm never stops (it stopped at
period 28), and the shop's hours stay between 31 and 40; the end is care 34, utility 21 and food 4 unmet.

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|
|--:|---|---|---|---|---|---|---|
| 1 | 1200/926/880/1400 | 0/0/0/0, 753 | 12/25/30/38 | 120/36/40 | 36/40 | 120/40/40/40 | 0/0/0 |
| 2 | 1200/998/880/1400 | 0/0/0/0, 681 | 12/25/29/38 | 120/36/38 | 32/40 | 120/40/40/40 | 0/0/2 |
| 3 | 1200/1084/880/1400 | 15/5/14/5, 556 | 11/25/28/38 | 118/36/35 | 28/40 | 120/40/38/40 | 0/0/5 |
| 5 | 1080/1303/880/1400 | 65/45/23/45, 318 | 10/25/26/38 | 103/36/27 | 20/40 | 115/40/31/40 | 0/8/13 |
| 8 | 960/1381/880/1400 | 25/142/1/102, 267 | 10/25/25/38 | 91/36/20 | 17/40 | 98/40/20/38 | 0/9/20 |
| 13 | 840/1359/880/1400 | 23/274/5/54, 322 | 10/25/24/40 | 79/36/13 | 18/40 | 82/40/13/35 | 5/14/27 |
| 21 | 1160/1065/880/1400 | 0/282/8/24, 338 | 10/25/24/44 | 73/36/8 | 31/40 | 77/40/8/34 | 8/15/32 |
| 34 | 1140/1258/851/1360 | 4/3/1/26, 515 | 10/26/25/49 | 65/36/6 | 22/40 | 71/40/6/35 | 4/21/34 |

### P3 under the market policy, after: unchanged

No market is ever short and every service is paid for what it performs, so R12 moves nothing; the table
above stands.

### P4 under the market policy, after: cycles in a depressed band, nothing stops for good

R12 changed it: no site runs dry (the clinic stopped at period 19, the farm at 19 and the shop at 26);
the clinic's output slides from 36 to 6, is zero at periods 18, 27, 28 and 29 and returns to 11 at
period 30, while the farm and the shop swing between 20 and 40 units and 24 and 40 hours.

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|
|--:|---|---|---|---|---|---|---|
| 1 | 1200/880/880/1400 | 29/29/39/29, 670 | 11/25/31/38 | 116/40/36 | 40/40 | 120/40/40/40 | 0/0/4 |
| 2 | 1200/882/880/1400 | 7/25/75/25, 663 | 12/25/30/38 | 116/40/34 | 40/40 | 116/40/40/40 | 0/0/6 |
| 3 | 1200/881/880/1400 | 30/22/46/22, 675 | 11/25/31/38 | 114/40/34 | 40/40 | 120/40/34/40 | 0/0/6 |
| 5 | 1200/1100/880/1400 | 27/17/19/17, 497 | 11/25/29/38 | 113/40/29 | 30/40 | 115/40/33/40 | 0/0/11 |
| 8 | 1110/1152/880/1400 | 21/72/15/72, 435 | 10/25/26/38 | 100/40/24 | 30/40 | 107/40/25/40 | 0/5/16 |
| 13 | 1136/1043/804/1400 | 14/252/11/232, 264 | 11/25/23/38 | 86/40/15 | 34/40 | 86/40/19/38 | 0/13/25 |
| 21 | 1106/829/880/1599 | 0/21/1/0, 720 | 12/21/23/41 | 70/30/8 | 29/40 | 70/40/10/39 | 3/9/32 |
| 34 | 1200/1588/652/1299 | 1/49/0/30, 337 | 13/27/28/49 | 75/40/7 | 2/40 | 82/40/7/38 | 4/12/33 |

## Tiers

The same world under the market policy with household wants (`tiers.rs`, `World::with_tiers`; spec rules
O7 and O8). Every household account wants, per person, one household service in tier 2 (comforts) and one
food and one utility in tier 3 (luxuries), so its wants follow its cohort as its needs do: the owner,
counted at 10 persons, wants 10 of each. The order of paying is unchanged: food, utility, household
services. A want is bought in the same market at the same price as a need, with the money its own list
does not need.

**Why the quiet run stays still at any size.** An account's cash at its moments of sale is exactly its
needs' posted cost (workers are paid their need at the opening, the owner holds its need), so every want's
room is $0: wants bid nothing, leave no order and no performance row, and the markets' demand at the quote,
from which a service plans, is the needs' alone. Every measure of the quiet run with tiers equals the quiet
run under the market policy in all 34 periods, the clinic plans 40 batches and the utility 120 each period,
and the clinic's service market receipt plans 40. Bought for wants: 0. Wanted, at posted prices (comforts,
luxuries): workers of the utility $450 and $750, the other three workers $150 and $250, the owner $300 and
$500. Every account is getting by (its needs are met and it bought no comfort).

The columns are those of the runs above, with "wants bought $" (comforts + luxuries, all accounts, at
posted prices) and "standards" (accounts going without / getting by / comfortable / affluent; five
accounts). Each run is set beside the same push under the market policy after Task 6b (the tables above).

### P1 with tiers: returns to the opening state

Without tiers the owner, who counts half its persons, keeps $910 it has no need to spend and the world runs
slides down (care unmet 23 at period 34, the clinic at 12 units). With tiers (O7) the owner spends what its needs
leave on its own comforts and luxuries: 5 persons' worth, $150 and $250 a period, 5 units of each good.
Utility, clinic and shop sell what they did in the balanced opening, no quote falls, and every period equals
the first, which equals the opening (cash, prices, plans, output). Nothing is unmet. The owner is the one
affluent account; the four worker accounts buy no want and are getting by.

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|wants bought $|standards|
|--:|---|---|---|---|---|---|---|---|---|
| 1 | 1200/880/880/1400 | 0/0/0/0, 800 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 150+250 | 0/4/0/1 |
| 2 | 1200/880/880/1400 | 0/0/0/0, 800 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 150+250 | 0/4/0/1 |
| 13 | 1200/880/880/1400 | 0/0/0/0, 800 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 150+250 | 0/4/0/1 |
| 34 | 1200/880/880/1400 | 0/0/0/0, 800 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 150+250 | 0/4/0/1 |

Beside it, P1 under the market policy after: period 34 cash 1116/760/880/1479, owner $883, prices
10/23/28/43, output 62/30/12, unmet 2/19/23, no wants.

### P2 with tiers: settles in the same depressed band

Period 1 is P2's own. The households' money goes to needs: wants are bought in 7 of the 34 periods (periods 4 to 7, 12,
16 and 24), never for more than $81 in a period, all of them comforts, and at period 34 every account goes without. No
site stops (it is also so without tiers). The band is a little different, by two rules: under O8 a comfort is
bought only in the periods when a worker's purse covers its needs at the clearing price (7 of 34 periods), and R12
plans from the demand at the quote, wants' rungs included, so the markets' plans and prices move off the run without
tiers. The clinic's output slides from 40 to between 4 and 7 units from period 14 (between 5 and 11 from period 16
without tiers), the farm makes 36 units in most periods and 27 in some (36 without tiers), its cash is $1,320 at
period 34, the utility's and the shop's markets clear short at period 34, and unmet at period 34 is food 5, utility
18, care 33 (4, 21, 34 without tiers). The largest worker account holds $20 at period 13 and $24 at period 34 (without
tiers $274 and $26).

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|wants bought $|standards|
|--:|---|---|---|---|---|---|---|---|---|
| 1 | 1200/926/880/1400 | 0/0/0/0, 753 | 12/25/30/38 | 120/36/40 | 36/40 | 120/40/40/40 | 0/0/0 | 0+0 | 0/5/0/0 |
| 2 | 1200/998/880/1400 | 0/0/0/0, 681 | 12/25/29/38 | 120/36/38 | 32/40 | 120/40/40/40 | 0/0/2 | 0+0 | 1/4/0/0 |
| 3 | 1200/1084/880/1400 | 15/5/14/5, 556 | 11/25/28/38 | 118/36/35 | 28/40 | 120/40/38/40 | 0/0/5 | 0+0 | 2/3/0/0 |
| 5 | 1110/1303/880/1400 | 10/18/6/18, 414 | 10/25/26/38 | 106/36/31 | 20/40 | 115/40/32/40 | 0/6/12 | 81+0 | 2/3/0/0 |
| 8 | 1200/1560/695/1400 | 13/5/1/11, 272 | 11/25/25/39 | 97/27/18 | 3/40 | 97/40/29/38 | 0/7/22 | 0+0 | 3/2/0/0 |
| 13 | 1200/1553/635/1359 | 20/17/3/4, 364 | 11/26/24/40 | 80/27/8 | 2/40 | 80/40/15/32 | 8/11/32 | 0+0 | 4/1/0/0 |
| 21 | 1200/1406/659/1359 | 5/19/2/22, 485 | 13/26/24/44 | 64/27/7 | 8/40 | 64/40/7/37 | 4/17/33 | 0+0 | 5/0/0/0 |
| 34 | 1200/1320/588/1280 | 2/24/13/16, 713 | 14/28/25/49 | 67/27/7 | 5/40 | 67/40/14/35 | 5/18/33 | 0+0 | 5/0/0/0 |

Beside it, P2 under the market policy after (the table above): period 13 cash 840/1359/880/1400, workers
23/274/5/54, owner $322, output 79/36/13; period 34 cash 1140/1258/851/1360, owner $515, output 65/36/6.

### P3 with tiers: settles at once

As P3 and as the quiet run with tiers: the shop holds its $700, every period equals the first, nothing is
short and no account has money beyond its needs, so no want is bought. Every account is getting by.
Bought for wants: $0 at periods 1, 13 and 34.

### P4 with tiers: cycles in a depressed band, nothing stops

In period 1 the clinic's cash buys 36 units of utility, so four accounts go without care; the clinic's market clears
short, at $31.66 where it cleared at its posted $30 without tiers; the owner holds $715 at the close, $670 without
tiers, and no want is bought in period 1. The cause is O8, the one price of ADR312 P2 as amended, through
`clear_ladder_market`: the workers' care comfort rungs count in the demand at the $30 quote, which lifts it above
the clinic's 36 units, so the short market clears above its posted price by bisection; at $31.66 each purse fills
its need rung first and the comfort rungs get nothing, so the workers pay $1.66 more per unit of need (w_clinic,
5 units, about $8.30 more: its cash falls from $39 to $31) and buy nothing for it. R12 plans the clinic from the
demand at the quote, which includes those rungs (41 against 40). The workers' surplus wage buys a comfort in 15 of the
34 periods: $62, $54 and $56 of care at periods 2, 8 and 13 among them, never more than $62 and never a luxury. No
site stops, and the clinic does not make nothing in periods 18, 27, 28 and 29 as it did without tiers; it ends at 3
units (7 without), unmet at period 34 is food 4, utility 7, care 37 (4, 12, 33), and every account goes without. The
largest worker account holds $19 at period 13 and $12 at period 34 (without tiers $252 and $49).

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|wants bought $|standards|
|--:|---|---|---|---|---|---|---|---|---|
| 1 | 1200/880/880/1400 | 6/23/31/23, 715 | 11/25/31/38 | 116/40/36 | 40/40 | 120/40/40/40 | 0/0/4 | 0+0 | 4/1/0/0 |
| 2 | 1200/882/880/1400 | 15/18/5/18, 739 | 12/25/30/38 | 116/40/36 | 40/40 | 116/40/40/40 | 0/0/6 | 62+0 | 2/3/0/0 |
| 3 | 1200/881/880/1400 | 11/17/30/17, 721 | 11/25/31/38 | 116/40/36 | 40/40 | 120/40/36/40 | 0/0/4 | 0+0 | 2/3/0/0 |
| 5 | 1200/1100/880/1400 | 18/12/27/12, 509 | 11/25/29/38 | 116/40/32 | 30/40 | 117/40/36/40 | 0/0/8 | 0+0 | 3/2/0/0 |
| 8 | 1170/1152/880/1400 | 27/8/9/8, 502 | 10/25/28/38 | 109/40/29 | 30/40 | 109/40/29/40 | 0/0/13 | 54+0 | 3/2/0/0 |
| 13 | 1200/1099/880/1400 | 17/11/19/10, 520 | 11/25/27/38 | 102/40/23 | 30/40 | 102/40/26/40 | 0/4/19 | 56+0 | 3/2/0/0 |
| 21 | 1200/1162/734/1400 | 0/10/19/8, 623 | 11/25/27/38 | 99/30/18 | 20/40 | 99/40/25/40 | 0/3/22 | 0+0 | 3/2/0/0 |
| 34 | 1183/1544/143/1359 | 7/12/1/1, 906 | 10/26/25/43 | 83/40/3 | 10/40 | 93/40/10/36 | 4/7/37 | 0+0 | 5/0/0/0 |

Beside it, P4 under the market policy after (the table above): period 13 cash 1136/1043/804/1400, workers
14/252/11/232, output 86/40/15; period 34 cash 1200/1588/652/1299, owner $337, output 75/40/7.

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
9. Under the market policy a service plans and staffs for what its buyers can pay for (R12), so the idle
   hours of item 5 are not paid: no pushed run stops a site for good, and the three that ran away now slide
   or cycle in a depressed band (P1, P2, P4 under the market policy).
10. With tiers, money a push frees is spent on wants only where an account has it and its needs are met:
    the owner of P1 spends $400 a period on 5 persons' comforts and luxuries and the world returns to its
    opening state, which no run without tiers does. In P2 and P4 the money is spent on needs that go unmet,
    so wants are bought in 7 and 15 of the 34 periods and never for more than $81 (P2) or $62 (P4), and
    no luxury is ever bought there; every account ends going without.
11. Workplaces no longer run dry from idle cash in workers' accounts (point 3), but that was already so
    under the market policy after Task 6b, and the tiers change it only a little: the largest worker
    account at period 34 is $0 in P1 (it was $27), $24 in P2 (it was $26) and $12 in P4 (it was $49), at
    period 13 $0, $20 and $19 (it was $113, $274 and $252). The clinic of P4 stops at no period, where it
    made nothing in periods 18, 27, 28 and 29 under the market policy. What tiers do not do is put the
    shortage right: unmet need in P2 and P4 is as large as without them (P4 care 37, was 33).

## With a national fund

The taxed world of the record (`World::taxed`, 40 persons: 12/4/4/4 workers, owner 8, supported 8) with its tax shared
between the treasury and a national fund (`World::benefits`, `benefits.rs`; spec rules O12 and O13, ADR313). Both
public accounts tax the same payers: the treasury at 500 points on each worker account's wages and on each site's
positive operating income, the fund at 1,500, which together are the taxed world's 20%. The fund's budget is
`CashInProportion` (cap 0, floor 0): it pays every claim in full while it has the cash and cuts each rank in
proportion when it has not. It holds two programs, both rank 0: `no_earner`, $60 a person of the supported account (8
persons, $480 a period), and `laid_off`, half pay (5,000 points) for 13 half periods to the four worker accounts. The
treasury pays the rest of the support, $80 - $60 = $20 a person, $160 a period.

**Derivation.** Assessed taxes are the taxed world's: wages 12 x 100 + 3 x 4 x 100 = 2,400 at 20% = 480, operating
income 160, 640 in all, of which the fund collects 480 (15%) and the treasury 160 (5%). The fund opens with $960, two
periods of its payments (O13), and pays 480 a period; the treasury opens with 160 and pays 160. In the quiet run each
account collects what it pays, so the book is conserved and nothing moves. A person laid off in play was working 10
hours at $10: the program owes half, $50, in each of the first six periods and a half of that, $25, in the seventh (13
half periods), and nothing in the eighth. The two steps of a layoff are then: pay falls from the wage to half pay at
the layoff, and half pay itself ends in period 7 after the layoff, 50, 50, 50, 50, 50, 50, 25, 0.

Columns are those of the runs above, with "fund cash" (closing), "due/paid" of `no_earner` (the supported account) and
of `laid_off` (the four worker accounts together), and "covered" (the persons the half-pay program counts). Prices are
in dollars; periods 1, 2, 3, 5, 8, 13, 21 and 34 are shown. A worker account in the small world is one pooled
household of 4 to 12 persons with one staffing member each, so a layoff of one person is one person of a pool: the
account's wage income falls by $100 (and the benefit it is paid replaces some of it), not the whole of a household's;
across a pool's households people would go back in proportion to each one's people looking for work, and in the small
world each pool has one household, so that rule is not exercised here.

### How each fund run is compared

Every fund run is set beside **its control**: the same push on the same opening with no fund. The fund's opening is
the taxed world (`World::taxed`: 10 hours, 12/4/4/4 workers, owner 8, a 20% tax, a supported account), so the control
is `World::taxed().pushed(P)` for form (a) and `World::taxed().with_tiers().pushed(P)` for form (b), the treasury
alone paying the whole support. What differs between a fund run and its control is the fund and nothing else. The
earlier runs of this record (`World::plain()`: 8 hours, 15/5/5/5, no tax) are a different opening; they are given only
as a second, labeled comparison and no difference between them and a fund run is credited to the fund. The controls
are printed by the ignored dump (`taxed P1` to `taxed P4`, `taxed tiers P1` to `taxed tiers P4`); no test pins them.

### Form (a): the taxed world, no market policy

**Quiet: exactly still.** Every period equals the first, which equals the opening
(`the_fund_with_both_programs_is_still`): the fund holds $960 and pays $480, the treasury holds $160 and pays $160,
nobody is laid off, and the record of layoffs is empty in all 34 periods.

#### P1 on the fund: runs away

The owner counts 4 persons instead of 8. The record: no one is laid off in play (employment stays 12/4/4/4), the fund
is cut from period 6 (465.57 of 480), and from period 18 the farm, clinic and shop stop (periods 18, 19, 18), the
utility ending at 28 units; unmet need at period 34 is 36/8/36 and the fund holds $46. Class: runs away.
**Control (taxed, no fund):** also runs away. The farm and clinic stop at periods 18 and 17, unmet at period 34 is
36/11/36, the utility makes 25 units, and employment first falls at period 26 (one person of the shop's pool). **What
the fund changed:** the clinic stops two periods later (19), the utility makes 28 units and its unmet is 8 rather than
11, and nobody is laid off; the farm stops at the same period and the class is the same. A person sees the same
collapse in both; with the fund the supported household's $60 a person is paid in full to period 5, then shrinks to
$5.85 a person (46.8 of 480) by period 34. *Second comparison (plain world, a different opening):* P1 there runs away
too, with the clinic stopped from 17 and unmet 10/24/35.

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|fund cash|due/paid no_earner|due/paid laid_off|covered|
|--:|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1200/792/880/1400 | 0/0/0/0, 774 | 11/24/29/38 | 116/40/36 | 44/40 | 120/40/40/40 | 0/0/0 | 925 | 480/480 | 0/0 | 0 |
| 2 | 1200/871/880/1436 | 0/8/0/0, 792 | 10/24/28/38 | 107/30/36 | 38/40 | 116/40/36/36 | 0/0/0 | 793 | 480/480 | 0/0 | 0 |
| 3 | 1200/887/880/1439 | 0/24/0/0, 855 | 10/23/27/38 | 112/40/36 | 42/40 | 112/40/36/36 | 0/0/0 | 682 | 480/480 | 0/0 | 0 |
| 5 | 1100/950/880/1515 | 8/0/0/0, 1015 | 10/22/25/38 | 102/30/36 | 40/40 | 112/30/36/36 | 0/0/0 | 465 | 480/480 | 0/0 | 0 |
| 8 | 1200/831/847/1519 | 24/105/9/0, 1024 | 11/21/22/38 | 112/40/33 | 42/40 | 112/40/36/36 | 0/0/3 | 403 | 480/398.38 | 0/0 | 0 |
| 13 | 1070/762/712/1559 | 336/329/73/64, 704 | 10/21/20/38 | 107/30/33 | 12/40 | 108/40/36/36 | 0/0/3 | 367 | 480/372.29 | 0/0 | 0 |
| 21 | 320/8/8/356 | 1131/643/460/1112, 216 | 11/27/27/43 | 32/0/0 | 0/0 | 32/0/0/38 | 36/4/36 | 105 | 480/106.5 | 0/0 | 0 |
| 34 | 315/8/8/6 | 2885/173/114/842, 60 | 10/40/40/56 | 28/0/0 | 0/0 | 31/0/0/0 | 36/8/36 | 46 | 480/46.8 | 0/0 | 0 |

#### P2 on the fund: runs away

The farm's yield is 9 a batch. The clinic stops at period 14, the farm's output falls from 36 to 9
units by period 34, the fund is cut from period 9 and holds $121 at period 34; unmet 18/29/40. The first layoff in
play is at period 28 (one person of the shop's pool): 50 due for six periods, 25 in the seventh, paid at 10 to 13
dollars of the 50 (the fund pays about a quarter of every claim, cut in proportion), so the two steps show in the
receipts at periods 28 to 33 and 34 (50, 50, 50, 50, 50, 50, 25). Class: runs away.
**Control (taxed, no fund):** also runs away. The clinic stops at 13, the farm makes 18 units at 34, unmet is
17/30/40, and employment first falls at period 23. **What the fund changed:** the clinic stops one period later (14),
the farm makes fewer units (9, not 18), unmet is 18/29/40 (one more of food, one fewer of utility), and the first fall
in employment comes four periods later (27). The fund did not keep the farm up. A person sees the same stop, but a
laid-off shop worker is paid a quarter of the half pay it is owed. *Second comparison (plain world):* the clinic stops
at 13 and unmet is 40/28/40.

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|fund cash|due/paid no_earner|due/paid laid_off|covered|
|--:|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1200/926/880/1400 | 0/0/0/0, 602 | 12/25/30/38 | 120/36/40 | 36/40 | 120/40/40/40 | 0/0/0 | 953 | 480/480 | 0/0 | 0 |
| 2 | 1200/998/880/1400 | 0/0/0/0, 533 | 12/25/29/38 | 120/36/37 | 32/40 | 120/40/40/40 | 0/0/3 | 928 | 480/480 | 0/0 | 0 |
| 3 | 1200/1084/880/1400 | 12/4/4/4, 463 | 12/25/28/38 | 120/36/36 | 28/40 | 120/40/40/40 | 0/0/4 | 892 | 480/480 | 0/0 | 0 |
| 5 | 1200/1272/864/1400 | 72/24/24/24, 290 | 11/25/26/38 | 117/36/32 | 20/40 | 120/40/40/40 | 0/3/8 | 773 | 480/480 | 0/0 | 0 |
| 8 | 1130/1357/824/1400 | 256/114/104/64, 153 | 11/25/23/38 | 113/36/32 | 18/40 | 113/40/40/36 | 2/7/8 | 479 | 480/480 | 0/0 | 0 |
| 13 | 864/1293/255/1400 | 581/395/420/79, 225 | 10/25/24/41 | 86/36/11 | 21/40 | 97/40/40/36 | 3/5/29 | 361 | 480/371.81 | 0/0 | 0 |
| 21 | 624/1182/5/1400 | 221/1299/4/760, 273 | 10/25/32/42 | 62/36/0 | 26/40 | 66/40/0/34 | 6/18/40 | 259 | 480/262.87 | 0/0 | 0 |
| 34 | 260/577/5/1391 | 0/2445/4/1103, 149 | 11/26/45/43 | 21/9/0 | 5/40 | 31/40/0/23 | 18/29/40 | 121 | 480/112.52 | 25/5.86 | 1 |

#### P3 on the fund: settles at once

The shop opens with $700. Every period equals the first, as without the fund: the shop holds $700, the fund $960, no
one is laid off and the fund is never cut. Class: settles at once in a different steady state.
**Control (taxed, no fund):** the same, exactly still with the shop at $700 and the treasury, which collects the whole
tax of $640 and pays $160, holding $640 (with the fund the treasury holds $160 and the fund $960). **What the
fund changed:** nothing. A person sees nothing different with the fund. *Second comparison (plain world):* the same.

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|fund cash|due/paid no_earner|due/paid laid_off|covered|
|--:|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1200/880/880/700 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 960 | 480/480 | 0/0 | 0 |
| 2 | 1200/880/880/700 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 960 | 480/480 | 0/0 | 0 |
| 3 | 1200/880/880/700 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 960 | 480/480 | 0/0 | 0 |
| 5 | 1200/880/880/700 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 960 | 480/480 | 0/0 | 0 |
| 8 | 1200/880/880/700 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 960 | 480/480 | 0/0 | 0 |
| 13 | 1200/880/880/700 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 960 | 480/480 | 0/0 | 0 |
| 21 | 1200/880/880/700 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 960 | 480/480 | 0/0 | 0 |
| 34 | 1200/880/880/700 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 960 | 480/480 | 0/0 | 0 |

#### P4 on the fund: runs away

The clinic pays $11. The fund is cut from period 11 (385.17 of 480), the farm, clinic and shop stop (periods 24, 14,
24), and unmet at period 34 is 40/15/40. One shop worker is laid off at 27:
the two steps show in the dues, 50 for periods 27 to 32, 25 at 33, 0 at 34, but the fund paid $3.37 to $6.28 of every $50
(7 to 13%, about a tenth). Class: runs away. **Control (taxed, no fund):** also runs away. The farm and clinic stop at 26 and 12,
the utility makes 11 units at 34, unmet is 40/29/40, and employment first falls at period 23. **What the fund
changed:** the farm stops two periods earlier (24) and the clinic two later (14), the utility makes 25 units and its
unmet is 15 rather than 29. The fund's 40/15/40 equals the *plain* P4's unmet, but that is a different opening and is
not a fund effect. A person sees the same stop, and a laid-off worker is paid about a tenth of the half pay it is owed.
*Second comparison (plain world):* unmet 40/15/40 there too.

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|fund cash|due/paid no_earner|due/paid laid_off|covered|
|--:|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1200/880/880/1400 | 0/30/62/30, 542 | 11/25/31/38 | 116/40/36 | 40/40 | 120/40/40/40 | 0/0/4 | 942 | 480/480 | 0/0 | 0 |
| 2 | 1200/900/880/1400 | 0/30/94/30, 494 | 11/25/30/38 | 120/40/35 | 40/40 | 120/40/40/40 | 0/0/5 | 915 | 480/480 | 0/0 | 0 |
| 3 | 1200/910/880/1400 | 12/34/130/34, 460 | 11/25/29/38 | 120/40/35 | 40/40 | 120/40/40/40 | 0/0/5 | 885 | 480/480 | 0/0 | 0 |
| 5 | 1200/917/880/1400 | 72/54/214/54, 349 | 11/25/27/38 | 120/40/32 | 40/40 | 120/40/40/40 | 0/0/8 | 794 | 480/480 | 0/0 | 0 |
| 8 | 1120/888/816/1438 | 220/122/378/114, 203 | 10/23/24/38 | 112/40/32 | 43/40 | 113/40/40/39 | 0/8/8 | 573 | 480/480 | 0/0 | 0 |
| 13 | 869/721/144/1636 | 410/356/806/231, 241 | 10/20/25/38 | 79/40/6 | 48/40 | 94/40/40/37 | 3/7/34 | 366 | 480/360.9 | 0/0 | 0 |
| 21 | 633/742/1/1480 | 391/1226/0/1020, 185 | 10/23/33/40 | 63/30/0 | 0/40 | 71/40/0/32 | 8/11/40 | 248 | 480/265.36 | 0/0 | 0 |
| 34 | 352/4/1/4 | 1007/1229/0/1956, 100 | 13/36/46/51 | 25/0/0 | 0/0 | 38/0/0/0 | 40/15/40 | 57 | 480/57 | 0/0 | 0 |

#### P5 on the fund: runs away after the fund runs short

The fund's two rates fall to 1,125 points: it collects 360 against 480 and drains its reserve by 120 a period (840,
720, 600, 480 and 360 at period 5). **The first cut is at period 6**: the fund opens with $360 against 480 due, only
`no_earner` has a claim (the four `laid_off` receipts are due nothing), so it is paid 75%, $360. The cut then deepens
as the world shrinks: 339 at period 8, 288 at 13, 128 at 21, 18 at 34. When a layoff is in play the cut is shared in
proportion: at period 21 the claims are 480 + 50 + 50 and each is paid the same 26.6% (127.85 + 13.32 + 13.32);
`every_cut_is_in_proportion` checks each short period of this run and the one under tiers (each receipt is floor(due x
budget / total) or one micro more, and the paid amounts add to the budget). Layoffs in play begin at period 20 (the
farm); the shop's cohort of period 28 shows the two steps (50 for six periods, 25 at 34, paid $3 to $4 of the 50).
From period 6 the clinic's quote and output slide; the clinic first makes nothing at period 15 and the farm and the
shop at period 26; unmet at period 34 is 40/24/40. Class: runs away. There is no run of the same push without a fund
in the record.

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|fund cash|due/paid no_earner|due/paid laid_off|covered|
|--:|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1200/880/880/1400 | 45/15/15/15, 670 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 840 | 480/480 | 0/0 | 0 |
| 2 | 1200/880/880/1400 | 90/30/30/30, 700 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 720 | 480/480 | 0/0 | 0 |
| 3 | 1200/880/880/1400 | 135/45/45/45, 730 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 600 | 480/480 | 0/0 | 0 |
| 5 | 1200/880/880/1400 | 225/75/75/75, 790 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 360 | 480/480 | 0/0 | 0 |
| 8 | 1200/880/880/1400 | 396/132/132/132, 468 | 12/25/27/38 | 120/40/34 | 40/40 | 120/40/40/40 | 0/0/6 | 332 | 480/339.19 | 0/0 | 0 |
| 13 | 922/822/505/1437 | 797/368/344/293, 214 | 10/23/26/38 | 92/40/20 | 46/40 | 100/40/40/37 | 0/8/20 | 271 | 480/287.8 | 0/0 | 0 |
| 21 | 515/715/5/1607 | 654/1185/2/996, 209 | 11/20/34/38 | 51/20/0 | 35/40 | 51/30/0/30 | 8/18/40 | 152 | 480/127.85 | 100/26.64 | 2 |
| 34 | 221/6/5/4 | 612/1552/2/2300, 80 | 15/32/47/49 | 16/0/0 | 0/0 | 16/0/0/0 | 40/24/40 | 25 | 480/18.07 | 25/0.94 | 1 |

### Form (b) before: the engine before the wage tax was ahead of comforts

**These tables show the engine before the task "The wage tax is ahead of comforts and luxuries" (21 November 2026).**
They are kept as they were. The same runs after it follow in "Form (b) after", and the sentences below that say the
quiet run cannot be made still, or that a run slides, cycles or runs short, describe this engine only.

This is the form the country will run in (`World::benefits().with_tiers()`): the fund's two taxes, per-person benefit
and half pay, under the market policy with household wants (rules O7 and O8; section "Tiers").

**It cannot be made exactly still, and the fund is not the reason.** In the plain world the quiet run with tiers is
still because each account's cash at its moments of sale is exactly its needs' posted cost, so a want's room is $0. In
the taxed world the workers are paid the gross wage and the 20% tax is levied after they have bought, so a worker
account has room up to its tax (240 for the utility's, 80 for the others) and bids for comforts with it: in period 1
the workers buy $150 of comforts, the public accounts collect 280 of the 640 assessed (the tax is then uncollected
from accounts that spent it first), the owner ends with $1,000 where it opened with $640, the clinic's market clears
at $40 and 5 units of care go unmet. The same happens with no fund at all: `World::taxed().with_tiers()` also collects
280 in period 1, and its owner holds $1,000. No sizing of the fund can put this right with the same two taxes, because
the cause is the timing of the tax against the purchase, so the run was not forced. What remains after the opening's
transient is a narrow band: unmet need 0 to 2 food, 3 to 8 utility and 6 to 10 care at the periods shown, the fund at
$209 to $236 in periods 4 to 34, taxes collected 325 to 367 of 640 assessed at periods 5 to 34, the supported
household paid $26 to $34 a person rather than $60 (the fund pays $210 to $273 of the $480 due), and no site stops.
Without the fund (the taxed world with tiers, the treasury alone paying the whole support) the clinic slides to 4
units by period 34; with the fund it holds 39 (the same band, then, is not a product of the fund). Class: cycles in a
narrow band, never exactly still after period 1.

The first fund cut is at period 3 in every run of this form, because the reserve of $960 is spent in the first two
periods.

#### Quiet on the fund with tiers: cycles in a narrow band

Period 1 pays in full out of the reserve (480 of 480); the first cut is at period 3 (396.26 of 480) and at period 34
the fund pays 222.98.

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|wants bought $|standards|fund cash|due/paid no_earner|due/paid laid_off|covered|
|--:|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1200/880/880/1400 | 0/0/0/0, 1000 | 12/25/31/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/5 | 150+0 | 2/4/0/0 | 680 | 480/480 | 0/0 | 0 |
| 2 | 1200/1000/880/1400 | 0/0/0/0, 1079 | 13/25/32/39 | 120/30/38 | 30/40 | 120/40/40/40 | 0/0/6 | 124+36 | 1/5/0/0 | 396 | 480/480 | 0/0 | 0 |
| 3 | 1200/1061/880/1400 | 0/0/0/0, 1161 | 12/25/33/40 | 119/40/36 | 30/40 | 120/40/40/40 | 0/0/10 | 192+39 | 4/2/0/0 | 273 | 480/396.26 | 0/0 | 0 |
| 5 | 1200/1113/880/1400 | 0/0/0/0, 1192 | 10/25/33/42 | 116/40/40 | 30/40 | 119/40/40/40 | 0/8/8 | 264+126 | 1/4/1/0 | 221 | 480/230.29 | 0/0 | 0 |
| 8 | 1200/1145/880/1400 | 0/0/0/0, 1124 | 10/25/34/45 | 118/40/40 | 30/40 | 118/40/40/40 | 1/3/8 | 264+98 | 1/4/1/0 | 210 | 480/210.63 | 0/0 | 0 |
| 13 | 1170/1155/880/1400 | 0/0/0/0, 1148 | 10/25/38/48 | 115/40/40 | 30/40 | 117/40/40/40 | 1/5/8 | 304+48 | 1/4/1/0 | 215 | 480/209.4 | 0/0 | 0 |
| 21 | 1200/1106/880/1400 | 0/0/0/0, 1187 | 11/25/38/49 | 115/40/38 | 31/40 | 115/40/40/40 | 1/7/10 | 312+20 | 2/3/1/0 | 222 | 480/214.11 | 0/0 | 0 |
| 34 | 1200/1089/880/1400 | 0/0/0/0, 1174 | 10/25/34/54 | 117/40/39 | 32/40 | 119/40/39/40 | 2/6/9 | 264+150 | 2/3/1/0 | 233 | 480/222.98 | 0/0 | 0 |

#### P1 on the fund with tiers: slides down, nothing stops

The owner spends its freed money on its own comforts and luxuries and holds $1,000 to $1,480 over the run (the one
affluent account from period 2); the utility and the clinic slide, to 88 and 16 units. A layoff in play comes at
period 18 (the utility): 50 for periods 18 to 23, 25 at 24, 0 at 25, paid $14 to $16 of the 50. At 34 unmet is 4/9/24,
no site has stopped. Class: slides down without stopping.
**Control (taxed with tiers, no fund):** not still either, and it slides the same way: the utility makes 88 units and
the clinic 14, unmet at 34 is 6/4/26, no site stops, employment first falls at period 15, and the owner holds $895 at
34. **What the fund changed:** the clinic makes 2 more units (16), care unmet is 24 rather than 26, utility unmet is 9
rather than 4, and the owner holds $1,096; the utility's output is the same (88). The class is the same. *Second
comparison (plain world with tiers, no tax):* P1 returns to its opening state, every period equal to the first. That
return is not the fund's absence: the taxed world with tiers and no fund does not return, because the tax is levied
after the purchases. A person sees: the owner's household is better off than at the opening and the clinic's patients
are worse off, with or without the fund.

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|wants bought $|standards|fund cash|due/paid no_earner|due/paid laid_off|covered|
|--:|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1200/880/880/1400 | 0/0/0/0, 1000 | 12/25/31/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/2 | 180+200 | 1/5/0/0 | 680 | 480/480 | 0/0 | 0 |
| 2 | 1200/880/880/1400 | 0/0/0/0, 1240 | 12/25/32/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/5 | 279+200 | 1/4/0/1 | 400 | 480/480 | 0/0 | 0 |
| 3 | 1200/880/880/1400 | 0/0/0/0, 1480 | 12/25/33/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/5 | 288+200 | 1/4/0/1 | 200 | 480/400 | 0/0 | 0 |
| 5 | 1200/947/880/1439 | 0/0/0/0, 1399 | 12/24/33/38 | 113/30/38 | 32/40 | 113/40/40/39 | 0/5/8 | 340+196 | 1/4/0/1 | 134 | 480/165 | 0/0 | 0 |
| 8 | 1200/940/880/1439 | 0/0/0/0, 1374 | 11/24/34/39 | 109/40/37 | 37/40 | 115/40/37/39 | 0/8/8 | 297+204 | 1/4/0/1 | 149 | 480/149.61 | 0/0 | 0 |
| 13 | 1200/925/880/1439 | 0/0/0/0, 1401 | 12/24/33/40 | 108/30/33 | 26/40 | 108/40/37/38 | 2/6/8 | 170+204 | 1/4/0/1 | 144 | 480/147.28 | 0/0 | 0 |
| 21 | 1200/931/880/1439 | 0/0/0/0, 1381 | 12/24/33/42 | 105/30/27 | 4/40 | 105/40/33/37 | 3/5/13 | 136+208 | 4/1/0/1 | 169 | 480/143.4 | 50/14.94 | 1 |
| 34 | 1200/1760/764/962 | 0/0/0/0, 1096 | 11/29/32/49 | 88/30/16 | 0/38 | 88/40/23/36 | 4/9/24 | 132+236 | 4/1/0/1 | 212 | 480/139.18 | 50/14.5 | 1 |

#### P2 on the fund with tiers: cycles in a depressed band

Class: cycles in a depressed band, no site stopping; unmet at 34 is 6/8/30, the clinic makes 18 units, and the shop's
cash falls to $420. **Control (taxed with tiers, no fund):** also depressed with no site stopping: unmet 4/14/31, the
clinic makes 9 units, the shop holds $852, and employment first falls at period 8. **What the fund changed:** the
clinic makes twice as many units (18 against 9), utility unmet is 8 rather than 14, the shop ends with $420 against
$852, and the first fall in employment comes at 14, not 8. *Second comparison (plain world with tiers):* settles in a
depressed band, unmet 5/18/33, clinic 7 units. Layoffs in
play come in waves from period 15 (the clinic) and 16 (the utility), up to 3 persons of the utility at once at periods
20 to 22. The clinic's pinned window shows two cohorts: one person at 50 for periods 15 to 18, a second laid off at 19
makes it 100 for periods 19 and 20, then 75 at 21 (the first at its half step, 25, plus the second's 50) and 50 at 22,
paid at 30 to 48% of what is due. A person sees about the same as the control, with a clinic that makes more and
worker accounts that hold $0 of cash.

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|wants bought $|standards|fund cash|due/paid no_earner|due/paid laid_off|covered|
|--:|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1200/926/880/1400 | 0/0/0/0, 962 | 12/25/31/38 | 120/36/40 | 36/40 | 120/40/40/40 | 0/0/5 | 150+0 | 2/4/0/0 | 673 | 480/480 | 0/0 | 0 |
| 2 | 1200/989/880/1400 | 0/0/0/0, 1104 | 13/25/32/39 | 120/36/38 | 32/40 | 120/40/40/40 | 0/0/6 | 124+24 | 1/5/0/0 | 392 | 480/480 | 0/0 | 0 |
| 3 | 1200/1064/880/1400 | 0/0/0/0, 1180 | 13/26/33/40 | 120/36/36 | 28/40 | 120/40/40/40 | 0/0/11 | 224+52 | 4/2/0/0 | 255 | 480/392.9 | 0/0 | 0 |
| 5 | 1200/1284/880/1360 | 0/0/0/0, 1083 | 13/26/33/42 | 112/27/36 | 11/40 | 112/40/36/40 | 0/5/11 | 224+77 | 3/3/0/0 | 197 | 480/238.63 | 0/0 | 0 |
| 8 | 1200/1646/880/1360 | 0/0/0/0, 806 | 12/26/34/43 | 112/36/39 | 1/40 | 112/40/40/40 | 0/7/8 | 245+0 | 1/5/0/0 | 153 | 480/164.13 | 0/0 | 0 |
| 13 | 1200/1760/880/1176 | 0/0/0/0, 843 | 11/30/33/45 | 111/36/27 | 0/36 | 111/40/35/38 | 4/4/14 | 34+0 | 4/2/0/0 | 158 | 480/168.45 | 0/0 | 0 |
| 21 | 1200/1760/781/888 | 0/0/0/0, 1064 | 12/38/33/53 | 86/36/13 | 0/36 | 86/40/13/40 | 5/11/30 | 96+96 | 5/1/0/0 | 287 | 480/192.88 | 225/90.41 | 5 |
| 34 | 1200/1760/880/420 | 0/0/0/0, 1448 | 12/51/27/66 | 90/36/18 | 0/36 | 90/40/18/40 | 6/8/30 | 224+195 | 5/0/1/0 | 269 | 480/226.6 | 100/47.21 | 2 |

#### P3 on the fund with tiers: the quiet run, the shop at half its cash

Every period equals the quiet run with tiers on the fund, apart from the shop's cash: $700 where the quiet run has
$1,400 (outputs, unmet need, the fund's cash and every other account agree in all 34 periods). Class:
cycles in the quiet run's narrow band. **Control (taxed with tiers, no fund):** not still, and equal to the taxed
quiet run with tiers in every measure but the shop's cash ($620 at 34): the clinic slides to 4 units and unmet at 34 is
5/4/36. **What the fund changed:** the clinic holds 39 units and unmet is 2/6/9. As in the quiet run, the fund holds
the clinic up. *Second comparison (plain world with tiers):* settles at once, exactly still. A person sees nothing the
quiet run does not show.

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|wants bought $|standards|fund cash|due/paid no_earner|due/paid laid_off|covered|
|--:|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1200/880/880/700 | 0/0/0/0, 1000 | 12/25/31/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/5 | 150+0 | 2/4/0/0 | 680 | 480/480 | 0/0 | 0 |
| 2 | 1200/1000/880/700 | 0/0/0/0, 1079 | 13/25/32/39 | 120/30/38 | 30/40 | 120/40/40/40 | 0/0/6 | 124+36 | 1/5/0/0 | 396 | 480/480 | 0/0 | 0 |
| 3 | 1200/1061/880/700 | 0/0/0/0, 1161 | 12/25/33/40 | 119/40/36 | 30/40 | 120/40/40/40 | 0/0/10 | 192+39 | 4/2/0/0 | 273 | 480/396.26 | 0/0 | 0 |
| 5 | 1200/1113/880/700 | 0/0/0/0, 1192 | 10/25/33/42 | 116/40/40 | 30/40 | 119/40/40/40 | 0/8/8 | 264+126 | 1/4/1/0 | 221 | 480/230.29 | 0/0 | 0 |
| 8 | 1200/1145/880/700 | 0/0/0/0, 1124 | 10/25/34/45 | 118/40/40 | 30/40 | 118/40/40/40 | 1/3/8 | 264+98 | 1/4/1/0 | 210 | 480/210.63 | 0/0 | 0 |
| 13 | 1170/1155/880/700 | 0/0/0/0, 1148 | 10/25/38/48 | 115/40/40 | 30/40 | 117/40/40/40 | 1/5/8 | 304+48 | 1/4/1/0 | 215 | 480/209.4 | 0/0 | 0 |
| 21 | 1200/1106/880/700 | 0/0/0/0, 1187 | 11/25/38/49 | 115/40/38 | 31/40 | 115/40/40/40 | 1/7/10 | 312+20 | 2/3/1/0 | 222 | 480/214.11 | 0/0 | 0 |
| 34 | 1200/1089/880/700 | 0/0/0/0, 1174 | 10/25/34/54 | 117/40/39 | 32/40 | 119/40/39/40 | 2/6/9 | 264+150 | 2/3/1/0 | 233 | 480/222.98 | 0/0 | 0 |

#### P4 on the fund with tiers: cycles, with layoffs from period 6

The world cycles in a band with no site stopping and the clinic holds at 32 units, unmet 3/3/16 at 34. The first
layoff in play is at period 6, in the clinic's pool at $11 an hour: 55 due for periods 6 to 11, 27.5 at 12, 0 at 13
(the two steps), paid at $23 to $27 of the 55 (43 to 49%). Class: cycles in a depressed band. **Control (taxed with
tiers, no fund):** no site stops, but the clinic ends at 2 units, unmet at 34 is 5/9/38, and employment first falls at
period 16. **What the fund changed:** the clinic holds 32 units rather than 2, care unmet is 16 rather than 38, food
and utility unmet are 3/3 rather than 5/9, and the first fall in employment comes at 5 (a layoff at 6) rather than 16.
*Second comparison (plain world with tiers):* the clinic at 3 units and unmet 4/7/37. A person sees: the care shortage
that ends at 38 unmet without the fund ends at 16, and a laid-off clinic worker is paid 43 to 49% of the half pay
owed.

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|wants bought $|standards|fund cash|due/paid no_earner|due/paid laid_off|covered|
|--:|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1200/880/880/1400 | 0/0/0/0, 908 | 11/25/31/38 | 116/40/36 | 40/40 | 120/40/40/40 | 0/0/6 | 60+0 | 2/4/0/0 | 666 | 480/480 | 0/0 | 0 |
| 2 | 1200/880/880/1400 | 0/0/0/0, 1128 | 12/25/32/38 | 116/40/36 | 40/40 | 116/40/40/40 | 0/0/6 | 62+0 | 4/2/0/0 | 474 | 480/480 | 0/0 | 0 |
| 3 | 1200/880/880/1400 | 0/0/0/0, 1355 | 12/25/33/39 | 120/40/36 | 40/40 | 120/40/40/40 | 0/0/10 | 192+48 | 4/2/0/0 | 247 | 480/474.29 | 0/0 | 0 |
| 5 | 1200/900/880/1400 | 0/0/0/0, 1311 | 10/25/31/41 | 109/40/26 | 40/40 | 113/40/30/40 | 0/7/22 | 256+146 | 5/0/1/0 | 261 | 480/253.17 | 0/0 | 0 |
| 8 | 1200/917/880/1400 | 0/0/0/0, 1307 | 12/25/30/44 | 105/40/27 | 40/40 | 105/40/27/40 | 3/6/21 | 248+173 | 5/0/1/0 | 256 | 480/205.18 | 105/44.88 | 2 |
| 13 | 1200/1041/880/1400 | 0/0/0/0, 1196 | 13/25/31/49 | 105/40/30 | 30/40 | 105/40/30/40 | 2/5/18 | 256+96 | 5/0/1/0 | 247 | 480/223.48 | 25/11.64 | 1 |
| 21 | 1200/1053/880/1400 | 0/0/0/0, 1206 | 13/25/29/57 | 111/40/33 | 30/40 | 111/40/35/40 | 2/4/15 | 240+112 | 5/0/1/0 | 234 | 480/241.07 | 0/0 | 0 |
| 34 | 1200/1068/880/1400 | 0/0/0/0, 1213 | 10/25/28/60 | 111/40/32 | 32/40 | 113/40/33/39 | 3/3/16 | 232+129 | 5/0/1/0 | 225 | 480/234.85 | 0/0 | 0 |

#### P5 on the fund with tiers: cycles with a thin reserve

The fund's rates fall to 1,125 points. In period 1 the fund holds $635, the first cut is at period 3 (312.34 of 480),
and it holds $159 to $192 in periods 4 to 34 and $173 at period 34 (the quiet run holds $233). Nobody is laid off in
play. The clinic makes 33 units, unmet 4/7/15 at period 34 (2/6/9 in the quiet run). `every_cut_is_in_proportion`
checks every short period. Class: cycles in a band, as the quiet run does. A person sees the supported household paid
a little less at period 34 ($22 of $60 a person, rather than $28).

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|wants bought $|standards|fund cash|due/paid no_earner|due/paid laid_off|covered|
|--:|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1200/880/880/1400 | 0/0/0/0, 1045 | 12/25/31/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/5 | 150+0 | 2/4/0/0 | 635 | 480/480 | 0/0 | 0 |
| 2 | 1200/1000/880/1400 | 0/0/0/0, 1207 | 13/25/32/39 | 120/30/38 | 30/40 | 120/40/40/40 | 0/0/7 | 155+36 | 1/5/0/0 | 312 | 480/480 | 0/0 | 0 |
| 3 | 1200/1064/880/1400 | 0/0/0/0, 1252 | 12/25/31/40 | 113/40/35 | 30/40 | 120/40/40/40 | 0/7/13 | 256+91 | 5/0/1/0 | 177 | 480/312.34 | 0/0 | 0 |
| 5 | 1200/1075/880/1400 | 0/0/0/0, 1237 | 12/25/31/42 | 112/40/34 | 30/40 | 114/40/36/40 | 0/4/14 | 256+164 | 5/0/1/0 | 192 | 480/170.1 | 0/0 | 0 |
| 8 | 1200/1087/880/1400 | 0/0/0/0, 1215 | 11/25/30/45 | 109/40/32 | 30/40 | 112/40/33/40 | 3/4/16 | 248+132 | 5/0/1/0 | 188 | 480/187.56 | 0/0 | 0 |
| 13 | 1200/1113/880/1400 | 0/0/0/0, 1233 | 10/25/29/50 | 112/40/35 | 30/40 | 112/40/35/40 | 4/3/13 | 240+196 | 3/2/1/0 | 165 | 480/168.27 | 0/0 | 0 |
| 21 | 1180/1107/880/1400 | 0/0/0/0, 1255 | 10/25/30/56 | 117/40/38 | 32/40 | 119/40/40/39 | 3/8/10 | 248+160 | 3/2/1/0 | 169 | 480/163.15 | 0/0 | 0 |
| 34 | 1200/1031/880/1400 | 0/0/0/0, 1289 | 10/25/23/64 | 114/40/33 | 34/40 | 119/40/35/40 | 4/7/15 | 192+318 | 5/0/1/0 | 173 | 480/178.42 | 0/0 | 0 |

### Form (b) after: the wage tax is ahead of comforts and luxuries

The same six runs of `World::benefits().with_tiers()` (quiet, P1 to P5) after rule O8 as amended on 21 November 2026:
the wage tax an account owes for the period is held back from every comfort and luxury it wants, so a want's room is the
account's cash less its needs still to buy less its tax. The tax is what the close will assess, read when the lists open
from the wages the period has booked by then (the wage accruals of the opening, before any buying, rule R6; the income
statement is only filled at the household close, so `HouseholdLists::open` is given the period's wage accruals and
applies each wage tax row of a household account to them: `tax_ahead`). A need keeps reserve 0. The money held back
stays in the account until the close collects it, and no record is added.

**Quiet: exactly still.** The cause named above is gone: each worker account's room for wants is $0, the public accounts
collect the 640 they assess in every period, the fund pays its 480 from what it collects and holds $960 at every close,
the owner holds $640, no want is bought, and every period equals the first
(`the_fund_with_tiers_is_still_the_wage_tax_is_ahead_of_the_wants`, by `assert_still`). The taxed world with tiers and
no fund (the control) is exactly still too.

#### Quiet on the fund with tiers (after): exactly still

Every period equals the first; the periods shown are those of the table of the same run before.

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|wants bought $|standards|fund cash|due/paid no_earner|due/paid laid_off|covered|
|--:|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1200/880/880/1400 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 0+0 | 0/6/0/0 | 960 | 480/480 | 0/0 | 0 |
| 2 | 1200/880/880/1400 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 0+0 | 0/6/0/0 | 960 | 480/480 | 0/0 | 0 |
| 3 | 1200/880/880/1400 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 0+0 | 0/6/0/0 | 960 | 480/480 | 0/0 | 0 |
| 5 | 1200/880/880/1400 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 0+0 | 0/6/0/0 | 960 | 480/480 | 0/0 | 0 |
| 8 | 1200/880/880/1400 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 0+0 | 0/6/0/0 | 960 | 480/480 | 0/0 | 0 |
| 13 | 1200/880/880/1400 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 0+0 | 0/6/0/0 | 960 | 480/480 | 0/0 | 0 |
| 21 | 1200/880/880/1400 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 0+0 | 0/6/0/0 | 960 | 480/480 | 0/0 | 0 |
| 34 | 1200/880/880/1400 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 0+0 | 0/6/0/0 | 960 | 480/480 | 0/0 | 0 |

Nothing else moved: the figures of form (a) (no market policy) and every run of `quiet.rs`, `pushed.rs` and `tiers.rs`
are as they were. The controls below are printed by the ignored dump and pinned by no test.

#### P1 on the fund with tiers (after): returns to its opening state

Before: the owner and the tax spent first, the clinic and the utility slid to 16 and 88 units, a layoff at 18, a cut
from period 3. After: no tax is spent on comforts, the owner buys only what its own freed money allows ($120 of comforts
and $200 of luxuries, every period), the fund never falls short (cut at none, $960 at every close), nobody is laid off
and every period equals the first, with the shop at $1,400 and unmet need 0/0/0 at 34. **Control (taxed with tiers, no
fund):** also returns to its opening state (outputs 120/40/40/40, unmet 0/0/0, the owner at $640), so the fund changes
nothing here.

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|wants bought $|standards|fund cash|due/paid no_earner|due/paid laid_off|covered|
|--:|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1200/880/880/1400 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 120+200 | 0/5/0/1 | 960 | 480/480 | 0/0 | 0 |
| 2 | 1200/880/880/1400 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 120+200 | 0/5/0/1 | 960 | 480/480 | 0/0 | 0 |
| 3 | 1200/880/880/1400 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 120+200 | 0/5/0/1 | 960 | 480/480 | 0/0 | 0 |
| 5 | 1200/880/880/1400 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 120+200 | 0/5/0/1 | 960 | 480/480 | 0/0 | 0 |
| 8 | 1200/880/880/1400 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 120+200 | 0/5/0/1 | 960 | 480/480 | 0/0 | 0 |
| 13 | 1200/880/880/1400 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 120+200 | 0/5/0/1 | 960 | 480/480 | 0/0 | 0 |
| 21 | 1200/880/880/1400 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 120+200 | 0/5/0/1 | 960 | 480/480 | 0/0 | 0 |
| 34 | 1200/880/880/1400 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 120+200 | 0/5/0/1 | 960 | 480/480 | 0/0 | 0 |

#### P2 on the fund with tiers (after): cycles in a depressed band

Before: the first cut at period 3, layoffs from 15, the clinic at 18 units, unmet 6/8/30. After: the reserve is no
longer spent on the tax-paid comforts of the first periods, so the fund holds $872 at period 3 and its first cut falls
at 9 (405.08 of 480 paid); layoffs in play start at 11 (two people of the clinic, 100 due), the clinic ends at 18 units
and the utility at 92, unmet at 34 is 6/8/30 as before, and the fund holds $279 (269 before). Class: a depressed band,
no site stopping. **Control (taxed with tiers, no fund):** a depressed band too, the clinic at 15 units, unmet 5/12/25,
the shop at $1,400, and employment first falls at period 7. The fund holds the clinic up by 3 units and keeps utility
unmet lower (8 against 12), at the price of care unmet (30 against 25); the first fall in employment comes at 10, not 7.

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|wants bought $|standards|fund cash|due/paid no_earner|due/paid laid_off|covered|
|--:|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1200/926/880/1400 | 0/0/0/0, 602 | 12/25/30/38 | 120/36/40 | 36/40 | 120/40/40/40 | 0/0/0 | 0+0 | 0/6/0/0 | 953 | 480/480 | 0/0 | 0 |
| 2 | 1200/998/880/1400 | 0/0/0/0, 533 | 12/25/29/38 | 120/36/37 | 32/40 | 120/40/40/40 | 0/0/3 | 0+0 | 2/4/0/0 | 928 | 480/480 | 0/0 | 0 |
| 3 | 1200/1084/880/1400 | 12/4/0/4, 487 | 11/25/28/38 | 117/36/36 | 28/40 | 120/40/37/40 | 0/0/4 | 0+0 | 1/5/0/0 | 872 | 480/480 | 0/0 | 0 |
| 5 | 1200/1303/880/1400 | 14/4/0/4, 416 | 10/25/28/38 | 116/36/36 | 20/40 | 116/40/36/40 | 0/0/7 | 81+0 | 1/5/0/0 | 727 | 480/480 | 0/0 | 0 |
| 8 | 1150/1760/880/1308 | 0/30/0/0, 426 | 10/26/29/38 | 106/36/33 | 0/39 | 111/40/33/40 | 0/7/8 | 28+0 | 1/5/0/0 | 405 | 480/480 | 0/0 | 0 |
| 13 | 1183/1760/182/1248 | 0/0/0/0, 1317 | 10/31/28/43 | 83/36/2 | 0/36 | 93/40/20/40 | 8/17/38 | 0+0 | 6/0/0/0 | 280 | 480/161.41 | 150/50.44 | 3 |
| 21 | 1200/1760/585/960 | 0/0/0/0, 1193 | 11/39/31/51 | 80/36/18 | 0/36 | 80/40/18/40 | 4/18/30 | 256+50 | 5/0/1/0 | 264 | 480/307.63 | 50/32.04 | 1 |
| 34 | 1200/1760/880/492 | 0/0/0/0, 1363 | 10/52/32/64 | 92/36/18 | 0/36 | 98/40/20/39 | 6/8/30 | 264+126 | 5/0/1/0 | 279 | 480/224.31 | 75/35.05 | 2 |

#### P3 on the fund with tiers (after): exactly still, the shop at half its cash

Before: the quiet run's band, with the shop at $700. After: every period equals the first and the first closes with the
opening cash, the shop holding $700 throughout (the push only moves the shop's opening cash), outputs 120/40/40/40 and
unmet 0/0/0 at 34, the fund at $960 (`p3_with_a_fund_and_tiers_is_still_with_the_shop_at_half_its_cash`). **Control
(taxed with tiers, no fund):** also exactly still, the shop at $700.

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|wants bought $|standards|fund cash|due/paid no_earner|due/paid laid_off|covered|
|--:|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1200/880/880/700 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 0+0 | 0/6/0/0 | 960 | 480/480 | 0/0 | 0 |
| 2 | 1200/880/880/700 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 0+0 | 0/6/0/0 | 960 | 480/480 | 0/0 | 0 |
| 3 | 1200/880/880/700 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 0+0 | 0/6/0/0 | 960 | 480/480 | 0/0 | 0 |
| 5 | 1200/880/880/700 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 0+0 | 0/6/0/0 | 960 | 480/480 | 0/0 | 0 |
| 8 | 1200/880/880/700 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 0+0 | 0/6/0/0 | 960 | 480/480 | 0/0 | 0 |
| 13 | 1200/880/880/700 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 0+0 | 0/6/0/0 | 960 | 480/480 | 0/0 | 0 |
| 21 | 1200/880/880/700 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 0+0 | 0/6/0/0 | 960 | 480/480 | 0/0 | 0 |
| 34 | 1200/880/880/700 | 0/0/0/0, 640 | 12/25/30/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/0 | 0+0 | 0/6/0/0 | 960 | 480/480 | 0/0 | 0 |

#### P4 on the fund with tiers (after): cycles, with no layoff in play

Before: layoffs from period 6, the clinic at 32 units, unmet 3/3/16, the fund at $225. After: the first cut falls at 4
(476.96 of 480 paid) and nobody is laid off in play; the clinic holds 39 units, unmet at 34 is 2/5/9 and the fund holds
$233, near the old quiet run's figures: raising the pay no longer sends the workers' tax into comforts. Class: cycles in
a band. **Control (taxed with tiers, no fund):** the clinic at 27 units, unmet 2/8/14, and employment first falls at
period 13 (it was 2 units, 5/9/38 and period 16 before). The fund holds the clinic up by 12 units, utility and care
unmet are lower (5 and 9 against 8 and 14, food 2 in both), and no one is laid off in play with it.

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|wants bought $|standards|fund cash|due/paid no_earner|due/paid laid_off|covered|
|--:|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1200/880/880/1400 | 0/0/14/0, 669 | 11/25/31/38 | 116/40/36 | 40/40 | 120/40/40/40 | 0/0/4 | 0+0 | 2/4/0/0 | 879 | 480/480 | 0/0 | 0 |
| 2 | 1200/882/880/1400 | 0/0/10/0, 841 | 12/25/32/38 | 116/40/36 | 40/40 | 116/40/40/40 | 0/0/4 | 0+0 | 2/4/0/0 | 694 | 480/480 | 0/0 | 0 |
| 3 | 1200/881/880/1400 | 0/0/0/0, 1130 | 11/25/33/38 | 116/40/36 | 40/40 | 120/40/40/40 | 0/0/4 | 0+0 | 2/4/0/0 | 476 | 480/480 | 0/0 | 0 |
| 5 | 1200/1098/880/1400 | 0/0/0/0, 1130 | 11/25/33/40 | 114/40/35 | 30/40 | 120/40/37/40 | 0/7/13 | 272+126 | 5/0/1/0 | 238 | 480/230.96 | 0/0 | 0 |
| 8 | 1200/1127/880/1400 | 0/0/0/0, 1150 | 10/25/34/43 | 114/40/38 | 30/40 | 116/40/38/40 | 0/8/9 | 231+86 | 2/4/0/0 | 217 | 480/228.4 | 0/0 | 0 |
| 13 | 1200/1102/880/1400 | 0/0/0/0, 1166 | 11/25/37/48 | 116/40/38 | 30/40 | 118/40/38/40 | 1/6/9 | 252+95 | 2/4/0/0 | 219 | 480/252.56 | 0/0 | 0 |
| 21 | 1200/1093/880/1400 | 0/0/0/0, 1188 | 10/25/37/50 | 113/40/38 | 32/40 | 114/40/38/40 | 1/8/10 | 304+83 | 2/3/1/0 | 222 | 480/230.16 | 0/0 | 0 |
| 34 | 1200/1085/880/1400 | 0/0/0/0, 1188 | 10/25/34/53 | 116/40/39 | 32/40 | 118/40/39/40 | 2/5/9 | 280+128 | 2/3/1/0 | 233 | 480/233.97 | 0/0 | 0 |

#### P5 on the fund with tiers (after): cycles with a thin reserve

Before: the first cut at 3, the clinic at 33 units, unmet 4/7/15, the fund at $173. After: the fund's rates fall to
1,125 points and, with the tax paid first, it keeps its reserve longer: the first cut falls at 5 (435.28 of 480 paid,
where it was 3), the clinic ends at 31 units, unmet at 34 is 4/5/15 and the fund holds $171. Nobody is laid off in play.
`every_cut_is_in_proportion` checks every short period of this run and of form (a)'s. Class: cycles in a band.

|p|cash U/F/C/S|cash wU/wF/wC/wS, O|price U/F/C/S|out U/F/C|stock F/S|hours|unmet F/U/C|wants bought $|standards|fund cash|due/paid no_earner|due/paid laid_off|covered|
|--:|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1200/880/880/1400 | 15/15/15/15, 700 | 12/25/31/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/1 | 30+0 | 1/5/0/0 | 840 | 480/480 | 0/0 | 0 |
| 2 | 1200/880/880/1400 | 32/20/20/20, 756 | 12/25/32/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/1 | 31+0 | 1/5/0/0 | 730 | 480/480 | 0/0 | 0 |
| 3 | 1200/880/880/1400 | 9/13/13/13, 895 | 12/25/33/38 | 120/40/40 | 40/40 | 120/40/40/40 | 0/0/1 | 32+0 | 1/5/0/0 | 635 | 480/480 | 0/0 | 0 |
| 5 | 1200/1000/880/1400 | 0/0/0/0, 1231 | 13/25/35/39 | 120/30/38 | 30/40 | 120/40/40/40 | 0/0/8 | 204+36 | 4/2/0/0 | 197 | 480/435.28 | 0/0 | 0 |
| 8 | 1200/1072/880/1400 | 0/0/0/0, 1258 | 12/25/32/42 | 114/40/36 | 30/40 | 115/40/36/40 | 0/4/12 | 264+149 | 3/2/1/0 | 180 | 480/182.73 | 0/0 | 0 |
| 13 | 1200/1058/880/1400 | 0/0/0/0, 1305 | 13/25/29/47 | 113/40/36 | 30/40 | 113/40/37/40 | 4/4/12 | 240+196 | 3/2/1/0 | 174 | 480/172.15 | 0/0 | 0 |
| 21 | 1200/1099/880/1400 | 0/0/0/0, 1264 | 11/25/27/55 | 113/40/37 | 30/40 | 117/40/37/40 | 3/8/10 | 182+210 | 3/3/0/0 | 166 | 480/163.71 | 0/0 | 0 |
| 34 | 1180/1093/880/1400 | 0/0/0/0, 1275 | 10/25/26/62 | 112/40/31 | 32/40 | 114/40/31/40 | 4/5/15 | 150+304 | 3/3/0/0 | 171 | 480/177.72 | 0/0 | 0 |

### What the fund changes

1. A fund of $960 (two periods) with a $480 benefit and no layoffs is exactly still in the taxed world with no market
   policy: the programs add no motion of their own (quiet).
2. The money the fund pays is the money it collects. A push that shrinks the taxes' base (every runaway above) shrinks
   the benefit with it: in form (a) the fund is first short at period 6 (P1, P5), 9 (P2) and 11 (P4) and pays 4 to 23%
   of its due by period 34; P3, which changes no tax base, is never cut.
3. The half pay after a layoff shows its two steps in every layoff of the record (50 for six periods, 25 in the
   seventh, nothing in the eighth; 55, 27.5 for the clinic at $11), but while the fund is short it is paid at a
   fraction (4 to 49%) of its due: a laid-off worker's income falls by nearly the whole wage, not by half, so the
   expectation that a layoff cuts a household's spending by about half for six and a half periods is not what the
   record shows, and the program would give it only to a fund that stays solvent (the rich fund of
   `a_layoff_is_paid_half_pay_for_six_and_a_half_periods`). The laid-off account's income, from the due/paid columns: a
   wage of $100 a person ($110 in the clinic) becomes half pay of $50 ($55) when the fund is solvent, and in the runs
   above it was paid $2 to $27 of that. The record does not give each account's purchases. In the tiers runs of the quiet run, P1 and P3 the worker
   accounts close every period at $0, so they buy what they receive and no more; in P2 (periods 3 to 8), P4 (periods
   1 and 2) and P5 (periods 1 to 3) of form (b) after the wage tax was ahead of comforts, a worker account closes a
   few periods with $1 to $32.
4. Layoffs in play are few and come after a site has begun to fail, when it asks staffing for fewer hours: none in P1
   and P3 of form (a), and at periods 20 (P5), 27 (P4) and 28 (P2) elsewhere in it; under tiers at 6 (P4), 15 (P2) and
   18 (P1), none in the quiet run, P3 and P5. After the wage tax was ahead of comforts, under tiers: at 11 (P2), and
   none in the quiet run, P1, P3, P4 and P5.
5. A short fund is cut in proportion: every claim of a rank is paid the same share of its due, a zero claim gets
   nothing, and the paid amounts add to the budget (`every_cut_is_in_proportion`), so a laid-off cohort and the
   no-earner household lose alike.
6. Under tiers no run of the fund's world returns to its opening state, and none stops a site: the timing of the tax
   against the purchase of wants (the taxed world with tiers and no fund does the same) keeps the quiet run off a
   fixed point, and the fund, holding $108 to $339 after period 3, pays its household $14 to $38 a person rather than
   $60. Without tiers three of four pushes (P1, P2, P4) run away, as they do on the taxed world with no fund, and P5, which
   has no control without a fund, runs away too;
   with tiers the same pushes cycle in a band (P2, P4, P5) or slide (P1). Against the no-fund control the fund holds
   the clinic up in P2, P3 and P4 (18, 39 and 32 units at period 34, against 9, 4 and 2) and barely in P1 (16 against
   14); in P2 under form (a) it does not help the farm (9 units against 18). **After the wage tax was ahead of comforts
   this item no longer holds for form (b):** the quiet run, P1 and P3 are exactly still or return to their opening
   state (as do their controls); P2, P4 and P5 cycle in a band with no site stopping, and the fund holds the clinic up
   in P2 and P4 (18 and 39 units against 15 and 27).
7. The class of each end, beside the same push on the same opening with no fund (the controls). Form (a): P1 runs
   away, and so does its control (the clinic stops 2 periods later with the fund); P2 runs away, and so does its control
   (clinic 1 period later); P3 settles at once, and so does its control; P4 runs away, and so does its control (farm 2
   periods earlier, clinic 2 later). The fund moves each runaway's timing by a few periods and changes no class. Form
   (b): P1 slides, and so does its control (clinic 16 against 14 units); P2 cycles in a depressed band, its control is
   depressed too (clinic 18 against 9); P3 cycles in the quiet run's band, its control slides (clinic 39 against 4);
   P4 cycles with the clinic at 32 units, its control ends the clinic at 2. Only under tiers does the fund change what
   the clinic ends at by more than a few units. The plain-world runs (no tax, a different opening) are a second
   comparison only: there P1 with tiers returns to its opening state and P3 with tiers is exactly still, which no
   world with the tax does, with or without a fund.
