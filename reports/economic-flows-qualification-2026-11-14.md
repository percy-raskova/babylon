# Economic flows and company accounting on the local national campaign

Use the [local setup guide](../SETUP_GUIDE.md#inspect-a-company-or-freight-route) to open a national campaign and follow a payment from a county to a company’s books. The first measurements below use the earlier national opening. The company results begin with [the v8 opening](#the-first-company-enabled-national-opening). The [three-turn measurements](#three-full-observer-turns) cover the time until the observer shows usable amounts, storage growth and memory.

## Money and recorded labor in the v7 campaign

The national v7 campaign `…7392` reached period 2 with 25,357 settled payments and 33,325 labor movements. The full observer read the material receipts from Postgres 17.11. The fixture binds its results to foundation `0458f252d24189c8c53676ce89f1e142fcbc5476f51c2eeb39b471ff7a75d713` and period-2 tick content `2259222661ee1978e5946e090942898d56a43e5dc53340b720516be2984bb83a`. The 69,444,235-byte database archive has SHA-256 `bfe7255fd848e4133d3989ca7ee0a01d4ba6c638a0e6db7874d8c9acbd29394f`.

| Period | Recorded hours carried in | Direct hours worked | Hours released | Recorded hours carried out |
| --- | ---: | ---: | ---: | ---: |
| 1 | 0 | 260,206,621,969.000000 | 123,016,473,568.218750 | 137,190,148,400.781250 |
| 2 | 137,190,148,400.781250 | 126,590,526,145.000000 | 125,602,162,193.338245 | 138,178,512,352.443005 |

Each row reconciles to one millionth of an hour. Unknown prehistory travels alongside the recorded amount. In Wayne County, 78 period-2 movements within the county carried 117,873,218.120578 recorded hours. Sixty-three of those movements included unknown prehistory.

The native observer ran at 1366 × 768 on a GeForce RTX 3060. Wayne received $0 from outside and paid $2,240,212.80 outside. Payments within the county totaled $5,487,803,024.920346. Its period-1 external net was zero.

A ranked link from Sitka to Anchorage matched nine settlements totaling $819,146.25. The 17 operating sites in Sitka reported the following totals.

| Period 2 measure | Dollars |
| --- | ---: |
| Change in cash | 3,064,489.20229 |
| Profit | 5,828,245.310545 |
| Closing retained earnings | −1,594,702.8229 |

### Warm query times

Each CLI sample ran a new process against the restored database after a warm-up. The SQL column gives execution time for the ranking query. These measurements cover a single county in this two-period campaign.

| Wayne County query | CLI sample 1 (ms) | CLI sample 2 (ms) | SQL execution (ms) |
| --- | ---: | ---: | ---: |
| Money, period 2 | 330.915 | 310.294 | 203.240 |
| Money, periods 2 and 1 | 675.191 | 634.122 | 447.441 |
| Labor, period 2 | 333.613 | 340.973 | 297.727 |
| Labor, periods 2 and 1 | 528.718 | 521.690 | 448.124 |

The separate 15-period integration case exercised thirteen-period detail retention and reconstruction across gaps. The test canceled publication after the writer acquired its locks. A second connection verified the rollback. The next graph and material identities matched after the retry. Another case copied the selected campaign from the predecessor schema and inspected the copy. All three cases passed at the money and labor milestone, commit `a00dbf0bf`.

## The first company-enabled national opening

The v8 opening assigned 2,788 whole sites to 99 occupied companies. Those sites had 121,486,688 captured jobs.

| Company group | Jobs | Achieved share | Designed share |
| --- | ---: | ---: | ---: |
| First national | 42,499,818 | 34.9831% | 35% |
| Second national | 42,525,140 | 35.0040% | 35% |
| Regional | 36,461,730 | 30.0129% | 30% |

The Designed shares apply within each function and division. The largest absolute difference in any of the 81 cells was 0.6970 percentage points. In West North Central construction and housing, the first national company received 34.3030%.

The capture test compared physical sites and staffing across v7 and v8. It checked the original beneficiaries against 5,577 source claims and reopened the saved national graph.

| Cash at capture | Dollars |
| --- | ---: |
| Sites before the sweep | 18,386,523,946,435.10 |
| Sites after the sweep | 18,293,765,369,856.10 |
| Company treasuries after the sweep | 92,758,576,579.00 |

The exact integer headcounts and percentages for every cell are in the [opening employment table](economic-flows-qualification-2026-11-14-assets/national-company-employment.csv).

A second test ran all 99 companies through the authoritative decision rule and joined their selected whole-unit limits to the next period’s actual equipment purchases. It replayed period 1 from the same capture and restored its full checkpoint into a cold session. Period 2 reproduced the uninterrupted graph and material identity and receipt digest.

### First national close and financial publication

The local Postgres 17.11 campaign `…7398` used seed 319. The runtime closed and committed period 1 in 7.729 seconds. Simulation took 2.454 seconds, preparation took 1.282 seconds, and the durable-write phase took 3.993 seconds. The independent first publication through the financial CLI took 117.352 seconds. The CLI sample includes process launch, source authentication, projection and database publication.

Postgres spent 88.787 seconds checking 121,110 references to immediate labor nodes. The checks hit shared buffers 26,990,966 times. Each lookup supplied a node ordinal. The planner chose the location index each time.

The change restricts that index to nodes with known locations. The unqualified ordinal lookup then uses the primary key. An isolated Postgres 17 probe read three local buffers after the change, compared with 38 before. The county query continued to use the location index.

A fresh database with the partial index published the same first financial period in 30.568 seconds. The canonical close took 7.693 seconds. Simulation took 2.330 seconds, preparation took 1.262 seconds and durable writes took 4.101 seconds. These clocks have different endpoints from the rendered, usable-turn measurement.

The second national close took 6.769 seconds. This included 2.065 seconds of simulation, 0.996 seconds of preparation and 3.709 seconds of durable writes. After an interrupted publication rolled back, a clean retry published the second financial period in 19.187 seconds.

Period 2 contains 23,012 settlements. The 68,437,712-byte local archive has SHA-256 `a726265888f2a8918c7d701f39b7d09fad239c24912d270788a25aaf88d46f0e`. Its foundation digest is `2fb1c26a59f6642068e13a9a2e0dfcef9b9e17de1a5a4ad77594f4763d6cd455`. Its period-2 tick content hash is `67ca90fc47239c9aa04f349c10fac8a055e30773260bb85c71e6c8bb183bb31c`.

### Wayne queries in the company-enabled campaign

Each warm CLI sample starts a new observer process. SQL execution covers the ranked query for the same county and period.

| Query | CLI sample 1 (ms) | CLI sample 2 (ms) | SQL execution (ms) |
| --- | ---: | ---: | ---: |
| Money, period 2 | 337.800 | 305.357 | 198.417 |
| Money, periods 2 and 1 | 581.444 | 614.730 | 424.383 |
| Labor, period 2 | 466.024 | 474.844 | 412.334 |
| Labor, periods 2 and 1 | 604.280 | 598.603 | 580.212 |

The original nationwide labor rankings exceeded the observer’s five-second query limit. The revised query looks up company ownership once per campaign. It counts each labor amount once in the total. Each amount also belongs to a named group or the sum outside the displayed page.

| Period-2 ranking with period-1 comparison | Groups | Before statistics collection (s) | After statistics collection (s) |
| --- | ---: | ---: | ---: |
| National, by company | 78 | 1.427 | 0.505 |
| National, by `counterparty` | 5,654 | 1.705 | 0.707 |

Eight queries returned the same values as an independent calculation under both sets of planner statistics. The checks covered exact hours, movements with unknown prehistory, county selection, map bounds, period comparison and the sum outside the second page.

The full observer reads retained labor rankings from the published facts. The reader checks the source marker and row counts. The writer checks the fingerprint during verification and reconstruction. A database administrator who changes a retained amount while preserving its row count can affect that ranking until the writer verifies or rebuilds it.

### Native interaction and frame time with labor flow version 2

The observer used an NVIDIA GeForce RTX 3060. It ran on driver 550.163.01 with the `Vulkan` backend. Each window of 300 frames measured the active view. The final column gives the slowest 95th-percentile frame time from those windows.

| View | Window (pixels) | Frames sampled | Slowest p95 (ms) |
| --- | --- | ---: | ---: |
| Consolidated company | 1920 × 1080 | 900 | 14.567 |
| Legal parent | 1920 × 1080 | 3,300 | 17.290 |
| Freight map | 1920 × 1080 | 1,800 | 18.203 |
| Freight network | 1920 × 1080 | 600 | 16.417 |
| Labor map | 1366 × 768 | 2,700 | 18.811 |
| Labor Sankey | 1366 × 768 | 300 | 14.711 |
| Money map | 1366 × 768 | 14,100 | 15.418 |
| Money map | 1920 × 1080 | 17,100 | 18.393 |
| Money Sankey | 1366 × 768 | 900 | 13.156 |
| Money Sankey | 1920 × 1080 | 5,700 | 20.693 |

A physical map pick selected a payment of $800,060.625 from Sitka to Anchorage. In Wayne, the same 63 within-county movements stayed selected across the Labor map and Sankey. They carried 10,611,984.321064 recorded hours and 49 included unknown earlier hours.

In this capture, the two ends of a labor movement use the locations on the published ledger. Some final uses have no location on their receiving entry. A household can consume goods at home while the receiving entry has no county. That entry alone cannot show whether labor crossed a county line.

Opening a company showed its legal parent and consolidated statements. Five readings in each view matched the published figures. A separate full report for all 99 companies returned in 213.70 milliseconds. A physical selection on the county site list also opened that site’s three statements.

The native site view summarizes the balance sheet, income and cash flow for a completed period. The financial CLI also exposes stock basis by good, tax and expense detail, individual claims and the opening balance sheet. The native comparison uses the preceding period. The CLI accepts two explicit period ranges.

Switching from map to Sankey and back kept the same Household services company and its $829,377,792.00 Wayne payment leg. Both freight layouts showed the complete 64-character ID of the Oakland-to-Wayne corridor. Expanding Wayne’s food industry row showed seven source codes. NAICS 311 had 1,446,647 reported jobs, 1,317 reporting cells and 1,332 suppressed cells in the captured national data.

At 1366 × 768, Wayne’s prior external money net was −$348,926,580.00. Its current net was −$267,567,952.828417. The signed change of +$81,358,627.171583 was visible by 0.932 seconds.

For labor, the panel still showed “Reading” at 2.421 seconds. The signed change of −477,948.110576 hours was visible by 3.128 seconds. The labor ranking query took 552 milliseconds. The native labor comparison exceeded the two-second target for detailed queries.

After the ranking change, a second physical comparison on the same campaign showed the signed money change by 0.857 seconds. The last loading frame appeared at 0.408 seconds. For labor, the previous frame was still visible at 1.707 seconds, and the signed change was visible by 1.869 seconds. The screenshot files finished writing by 0.930 and 1.932 seconds respectively. Both comparisons met the two-second target in this sample.

### County labor geography in version 3

Household consumption has a known place when the source identifies the household. The same applies when a provider’s unused service expires at its site. Version 3 uses the place of those documented uses. Freight lost in transit still has no point along the route. Account identities, published receipts and the world hash keep their original values.

| Wayne County | Movements within Wayne | Recorded hours within Wayne | Movements with unknown earlier hours |
| --- | ---: | ---: | ---: |
| Period 1 | 133 | 15,116,808.128125 | 119 |
| Period 2 | 97 | 15,174,203.394890 | 83 |

In period 2, version 2 had placed 34 local uses carrying 4,562,219.073826 hours outside the within-county total. Five movements brought 61.963250 recorded hours to Wayne from entries with no recorded location. All five carried unknown earlier labor. The corrected net change from the previous period was +61.963250 hours.

Ten regional and national queries matched an independent calculation from the original movement and node rows. The checks included selected connections, map bounds and the sum outside the second page. The nationwide totals for `company` and `counterparty` matched version 2.

The Labor Sankey shows the county’s opening and closing holdings. Wayne’s period-2 holdings rose from 1,236,417 to 1,854,677.889424 recorded hours. Both balances covered 59 positions with unknown earlier labor. The transfer from an unknown location to Wayne stayed selected across both views. Its five movements carried 61.963250 recorded hours. A position can hold hours across a period without appearing among the transfers on the displayed page.

The original balance query timed out in the compact native window. The corrected query read the 91 Wayne node keys once and scanned the period’s 43,478 positions once. It took 32.8 milliseconds in Postgres and 125 milliseconds with the connection included. A second query checked the exact hours and counts on both sides. An empty county returned zero balances. A period with no publication returned no coverage.

On a fresh restore, the first native Labor selection showed the county figures before any statistics collection on the labor tables. At 1366 × 768, a physical comparison still showed the loading frame at 0.858 seconds. The signed change of +61.963250 hours was visible by 1.358 seconds. The screenshot finished writing by 1.435 seconds. The ranked query took 676 milliseconds, the boundary query took 22 milliseconds, and the frame check took 18 milliseconds.

The text reader mistook the slashed zero for a copyright symbol. The original screenshot shows zero for period 1. Its pixels match the zero in the same frame’s confirmed outbound total. Eight consecutive frames showed the same three values as the independent ledger check.

The national integration case independently checked both county balances and their unknown-hour counts through the full observer login. In a separate 15-period case, the reader recovered the same county balances and flow page after period 1 had passed the detail retention cutoff.

### Third-period publication

A separate process advanced the restored archive to period 3 in 10.499 seconds. A new full-observer publisher then made the same period readable in 25.842 seconds. The read matched 22,246 payments, 28,351 labor movements, 7,463 sites and 99 companies.

| Publication stage | Seconds |
| --- | ---: |
| Read and authenticate source data | 13.692 |
| Company dimensions and accounts | 0.900 |
| Payments and journal totals | 2.018 |
| Site statements | 1.243 |
| Company statements | 0.076 |
| Labor facts | 2.646 |
| Retention, marker and commit | 3.638 |
| Complete publication, including setup | 25.704 |

This cold run took 36.341 seconds to advance the period and read its financial facts. The publisher started after the period closed. The probe ran without a renderer.

### Three full-observer turns

The local runtime, native client, financial publisher and Postgres all ran during these turns. Each row ends when the client has rendered the committed period and SQL exposes that period’s payments, labor, sites and companies.

| Period | Installed frame (s) | Captured frame (s) | Frame and financial read (s) | Charged storage growth (bytes) |
| ---: | ---: | ---: | ---: | ---: |
| 3 | 25.950 | 27.598 | 42.679 | 63,586,304 |
| 4 | 27.090 | 30.088 | 36.776 | 65,331,200 |
| 5 | 27.141 | 28.842 | 35.586 | 62,480,384 |

All three turns exceeded the 30-second budget and the limit of 40,000,000 bytes of growth per close. The database itself grew from 273,667,763 bytes after period 2 to 462,755,507 after period 5. These ages precede the 13-period retention cutoff.

Labor relations grew by 89,432,064 bytes and payments by 44,654,592 bytes. Site books grew by 31,039,488 bytes and company relations by 737,280 bytes. These counts include the tables’ indexes and overflow storage. Periods 52 and 325 still need measurements.

The next build authenticated the current and prior endpoints in parallel. Both connections read the same Postgres snapshot. The same seed produced the same three world hashes. For period 4, the publisher read and authenticated its source in 7.738 seconds. The earlier build took 10.357 seconds. The table gives the elapsed time from the command to each observation.

| Period | Installed frame (s) | Frame and financial SQL read (s) | Last frame missing amounts (s) | First frame with all three amounts (s) | Charged growth (bytes) |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 3 | 26.764 | 40.809 | 42.156 | 43.507 | 65,388,544 |
| 4 | 27.143 | 34.248 | 36.762 | 37.987 | 64,479,232 |
| 5 | 26.836 | 32.750 | 36.560 | 37.775 | 62,160,896 |

For each period, a separate query checked the displayed amounts that Wayne received, paid and settled within the county. The last incomplete frame and the first complete frame bound the time when the amounts appeared. Each turn exceeded both limits.

The memory check followed the runtime, native client, financial publisher and database together on another restore. It collected 114 complete samples from period 2 through period 5. The highest sampled total of resident memory and Linux HugeTLB pages was 4,593,225,728 bytes in period 4. The cap is 10,000,000,000 bytes.

The highest proportional-set size was 4,342,160,384 bytes. No sample used swap. The longest gap between samples was 3.825 seconds. This run started from the archive, so campaign creation and the 52- and 325-period limits still need checks.

A separate storage experiment restored the period-2 archive and loaded its two periods into temporary tables. It compared five fact families under two layouts. The alternative stored recurring labor nodes, stock identities and payment endpoints once and paired the opening and closing labor positions. Bidirectional SQL comparisons, including duplicate counts, recovered every field in both periods.

Between periods 1 and 2, the five families and their indexes grew by 46,194,688 bytes. The alternative layout grew by 23,347,200 bytes. The 22,847,488-byte saving applies to these temporary tables. The experiment excluded other relations, durable writes and concurrent queries.

The largest measured close exceeded the cap by 25,388,544 bytes. Two secondary indexes on site history grew by 11,182,080 bytes over the three closes. In a copy of the period-2 database, removing those indexes freed 4,694,016 bytes. The selected-site history reader now uses the primary keys for each covered period.

The restricted observer returned the same rows for a site with stock, a site without stock and an absent site. A query fixture repeated the stock and statement data for 128 actual sites over 325 periods. It contained 41,600 statements and 57,200 stock rows. The following median times cover three warm SQL runs for one selected site.

| 325-period site history | Rows returned | With secondary indexes (ms) | With primary keys (ms) |
| --- | ---: | ---: | ---: |
| Statements | 325 | 66.691 | 70.188 |
| Stock balances | 975 | 0.629 | 2.234 |

Both queries returned the same full rows, including the signed statement lines and stock basis. The 325-period fixture measures query behavior. The full campaign still needs separate measurements of storage growth and usable turns at that age.

A second restore measured the physical tables and indexes used for cash movements, site accounts and stock. The observer read 80,546 cash movements in period 1 and 44,563 in period 2. In both periods, the compact tables reproduced every original movement, economic payment, site statement and stock balance, including nulls and duplicate counts. Changing the paying account on an escrow settlement changed exactly one economic payment. Its custody debit still identified the same reserve.

| Family | Original growth, period 1 to 2 (bytes) | Compact growth (bytes) |
| --- | ---: | ---: |
| Cash movements and their economic payers | 15,908,864 | 8,486,912 |
| Site statements and stock balances | 11,132,928 | 4,317,184 |

The two families saved 14,237,696 bytes together. The old site-history indexes account for 4,243,456 of those bytes. The compact representation saved a further 9,994,240 bytes. These figures cover the listed relations and their keys. The campaign growth limit applies to the entire database.

On the two-period labor data, the old ranking query checked the source marker once for each of 68,942 movements. The revised query checks the marker for each selected period and reads the captured company roster once. On compact storage, Wayne’s `--group counterparty` query fell from 1.906 to 0.625 seconds. The nationwide query ranked 5,654 groups in 0.839 seconds, down from 1.968 seconds. All five ordered pages matched, including their comparisons and the totals outside each page.

The repair check removed 34,181 period-1 labor nodes while keeping period 2. With sparse planner statistics, Postgres scanned the destination index once for each source node and reached the 120-second statement limit. Sampling the endpoint columns took 0.108 seconds. The deletion then took 2.843 seconds and the deferred checks took 0.281 seconds. Every period-2 node and balance still matched the original.

### Inspecting the earlier national save

The campaign-copy command read `…7398` from the schema at `dccef45d6` and copied its two committed periods into a fresh database in 24.580 seconds. The foundation, tick identities, actions, register and receipt bytes matched. The financial publisher rebuilt both periods in 51.968 seconds.

Separate full-observer logins read each database. All 439,481 rows across 14 observer views matched field for field in the same order. These included 58,302 economic payments, 125,109 custody movements and 14,926 site statements. Company statements, eliminations, realized margins and labor balances also matched. The [comparison record](economic-flows-qualification-2026-11-14-assets/national-inspection-copy.csv) gives the tick hash, row count and digest for each view and period.

### Reading the committed graph for the observer

The national period-2 frame contains 33,370 nodes and 56,628 numeric node attributes. The two graph queries formerly looked up identifiers and strings for each returned field. The revised queries select the vectors for one period and read the campaign dictionaries once. Combined Postgres execution time fell from 2.270 seconds to 0.241 seconds. The two queries touched 2,443 shared buffers, down from 3,441,015.

The restricted observer returned the same ordered bytes for both queries in periods 1 and 2. These times cover Postgres execution. Separate measurements cover the time to install the frame and display the financial figures.

### Three turns after the compact journal rebuild

The native client reopened the verified copy on a GeForce RTX 3060. Each step reproduced the earlier tick hash, world hash and counts for payments, labor, sites and companies. A full-observer connection checked the financial markers. Screen samples identified the first frame with all three correct Wayne amounts.

| Period | Commit visible by (s) | Frame rendered by (s) | Journal visible by (s) | First correct amounts between (s) | Charged growth (bytes) |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 3 | 12.029 | 23.415 | 40.896 | 41.074–41.326 | 39,362,560 |
| 4 | 13.465 | 26.255 | 34.315 | 34.726–34.978 | 39,976,960 |
| 5 | 14.289 | 26.147 | 34.339 | 37.272–37.524 | 45,662,208 |

Periods 3 and 4 fit the 40,000,000-byte limit. Period 5 exceeded it by 5,662,208 bytes. All three turns exceeded the 30-second budget for visible financial figures. The [native measurements](economic-flows-qualification-2026-11-14-assets/national-compact-native-turns.csv) include the observation bounds, hashes and counts.

After the three turns, fresh full-observer CLI processes compared period 2 with period 1. Warm `--group counterparty` queries took 0.850 seconds for Wayne and 1.108 seconds nationwide. The national company ranking took 0.959 seconds. Each complete ranked page matched the earlier SQL result.

### Graph validation and recovery of expired labor detail

A test placed 33,370 graph nodes and 56,628 numeric attributes from national period 2 under a new marker. Reading the selected period's vectors and the campaign's names once cut validation from 4.316 seconds to 0.334 seconds. Nine malformed graphs produced the same rejection as before. Rolling back restored the original marker function and period-2 state.

An ordinary turn exposed a different plan in period 4. Postgres estimated ten attribute rows and ten member rows, then repeatedly scanned the member list for each attribute. The graph query took 145.077 seconds inside the canonical commit. The period-2 benchmark did not reproduce this later-period cost.

The replacement checks membership by set difference and groups attributes by node and name to detect duplicates. On the saved period-5 campaign, all 36 plans checked the period-3 through period-5 attributes in 78–106 milliseconds. This covered missing statistics, empty-table estimates, period-2 estimates and current estimates. The full check for a new marker took 159–173 milliseconds. Both versions rejected ten damaged graphs with the same errors.

The national recovery test exposed a separate delay after the last period of labor detail expired. Postgres still estimated zero rows in both parent tables after the writer restored the nodes. It checked some references by scanning the period and filtering for the node ordinal.

On a copy of the save, the writer restored 31,540 period-2 nodes and refreshed both estimates in 52 milliseconds. Postgres then used all three primary-key columns. The deferred checks took 3.703 seconds. Every restored node, position and movement matched the source.

The labor directory retains each full content digest. Period links refer to its entry by an integer key. Across the same two periods, growth in these two tables and their indexes fell from 9,134,080 to 6,643,712 bytes.

The following native run combined integer labor references with the graph query tested above. All three closes reproduced the original campaign hashes and Wayne amounts. The publisher authenticated the reopened period-2 history in 10.788 seconds before the first step. On this restored database, the observer's first count of period-2 payments timed out after five seconds.

| Period | Commit visible by (s) | Financial figures visible between (s) | Charged growth (bytes) |
| ---: | ---: | ---: | ---: |
| 3 | 9.226 | 32.028–32.279 | 35,217,408 |
| 4 | 153.425 | 174.177–174.429 | 43,614,208 |
| 5 | 149.177 | 169.725–169.977 | 33,021,952 |

Period 4 exceeded the storage limit by 3,614,208 bytes. Warm labor queries with `--group counterparty` took 0.894 seconds for Wayne and 1.044 seconds nationwide. The national company ranking took 0.823 seconds.

The writer can store opening and closing holdings on the node that carries them in each period. In a replay of all five periods, this saved 2,588,672, 2,580,480 and 2,473,984 bytes across the final three closes. These savings cover the affected labor tables and indexes. Every node, position and movement matched, including after removal and reconstruction of period 3.

On a freshly restored period-2 save, resolving both payment parties from the captured account directory let the original coverage check finish in 63 milliseconds. The first Wayne ranking took 193 milliseconds and matched the previous complete result. Two-period company rankings took about 2.5 seconds on a cold restore and 0.48–0.53 seconds when warm.

Commit `3db768eeb` passed all five Postgres 17.11 integration cases. They covered exact national account totals, recovery of expired or damaged records, concurrent reads, inspection of a predecessor campaign and organizer actions during financial publication. The Python gate passed 4,169 tests and skipped 18.

### Three native turns after the graph and labor repairs

The repaired build reopened the national campaign on the RTX 3060. All 439,481 rows across the 14 observer views still matched the original archive. The first Wayne payment query returned in 0.316 seconds. Screen capture confirmed all three period-2 amounts within 5.131 seconds of the opening measurement.

| Period | Commit visible by (s) | Journal visible by (s) | Wayne figures visible between (s) | Charged growth (bytes) |
| ---: | ---: | ---: | ---: | ---: |
| 3 | 8.419 | 30.469 | 30.495–30.746 | 33,341,440 |
| 4 | 8.088 | 27.330 | 29.785–30.037 | 36,323,328 |
| 5 | 8.279 | 26.725 | 26.615–26.866 | 32,948,224 |

All three turns fit the 40,000,000-byte limit and reproduced the earlier world hashes. Period 3 missed the 30-second usable-turn limit. The period-4 samples fall on either side of the limit. Period 5 passed. Separate sampling clocks recorded the journal and the rendered figures.

Warm labor queries with `--group counterparty` took 0.854 seconds for Wayne and 1.051 seconds nationwide. The national company ranking took 0.860 seconds. The [native measurements](economic-flows-qualification-2026-11-14-assets/national-compact-native-turns.csv) identify each of the three database layouts and saved inputs.

### Organizer action during financial publication

An ordinary organizer submitted remote aid while the financial writer was running. The second confirmation timed out. In a two-connection replay, an uncommitted financial row held a foreign-key lock on the campaign foundation. Postgres refused the organizer’s original update lock with SQLSTATE `55P03`.

The revised lock allowed the same confirmation while the writer held its foreign-key lock. It still serialized competing organizer commands, a period advance and the financial writer’s final source check. A later ordinary run traced a second wait to the period advance. The advance still used the original update lock while the financial writer inserted labor details.

After the same lock change in the advance, the organizer completed three turns in 12.720, 13.690 and 15.938 seconds. Each clock covers a local action and the resulting usable organizer frame. The storage check caught an 8,192-byte increase in the archive index between its two size readings.

The corrected collector uses one physical reading for each component. A fresh organizer run completed all three turns in 11.022, 13.490 and 15.750 seconds. The final stored snapshot matched the campaign and its three committed periods.

### Recovery after corrupted accounts

The full observer refused a balanced change to period-2 income and a balanced change to consolidated assets and equity. The test also damaged the earlier derived carrying-value checkpoint. An initial rebuild timed out at 120 seconds while deleting old labor movements through a foreign key.

The repaired writer deletes the old period’s child rows before its parent rows. It recovered all 99 sets of accounts from the source in a disposable copy of the national archive. Financial publication took 43.803 seconds, including 21.605 seconds to recover the source after damage to the earlier checkpoint. The 443,993 bytes of repaired accounts matched the original output exactly. Their SHA-256 is `d5434f5546042e1a06433aac64fbd79dd2aac614d9f7f01b512c5dc7b44cbc65`. The test also checked the prior period’s markers and row counts.

A fresh local Postgres 17.11 run on the source in commit `1a531db05` passed all five integration cases. It checked national publication and recovery, concurrent reads of one snapshot and thirteen-period retention. It also tested inspection of a campaign from the predecessor schema and organizer commands during financial writes. The runner verified cleanup of the disposable database. The repository’s Python check passed 4,168 tests and skipped 18.

## Michigan freight coverage

The observer opens freight access at Wayne. It can show the captured corridors in each direction, with the same selected endpoint on the geographic and network views. The local reference identifies 83 Michigan county terminals. The complete directed distance matrix was absent from the available source drives. Its pinned upstream road extract, dated September 8, 2026, returned HTTP 404. The pinned extract has 19,349,498,972 bytes and SHA-256 `31abe79b95cab2836ac9c6924701dc5ed0e6001ff102c572581097573df1d094`.

An executable directed-road case exercised access restrictions, asymmetric distance and selection with a missing matrix. Captured corridors remain inspectable when reference distances are unavailable. Airports appear as facility locations. Complete Great Lakes reachability and observed air services remain unqualified. The [source manifest](../tools/michigan_road_network_source_manifest.json) identifies the exact extract for a future rebuild.

## Controller count and investment

Each national opening kept the same 7,463 operating sites, 7,463 staffing pools, 6,432 equipment cohorts and 23,184 supplier routes. All 2,788 commercial member sites belonged to occupied companies. Reopening with the same seed reproduced the first close and every company’s choice at all three scales.

| Occupied companies | Tick preparation, median / peak (s) | Policy replay, median (ms) | In-memory commit, median (ms) | Peak register / receipts (MiB) | Different choices / matched decisions with alternatives |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 99 | 1.989 / 2.061 | 1.269 | 10.277 | 26.6 / 60.7 | 5 / 14 |
| 300 | 2.041 / 2.163 | 1.155 | 10.614 | 26.6 / 60.8 | 4 / 14 |
| 600 | 2.137 / 2.339 | 1.189 | 11.367 | 26.7 / 60.9 | 4 / 14 |

Each timing row covers three closes per seed. Policy replay recomputed the evidence for every company. We paired the same company and period across seeds 37 and 319. Each pair had the same operating evidence and at least two positive-weight choices.

All 99 companies deferred in ordinary period 1. Through period 3, their sites bought eight units with seed 37 and zero with seed 319. The Postgres and native display measurements use 99 companies.

| National treatment, 99 companies | Peak observed pressure, seed 37 / 319 | Equipment units authorized, seed 37 / 319 | Units bought next period, seed 37 / 319 |
| --- | --- | ---: | ---: |
| Less opening input stock and a smaller resource reserve | 1,067 / 1,067 processes with accepted orders still awaiting shipment | 57 / 121 | 15 / 0 |
| Larger opening pantries and a smaller retail buffer | 2,472 / 2,472 processes below recorded capacity | 57 / 121 | 11 / 0 |
| Less remaining life in opening equipment | 106 / 106 exhausted equipment cohorts | 98,414 / 100,840 | 98,371 / 100,651 |
| Less remaining life in opening equipment and slower installation | 90 / 23 unfinished installations | 289 / 229 | 289 / 229 |

These treatments each ran five periods per seed. The table covers the first four company decisions and the purchases in periods 2–5. Through period 3, the ordinary and larger-pantry openings both had as many as 2,472 processes below capacity. Less remaining life in opening equipment raised the exhausted-cohort count from zero to 106 over that same interval.

The ordinary treasury sweep took 10% of opening cash above the operating floor. Two periods of working capital supplied 1,394,094,647,710,000,000 micros to member sites. One period supplied half that amount, 697,047,323,855,000,000 micros. Across three closes per seed, site and parent cash covered at least one unit for every investment proposal.

With one period of cash and a zero opening treasury sweep, members kept their own balances. Across five closes under both seeds, each site and its treasury had enough cash to buy one unit for each investment proposal. Sites bought 15 units under seed 37 and 0 under seed 319.

The protected-cash stress raised the existing operating floor for each member in a private copy of the zero-sweep opening. Each floor equaled total cash and reserves in the economy, 14,637,178,811,308,920,000 micros. Opening balances, prices, orders, staffing and routes matched the control.

At period 2 both seeds recorded demand for 2,843 equipment units. Each seed had 63 member processes without enough spendable cash for one unit. All companies deferred across the first four closes for both seeds. The following closes admitted zero units. With the ordinary operating floors in the matched control, the same seeds bought 15 and 0 units.

The [period records](economic-flows-qualification-2026-11-14-assets/national-company-experiments.jsonl) show the capture identities, world hashes, observed conditions and timing samples. The [portfolio decision table](economic-flows-qualification-2026-11-14-assets/national-company-portfolio-decisions.csv) shows how many companies qualified for each choice, gave it positive weight and selected it. It also records purchases under each preceding choice.

## Repeat the local checks

From the project root, run the financial publication, recovery and role checks in a disposable Postgres database.

```bash
BLAS=1 BABYLON_POSTGRES_LIVE_FOCUS=money_journal mise exec -- bash tools/run_rust_postgres.sh
```

From `rust/`, check what sites can buy after a national checkpoint restart. The second command exercises the protected-cash opening with seeds 37 and 319.

```bash
BLAS=1 cargo test --locked -p babylon-persistence --test national_company_replay \
  national_99_choices_bound_next_purchases_and_survive_full_checkpoint -- --nocapture
BLAS=1 cargo test --locked -p babylon-persistence --lib \
  protected_member_cash_limits_observed_requests_and_the_following_real_committed_purchases -- --ignored --nocapture
```
