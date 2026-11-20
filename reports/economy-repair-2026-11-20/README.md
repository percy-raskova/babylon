# The health of the national economy, today and under candidate repairs

Measures the whole national economy (every domestic county, every foreign region and dependency) in
every one of 34 periods of the shipped campaign, from the engine's own receipts and committed state.
Test-only: no engine, persistence or scenario source changed.

## The record: `national-economy-health.json`

- Campaign `00000000-0000-0000-0000-002616317036`, replay seed 319, compiler `national-world-v12`,
  no organizer commitment (the County Review's `no-contact` line), the shipped policy text.
- Command, from the repository root (about 160 s inside nextest after the build):
  `mise run rust:test:q -- -p babylon-persistence -E
  'binary(national_household_units) & test(record_national_economy_health)' --run-ignored ignored-only`
- Recorder `record_national_economy_health` in
  `rust/crates/babylon-persistence/tests/national_household_units.rs`; reader
  `rust/crates/babylon-persistence/tests/support/economy_health.rs`. The cheap opening test
  `the_health_reader_adds_back_at_the_opening` proves the reader's sums against the opening
  (households and persons by scope, site count, the panel, cash against the money book).
- Money is millionths, as decimal strings. Every figure is a sum; a share is two sums divided, in
  basis points (`unmet_share_bps`), never an average of rates. One period is one line; `columns`
  names the fields of each array.

What each period holds:

- `supply`: for each of the six needs, the national sum over the 187 domestic counties with
  households, as [required, unmet, unpaid (requested less admitted), unsupplied (admitted less
  fulfilled or performed), unmet share]; the counties in each band of unmet share (0, up to 10%, up
  to 50%, above 50%, nothing required); and the five counties with the most unmet units.
- `panel`: the same rows for Wayne 26163, Cook 17031, Los Angeles 06037, Harris 48201, the domestic
  county with the fewest households at the opening (Kalawao HI 15005, 40 households) and the one whose
  Food and Extraction workplaces employ the most people at the opening (Kern CA 06029, 296,153).
  The rules are written in the file.
- `abroad`: the same rows for each foreign region and dependency.
- `jobs`: by scope (domestic, foreign, dependency) and economic function: at work and looking for
  work at the open and the close, hires and layoffs (staffing receipts).
- `businesses`: by scope and function: sites; sites ending the period with cash under their
  service-input floor and under their replenishment floor; sites with a plan and zero output; wages
  accrued, sales and cash.
- `products`: for each commodity, the lowest and highest domestic and foreign offer, the quantity
  sold (households: fulfilled; firms: admitted delivery orders; services: performed) and its value;
  and for its designed process, a batch's cost (labor at the default wage of $24 an hour, inputs at
  the lowest domestic offer) beside its receipts at the lowest and highest domestic offer, with the
  verdict `covers cost`, `below cost`, or `below cost at the lowest seller`.
- `trade`: imports from each foreign region or dependency to domestic buyers, by good, as [open
  backlog, ordered, shipped, backlog after, supplier stock, bound by]; the same for Wayne's buyers
  alone; and each capacity that bound (a route corridor or a supplier's handling capacity with less
  than one unit left): what it could carry, what it carried, how many flows used it and its three
  largest users.
- `money`: cash by kind of account (households and businesses by scope, companies, public bodies,
  organizations), purchase escrow, wages owed and the total.

## Today's economy (shipped policy)

National unmet share, by need (unmet over required, summed over every domestic county):

| Period | food | materials | utility | housing | household_services | public_provision |
|---|---|---|---|---|---|---|
| 1 | 0.0% | 0.0% | 11.8% | 0.0% | 100.0% | 7.6% |
| 2 | 0.0% | 0.0% | 0.7% | 0.7% | 100.0% | 2.5% |
| 3 | 0.0% | 0.0% | 19.1% | 19.0% | 100.0% | 20.5% |
| 4 | 24.1% | 5.2% | 51.9% | 50.9% | 100.0% | 52.4% |
| 5 | 80.3% | 31.4% | 68.3% | 67.8% | 100.0% | 71.1% |
| 13 | 98.8% | 98.6% | 79.9% | 92.2% | 100.0% | 98.1% |
| 34 | 99.5% | 99.4% | 92.0% | 96.9% | 100.0% | 98.3% |

Counties in each band of unmet share (unmet 0 / up to 10% / up to 50% / above 50%), of 187:

| Period | food | materials | utility | housing | household_services | public_provision |
|---|---|---|---|---|---|---|
| 1 | 185/2/0/0 | 185/2/0/0 | 121/18/43/5 | 185/2/0/0 | 4/1/3/179 | 141/12/34/0 |
| 2 | 185/2/0/0 | 185/2/0/0 | 172/10/5/0 | 172/10/5/0 | 1/4/3/179 | 99/72/16/0 |
| 3 | 185/2/0/0 | 185/2/0/0 | 130/5/32/20 | 110/21/36/20 | 0/1/4/182 | 80/49/37/21 |
| 4 | 63/27/61/36 | 129/8/34/16 | 1/10/113/63 | 0/2/125/60 | 0/0/0/187 | 2/11/113/61 |
| 5 | 1/13/42/131 | 64/16/33/74 | 0/8/84/95 | 0/2/92/93 | 0/0/0/187 | 0/10/79/98 |
| 13 | 0/1/4/182 | 0/0/0/187 | 0/4/51/132 | 0/0/2/185 | 0/0/0/187 | 0/4/13/170 |
| 34 | 0/0/1/186 | 0/0/0/187 | 0/3/14/170 | 0/0/0/187 | 0/0/0/187 | 0/1/5/181 |

People at work and sites under a floor (domestic jobs at the close; sites in every scope):

| Period | at work | looking for work | hires | layoffs | sites under service-input floor | under replenishment floor | zero output with a plan |
|---|---|---|---|---|---|---|---|
| 1 | 161,352,247 | 8,847,273 | 55,092 | 0 | 630 | 630 | 5703 |
| 2 | 50,175,981 | 120,023,539 | 884 | 111,177,150 | 651 | 651 | 949 |
| 3 | 45,806,147 | 124,393,373 | 366,010 | 4,735,844 | 828 | 828 | 969 |
| 4 | 46,503,822 | 123,695,698 | 860,218 | 162,543 | 833 | 833 | 1064 |
| 5 | 47,573,621 | 122,625,899 | 1,259,855 | 190,056 | 940 | 942 | 1169 |
| 13 | 47,848,513 | 122,351,007 | 41,450 | 27,293 | 1131 | 1145 | 1286 |
| 34 | 47,992,382 | 122,207,138 | 3,168 | 3,778 | 1364 | 1682 | 1330 |

- Supply. Food and materials hold for three periods on opening stock and collapse from period 4;
  household services are never supplied anywhere; utility and housing fall from period 3. By period
  34 more than 99% of food is unmet and 186 of 187 counties lack more than half their food. Abroad
  is no better: every foreign region and dependency has 100% of its food unmet at period 34.
- Jobs. 161.4 million at work at the close of period 1; 111.2 million are laid off in period 2,
  and employment stays near 48 million (122 million looking) to period 34.
- Businesses. From period 1, 315 domestic business-services and 315 household-services sites end
  under their service-input floor; 1,054 of 1,057 business-services sites and nearly every goods
  producer have a plan and produce nothing in period 1. By period 34, 1,364 sites are under a
  service-input floor and 1,682 under a replenishment floor.
- Products. Business services ($100 against a unit cost of $252.19) and resources ($40 against
  $69.88) are below cost at every seller in every period; public provision is below cost by design
  (its provider is paid by public grants). Every other private product covers its cost.
- Money. The total (cash, escrow and wages owed) is $29,274,357,622,617.84 in every period: money is
  conserved. Idle cash sits abroad: foreign businesses hold $14.2 trillion at period 1.
- Trade, and Sub-Saharan Africa's food. Wayne's retailer orders 443,064 parcels of food a period
  from Sub-Saharan Africa and receives about 30. Supplier stock is not the limit (16 to 19 billion
  parcels). The route's two shared corridors (`80d488dedd3e` and `a5db7fd597e5`) carry
  1,000,000,000 grams a period (71,428 parcels) and are full every period: 319 flows share them, and
  the largest users are domestic food from Kern CA (06029) to Sub-Saharan Africa and to West Asia
  and North Africa, and materials from Los Angeles to Sub-Saharan Africa. The engine shares a full
  corridor in proportion to requested grams (`outbound/orders.rs` `limit_allocations`), so Wayne's
  share is a few hundred kilograms. All of Sub-Saharan Africa's food to the whole country is about
  730 parcels a period.

## Candidate repairs, by policy text only (`experiments.json`)

Each candidate replaces exact lines of the shipped policy text inside the catalog input of the test
(`defines.toml` is not edited) and plays the same 34 periods. `experiments.json` holds, for each,
its edits and the summary rows below (periods 1, 2, 3, 4, 5, 13, 34); the full records are written
under the cargo target's `tmp/economy-repair/` and are not committed.

Command, from the repository root (about 35 minutes for all twelve; `ECONOMY_CANDIDATES=A,B` plays
only those and writes `experiments-partial.json` under the target's tmp instead):
`mise run rust:test:q -- -p babylon-persistence -E
'binary(national_household_units) & test(record_economy_repair_candidates)' --run-ignored ignored-only`.
The Wayne supply chain of one candidate (`ECONOMY_CANDIDATE=E`):
`... & test(record_wayne_supply_chain_of_a_candidate)' --run-ignored ignored-only`.

| Candidate | Edits (cumulative where named) |
|---|---|
| A | `opening_treasury_bps` 1000 -> 0 |
| B | A + business services `output_units_per_batch` 16 -> 48 |
| C | B + extraction `output_units_per_batch` 8 -> 16 and `resource_deposit` 8 -> 16 |
| D | B + extraction 32 units from 32 deposit |
| E | D + energy utilities `output_units_per_batch` 160 -> 320 |
| F | E + `foreign_procurement_bps` 2500 -> 0 |
| G | C + `foreign_procurement_bps` 2500 -> 0 |
| H | F + `reserve_food_support_periods` 1 -> 16 |
| I | F + food `output_units_per_batch` 16 -> 32 |
| J | I + `wage_tax_bps` and `operating_income_tax_bps` 1500 -> 0 |
| K | I + `reserve_food_support_periods` 1 -> 16 |

National unmet share by need, food counties by band, domestic jobs at the close and sites under a floor (every scope):

| Candidate | period | food | materials | utility | housing | household_services | public_provision | food counties (0/10/50/>50) | at work | looking | under service floor | under replenishment floor |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| shipped | 1 | 0.0% | 0.0% | 11.8% | 0.0% | 100.0% | 7.6% | 185/2/0/0 | 161,352,247 | 8,847,273 | 630 | 630 |
| shipped | 2 | 0.0% | 0.0% | 0.7% | 0.7% | 100.0% | 2.5% | 185/2/0/0 | 50,175,981 | 120,023,539 | 651 | 651 |
| shipped | 3 | 0.0% | 0.0% | 19.1% | 19.0% | 100.0% | 20.5% | 185/2/0/0 | 45,806,147 | 124,393,373 | 828 | 828 |
| shipped | 4 | 24.1% | 5.2% | 51.9% | 50.9% | 100.0% | 52.4% | 63/27/61/36 | 46,503,822 | 123,695,698 | 833 | 833 |
| shipped | 5 | 80.3% | 31.4% | 68.3% | 67.8% | 100.0% | 71.1% | 1/13/42/131 | 47,573,621 | 122,625,899 | 940 | 942 |
| shipped | 13 | 98.8% | 98.6% | 79.9% | 92.2% | 100.0% | 98.1% | 0/1/4/182 | 47,848,513 | 122,351,007 | 1131 | 1145 |
| shipped | 34 | 99.5% | 99.4% | 92.0% | 96.9% | 100.0% | 98.3% | 0/0/1/186 | 47,992,382 | 122,207,138 | 1364 | 1682 |
| A | 1 | 0.0% | 0.0% | 15.8% | 0.0% | 39.2% | 9.7% | 185/2/0/0 | 161,351,676 | 8,847,844 | 0 | 0 |
| A | 2 | 0.0% | 0.0% | 0.7% | 0.7% | 50.2% | 2.5% | 185/2/0/0 | 49,438,667 | 120,760,853 | 234 | 234 |
| A | 3 | 0.0% | 0.0% | 37.2% | 40.6% | 60.4% | 37.7% | 166/21/0/0 | 44,004,923 | 126,194,597 | 411 | 411 |
| A | 4 | 8.8% | 5.8% | 73.1% | 73.0% | 83.1% | 71.7% | 48/64/69/6 | 42,108,562 | 128,090,958 | 434 | 434 |
| A | 5 | 51.2% | 29.6% | 79.0% | 78.9% | 92.3% | 78.4% | 4/9/97/77 | 41,991,037 | 128,208,483 | 467 | 469 |
| A | 13 | 98.2% | 99.0% | 85.5% | 91.7% | 100.0% | 97.2% | 0/0/9/178 | 40,849,652 | 129,349,868 | 694 | 702 |
| A | 34 | 99.2% | 99.7% | 91.6% | 96.8% | 100.0% | 99.0% | 0/0/2/185 | 41,614,185 | 128,585,335 | 1011 | 1303 |
| B | 1 | 0.0% | 0.0% | 15.8% | 0.0% | 39.2% | 9.7% | 185/2/0/0 | 161,339,122 | 8,860,398 | 0 | 0 |
| B | 2 | 0.0% | 0.0% | 0.7% | 0.7% | 50.2% | 2.5% | 185/2/0/0 | 43,821,414 | 126,378,106 | 43 | 43 |
| B | 3 | 0.0% | 0.0% | 33.5% | 38.1% | 57.6% | 34.0% | 166/21/0/0 | 39,559,260 | 130,640,260 | 50 | 50 |
| B | 4 | 4.5% | 1.8% | 67.8% | 68.0% | 75.6% | 66.2% | 59/71/54/3 | 38,467,759 | 131,731,761 | 227 | 227 |
| B | 5 | 23.9% | 15.6% | 80.3% | 79.0% | 87.6% | 78.4% | 7/17/136/27 | 38,357,325 | 131,842,195 | 264 | 266 |
| B | 13 | 95.4% | 93.5% | 86.2% | 87.8% | 99.9% | 87.4% | 0/0/4/183 | 38,489,623 | 131,709,897 | 487 | 495 |
| B | 34 | 98.0% | 97.4% | 85.5% | 94.2% | 100.0% | 98.2% | 0/0/1/186 | 39,292,301 | 130,907,219 | 813 | 1057 |
| C | 1 | 0.0% | 0.0% | 15.8% | 0.0% | 39.2% | 9.7% | 185/2/0/0 | 161,339,041 | 8,860,479 | 0 | 0 |
| C | 2 | 0.0% | 0.0% | 0.7% | 0.7% | 50.2% | 2.5% | 185/2/0/0 | 43,807,520 | 126,392,000 | 43 | 43 |
| C | 3 | 0.0% | 0.0% | 30.3% | 35.5% | 56.8% | 31.0% | 166/21/0/0 | 39,607,814 | 130,591,706 | 45 | 45 |
| C | 4 | 4.5% | 1.8% | 59.7% | 60.1% | 71.5% | 58.1% | 56/74/54/3 | 38,594,271 | 131,605,249 | 50 | 50 |
| C | 5 | 23.6% | 15.0% | 75.7% | 74.2% | 83.4% | 73.6% | 7/18/141/21 | 38,310,531 | 131,888,989 | 87 | 89 |
| C | 13 | 94.0% | 91.2% | 87.3% | 90.2% | 99.7% | 89.8% | 0/0/3/184 | 36,720,129 | 133,479,391 | 376 | 384 |
| C | 34 | 97.4% | 95.1% | 82.1% | 92.0% | 100.0% | 96.0% | 0/0/0/187 | 37,710,684 | 132,488,836 | 605 | 822 |
| D | 1 | 0.0% | 0.0% | 15.8% | 0.0% | 39.2% | 9.7% | 185/2/0/0 | 161,338,896 | 8,860,624 | 0 | 0 |
| D | 2 | 0.0% | 0.0% | 0.7% | 0.7% | 50.2% | 2.5% | 185/2/0/0 | 43,721,284 | 126,478,236 | 43 | 43 |
| D | 3 | 0.0% | 0.0% | 25.7% | 31.3% | 56.1% | 26.6% | 166/21/0/0 | 39,621,236 | 130,578,284 | 45 | 45 |
| D | 4 | 4.5% | 1.7% | 52.5% | 53.4% | 67.9% | 50.7% | 52/78/54/3 | 38,669,180 | 131,530,340 | 51 | 51 |
| D | 5 | 23.2% | 14.7% | 69.0% | 69.0% | 79.6% | 68.4% | 4/16/146/21 | 38,293,532 | 131,905,988 | 72 | 74 |
| D | 13 | 92.2% | 87.4% | 87.3% | 92.4% | 99.9% | 91.2% | 0/0/2/185 | 34,317,601 | 135,881,919 | 311 | 319 |
| D | 34 | 96.0% | 90.9% | 78.0% | 90.8% | 99.8% | 92.7% | 0/0/0/187 | 35,911,707 | 134,287,813 | 493 | 686 |
| E | 1 | 0.0% | 0.0% | 0.5% | 0.0% | 29.1% | 2.2% | 185/2/0/0 | 161,337,754 | 8,861,766 | 0 | 0 |
| E | 2 | 0.0% | 0.0% | 0.0% | 0.0% | 28.7% | 1.8% | 185/2/0/0 | 43,329,275 | 126,870,245 | 2 | 2 |
| E | 3 | 0.0% | 0.0% | 8.8% | 19.3% | 31.8% | 11.3% | 161/26/0/0 | 39,191,734 | 131,007,786 | 2 | 2 |
| E | 4 | 5.1% | 1.9% | 20.1% | 26.0% | 42.4% | 20.1% | 26/100/58/3 | 37,612,805 | 132,586,715 | 4 | 4 |
| E | 5 | 20.1% | 18.5% | 43.4% | 46.9% | 54.8% | 44.8% | 1/7/166/13 | 35,799,025 | 134,400,495 | 18 | 20 |
| E | 13 | 90.1% | 84.2% | 80.5% | 90.2% | 99.7% | 90.1% | 0/0/2/185 | 25,910,283 | 144,289,237 | 176 | 184 |
| E | 34 | 94.8% | 87.3% | 73.9% | 87.6% | 99.6% | 91.1% | 0/0/0/187 | 27,718,862 | 142,480,658 | 284 | 430 |
| F | 1 | 0.0% | 0.0% | 0.5% | 0.0% | 29.1% | 2.2% | 185/2/0/0 | 161,338,657 | 8,860,863 | 0 | 0 |
| F | 2 | 0.0% | 0.0% | 0.0% | 0.0% | 28.7% | 1.8% | 185/2/0/0 | 44,338,757 | 125,860,763 | 2 | 2 |
| F | 3 | 0.0% | 0.0% | 9.2% | 19.6% | 32.1% | 11.7% | 161/26/0/0 | 39,583,772 | 130,615,748 | 2 | 2 |
| F | 4 | 5.1% | 2.2% | 21.0% | 26.7% | 45.1% | 22.1% | 26/100/58/3 | 36,297,272 | 133,902,248 | 3 | 3 |
| F | 5 | 20.6% | 21.6% | 43.7% | 47.4% | 56.2% | 45.0% | 0/8/163/16 | 34,557,584 | 135,641,936 | 15 | 15 |
| F | 13 | 82.5% | 63.2% | 88.4% | 92.0% | 99.3% | 89.8% | 0/0/5/182 | 33,270,631 | 136,928,889 | 231 | 231 |
| F | 34 | 88.4% | 68.5% | 91.7% | 93.3% | 99.8% | 93.7% | 0/0/0/187 | 34,831,492 | 135,368,028 | 376 | 466 |
| G | 1 | 0.0% | 0.0% | 15.8% | 0.0% | 39.2% | 9.7% | 185/2/0/0 | 161,340,005 | 8,859,515 | 0 | 0 |
| G | 2 | 0.0% | 0.0% | 0.9% | 0.9% | 50.3% | 2.7% | 185/2/0/0 | 44,700,506 | 125,499,014 | 44 | 44 |
| G | 3 | 0.0% | 0.0% | 33.9% | 38.8% | 57.9% | 34.6% | 166/21/0/0 | 40,097,502 | 130,102,018 | 45 | 45 |
| G | 4 | 4.6% | 2.0% | 66.2% | 65.8% | 75.5% | 64.1% | 57/72/55/3 | 37,902,098 | 132,297,422 | 51 | 51 |
| G | 5 | 23.7% | 19.5% | 82.7% | 82.5% | 87.5% | 81.6% | 9/18/136/24 | 37,636,509 | 132,563,011 | 93 | 93 |
| G | 13 | 93.0% | 79.2% | 97.4% | 98.0% | 100.0% | 97.8% | 0/0/5/182 | 39,287,544 | 130,911,976 | 408 | 408 |
| G | 34 | 96.3% | 86.6% | 98.3% | 98.6% | 100.0% | 98.7% | 0/0/0/187 | 39,975,605 | 130,223,915 | 720 | 913 |
| H | 1 | 0.0% | 0.0% | 0.5% | 0.0% | 29.1% | 2.2% | 185/2/0/0 | 161,338,657 | 8,860,863 | 0 | 0 |
| H | 2 | 0.0% | 0.0% | 0.0% | 0.0% | 28.7% | 1.8% | 185/2/0/0 | 44,338,757 | 125,860,763 | 2 | 2 |
| H | 3 | 0.0% | 0.0% | 1.0% | 5.7% | 32.2% | 2.8% | 185/2/0/0 | 39,603,607 | 130,595,913 | 2 | 2 |
| H | 4 | 0.6% | 1.1% | 20.8% | 24.7% | 43.3% | 22.2% | 166/16/2/3 | 36,594,536 | 133,604,984 | 3 | 3 |
| H | 5 | 10.1% | 11.1% | 39.9% | 44.9% | 53.9% | 41.3% | 33/114/24/16 | 35,061,991 | 135,137,529 | 15 | 15 |
| H | 13 | 76.8% | 61.5% | 86.3% | 91.2% | 99.4% | 90.7% | 0/2/36/149 | 33,827,016 | 136,372,504 | 223 | 223 |
| H | 34 | 90.8% | 72.0% | 92.8% | 93.7% | 99.9% | 96.4% | 0/0/0/187 | 34,973,175 | 135,226,345 | 487 | 600 |
| I | 1 | 0.0% | 0.0% | 0.3% | 0.0% | 30.6% | 1.9% | 177/2/0/0 | 161,337,825 | 8,861,695 | 0 | 0 |
| I | 2 | 0.0% | 0.0% | 0.0% | 0.0% | 30.3% | 1.5% | 177/2/0/0 | 42,888,776 | 127,310,744 | 2 | 2 |
| I | 3 | 0.0% | 0.0% | 8.3% | 19.1% | 33.0% | 10.7% | 156/23/0/0 | 38,075,855 | 132,123,665 | 2 | 2 |
| I | 4 | 4.3% | 1.5% | 22.2% | 27.5% | 46.1% | 22.7% | 27/98/53/1 | 35,354,018 | 134,845,502 | 2 | 2 |
| I | 5 | 16.4% | 21.0% | 46.7% | 49.1% | 57.2% | 47.7% | 0/10/168/1 | 33,225,778 | 136,973,742 | 16 | 16 |
| I | 13 | 79.8% | 62.7% | 90.2% | 91.9% | 99.2% | 90.7% | 0/0/8/171 | 31,461,677 | 138,737,843 | 217 | 217 |
| I | 34 | 85.4% | 66.1% | 91.2% | 92.5% | 99.8% | 93.0% | 0/0/2/177 | 33,203,497 | 136,996,023 | 307 | 360 |
| J | 1 | 0.0% | 0.0% | 0.3% | 0.0% | 30.6% | 1.9% | 177/2/0/0 | 161,337,825 | 8,861,695 | 0 | 0 |
| J | 2 | 0.0% | 0.0% | 0.0% | 0.0% | 30.3% | 1.5% | 177/2/0/0 | 42,888,776 | 127,310,744 | 2 | 2 |
| J | 3 | 0.0% | 0.0% | 8.8% | 19.2% | 33.0% | 12.5% | 155/24/0/0 | 38,072,848 | 132,126,672 | 3 | 3 |
| J | 4 | 4.5% | 2.9% | 22.1% | 25.4% | 43.7% | 45.5% | 27/95/56/1 | 35,323,040 | 134,876,480 | 40 | 40 |
| J | 5 | 16.4% | 26.6% | 43.3% | 47.3% | 55.1% | 77.2% | 0/10/168/1 | 32,799,524 | 137,399,996 | 95 | 95 |
| J | 13 | 82.8% | 65.7% | 89.7% | 91.8% | 99.1% | 98.5% | 0/0/12/167 | 30,782,914 | 139,416,606 | 345 | 345 |
| J | 34 | 90.1% | 70.6% | 91.9% | 93.2% | 99.8% | 99.0% | 0/0/3/176 | 32,834,354 | 137,365,166 | 473 | 526 |
| K | 1 | 0.0% | 0.0% | 0.3% | 0.0% | 30.6% | 1.9% | 177/2/0/0 | 161,337,825 | 8,861,695 | 0 | 0 |
| K | 2 | 0.0% | 0.0% | 0.0% | 0.0% | 30.3% | 1.5% | 177/2/0/0 | 42,888,776 | 127,310,744 | 2 | 2 |
| K | 3 | 0.0% | 0.0% | 0.4% | 5.1% | 33.1% | 2.0% | 177/2/0/0 | 38,099,578 | 132,099,942 | 2 | 2 |
| K | 4 | 0.1% | 0.5% | 22.2% | 25.7% | 44.0% | 23.1% | 169/9/0/1 | 35,691,178 | 134,508,342 | 2 | 2 |
| K | 5 | 3.6% | 10.8% | 41.8% | 47.5% | 55.5% | 44.0% | 37/127/14/1 | 33,472,345 | 136,727,175 | 16 | 16 |
| K | 13 | 68.1% | 60.2% | 89.5% | 91.9% | 99.2% | 90.7% | 0/2/43/134 | 31,965,772 | 138,233,748 | 212 | 212 |
| K | 34 | 89.3% | 69.0% | 92.6% | 93.4% | 99.8% | 97.0% | 0/0/2/177 | 33,409,189 | 136,790,331 | 401 | 466 |

### What each round found

- A (no opening sweep). Household services are supplied in period 1 (39% unmet, from 100%) and the
  sites under a service-input floor fall from 630 to 0 in period 1, but business services and
  resources still sell below cost, and supply collapses from period 4 as before.
- B, C (the Director's repair). Business services and extraction now cover their cost at every
  seller in period 1. Food holds better to period 5 (24% unmet, from 80%) but not after: by period
  13, 94% of food is unmet. The Wayne chain under C shows the next boundary: the county's utility
  plant runs out of resources (it needs 8 a batch; Wayne's extraction makes 95,000 a period against
  187,000 the plant uses), so business services, household services, food and housing lose their
  utility input from period 3 and household services pay idle labor until their cash is gone.
- D, E (resources and utility). Extraction at 32 units a batch and energy at 320 units of utility a
  batch remove the utility shortfall at the opening (utility 0.5% unmet in period 1, from 15.8%),
  but supply still collapses from period 5. Under E the Wayne retailer's food from Sub-Saharan
  Africa (443,064 a period, of which about 30 arrive) and from Wayne's own food plant (which can
  make 873,000 against 1.33 million ordered) piles up as inbound orders; by period 8 the inbound
  count reaches the retailer's target and it orders nothing more at home, so the food plant cuts
  its plan and lays off.
- F, G (no foreign procurement). Removing the undeliverable imports helps food (88% unmet at 34,
  from 95%) but takes away imported resources, so utility is worse (G, on C, is worse than C).
- H, K (support at the policy's maximum). Food holds longer (K: 3.6% unmet in period 5) but the
  collapse follows by period 13.
- I (food at 32 a batch). The best food at period 34 (85% unmet) and the fewest sites under a floor.
- J (no taxes). No help: public money is not the leak.

### Why no candidate works: the next binding causes, which policy text cannot remove

1. Households outside the labor force have no income. In every candidate, 375,434 Wayne persons
   (the no-earner nonowner group) cannot pay for utility and household services from period 3:
   unmet equals unpaid exactly. County support pays only for each opening job-seeker
   (`opening/financial.rs` `household_support`), fixed at the opening.
2. The designed processes use about a quarter of the opening workforce. In period 2 every
   candidate lays off about 118 million of 161 million domestic workers (distribution 28.7 to 2.9
   million, business services 26.7 to 2.9 million, household services 71.9 to 29 million), because
   a pool keeps only the people its requested hours need (`staffing/transition.rs`
   `advance_pool`). Domestic wages fall from $556 billion in period 1 to $163 billion in period 2
   and $23 billion by period 34, and unpaid need grows with them. The labor figures cannot rise
   under the Director's rule: retail's margin on food ($280 to $304) is exactly one hour of the
   default wage, and household services cover their cost by $765 a batch, so more hours put them
   below cost.
3. Orders that cannot ship count as inbound. A replenishment buyer subtracts every outstanding
   order from its target (`recurring/firms.rs`), including imports held by a full corridor and
   orders its domestic supplier cannot fill, so it stops ordering what could be made at home.

Each of these is an engine or compiler change (support that follows the current job-seekers and
the households outside the labor force; an order book that discounts what cannot arrive; or new
labor and price figures), and none was made. Six rounds after C were allowed; five were run.

Under FOOD_32 (I, J, K) the opening has 179 domestic counties with household rows instead of 187,
with the same national households and persons; the reason was not established.
