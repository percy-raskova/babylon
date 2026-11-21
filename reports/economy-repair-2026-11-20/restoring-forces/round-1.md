# What brings the small economy back after a push

Measured 21 November 2026 in the small world: four workplaces (utility, farm, clinic, shop), one place, 40
people, 240 hours of work a period. Two worlds: "plain" (no taxes) and "fund" (a 20% wage tax, a 20% tax on
profits, and a benefits fund). Every run lasts 100 periods. Every figure comes from a run's summary or its
rows; where an agent's account differs, the rows are used.

The pushes: **P2** is a poor harvest (the farm makes 9 food a batch, not 10). **P4** is higher pay at the
clinic ($11 an hour, not $10). **P5** is a cut in the fund's tax rates (fund world only). **P1** and **P3**
are pushes the economy already shrugs off, and **quiet** is no push at all. Unmet is food/utility/care, out of
40.

## 1. The answer

- **No single rule brings both worlds back.** The best is **f at a half share** (a workplace with spare cash
  plans a little above what its buyers paid for). It mends the plain world and harms the fund world.
- **Only one measured set brings P2 and P4 near full work in both worlds: f (half share) + a + d2.** a lets
  idle workers be lent to another workplace, and d2 has owners top up a workplace that is short of cash for
  wages and inputs. Both P4s and fund P5 hold 240 hours over periods 81-100. Both P2s come close but are still
  swinging and rising at p100: plain P2 209-240 (mean 227), fund P2 226-240 (mean 238). Neither P2 is shown to
  settle. No workplace closes, the quiet runs stay still, and no money is lost.
- **Build order: f, then d2, then a.** f pushes output back up. d2 is needed in the fund world: f with a but
  without d2 collapses fund P2 and fund P4. Whether a is needed was never tested (f + d2 was not run).
- **Cost: the owner.** In plain P2, plain P4 and fund P2 the owner goes without most or all of its care, and
  in both P2s also 2-5 food and 5-10 utility. The care price falls to $20-25, and the owner's cash moves into
  the farm's till, where it stays. Pay rises: the plain P2 wage bill over the run is $233,930 against
  $153,080.

## 2. Where we start

The targets are the balanced states the arithmetic allows with prices and pay unchanged: 240 hours in every
run. Unmet care is 4.44 in both P2s, 1.33 in plain P4, 1.07 in fund P4 and 4 in fund P5. Food and utility: 0.

| world | run | class | settles | hours p34 | hours p100 | mean p81-100 | unmet p34 | unmet p100 | what happened |
| --- | --- | --- | --: | --: | --: | --: | --- | --- | --- |
| plain | P2 | runs away | - | 156 | 116 | 124.2 | 5/18/33 | 16/22/40 | clinic closes from p74 |
| plain | P4 | runs away | - | 179 | 129 | 115.55 | 4/7/37 | 12/21/40 | clinic closes from p38 |
| fund | P2 | cycles | 100 | 197 | 177 | 175.7 | 6/8/30 | 14/14/31 | band 171-182 |
| fund | P4 | cycles | - | 237 | 238 | 236.45 | 2/5/9 | 2/4/8 | band 234-239, near target |
| fund | P5 | slides | - | 225 | 183 | 196.95 | 4/5/15 | 7/14/30 | falls 1.29 hours a period |

Both quiet runs, both P1s and both P3s stay exactly still at 240 hours with nothing unmet. The 34-period
record had called plain P2, plain P4 and fund P5 steady low bands; run to 100 periods, all three keep falling.

**Two diagnostics**, each meant to remove the cause the written diagnosis named:

- *P4 with the clinic opening at $920* (one period's wages and inputs) runs away faster: 153 hours at p34, 15
  at p100; the clinic closes from p18, the farm from p52, the shop from p53. In p1, 41 care is wanted against
  40 made; the clinic raises its price to $31, demand falls to 37, and it plans 37 from then on. Demand above
  the plan raises the price; demand below it cuts the plan. So output can only ratchet down.
- *P2 with the farm's workforce at 7 instead of 5* also runs away: 35 hours at p34, 15 at p100; the farm
  closes from p9, the clinic and shop from p10. The farm pays 50-56 hours a period but its cash buys power for
  3 batches, so 20 to 55 hours a period are paid idle and its cash falls from $1,052 at p6 to $9 at p9.

**The diagnosis did not hold.** Its account of how each slump starts matches the rows. But both of its
proposed cures fail. In both slumps, the binding cause is a workplace that has only one period's cash for
wages and inputs, together with plans that only ever ratchet down.

## 3. Each rule alone

Tables give class, the period it settles in, hours and unmet at p34/p100, and the baseline. "Closes" means it
makes nothing from then on. Hours are paid hours, idle ones included. **Still moving** marks a run that swings
more than 2 hours over p81-100 with a rising slope and never settles; summarize.py labels such runs "settles"
by a fault (see Checked).

### a. Workers who can change jobs (lent for one period at a time)

A workplace that wants more hours than its own people can give borrows idle hours from other workplaces in the
place, at its own wage.

| world | run | class | settles | hours 34/100 | unmet 34 | unmet 100 | base hours 34/100 | base class |
| --- | --- | --- | --: | --- | --- | --- | --- | --- |
| plain | P2 | runs away | - | 120/106 | 40/10/12 | 40/10/14 | 156/116 | runs away |
| plain | P4 | runs away | 73 | 240/118 | 0/0/10 | 40/10/14 | 179/129 | runs away |
| fund | P2 | runs away | - | 120/116 | 40/8/10 | 40/8/11 | 197/177 | cycles |
| fund | P4 | settles elsewhere | - | 240/240 | 0/6/12 | 2/8/12 | 237/238 | cycles |
| fund | P5 | runs away | - | 240/48 | 2/5/12 | 40/7/40 | 225/183 | slides |

- **What a person sees:** spare clinic staff go to help on the farm. But the farm cannot buy the power to use
  them, so it pays them to stand idle. In both P2s the farm closes from p16 and the shop from p17, and nobody
  has food. In plain P4 and fund P5 the town looks fully at work for a while (until about p38 and p55), and
  then the farm goes under.
- **Cost and who pays:** the farm pays. It wants 50 to 80 hours and can pay for about 40. Its cash at p100 is
  $3 in plain P2 and $5 in plain P4 (baseline $827 and $1,170). Fund P4 keeps its hours (mean 239.70), but
  care unmet is 11.28 above target against 7.68 in the baseline. So it is worse for people.
- **Quiet runs:** still. Nothing is lent in quiet, P1 or P3.

### d2. Owners put in working cash

Before each period, a workplace with less cash than its coming wages and inputs gets the gap from its owner.

| world | run | class | settles | hours 34/100 | unmet 34 | unmet 100 | base hours 34/100 | base class |
| --- | --- | --- | --: | --- | --- | --- | --- | --- |
| plain | P2 | slides | - | 135/150 | 11/28/38 | 13/21/30 | 156/116 | runs away |
| plain | P4 | slides | - | 192/158 | 4/12/32 | 11/16/32 | 179/129 | runs away |
| fund | P2 | runs away | - | 191/107 | 5/7/33 | 19/18/38 | 197/177 | cycles |
| fund | P4 | slides | - | 214/167 | 0/7/14 | 7/15/29 | 237/238 | cycles |
| fund | P5 | slides | - | 199/156 | 8/13/39 | 10/26/31 | 225/183 | slides |

- **What a person sees:** a workplace about to run short is topped up by its owner, and the economies still
  sink. In plain P4 the owner's $40 is $40 it no longer spends on care. The clinic is again one buyer short
  and shrinks at once.
- **Cost and who pays:** the owner pays $6,984.57 in plain P2, $4,976.88 in plain P4, $1,278.96 in fund P2,
  $695.90 in fund P4 and $2,023.69 in fund P5. Most of it goes to the farm ($6,406.90 in plain P2), which
  plans hours it cannot staff, so the money sits there unused. None of it is ever paid back.
- The summary calls plain P2 a slide (-0.80 a period); the agent read a noisy band. p81-100 range 132-160.
- **Quiet runs:** still. No top-up is ever asked for.

### f. A workplace with spare cash plans above what was paid for

Run at three shares: 10%, 25% and 50%. f-off (share 0) reproduces the baseline exactly.

| world | run | f-10: class, hours 34/100, unmet 100 | f-25 | f-50 | base |
| --- | --- | --- | --- | --- | --- |
| plain | P2 | runs away, 151/127, 11/22/40 | runs away, 150/144, 8/20/40 | **cycles (98)**, 231/230, 3/9/10 | runs away, 156/116 |
| plain | P4 | runs away, 188/115, 14/17/40 | slides, 240/196, 2/22/38 | **settles elsewhere (88)**, 240/240, 0/0/4 | runs away, 179/129 |
| fund | P2 | runs away, 204/32, 40/20/40 | runs away, 193/117, 40/7/8 | runs away, 183/32, 40/20/40 | cycles, 197/177 |
| fund | P4 | slides, 231/208, 4/10/30 | cycles, 239/238, 0/0/5 | slides, 185/184, 9/18/31 | cycles, 237/238 |
| fund | P5 | slides, 235/196, 6/11/32 | cycles, 240/188, 8/18/32 | slides, 237/226, 3/6/10 | slides, 225/183 |

- **What a person sees (half share):** a clinic or utility with money in the bank keeps a few more staff on
  than paying customers justify. In the plain world the town stays at work: plain P2 averages 231.3 hours over
  p81-100 (baseline 124.2), and plain P4 holds 240. In the fund world's poor harvest, people buy more food
  than the short-handed farm can grow. The farm's stock runs out, the shop spends all its cash at a shortage
  price and closes (from p65), and the farm follows (from p66).
- **Cost and who pays:** each workplace spends its own spare cash on wages and power. In plain P2 at a half
  share the clinic's price falls to $21-23 and the owner's cash to $172-300 over p81-100 (baseline
  $1,823-2,037). The owner goes without all 10 of its care.
- **The share matters, and not in a steady way.** Plain P4 runs away at 10%, slides at 25% and holds at 50%.
  Fund P4 holds only at 25%. No single share is safe on both worlds.
- **Quiet runs:** still at every share.

### e. A goods price falls when goods go unsold

Two readings were run: e as written, where everything on the shelf counts as offered, and e-kept, where a
producer's own buffer stock does not count.

| world | run | e: class, settles, hours 34/100, unmet 100 | e-kept: class, settles, hours 34/100, unmet 100 | base hours 34/100 |
| --- | --- | --- | --- | --- |
| plain | quiet | **settles elsewhere**, 11, 240/240, 0/0/6 | returns to opening, 1, 240/240, 0/0/0 | 240/240 |
| plain | P1 | **slides**, -, 180/122, 10/22/33 | returns to opening, 1, 240/240, 0/0/0 | 240/240 |
| plain | P2 | runs away, -, 137/30, 40/19/40 | runs away, -, 145/93, 17/28/40 | 156/116 |
| plain | P4 | runs away, -, 135/119, 9/16/40 | **settles elsewhere**, 18, 240/240, 0/0/4 | 179/129 |
| fund | quiet | **still moving**, -, 168/186, 5/7/28 | returns to opening, 1, 240/240, 0/0/0 | 240/240 |
| fund | P2 | slides, -, 194/170, 7/17/29 | runs away, -, 148/144, 10/15/40 | 197/177 |
| fund | P4 | runs away, -, 145/33, 40/8/40 | slides, -, 208/185, 4/17/28 | 237/238 |
| fund | P5 | cycles, -, 174/185, 7/17/28 | **cycles**, 99, 237/238, 4/5/8 | 225/183 |

(e as written also moves both P3s: plain P3 settles elsewhere with 6 care unmet, and fund P3 runs away to
119.)

- **What a person sees:** as written, even an untouched town cuts prices. The farm always holds a buffer, so
  it always "has unsold food". It marks its price below cost and drains its own cash, and the fund-world quiet
  town slides into a slump of its own. In e-kept the quiet towns stay still. The higher-pay push in the plain
  world then recovers fully: the utility cuts its price a dollar and plans for the buyers who can now afford
  it.
- **Cost and who pays:** in e-kept plain P4, the utility's buyers pay $11,874 less over the run. That money is
  the utility's earnings, and so the owner's income. Care unmet settles 2.07 above target.
- **Quiet runs:** e moves both. e-kept keeps both still.

### d1. Spare cash goes back to the owner

A workplace pays its owner any cash above 1.5 periods of its wages and inputs.

| world | run | class | settles | hours 34/100 | unmet 34 | unmet 100 | base hours 34/100 |
| --- | --- | --- | --: | --- | --- | --- | --- |
| plain | quiet | **runs away** | 96 | 190/40 | 5/17/30 | 40/15/40 | 240/240 |
| plain | P2 | settles elsewhere | 77 | 181/180 | 12/22/30 | 11/21/30 | 156/116 |
| plain | P3 | runs away | - | 149/30 | 5/15/40 | 40/10/40 | 240/240 |
| plain | P4 | runs away | - | 195/40 | 3/16/28 | 40/15/40 | 179/129 |
| fund | quiet | **runs away** | 97 | 187/92 | 8/20/32 | 40/8/24 | 240/240 |
| fund | P2 | runs away | - | 40/40 | 40/12/40 | 40/12/40 | 197/177 |
| fund | P3 | runs away | - | 216/88 | 3/8/20 | 40/8/30 | 240/240 |
| fund | P4 | still moving | - | 184/183 | 8/13/31 | 11/19/30 | 237/238 |
| fund | P5 | runs away | - | 190/89 | 8/12/31 | 40/8/33 | 225/183 |

- **What a person sees:** at the end of period 1 the shop's owner takes out $800 the shop was not using ($100
  in both P3 runs) and goes shopping for comforts. The shelves hold only enough food for everyone's needs, so
  the price jumps. Workers spend all their pay on food and go without power and care, and the town shrinks
  whatever the push.
- **Cost and who pays:** $800 (both P1s, the shop's p1 payout only) to $2,685 (fund P5) moves from the
  workplaces to the owner.
- **Quiet runs:** neither stays still; where they "settle" (p96, p97) it is at their collapsed level. Both P1s
  end at 240 hours, but the $800 payout makes them "settles near target", not "returns to opening" as the
  agent wrote.

### g. The benefits fund opens with a deeper reserve (fund world only)

The fund opens holding 4 or 6 periods of benefit payments instead of 2. The plain world is unchanged.

| run | g-4: class, hours 34/100, unmet 100 | g-6: class, hours 34/100, unmet 100 | base |
| --- | --- | --- | --- |
| fund P2 | slides, 183/172, 17/8/32 | slides, 200/166, 16/20/32 | cycles, 197/177, 14/14/31 |
| fund P4 | slides, 186/172, 11/16/29 | cycles, 177/179, 9/20/32 | cycles, 237/238, 2/4/8 |
| fund P5 | runs away, 187/124, 40/8/10 | still moving, 188/195, 10/19/30 | slides, 225/183, 7/14/30 |

- **What a person sees:** people with no earner are paid in full a few periods longer, but the money only bids
  up short food. Workers drop care, the clinic shrinks to about 16 units, and every pushed fund run ends
  lower.
- **Cost and who pays:** the fund spends all the extra reserve: $1,522.93 to $1,658.02 net at g-4, and
  $2,449.54 to $2,588.36 at g-6. In this prototype the extra reserve is new money created at the opening.
- **Quiet runs:** still.

### c. A service's price counts its idle wages

A service counts the hours it paid for and could not use as part of its cost, and does not cut its price while
it earns less than that cost. Two forms were run: c (the full cost both blocks a price cut and drives a price
rise) and c-down (it only blocks a cut).

| world | run | c: class, hours 34/100, unmet 100 | c-down: class, hours 34/100, unmet 100 | base |
| --- | --- | --- | --- | --- |
| plain | P2 | slides, 141/136, 15/19/35 | slides, 144/131, 13/24/34 | runs away, 156/116 |
| plain | P4 | slides, 147/136, 11/24/34 | runs away, 143/20, 40/20/40 | runs away, 179/129 |
| fund | P2 | still moving, 168/129, 24/8/30 | slides, 186/167, 17/9/32 | cycles, 197/177 |
| fund | P4 | runs away, 198/120, 40/8/13 | slides, 192/124, 40/4/12 | cycles, 237/238 |
| fund | P5 | slides, 231/186, 7/9/29 | slides, 231/180, 6/16/29 | slides, 225/183 |

- **What a person sees:** in a slump the clinic and utility stop cutting prices and often raise them; the
  clinic survives but serves fewer. In fund P4 the shop closes from p78 and the farm from p80.
- **Cost and who pays:** buyers pay more and buy less. The wage bill over the run falls against the baseline:
  $26,930 less in fund P2 and $56,510 less in fund P4.
- **Quiet runs:** still in both forms.

### b. Pay that rises 2% a period when a workplace cannot find staff

| world | run | class | settles | hours 34/100 | unmet 34 | unmet 100 | base hours 34/100 | base class |
| --- | --- | --- | --: | --- | --- | --- | --- | --- |
| plain | P2 | slides | - | 174/161 | 4/16/33 | 16/17/30 | 156/116 | runs away |
| plain | P4 | runs away | - | 188/108 | 3/2/29 | 15/17/40 | 179/129 | runs away |
| fund | P2 | runs away | - | 143/131 | 10/20/40 | 20/21/40 | 197/177 | cycles |
| fund | P4 | runs away | 96 | 161/116 | 40/4/15 | 40/8/12 | 237/238 | cycles |
| fund | P5 | runs away | 95 | 186/108 | 5/7/26 | 40/8/15 | 225/183 | slides |

- **What a person sees:** the farm (and in fund P4 and P5 the shop) keeps raising pay to find people who are
  not there, and nobody comes. Its food price rises, and the shop's climbs much faster. In the fund world the
  farm runs out of cash and closes (fund P4 from p30, fund P5 from p56), and everyone goes without food.
- **Cost and who pays:** the premium above the opening wage is $5,010.19 (fund P4) to $18,226.78 (fund P5).
  The farm pays it, and in fund P4 and P5 the shop too (7 and 13 raises); the sum covers every employer. Plain
  P2 looks better (mean 170.55 against 124.2), but the gain comes through higher prices that pay the owner.
- **Quiet runs:** still. The rule never acts in them.

## 4. The rules together

Each cell gives class, the period it settles in, hours at p34/p100, and unmet at p100. All four sets keep both
quiet runs, both P1s and both P3s exactly still, and no money is lost.

| world | run | 1: f-50 + e-kept | 2: a + d2 | 3: f-50 + a + d2 | 4: f-50 + a | base |
| --- | --- | --- | --- | --- | --- | --- |
| plain | P2 | runs away, 203/138, 12/25/40 | slides, 232/121, 17/16/37 | still moving, 240/240, 4/8/10 | **cycles**, 240/240, 1/10/10 | runs away, 156/116 |
| plain | P4 | settles elsewhere (46), 240/240, 0/0/3 | still moving, 173/123, 15/20/30 | settles elsewhere, 240/240, 0/0/10 | settles elsewhere (88), 240/240, 0/0/4 | runs away, 179/129 |
| fund | P2 | runs away, 188/117, 40/8/9 | slides, 240/185, 6/11/29 | **still moving**, 240/240, 3/8/9 | runs away, 184/32, 40/20/40 | cycles, 197/177 |
| fund | P4 | still moving, 197/194, 6/15/30 | cycles, 240/240, 0/8/14 | **settles near target (17)**, 240/240, 0/0/1 | runs away, 163/35, 40/19/40 | cycles, 237/238 |
| fund | P5 | slides, 231/179, 8/4/38 | slides, 230/161, 9/18/32 | **settles near target (9)**, 240/240, 0/0/4 | settles elsewhere, 240/240, 3/8/8 | slides, 225/183 |

Hours over p81-100 for set 3: plain P2 mean 227.15 (209-240, slope +1.16), fund P2 237.80 (226-240, +0.49),
and 240 in plain P4, fund P4 and fund P5. Distance from the unmet target (food/utility/care): plain P2
2.95/8.05/7.51, plain P4 0/3.70/8.52, fund P2 3.15/6.60/5.71, fund P4 0/0/0.03, fund P5 0/0/0.50.

**What the rules do to each other:**

- *f + e-kept:* e undoes f in P2. The shop cuts its food price while food is really short, because buyers who
  cannot pay are read as goods left unsold. The farm's stock sells out, and the plain P2 clinic closes from
  p63 (f-50 alone held 228-234). In P4 they add nothing to each other.
- *a + d2:* they help each other only for a while. With the owner's cash, the farm can pay for borrowed hours,
  and fund P2 holds 240 to about p40. But the farm's plan keeps asking for more hours than it can use, and the
  owner keeps paying: $17,049.09 in plain P2 and $12,653.07 in plain P4, nearly all of it to the farm.
- *f + a + d2:* each covers another's failure. f supplies the push upward. a gives the farm the hands that f's
  extra food demand needs, which removes f's fund P2 collapse. d2 refills workplaces that f's extra staff and
  late power deliveries drain. Top-ups fall to $76 (fund P4) to $1,408.65 (plain P2). But the care price falls
  to $20-23 (both P2s) and $22-25 (plain P4), against a target of $30. Over p81-100 the owner's cash is
  $248-378 in plain P2 and $188-270 in fund P2; in the baseline it was $1,823-2,037 and $1,935-2,175. The
  owner goes without 10 of 10 care in plain P2, 7-10 in plain P4 and 8 of 8 in fund P2. (The agent's $230-370
  and $34-224 are not the p81-100 figures; fund P2's low over the run is $3.26.) Late in the run workplaces
  fall below one period of outlay (plain P2 utility at -$121 at p95), so the top-ups never stop.
- *f + a without d2:* the best plain world measured (plain P2 averages 239.55 hours), but fund P2 and fund P4
  collapse: the clinic, drained by paid idle hours, closes from p24 and p28, and the farm and shop follow.
  Nothing refills cash in the taxed world, so d2 is needed there.

## 5. What each recommended rule needs to become real

- **f.** *Remember:* the share and a cash reserve per workplace as a policy row, not the spike's
  `SPIKE_F_SHARE` variable in `recurring/firms.rs` (`reserve_share`, `extend_from_reserve`). *Record:* the
  extension on each plan's record (the spike adds `reserve_plans`). Unpaid demand must count want tiers, and
  the utility must see the clinic's extension in the same period. *The player sees:* a workplace keeping staff
  on through a slump while it has money, and a falling care price.
- **d2.** *Remember:* a policy row (owner, workplace, periods of outlay), capped at the hours the workplace
  can staff, plus a way to pay capital back (d1 failed at that alone). *Record:* the capital contribution
  receipt; the spike orders it in the harness (`order_working_cash`, `tests/small_world/support.rs`). *The
  player sees:* owners putting money into their businesses and spending less.
- **a.** *Remember:* people away and pay terms per (home, host) pair. *Record:* a lending receipt per pair and
  period, and a pause in the layoff record; the spike never lends a laid-off person on half pay, and lives
  only in the harness (`lend_hours`, `lent_attendance`). It needs place and distance, and a host's request
  capped at what it can pay. *The player sees:* workers moving between workplaces in their town.

## 6. What NOT to add

- **b, pay that moves:** it makes every fund run worse (fund P4 runs away to 116 hours against 238). Its one
  better run, plain P2, comes through prices that pay the owner while every worker household goes without.
- **d1, spare cash to the owner:** it moves both quiet runs into collapse (40 and 92 hours at p100) and turns
  five runs that hold in the baseline (both quiets, both P3s, fund P2) into runaways.
- **g, a deeper fund reserve:** it lowers every pushed fund run (fund P4 mean 178.80 at g-4 against 236.45)
  and creates money at the opening.
- **c, idle wages in the price:** it wrecks fund P4 (shop closes p78, farm p80). Its plain-world gain is a
  clinic that survives by selling 4-7 care a period at a higher price.
- **e as written:** it moves both quiet runs. **e-kept** is only safe alone. With f it undoes f's plain P2
  recovery (set 1), so it should not join the recommended set.
- **a or d2 alone:** a makes every slump it touches worse, and d2 only slows the fall. Each is useful only
  alongside f.

## 7. What is still unexplained, and what was not measured

- **Whether a is needed.** f + d2 without a was never run. That a is needed is inferred only from f's fund P2
  failure (a farm short of hands); no run shows it.
- **Why f is so sensitive to its share.** Results do not improve steadily with the share. The agent's guess is
  whole-unit rounding plus the utility planning a period late; that was not tested.
- **Whether set 3 rests on luck.** Only share 50 was combined, and only set 1 had a check that its merge
  reproduces each rule exactly. Sets 2, 3 and 4 had no such check.
- **The owner's lost care.** In set 3 the owner's money becomes cash the farm never pays back. A top-up that
  is repaid, or one capped at the hours the farm can staff, was not measured.
- **Not run:** the pushes without want tiers, other values of each rule's setting except f's three shares and
  g's two reserves, and any period beyond 100. Both P2s under set 3 were still swinging and rising at p100;
  runs well past period 100 are needed to know whether they settle at 240.
- **What a country could do differently.** Here there are four workplaces, one place, one owner and one seller
  of power. In a country lent workers travel, owners top up from different purses, a farm short of power can
  buy elsewhere, and a shortage spreads over many shops (here the shop restocks food at $83-87 against a
  $49-50 price). At the national opening almost every workplace holds one period of cash, so f stays silent
  until cash builds up.

## Checked

- d1: returns run $800 (both P1s) to $2,685 (fund P5), not $2,676-2,685; the shop pays $100 at p1 in both P3s.
- b: the shop also raised pay in fund P4 (7 times) and fund P5 (13); the premium is not the farm's alone.
- Set 3 plain P2 (209-240) and fund P2 (226-240) are reclassed "still moving"; the headline and sections 1 and
  7 claim full work only for both P4s and fund P5.
- summarize.py labels a swing over 2 hours with slope above +0.1 "settles". Also reclassed "still moving": c
  fund P2, d1 fund P4, e fund quiet, g-6 fund P5, set 1 fund P4, set 2 plain P4.
- Set 3 cost: added the owner's unmet food and utility, and workplaces below one period of outlay.
- Section 6, d1: five runs that hold in the baseline become runaways, not six.
- No prototype was dishonest: each matches its stated rule and conserves money; no numbers are struck.
