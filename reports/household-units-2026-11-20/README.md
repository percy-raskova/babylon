# Wayne's pooled household accounts, today

Records what the eight pooled Wayne budget groups hold and are paid, read from the engine's own
accounts in every one of 34 periods. It is the measurement that step A (household units) starts from.
Test-only: no engine or persistence source changed.

## What was run

- Campaign `00000000-0000-0000-0000-002616317036`, replay seed 319, compiler `national-world-v12`
  (the shipped national campaign with no household units).
- No organizer commitment is made in any period, so the run is the County Review's `no-contact` line.
- Command, from the repository root:
  `mise run rust:test:q -- -p babylon-persistence -E
  'binary(national_household_units) & test(record_wayne_pooled_accounts)' --run-ignored ignored-only`
- Test file `rust/crates/babylon-persistence/tests/national_household_units.rs`; reader
  `rust/crates/babylon-persistence/tests/support/household_accounts.rs`.

## Time it took

The recorder (capture, opening and 34 closes, in memory) took 134 s inside nextest (2 min 34 s of wall
time for the command, build included). The cheap opening test runs in about 4 s after its build.

## Where each figure comes from

- Households and persons: the account's household cohort. Labor force: people at work plus people
  seeking work, for each household, summed over the County Review roster rows of the account's group.
- Cash: the money book. Pantry: the historical cost of the stocks the account owns. Net assets: the
  account's capital row (the engine checks it against the money book at every close). The rest
  (freight and claims carried, purchase escrows, wages owed to it) is read separately, and cash +
  pantry + the rest equals net assets for every account at every period.
- Ownership income: the company payouts plus the site distributions paid to the account; their sum
  is checked against the income statement's distribution income. Wages, support and aid are the
  statement's wage, public transfer and gift income. Wage tax is the sum over the wage-income tax
  receipts of the account. The county register's own facts for the period (ownership, support, aid
  income, wage tax collected, closing households) are asserted equal to these in every period.
- Needs: the quantity required and the quantity unmet come from the household consumption receipt
  (goods) or household service receipt (services). Cost of needs = required x the period's price, the
  offer of the account's purchase-policy retailer, read before the period closes.
- The top tenth is the groups whose households are all in the top 1% or next 9%. It is exactly the
  groups with ownership income (asserted). Its wealth share is its net assets over the net assets of
  all groups that have households. Money is added; no rate is averaged.

## Unmet, could not pay, paid but not supplied

- **unmet**: people or households that needed a good and did not get it (required minus consumed).
- **unpaid** ("could not pay"): requested minus admitted. The order was cut back because the account
  could not fund it.
- **unsupplied** ("paid and not supplied"): admitted minus fulfilled (goods), or admitted minus
  performed (services). The account paid and the seller delivered less.

## Findings

### The top tenth's share of household wealth, beside the law's two thirds (6667 bp)

| Period | share (bp) |
|---|---|
| 0 | 1021 |
| 1 | 894 |
| 2 | 884 |
| 5 | 1621 |
| 10 | 2271 |
| 20 | 2539 |
| 34 | 2925 |

The top tenth is the two groups with ownership income (no-earner-owner, which holds the whole
top 1%, and earning-owner).

### Top tenth: ownership pay beside the cost of its needs (millions of dollars, each period)

| Period | ownership pay | cost of needs | ownership over needs (bp) |
|---|---|---|---|
| 1 | 0 | 289,441,760 | 0 |
| 2 | 81,362,648 | 289,981,600 | 2805 |
| 3 | 122,067,331 | 291,320,698 | 4190 |
| 4 | 142,431,644 | 298,207,785 | 4776 |
| 5 | 152,610,186 | 305,305,579 | 4998 |
| 6 | 149,388,022 | 312,403,898 | 4781 |
| 7 | 128,182,589 | 319,502,742 | 4011 |
| 8 | 99,201,933 | 326,602,113 | 3037 |
| 9 | 73,416,334 | 333,702,009 | 2200 |
| 10 | 55,016,939 | 340,798,878 | 1614 |
| 11 | 43,763,648 | 347,897,338 | 1257 |
| 12 | 37,821,170 | 354,999,924 | 1065 |
| 13 | 34,752,392 | 362,098,060 | 959 |
| 14 | 32,956,722 | 369,196,578 | 892 |
| 15 | 31,056,851 | 376,294,175 | 825 |
| 16 | 29,011,969 | 383,394,762 | 756 |
| 17 | 24,366,254 | 390,493,076 | 623 |
| 18 | 19,950,165 | 397,593,100 | 501 |
| 19 | 16,699,783 | 404,692,106 | 412 |
| 20 | 14,539,868 | 411,790,025 | 353 |
| 21 | 13,198,378 | 418,889,677 | 315 |
| 22 | 12,408,800 | 425,989,664 | 291 |
| 23 | 11,940,473 | 433,089,985 | 275 |
| 24 | 11,617,140 | 440,189,122 | 263 |
| 25 | 11,308,158 | 447,285,460 | 252 |
| 26 | 10,955,643 | 454,385,123 | 241 |
| 27 | 10,512,194 | 461,485,072 | 227 |
| 28 | 10,140,187 | 468,582,080 | 216 |
| 29 | 9,805,905 | 475,677,640 | 206 |
| 30 | 9,519,926 | 482,776,668 | 197 |
| 31 | 9,144,671 | 489,872,562 | 186 |
| 32 | 8,803,305 | 496,970,311 | 177 |
| 33 | 8,542,791 | 504,068,250 | 169 |
| 34 | 8,342,403 | 511,161,107 | 163 |

### The other nine tenths: ownership pay (zero) beside the cost of their needs (millions of dollars)

| Period | ownership pay | cost of needs |
|---|---|---|
| 1 | 0 | 2,545,416,694 |
| 2 | 0 | 2,549,220,825 |
| 3 | 0 | 2,560,025,751 |
| 4 | 0 | 2,620,548,566 |
| 5 | 0 | 2,682,966,306 |
| 6 | 0 | 2,745,384,040 |
| 7 | 0 | 2,807,802,596 |
| 8 | 0 | 2,870,224,030 |
| 9 | 0 | 2,932,645,950 |
| 10 | 0 | 2,995,068,141 |
| 11 | 0 | 3,057,491,596 |
| 12 | 0 | 3,119,913,708 |
| 13 | 0 | 3,182,341,726 |
| 14 | 0 | 3,244,766,833 |
| 15 | 0 | 3,307,192,583 |
| 16 | 0 | 3,369,617,504 |
| 17 | 0 | 3,432,041,382 |
| 18 | 0 | 3,494,468,128 |
| 19 | 0 | 3,556,890,744 |
| 20 | 0 | 3,619,315,990 |
| 21 | 0 | 3,681,739,523 |
| 22 | 0 | 3,744,164,070 |
| 23 | 0 | 3,806,585,075 |
| 24 | 0 | 3,869,003,770 |
| 25 | 0 | 3,931,426,110 |
| 26 | 0 | 3,993,844,335 |
| 27 | 0 | 4,056,259,748 |
| 28 | 0 | 4,118,673,747 |
| 29 | 0 | 4,181,086,191 |
| 30 | 0 | 4,243,495,273 |
| 31 | 0 | 4,305,905,837 |
| 32 | 0 | 4,368,311,042 |
| 33 | 0 | 4,430,712,335 |
| 34 | 0 | 4,493,118,291 |

### Each owning group, for each household (dollars)

| Group | Period | ownership pay | cost of needs |
|---|---|---|---|
| no-earner-owner | 1 | 0 | 3,708 |
| no-earner-owner | 2 | 1,161 | 3,709 |
| no-earner-owner | 5 | 2,179 | 3,898 |
| no-earner-owner | 10 | 785 | 4,353 |
| no-earner-owner | 20 | 208 | 5,262 |
| no-earner-owner | 34 | 119 | 6,535 |
| earning-owner | 1 | 0 | 4,293 |
| earning-owner | 2 | 1,161 | 4,303 |
| earning-owner | 5 | 2,178 | 4,533 |
| earning-owner | 10 | 785 | 5,059 |
| earning-owner | 20 | 208 | 6,112 |
| earning-owner | 34 | 119 | 7,586 |

### First period with unmet need, and with could-not-pay and paid-not-supplied, by group

| Group | first unmet | first unpaid | first unsupplied |
|---|---|---|---|
| no-earner-owner | 1 | 4 | 1 |
| earning-nonowner | 1 | never | 1 |
| no-earner-nonowner (claimants) | 1 | 3 | 1 |
| earning-owner | 1 | never | 1 |
| collective-residence | 1 | never | 1 |
| earning-nonowner (aid donors) | 1 | never | 1 |
| no-earner-nonowner | 1 | 3 | 1 |
| no-earner-nonowner (aid partners) | 1 | 1 | 3 |

### Other persons for each household, at the opening (C8)

| Group | households | persons | labor force | other persons | admits every crewless unit |
|---|---|---|---|---|---|
| no-earner-owner | 19334 | 41713 | 2949 | 38764 | true |
| earning-nonowner | 456528 | 1196378 | 685824 | 510554 | true |
| no-earner-nonowner (claimants) | 2 | 2 | 2 | 0 | false |
| earning-owner | 50726 | 139681 | 104600 | 35081 | false |
| earning-nonowner (aid donors) | 4 | 8 | 4 | 4 | true |
| no-earner-nonowner | 173993 | 375394 | 26536 | 348858 | true |
| no-earner-nonowner (aid partners) | 4 | 4 | 0 | 4 | true |

Groups where `admits_every_crewless_unit` is false: no-earner-nonowner (claimants), earning-owner.

Homes are not in yet: a household's wealth in this engine is cash, a pantry and claims carried at zero.
