# Make the landlord's ledger the battlefield

*Filed with the design of homes, rent and nation (ADR315) on 21 November 2026. It is the report as
written, refitted to this repository's line length. The fourteen sets of notes it cites by file name
are kept with the lane's working files and are not in the repository. Where this report proposes and
the design decides otherwise, the design holds.*

US landlords do not set rent by formula. They set it from their own empty homes and their own
habits. Large operators reprice empty units often and push renewals. Small owners hold rent for
tenants they trust and catch up when a home turns over. Across a market, rents move slowly and
vacancy takes most of a shock first. Detroit is really two markets. One is a tight let market: about
4.6% of rental homes were for rent in 2024 (this report's arithmetic from the census). The other is
a huge stock of empty homes off the market, about 22% of all units, beside property taxes near 3% of
value, cheap houses, mostly small landlords who seldom hold the city's certificate, and a record in
which tax foreclosure, auction to investors and eviction fed each other. The proposal at the heart
of this report is to split a tenant's rent in two. One part is a service cost, the engine's Housing
provision. The other is the holder's take, a transfer to the top tenth, set by each holding's own
asking-rent rule. Each holding then gets books (rent roll, upkeep, tax, debt, cash), and the player
can read how long its cash will last and race against it. Michigan's own clocks decide how homes are
lost: about two four-week periods for a tenant at the fastest lawful pace, about three years for a
tax foreclosure, and for a mortgage a sheriff's sale followed by six or twelve months to redeem.
Struggle climbs a ladder from a building committee to escrow, strike, eviction defense, portfolio
campaigns and county politics. Who wins is decided by accounts: how long the landlord's cash and the
lender's patience last, against how long the tenants can hold. Equity should move a home owner's
outlook by weighing what the household stands to lose against what the struggle offers it, never by
a line drawn through equity. That follows MIM's line that home ownership is settler standing and
property. Treating equity as a growing quantity that moves a household is the reader's own
development: neither Sakai nor MIM describes it that way. The owner's most important open choice is
what a tenant's rent is made of. The second is whether households carry nation. Without it the game
cannot show MIM's first sorter of who owns and who is evicted.

A note on marks used throughout. **Measured** means an author estimated it from data, given with
size, place and year. **Argued** means an author's interpretation. **Arithmetic** or **inference**
means a note-taker's or this report's own working, not a source's statement. Flags the notes put on
figures (second-hand, unverified, conflicting) are carried forward. Game documents are cited by
short name, following `what_the_game_already_has.md`. HH is the approved households-and-homes design
(20 Nov 2026). CR is the County Review design. OPEN and ADR313 are the rebuilt national opening.
ADR312 is the price of a short market. SPIKE is builder spike 2. ADJ is the 21 Nov rulings on how
the economy adjusts. HHR is the 20 Nov rulings on households and homes.

---

## Part one: how rent works

### Landlords price from their own vacancy; big and small owners differ

Big operators run revenue-management software. RealPage's YieldStar suggests a daily price for each
open unit. It estimates price elasticity, weighs expected vacancies, and lets managers set an
occupancy target. Former staff said as many as 90% of its suggestions were adopted ([ProPublica,
2022](https://propublica.org/article/yieldstar-rent-increase-realpage-rent)). The key fact is that
the software trades occupancy for rent. In 2017 RealPage's chief executive said one firm with over
40,000 units moved its occupancy target from 97-98% to about 95%, and revenue rose 3-4%
([ProPublica](https://propublica.org/article/yieldstar-rent-increase-realpage-rent)). Camden
accepted about 15 points more turnover for 7.4% more revenue after adopting it (same source). This
was argued in court to be collusion. The Justice Department sued in August 2024 and settled with
RealPage on 24 November 2025. The settlement had no damages. RealPage must stop using rivals'
non-public data in live pricing and must remove features that limit price cuts
([DOJ](https://www.justice.gov/opa/pr/justice-department-requires-realpage-end-sharing-competitively-sensitive-information-and)).
Private class settlements reached nearly $360 million by May 2026; court approval was not verified
([Fortune](https://fortune.com/2025/10/03/americas-landlords-settle-claim-they-used-rent-setting-algorithms-to-gouge-consumers-nationwide-for-141-million/)).

Renewals are priced apart from new leases. Vendor data put 2025 renewal increases near 3.5-4.5%
against move-in growth near 1-2%
([LeaseLock](https://leaselock.com/renewal-lease-rent-growth-2025/), industry data). Yardi Matrix
instead reported renewal growth of 1.7% in September 2025, the lowest since before 2020
([GlobeSt](https://www.globest.com/amp/2025/10/22/retention-not-rent-hikes-is-sustaining-multifamily-revenue/)).
The two conflict. Both are industry samples, and neither is better sourced. Large owners also use
the court as a collection tool. Landlords with bigger portfolios file serially against the same
tenants, collect fees, and withdraw when tenants pay ([NLIHC on Watson et al.
2023](https://nlihc.org/resource/large-landlords-more-likely-engage-serial-eviction-filing)).
Invitation Homes paid a $48 million FTC settlement in September 2024 over filings and junk fees
([FTC](https://www.ftc.gov/news-events/news/press-releases/2024/09/ftc-takes-action-against-invitation-homes-deceiving-renters-charging-junk-fees-withholding-security)).

Small owners behave another way. A survey of 950 owners of one-to-four-unit properties found they
price below market to avoid vacancy and keep trusted tenants. Nearly half gave a discount averaging
about 16%. This comes second-hand, from a summary of Decker's study
([Planning.org](https://www.planning.org/blog/9211495/affordable-housing-without-public-subsidies/)).
Most small properties are self-managed, about 75% of their units, and 46% are part of the owner's
retirement plan ([Terner/Decker
2021](https://ternercenter.berkeley.edu/wp-content/uploads/2021/07/Small-Rental-Properties-Decker-July-2021.pdf)).
Rent stickiness is old and measured. In 1974-81 US apartment data, 29% of units had no nominal rent
change from one year to the next, and rigidity was highest for sitting tenants ([Genesove, NBER
w7137](https://www.nber.org/papers/w7137)). The new-tenant rent index leads the all-tenant rent
measure by about four quarters. In 2022 Q2 the first showed 11.88% a year against 5.14% for the
official rent index ([Cleveland
Fed](https://www.clevelandfed.org/-/media/project/clevelandfedtenant/clevelandfedsite/publications/working-papers/2022/wp-2238-disentangling-rent-index-differences.pdf),
via search summary).

Who owns rental homes nationally is recorded, but the figures disagree. In the 2021 Rental Housing
Finance Survey, individuals held 70.2% of properties and 37.6% of units ([CRS
R47332](https://www.everycrsreport.com/reports/R47332.html)). For 2024, one report gives about 59%
of properties and about 32% of units
([HousingWire](https://www.housingwire.com/articles/small-investors-housing-supply/)). HH's reading
of the 2024 public file gives 35.4% of rented homes. That figure drops owners not reported, 10.8% of
homes (HH Appendix B). The denominators differ, so HH's figure is the better one for the game's
opening split. About four in ten rental properties carry a mortgage: 41% in 2021 by one source, 42%
in an earlier survey by another, and the year is unresolved ([MBA
NewsLink](https://newslink.mba.org/?p=100907)).

### Rents follow vacancy slowly, and decline is not the mirror of growth

The best measured link between vacancy and rent comes from 29 metro areas in 1987-96. The effect of
log vacancy on yearly real rent growth is about -0.025 to -0.031. About 22% of the gap to the
equilibrium rent closes each year. The "natural" vacancy rate, where real rents hold flat, is
4.0-4.5%, and 4.2% for Detroit ([Gabriel and Nothaft, read in
full](https://lusk.usc.edu/sites/default/files/working_papers/wp_1999_100.pdf)). The paper does not
say whether its dependent variable is a fraction or a percent. The note-taker reads it as a
fraction, which would mean a doubling of vacancy lowers rent growth about two points a year. That
reading is unconfirmed. Those rates are on the BLS sample's basis and cannot be compared directly
with the Census vacancy survey, which put national rental vacancy at 7.1% in 2025 ([FRED
USRVAC](https://fred.stlouisfed.org/data/USRVAC)). Asking rents move faster than average rents. In
Austin, after about 31,000 units were delivered in 2024, vacancy peaked near 15.8% and asking rents
fell about 8.3% in a year
([Northmarq](https://www.northmarq.com/insights/insights/multifamily-renter-demand-outpaces-new-deliveries-first-half-austin);
[Pew](https://www.pew.org/ru/research-and-analysis/articles/2026/03/18/austins-surge-of-new-housing-construction-drove-down-rents)).
That is a single case.

Over a decade, rents track local jobs about one for one in both directions. Across 215 metros,
decennial census data for 1980-2000 give an elasticity of rents to a local labor-demand shock of
0.842. Population, though, is strongly lopsided: it rises a lot after good shocks and barely falls
after bad ones, because houses last ([Notowidigdo, NBER w17167, Table
4](https://www.nber.org/system/files/working_papers/w17167/w17167.pdf)). Glaeser and Gyourko explain
the mechanism. Durable housing means that when prices fall below what it costs to build, nothing is
built, and a city shrinks only as houses decay ([NBER w8598](https://www.nber.org/papers/w8598)).
Owner-occupied homes valued below replacement cost get about 50% less renovation ([Gyourko and
Saiz](https://www.philadelphiafed.org/-/media/frbp/assets/working-papers/2003/wp03-9.pdf)). That is
the road a declining Detroit block takes: upkeep stops, then tax goes unpaid, then the home is
taken, then it is demolished at public cost.

What a let home costs is measured. In 2021 the median operating expense, before debt, was $380 per
unit a month against median rent of $1,000. The 38% ratio is the searcher's division, not the
survey's ([HUD on RHFS 2021](https://archives.hud.gov/news/2022/pr22-242.cfm)). In 2024 the mean
yearly operating cost per unit ran from $5,820 for two-to-four-unit properties to $10,979 for 50+
units. The median debt-service coverage (net income over mortgage payments, times 100) was 80 for
single-unit and 74 for two-to-four-unit properties. In other words, the median small mortgaged
rental did not cover its mortgage from rent ([RHFS 2024
infographic](https://www.census.gov/content/dam/Census/programs-surveys/rhfs/2024-rhfs-infographic.pdf)).
Desmond and Wilmers found that profit per unit is higher in poor neighborhoods of low-cost cities.
Rents there are only modestly lower, but prices, mortgages and taxes are much lower. Annual rent ran
about 25% of property value where 50-60% of people are poor, against about 10% in low-poverty areas
([Route
Fifty](https://www.route-fifty.com/management/2019/03/how-poor-americans-get-exploited-their-landlords/155780/?oref=rf-next-story),
press summary; the data year is unconfirmed).

### A landlord with debt breaks after losing about a tenth of its rent

Agency lenders size multifamily loans to at least 1.25 times debt-service coverage and at most
75-80% of value. That comes from a search summary of Fannie Mae term sheets ([Fannie
Mae](https://multifamily.fanniemae.com/media/document/pdf/conventional-properties-term-sheet)).
Operating costs do not fall when tenants stop paying. The note-taker's arithmetic follows from that.
With operating cost at 40% of gross rent and debt sized at 1.25 times, a shortfall of about 12
points of gross rent takes coverage to 1.0. Below 88% collections the building cannot pay both costs
and debt. A mortgage-free small owner can lose up to about 60% of rent before the building costs
more than it brings in. Its pain comes through its own household budget, its taxes and its repairs
(note-taker's arithmetic, `landlord_under_pressure.md` §2). Real buildings sit near that edge. In
New York rent-stabilized buildings, collections at full occupancy fell to the low 70s in 2020 and
are about 92% now. Of CPC's surveyed loans, 32% had coverage below 1.0 in 2024. Those with payments
60 or more days late, counting homes taken back, were 12% in December 2025. Before 2020 the lender
had almost never enforced a loan ([CPC data brief, April
2026](https://communityp.com/wp-content/uploads/2026/04/CPC-NYC-Portfolio-Data-Brief-2026-final2.pdf)).

Landlord behavior under shortfall was measured in 2020-21, under moratoria and federal aid, so these
figures are a lower bound. About a third of landlords of every size collected under 90% of rent in
2020. Some 19% missed a mortgage, tax or utility payment, against 4% in 2019. Among those short 10%
or more, 37% missed one; among those short 50% or more, 56%. Deferred maintenance rose from 5% to
31%. Repayment plans rose from 15% to 50%. Small owners were likely to seek eviction in under 10% of
cases when a tenant was less than two months behind, about 20% at three to five months, and nearly
70% at six months or more. Listings for sale rose from 3% to 13% ([JCHS/Terner, Sept
2021](https://www.jchs.harvard.edu/sites/default/files/research/files/harvard_jchs_impact_on_landlords_two_national_surveys_kneebone_et_al_2021.pdf)).
The surveys had response rates of 2% and 5%, so they carry selection bias. Among mortgaged rental
owners, lender forbearance peaked at 10.3% in June 2020 and missed payments at 6.9% in May 2020
([JPMorgan Chase
Institute](https://www.jpmorganchase.com/institute/all-topics/housing/how-did-landlords-fare-during-covid)).

The order of retreat is clear in the record. Repairs go first. Tax and utilities come next. The
lender comes last, because a missed mortgage brings the lender in. Older studies of disinvestment
describe the same sequence ending in abandonment ([MSU thesis
summary](https://d.lib.msu.edu/etd/9104/OBJ/download)). A Wharton study of New York in 1990-96 found
that a ratio of liens to value above one strongly predicted abandonment; this is second-hand,
because the PDF was encrypted
([Wharton](https://realestate.wharton.upenn.edu/wp-content/uploads/2017/03/307.pdf)). Lenders prefer
to modify a loan or sell it. Signature Bank's rent-stabilized book sold for about 59 cents on the
dollar, a figure from a search summary ([NYC
Comptroller](https://comptroller.nyc.gov/reports/letter-to-federal-and-state-regulators-about-signature-banks-rent-stabilized-housing-portfolio)).
Once a lender forecloses, receivers often step in. They collect rent and file evictions, but they
often lack money for repairs
([Buchalter](https://buchalter.com/publication/the-receiver-strikes-back-navigating-coordinated-tenant-rent-strikes-through-a-receivership)).
No study follows a set of rent strikes through to default. That gap is stated plainly in the notes.

### Detroit: modest rents, the highest taxes, empty homes off the market

Detroit's numbers explain why its landlords behave as they do. In the 2024 one-year census, Detroit
had 343,649 housing units. Of these, 75,601 (22.0%) were vacant, but only 6,301 were for rent and
60,065 were "other vacant": derelict, held or abandoned. The city had 131,427 renter households
([ACS 2024 via Census
Reporter](https://api.censusreporter.org/1.0/data/show/latest?table_ids=B25002,B25004&geo_ids=16000US2622000,05000US26163,01000US)).
The note-taker's arithmetic puts homes for rent at 4.6% of the rental market in both Detroit and
Wayne County, against 5.7% nationally on the same basis. Detroit's let market is therefore tighter
than the nation's, even though one unit in five stands empty. Detroit's effective property tax was
3.02% of market value in 2024, the highest of major US cities ([Ford
School](https://fordschool.umich.edu/news/2026/nothaft-commentary-detroits-high-property-taxes-are-driving-housing-affordability-crisis)).
Median household income was $39,209 in 2024, and about a quarter of home owners had no homeowners
insurance ([Chicago
Fed](https://www.chicagofed.org/publications/chicago-fed-insights/2026/detroit-housing-data-local-responses)).

Burden is heavy at the bottom. In Wayne County, 93% of renters with incomes under $20,000 pay 30% or
more of income for housing, against 5.6% of renters at $75,000 and above. This is the note-taker's
computation from census table B25106. Of all Wayne renters, 56.6% pay 30% or more and 33.1% pay 50%
or more ([B25070 and B25106 via Census
Reporter](https://api.censusreporter.org/1.0/data/show/latest?table_ids=B25106&geo_ids=05000US26163,16000US2622000,01000US)).
Detroit's landlords are mostly small and mostly local. The 2022 Detroit Future City report counted
42,191 landlords and about 137,346 rental units. Of the landlords, 70% owned one or two properties,
the top 5% held about a third of rental properties, and 60% had a Detroit address
([BridgeDetroit](https://www.bridgedetroit.com/who-owns-rental-housing-in-detroit-new-report-offers-glimpse/)).
Compliance with the city's rental rules is very low, about 14% for one-to-two-family rentals
([BridgeDetroit/Outlier](https://www.bridgedetroit.com/detroit-eased-rental-inspection-rules-to-improve-housing-safety-it-hasnt-worked/)).
Housing attorneys argue that most Detroit landlords therefore have no legal right to collect rent
([Metro
Times](https://www.metrotimes.com/news/most-detroit-landlords-have-no-legal-right-to-collect-rent-housing-attorneys-say/)).
Nine in ten pandemic-era eviction cases came from non-compliant landlords ([U-M Poverty
Solutions](https://poverty.umich.edu/news/2022/9-10-detroit-eviction-cases-filed-during-pandemic-came-landlords-not-compliant-rental)).

The record that made this market is a loop. Detroit lost 100,116 properties to tax foreclosure in
2011-2015, one in four in the city. In every year from 2009 to 2015, 53-84% of residential
assessments broke the state's cap of half of market value, worst for the cheapest homes ([Atuahene
and Hodge, peer-reviewed, read in
full](https://southerncalifornialawreview.com/2018/01/02/stategraft-article-by-bernadette-atuahene-timothy-r-hodge/)).
About 90% of purchases at the Wayne tax auction went to investors and bulk buyers. Bulk buyers
treated eviction as a business model. Homes changed hands among them by $1 quitclaim deeds. And
2,241 homes ran from foreclosure to speculator to demolition at about $34 million ([Akers et al.,
Eviction
Machine](https://poverty.umich.edu/files/2019/08/Akers-et-al-Eviction-Machine-Revised-August-12.pdf)).
HH records a median winning bid of $1,300 in 2005-2015 (HH Appendix B). This report's inference from
those figures: a $1,300 house let at around $1,000 a month repays its price in under two months.
Skipping tax costs nothing until the three-year clock ends. So a speculator's best move is to milk
the house and let the county take it back. That loop is exactly what the rules proposed below should
produce on their own.

Several Detroit and Wayne figures conflict across the notes. The table shows both sides and which is
better sourced.

| Figure | One source | Other source | Better sourced |
| --- | --- | --- | --- |
| Wayne renter households | 246,326 of 693,446 (project table, labelled 2023, vintage unconfirmed; HH) | 247,364 of 707,662 (ACS 2024 one-year) | ACS 2024 for current; the two are close |
| Detroit median gross rent | $1,034 (2023 ACS via aggregator) | $1,091 (ACS 2024 one-year) | ACS 2024 |
| Wayne median gross rent | $1,087 (2019-23 five-year, QuickFacts) | $1,171 (ACS 2024 one-year) | Both official; different vintages and sample sizes |
| Detroit renters paying 30%+ | 49.3% (aggregator); 30.6% (no year) | 61.6% (arithmetic from table B25070, 2024, excluding "not computed") | B25070 |
| Detroit landlords | 42,191; 70% own one or two; top 5% hold about a third (DFC 2022) | 54,365; 93% own one or two and hold about 76% of rented homes (DFC 2026 as read for HH; the law notes could not open the PDF; method changed) | 2022 is well reported; 2026 is newer but unconfirmed here |
| Tax foreclosures, 2015 | 28,158 Detroit properties (Atuahene and Hodge) | About 25,000 in Wayne, 9,000+ occupied (HH Appendix B) | Atuahene and Hodge; the two cannot count the same thing |
| Over-assessment | Lowest-valued homes at 8.87 times the cap in 2009 (Atuahene and Hodge) | Cheapest fifth assessed at 7.5 times price, 2011-15, city disputes it (HH Appendix B) | Different measures; both stand |
| Wayne mortgage foreclosures, 2007 | 49,381 filings (WSWS, partisan) | 72,616 filings on 41,273 properties (RealtyTrac via a blog reprint) | Neither strong; likely different measures |
| Detroit demolitions | About 20,800 since 2014, over $250 million | About 27,000 houses in 12 years (city, Dec 2025); 29,065 (DLBA); over 30,000 (2020 release) | All city self-reports |

### Michigan's own clocks decide how a home is lost

Michigan law gives every way of losing a home its own pace. The HH ruling binds: these clocks are
never shortened to fit a run, and they are written as one record per state (HHR item 8, quoted in
HH). Local rent control is banned by the 1988 Rent Control Preemption Act (1988 PA 226). Repeal
bills, the latest being HB 4009 in 2025, have died or not been shown enacted
([MichiganVotes](https://www.michiganvotes.org/legislation/2025/house/bill-4009)).

| Path | The law's steps | In 28-day periods | What stops it |
| --- | --- | --- | --- |
| Tenant behind on rent | 7-day demand (MCL 600.5714(1)(a)); summary proceeding in district court; judgment; at least 10 days before an order (MCL 600.5744(5)); order issued within 56 days and executed within 56 more (MCR 4.201(M)) ([bench book](https://www.courts.michigan.gov/499fdf/siteassets/publications/benchbooks/lltbb/lltbbresponsivehtml5.zip/LLTBB/Ch_4_Summary_Eviction_Proceedings/Orders_of_Eviction.htm)) | About 1.5-2.5; about two at the fastest lawful pace (note's inference) | Paying the judgment plus costs before the order (MCL 600.5744(7)); retaliation presumed within 90 days of a protected complaint (MCL 600.5720); escrow for code violations (MCL 125.530); Detroit's certificate of compliance; city-funded counsel below 200% of poverty since 2023 |
| Land contract buyer | 15-day forfeiture notice (MCL 600.5728), then summary proceedings | About 1.5-3; no redemption found | Curing the arrears within the notice |
| Mortgage | Foreclosure by advertisement: four weekly notices, sheriff's sale, then redemption of six months where over two-thirds of the debt is owed, a year where less, 30 days if abandoned (MCL 600.3240) ([Nolo](https://www.nolo.com/legal-encyclopedia/michigan-foreclosure-laws-procedures.html)) | About one for notice, then 6.5 or 13 for redemption | Redeeming. The 2009 counselling window (PA 29-31) has lapsed; a "90-day" pre-sale window was not verified and should not be used |
| Property tax, Wayne | Delinquent 1 March (4% fee, 1% a month); forfeited the next 1 March ($175 fee, 1.5% a month back to delinquency); judgment in March of year three; redeem by 31 March; title passes 1 April; auction in autumn ([Wayne County Treasurer](https://www.waynecountymi.gov/Government/Elected-Officials/Treasurer/Property-Tax-Information/ForfeitureForeclosure-Timeline)) | HH: yearly return at the close of period 3; forfeiture 13 periods later; foreclosure 27 periods after the return; first homes taken about period 43 | Paying; the poverty exemption (MCL 211.7u); payment plans; the former owner's claim to sale proceeds above the debt ([Rafaeli 2020](https://law.justia.com/cases/michigan/supreme-court/2020/156849.html); Tyler 2023) |

Two things follow for play. First, a tenant's eviction is a cash event before it is a removal: a
tenant who pays the judgment stays. Few filings end in removal. In 2019 about 10,000 orders came
from 30,580 Detroit filings, a third (arithmetic), and in 2022 about 15%
([BridgeDetroit](https://www.bridgedetroit.com/?p=188803)). Where execution is recorded, in
Virginia, about 13% of eviction judgments end in an executed writ ([Virginia Equity
Center](https://virginiaequitycenter.github.io/va-evictions/writs/writs_of_eviction.html)).
Combining the two figures, which come from different places and years, guesses that about 4% of
filings end in a physical removal. The note-taker gives that guess a range of two to three times
either way. Second, unpaid Detroit water bills can be rolled onto the property tax roll. That is a
hidden road into the tax clock ([Michigan
Public](https://www.michiganpublic.org/politics-government/2016-08-12/citizen-research-links-detroit-water-shutoffs-tax-foreclosures)).

### The game's line: rent is tribute, and a house is settler standing

The game takes MIM's position. Its lineage runs through Marx, Engels, Lenin and Mao.

**Marx** treats ground rent as a share of surplus-value that the owner's monopoly of land pulls away
from functioning capital. The owner creates none of it: landed property "merely enables the
landowner ... to coax this surplus-profit out of the pocket of the manufacturer and into his own"
([Capital III, ch. 38](/home/user/Downloads/babylon_books/Capital-Volume-III.pdf)). For building
sites, location rules. "One part of society thus exacts tribute from another for the permission to
inhabit the earth," and "poverty is more lucrative for house-rent than the mines of Potosi ever were
for Spain" ([Capital III, ch.
46](/media/user/data/old-hdd/old-hdd/www.marxists.org/archive/marx/works/1894-c3/ch46.htm)). Marx
separates house rent into interest and amortisation on the building on one side and rent for the
land on the other (same chapter). He says plainly that rent actually collected can be "a deduction
from the average profit or from the normal wages, or both" ([ch.
37](/home/user/Downloads/babylon_books/Capital-Volume-III.pdf)). The price of land is rent
capitalised at the rate of interest. It "may rise ... by a mere fall in interest rate" with rent
unchanged ([ch. 37 and ch.
46](/media/user/data/old-hdd/old-hdd/www.marxists.org/archive/marx/works/1894-c3/ch46.htm)).

**Engels** says the tenant-landlord deal is "simple commodity sale", "a transfer of already
existing, previously produced value". He lists what rent must cover: building costs, "repairs and
the average sum of bad debts, unpaid rents, as well as the occasional periods when the house is
untenanted", and ground rent ([Housing Question, Part
One](/media/user/data/old-hdd/old-hdd/www.marxists.org/archive/marx/works/1872/housing-question/ch01.htm)).
On home owning he says: "chain them once again to the soil and you break their power of resistance".
The house is not capital for the one who lives in it, "just as a coat ceases to be capital the
moment I buy it from the tailor and put it on". Where owning becomes general, "wages would fall on
an average corresponding to the average sum saved on rent" ([Part Two,
I](/media/user/data/old-hdd/old-hdd/www.marxists.org/archive/marx/works/1872/housing-question/ch02.htm)).
**Lenin** gives the mechanism of alignment. Superprofits buy "the upper stratum of the labour
aristocracy", who are "quite philistine in their mode of life ... and in their entire outlook" and
in civil war "take the side of the bourgeoisie" ([Imperialism,
Preface](/home/user/Documents/books/LeninImperialism.pdf)). **Mao** gives the staging of rent
struggle. "Rent reduction must be the result of mass struggle, not a favour bestowed by the
government" ([7 Nov 1945](/media/user/data/mim/etext/classics/mao/sw4/mswv4_08.html)). Political
authority over the landlord comes first ([Hunan
report](/media/user/data/mim/etext/classics/mao/sw1/mswv1_2.html)). He also gives a three-wing
reading of small owners. The right wing has "some surplus money or grain" and wants to climb. The
middle "prefer to be neutral". The left wing are "those whose standard of living is falling ...
their debts mounting" ([Analysis of the Classes,
1926](/media/user/data/mim/etext/classics/mao/sw1/mswv1_1.html)).

**MIM's line** on homes is direct. "The key to full rights as an Amerikan citizen is home-ownership.
You can't be a settler without a house" ([MIM Notes 60, Jan
1992](/media/user/data/mim/etext/mn/mn060.txt)). "Net worth is means of production, in which home
equity and pension funds have to be counted" ([White proletarian myths, c.
2003-06](/media/user/data/mim/etext/contemp/whitemyths/index.html)). "Home equity is another word
for property--a kind of property that still identifies Euro-Amerikans as settlers" ([MIM, Sept
1995](/media/user/data/mim/etext/contemp/marxspace/laborarist2b.htm)). "Settlers--workers with real
estate, especially that recently seized--are more reactionary" ([MIM, 15 Sept
1995](/media/user/data/mim/etext/contemp/marxspace/laborarist2c.htm)). House-price wealth
"contributed to the corruption of the political outlook of workers here" ([MIM Notes 112,
1996](/media/user/data/mim/etext/mn/mn112.txt)). MIM treats mortgage and consumer debt as "a sign of
the ability to pay as recognized by banks" and its anxieties as "bourgeois anxieties" (White
proletarian myths). On who is exploited, the line is that a worker is exploited only "if ey earns
less than the value of the work ey performs", and that the First World wage-earner above that line
is "the lower segment of the petty-bourgeoisie ... not exploited" ([MIM(Prisons) FPL,
2023](/home/user/Documents/books/communism/FPLmimp.pdf)). On tenant struggle, MIM backed
oppressed-nation public-housing tenants at Geneva Towers ("Never trust HUD"). It warned that "even
poor people in Amerika have 'something to lose'" and that "oppressed people are disarmed politically
when we organize to grab 'a piece of the pie'" ([MIM Notes
83](/media/user/data/mim/etext/mn/mn083.txt)). HH quotes MIM Notes 239, "Household ownership is one
reason that there is not a large proletariat within U.$. borders" (HH Appendix C). The theory notes
did not re-read that issue, so treat the quotation as HH's.

**Sakai**, on whom MIM's class analysis "relies heavily" though MIM calls him an anarchist, makes
land the aim and base of the settler nation. "Where land was not available, settlers refused to
come. Period." "Every white settler could be a property owner," and "most settler workmen had no
reason to develop a proletarian consciousness" ([Settlers, ch.
I](https://readsettlers.org/ch1.html)). For 1900 he describes a settler stratum "with the majority
being homeowners and voting citizens of the Empire" (ch. V). For later decades he describes "a small
homeowning, small-propertied community" whose "garrison communities are enforcers of the oppressor
nation way of life" (ch. XIII). Alliances between settler and oppressed are "not unity, but the
momentary convergence of the fundamentally differing interests" and "just a quid pro quo" (ch. II).
Quotations from Sakai came through a page reader capped at about 125 characters, so they are
fragments.

**Where the classics and MIM disagree**, the notes are plain, and the game takes MIM's side each
time:

- *Is a worker's house capital?* Engels says no: the owner is "no longer a proletarian", but not a
  capitalist. MIM counts equity as means of production and as access to it ("The second worker can
  expect dividends or interest from investments using the equity as collateral").
- *Mortgage debt.* Engels and Eleanor Marx-Aveling read it as slavery to the usurer and the
  employer. MIM reads it as a sign of ability to pay. The gap is that Engels wrote of a worker still
  exploited by industrial capital, while MIM holds the First World worker is not exploited. Engels's
  mechanics (tied to place, tied to the lender) can stay in the game as texture, not as the class
  result.
- *Rent and wages.* Engels says that where owning is general, wages fall by the rent saved. The
  game, following MIM, lets owners keep the saving. That is a departure from Engels.
- *Who bears the shortage.* Engels says the petty bourgeoisie too. MIM says the oppressed nations,
  at the bottom.
- *Is rent exploitation?* No source calls rent exploitation of the tenant in the strict value-theory
  sense. Engels says it is not. Marx calls it "tribute", and MIM calls it parasitism.
- *Which landlord?* Mao's landlords are feudal rent collectors. Marx's are capitalist landowners.
  MIM uses the word for both without marking the difference.

**What the sources do not say.** No passage in Sakai ties mortgage equity, the pace of payment, or a
rising house value to a change in class position. Sakai treats ownership as a standing condition of
a stratum (`sakai_settlers.md`, closing caution). MIM comes closest in one 1995 reply: "if one is no
where on the mortgage yet, and the other has $100,000 in equity, there is a big difference". That is
a comparison of levels between two workers, not a rule of growth. It also partly corrects HH's
reading that "MIM ... does not sort owners by how much of the home they have paid for." MIM draws no
line between owners, but it does say the amount matters to class. Mao's three wings key small
owners' politics to whether their standing rises or falls, but he wrote of China's petty
bourgeoisie. Applying him to Wayne's owners is the reader's development. So the rule proposed below,
in which a growing stake moves outlook period by period, rests on the texts for its direction
(ownership is settler standing; equity is property and access; owners have something to lose; the
falling owner is the left wing). The rest is the reader's own building on them: the growth, the
weighing, and the pace.

### Measurement agrees on direction, not size; loss brings withdrawal

Mainstream political science is not the game's line, but it measured things the line leaves open, so
it serves here as contrast and calibration. Ansell (2014) found that rising house prices cut owners'
support for redistribution. Among US owners in 2000-04, 10% appreciation against 50% raised the
chance of wanting less Social Security from 14.2% to 22.5%. In the UK panel of 1991-2006, a doubling
of house value moved owners two-thirds of a within-person standard deviation rightward. In the 2009
survey across 29 countries, strong support for reducing income gaps was 34% among negative-equity
owners, 30% among renters, 27% among moderate-equity owners and 21% among high-equity owners
([Ansell, APSR, author's PDF pp.
12-20](https://ora.ox.ac.uk/objects/uuid:879a39dd-1b45-4bdd-8efc-60a1b885225e/files/s2j62s5086)).
Ansell reads it as "owning equity in a house, rather than the title", and finds a remaining mortgage
or trouble paying holds owners nearer the redistributive side. The effect was 1.5 to 3 times larger
for right-leaning owners and near nothing for committed left ones. Hadziabdic and Kohl found no
systematic effect of housing value on populist voting in Germany, Switzerland and the UK ([EJPR
2022](https://www.cambridge.org/core/product/FBE224817F9096D1C958986964722AA0/core-reader)), so
outside Denmark the size is uncertain. Losing a home brings withdrawal. Foreclosed Ohio owners voted
less, "so foreclosure did not mobilize them" ([Hall, Yoder and Karandikar, PSRM
2021](https://cambridge.org/core/journals/political-science-research-and-methods/article/economic-distress-and-voting-evidence-from-the-subprime-mortgage-crisis/D958A49361C3F0B59A9D6E667BB49E31)).
Buying a home raises local turnout, more than twice as much in the top price decile ([Stanford GSB
on Hall and Yoder](https://gsb.stanford.edu/insights/if-you-lived-here-you-might-be-voter-now)). In
Detroit, white owners founded 192 neighborhood associations between 1943 and 1965 to defend value
and racial boundary. That figure is second-hand, from a summary of Sugrue
([SuperSummary](https://www.supersummary.com/the-origins-of-the-urban-crisis/part-3-summary)).
Nothing measured shows that mortgages reduce strikes. The only evidence is an aggregate
cross-country link between household debt and fewer strikes ([The
Conversation](https://theconversation.com/strikes-how-rising-household-debt-could-slow-industrial-action-this-year-198466)).
The settler-colonial scholars argue, without measuring households, that alienable freehold and the
foreclosable mortgage are instruments of the settler order ([Wolfe
2006](https://dn721801.ca.archive.org/0/items/FugitiveDistro_Settler_Colonialism_And_The_Elimination_Of_The_Native_Anonymous/Settler%20Colonialism%20And%20The%20Elimination%20Of%20The%20Native_PRINT_EN_12.pdf);
[Park
2016](https://www.cambridge.org/core/journals/law-and-social-inquiry/article/money-mortgages-and-the-conquest-of-america/46A24B838E06D7A956C6C1D1792344E6)).

---

## Part two: rent, landlords, mortgages and equity as play

### What is already decided, and how the documents' disagreements resolve

The proposal keeps every decision `what_the_game_already_has.md` quotes. An owner is one kind, and
no class line is drawn by equity (HHR item 3). Landlords exist "both ways": through the property
company, and directly through owner units of the top 1% and next 9%. A landlord is read from what a
unit holds, never labelled (HH 7.7; ADR208 R9). The law's clocks are never shortened (HHR item 8).
Foreclosed occupants leave at once (HHR item 13). Bottom-half owners open with no equity (HHR item
11). Banks create money, and households can borrow (ADJ items 9-10). People move between places
slowly (ADJ item 5). Every outcome comes from accounts, never from dice or a curve drawn in advance
(CR D.1; ADR302). The proposal adds a landlord's own choices, which HH lists as later scope (HH
§11). That is new scope, not a contradiction. The disagreements that file lists resolve as follows.

| Disagreement | Resolution | Why |
| --- | --- | --- |
| Does an owner buy housing? ADR313 call 6 says owners' imputed rent is left out but every household still buys housing. HH 7.8 says an owner buys no Housing provision. SPIKE R3 has owners buy housing and the rent return to the bands that hold homes. | HH stands: an owner buys no rent. Write the ADR313 line "every household still buys its housing" as a stopgap that ends when the households lane builds homes, and amend ADR313 when step B lands. Drop R3a as written. | HH is approved and later than OPEN for homes, and OPEN itself defers homes to the households lane. R3a would make owners pay rent to themselves through the housing trade, which HH rules out. What R3a found is still true and is used below: rent in the opening is cheap because the accounts' 12.1% owners' rent was cut out. |
| Who gets housing profit? SPIKE R2a/R3a pay it by DFA share of homes to all bands. HH puts every rented home in the top tenth at the opening. | The Director's ruling binds the opening: all rent income goes to the top tenth, both ways. After the opening any band with cash may buy at the county sale (HH 7.13), so ownership of let homes can drift. It is measured, never re-imposed. The DFA rented-property split (1.0 / 14.2 / 84.8) serves only as a check on what drift looks like. | Rulings 5, 6 and 9 and the rule of thirds bind. SPIKE itself flags that DFA sorts by wealth while the game's bands sort by pay. |
| "The bottom 50% don't own homes" against 64% ownership in Wayne. | Keep the Director's reading: they own with no equity. | Already ruled (HHR item 11), and it creates the play below, where a bottom-half owner's stake begins as rent saved and grows only as it pays. |
| Equity: HH says "no rule reads it"; the Director (21 Nov) says it moves class dynamics, outlook and alignment. | The later ruling leads. Amend HH 7.8 and 7.14 so that rules read equity continuously, through a weighing. Keep the anti-goal of "a line drawn between owners by the size of their equity". | The anti-goal bans a threshold, not a continuous effect. The weighing below has no threshold. |
| County Review floor: $48 (two hours at $24) or about $74 (two hours at Wayne's average pay). | The ruled thing is the definition, two hours at the crew's own wage. The number follows the rebuilt opening, so about $74. | ADR313 is accepted, and it is later. |
| How a short seller shares its stock. | ADR312 governs: in proportion to orders, not by order of identifiers. | HH corrected itself on 20 Nov and defers to ADR312. |
| The Director's original typing in the memory files against HH's normalized spelling. | Keep the verbatim words in the memory files; HH may normalize. | No substance differs. |

One more tension is not on that file's list. HH carries a home's value at what was paid, and it
rejects "a home value that follows a market the game does not have". Once holdings post rents and
banks set rates, the game does have such a market, because Marx's capitalised rent can be computed
from its own figures. Whether to use it is a question for the owner, listed last.

### Nine rules run a rental market in four-week steps

The core proposal is a split, and it reconciles SPIKE with the census. Census median gross rent in
Wayne was $1,171 a month in 2024. That is about $1,081 per 28-day period (this report's arithmetic,
times 12/13). SPIKE's rebuilt opening prices a household's housing at $202 to $689 a period in
Wayne, depending on the option. HH opens Housing provision at $1,450. The gap is not an error to be
tuned away. It is the difference between what the service costs and what tenants actually pay.
Following Engels's list and Marx's split, a tenant's rent has two parts. The first is the service:
upkeep labor, materials, management, which the engine already makes as Housing provision at cost
plus margin. The second is the holder's take, a transfer to the holder that the holder does not
produce. The holder buys the service. The tenant pays the holder. The holder's take is what feeds
the top tenth's third and every fight below.

| Rule | What it does (decided from the account's own figures) | Grounding |
| --- | --- | --- |
| 1. Asking rent | Each holding (one holder, one place, one building-size class) posts an asking rent for its empty homes. It falls one step in a period that ends with a home empty for the whole period. It rises one step in a period when the holding turned away a seeker it could not house. It never falls below the upkeep a let home needs, because tax and debt are owed whether the home is let or not. The step is the engine's existing price step. | Measured: asking rents respond faster than average rents (Austin); an average vacancy spell lasts 1.5-2 months (Gabriel and Nothaft). The step rule is the engine's built ServiceResponsive rule, now applied per holding. |
| 2. Sitting rent | Each tenancy keeps its own rent. On its yearly anniversary (13 periods after it began, so set by start date, not by chance), a company tenancy moves to the asking rent. A tenancy held directly keeps its rent until the tenant leaves; the next tenancy takes the asking rent. | Measured: renewal and move-in growth differ (vendor data, conflicting); small owners hold rent and catch up at turnover (Decker, second-hand; Genesove 1974-81). |
| 3. Vacancy | An empty home earns nothing and still pays tax (HH's school tax on let and empty homes), insurance and debt. Seekers (evicted, newly formed, arriving, or moving) take the cheapest empty home their cash covers for two periods, which is HH's rule. Seekers are ranked by their own cash, and splits use largest remainder. A home is "unfit" when the upkeep it is owed exceeds the home's value, and an unfit home leaves the let market. | Engels counts "periods when the house is untenanted" in rent. Detroit's empty homes are mostly off the market (ACS 2024). The unfit test compares two of the home's own figures, so no fixed number is drawn. |
| 4. The holding's books | Rent collected first pays whatever would cost the holding soonest under a clock, then debt service, then property tax, then upkeep, then the holder's share. Under HH the company keeps a 10% management part from holders' shares and holds back 15% tax on the holder's rent. | The order of retreat is measured: repairs go first, the lender last (JCHS/Terner 2021). It mirrors HH's household rule of paying first whatever would cost the home this period. |
| 5. A holding that loses money | When cash runs short, upkeep is skipped first, so deferred upkeep piles up. Tax is next, which starts the law's tax clock at the yearly return. Debt service is last, which starts the lender's clock. A holder walks away from a holding when its liens (debt, tax owed, fees) exceed its value; the county takes it at tax foreclosure and offers it twice, as in HH 7.13. | Measured: about 12 points of lost rent breaks a holding with debt sized at 1.25 times (arithmetic); liens above value predicted abandonment (Wharton, second-hand). Detroit's loop from foreclosure to speculator to demolition comes out of this rule with cheap prices and a long tax clock. |
| 6. The landlord's answer to arrears | The company files on the period a tenant falls behind, because a filing costs less than a period's rent and works as collection. A direct holder files only when the arrears exceed what an eviction would cost it. | Measured: large owners file serially (Watson et al. 2023). Small owners rarely seek eviction under two months' arrears (2020-21). An eviction costs about two to three months' rent (low-grade industry sources). |
| 7. How a household loses its home | A tenant moves through the law's stages: demand, filing, judgment, 10 days, order. A tenant that pays the judgment plus costs stays. Each stage is a place to intervene (counsel, the certificate defense, escrow, retaliation). An owner loses its home to tax under HH's clock, may claim proceeds above the debt, and leaves at once at the judgment. If the lender may foreclose, the owner gets notice, a sale, and the law's redemption, then leaves at once when title vests. | The statutes in the table above. The Director's "leave at once" applies where the law leaves the moment open; redemption is the law's own clock, so it is kept. |
| 8. Equity | Equity is carrying value less balance less arrears (HH). It grows by the principal paid each period. It is drawn on through a home-secured loan from the bank, within the bank's own capital limit (ADJ 9-10). It is lost through arrears and fees, through foreclosure (keeping only the surplus claim), and through a fall in value if value moves (owner question 5). | HH 7.9; MIM's equity as collateral; Michigan's surplus rule. |
| 9. The stake | Each owner household's stake is its equity, plus the yearly rent it does not pay, plus the standing its home tax buys at the County Review. The stake is weighed against what a struggle in reach would give it (next section). | MIM, Engels, Mao, Ansell; the Director's ruling that home tax counts in relief (HHR item 7). |

Three consequences of these rules matter for play. The first is that HH's mortgage schedule builds
equity fast. HH sets each period's payment at the balance divided by periods remaining, plus
interest at 5% a year, over 196 periods. That pays the same principal every period. By this report's
arithmetic, about 57% of the first payment is principal. A bottom-half owner who opens with no
equity holds 6.6% of its home after one game year and 26.5% after the 52-period run HH requires. A
real 30-year loan at 6.5% repays about 1% in year one and about 6% by year five (note-taker's
arithmetic). So HH's equity grows several times faster than a real loan early on. That suits play,
since the change is visible within a run. It is still a choice (owner question 6). As a check, at
Wayne's median owned-home value of $170,200 (2019-23), HH's schedule asks about $1,520 a period. The
census median owner cost with a mortgage, which also includes tax and insurance, is $1,512 a month
(arithmetic; [QuickFacts](https://census.gov/quickfacts/waynecountymichigan)). The schedule sits in
the observed range.

The second is that these rules make the economy's adjustment visible through housing. ADJ item 5
says households move toward work over years and "rents follow". Under rules 1 and 3, out-migration
leaves empty homes, which lowers asking rents step by step, which squeezes holders whose debt was
sized for full rent. That matches the measured lopsidedness in which rents fall with jobs but people
barely leave (Notowidigdo). No curve is drawn. The fall comes from each holding's own empty homes.

The third is that the landlord becomes a counterparty, not weather. The rent a tenant pays has an
author with a name, a cash balance and a debt, and so a weak point.

### Equity moves outlook by weighing stakes, never by a line

The owner is one kind from the first period. The Director's words: "the class aspirations of someone
who owns a home with little-to-no equity is the same as someone who owns a home with equity, and low
equity evolves into equity over time" (HHR item 3). Rule 9 respects this. Even a bottom-half owner
with no equity has a stake from the opening: the rent it does not pay, and the standing its home tax
buys at the county. This is MIM's "you can't be a settler without a house" expressed in the
household's own dollars. What changes over time is how large the stake is, and so how much any
struggle has to offer before the household will risk it.

**The weighing.** A household joins an action when what the action offers it is more than what
joining puts at risk of its own stake. Both sides are in its own figures. The offer is the demand
translated into that household's dollars: relief won, tax excused, old debt cut, rent reduced, a
home kept. The risk is what the action could cost it: for an owner on a tax or mortgage strike, its
home on the law's clock; for a tenant, its tenancy on the eviction clock. The group's response is
the count of households the comparison admits, as the counting law requires. Nothing is drawn at a
fixed level of equity. A household with more equity simply needs a bigger offer. Owners differ home
by home because HH keeps a balance per mortgaged home. If the opening spreads remaining periods
across homes rather than giving all 196, households cross the comparison one at a time as they pay
down. Drift is gradual and needs no dice. This is the direct answer to the theory notes' open
question about where thin equity stops counting as settler-aligned: nowhere fixed. Thin equity is
simply a small stake, cheap to outweigh.

**Direction as wing.** Mao's reading supplies the sense of motion. An owner whose stake rose this
period stands with the order (the right wing, wanting to climb). One whose stake held flat stays
neutral. One whose stake fell as debts mounted (arrears, the tax clock running, value lost) is the
left wing, and in the game it is the owner the organizer can reach. The direction is read from this
period's stake against last period's, so no meter is stored and no curve applies. Measurement points
the same way, both up and down, with negative equity above the renter baseline (Ansell). Engels's
texture belongs here too. A heavily mortgaged owner is tied to place and lender, so its risk on any
strike is large.

**What the stake does in play.** The stake changes class dynamics as well as mood, and through a
mechanism MIM names: equity is access. Through rule 8, equity is borrowing power at the bank. An
owner of the next 40% can draw on it to buy a tax-foreclosed home at the county sale and let it.
From then on it is read as a landlord, by HH's own rule that a landlord is read from holdings. That
is how class moves in this game without a label: equity becomes credit, credit becomes a let home,
the let home pays rent, and the rent makes the household's stake larger still. It mirrors the record
that 90% of auction purchases went to investors. Owners with large stakes also form the opposing
body. When a threat to their stake arrives in their place, such as land-bank homes let to tenants, a
strike next door, or a relief claim that competes with their ranking, they press the county. This
follows Sugrue's 192 associations (second-hand) and Sakai's garrison community.

**The line's verdict, built in.** MIM warns that organizing settler owners around their property is
fighting for "a piece of the pie". Sakai calls such alliances "just a quid pro quo". The weighing
reproduces both without any extra rule. An owner won by a tax offer joins only while the offer
outweighs its stake. Once it is paid and its equity recovers, its stake grows back and it leaves.
The player can make that bargain. The game shows what it buys. Owners who lose their homes move the
other way and withdraw, as measured in Ohio and Milwaukee. A foreclosed household becomes a homeless
tenant with no stake that comes to nothing until the organizer reaches it. That is the Director's
"more opportunity to intervene", made a real race against time.

**The settler level.** The stake exists only while the county, the courts and the police enforce
title. Wolfe and Park argue that alienable, pledgeable, foreclosable land is how the settler order
was made. In the game, a household defending its stake is defending the order that enforces it. That
is the precise sense in which home ownership is the level at which settler colonialism lives in a
household. It is the reader's development of MIM and Sakai, not a claim found in either.

### A ladder of collective action, decided by whose cash runs out first

Every step below is decided the same way. Two runways race, each computed from accounts. The
landlord's runway is its cash plus any forbearance, divided by the gap between its fixed costs and
the rent still coming in. The tenants' runway is how many periods each member can hold before
removal: the law's stages, lengthened by counsel and defenses, and kept going by whatever the
organization's hardship fund can pay toward judgments. Members leave when their own figures say that
paying costs less than losing the home. The landlord concedes when a concession costs less, over the
lease year, than the rent it will lose before it can remove the strikers. Third parties enter by
their own rules. The lender comes in when payments are missed. The court acts by statute. The police
come with the officer hours the city can assign. This follows the case record. Wins had dense
participation, a landlord under debt or lender pressure, a third party, and a legal route. Losses
had thin participation, injunctions, police backing, and a landlord with cash
(`tenant_struggles_tactics_outcomes.md` §6, a qualitative synthesis with no measured win rates). The
notes' suggestion of a "win probability" is replaced here by those runways. No outcome is drawn.

| Step | What it needs | What it does to the landlord's books | How landlord, lender, court and police answer | What decides it |
| --- | --- | --- | --- | --- |
| 1. Building committee | Organizer contacts with households in one holding | Nothing yet. It reveals the rent roll and conditions to the player. | Landlord: non-renewal, a filing against a leader, a rival group, credits for staying out (alleged in [In These Times](https://inthesetimes.com/article/tenants-union-busting-landlord-capital-realty)). Court: a retaliatory eviction within 90 days of a protected complaint is presumed retaliatory (MCL 600.5720). | Whether a protected complaint was filed in time. The 90-day clock is about three periods. |
| 2. Complaint and certificate | A code complaint; Detroit's inspection | A holding without a certificate cannot win rent in court (attorneys' argument; DTU's 2026 suit). Its filings fail until it repairs. | Landlord: repairs (upkeep spending rises), sells, or walks away. Court: the certificate check, which the 2026 DTU suit seeks to enforce. | The repair cost against the rent at risk. With compliance near 14%, most holdings are exposed. |
| 3. Escrow | A violation, legal aid, and counsel (Detroit, under 200% of poverty) | Rent is blocked, not lost (MCL 125.530). Cash falls, debt does not. | Landlord: repairs to release the escrow, or sues for it (Ann Arbor 1969). | Months of blocked cash against the repair bill. Mild, and lawful. |
| 4. Rent strike in one holding | A majority of the holding's tenant households, floor captains, a hardship fund | Collections fall. About 12 points of lost rent breaks coverage at 1.25 times (arithmetic). | Landlord: files against every striker and asks for injunctions. Lender: forbearance, then a receiver who collects and evicts but has no repair money. Police: execute orders. | The two runways. Independence Towers, Kansas City, 2024-25: 247 days, lender suit and receiver, sale, a one-year contract, no repayment of strike rent ([In These Times](https://inthesetimes.com/article/rent-strike-victory-kansas-city), advocacy outlet quoting an organizer). |
| 5. Eviction defense on the day | A block network and a crowd present at execution | Delay. An unexecuted order lapses after 56 days and the landlord must file again. | Police and court officers clear the crowd if enough are assigned; arrests follow. | Crowd present against officer hours assigned, both counts. The city's police budget and politics set the hours. |
| 6. Portfolio strike against one holder | Committees in several of its holdings, plus press | Hits the holder's total rent and its covenant with the lender | Holder: landlord associations, picketing bans, blacklists (Bronx 1932-33). Lender: acceleration across the portfolio. | The holder's total runway. UTCA in 1968: six councils struck Goodman Brothers at once, "crippled the company", and won control of 17 buildings with 75% of rents ([Rise Up Detroit](https://riseupdetroit.org/chapters/chapter-2/part-3/tenant-organizing/), unfootnoted). |
| 7. Auction and land-bank action | Organization cash; a crowd at the county sale | Deters bulk buyers from the second offer at $500 | County: holds the home in the land bank. Investors: outbid. | Cash on the day against the bulk buyer's cash. Penny auctions of the 1930s are the pattern ([penny auction](https://en.wikipedia.org/wiki/Penny_auction_(foreclosure))). |
| 8. County and state demands | Households at the County Review; a mass behind the demand | Relief or exemption paid from the county pot; at state level a moratorium or new law | County: ranks by tax paid, so tenants stand below owners (Director). State: rent control is barred (1988 PA 226). | The county's cash and its spending limit. State changes are later scope. Michigan's 1933 Act 98 is the precedent for a delay won by pressure. |
| 9. Taking over a holding | Financing, the majority's consent, the organization's competence | The holder sells, or a receiver sells | Price, delay; construction-trade hostility (UTCA's Accord, Inc. failed within two years) | Cash and capacity. After taking over, the organization is read as a landlord (owner question 7). |

Mao's rule shapes what a win builds. A rent cut granted by the county as a favour builds nothing in
the game. A cut won by a strike leaves a committee, members and a hardship fund that carry to the
next fight. MIM's caution shapes where the base is. In MIM's US line, organized rent struggle is
chiefly the oppressed nations' fight, with independent power as the aim, not a share of settler
privilege.

### Player-made crises run through rent within a period or two

The Director asked that organizing could itself cause crises: "a call for a general strike, a union
organizing effort, a tenant rent strike, a mass protest that disrupts commerce and roads". Rent is
the channel that turns each of these into a citywide event without any script. A general strike
stops wages for striking households. Within one period many tenants fall behind together. Their
holders' collections fall, and holdings with debt break coverage. Holders miss debt service, and the
lender (HH's Wayne business-services lender, or ADJ's banks) books losses. The bank's capital limit
tightens, a credit crunch reaches businesses' borrowing (ADJ item 10), and more layoffs follow.
Striking owners miss mortgage payments, which in HH's slice are only a debt plus a 5% fee. They also
miss tax, which starts the yearly clock. The county's cash falls from both sides, and in CR's
recorded runs relief already stops around period 30. The government defaults to rescuing the big
companies (ADJ item 12), here the property company and the lender, and that rescue becomes the next
fight. A mass protest that closes roads cuts shops' sales and transport income, and with them wage
hours, and the same chain follows a period later. A union drive that wins a raise in a tight let
market leaks to landlords. Asking rents climb where homes are full (rule 1), and Marx's point that
rent can be "a deduction from ... normal wages" plays out in front of the player. That gives a
material reason to pair a union drive with a tenant committee. Detroit's 1933 bank holiday is the
historical shape: deposits frozen, tenants and owners unable to pay, then staged repayment ([1956
MSU thesis](https://d.lib.msu.edu/etd/23693/FULL_TEXT/view)). Each step in these chains is a
transfer between accounts that exist, so the crisis is emergent and fully traceable.

### What the player sees: books, clocks and the race

The player sees four things, each traceable to a cause in a few steps.

The first is the holding's ledger: homes let, homes empty, asking rent, the rent roll, collected
this period, upkeep owed, tax owed and its clock, debt service and its lender, cash, and "periods of
cash left" (the landlord's runway). Figures beyond the structure are earned by organizing. Committee
members know the rent roll, a court filing reveals arrears, and the county's public record already
lists holders with unpaid tax (HH 7.12). This fits the project's existing rule that structure is
public and magnitudes are earned (ADR182, per the project memory index rather than the notes).

The second is clocks drawn as stages. Each tenant household's eviction stage is shown with the next
legal step and what would stop it. Each owner's tax track is shown with return, forfeiture and
judgment. The lender's notice and redemption are shown too.

The third is the race preview before any action. It shows the landlord's runway against the members'
runway from current figures, labelled as a forecast that changes with the landlord's, lender's and
households' own choices.

The fourth is the stake readout for owner forms: equity per household, rent saved, standing at the
county, and how many households the current offer would admit. Alongside it are counts of owners
rising, flat and falling, Mao's three wings.

HH's first screen stays as the summary: four bands by tenants and owners, with paid, behind, lost
and bought, and homes held to let. Alerts name an actor and a number ("Holding on Linwood missed its
tax; 14 homes now on the county's clock"), never a mood.

### Detroit's own record supplies the precedents

| Precedent | What it shows for play | Evidence quality |
| --- | --- | --- |
| Unemployed Councils, 1930-33: block alerts, crowds at evictions, furniture returned; reported evictions about 150 a day in summer 1931 | Eviction defense raises the cost of each eviction but does not change the household's cash; relief money decided that | Movement accounts and one journal; no count of evictions stopped ([Against the Current](https://againstthecurrent.org/atc213/the-detroit-left-social-unionism-in-the-1930s/)) |
| Ford Hunger March, 7 March 1932: about 4,000 marchers; five killed; 60,000 at the funeral | A mass march on an employer-creditor meets gunfire; outrage without relief | Reuther archive ([Reuther](https://reuther.wayne.edu/node/7291)); wounded counts conflict (22, about 50, up to 60) |
| City relief collapse, May 1932; levy over a third delinquent | A public body goes broke when delinquency, debt service and relief demand meet; the way out is outside money | Historian Bates ([UNC Press blog](http://uncpressblog.com/2014/02/26/beth-tompkins-bates-what-happened-the-last-time-detroit-faced-bankruptcy/)) |
| Bank holiday, 14 February 1933: $1.5 billion of Michigan deposits frozen | A bank failure freezes households' cash, and rent and tax go unpaid | Thesis; final depositor loss disputed (paid in full eventually, against planned 50-72%) |
| Michigan Act 98 of 1933: courts may delay mortgage foreclosure to 1 March 1935 | Pressure converted into a time-limited delay, upheld after Blaisdell | Search summaries ([1934 cases](https://hallapproved.com/mi/cases/supreme/1934/3522265/)) |
| Birwood wall, 1941: FHA guarantees in exchange for a wall | Credit is a gate that lenders and officials control by neighborhood | [Wikipedia, Detroit Wall](https://en.wikipedia.org/wiki/Detroit_Wall) |
| Sojourner Truth Homes, 1942: white mobs; 1,600 Guard and police for 168 Black families | Owners' associations against public housing; the opposing body in action | Second-hand; move-in date conflicts (28 February or 29 April) |
| Tenants' Action Council, 1964 (50+ building groups); UTCA, 1967-69, against Goodman Brothers | A portfolio strike against a visible owner won buildings, then lost them to lack of capital, trade-union sabotage and violence against its leader | Educational site without footnotes |
| 1968 Tenants' Rights package: escrow (MCL 125.530), new defenses | The state converts strikes into court channels | Search summaries of law reviews |
| Section 235, about 1968-74: insured loans on overpriced houses; Detroit's abandonment wave | When the state insures the lender, the lender's risk disappears and the household's does not | Second-hand counts of 15,000-25,000 Detroit houses, unverified |
| Sheriff Evans halts sales, 2009, and reverses after a lender's suit | An official's moratorium is cheap to reverse; law outlasts it | Trade press ([HousingWire](https://www.housingwire.com/articles/michigan-sheriff-halts-foreclosure-sales/)) |
| Tax foreclosure, 2011-15: 100,116 properties; payment plans for 7,000+ households by March 2015 | The tax clock and the auction as the main machine of loss; relief came as plans, not a halt | Peer-reviewed ([Atuahene and Hodge](https://southerncalifornialawreview.com/2018/01/02/stategraft-article-by-bernadette-atuahene-timothy-r-hodge/)); public radio |
| Water shutoffs, 2014 onward; Judge Rhodes finds no enforceable right to water | A creditor's lever that rides onto the tax roll | Press; nonprofit magazine |
| Bankruptcy, 2013-14: general retirees cut 4.5% and lose cost-of-living raises; $816 million Grand Bargain | Who takes the haircut is fought over and settled by officials and outside money | Wikipedia; city release |
| Right to counsel, 2023: more than 16,000 clients by December 2025 | Counsel changes outcomes inside the clock, not the clock | City evaluation ([Stout](https://detroitmi.gov/sites/detroitmi.localhost/files/2026-06/Stout%20Detroit%20-%20FINAL.pdf)) |
| Leland House, 2025-26: over $500,000 compensation, settled at a bankruptcy hearing | A failing owner plus a union yields a building-level settlement | TV station reporting DTU's figure ([ClickOnDetroit](https://www.clickondetroit.com/news/local/2026/11/07/detroit-tenants-union-secures-compensation-agreement-for-displaced-leland-house-residents/)) |
| DTU suit against the 36th District Court over certificates, 2026 | The certificate as a lever usable by every tenant of a non-compliant holding | Press ([Michigan Public](https://www.michiganpublic.org/politics-government/2026-09-15/why-this-detroit-tenants-lawsuit-is-making-landlords-nervous)) |

The pattern across the record is an inference from the notes. Crowd-based fights won delay or
building-level gains, which were then turned into statute or lost. Fights against systems (bank, tax
roll, water, bankruptcy) were decided by officials, courts or outside money. Each time, the other
side's weak point was a single exposed stream of cash.

### Lessons from other games, and the failure each risks

Other games give patterns and warnings only. Nothing here recreates any of them.

| Pattern | Where it is documented | Use here | Failure it risks |
| --- | --- | --- | --- |
| Two rule sets on one land base | The Landlord's Game, 1904 ([Public Domain Review](https://publicdomainreview.org/collection/the-landlords-game)) | Who receives rent is a visible lever: holder, county or tenants' body | Only the hoarding version survives play; or the shared one reads as a lecture |
| A bill with staged consequences | Papers, Please ([Game Developer](https://www.gamedeveloper.com/design/what-games-can-learn-from-the-engagement-layers-of-papers-please)); Spent ([Wikipedia](https://en.wikipedia.org/wiki/Spent_(game))) | Rent and tax as stages with a next step and a way out | A fixed deduction with one right answer becomes tedium |
| The opponent as an actor with books | Contrast: Cities: Skylines II removed its landlords after rent complaints ([PC Gamer](https://pcgamer.com/games/city-builder/cities-skylines-2-kills-off-its-virtual-landlords-to-save-players-from-soaring-rent-prices-the-existence-of-which-is-news-to-them), headline only) | Every rent has a named holder with cash and debt | Without the holder, rent is weather and the player blames the simulation |
| A lever that costs its user | Hegemony's strike, "a game of chicken where perhaps everyone suffers" ([Player Elimination](https://playerelimination.com/2023/09/21/coin-goes-to-washington-a-hegemony-lead-your-class-to-victory-review)) | Strikers risk their homes; the hardship fund is spent | Both sides always lose, or the end of a strike is unclear; show what ends it |
| The opponent's routine feeds the movement | Root's Woodland Alliance outrage ([Leder Games](https://ledergames.com/blogs/news/root-hard-cuts-the-continued-development-of-root)) | Each filing and each eviction in a place raises what the organizer can offer there | The designer reported that softening the faction for fairness removed its tension |
| A graded debt ladder | Offworld Trading Company ([Designer Notes 5](https://designer-notes.com/otc-designer-notes-5-debt)) | A holder's coverage and lender standing as a readable rating | Free debt invites "debt diving"; permanent penalties freeze play into one safe opening |
| Shared loss | Cross Bronx Expressway's bankruptcy rule ([Player Elimination](https://playerelimination.com/2025/12/15/the-legacy-of-robert-moses-a-cross-bronx-expressway-review/)) | The county's cash couples owners, tenants and landlords | "Always near collapse"; players court collapse for standing |
| Value pools plus a profit preview | Victoria 3 ([Game Developer](https://www.gamedeveloper.com/design/deep-dive-modeling-the-global-economy-in-victoria-3)) | The race preview and the holding's ledger | Opacity and a routine that turns dull (Kotaku) |
| Short, attributable cause chains | Sylvester, "The Simulation Dream" ([Game Developer](https://gamedeveloper.com/design/the-simulation-dream)) | Every alert names a holding and a figure | Tangled chains bury the story "unobserved" |
| Pacing of what surfaces, with mercy | RimWorld's storyteller ([Game Developer](https://gamedeveloper.com/design/how-i-rimworld-i-fleshes-out-the-i-dwarf-fortress-i-formula)) | Only for choosing which events the player is shown; never for deciding what happens, which stays with accounts | Using it to make events would break the no-dice rule |
| A failed firm becomes a neutral actor | Offworld's subsidiaries ([Designer Notes 17](https://www.designer-notes.com/otc-designer-notes-17-stock-market/)) | A receiver runs a failed holding by its own rules | The winner inherits too much to manage, and the game snowballs |

The notes found no game that models mortgage equity as play or a leveraged landlord brought down by
its own debts. Both are open ground.

## Conclusion

The research changes the question. Rent is not a price to be tuned. It is the meeting point of three
ledgers: the tenant's wage, the holder's debt, and the county's tax roll. Detroit's history is the
record of what happens when any one of them breaks. Once the holder's take is separated from the
service cost and given to a named holder with books, rent becomes a lever that runs straight to the
top tenth's third. The player can see it, and can break it from the tenants' side. The Michigan
clocks then do the dramatic work the Director asked for without any shortening. They are fast for
tenants, slow for owners, and visible at every stage. The settler level of the design comes from one
comparison, not from a class line: a household's stake against the offer. That comparison lets the
game say what MIM says. Ownership buys a household into the order. Equity deepens the purchase.
Bargains with owners last only as long as they pay. Owners who lose everything withdraw rather than
rise unless someone reaches them.

There are two risks to name plainly. If landlords carry no debt at the opening, a rent strike can
only bite through tax, which works on a three-year clock, and the ladder's middle rungs go slack. If
households carry no nation, the game cannot show MIM's first sorter. White householders in Wayne own
at about 77% and Black householders at about 47% (project table, labelled 2023, vintage
unconfirmed). Without nation, the organizer's base and the opposing owners' bodies blur into one
population.

## Questions only the owner can answer

These are ordered by how much each one changes play.

**1. What is a tenant's rent made of?** (a) Keep HH: rent is the engine's posted price of Housing
provision, one seller, one price. Play stays simple. There is one opponent, and rent moves only with
the trade's capacity, so landlords cannot be fought building by building. (b) Split rent into a
service cost plus the holder's take, set per holding by rules 1-2, opening near census rent (about
$1,081 a period in Wayne, arithmetic from 2024). Landlords become actors with prices and weak
points, and rent income feeds the thirds. This needs an explicit amendment of HH 7.8 and of ADR313
call 6's interim line, and ADR312's "one price for all" would apply within each holding rather than
across the county. (c) Adopt SPIKE R3a. Owners would pay rent to themselves, which contradicts HH
7.8. This report recommends (b).

**2. Do households carry nation?** (a) No, as in HH's current non-goal. Tenure alone sorts
households, and MIM's line can be shown only through bands. (b) Yes, from the census tenure-by-race
tables, applied once at the opening. Who owns and who is evicted then follows nation. The weighing
would show thin equity among oppressed-nation owners as fragile (MIM Notes 112), and the player's
base and the owners' bodies would become distinct. The vintage of the project table must be
confirmed in the 2024 capture.

**3. Who is a tenant's landlord?** (a) The property company manages every rented home, as in HH's
overrulable Call. There is one target, and direct holders receive passive income. (b) Holders let
their own homes, or hire the company for its 10% part. That gives two behaviors (rules 2 and 6),
many small targets, and a Detroit-like field in which most landlords own one or two properties.

**4. Do let homes open with mortgages?** (a) No, as in HH 7.15. Strikes then bite only through tax
and cash, and the lender never enters a rent fight. (b) Yes, as existing mortgages on a share of let
homes (about four in ten rental properties carry one nationally; the year conflicts). The lender,
forbearance, receivers and portfolio strikes become live. This fits "Existing mortgages only" if the
Director reads it as covering let homes.

**5. Does a home's value move?** (a) Carrying value, as in HH. Equity grows only by paying and is
lost only by arrears or foreclosure. Play is steady and legible. (b) Capitalised value, from the
place's own rents and the bank's rate (Marx, ch. 37). Equity rises and falls with booms, busts and
rates. That brings MIM's "watching the price go up" and Ansell's measured price effects into play,
along with more drama and more volatility. It revisits HH's anti-goal.

**6. How fast does equity build?** (a) HH's straight-line schedule over 196 periods: fast and
visible, 26.5% after 52 periods for a zero-equity owner. (b) A real 30-year annuity: slow, about
1-2% a year early on, so movement within a run would come mostly from arrears and loss.

**7. May the player's organization hold homes?** (a) No. The organization fights for tenants but
never becomes their landlord. (b) Yes, at the county sale or by taking over a failed holding. It is
then read as a landlord by the game's own rule, which plays out MIM's "piece of the pie" warning and
UTCA's history on the player's own books.

**8. May a lender foreclose on a household's home?** (a) No, as in HH, so a missed mortgage is only
debt and a fee. (b) Yes, under Michigan's notice, sale and redemption, with "leave at once" when
title vests. This was left standing by ADJ item 11 for households. Choosing (b) gives the bank a
direct hand in the settler stake.

**9. Does the County Review get a tenant road?** (a) No. Relief moves toward owners by tax, as the
Director ruled, and tenants fight landlords directly. (b) Yes, as an added rent-relief claim
competing for the same fixed pot. That sets tenants and owners against each other in the session,
which is the county's real politics.

**10. Is the eviction clock the law's stages or HH's two periods?** (a) HH's Designed two-period
clock. (b) The statute's stages, which fit two periods at the fastest lawful pace but give the
player a point to intervene at each stage. The Director's rule against Designed shortcuts where a
statute gives the figure points to (b).
