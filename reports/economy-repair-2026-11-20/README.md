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
