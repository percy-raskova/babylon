# The twelve trades on the country bench, with bands (26 November 2026)

These are records of the country bench (`docs/superpowers/plans/2026-11-24-the-country-bench.md`) on the one
scenario of twelve trades that exists so far, recorded by stage 2 of the country's rebuilt opening
(`docs/superpowers/plans/2026-11-20-opening-stage-2-twelve-trades.md`).

**What the scenario is.** A test's own file
(`rust/crates/babylon-persistence/tests/fixtures/national_twelve_trades.defines.toml`): the twelve trades, each
workplace paying the observed wage of its trade and place, and three bands of earners in every place, with the
shipped scenario's prices, recipes and taxes. It is not the rebuilt opening. The numbers that are meant to make the
country stand are stage 5's (`ai/decisions/ADR325_the_countrys_numbers_before_the_pay_fight.yaml`,
`docs/superpowers/plans/2026-11-25-opening-stage-5-the-countrys-numbers.md`). So these records show who the
country's people are at the opening, and whether the engine and the rules RUN on them at the country's size. They
are no verdict on the twelve trades, on observed pay, on the bands or on any rule.

**"The country" here** is the 187 pooled places of ADR296, not 3,144 counties. A pooled place is kept in one or two
parts, by its counties' share of people looking for work: 316 parts in all, each with its own household accounts,
workplaces and public body.

## The files

| File | What it holds |
|---|---|
| `bands-opening.json` | the opening by band, for the nation and each of the 187 places, before any period |
| `bands-baseline.json` | 34 periods with the scenario's own order of paying and no other rule |
| `bands-all-six.json` | 34 periods with the six rules added |
| `bands-all-six-with-benefits.json` | the same with the bench's stand-in fund and its two benefits |
| `bands-timings.json` | one timed period of each set |
| `twelve-trades-*.json` | the same scenario before the bands, as recorded on 25 November |

Every figure below is a sum of a record's own figures, or, where that is said, of the compiled opening's own rows. The
records with rules are judged against this folder's baseline, never against a record of the shipped scenario.

## Its size

187 places with households, in 316 parts. 8,475 domestic workplaces, 144 foreign and 72 in dependencies (the shipped
opening has 7,283, 120 and 60). 1,900 domestic household accounts in the six kinds below, where the shipped opening has
1,584: the bands split each place's earners in three. The stage's tests pin 23,281 staffing members and 94,416 members
with rows for people who look for work, against the engine's limit of 131,072.

## Who the country's people are at the opening

| Band | Households | Persons | At work | Of them paid a wage | Looking for work | Wages a period, thousand million dollars | Pay an hour |
|---|--:|--:|--:|--:|--:|--:|--:|
| Owners | 10,011,206 | 32,083,328 | 25,091,045 | 9,038,288 | 364,047 | 77.9 | $53.87 |
| Better-paid forty | 40,038,490 | 104,073,352 | 58,814,317 | 58,814,317 | 2,353,112 | 402.8 | $42.80 |
| Lower-paid half | 50,048,120 | 130,091,632 | 73,517,882 | 73,515,544 | 2,941,380 | 312.9 | $26.60 |
| Residences | 0 | 8,200,068 | 3,873,911 | 3,574,559 | 216,746 | 8.9 | $15.63 |
| No earner, no owner | 26,215,303 | 54,423,764 | 0 | 0 | 2,724,256 | 0.0 |  |
| No earner, owner | 2,914,377 | 6,050,355 | 0 | 0 | 302,824 | 0.0 |  |

- **334,922,499 persons in 129,227,496 households.** 161,297,155 are at work and 8,902,365 look for work.
- **16,354,447 people work and draw no wage** (10.1 of every 100 at work). 16,052,757 of them are in the owners' band,
  nearly all owners at work in their own business.
- **Of those paid a wage,** the owners' band earns $53.87 an hour, the better-paid forty $42.80 and the lower-paid half
  $26.60. In 187 of the 187 places the three stand in that order.
- **The better-paid forty hold 36.5% of the jobs and 50.2% of the wages;** the lower-paid half 45.6% and 39.0%.
- **60,474,119 persons live in households with no earner,** 54,423,764 of them with no owner either.

Wayne (26163):

| Band | Households | Persons | At work | Of them paid a wage | Looking for work | Wages a period, thousand million dollars | Pay an hour |
|---|--:|--:|--:|--:|--:|--:|--:|
| Owners | 50,726 | 139,681 | 101,930 | 44,456 | 2,669 | 0.4 | $52.53 |
| Better-paid forty | 202,903 | 531,727 | 287,552 | 287,552 | 17,261 | 2.1 | $44.91 |
| Lower-paid half | 253,629 | 664,659 | 359,440 | 359,440 | 21,576 | 1.7 | $28.99 |
| Residences | 0 | 19,079 | 8,151 | 7,220 | 772 | 0.0 | $19.79 |
| No earner, no owner | 173,999 | 375,400 | 0 | 0 | 26,538 | 0.0 |  |
| No earner, owner | 19,334 | 41,713 | 0 | 0 | 2,949 | 0.0 |  |

## What ran

All 34 periods closed in every set, and nothing was refused. The money is the same sum in every row of every record:
34,770,950,958,690,514,560 millionths of a dollar. Mean time a period over the run: 5.8 seconds (no rule), 6.4 seconds
(six rules), 6.5 seconds (six rules and benefits). The machine was shared with other work, so the times are rough.

One period timed alone: 11.5 seconds with no rule, 12.8 with the six rules and 12.8 with benefits too.

## What the records show

Domestic persons at work at the close of a period:

| Period | No rule | Six rules | Six rules and benefits |
|--:|--:|--:|--:|
| 1 | 161,347,288 | 161,310,039 | 161,310,039 |
| 2 | 38,853,521 | 30,279,988 | 30,292,873 |
| 3 | 33,365,462 | 17,754,207 | 18,537,794 |
| 5 | 12,907,943 | 10,574,204 | 10,204,030 |
| 8 | 10,806,541 | 5,983,966 | 6,010,731 |
| 13 | 9,121,198 | 4,476,289 | 4,340,423 |
| 21 | 9,806,182 | 3,379,690 | 3,304,132 |
| 34 | 11,167,858 | 1,737,098 | 1,575,877 |

- **It falls in period 2, as the shipped opening falls.** 122,494,988 domestic persons are laid off in period 2 with no
  rule.
- **Businesses pay out more than they sell from the first period.** Domestic businesses pay $802.5 thousand million of
  wages in period 1 and sell $654.9 thousand million (the shipped opening: $556.6 and $432.1).
- **Household services are nearly all unmet from period 1.** The scenario's own price rule is on, so its 182 short
  domestic markets of household services clear above the posted $600 a unit: 2,548,768 units are sold of 329,390,231
  asked for at the quote, and the highest clears at $193,888. The section after this one says why.
- **Needs that households do not get** (unmet over required, domestic):

  | Need | Period | No rule | Six rules | Six rules and benefits |
  |---|--:|--:|--:|--:|
  | Food | 1 | 0.0% | 0.0% | 0.0% |
  | Food | 2 | 0.0% | 0.0% | 0.0% |
  | Food | 5 | 78.9% | 79.2% | 80.6% |
  | Food | 34 | 99.9% | 99.9% | 99.9% |
  | Household services | 1 | 99.2% | 99.2% | 99.2% |
  | Household services | 2 | 99.3% | 99.6% | 99.0% |
  | Household services | 5 | 99.8% | 99.6% | 99.9% |
  | Household services | 34 | 100.0% | 99.9% | 99.9% |
  | Housing | 1 | 1.1% | 1.1% | 1.1% |
  | Housing | 2 | 19.2% | 20.0% | 18.3% |
  | Housing | 5 | 99.0% | 98.7% | 99.3% |
  | Housing | 34 | 99.3% | 99.4% | 98.8% |

- **By band, with no rule.** Persons at work at the close:

  | Period | Owners | Better-paid forty | Lower-paid half | Residences |
  |--:|--:|--:|--:|--:|
  | 1 | 25,092,960 | 58,826,829 | 73,541,340 | 3,874,065 |
  | 2 | 2,032,614 | 15,019,468 | 21,728,578 | 60,398 |
  | 5 | 1,032,456 | 6,876,041 | 4,936,348 | 41,685 |
  | 13 | 825,350 | 5,032,675 | 3,191,887 | 36,205 |
  | 34 | 860,854 | 5,328,310 | 4,871,352 | 37,417 |

  Money held at the close of period 34, in thousand millions of dollars: owners 338.5, better-paid forty 9.5, lower-paid
  half 13.2, residences 0.1, no earner, no owner 0.8, no earner, owner 96.7. At the close of period 1: owners 113.9,
  better-paid forty 503.0, lower-paid half 474.7, residences 16.9, no earner, no owner 103.1, no earner, owner 11.5.
- **By band, six rules,** persons at work at the close of period 34: owners 329,386, better-paid forty 971,496,
  lower-paid half 420,224, residences 6,559.
- **By band, six rules and benefits,** persons at work at the close of period 34: owners 306,805, better-paid forty
  912,766, lower-paid half 340,643, residences 6,573.
- **The owner's restart, with the six rules:** over the run 41,216 resting prices were raised to cost; 377 stopped
  workplaces were restarted with $14.53 thousand million of their owners' money, 164,746 tests failed and 516 found no
  buyer.
- **The stand-in fund pays 4.8 of every 100 dollars due** over the 34 periods ($17,418 thousand million due). Its
  no-earner benefit is the baseline's first-period spend on needs a domestic person, $7,196.14 a person a period at this
  scenario's cleared prices: a stand-in of the bench, which stage 5 replaces with the scenario's own programs.

## Why most of the fall comes at once

Counted by the lead on 26 November from the compiled opening itself: who sells to whom and what each workplace
holds, before any period. Two things of the opening stop it, apart from its numbers.

**1. Most workplaces have no buyer.** The compiler gives every buyer one seller of each product: the largest
workplace of the trade in its place. A place has several. So a large share of the country's workers are at
workplaces that nobody is given to buy from, whatever the recipes and prices are, and they are laid off when the
first period closes without a sale:

| Trade | Workers | At workplaces with no buyer | Laid off in period 2, no rule |
|---|--:|--:|--:|
| Household services | 55,463,744 | 35,661,169 | 35,907,019 |
| Leisure | 16,406,061 | 16,406,061 | 16,406,061 |
| Public provision | 9,309,178 | 5,808,745 | 7,259,870 |
| Machines | 2,994,692 | 2,994,692 | 2,993,972 |
| Consumer goods | 2,058,401 | 2,058,401 | 2,058,401 |
| Food | 3,286,458 | 1,088,197 | 1,177,528 |
| Utility | 984,732 | 482,900 | 596,413 |
| Extraction | 638,542 | 193,914 | 261,319 |
| Business services | 26,744,137 | 7,160,833 | 19,206,827 |
| Premises | 9,721,849 | 3,095,193 | 8,920,855 |
| Shops | 28,678,765 | 1,727,512 | 25,777,372 |
| Materials | 5,010,596 | 3,396 | 1,929,351 |
| All | 161,297,155 | 76,681,013 | 122,494,988 |

Leisure and consumer goods have no buyer at all in this scenario (wants come with stage 5), and the buyers of
machines were not in the count. The record does not name workplaces, so the last two columns are a match of counts
and not a trace of persons. Where far more are laid off than have no buyer (shops, business services, premises),
the second cause and the scenario's own numbers do the rest.

**2. The sellers that do have buyers cannot pay for their first period.** The compiler gives a workplace two
periods of its wages and inputs as cash. A company then takes a tenth of what its workplace holds above one
payroll (`[companies] opening_treasury_bps = 1000`). The engine sets a period's wages aside first, and lets a
workplace buy a service input only with cash above a floor of one payroll. A company's workplace whose inputs
are light beside its wages has nothing left:

| Trade | Workplaces that cannot pay for their input in period 1 | Their workers | Share of the trade's workers | Of the sellers with a buyer |
|---|--:|--:|--:|--:|
| Household services | 315 | 28,121,846 | 50.7% | 153 of 187 |
| Extraction | 14 | 98,562 | 15.4% | 10 of 175 |
| Business services | 315 | 26,336,319 | 98.5% | 186 of 186 |
| All | 644 | 54,556,727 | 33.8% | |

They are the largest workplaces, so they are the ones the buyers are given. The record's own column agrees: at the close
of period 1, 314 workplaces of business services and 303 of household services are under the floor of their service
input. Every maker of goods needs business services, so nothing upstream is made. This is the cause the repair report of
20 November found on Wayne (`reports/household-units-2026-11-20/README.md`), and the Director ruled the sweep out that
day (measured then on the shipped scenario, `reports/economy-repair-2026-11-20/README.md`, candidate A). No scenario has
taken the ruling up yet.

Stage 5's plan mends both before the country's numbers are judged: its Task 7a switches the sweep off and checks
that every workplace can pay for its first period, and its Tasks 7b to 7d deal buyers to sellers in proportion to
the sellers' people. Its section "What the compiled opening showed" has the counts in full.

## What cannot be concluded from these records

- Whether the twelve trades, observed pay or the bands make a country that stands: this scenario has the shipped
  prices and recipes, most of its workplaces have no buyer, and the largest cannot pay for their first period.
- Whether any rule does its work at the country's size. The rules have nothing to restore here.
- Anything from 34 periods about where the country ends. A verdict is read from 400 periods.

## To record again

From the checkout's root, one set at a time (about four minutes each):

```
TWELVE_TRADES_SET=baseline mise run rust:test:q -- -p babylon-persistence \
  -E 'binary(national_household_units) & test(record_twelve_trades_sets)' --run-ignored only --no-capture
```

`TWELVE_TRADES_SET` is `baseline`, `all-six` or `all-six-with-benefits`. Every run writes `bands-opening.json` first.
The two sets with rules were last recorded at `3634cdb8a`, and the baseline and the opening at `7ea57304a`.
