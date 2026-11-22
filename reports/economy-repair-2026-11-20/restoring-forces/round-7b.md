# Restoring forces, round 7b: the bank as the design words it

Measured on 2026-11-22 on the small test economy, doubled (two of everything, 480 hours a period), in the plain world
and in the taxed world with the benefits fund. A set is 25 runs: two quiet ones, six mild ones and 17 pushed ones. Each
set was run for 200 and for 400 periods, at the small world's figures and at the national ones. Sixty sets were
measured. Two readers checked the round: one recomputed the claims from the rows, one read the prototypes' code. Every
figure below was then counted again from the raw rows by the lead's own scripts, except where the text names its source.
The prototypes are throwaway code on scratch branches and are not part of the engine.

Columns of every table: small figures at 200 and 400 periods, then national figures at 200 and 400.

## 1. The answer

- **The bank as the design words it does not keep workplaces open.** A workplace stops for good in 9, 9, 6, 9 of the 17
  pushed runs. Under the owners' top-ups it is 0, 0, 0, 0, and with no credit at all 9, 9, 5, 11. At the small figures
  the runs with a stop are the same runs as with no credit. Mean hours of the pushed runs, of 480: 260, 253, 393, 273
  with the bank, 473, 473, 465, 462 with the top-ups, 295, 266, 417, 291 with no credit.
- **The harm of round seven is gone.** The bank takes 23, 23, 6, 18 businesses, where round seven's took 67 at the small
  figures, all of them holding the cash to pay. Now one business held its debt in cash (the same one at both lengths of
  the small figures), and none had sold anything in the three periods before. Nothing is lent to a business the bank
  holds. The bank's cash never reaches $0. Nothing is owed at the end of any run. No repayment is larger than the sales
  of its period.
- **Money is exact** in every period of every run of all 52 sets with a bank.
- **As worded, the loan bridges one period.** It is drawn at the opening and repaid from sales at the close. Of 1,836
  periods in which a workplace drew a loan (small figures, 200 periods), 1,807 ended with nothing owed. Everything lent
  was repaid or written off: $826,648 lent, $822,354 repaid, $4,294 written off.
- **The loan refuses the business that the top-ups kept open.** A business whose sales fell is bounded by those sales,
  and one that has stopped has none. Without that bound a workplace stops in 2, 4, 0, 1 runs, and mean hours are 408,
  369, 460, 441. The price is debts that still grow at the end and a bank that runs empty in some runs (section 5).
- **So what carried the test economy in the earlier rounds was not credit.** It was the owners' own money, put into a
  losing workplace and never asked back. The design has no such rule (section 11).
- **Built next to the rule the engine already has, the bank adds nothing.** The spare-money rule with the bank: a
  workplace stops in 7, 9, 1, 6 runs. The spare-money rule alone: 8, 9, 1, 7. With the top-ups: 0, 0, 0, 0.
- **Of the two readings of the spare-money rule at a service, one fails and one helps** (section 8). Where a service
  plans only for what was paid for, hours collapse and prices run away. Where the hours the rule adds are a bet that
  does not count in the price test, hours hold, and the harvest that fails on one copy comes back in the taxed world at
  the national figures, with every price at its opening. No run of round seven passed the design's test at the national
  figures.
- **A harvest that fails on both copies comes back in no set.** The owners stay short of power and care for good.

## 2. What was on the bench

Round seven's bank, with three corrections, each behind its own switch:

1. **Repayment from sales.** At the close, before any payout is declared, a business that owes pays out of its cash:
   first interest, then principal, as much as it owes and no more than it took in from sales in that period.
2. **No lending to a business the bank holds.** Nothing on the bench can buy a taken business, so the bank holds it.
3. **The plan as far as it can be worked.** What the borrower needs, and the receipts of the bank's test, are reckoned
   on the batches that the borrower's own people can work.

One variant reads the test's receipts from the sales of the period before. Everything else of round seven's bank stayed:
its capital of $2,400, its rate, the test, the two bounds, three closes to a taking.

Two readings of the spare-money rule (A6) at a service whose buyers cannot pay, each with the cap on orders and the rule
that a service cuts its price only when it performed less than it planned:

- **Paid:** a service plans for what was paid for and for its business buyers' orders. The spare-money rule adds nothing
  to a service's plan.
- **Bet:** the spare-money rule still staffs the service, but the price test compares what the service performed with
  its plan before the rule's addition. Losing the bet costs idle pay, not a step of the price.

The references are round seven's rows: the owners' top-ups with all four rules ("the top-ups"), the same with no credit,
and round seven's bank. Controls reproduced those rows byte for byte before anything was changed.

## 3. The bank against the top-ups and no credit

Mean hours of the last 20 periods over the 17 pushed runs, of 480, and in brackets the runs with a workplace stopped for
good:

| Credit | Small, 200 | Small, 400 | National, 200 | National, 400 |
| --- | --- | --- | --- | --- |
| The owners' top-ups | 473 (0) | 473 (0) | 465 (0) | 462 (0) |
| No credit | 295 (9) | 266 (9) | 417 (5) | 291 (11) |
| Round seven's bank | 295 (11) | 235 (11) | 426 (5) | 309 (9) |
| The bank as the design words it | 260 (9) | 253 (9) | 393 (6) | 273 (9) |
| The same with the cap on orders | 307 (8) | 293 (8) | 383 (8) | 270 (9) |

Runs better and worse than under the top-ups, by more than an hour: 0 / 13 | 1 / 13 | 1 / 8 | 0 / 10.

The verdict on a run can turn on the figures. Under the bank the taxed pay rise ends with every workplace stopped at the
small figures (0 hours at 200 and at 400 periods) and with all 480 hours worked at the national ones.

## 4. Against round seven's bank

| | Small, 200 | Small, 400 | National, 200 | National, 400 |
| --- | --- | --- | --- | --- |
| Businesses taken | 23 | 23 | 6 | 18 |
| Of those, holding their debt in cash | 1 | 1 | 0 | 0 |
| Of those, with a sale in the three periods before | 0 | 0 | 0 | 0 |
| Lent | $826,648 | $1,388,054 | $252,944 | $420,003 |
| Written off | $4,294 | $4,294 | $680 | $3,634 |
| Lent to a business the bank holds | $0 | $0 | $0 | $0 |
| Runs in which the bank's cash reaches $0 | 0 | 0 | 0 | 0 |
| Owed at the end | $0 | $0 | $0 | $0 |

Round seven's bank at the small figures, 200 periods: 67 taken, all 67 holding the cash; $303,639 lent, $80,164 written
off, $72,145 lent to businesses it had taken; its cash at $0 in 12 of 25 runs.

**Most of the lending at the small figures is one calm run.** In the run where the shop opens with half its cash, each
shop borrows $700 at the opening of 796 of 800 shop-periods and repays it at that close. That is $557,200 of the
$826,648 lent, 67 hundredths, and 80 hundredths at 400 periods. The shop pays its owner a payout in every one of those
periods and never rebuilds its cash. At the national figures, where a workplace opens with two periods of cash, that
shop borrows nothing. The rows reader found this; the measuring agent had said the shop never borrows.

## 5. The clauses, one by one

Each clause taken away from the bank as the design words it. Runs better and worse than that bank, and in the last row
of each pair the runs with a stop (the bank itself: 9, 9, 6, 9):

| Clause taken away | Small, 200 | Small, 400 | National, 200 | National, 400 |
| --- | --- | --- | --- | --- |
| Repayment from sales (round seven's form in its place) | 9 / 2 | 5 / 3 | 6 / 5 | 7 / 4 |
| stops | 8 | 9 | 6 | 11 |
| No lending to what it holds | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| stops | 9 | 9 | 6 | 9 |
| The plan as far as it can be worked | 7 / 5 | 5 / 6 | 2 / 8 | 3 / 6 |
| stops | 12 | 12 | 10 | 11 |
| The test of whether the loan pays | 8 / 4 | 6 / 5 | 8 / 3 | 7 / 3 |
| stops | 12 | 12 | 4 | 6 |
| The bound by last sales | 9 / 0 | 8 / 1 | 8 / 0 | 9 / 0 |
| stops | 2 | 4 | 0 | 1 |
| The taking | 2 / 1 | 2 / 0 | 0 / 1 | 3 / 0 |
| stops | 9 | 9 | 6 | 9 |
| The test reads last period's sales (a variant, nothing taken away) | 4 / 1 | 5 / 1 | 8 / 3 | 8 / 2 |
| stops | 9 | 9 | 5 | 9 |

- **Repayment from sales** is what ended the wrongful takings. Without it the bank takes 53, 53, 39, 58 businesses, of
  which 42, 42, 39, 54 held the cash and 50, 50, 39, 57 were still selling.
- **No lending to what it holds** changes no run: the bound by last sales already refuses a business that has stopped.
- **The plan as far as it can be worked** is the bank's restraint. Without it more workplaces stop in every form.
- **The test** is mixed: without it more workplaces stop at the small figures and fewer at the national. As built it
  sets the whole plan's receipts against the whole need and the interest, and passes when they are equal. The design
  says "what the loan pays for will sell above its cost and the interest". That narrower test is not built.
- **The bound by last sales** is the clause that matters most. Without it the bank lends $2,884,930 at the small figures
  in 200 periods, against $826,648. Debts, with their unpaid interest, still grow at the end at 2, 8, 4, 4 workplaces,
  and the bank's cash reaches $0 in 1, 3, 0, 1 runs.
- **The taking** changes little in hours. Without it nothing is written off. Debts stand with interest running: $8,601,
  $13,903, $1,832, $8,401 is owed at the end, still growing at 21, 21, 9, 20 workplaces.

## 6. The form that would be built next

Plans through the chain are not being built, and lent hands are a stand-in for the design's third part. So the engine
that would exist if a bank were built next is the spare-money rule and the bank, nothing else.

| Rules on | Small, 200 | Small, 400 | National, 200 | National, 400 |
| --- | --- | --- | --- | --- |
| The spare-money rule alone (the engine today) | 370 (8) | 316 (9) | 443 (1) | 396 (7) |
| With the bank as the design words it | 370 (7) | 286 (9) | 438 (1) | 382 (6) |
| With the owners' top-ups | 465 (0) | 465 (0) | 444 (0) | 446 (0) |

Runs better and worse than under the top-ups: 2 / 10 | 4 / 10 | 3 / 7 | 1 / 9. Better and worse than under the spare-
money rule alone: 4 / 3 | 2 / 6 | 2 / 7 | 3 / 6. This bank lends more than the one of section 3: $1,289,105 at the small
figures in 200 periods, of which all but $2,293 was repaid.

## 7. The owners' money

The question of the round was whether a bank can do what the top-ups do without what they cost: the owners' own money
gone into a workplace for good. In the taxed returning harvest it leaves their money alone, and it does so by not
lending. "At rest" is the mean of the last 20 periods.

| Taxed returning harvest, small figures, 200 periods | Top-ups | No credit | The bank |
| --- | --- | --- | --- |
| Both copies: put in by owners, or lent | $22,803 | $0 | $45 |
| Both copies: an owner's money at rest (quiet run: $640) | $393 | $366 | $366 |
| Both copies: the owner's care not met, of 8 | 8.0 | 8.0 | 8.0 |
| One copy: put in by owners, or lent | $888 | $0 | $0 |
| One copy: the struck copy's owner's money at rest | $576 | $658 | $658 |
| One copy: the owner's care not met, of 8 | 2.1 | 0.0 | 0.0 |

With the cap on orders the top-ups themselves cost far less in the run on both copies: $643 in 200 periods, where
without the cap they are $22,803. Most of what the top-ups cost there was paying a utility for orders that could not be
worked.

## 8. The two readings of the spare-money rule at a service

Each with the cap on orders and the service price rule. Mean hours of the 17 pushed runs and, in brackets, runs with a
stop:

| Set | Small, 200 | Small, 400 | National, 200 | National, 400 |
| --- | --- | --- | --- | --- |
| The rule as designed, top-ups | 472 (0) | 470 (0) | 461 (0) | 462 (0) |
| Paid, top-ups | 195 (2) | 152 (6) | 366 (0) | 315 (1) |
| Bet, top-ups | 466 (0) | 462 (0) | 465 (0) | 464 (0) |
| The rule as designed, the bank | 295 (8) | 288 (8) | 374 (7) | 275 (9) |
| Paid, the bank | 201 (14) | 173 (15) | 327 (12) | 305 (12) |
| Bet, the bank | 321 (8) | 295 (8) | 405 (4) | 327 (7) |

- **Paid fails.** With the top-ups it is worse than the rule as designed in 17, 17, 15, 17 of 17 runs. In the taxed
  returning harvest at the small figures power ends at $123 and care at $101, from $12 and $30, and hours rest at 96 of
  480.
- **Bet holds hours with the top-ups** (466, 462, 465, 464 against 472, 470, 461, 462) and no workplace stops. With the
  bank it is better than the rule as designed in every form.
- **Under Bet a service's price is cut less often.** Price cuts of the utility over the pushed runs (small figures, 200
  periods): 1,013 with the rule as designed, of which 920 follow a period that the spare-money rule had staffed beyond
  what was paid for. Under Bet: 540, of which 462. Of the clinic: 2,184 and 1,993.
- **Neither reading holds both service prices where the harvest fails on both copies.** Under Bet with the bank, power
  stays at $12 through that run at the small figures; care still falls from $30 to $24.

## 9. A shock that ends

The design's test: after a harvest that fails for ten periods, hours and every account's needs are back to nineteen
twentieths of the opening by period 76 and stay there, and prices settle.

- **On both copies, in the plain world or the taxed one: no set passes.** Nor does the plain world's harvest on one
  copy.
- **The taxed harvest on one copy passes at the small figures wherever no credit is in play:** with no credit, and in
  the bank as the design words it, which lends nothing in that run, so that its rows are the no-credit rows. It fails
  under the top-ups, where the owners end short of care.
- **Under Bet it passes in all four forms with the bank, and at the national figures with the top-ups.** In those runs
  neither the bank nor the owners put anything in. At the national figures every posted price is back at its opening
  ($12 for power, $30 for care) and all 480 hours are worked. The same run under the rule as designed rests at 454 hours
  with care at $20.25.
- **A run that passes is not the run it was.** At the national figures under Bet the struck farm ends with $2,574 (quiet
  run: $1,760) and 3 units of stock (quiet: 40), and the fund with $960 of $1,920.

No set isolates Bet with no credit at all. In every passing run nothing was lent or put in, so the pass is credited to
the reading and the two rules beside it, not to credit. That is a reading of the rows, not a measured set.

## 10. What the checks corrected, and what the prototype chose

The rows reader held 26 of 30 claims and refuted three:

- The measuring agent said the shop that opens with half its cash never borrows. It borrows $700 at every opening
  (section 4).
- It said that where a workplace stops every account goes without food and care. Every account of the struck copy does,
  and both copies only where both are struck.
- It gave the top-ups' lowest runs as 455 to 469 hours. They are 452.6 to 469.2.

It could not confirm one split (how many workplaces had asked for nothing in the ten periods before they stopped), which
depends on how the window is cut. That split is left out of this record.

The code reader found every prototype honest, and named the choices that the prototype made where the design's words
left room:

- **Repay as much as sales and cash allow, at every close.** That is the plain reading of "it repays from its sales at
  the close". The design's debt record also carries "when it falls due". A loan that stands to a later date, with
  interest paid from sales, was not measured.
- **Sales are the period's sales on the books,** capped by cash. One business was taken holding its debt in cash,
  because it had sold nothing.
- **The plan as far as it can be worked** is the cap's own count at goods makers and services. At a shop it is the
  agent's own construction, and it may read the plan after the spare-money rule has raised it.
- **The test passes when receipts equal need and interest.** The design says "above".
- **Any payment above $0 resets the count of missed closes,** so a business with any sales is never taken.

## 11. Read against the approved design

| Rule | What the rows say |
| --- | --- |
| A8, a loan is new money | Build as worded. Exact in every period of every run |
| A9, repayment from sales before any payout | Build as worded. It ends the taking of businesses that can pay. As worded the loan bridges one period and no more |
| A9, the test | Not yet judged: the test built is wider than the design's words |
| A10, the bound by last sales | As worded it shuts out a workplace whose sales fell, which is when it asks. Lifting it saves most runs and leaves debts that grow |
| A11, taking after three closes with nothing paid | With repayment from sales it takes only dead businesses. Build it together with A17, the sale of what is taken |
| A6, the sentence "credit (A9) is what gives a sound workplace that money" | Not borne out. A loan repaid at the close leaves no spare money |
| A6 at a service | The Bet reading. The Paid reading is refuted |

The owners' top-ups kept every workplace open in rounds four to seven by covering losses that the design's loan is right
to refuse. Among the failures the design names is "a stabilizer that hides the economy", and a top-up that never ends is
one. The design's own way back for a workplace that stops is its fourth part: it is taken or shut, a buyer restarts it
when its product sells above its cost at the day's pay, and the slump leaves marks. None of that is on the bench yet,
and neither is the third part, by which a workplace sheds hands and pay moves.

So the round does not say the bank is wrong. It says that the bank is not what restores, and that round seven's record
was wrong to say credit carries the test economy.

## 12. What follows

- **The reference changes.** From here a rule is measured against two things: no credit, and the bank as the design
  words it. The top-ups stay on the bench as a stand-in that hides losses, and are named so.
- **The spare-money rule at a service is built in the Bet reading** when it is next touched. That is the lead's call
  from these rows, for the Director to check.
- **Next on the bench is the design's third part,** as the design orders it: people who look for work in their place,
  pay that moves by steps, and a workplace that lets people go before it cuts its price. A workplace that can shed hands
  and cut pay may keep going where today it stops.
- **Then the first rule of the fourth part,** a buyer for a workplace that the bank took or that shut. Without it
  nothing that stops can come back, in any round so far.
- **For the Director:** the sentence in A6 about credit; whether a narrower test and a loan with a later due date should
  be measured; and whether owners may ever keep a losing workplace open with their own money.
