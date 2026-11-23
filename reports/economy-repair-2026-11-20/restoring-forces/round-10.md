# Restoring forces, round ten: the restart mended, a price that comes down, capacity added, idle money taken out

Measured on 22 November 2026 on the small test economy, from head `a37fc78e8` of the branch. Round ten is the last round
of this effort. It put on the bench the four things the rows of round nine showed were missing (`round-9.md`, section
10): a restart that asks whether the workplace can work (step M); a goods price that comes down when goods go unsold
(step P); capacity added where buyers who could pay went unserved (step A); and an owner who takes idle money out of a
workplace (step W).

All of it is throwaway code behind switches, on the scratch branches `spike/r10-M` (`a361e0617`), `spike/r10-P`
(`3944ee9f3`), `spike/r10-A` (`e49666428`) and `spike/r10-W` (`345f43335`), the last of which is also `spike/r10-all`.
Nothing of this round is in the engine.

**How to read the figures.** As in round nine. A set is 25 runs: 8 calm and 17 pushed, each of 400 periods, about 31
years. Two figures side by side are the small figures and then the national figures. *Stops* is the number of pushed
runs, of 17, with a workplace that made or sold nothing in each of the last ten periods. *Hours* are the hours attended,
of 480 a period, on the mean of the last 20 periods over the pushed runs. The round is judged by the Director's test of
22 November (ADR319; `round-9.md`, section 2): R1 a calm world stays still, R2 a harvest that fails and returns is back
within five years and still back at the end, R3 after a lasting loss no place is left without a product and no price
climbs without end. Two credits were measured: none, and the bank of the ruling with a term of 3 periods. *The light
form* has seekers of the place, the stop rule, the bound on hiring, the resting price and the restart; *the whole third
part* adds pay by steps, letting go at once and plans down the chain.

Every figure was counted from the rows by my own scripts, except where a sentence names the measuring agent, a reader or
an earlier record. The round wrote 67 whole sets of 400 periods.

## 1. The answer

- **As I read the Director's test, no form passes it at both sets of figures.** Three forms pass at the small figures:
  the light form with the mended restart and the step down, under no credit and under a term of 3, and the same with
  capacity added, under a term of 3. Each fails at the national figures, and each fails there in the same run as every
  form of rounds eight and nine: the harvest that fails in one place for ten periods and returns.
- **That run fails in every national set of this round**, all 21 of them. In the form that comes closest it is the only
  run that fails, under both credits.
- **That verdict turns on half a line that I added to the test.** Its second line reads "work and output are back within
  five years". To count it I added "and still back at the end". Without my half, 6 forms pass the whole test at both
  sets of figures, the closest form under both credits among them (section 2). In each of them the harvest's own loss is
  made good within five years. What my half counts is a later slump: in one run at the national figures the hours fall
  again years after the harvest has returned, to a first low 5.2 to 6.5 years after the start, and end at 70% to 82%
  (section 8). Whether that later slump is a failure or play is the first question for the Director.
- **The step down is the piece that matters.** With it no shop's price is a ratchet any more: over the pushed runs a
  shop's posted price stepped down 1,582 and 1,927 times, where in the light form it never did. Hours rise from 396 and
  402 to 439 and 443 with no credit, and no workplace is stopped for good at the end, at either set of figures.
- **The mended restart** does what it was built for and changes no verdict. No restart puts in $0 any more and none has
  an idle period after it (section 4).
- **Adding capacity, as I worded it, is not the answer.** Shops used what was added. Clinics and utilities almost never
  did: there were no hands and no power for it. It adds stops in every pair I measured (section 6).
- **Taking idle money out is mixed**, and the Director has not ruled on it. Beside adding it raises hours. It also took
  away the one pass that adding had (section 7).
- **What a player would see in the closest form** (section 3; reported, not scored). With no credit, 10 and 10 of the 17
  pushed runs slump. The first low comes after a median of 1.2 and 1.9 years at 79% and 86% of the hours; 8 and 10 of
  those slumps are back within five years of it. The worst run ends at 74% and 76% of the hours, where the light form of
  round nine ended at 15% and 53%. Where the loss lasts, workers end with 60% and 55% of their needs met and owners hold
  2.2 and 2.7 times their calm-run money.
- **The run that fails everywhere is a crisis that the closest form does not end** (section 8). The harvest returns and
  everything is back. Then care runs short, the owners grow rich on it, food is bid up, and workers can no longer pay
  for care. With the step down the price of food stops climbing, at about two and a half times its opening price, and
  stays there. In one set, with pay by steps and the loan with a term, the crisis ends by itself after about eighteen
  years of repeated short dips, with pay higher than before.
- **The effort ends here**, as fixed on 22 November: rounds nine and ten are recorded and there is no round eleven.
  Section 10 says what ten rounds measured for each rule. Section 11 says what waits for the Director.

## 2. The Director's test, form by form

For each set: the returning-harvest runs that fail R2, of 4; the lasting-loss runs that fail R3, of 8; the other pushed
runs that fail the lines of R3, of 5 (reported); stops; hours attended. R1 holds in every set of the round.

| Form | Credit | Small: R2, R3, other | stops | hours | passes | National: R2, R3, other | stops | hours | passes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| The light form, as round nine left it | no credit | 0, 2, 0 | 1 | 396 | no | 1, 1, 0 | 0 | 402 | no |
| The light form, as round nine left it | a term of 3 | 1, 0, 0 | 0 | 421 | no | 1, 0, 0 | 0 | 425 | no |
| With the mended restart and the step down | no credit | 0, 0, 0 | 0 | 439 | yes | 1, 0, 1 | 0 | 443 | no |
| With the mended restart and the step down | a term of 3 | 0, 0, 0 | 0 | 445 | yes | 1, 0, 0 | 0 | 443 | no |
| The same with capacity added | no credit | 0, 4, 1 | 4 | 424 | no | 1, 7, 0 | 8 | 405 | no |
| The same with capacity added | a term of 3 | 0, 0, 0 | 0 | 430 | yes | 1, 1, 0 | 2 | 436 | no |
| All four steps | no credit | 1, 3, 0 | 3 | 446 | no | 1, 3, 0 | 3 | 456 | no |
| All four steps | a term of 3 | 1, 1, 0 | 1 | 452 | no | 1, 1, 0 | 1 | 456 | no |
| All four without adding | no credit | 1, 1, 0 | 1 | 411 | no | 1, 0, 0 | 0 | 439 | no |
| All four without adding | a term of 3 | 1, 0, 0 | 0 | 417 | no | 1, 0, 0 | 0 | 447 | no |
| All four without the step down | no credit | 1, 2, 1 | 1 | 418 | no | 1, 2, 0 | 1 | 431 | no |
| All four without the step down | a term of 3 | 1, 2, 1 | 1 | 411 | no | 1, 0, 1 | 0 | 441 | no |
| The step down and withdrawing only | no credit | 1, 1, 0 | 0 | 412 | no | 1, 0, 0 | 0 | 439 | no |
| All four with pay by steps | no credit | 3, 0, 0 | 0 | 436 | no | 2, 0, 0 | 1 | 440 | no |
| All four, two people looking at the opening | no credit | 1, 2, 0 | 2 | 454 | no | 1, 3, 0 | 3 | 467 | no |
| All four with the whole third part | no credit | 2, 1, 0 | 1 | 419 | no | 1, 2, 1 | 2 | 464 | no |
| All four with the whole third part | a term of 3 | 3, 4, 3 | 8 | 370 | no | 1, 1, 0 | 1 | 467 | no |
| The whole third part, as round nine left it | no credit | 3, 2, 0 | 3 | 386 | no | 1, 1, 0 | 0 | 429 | no |
| The whole third part, as round nine left it | a term of 3 | 3, 1, 0 | 2 | 424 | no | 1, 0, 1 | 1 | 434 | no |

What fails at the national figures in the forms that pass at the small figures (`clinic_a` is the clinic of place A, as
the rows name it; hours at the end count as back from 456 of 480):

- **With the mended restart and the step down, no credit.** R2 in fund-P8a: hours at the end 375 of 480; output short at
  the end at utility_a, clinic_a, utility_b, clinic_b.
- **With the mended restart and the step down, a term of 3.** R2 in fund-P8a: hours at the end 394 of 480; output short
  at the end at utility_a, clinic_a, utility_b, clinic_b.
- **The same with capacity added, a term of 3.** R2 in fund-P8a: hours at the end 331 of 480; output short at the end at
  all eight workplaces; R3 in plain-P2a: nothing made or sold for good at clinic_a.

The same run is close to passing in one more set: all four steps with the whole third part under a term of 3, at the
national figures. R2 in fund-P8a: output short at the end at clinic_b; R3 in fund-P2: nothing made or sold for good at
clinic_a, clinic_b. That form fails at the small figures, where 8 of the 17 pushed runs end with a workplace stopped for
good.

**Read without my added half.** Here the second line is met when there is a period within five years of the harvest's
return in which hours and every workplace's output are back to nineteen twentieths, whatever comes after. Rounds nine
and ten measured 45 forms at both sets of figures. With my half none of them passes at both. Without it these 6 do:

| Form | Credit | Stops, small and national | Hours | What my added half counted: small | national |
| --- | --- | --- | --- | --- | --- |
| The light form with the mended restart and the step down | no credit | 0 and 0 | 439 and 443 | nothing | fund-P8a: hours end at 78% |
| The light form with the mended restart and the step down | a term of 3 | 0 and 0 | 445 and 443 | nothing | fund-P8a: hours end at 82% |
| The same, with the step down for goods only | no credit | 0 and 0 | 436 and 440 | nothing | fund-P8a: hours end at 75% |
| The light form, as round nine left it | a term of 3 | 0 and 0 | 421 and 425 | plain-P8a: clinic_a ends smaller | fund-P8a: hours end at 70% |
| All four without adding | a term of 3 | 0 and 0 | 417 and 447 | fund-P8a: hours end at 72% | fund-P8a: hours end at 78% |
| The light form, as round nine left it (a set of round nine) | a term of 13 | 0 and 0 | 438 and 418 | plain-P8a: clinic_a ends smaller | fund-P8a: hours end at 70% |

In all 6 the national set fails my half in one run only, the harvest that fails in one place and returns, and for one
reason: a later slump, whose first low comes 5.2 to 6.5 years after the start and whose hours end at 70% to 82%. Read on
the whole economy instead of workplace by workplace, my reading still passes no national set (counted for the end of the
run).

## 3. What a player would see

Reported, not scored. A slump is a run whose hours fall under nineteen twentieths of the quiet run's. The first low is
the first period under that line that is not undercut in the year after it. The design's pace is "A slump takes one to
two years to its low and up to five back".

**Small figures**, over the 17 pushed runs.

| Form | Slumps | First low, years (median) | Hours at it | Back within five years | Hours at the end: median, least | Still swinging: runs, median width | Shut at the end: workplaces (runs) | Reopened (working at the end) | Taken by the bank | Bought |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| The light form, as round nine left it, no credit | 8 | 1.7 | 77% | 6 | 98%, 15% | 13, 74 | 5 (1) | 5 (5) | 0 | 0 |
| With the mended restart and the step down, no credit | 10 | 1.2 | 79% | 8 | 92%, 74% | 12, 66 | 0 (0) | 6 (6) | 0 | 0 |
| With the mended restart and the step down, a term of 3 | 9 | 1.2 | 83% | 9 | 97%, 77% | 12, 80 | 0 (0) | 2 (2) | 4 | 4 |
| All four steps, no credit | 10 | 1.2 | 75% | 10 | 96%, 78% | 10, 59 | 3 (3) | 4 (4) | 0 | 0 |
| All four steps, a term of 3 | 10 | 1.4 | 78% | 10 | 97%, 61% | 9, 116 | 2 (1) | 2 (2) | 7 | 6 |
| All four with the whole third part, no credit | 14 | 1.1 | 84% | 14 | 92%, 8% | 11, 113 | 4 (1) | 4 (2) | 0 | 0 |
| All four with the whole third part, a term of 3 | 14 | 2.5 | 62% | 14 | 90%, 40% | 12, 86 | 26 (8) | 38 (22) | 25 | 15 |

**National figures**, over the 17 pushed runs.

| Form | Slumps | First low, years (median) | Hours at it | Back within five years | Hours at the end: median, least | Still swinging: runs, median width | Shut at the end: workplaces (runs) | Reopened (working at the end) | Taken by the bank | Bought |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| The light form, as round nine left it, no credit | 10 | 1.3 | 85% | 9 | 81%, 53% | 10, 180 | 0 (0) | 7 (7) | 0 | 0 |
| With the mended restart and the step down, no credit | 10 | 1.9 | 86% | 10 | 95%, 76% | 10, 110 | 0 (0) | 1 (1) | 0 | 0 |
| With the mended restart and the step down, a term of 3 | 10 | 2.0 | 85% | 10 | 94%, 75% | 10, 132 | 0 (0) | 0 (0) | 0 | 0 |
| All four steps, no credit | 10 | 1.5 | 86% | 10 | 96%, 81% | 10, 126 | 5 (3) | 3 (3) | 0 | 0 |
| All four steps, a term of 3 | 10 | 1.5 | 88% | 10 | 95%, 78% | 9, 126 | 2 (1) | 1 (1) | 4 | 2 |
| All four with the whole third part, no credit | 11 | 1.2 | 88% | 11 | 98%, 86% | 9, 125 | 4 (2) | 6 (4) | 0 | 0 |
| All four with the whole third part, a term of 3 | 11 | 1.2 | 87% | 11 | 98%, 86% | 10, 92 | 2 (1) | 12 (10) | 7 | 6 |

**Who ends poorer**, in the eight runs where the loss lasts: the share of needs met on the mean of the last 20 periods
(median of the runs), and the owners' money at the end as a multiple of what they hold in the calm run.

| Form | Small: owners, workers, on benefits | owners' money | National: owners, workers, on benefits | owners' money |
| --- | --- | --- | --- | --- |
| The light form, as round nine left it, no credit | 82%, 58%, 23% | 1.4 | 98%, 41%, 36% | 2.7 |
| With the mended restart and the step down, no credit | 100%, 60%, 35% | 2.2 | 100%, 55%, 52% | 2.7 |
| With the mended restart and the step down, a term of 3 | 93%, 79%, 34% | 1.3 | 99%, 45%, 40% | 2.9 |
| All four steps, no credit | 86%, 76%, 37% | 1.2 | 90%, 72%, 47% | 1.4 |
| All four steps, a term of 3 | 94%, 87%, 34% | 1.1 | 75%, 85%, 42% | 1.6 |
| All four with the whole third part, no credit | 92%, 78%, 35% | 1.3 | 71%, 85%, 63% | 1.4 |
| All four with the whole third part, a term of 3 | 75%, 71%, 46% | 1.8 | 90%, 83%, 61% | 1.4 |

- **Slumps still come at the design's pace and now end less deep.** In the closest form the first low comes after one to
  two years on the median, and the worst run of the set ends at 74% and 76% of the hours, against 15% and 53% in the
  light form before.
- **Workers end less poor with all four steps.** Where the loss lasts, workers end with 76% and 72% of their needs met
  with all four steps and no credit, against 58% and 41% in the light form before. Owners still end with more money than
  in the calm run in every form of the table.
- **The economy still swings at the end** in most pushed runs of every form, by a median of 59 to 179 hours of 480
  across the forms of the two tables.
- **The whole third part under a term of 3 is the stormiest form at the small figures**: 26 workplaces are shut at the
  end in 8 runs, the bank took 25 and 15 were bought back, and 38 reopened after ten or more periods shut.

## 4. Step M: the restart asks whether the workplace can work

Three mends of round nine's restart: its test also asks that the inputs of one batch can be had, and a restart that
would put in $0 is none; a resting price that stands under its cost is raised to it; and the bound on hiring for the
next period is reckoned after the restart's money is in. To do the third the builder moved the whole restart ahead of
the close's staffing. Measured at the small figures.

| Form, credit | Stops: before, with the mend | Hours: before, with | Restarts with money: before, with | Closes refused for want of inputs | Raised to cost |
| --- | --- | --- | --- | --- | --- |
| The light form, no credit | 1, 1 | 396, 400 | 53, 48 | 197 | $12 |
| The light form, a term of 3 | 0, 0 | 421, 433 | 19, 10 | 16 | $5 |
| The whole third part, no credit | 3, 3 | 386, 401 | 28, 32 | 54 | $50 |
| The whole third part, a term of 3 | 2, 1 | 424, 411 | 2, 9 | 404 | $27 |

- **It changes little that can be counted at the end.** Stops and hours stay close to those before in all four pairs.
- **As the builder counted**, no restart puts in $0 in any of the four sets, where round nine had them, and no restarted
  workplace is idle in the period after its restart, where in round nine every one was.
- **Most refusals for want of inputs are clinics that cannot get power** where power is scarce for good. Those clinics
  are not restarted and stay shut, which is what R3 then counts (section 2).
- **A utility whose price rested under its cost now passes the test, and still nobody restarts it**, as the builder
  traced: the bank had taken it and no owner had the money to buy it. Whole copies of the economy still die after the
  bank takes a utility.

## 5. Step P: a goods price comes down when goods go unsold

The design's rule A1 for the step down: a price steps down when goods it offered went unsold and nobody was turned away.
Round four built it; no form of rounds seven to nine had it on. The builder found that round four's rule already reads
"nobody was turned away" as nobody who could pay, so the switch of this round only turns that rule on, and proved it:
the rows with round four's switches equal the rows with this round's, file for file. On this bench the rule acts on
shops only. A farm's buffer is its whole opening output, so nothing it holds counts as unsold, and no farm's price
stepped down by the rule in any set.

| Set, small figures | Stops: without, with | Hours: without, with | R2, R3 failing: without, with | Shop prices: steps up, steps down | Highest shop price, mean at the end |
| --- | --- | --- | --- | --- | --- |
| The light form with the mend, no credit | 1, 0 | 400, 439 | 0 and 1, 0 and 0 | 2,254, 1,582 | $108, $58 |
| The same, a term of 3 | 0, 0 | 433, 445 | 1 and 0, 0 and 0 | 2,283, 1,817 | $123, $52 |
| The whole third part with the mend, no credit | 3, 1 | 401, 450 | 3 and 3, 1 and 2 | 1,491, 1,052 | $97, $51 |
| The step down alone, no other rule | 9, 9 | 316, 290 | 1 and 6, 0 and 8 | 5,426, 739 | $431, $176 |

- **With the light form it turns failing into passing at the small figures**, with or without the bank, and raises hours
  by 38 with no credit and 12 under a term of 3.
- **Alone it still harms**, as rounds five and six found: without the bound and the restart beside it, hours fall from
  316 to 290. A price that comes down is safe only where a workplace cannot hire hands it cannot use and a shut
  workplace can come back.
- **Taking it away from all four steps brings the ratchet back**: hours fall to 418 and 431 with no credit and 411 and
  441 under a term of 3, against 446 and 456 and 452 and 456 with it.
- **Its floor is too low.** As built the step down stops at $1, not at the seller's cost. As the builder counted, a step
  down was followed at the next close by a step up for cost alone in 229 closes of the first set. The rule to build
  stops at cost.

## 6. Step A: capacity is added where buyers who could pay went unserved

The design's A18 and A19, for adding to a workplace only: where a workplace sold everything it offered for three periods
and buyers who could pay went unserved, its owner adds a step with their own money, ranked with the restart by what each
would earn. Founding a new workplace was not built.

Whether what was added was used, over the 17 pushed runs: the workplace-periods in which capacity stood above the
opening's, and those in which the workplace made (a shop: sold) more than at the opening.

| Set | Clinics: capacity above, made above | Utilities | Shops | Money put in |
| --- | --- | --- | --- | --- |
| All four steps, no credit, small | 1,878, 0 | 689, 0 | 2,960, 1,672 | $47,067 |
| All four steps, no credit, national | 2,264, 4 | 1,217, 0 | 5,422, 2,959 | $200,747 |
| Without withdrawing, no credit, small | 1,287, 438 | 298, 0 | 1,461, 327 | $31,336 |
| Without withdrawing, no credit, national | 695, 13 | 248, 0 | 2,580, 1,083 | $65,140 |
| Without withdrawing, a term of 3, small | 1,055, 0 | 476, 0 | 987, 114 | $35,750 |
| Without withdrawing, a term of 3, national | 633, 8 | 354, 0 | 1,194, 115 | $60,443 |

- **Shops used what was added; clinics and utilities did not.** With all four steps and no credit, clinics stood with
  added capacity in 1,878 and 2,264 workplace-periods and made more than their opening 40 in 0 and 4 of them. No utility
  ever made more than its opening 120. An added step asks for hands and for power, and where everyone is at work and the
  utility is at its limit there are none.
- **It adds stops.** Against the same form without adding: 3 / 3 stops against 1 / 0 with no credit, and 1 / 1 against 0
  / 0 under a term of 3.
- **Without adding, R3 passes at the national figures under both credits**, and the only failure left there is the one
  run of section 8.
- **It is the one set of the sets step that passes**: without withdrawing, under a term of 3, at the small figures. At
  the national figures the same form fails in two runs.
- **What the reader of the code found**: the inputs test of step M is not applied to adding, so a clinic batch can be
  added while its utility is at its limit; and an added step moves the target that the price rule reads.

## 7. Step W: an owner takes idle money out of a workplace

My reading of the ruling on who carries a loss (ADR318), turned round: money a workplace has held beyond its outlay in
each of the last 13 periods goes back to its owner as capital. The Director has not ruled on it.

| Form | Credit | Stops: without, with | Hours: without, with | Money taken out | Share of all money in workplaces at the end: without, with |
| --- | --- | --- | --- | --- | --- |
| All four steps against the same without withdrawing, small | no credit | 4, 3 | 424, 446 | $34,814 | 81%, 79% |
| All four steps against the same without withdrawing, national | no credit | 8, 3 | 405, 456 | $148,012 | 89%, 86% |
| All four steps against the same without withdrawing, small | a term of 3 | 0, 1 | 430, 452 | $75,881 | 71%, 68% |
| All four steps against the same without withdrawing, national | a term of 3 | 2, 1 | 436, 456 | $188,734 | 80%, 78% |

- **Beside adding it raises hours** at both sets of figures with no credit, and at the national figures it cuts the
  stops that adding alone leaves.
- **It took away the one pass.** Under a term of 3 at the small figures the form with adding passes; with withdrawing as
  well it fails in two runs, one of them the harvest that fails in one place and returns.
- **The money still rests in the workplaces**: they hold 68% to 86% of all money at the end across the four sets with
  all four steps.
- **Adding and withdrawing recycle the same money**, as the reader of the code counted: an unused step leaves its money
  above the workplace's outlay, withdrawing hands it back after 13 periods, and adding puts it in again while the
  shortage lasts. The totals of money put in under all four steps largely count the same money several times.

## 8. The run that still fails everywhere

The harvest fails in one of the two places for ten periods and then returns, at the national figures (run fund-P8a;
`round-9.md`, section 10). It fails R2 in every national set of the round. Figures are for the place where the harvest
failed.

**In the closest form** (the light form with the mended restart and the step down), under both credits:

1. **Periods 11 to 37.** Everything is back and all 480 hours are worked. Care is cheap, so households ask for more than
   the clinic's 40. Its price steps up to $42 by period 37. The profit goes to the owners, who hold more than $1,400 by
   period 40 against $640 in the calm run.
2. **Periods 38 to 100.** The owners want up to 8 more units of food than the 40 the shop stocks. Buyers who could pay
   are turned away every period, so the shop's price steps up, from $35 to about $95 by period 100. The hours first fall
   under nineteen twentieths in period 50.
3. **To the end.** The price of food stops climbing and stays between $90 and $100: the ratchet is gone, and the price
   has found the level at which those who can pay take what there is. The clinic sells 15 of 40 units on the mean of the
   last 20 periods, because workers who pay that much for food cannot pay for care. Hours end at 375 with no credit and
   394 under a term of 3, of 480. With no credit the hours are back at nineteen twentieths in only 4 of the 350 periods
   after period 50.

So the step down ends the climb and does not end the crisis. The price of food rose for a reason the price rule counts
as sound: buyers with money were turned away. What nothing on the bench answers is where that money came from, the
owners' gain from a clinic that could not make more, and that no worker's pay follows the cost of living.

**In one set the crisis ends by itself**: all four steps with the whole third part under a term of 3. There the hours
are under nineteen twentieths in 54 periods between period 97 and period 337, in 25 short spells over 18.5 years, with a
low of 298 in period 267, and not again after it. The shop's price peaks at $65.55 in period 230 and ends at $33.95,
under its opening $38. Pay rises by steps from period 90, from $10 to $13.75 an hour at the clinic. The wage bill ends
at $5,577 against $4,800 at the opening, and the owners' money falls back to $417, under their calm-run $640. The run
ends with 479 of 480 hours. It fails R2 only because the clinic of the other place ends at 33 of 40 units. The design's
pace is up to five years back.

## 9. Calm runs, exactness, the bank, and what the readers corrected

- **R1 holds in all 67 sets**: the quiet run of each world is still, and money and people are exact in every period of
  every run.
- **The calm run P3 is not calm under a term of 3 at the small figures**, in any set, the baseline included. As the
  builders traced it, the shop there borrows $700 every three periods and its interest moves the run from the first
  period; in one set a whole world of that run dies after the bank takes both utilities. R1 looks at the quiet run only,
  so this passes it. At the national figures every calm run is still under a term of 3.
- **The bank under a term of 3.** Workplaces taken, small and national: 4 and 0 in the closest form, 12 and 10 with
  adding, 7 and 4 with all four steps, 25 and 7 with the whole third part. Workplaces whose debt rose over the last 20
  periods, in that order: 10 and 10, 7 and 5, 5 and 3, 5 and 5.
- **The recount of the rows** by a second reader gave 33 findings: 29 of the measuring agents' claims hold, 3 were
  refuted and 1 is unclear. Every verdict of the test, every count of stops and every figure of hours matched. Refuted:
  that one set was the only pass of the round (three forms pass at the small figures, counted here); that utilities made
  more than 120 in 55 periods (none did); and one total of money withdrawn.
- **The reader of the code** gave 32 findings: 31 hold and 1 is unclear. All four prototypes are honest: each sits
  behind its switch, names no place or period, and says where it departs from its brief.
- **One variant could not be run**: all four steps without the mend. Adding needs the mended restart's timing and
  refuses to run without it. The measuring agent ran the step down and withdrawing alone in its place.
- **A fault of mine, caught before launch.** My first draft of step P rested on a claim I had not counted: that a shop's
  price stepped up for needs nobody could pay for. The count showed the opposite fault, a price that never steps down,
  and I redrew the step. The lesson is in my notes: every "because" in a design note gets its own count before a builder
  is briefed on it.
- **A second fault of mine, found while writing the final report.** The first version of this record (commit
  `7c73aa582`) said that no form passes and did not say that this rests on the half-line I added to the test, nor count
  what passes without it. This version does, in sections 1, 2 and 11. No figure of the first version changed.

## 10. What ten rounds measured, rule by rule

Each rule is a throwaway prototype on the small test economy, measured for 400 periods at two sets of figures. A verdict
here is what the bench says, not a decision to build.

| Rule | Design | As measured | The bench says |
| --- | --- | --- | --- |
| A workplace with spare money plans for what was asked | A6 | Helped in every round (rounds one to seven) | Build it. It is in the engine, behind a setting |
| A workplace asks for hands only for the hours it can work | A5, A6 as read in round nine | Without it every form with seekers is in ruin: 15 stops of 17 against 3 and 0 | Build it |
| People who look for work belong to their place; a workplace with no money stops | A14, A17 | Needed by the restart; alone they add stops (round eight) | Build them with the bound |
| A stopped workplace's price rests; a buyer restarts it | A17, A19 | With the owners' own money nearly every restarted workplace is working at the end | Build it, with the mend of this round |
| A goods price steps down when goods go unsold | A1 | Ends the ratchet of shop prices; the light form passes at the small figures with it | Build it, with its floor at cost |
| A loan to keep running stands for a term | A10, ADR318 | A term of 3 measured best; terms of 13 and 26 end worse; a calm run that borrows is moved by it | Build it changed; the calm run that borrows needs a look |
| Pay moves by steps | A15 | Mixed in rounds eight and nine; the one crisis that ended in this round ended in a form with it, with pay more than a third higher | Not settled |
| Letting people go at once, with the service price rule | A3 | Saved runs at the national figures in round eight | Not settled |
| Plans made through the chain of supply | A5 | Helped under the bank in round eight, harmed under a term of 13 in round nine | Not settled |
| Capacity is added where buyers went unserved | A18, A19 | Shops use it; clinics and utilities cannot; it adds stops | Not as worded: add only where hands and inputs can be had |
| An owner takes idle money out | my reading of ADR318 | Raises hours beside adding; took away the one pass | Not settled, and not ruled |
| The owners' top-ups | the stand-in of rounds four to seven | Hid every stop; they were owners' money, not credit | Do not build |

## 11. What waits for the Director

1. **Whether the later slump of section 8 is a failure or play.** This one answer decides the verdict. A local crop
   failure ends and everything is back. About three years after it the cost of living rises, owners grow rich and
   workers go without care, and in the closest form that does not end. If it is play, 6 forms meet the test at both sets
   of figures and the closest form is the one to build. If it is a failure, no form passes, and what is missing is
   whatever ends it: in this round only a form with pay that moves by steps did, over about eighteen years.
2. **Whether the rest of my reading stands.** I ask that every workplace's own output be back, not only the whole. An
   economy that came back changed fails that. It changes no verdict of this round at the national figures.
3. **Which rules to build into the engine.** Section 10 gives what the bench says. Building them is a new piece of work,
   larger than any round, and none of it is planned.
4. **What the bench never reached**: organized workers who answer a squeeze (A16), the founding of a new workplace
   (A18), capital that moves across borders, and the design's test of a cycle with no outside push.
5. **Whether an owner may take idle money out of a workplace** (step W). I built it as a reading of the ruling on
   losses; it has not been ruled.

