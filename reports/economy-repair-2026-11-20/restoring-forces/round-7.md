# Restoring forces, round seven: a bank in the top-ups' place, and a cap on orders

**Corrected by round 7b.** This record says that credit and the spare-money rule carry the test economy together
(sections 1 and 8). Round 7b put the bank on the bench as the design words it and found otherwise: what carried it was
the owners' own money, which is never repaid. A bank that is repaid does not do the same. See `round-7b.md`, sections 1
and 11.

Measured 2026-11-22 on the small test economy with two of everything, in both worlds (no taxes; taxes and a national
benefits fund), at both sets of figures, for 200 and for 400 periods. Every rule is a throwaway prototype behind a
switch, on the branch `spike/r7-all`. Two readers checked the round, one from the rows and one from the code. Every
count below was made again from the raw rows by a script of the lead's, unless the text says whose it is. A pushed run
is one of 17: every push but the three mild ones of each world, which are the owners needing half as much (P1), the shop
opening with half its cash (P3) and more mouths in the owners' household (P7). A set holds 25 runs: the 17, the six mild
ones and the two quiet runs.

## 1. The answer

- **The bank as this round built it is about as bad as no credit at all,** and far worse than the owners' top-ups whose
  place it took. A workplace stops for good in 11 of 17 pushed runs at the small figures (11 at 400 periods) and in 5
  and 9 at the national. With no credit at all the counts are 9, 9, 5 and 11. Under the top-ups no workplace stops in
  any run.
- **That is not yet a verdict on the design's bank.** Two things in the prototype did the damage, and neither is in the
  design's words. First, the brief had a business repay out of what it would have paid its owner. The design says it
  repays "from its sales". A business with a loss on its books declares no payout, so it repaid nothing whatever cash it
  held, and after three closes the bank took it. All 67 first takings at the small figures were of businesses that held
  at least their debt in cash. Second, the bank went on lending to the businesses it had taken and wrote those loans off
  again. That used up its capital. At the small figures the bank's cash reaches $0 in 12 of a set's 25 runs, and those
  are the 12 runs in which a workplace stops: the 11 pushed runs above and 1 mild one.
- **Money is exact.** In every period of every run of all 24 sets with the bank, the money in all accounts equals base
  money plus the principal outstanding. A loan as new money (A8) can be built as it is.
- **The bound by last sales is the clause that matters most at the small figures.** Without it a workplace stops in 4
  and 8 runs, where the bank as built has 11 and 11. It is also the only form in which a workplace that had stopped
  starts again. As designed the bound shuts a stopped workplace out of credit for good. What brings such a workplace
  back in the design is its fourth part, which is not on the bench.
- **The cap on orders does what it was built for, and no more.** With it a supplier is no longer staffed for orders that
  the buyer's people cannot work. In the taxed returning harvest the utility's top-up, $60 in 195 of 200 periods, stops
  altogether. Over the pushed runs hours are neither better nor worse.
- **Nothing comes back after a shock that ends** on both copies. The harvest that fails on one copy passes the design's
  test in the taxed world wherever there is no credit, with the farm's stock nearly gone, and fails it under the top-ups
  (section 7).
- **Credit and the spare-money rule carry the bench together; plans down the chain do not** (section 8). With both
  present no workplace stops, and plans down the chain add less than a hundredth to the hours. So they are not built
  now.

## 2. What was on the bench

- **The base** is round six's best set: the engine's own price rules, the spare-money rule as it is built (A6), plans
  down the chain (the prototype of A5), lent hands, the owners' top-ups, and buyers bound to the sellers of their own
  copy. The round's first step reproduced round six's rows byte for byte, at 200 and at 400 periods and at both sets of
  figures.
- **Step B, the bank, in the top-ups' place.** One bank for the place. It opens with $2,400 of base money and belongs to
  the two owners' households in halves. A business short of money for its planned wages, inputs and restocking asks at
  the opening of a period. The loan is given when the plan's receipts cover its cost and one period's interest. All
  principal stays within ten times the bank's cash, and one borrower's principal within its sales of the period before.
  Interest is 60 hundredths of a percent a period, fixed. Repayment came out of the payout the business declared
  (section 4). A business that paid nothing at three closes running was taken: its debt written off against the bank's
  cash, its payouts going to the bank from then on. Each clause had a switch that takes it away.
- **Step H, the cap on orders.** Plans down the chain count a business buyer's plan in full at its supplier, even past
  what the buyer's people can work. With the cap a buyer's plan counts at its supplier only as far as the buyer's own
  people can work it. The buyer's own plan is not changed.

## 3. The bank against the top-ups

Runs of 17 in which a workplace stops for good:

| Set | Small, 200 | Small, 400 | National, 200 | National, 400 |
| --- | --- | --- | --- | --- |
| Owners' top-ups (round six's best set) | 0 | 0 | 0 | 0 |
| No credit at all | 9 | 9 | 5 | 11 |
| The bank | 11 | 11 | 5 | 9 |
| The bank, without the test | 11 | 11 | 1 | 9 |
| The bank, without the bound by last sales | 4 | 8 | 2 | 2 |
| The bank, with round five's repayment | 10 | 10 | 4 | 10 |
| The bank that never takes | 11 | 11 | 3 | 8 |

Runs of 17 whose hours over the last 20 periods are at nineteen twentieths of the opening or more:

| Set | Small, 200 | Small, 400 | National, 200 | National, 400 |
| --- | --- | --- | --- | --- |
| Owners' top-ups | 14 | 14 | 13 | 10 |
| No credit at all | 8 | 8 | 11 | 6 |
| The bank | 6 | 6 | 10 | 7 |
| The bank, without the test | 6 | 6 | 14 | 8 |
| The bank, without the bound by last sales | 10 | 8 | 11 | 8 |
| The bank, with round five's repayment | 7 | 7 | 10 | 7 |
| The bank that never takes | 6 | 6 | 10 | 9 |

Runs better and worse than under the top-ups, by more than an hour of the mean of the last 20 periods:

| Set | Small, 200 | Small, 400 | National, 200 | National, 400 |
| --- | --- | --- | --- | --- |
| No credit at all | 0 / 13 | 1 / 13 | 1 / 9 | 0 / 11 |
| The bank | 2 / 11 | 2 / 11 | 2 / 9 | 0 / 10 |
| The bank, without the bound by last sales | 4 / 8 | 2 / 10 | 2 / 9 | 1 / 9 |

Where the bank's runs end in ruin, the shortage is everyone's: food and care go unmet in every account, while the money
sits where it cannot be spent. The measuring agent found the utility's workers holding $6,000 to $7,000 each in such
runs. That figure is the agent's; it was not counted again here.

## 4. Why the bank emptied

1. **Repayment came out of the payout.** The engine declares a payout only out of earnings on the books: what was kept
   from earlier periods plus the period's net income, never under zero. A business with losses on its books declares
   nothing. So under this round's clause it repaid nothing, whatever it held.
2. **Three closes later the bank took it.** At the small figures, 200 periods, 67 businesses were taken for the first
   time, in 17 of the set's 25 runs. Every one of them held at least its debt in cash at that close, and every one had
   declared no payout at that close and the two before. The debts ran from $5 to $679. At the national figures it is the
   same: 48 first takings, all 48 with the cash in hand.
3. **The bank went on lending to what it held.** Of $303,639 lent in that set, $72,145 went to businesses after the bank
   had taken them. Of $80,164 written off, $68,563 was on those loans.
4. **Its room to lend went with its cash.** A write-off comes out of the bank's cash, and all principal must stay within
   ten times that cash. The bank's cash reaches $0 in 12 of 25 runs at the small figures, at 200 and at 400 periods
   alike, and those are the runs in which a workplace stops for good. At the national figures its cash reaches $0 in 8
   runs at 200 periods and 10 at 400, and every run with a stop is among them (5 and 9).
5. **The taking is not the whole of it.** With the taking switched off the bank never runs empty, and a workplace still
   stops in 12 of 25 runs at the small figures. There the debts are never repaid, and the bound by last sales ends the
   credit.

Of $4,051,003 asked for in the set at the small figures, $303,639 was lent. The bound by last sales refused $3,424,303,
the bank's own room $276,068, and the test $46,993. Most of what the bound by last sales refused was asked by workplaces
that had already stopped and so had no sales: the measuring agent traced the stops themselves to refusals for the bank's
room, and the reader of the rows confirmed it.

What the design says at each point:

- On repaying: "It repays from its sales at the close, before any profit is paid out" (A9). Sales, not profit.
- On a business that is taken: "The old owners' claims end, the debt is written down, and the business is put up for
  sale (A17). The bank bears the loss" (A11). Nothing on the bench can buy a business, so the bank kept it, and the
  prototype let the bank keep lending to it.
- On a bank that loses its capital: it fails (A12) and may be rescued (A13). Neither is on the bench. Here an empty bank
  simply lends nothing for good.

## 5. The clauses, one by one

Runs better and worse than under the bank as built, by more than an hour of the mean of the last 20 periods:

| Clause taken away | Small, 200 | Small, 400 | National, 200 | National, 400 |
| --- | --- | --- | --- | --- |
| The test of whether the loan pays | 6 / 3 | 6 / 1 | 8 / 1 | 5 / 4 |
| The bound by last sales | 9 / 1 | 7 / 3 | 2 / 1 | 8 / 1 |
| Repayment out of the payout (round five's form in its place) | 5 / 6 | 4 / 5 | 7 / 4 | 3 / 7 |
| The taking | 3 / 6 | 1 / 6 | 8 / 2 | 7 / 4 |

- **The test** changes nothing at the small figures: a workplace stops in 11 and 11 runs with it and without it. At the
  national figures taking it away puts the stops off: a workplace stops in 1 of the 17 runs at 200 periods, against 5,
  and in 9 at 400, against 9. As built it reckons receipts from the plan at the posted price, whether or not the plan
  can be worked or sold. So it lends to businesses that are losing money, and it refuses where receipts equal cost to
  the cent and only the interest is missing. Those two observations are the measuring agent's.
- **The bound by last sales** matters most at the small figures (4 and 8 runs with a stop, against 11 and 11), and at
  the national figures at 400 periods (2 against 9). A workplace whose sales have just fallen is refused, and one that
  has stopped has no sales and is shut out for good. With the bound lifted, a workplace that had made nothing for ten
  periods or more made something again 69 times over the four sets. In every other set of the round that count is 0.
- **Round five's repayment** takes what a business holds above the need of the period just closed. It saves some runs
  and harms others, and its takings are of the same kind: 45 of its 47 first takings at the small figures held the cash.
  A business that keeps its working money just under one period's need never has anything "above" it.
- **Without the taking** nothing is written off, the bank keeps its room, and the debts stand for good.

## 6. The cap on orders

With the owners' top-ups, the cap against no cap. Runs better and worse of 17, and runs in which some posted price still
moves in the last 20 periods:

| | Small, 200 | Small, 400 | National, 200 | National, 400 |
| --- | --- | --- | --- | --- |
| Better / worse with the cap | 3 / 2 | 3 / 4 | 4 / 2 | 5 / 4 |
| A workplace stops, with the cap | 0 | 0 | 0 | 0 |
| A price still moving, without the cap | 13 | 13 | 15 | 15 |
| A price still moving, with the cap | 16 | 16 | 15 | 15 |

The taxed returning harvest at the small figures, one copy (the other is the same):

| | Without the cap | With the cap | Quiet run |
| --- | --- | --- | --- |
| The utility's plan, periods 2 to 30 | 125 to 156 | 105 to 117 | 120 |
| The utility's idle hours a period, at rest | 6 | 2.35 | 0 |
| Periods of 200 with a top-up to the utility | 195 | 0 | 0 |
| The owner goes short of power, at rest | 6 | 3.5 | 0 |
| The owner goes short of care, at rest | 8 | 8 | 0 |
| The price of power: opening, lowest, last | $12 $10 $10 | $12 $10 $11 | $12 |
| The price of care: opening, lowest, last | $30 $23 $24 | $30 $22 $24 | $30 |
| The farm's money at the end | $1,662 | $1,642 | $880 |
| The owner's money at the end | $393 | $379 | $640 |
| The fund's money at the end | $864 | $880 | $1,920 |

So the cap ends one thing that section 7 of round six's record traced: a utility staffed for power the farm cannot use,
losing money each period, and topped up for good. It does not bring the owners' needs back, because the two service
prices have fallen all the same. The farm still plans past its people. The hands it is lent come to less than one
batch's hours, so they stand idle: that is the measuring agent's reading.

The cap as built counts a buyer's own labor force, the people at work and its own people looking for work. The design's
later rule, that people looking for work belong to their place (A14), will change what a buyer's people are.

## 7. A shock that ends

The design's test: after a harvest that fails for ten periods, hours and the needs met in each account are back to
nineteen twentieths of the opening within 65 periods of its return, which is period 76, and stay.

- No set passes it for the harvest that fails on both copies, in either world, at either set of figures.
- For the harvest that fails on one copy, the taxed world passes at the small figures wherever there is no credit: the
  spare-money rule alone, with plans down the chain, with the cap as well, with lent hands, with lent hands and the cap;
  and under the bank with round five's repayment. It passes in no set with the top-ups, and in none with the bank as
  built.
- Those runs do not rest as they opened. With no credit the struck farm ends with 3 units of stock where the quiet run
  holds 40, and the fund with $995 where the quiet run holds $1,920. They pass by the test's twentieth.
- Under the top-ups the hours are back in full and the owners stay short of power and care, as in round six. The top-up
  is the owners' own money, and it stays in the farm (round six's record, section 7, links 1 and 3).

## 8. After the round

Two short sets of runs on the round's own branch, with switches that already existed: 57 sets in all. Controls first
reproduced round six's best set and the round's own set with the cap, byte for byte.

**The rule for service prices together with the cap.** Round six found that the rule (a service cuts its price only when
it performed less than it planned) changed nothing in the returning harvest, because the service's plan was swollen. The
cap takes one cause of the swelling away. With the top-ups and the cap, the rule against no rule:

| | Small, 200 | Small, 400 | National, 200 | National, 400 |
| --- | --- | --- | --- | --- |
| Better / worse with the rule | 2 / 4 | 3 / 3 | 2 / 9 | 6 / 2 |
| A workplace stops, with the rule | 0 | 0 | 0 | 0 |
| A price still moving, without the rule | 16 | 16 | 15 | 15 |
| A price still moving, with the rule | 16 | 16 | 15 | 15 |

The taxed returning harvest at the small figures, one copy:

| | The cap alone | The cap and the rule |
| --- | --- | --- |
| The price of power: opening, lowest, last | $12, $10, $11 | $12, $10, $11 |
| The price of care: opening, lowest, last | $30, $22, $24 | $30, $22, $23 |
| The owner goes short of power, at rest | 3.5 | 3.5 |
| The owner goes short of care, at rest | 8 | 8 |
| The utility's idle hours a period, at rest | 2.35 | 1.85 |

So the rule with the cap does not hold the two prices either, and no run passes the design's test for a shock that ends
with it or without it. The table below shows why.

**What feeds a service's falling price.** In the best set at the small figures, 200 periods, over the 17 pushed runs and
both copies, from the second period on:

| | Price cuts | After plans down the chain had staffed it past what was paid for | After the spare-money rule had | Neither |
| --- | --- | --- | --- | --- |
| The utility, without the cap | 837 | 481 | 187 | 200 |
| The clinic, without the cap | 2222 | 0 | 785 | 1437 |
| The utility, with the cap | 1312 | 120 | 870 | 338 |
| The clinic, with the cap | 2375 | 0 | 836 | 1539 |
| The utility, with the cap and the rule for service prices | 1013 | 43 | 920 | 73 |
| The clinic, with the cap and the rule for service prices | 2184 | 0 | 741 | 1443 |

A cut in neither column is the engine's own: it cuts a service's price in any period the service runs under its
capacity. So three things feed the fall. The engine's cut is what the rule for service prices takes away. An order the
buyer's people cannot work is what the cap takes away. The third is new: the spare-money rule keeps a service staffed
for buyers who asked and could not pay, the hours go unsold, and each such period cuts the price a step. In the taxed
returning harvest every cut of the price of care after the first follows such a period.

Here two rules of the design pull apart. A workplace with spare money plans for what was asked of it, not only for what
was paid for (A6). A service cuts work before it cuts its price (A3). The design does not say which gives way at a
service whose buyers cannot pay. Both readings go on the bench next.

**What each rule adds.** Mean hours of the last 20 periods over the 17 pushed runs, of 480, and the number of those runs
in which a workplace stops for good:

| Rules on | Small, 200 | Small, 400 | National, 200 | National, 400 |
| --- | --- | --- | --- | --- |
| No rule of the design at all | 183 (17) | 137 (17) | 352 (0) | 231 (16) |
| The spare-money rule alone (the engine today) | 370 (8) | 316 (9) | 443 (1) | 396 (7) |
| The spare-money rule and plans down the chain | 372 (6) | 332 (9) | 429 (3) | 367 (8) |
| The same with the cap on orders | 358 (8) | 296 (9) | 443 (1) | 397 (7) |
| The spare-money rule, plans down the chain and lent hands | 295 (9) | 266 (9) | 417 (5) | 291 (11) |
| The owners' top-ups alone | 291 (0) | 231 (0) | 357 (0) | 301 (0) |
| The top-ups and the spare-money rule | 465 (0) | 465 (0) | 444 (0) | 446 (0) |
| The top-ups, the spare-money rule and plans down the chain | 469 (0) | 468 (0) | 448 (0) | 447 (0) |
| The same with the cap on orders | 465 (0) | 466 (0) | 442 (0) | 444 (0) |
| The top-ups, the spare-money rule and lent hands | 473 (0) | 469 (0) | 465 (0) | 462 (0) |
| All four: round six's best set | 473 (0) | 473 (0) | 465 (0) | 462 (0) |
| All four and the cap on orders | 473 (0) | 471 (0) | 466 (0) | 462 (0) |

The columns are small figures at 200 and 400 periods, then national figures at 200 and 400. Read it in four steps.

- **The spare-money rule (A6, built) is worth the most by itself.** It lifts the engine with no rule by +187, +179, +91,
  +164 hours.
- **Without credit, nothing else of the first part helps.** Plans down the chain change the mean by +3, +15, -13, -29
  hours. Lent hands on top of them change it by -78, -65, -13, -76.
- **Credit and the spare-money rule carry the bench together.** The top-ups alone keep every workplace open but at 291,
  231, 357, 301 hours. The spare-money rule alone gives 370, 316, 443, 396. Together they give 465, 465, 444, 446, and
  no workplace stops in any run.
- **With both present, plans down the chain add +4, +3, +4, +1 hours,** less than one hundredth of the whole. Lent hands
  add +7, +3, +21, +16: little at the small figures, three to five hundredths at the national. Both together add +8, +7,
  +21, +16. The cap on orders changes plans down the chain by -4, -3, -6, -3.

So rounds four to six were right that this set of four is the best, and wrong about why. The top-ups and the spare-money
rule do nearly all of the work, and lent hands add the rest at the national figures. Round four took plans down the
chain out of a set that also held the first part's price rules, and there they looked needed. No round had taken them
out of this set.

## 9. What the checks corrected, and what the brief got wrong

The reader of the rows held 26 of 31 claims and refuted four:

- Takings happen in 17 of 23 runs at the small figures, not 18.
- Utilities were taken over debts of up to about $300, not $30 to $70, and seven of 29 repaid something.
- "Nothing reopens" is wrong for the bank without the bound by last sales.
- Under the bank a write-off stops at the bank's cash, so some principal stays owed for good with nobody bearing the
  loss. With the taking off, debts with their interest still grow at 400 periods.

The reader of the code found both prototypes honest: no site, account, product or period is named, every clause is
behind its switch, the constants are the ones reported, and no floating point decides anything. It also said that the
results turn on the prototype's own choices more than on the design's words, and named them. The first two are the
brief's, not the builder's:

- **Repayment out of the payout.** The brief said that what a business would pay its owner goes first to its debt. The
  design says it repays from its sales. Section 4 follows from this.
- **Calm runs.** The brief asked that the runs with more mouths (P7) and with half the shop's cash (P3) stay exactly
  still. P7 is not still with every switch off: the owners go short of food from period 3, and nothing moves after. P3
  is still without a bank and moves with one, because the shop borrows; it is a push. The quiet runs and P1 are exactly
  still in every set.
- **The bank's owners** are the same two households whose businesses it takes, and it pays out everything it holds above
  its opening capital. So the payouts of a taken business come back to its old owners, shared between the two copies.
- A taken business may borrow again; the count of missed closes starts at the loan's own close; and borrowers are served
  in the order of the sites when the bank's room runs short.
- The cap reads a buyer's labor force before the close, not the people it will employ in the coming period. On this
  bench the two agree wherever the buyer's plan sets its request for hours.

## 10. Read against the approved design

| Rule of the design | What the rows say |
| --- | --- |
| A8, a loan is new money | Exact in every period of every run. Build as it is |
| A9, the test of whether a loan pays | Changes nothing at the small figures and puts the stops off at the national. As built it reckons receipts from the plan, not from sales, and so lends to businesses that are losing money |
| A9, repaying from sales before any profit | Not measured as the design states it. The round measured repayment out of the payout |
| A10, the bank lends up to a multiple of its capital | Bites once write-offs have eaten the capital. Cannot be judged without the failing bank (A12) and the rescue (A13) |
| A10, a loan to keep running is bounded by last sales | The clause that matters most at the small figures. It shuts a stopped workplace out for good, and the way back is the fourth part (A17) |
| A11, a business that pays nothing for three periods is taken | Not judged. Every taking here follows from the repayment clause. A taken business has to stop borrowing from the bank that holds it |
| A5, plans through the chain, with a cap on orders | Plans down the chain add less than a hundredth to the hours once credit and the spare-money rule are present, and take hours away at the national figures without credit. The cap ends a supplier's staffing for orders that cannot be worked, and changes hours by as little. Neither is proven on this bench, whose chains are two steps long |

## 11. What follows

- **Plans through the chain (A5) are not built now.** Round six's record said they would be. The table in section 8
  changed that. The plan stands (`docs/superpowers/plans/2026-11-21-adjust-1b-plans-through-the-chain.md`), and the rule
  is measured again where a chain is longer than this bench's two steps.
- **The bank goes back on the bench as the design words it** (round 7b): it repays from its sales at the close, before
  any payout; a business the bank has taken does not borrow from it; and the bank reckons a plan only as far as the
  borrower's people can work it. Each with a switch that takes it away. Until then the verdict on A9 to A11 is open, and
  the owners' top-ups stay the reference.
- **The question that round has to answer:** can a bank do what the top-ups do, which is that no workplace stops,
  without what they cost, which is the owners' own money gone into the workplace for good (section 7)? If it cannot,
  that goes to the Director with the numbers, because the top-ups are a stand-in and not a rule of the design.
- **In the same round, the two readings of the spare-money rule at a service** (section 8): the service plans for what
  was paid for; or the hours the rule adds are a bet that does not count in the price test.
- **Then the third part,** written and waiting: people who look for work belong to their place, pay moves by steps, and
  a workplace lets people go before it cuts its price. Lent hands, the stand-in for the first of these, are what adds
  hours at the national figures once credit is there.
