# The twelve trades on the country bench (25 November 2026)

These are records of the country bench (`docs/superpowers/plans/2026-11-24-the-country-bench.md`) on the one
scenario of twelve trades that exists so far. They were recorded by stage 2's Task 8b
(`docs/superpowers/plans/2026-11-20-opening-stage-2-twelve-trades.md`) at commit `8a4f4c01f`.

**What the scenario is.** A test's own file
(`rust/crates/babylon-persistence/tests/fixtures/national_twelve_trades.defines.toml`): the twelve trades, and each
workplace paying the observed wage of its trade and place, with the shipped scenario's prices, recipes and taxes. It
is not the rebuilt opening. The numbers that are meant to make the country stand are stage 5's
(`ai/decisions/ADR325_the_countrys_numbers_before_the_pay_fight.yaml`). So these records show whether the engine and
the rules RUN on twelve trades and observed pay at the country's size. They are no verdict on the twelve trades, on
observed pay or on any rule.

**"The country" here** is the 187 pooled places of ADR296, not 3,144 counties.

## The files

| File | What it holds |
|---|---|
| `twelve-trades-baseline.json` | 34 periods of the scenario as it is, with its own order of paying and no other rule |
| `twelve-trades-all-six.json` | 34 periods with the six rules added |
| `twelve-trades-all-six-with-benefits.json` | the same with the bench's stand-in fund and its two benefits |
| `twelve-trades-timings.json` | one timed period of each set |

Every figure below is a sum of a record's own figures, read by the lead. The records with rules are judged against
this folder's baseline, never against a record of the shipped scenario.

## Its size

187 places with households. 8,475 domestic workplaces, 144 foreign and 72 in dependencies (the shipped opening has
7,283, 120 and 60). 1,584 domestic household accounts, as shipped. 8,691 staffing pools and 23,877 members. 2,436
offers of goods and 5,914 of services. People who look for work need 78,763 member rows, against the engine's limit
of 131,072.

## What ran

All 34 periods closed in every set. No rule and no check of the bench refused anything. The money is the same sum in
every row of every record.

One period, timed alone: 12.6 seconds with no rule, 14.6 with the six rules, 13.9 with benefits too. Over 34 periods
the mean is 5.8, 7.1 and 7.2 seconds a period (the shipped opening: 1.2 with no rule and 3.7 with rules and
benefits, over 400 periods).

## What the records show

Domestic persons at work at the close of a period:

| Period | No rule | Six rules | Six rules and benefits |
|--:|--:|--:|--:|
| 1 | 161,347,288 | 161,310,039 | 161,310,039 |
| 2 | 38,734,712 | 30,280,395 | 30,335,347 |
| 5 | 12,492,128 | 10,274,568 | 10,125,190 |
| 13 | 9,060,391 | 4,570,635 | 4,340,448 |
| 34 | 11,202,191 | 2,158,434 | 1,927,192 |

- **It falls as the shipped opening falls.** 122.6 million domestic persons are laid off in period 2 with no rule
  (the shipped opening on this bench: 111.2 million). Food is met in periods 1 and 2. It is 26% to 30% unmet in
  period 4, about 80% in period 5 and 99.8% in period 34, across the three sets.
- **Businesses pay out more than they sell from the first period.** Domestic businesses pay $802.5 thousand million
  of wages in period 1 and sell $655.3 thousand million (the shipped opening: $556.6 and $432.1).
- **The two new trades have no buyer in this scenario.** No need names consumer goods or leisure, no recipe uses
  them, and wants come with stage 5. Nothing is sold of either in any period. Their 18,464,462 workers (2,058,401
  and 16,406,061) are at work in period 1 and none is from period 2, in every set.
- **Household services are 99.2% unmet in period 1** (the shipped opening: 99.97%). The scenario's own price rule is
  on from the first period, so its 183 short domestic markets of household services clear above the posted $600 a
  unit; the highest clears at $193,915.
- **The stand-in benefit is not like the shipped one.** The bench sets its no-earner benefit at the baseline's
  first-period spend on needs a domestic person. Here that spend is counted at those cleared prices: $7,198.79 a
  person a period, where the shipped scenario's stand-in is $1,595.03. One period of it is $435.3 thousand million,
  against $128.7 thousand million that all public bodies hold. It is a stand-in of the bench. Stage 5 replaces it
  with the scenario's own programs.

## What comes after

- The Director ruled on 25 November that public providers are left out of the resting price and the owner's
  restart (ADR325). The bench plan's Task 9 builds that and records the two sets with rules again, so
  `twelve-trades-all-six.json` and `twelve-trades-all-six-with-benefits.json` will change. The baseline will not.
- Stage 2's Tasks 9 to 10b add the three earning bands and record this scenario with them.
- Stage 5 sets the numbers. Its scenario replaces this one on the bench.
