# The country bench: first records

24 and 25 November 2026. Plan: `docs/superpowers/plans/2026-11-24-the-country-bench.md`. Ruling: ADR324.

## What this is

The bench steps the real national catalog on the engine's own period: 187 pooled places, 7,463 workplaces, 18
foreign regions and dependencies, trade routes, imports and companies. It goes around the game's turn, which cannot
yet ask for a rule. It ran five sets of rules for 34 periods each:

| Set | What is on |
|---|---|
| `baseline` | No rule: the engine as the shipped campaigns run it |
| `market` | The price of a short market (ADR312), with seven products in the order of paying |
| `no-seekers` | That, plans from spare money, hiring within means, the resting price and the goods step-down |
| `all-six` | That, people who look for work in their place, the stop without pay and the owner's restart |
| `all-six-with-benefits` | All six, and a national fund that pays a no-earner benefit and a laid-off benefit |

Each record is one JSON file here. Every figure below is a sum of a record's own figures, or two such sums divided.
`timings.json` holds one timed period of each set. The records were written three times: before the speed task,
and again after each of its halves. The three recordings are equal in every figure but the times; the files here
are the last. The runs' logs are not kept in the repository.

## What this is not

**It is not a verdict on the rules.** The opening is the shipped one (schema 7). It collapses by itself, for causes
on the supply side that were found before these rules were built, and the rebuilt opening (ADR313) is the repair.
The records of 34 periods answer three smaller questions: do the rules run at the country's size, how fast, and
what breaks. The two runs of 400 periods ("Four hundred periods", below) settle one thing only: nothing brings the
shipped country back.

The bench leaves out the companies' choice of what to hold, City PD attendance, the County Review and the game's
stored records. Each record's head lists what it leaves out.

## Do the rules run at the country's size

Yes. All five sets close all 34 periods. In every row of every record the money is the same:
29,274,357,622,617,840,000 millionths of a dollar, counting cash, money held for purchases and wages owed. Every
period, every person is explained by births and deaths, and every worker by the workers who left.

Two periods were refused on the way, each by a kind of thing the small worlds do not have. Both are mended in the
engine (see "What broke").

## What a player would see

The shipped country starves in five periods under every set, as it does with no rule on.

Food that households need and do not get (unmet over required, domestic):

| Period | No rule | Price rule | Without seekers | All six | With benefits |
|---|---|---|---|---|---|
| 3 | 0.00% | 0.60% | 0.43% | 0.43% | 0.02% |
| 4 | 24.09% | 28.94% | 28.70% | 28.70% | 25.16% |
| 5 | 80.31% | 79.35% | 78.96% | 78.96% | 80.65% |
| 8 | 97.10% | 97.24% | 97.42% | 97.50% | 97.48% |
| 34 | 99.55% | 99.79% | 99.86% | 99.86% | 99.78% |

Household services are 99.97% unmet from the first period in every set: the shipped opening supplies almost none.

People at work at the close of the period (domestic persons):

| Period | No rule | Price rule | Without seekers | All six | With benefits |
|---|---|---|---|---|---|
| 1 | 161,352,247 | 161,350,194 | 161,308,018 | 161,308,018 | 161,308,018 |
| 2 | 50,176,293 | 48,973,039 | 37,490,088 | 37,490,088 | 37,458,472 |
| 3 | 45,806,907 | 43,887,536 | 24,004,719 | 24,005,262 | 24,651,892 |
| 5 | 47,574,149 | 15,093,941 | 10,781,706 | 10,820,005 | 10,669,866 |
| 8 | 47,951,557 | 11,170,092 | 6,189,167 | 6,316,497 | 6,577,960 |
| 13 | 47,848,949 | 9,523,991 | 4,818,404 | 4,900,343 | 4,863,985 |
| 21 | 47,890,960 | 10,006,050 | 3,328,472 | 3,582,233 | 3,587,227 |
| 34 | 47,992,819 | 11,407,007 | 2,472,809 | 2,760,116 | 2,560,281 |

With no rule, 48 million people are still counted at work at period 34, while households go without 92 to 100 of
every 100 units of each need. With the adjustment rules on, the count at work falls to under 3 million. By period
34 nobody works in food in the three sets that have them (2,199,684 with no rule, 2,199,972 with the price rule
alone), and food is unmet in every set.

Housing goes faster under the price rule. Housing unmet in period 5 is 67.82% with no rule and 98.97% with the
price rule. Food comes first in the order of paying, and in a short market the price rises until what buyers can
pay for equals what there is. In `market`, the dearest domestic food market clears at $91,523 a unit in period 3
and at $4.3 million a unit in period 5, against posted prices of $304 and $311.

## Four hundred periods

Two runs of 400 periods were recorded after the speed task: no rule, and all six rules with benefits. Both close all
400 periods with the money equal in every row. They took 8 and 25 minutes. `long-baseline-summary.json` and
`long-all-six-with-benefits-summary.json` hold their rows of periods 1, 2, 3, 4, 5, 13, 34, 100, 200 and 400. The
whole records (9.6 and 9.2 million bytes) are not committed.

The shipped country does not come back in either.

| Period | At work, no rule | At work, all six with benefits | Food unmet, no rule | Food unmet, with benefits |
|---|---|---|---|---|
| 34 | 47,992,819 | 2,560,281 | 99.55% | 99.78% |
| 100 | 47,683,824 | 1,124,010 | 99.94% | 99.95% |
| 200 | 47,552,780 | 472,721 | 99.96% | 99.97% |
| 400 | 47,028,722 | 93,953 | 99.98% | 99.98% |

At period 400 with the rules, 91,517 of the 93,953 people at work are in distribution and transport, and 2,020 in
public provision. Over the 400 periods with all six rules and benefits:

- 15 people move to look for work: 2 in period 3, and one in each of 13 periods between 116 and 172;
- the stop without pay finds a workplace unable to pay 32 times, first in period 55, and holds 16 workplaces by the
  end;
- the owner's restart makes 2,286,262 tests that fail and 2,191 restarts, in 323 of the 400 periods, and owners put
  in $59.1 thousand million;
- the fund pays 4 of every 100 dollars due: $1,715 thousand million of $40,385 thousand million.

The count of people is the same in both runs, though almost nobody is fed in either: food is required for 334.9
million persons in period 1 and for 312.9 million in period 400. So in these runs births and deaths did not follow
whether needs were met.

That is a verdict on the shipped opening, and it was known: these rules cannot restore what the opening does not
supply. It is not a verdict on the rules.

## What each rule did, by the counts

These are counts of the engine's own receipts over the 34 periods of `all-six` unless a set is named.

- **Hiring within means.** Of 7,463 workplaces, those given fewer hours than they asked for: 466 in period 1, 716
  in period 2, 978 in period 5, 1,185 in period 13 and 1,339 in period 34.
- **The resting price.** Sellers whose price rests: 22 in periods 1 and 2, 4,617 in period 3, then rising to 5,629
  in period 34. The country has 7,463 workplaces.
- **The goods step-down.** 1,388 goods offers each period. Those with a planned gain: 1 in period 1, 234 in period
  5, 142 in period 13 and 51 in period 34.
- **Plans from spare money.** Plans raised above the period's own plan: 259 in period 1, 473 in period 2, 602 in
  period 5, 538 in period 13 and 409 in period 34.
- **People who look for work in their place.** Two people moved, both in period 3. In a collapse no workplace
  lacks hands, so there is nowhere to go. `no-seekers` and `all-six` are nearly the same run for that reason.
- **The stop without pay.** 7,463 rows each period. It held nobody, and no workplace was found unable to pay, in
  any period. (The record's `acted` list counts rows, so it names this rule in every period. Read the second and
  third figures of `stops`, not the list.)
- **The owner's restart.** No workplace is tested before period 3. Then 1,435 are tested in period 3, 4,030 in
  period 4 and 5,263 in period 34. Over the run 485 restarted, 154,262 failed the sales test and 105 found no
  buyer. Owners put in $13.2 thousand million in all.
- **The raise of a resting price to cost** (a step of the restart). 8 in period 1, 7 in period 2, 922 in period 3
  and 1,176 in period 34, with about a thousand in most periods between (111 and 230 in periods 18 and 19): 33,268
  in all. Whether those are the same sellers each time, lowered again in between, is not counted yet.

## Benefits

Stand-in figures, set by the lead and told to the Director (the plan's calls 15 and 22): the fund takes half of
each domestic tax rate; the no-earner benefit is what one person's needs cost at the opening's prices,
$1,595.03 a person a period; the laid-off benefit is half the pay of the job lost for six and a half periods.

The no-earner benefit goes to 635 accounts with 60,474,126 persons, so it is due $96.5 thousand million each
period. The country's 316 public bodies hold $77.1 thousand million between them at the opening, so the two
periods of reserve that the design gives the fund cannot be taken from them. The fund opens with no cash.

Thousand million dollars, in `all-six-with-benefits`:

| Period | No-earner due | paid | Laid-off due | paid | Fund's cash at the close |
|---|---|---|---|---|---|
| 1 | 96.5 | 0.0 | 0.0 | 0.0 | 66.7 |
| 2 | 96.5 | 66.7 | 0.0 | 0.0 | 59.9 |
| 3 | 96.5 | 19.1 | 206.4 | 40.8 | 31.8 |
| 5 | 96.5 | 6.7 | 248.0 | 17.3 | 22.3 |
| 8 | 96.5 | 6.0 | 264.4 | 16.5 | 22.8 |
| 13 | 96.5 | 19.5 | 10.3 | 2.1 | 21.4 |
| 34 | 96.4 | 12.0 | 1.1 | 0.1 | 12.2 |

Over the 34 periods $5,101 thousand million is due and $722 thousand million is paid: 14 in every 100. From period 4
the fund pays between 6 and 21 of every 100 dollars due. With benefits, domestic households hold more money at
period 34 ($500 thousand million against $308) and domestic businesses sell more ($165 thousand million in the
period against $97), but no more people are at work.

The laid-off benefit is for a member paid a wage. An owner who works in their own business, or an unpaid family
member, who loses that work is paid none (see "What broke", 2).

## Public providers

The country has 977 public provision sites: 959 domestic, 6 in dependencies and 12 foreign. 976 are funded by an
operating grant from their public body. One, in Jefferson County, Texas, has no grant and nobody at work.

Under `all-six`, counted over all 977:

- none is held by the stop without pay, in any period;
- hiring within means gives fewer hours than asked to 40 of them in period 1, 2 in period 5 and 36 in period 34;
- from period 3 between 772 and 805 of the 976 funded ones have a resting price;
- the owner's restart tests 238 of the funded ones in period 3 and between 746 and 785 in every period after. Every
  test fails. None is restarted;
- the one with no grant has its price raised once, in period 1, from $1.00 to its ceiling of $4.00, and is tested
  and fails every period from period 3.

Domestic persons at work in public provision fall from 9.3 million to about 2 million in period 2 in every set,
and stay near there under the rules (1.2 million at period 34 with no rule, 1.7 to 2.0 million with rules).

So the rules treat a public provider as a business: its price rests, and about 770 of them are tested for an
owner's restart every period. Whether they should is for the Director. The ruling that public provision does not
clear by price (ADR312, P12) bears on it.

## How fast

Seconds for one period on this machine, over the 34 periods of each record:

| Set | As first recorded: mean | slowest | After the speed task: mean | slowest |
|---|---|---|---|---|
| `baseline` | 1.4 | 1.6 | 1.3 | 1.8 |
| `market` | 3.8 | 6.3 | 4.0 | 7.6 |
| `no-seekers` | 8.2 | 12.2 | 3.9 | 6.8 |
| `all-six` | 136.6 | 153.5 | 4.1 | 7.1 |
| `all-six-with-benefits` | 135.8 | 151.8 | 4.4 | 7.3 |

As first recorded, a period with all six rules took about 25 seconds while the country stood and about 150 once it
had collapsed. The slow periods followed the count of stopped workplaces the owner's restart tests: 94 seconds with
1,435 tests, 126 with 4,030, 153 with 5,263. A profile found the cause. For every workplace it tested, and for every
resting price it raised, the engine made a table of every wage in the country anew. Timing one period of each set
had hidden this, because nothing is stopped in period 1.

The plan's Task 7 mends it in two halves (`701bffc61`, `c2b13488f`): the restart, the market's tables, spare money,
the hiring bound and the staffing in places each build their tables once a period. No rule's logic changed. The
engine's tests, the small worlds' tests and the fifteen long tests keep every value, and the five records came out
the same in every figure but the times. The slowest period of every set is now its first.

A turn of the game is meant to take ten seconds. All five sets now fit that at the country's 187 pooled places. What
is left of a period with the price rule on is mostly the market itself: workplaces restocking at the market's price
(about 2 seconds) and households' buying (about 1). The speed task's list did not name those.

## What broke

1. **Period 1 with all six rules: the engine refused the period** (`ServiceInvariant`). The restart raises a resting
   price to one unit's cost. For the public provider with no grant that was $25.36, above its offer's ceiling of
   $4.00. Mend `7b953cded`: a raise never leaves its offer's own range, and a provider funded by a grant is left
   alone. The small worlds have no public provider.
2. **Period 2 with benefits: the engine refused the period** (`PublicProgramInvariant`). Where people look for work
   in their place, the engine keeps two counts of who holds a record of layoffs, and they must agree. One counted
   by household alone, the other by a wage and the household. The country has 316 owners who work in their own
   business and 361 unpaid family members beside its wage members. In period 2 the counts differed by exactly the
   667 of them who had lost their work (16,045,004 and 301,543 persons). Mend `cf43785a6`: one rule for both
   counts, a record is for a member paid a wage. The small worlds pay every member a wage.

After each mend the engine's tests, the small worlds' tests and the fifteen long tests pass with no expected value
changed.

## What cannot be concluded from these records

- Whether any rule restores a country that can stand. The shipped opening leaves the rules nothing to restore, in
  34 periods and in 400.
- Whether people who look for work in their place, or the owner's restart, do their work at the country's size.
  Both need workplaces that are hiring.
- What the benefits do in a country that stands. Here the fund's taxes collapse with everything else.
- Anything about bands, the twelve trades or observed pay: the shipped opening has none of them.

## Open for the Director

1. Should the rules apply to public providers at all, and should one with no grant keep its token price?
2. What is a ruined small owner paid, if anything? It joins the open question of ADR318 about a household with
   one business.
3. The fund's stand-in figures, and that it opens with no cash. The other course is to leave benefits out of the
   bench until the rebuilt opening sets real rates.

## To record again

From the checkout's root. The five sets take about ten minutes.

```
mise run rust:test:q -- -p babylon-persistence \
  -E 'binary(national_household_units) & test(record_country_bench_sets)' --run-ignored only --no-capture
```

`COUNTRY_BENCH_SET=<name>` records one set. `record_country_bench_long` records 400 periods of the baseline and of
the set with benefits (`COUNTRY_BENCH_LONG_PERIODS` sets another length); its summaries land here and its whole
records in the build's own temporary folder, which the test prints.
