# What brings the small economy back: round five

Measured 21 November 2026, on the branch at `125d6dbf6`. Round four found that the design's first part carries
the small test economy by its quantity rules, that its price rules fail because no buyer answers a price, and
that owners' top-ups stand in for credit and never stop. Round five puts three things on the bench, as throwaway
prototypes behind switches:

- **F2**: the spare-money rule as it is now built in the engine (rule A6), in place of round four's prototype f.
- **L**: a buyer who answers a price. A merchant does not buy a good at more than it can resell it for: its own
  posted price less the handling wages of one unit. Above that it orders nothing from that supplier that period.
- **K**: one bank in place of the owners' top-ups. A workplace short of its coming wages and inputs borrows the
  gap as new money, within its sales of the last period and within ten times the bank's cash. It pays 0.6% a
  period. One that pays nothing for three closes running is taken.

The other letters are round four's: **d2** owners' top-ups, **a** lent workers, **D** plans down the chain,
**R** a service cuts its price only when it performed under its plan, **e-kept** a goods price steps down on
unsold stock, **S** a goods price steps up on low stock, **W** larger steps for raw goods and power. "The
engine's own prices" means none of R, e-kept, S and W.

The pushes: P2 a poor harvest for good, P4 higher pay at the clinic, P5 a cut in the fund's taxes, P6 scarcer
power, P8 a poor harvest for ten periods that then returns. Runs are 200 periods, and 400 for the main sets, at
the small world's own figures and at the national figures (steps of 2.5%, two periods of cash). Hours are out of
240 and are the mean of the last 20 periods. A double dagger (‡) marks a run in which a workplace stopped for
good. A dagger (†) marks one in which a workplace made nothing in some of the last 20 periods without stopping
for good. This file is written by the lead from the round's structured result (`round5-wf_7756832f.output.json`)
and its independent check. The rows are under `out/r5-*`.

## 1. The answer

- **Nothing measured brings the economy back after a shock that ends.** No run of the returning harvest, in any
  set of this round, at either set of figures, regains its opening state or even holds 228 hours with every need
  within 2 units to the end. Only round four's taxed run with prototype f did.
- **The rule as built is weaker than its prototype at the small figures.** With F2 in f's place the round-four
  core loses its one returning run (223 hours, not 240 exactly still). The taxed poor harvest goes to ruin (16
  hours against 154) and the no-tax world under scarcer power loses its clinic. Two runs improve. At the national
figures almost nothing changes. The cause is not isolated.
- **A buyer who answers stops the price climbing, and moves the hurt.** The merchant never buys above its limit.
  The farm's price no longer runs away while its stock drains. But a refused order empties the shop's shelf in
  the next period and leaves the farm without cash to work. Three runs are rescued and three made worse.
- **The price rules still do not help.** With a buyer who answers, the step up on low stock (S) still harms most
  runs. At the national figures it walks the shop's price from $38 to about $100, where it stays. Only R, the
  rule for services, is shown to be needed.
- **Credit as built here does not do what the owners' top-ups did.** It refuses a workplace whose sales have
  collapsed, at the moment it needs money most. It takes workplaces over debts of a few dollars. It leaves the
  owner rich while workers go short. With the engine's own prices it ruins four of nine pushed runs that
  top-ups hold at 227 to 240 hours. Its lending does not end either.
- **The best set by hours is still the plainest:** the engine's own prices, the spare-money rule, lent workers,
  plans down the chain, and owners' top-ups. It holds 227 to 240 hours in every pushed run at the small figures.
  The top-ups never stop ($879 to $2,598 in the last 20 periods of the runs of shortage), and in every run some
  band still goes short.

## 2. The rule as built against its prototype

Hours, small figures, 200 periods, in the round-four core (d2, a, D, R, e-kept, S, W).

| World | Push | Prototype f (round four) | The rule as built |
| --- | --- | --- | --- |
| No taxes | P2: poor harvest, for good | 185.30 | 199.20 |
| No taxes | P4: higher pay at the clinic | the same in every column | 240 |
| No taxes | P6: scarcer power | 207.75 | 121.35 ‡ |
| No taxes | P8: poor harvest for ten periods | 240 | 200.25 |
| Taxes and fund | P2: poor harvest, for good | 153.95 ‡ | 16.20 ‡ |
| Taxes and fund | P4: higher pay at the clinic | the same in every column | 240 |
| Taxes and fund | P5: a cut in the fund's taxes | 227.85 | 227.40 |
| Taxes and fund | P6: scarcer power | 212.50 | 219.90 |
| Taxes and fund | P8: poor harvest for ten periods | 240, exactly still | 223.10 |

- At the national figures the two are the same in the no-tax world's P2 and P4, and within a few hours
  elsewhere, except the taxed returning harvest: 198.55 against 209.55.
- The port is the engine's code line for line. The check compared them.
- **Why it is weaker is not known.** The first reading was that f paid idle hours past a workplace's full size
  and that those wages were income. The check refuted it: under F2 more idle hours are paid in most runs (4,264
  against 2,028 in the no-tax returning harvest). What the rows do show is in planning: the clinic stays near 40
  to 42 batches where f ran 46 to 57, and the shop attends 37, 32 and 34 hours where f paid 40.
- The rule drives a workplace's cash down to one period of what it pays out. That leaves no buffer.

## 3. Every set, by hours

Small figures, 200 periods.

| World | Push | Engine's prices, top-ups | All price rules, top-ups | With L | With L and credit | Engine's prices, credit |
| --- | --- | --- | --- | --- | --- | --- |
| No taxes | P2: poor harvest, for good | 240 | 199.20 | 164 † | 191.40 | 179.90 ‡ |
| No taxes | P4: higher pay at the clinic | 240 | 240 | 240 | 240 | 240 |
| No taxes | P6: scarcer power | 227.50 | 121.35 ‡ | 194.05 † | 20 ‡ | 22.50 ‡ |
| No taxes | P8: poor harvest for ten periods | 237.55 | 200.25 | 205 † | 199.85 | 240 |
| Taxes and fund | P2: poor harvest, for good | 240 | 16.20 ‡ | 215.70 † | 219.20 † | 120 ‡ |
| Taxes and fund | P4: higher pay at the clinic | 240 | 240 | 240 | 202.75 | 32.85 ‡ |
| Taxes and fund | P5: a cut in the fund's taxes | 240 | 227.40 | 240 | 199.80 † | 240 |
| Taxes and fund | P6: scarcer power | 234.60 | 219.90 | 197.15 † | 210.45 | 43.50 ‡ |
| Taxes and fund | P8: poor harvest for ten periods | 240 | 223.10 | 212.35 † | 206.55 | 240 |

National figures, 200 periods.

| World | Push | Engine's prices, top-ups | All price rules, top-ups | With L | With L and credit | Engine's prices, credit |
| --- | --- | --- | --- | --- | --- | --- |
| No taxes | P2: poor harvest, for good | 237 | 233.75 | 230.35 | 120 ‡ | 171.45 ‡ |
| No taxes | P4: higher pay at the clinic | 240 | 240 | 240 | 240 | 240 |
| No taxes | P6: scarcer power | 231.20 | 231 | 233.70 | 227.15 | 225.80 |
| No taxes | P8: poor harvest for ten periods | 240 | 224.65 | 224.90 | 228.25 | 240 |
| Taxes and fund | P2: poor harvest, for good | 198.45 | 214.05 | 210.40 | 218.40 | 175.45 ‡ |
| Taxes and fund | P4: higher pay at the clinic | 240 | 212.50 | 214.75 | 211.20 | 240 |
| Taxes and fund | P5: a cut in the fund's taxes | 240 | 206.70 | 207.05 | 215.15 | 213.10 |
| Taxes and fund | P6: scarcer power | 218.05 | 212.40 | 220.85 | 216 | 171.65 ‡ |
| Taxes and fund | P8: poor harvest for ten periods | 240 | 198.55 | 210.95 | 217.75 | 240 |

Small figures, 400 periods.

| World | Push | All price rules, top-ups | With L | With L and credit | Engine's prices, credit |
| --- | --- | --- | --- | --- | --- |
| No taxes | P2: poor harvest, for good | 219.80 | 139.80 † | 15 ‡ | 15 ‡ |
| No taxes | P4: higher pay at the clinic | 240 | 240 | 240 | 240 |
| No taxes | P6: scarcer power | 20 ‡ | 157.85 † | 20 ‡ | 20 ‡ |
| No taxes | P8: poor harvest for ten periods | 203.60 † | 200 † | 15 ‡ | 240 |
| Taxes and fund | P2: poor harvest, for good | 15 ‡ | 211 † | 210.60 † | 120 ‡ |
| Taxes and fund | P4: higher pay at the clinic | 240 | 240 | 202.30 | 15 ‡ |
| Taxes and fund | P5: a cut in the fund's taxes | 222.80 | 240 | 30.95 ‡ | 240 |
| Taxes and fund | P6: scarcer power | 218.40 | 209.95 † | 218.30 | 20 ‡ |
| Taxes and fund | P8: poor harvest for ten periods | 215.05 | 220.35 | 201.65 | 240 |

National figures, 400 periods.

| World | Push | All price rules, top-ups | With L | With L and credit | Engine's prices, credit |
| --- | --- | --- | --- | --- | --- |
| No taxes | P2: poor harvest, for good | 235.45 | 223.50 | 120 ‡ | 144.55 ‡ |
| No taxes | P4: higher pay at the clinic | 240 | 240 | 240 | 240 |
| No taxes | P6: scarcer power | 230.90 | 231.05 | 227.55 | 167.95 ‡ |
| No taxes | P8: poor harvest for ten periods | 225.65 | 228.15 | 224.45 | 240 |
| Taxes and fund | P2: poor harvest, for good | 213.65 | 214.55 | 215 | 32.85 ‡ |
| Taxes and fund | P4: higher pay at the clinic | 203.20 | 205.95 | 207.65 | 240 |
| Taxes and fund | P5: a cut in the fund's taxes | 201.60 | 205.95 | 212.80 | 160.95 ‡ |
| Taxes and fund | P6: scarcer power | 217.50 | 216.90 | 217.70 | 55.95 ‡ |
| Taxes and fund | P8: poor harvest for ten periods | 200.20 | 216.60 | 212.60 † | 240 |

With L nothing stops for good, but the farm and the shop make nothing in 3 to 8 of the last 20 periods of most
pushed runs. At 400 periods, in the no-tax poor harvest, the farm is at nothing from period 399 and the clinic at
period 400, at 139.80 hours. Over 20 periods that cannot be told from a closure.

## 4. A buyer who answers

The limit is the shop's posted price less $10 of handling: $28 at the opening, against the farm's $25.

- **It binds at once.** In the no-tax returning harvest at the small figures the shop refuses at period 2 (40
  units), period 5 (35) and period 7 (32). In 200 periods it refuses in 36, three of them in the last 20.
- **The farm's price stops climbing.** In round four it rose $4 a period from $25 to $65 while its stock drained
  from 36 to 16, and from period 5 to period 14 the shop paid more for a unit than its own posted price. Under L
  the farm's price saws between $25 and $33, then rests at $20 to $28. Its stock never drains after period 1.
- **The shop is never topped up** in that run, and never pays above its limit in any run.
- **What a refusal does instead.** The shop's shelf is empty the next period, because the restock comes after
  the households have bought: it sold nothing at period 3 and at period 32. The farm is left without cash: $220
  at period 2, $21 at period 7. The clinic is starved. Hours swing between 121 and 240.
- **The burden moves.** Top-ups in that run: utility $5,975, farm $2,470, clinic $2,460. The total is $10,905,
  against $3,913 without L.
- **At the national figures** L refuses in only 6 periods of 200, none after period 17. The shop's own price
  rises above the farm's instead: S steps it up about $0.95 a period, from $38 to $71.25 at period 40, and it
  rests near $103.55.
- **Against the same set without L, small figures.** Rescued: the taxed poor harvest (16.20 to 215.70 hours),
  scarcer power without taxes (121.35 to 194.05) and the tax cut (227.40 to 240). Made worse: the no-tax poor
  harvest (199.20 to 164.00), scarcer power with taxes (219.90 to 197.15) and the taxed returning harvest
  (223.10 to 212.35). Higher pay is unchanged: L never binds there.

## 5. The price rules, with a buyer who answers

Each rule taken away from the set with L, hours against that set.

- **S, the step up on low stock.** Without it most runs rise. At the national figures three taxed runs go to
  240 (higher pay, the tax cut, the returning harvest). But without it scarcer power in the no-tax world at the
  small figures is ruined (132.80 hours, the farm stopped from period 97), and scarcer power with taxes at the
  national figures falls (205.85 against 220.85).
- **W, larger steps for raw goods and power.** Mixed: better without it in four small runs, worse in three.
- **R, the rule for services.** Needed. Without it the no-tax poor harvest at the small figures is ruined (21.40
  hours, three workplaces stopped by period 115) and four national runs fall.
- **e-kept, the step down on unsold stock.** It harms the no-tax runs at the small figures and helps four runs
  at the national ones.

## 6. Credit in place of top-ups

- **Who borrows.** The farm, the utility and the clinic. The shop borrows only once, because its restocking is
  not counted in what it may borrow for.
- **How much.** In the set with every rule, small figures: $12,654 to $22,314 lent in most pushed runs of 200
  periods. Most is repaid at the same close. $1,136 to $3,648 is written off. Interest is $49 to $314.
- **Taken workplaces.** Every pushed run but one has two or three workplaces taken, many over debts of $10 to
  $270. A workplace that borrows because it is short has almost nothing above its plan at the close, so it
  cannot pay, and three closes later it is taken.
- **The refusal that kills.** A loan must stay within last period's sales. A workplace whose sales have fallen
  to nothing is refused. In the no-tax world under scarcer power the clinic's cash reaches $0 at period 4, it is
  refused, and the run is ruined by period 14 (20 hours). The owners' top-up refilled the clinic in the same
  periods.
- **Against top-ups with the engine's own prices,** credit ruins four of nine pushed runs at the small figures
  (the taxed poor harvest, taxed higher pay, and scarcer power in both worlds). Top-ups hold all four at 227.5
  to 240 hours. At the national figures credit closes the clinic in three runs by period 200 and in five by
  period 400.
- **It does not end.** In the set with every rule, lending continues in the last 20 periods of every pushed run
  but two. At 400 periods four small runs are in ruin. With the engine's own prices some lending does end:
  higher pay in the no-tax world borrows $704, all repaid at the same close, and is never carried.
- **Who goes without flips.** Under top-ups the owner is drained and goes short with everyone else. Under
  credit the owner holds $1,500 to $7,500, and the workers and the supported households carry the shortage.
  Worker households mostly hold $0, with $175 to $192 at most in two runs.
- **Money.** In every period of every run with credit, total money less the principal owed is one constant.

## 7. A shock that ends, and a shortage that lasts

- **No returning-harvest run returns.** Hours in the last 20 periods, no-tax and taxed: all price rules with
  top-ups 200.25 and 223.10; with L 205.00 and 212.35; with L and credit 199.85 and 206.55. At the national
  figures: 224.65 and 198.55; 224.90 and 210.95; 228.25 and 217.75.
- **Where it rests.** At the national figures the shop's price for food rests near $100 to $105, against $38 at
  the opening. The owner and the shop hold the money, and workers are priced out. At the small figures the sets
  swing and do not rest.
- **No set settles a lasting shortage at its target.** The best, the engine's own prices with top-ups, holds
  240 hours in the poor harvest with the owner short of every good, on $12,078 to $17,798 of top-ups.
- **Prices of stopped workplaces.** A stopped farm's price is capped at $1,000 or falls to $1. A stopped
  clinic's and shop's climb $1 a period to the end.

## 8. What the check corrected

The check recomputed the tables from the rows. They match to the cent. It refuted or corrected these claims of
the measuring agents, and this file follows the check:

- The shop paid above its own posted price from period 5 to period 14, not to period 15.
- Neither returning-harvest run with L has any shop top-up. (One was reported for the national run.)
- Taking S away lifts the taxed higher-pay and tax-cut runs to 240 only at the national figures. At the small
  figures they are at 240 already.
- Worker cash under credit is mostly $0 but reaches $175 to $192 in two runs. ("$0 to $22" was reported.)
- The explanation of why the built rule is weaker (idle wages) does not hold.
- **The bank's capital is new money.** The prototype was to carve it from the owner. It did not: every run with
  credit opens $2,400 to $2,440 richer than its twin. The agent disclosed it. It fails the stated check, so
  every credit figure here is for a world that opens with more money than the others.

## 9. What this round did not do

- No run has every price rule off and only F2, L and credit on.
- The test of needs was by product, not band by band, which is looser than the design's test.
- Credit was never measured with its own test (borrow only when what the loan pays for will sell above its cost
  and the interest): that test is not built. Profit is paid out while a debt is unserviced.
- A taken workplace is not sold, reopened or founded anew. The design's rules for that are not on the bench.
- There is one seller of each good, so a refused buyer has nowhere else to go.
- No rule was measured alone at the national figures. There was one check, not a second reader of the code.

## 10. Questions the rows do not settle

1. Is a merchant's limit its posted price, or the price its own short market cleared at? Should it buy part of
   an order instead of refusing all of it?
2. Is the bank's capital carved from the owner, with a richer opening, or new money?
3. May a workplace pay out profit while it owes and has paid nothing?
4. Does the bound on a loan use planned sales or earlier sales, and may a loan be made in the first period?
5. Is there a smallest debt below which a workplace is not taken?
6. Does a merchant's restocking count toward what it may borrow for?
7. The rule as built gives up the support its prototype gave. Is that accepted, or is the rule changed?
