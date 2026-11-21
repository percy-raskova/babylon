# Homes, rent and nation: design

Date: 21 November 2026. Issue: PER-371, with PER-369 (households and homes). Status: approved by
the Director on 21 November 2026 ("Approve"), after one check by a second reader against the
approved designs and the engine. Decision record: ADR315.

## 1. What was asked

The Director, on 21 November 2026, when asked how heavy rent should be:

> do some deep research into how landlords handle market pricing and how rental markets work and
> make it an engaging gameplay dynamic that leaves room for political struggle as a gameplay option

And, the same day:

> the equity building properties of paying a mortgage for homeowners are also somethign that will
> lead to their class dyanmics and outlook and alignment, it is the level of settler colonialism
>
> the players political organizing and decisions can also lead to crises for example if there is a
> call for a general strike, a union organizing effort, a tenant rent strike, a mass protest that
> disrupts commerce and roads, etc
>
> nation should be a hypergraph, and in the ~/projects/ directory I'm pretty sure we made a
> hypergraph library in rust that we ported from xgi in python, purely for this purpose

The research was done (fourteen sets of notes and one report; section 3). Six answers followed:

| Asked | Answered |
| --- | --- |
| What a tenant's rent is made of | Split it: the upkeep of the home and the holder's take. Landlords get books |
| Do households carry nation | Yes, everywhere, as a hypergraph |
| How nation acts in play | By the make-up of places, as named policy of institutions |
| Does the value of a home move | Values move |
| A tenant claim at the County Review | Yes |
| Where homes exist | Everywhere, finer in Wayne |

This design carries them out. It stands on two approved designs: households and homes (20 November)
and how the economy adjusts (ADR314). It changes the first in the places listed in section 5.

## 2. What the player sees

Rent has an author. Every rented home belongs to a holding with a name, cash, taxes and debts, and
the player can read where it is weak.

```text
HOLDING   Linwood Avenue, 48 homes          Holder: a property company
Let 43    Empty 5    Asking rent $1,060     Certificate: none

Collected this period        $41,200
  debt service (its bank)    $19,800
  property tax owed          $ 6,900        on the county's clock: no
  upkeep                     $ 9,400        skipped last period: $2,100
  the holder's take          $ 5,100
Cash $22,000                  2 periods left if 6 more homes stop paying
```

A sketch of play, not a measurement:

```text
Period 1    A committee forms on Linwood. It learns the rent roll: the holding owes its bank.
Period 3    The homes break the code. Rent goes into escrow; the holding's cash falls.
Period 5    31 of 43 households withhold rent into a fund. The holding files against all.
Period 7    The holding misses its debt payment. Its bank's clock starts.
Period 8    Two households are removed. Four pay the judgment and leave the strike. The holder
            offers a rent cut and repairs: giving way costs it less than losing the building.
Period 9    Settled. The committee, its members and what is left of the fund remain.
```

On the owners' side: homes in a suburb gain value while money is cheap; owners there borrow against
the gain, and some buy a second home to let. Their stake has grown, and a tenants' fight next door
now has to offer them more than it puts at risk, so they stand against it. In the bust, values
fall, some owe more than the home is worth, and those are the owners an organizer can reach.

And by nation: each nation's own view of the county shows what is happening to its members, home
by home and job by job, and the named policies that treat one neighbourhood unlike another.

## 3. Today, and what the research found

Today the engine has housing only as one service with one posted price ($1,450) and one need for
each household. There is no rent, landlord, tenure, mortgage, home or eviction in the code. The
homes design is approved and not built. The game's graph already has hyperedges whose members
carry their own fields (Amendment AG), stored in the project's hypergraph library; the country's
scenario writes none for nations yet.

The research (one report, `reports/housing-research-2026-11-21/`, from fourteen sets of notes):

- **How landlords price.** From their own empty homes and habits, not by formula. Large owners
  reprice often and accept more empty homes for a higher rent. Small owners hold the rent for a
  tenant they trust and catch up when the home turns over.
- **How the market moves.** Rents follow empty homes slowly: about a fifth of the gap closes in a
  year. Over ten years rents follow local jobs almost one for one, while people barely leave after
  job losses.
- **The landlord's weak point.** A lender sizes a loan so that rent covers costs and debt with a
  quarter to spare. So a holding with debt cannot pay both once about one rent in eight is unpaid
  (the readers' arithmetic). Under pressure a landlord skips repairs first, then taxes, the lender
  last. It walks away when what is owed on a building exceeds its value.
- **Eviction is a way to collect.** Large owners file as soon as a tenant is behind. About a third
  of Detroit filings became an order in 2019, and far fewer a removal.
- **Detroit.** Rented homes are scarce while one home in five stands empty, most of them off the
  market. Seven landlords in ten own one or two properties. About one small rental in seven holds
  the city's certificate. Tax foreclosure took one property in four in 2011 to 2015, and investors
  bought nine in ten at the county's sale.
- **Michigan's clocks.** About two periods from a demand to an eviction order; a mortgage sale and
  then six months to buy the home back; three years for unpaid property tax.
- **Equity and outlook, measured.** In a survey of 29 countries, strong support for redistribution
  was 34% among owners who owed more than the home was worth, 30% among renters and 21% among
  owners with much equity. Losing a home brought withdrawal from politics, not revolt.
- **The line.** MIM: "You can't be a settler without a house", and net worth, home equity counted,
  marks class. Neither MIM nor Sakai describes equity as a quantity that grows and moves a
  household over time; that step is the Director's, and the measurements support its direction.

## 4. The rules

Rules are numbered H1 to H22. Every figure named as "a policy row" is a number in the scenario
file from a public source. The law's own figures live in one record for each state and are never
shortened. No outcome is decided by dice or by a curve drawn in advance, no rule draws a line
between owners by the amount of their equity, and no rule reads one household's nation.

Homes, holdings, mortgages and values exist in every place. Outside Wayne they are pooled: tenant
and owner groups in each band, and one holding for each kind of holder. In Wayne the household
units and the holdings are kept one by one.

### Part one: nation

**H1. A nation is a hyperedge.** Each nation named by the national question ruling (ADR171: Black,
Chicano, Indigenous) is one hyperedge of the game's graph. A household group is a member of it,
and the membership carries how many of the group's households belong. No group is split by nation.
A household may belong to more than one; counts add up as the census publishes them, and the
overlap is shown, never netted. The memberships are written once, at the opening, from the census.
They belong to people: when households move to another place, their memberships move with them.

**H2. Nation works through who has what, and through how places are treated.** At the opening the
census sorts, by nation, who owns and who rents, what a home is worth and what is owed on it, and
which band a household earns in; that is written into the groups and their memberships. In play,
every rule below is the same for every household. What a nation's members live through is read
from the groups they belong to: each nation's hyperedge shows its evictions, foreclosures, layoffs
and equity. Where a public record shows it, an institution's rule depends on the make-up of the
place or group it deals with: a bank's bound on home loans falls with the share of an oppressed
nation's households in a place (the federal mortgage record); a county taxes its cheapest homes
above their worth (Detroit's record). Each is a named policy row the player can see and politics
can change.

### Part two: homes, holders and rent

**H3. A home and its state.** A home is lived in by its owner, let, empty for rent, empty and off
the market, or held by the county. An owner pays no rent. It buys the upkeep of its own home and
pays its tax and its mortgage.

**H4. A holding.** A holding is one holder's rented homes in one place, with its own books: cash,
the rent it is owed, upkeep owed, tax owed and debt. At the opening every rented home belongs to
the top tenth, part through the property company and part held directly, as ruled. A holder lets
its own homes or hires the company for a share of the rent. Whoever buys a home to let later holds
a holding, and is read as a landlord from that, never by a label.

**H5. Rent is the upkeep and the holder's take.** The holder buys the upkeep of its homes from the
housing trade. The tenant pays rent to the holder. What is left after upkeep is the holder's take;
out of it the holder pays tax and debt and keeps the rest. Rent opens at what the census reports
for the place.

**H6. Asking rent.** Each holding posts an asking rent for its empty homes. It falls one step after
a period in which a home stood empty throughout. It rises one step after a period in which the
holding turned away a seeker it could not house. It never falls below the upkeep and the tax of a
let home.

**H7. Sitting rent.** A tenancy is a standing agreement at its own rent. The company moves a
tenancy to the asking rent once a year, a thirteenth of its tenancies each period. A holder that
lets its own homes keeps the rent until the tenant leaves; the next tenant pays the asking rent.

**H8. Empty homes and seekers.** A household without a home takes the cheapest empty home whose
rent its money covers for two periods. A home whose owed upkeep exceeds its value is unfit and
leaves the market.

**H9. A holding's books, and its retreat.** Rent collected pays first whatever would cost the
holding soonest under a clock, then debt, then tax, then upkeep, then the holder. A holding short
of money skips upkeep first, then tax, which starts the law's tax clock, then debt, which brings in
its lender. A holder walks away from a holding when what is owed on it exceeds its value: it stops
paying tax and upkeep and goes on collecting rent, until the title passes by the law's own clock.

**H10. A tenant behind on rent.** The company files against a tenant in the period it falls behind:
a filing costs it less than a period's rent and works as collection. A holder that lets its own
homes files only when the arrears exceed what an eviction would cost it in fees and lost rent.

### Part three: losing a home

**H11. The law's stages.** A home is lost by the law's own steps, counted in days inside the
periods and never shortened. Each step is a moment where something can stop it.

- A tenant behind on rent: a demand of seven days, a filing, a hearing, a judgment, at least ten
  days, an order, removal. Paying the judgment and costs before the order ends it. Rent paid into
  escrow where the home breaks the code is a defence. A tenant who complained cannot be put out
  for complaining for 90 days; that does not shield a tenant who is behind.
- An owner behind on tax: the county's clock of the homes design, three years in all.
- An owner behind on a mortgage: four weeks of notice, a sale, then six months to buy the home
  back (a year where less than two thirds is still owed, 30 days if the home is abandoned). The
  owner leaves at once when the title passes. What a sale brings above the debt is the owner's.
- A holding behind on its debt: the property company's holdings follow the rule for a business
  (ADR314 A11, three periods); a holding in a household's hands follows the mortgage steps above.
  Meanwhile the lender may put in a receiver, who collects and evicts and has no money for repairs.
- Whether a holding without the city's certificate can win rent in court is a policy row: it
  opens as the courts apply it today and is something to fight over.

**H12. Removal needs hands.** An order is carried out by the court's officers, with the hours the
court has, the orders served in order of their dates. People present in greater number of hours
than the officers bring stop a removal for the day. An order not carried out in its time lapses
and must be asked for again. The court's hours are part of the opponent's capacity, built with it.

### Part four: mortgages, values and equity

**H13. Mortgages are loans from banks.** They are paid down as real loans are, slowly at first. At
the opening, owners of the upper bands hold loans of their real ages, and bottom-half owners owe
what the home is worth, as ruled. Banks make new loans to buyers, bounded by the buyer's income and
the home's value, by policy rows from the lenders' own standards and by the policy of H2. A rented
home may carry a mortgage; about four rental properties in ten do.

**H14. The value of a home moves.** The homes of a place have a posted value. At the opening it is
the census value, which fixes the place's number of years' rent that a home is worth. From then on
the value moves one step a period toward that number of years of what a home now earns (its rent
less upkeep and tax), raised or lowered as the going rate on mortgages has fallen or risen since
the opening. A home that earns nothing is worth nothing. Homes are bought and sold at the posted
value; the county's sale keeps the homes design's rule.

**H15. Equity.** Equity is the home's value less everything owed on it. It grows as the mortgage is
paid and as the value rises. An owner can borrow against it from a bank. It is lost through
arrears, through a fall in value, and through foreclosure.

**H16. The stake, and the weighing.** An owner household's stake is its equity, a year of the rent
it does not pay, and the relief its rank at the county would win in a year. A household joins an
action when what the action offers it within a year is more than what joining puts within reach of
the law's steps in that year, both in its own dollars. A household with a larger stake needs a
larger offer; nothing happens at any fixed amount. Households of one group differ by the age of
their loans, so they come in a few at a time. An owner whose stake rose this period leans toward
the order that protects it and one whose stake fell leans away; the player sees how many are
rising, level and falling, and the game's rules of outlook read that count when they are joined.

### Part five: the county and the places of struggle

**H17. A tenant claim at the County Review.** A tenant household behind on rent can ask the county
for rent relief, from the same fixed pot as every other claim, ranked as the Review ranks. So
tenants stand below owners unless politics changes the ranking. Relief is paid against the arrears
to the holding, as rent relief is: it stops the eviction, and the money ends with the holder.

**H18. The places where organized people act.** This design builds the places; the player's verbs
come with the player's organization. Tenant bodies open where public records show them, which is
in few places. Each fight is decided by a race between two sets of accounts: how long the holding's
money lasts against how long the households can hold.

| Place | What it does to the holding |
| --- | --- |
| A committee in a holding | Nothing yet. Its members know the rent roll and the state of the homes |
| A complaint | Exposes a holding without a certificate; protects those who complained |
| Escrow | Rent is held back, not lost; the holding's cash falls, its debt does not |
| A rent strike | Rent is withheld into a fund; with debt, the holding breaks at about one rent in eight |
| Defense on the day | A removal fails for the day; an order lapses in time |
| A strike across one holder's holdings | Hits the holder's whole income and its standing with its bank |
| The county's sale | The organization buys with its own money, ahead of those who buy to let |
| Taking over a holding | The holder or its bank sells; whoever holds it then is read as a landlord |

**H19. How the other side answers.** By rule, from its own accounts. A holding files against every
striker. It offers a settlement when giving way costs it less, over a year, than the rent it will
lose before it can remove them. Its lender acts as H11 says. The court moves by the law's stages,
and its officers come with the hours they have.

**H20. Owners act too.** Owners whose stake is threatened in their place press the county, by the
same weighing. The body they form is built with the game's organizations; this design gives it
what it needs to count.

### Part six: what is shown and recorded

**H21. What the player is shown.** The holding's books, as in section 2; each household's place on
the law's stages with the next step and what would stop it; before any action, a forecast of the
race, made only from the figures the player has earned; for owners, the stake and how many
households a given offer would bring; for each nation, what is happening to its members and the
policies that treat places unlike. The structure is public. Figures are earned: a committee knows
its rent roll, a court filing shows arrears, the county's list names holders behind on tax.

**H22. Every act leaves a record.** A rent that moved, a filing, a judgment, a payment into escrow,
a strike and how it ended, a removal carried out or stopped, a holding in the hands of a receiver,
a home taken, a home sold, a value that stepped: each is a record naming its holding and its
cause, carried with the records of ADR314.

## 5. What changes in the approved designs

| Where | Was | Becomes |
| --- | --- | --- |
| Homes design, non-goals | No unit carries nation; no homes outside Wayne; no landlord's own choices; no foreclosure by a lender | Nation as hyperedges (H1); homes everywhere, pooled outside Wayne; holdings set rent (H6); a lender forecloses (H11) |
| Homes design 7.7 | The property company manages every rented home | A holder lets its own homes or hires the company (H4) |
| Homes design 7.8 | Rent is the posted price of housing; an owner buys no housing | Rent is upkeep and the holder's take, set by each holding; an owner buys upkeep (H3, H5) |
| Homes design 7.9, 7.14 | A home is carried at what was paid; equity is shown and no rule reads it or a nation | Values move (H14); equity is weighed (H16); nation is read by H2's policies only |
| Homes design 7.9, 7.15 and ruling 10 | A straight-line schedule; a stand-in lender; existing mortgages only; let homes carry none | Real loans from banks, new ones too (ADR314 A9); let homes may carry one (H13) |
| Homes design 7.10 | A household pays first what would cost it its home this period | The same; a holding gets its own order of paying (H9) |
| Homes design 7.11 | A tenancy ends after two periods of arrears | The law's stages (H11) |
| Homes design 7.12 | The County Review has claims for owners | A tenant claim is added (H17) |
| Homes design 7.16 | Nation shown as an observed table, pending | Nation as hyperedges with memberships (H1, H2) |
| ADR312 P1, P3 | One price for every buyer of a market | Holds for empty homes at the asking rent; a tenancy keeps its own rent (H7) |
| ADR313, call 6 | Owners' rent is left out; every household buys housing | Tenants pay observed rent; owners buy upkeep; the opening's balances are recomputed |
| ADR313, rule O17 | Three earning accounts in every county | Tenant and owner groups in each band in every county |

Everything else in the homes design stands: an owner is one kind; every rented home opens in the
top tenth; bottom-half owners open with no equity; the tax clock; the county's sale; people who
lose a home leave at once.

## 6. What it does not do

- The player's verbs. The places of H18 are built; the player's organization comes with its own
  design.
- Rent control and other new laws. Michigan bars local rent control; changing the law is politics,
  with a later design.
- Public and social housing, and land held in common. The county's stock of homes is kept, as in
  the homes design.
- Land outside homes: farmland, mineral land and commercial land come with the land foundation.
- The national question's own play (ADR171): this design writes the memberships and the policies
  of H2, and no more.
- Insurance, water bills on the tax roll, and land contracts: later, with the same debt record.

## 7. What would make it a failure

- Rent as weather: a number with no author.
- A fight whose end the player cannot read from the two sets of accounts.
- A line between owners drawn by the amount of their equity.
- Nation as a label that decides an outcome by itself.
- A law's time limit shortened to make a run more lively.
- A recurring bill with one right answer every period.

## 8. Approaches

1. **Holdings with books, and the law's stages.** Chosen. It gives rent an author and every fight
   a target, and it lets Detroit's own loop of milking, tax foreclosure and buying to let arise
   from the rules.
2. **One price for housing in each place.** Rejected by the Director: landlords could not be
   fought building by building.
3. **Rent that every household pays, owners to themselves.** Rejected: it contradicts the homes
   design and still gives rent no author.
4. **Household groups split by nation.** Rejected by the Director: nation is a hypergraph. A split
   would also have multiplied the country's accounts and netted the overlap that the national
   question ruling says to show.

## 9. How we know it works

On the small test economy, with two holdings (one with debt, one without), twenty tenant
households, owners with loans of different ages, a bank, and two places of unlike make-up, each
run for 400 periods and checked by a second reader against the rows:

- **Still when quiet.** With homes, holdings and values, the balanced world does not move.
- **Empty homes lower the rent.** After households leave, the asking rent steps down and the
  holding with debt is squeezed; rents do not fall below upkeep and tax.
- **The race is decided by accounts.** The same strike is won against the holding with debt and
  lost against the one without; the forecast, made only from earned figures, matches what happens
  when nobody changes course.
- **Detroit's loop.** With cheap homes and a long tax clock, a holder skips upkeep and tax, goes
  on collecting, and loses the home to the county, without any rule that says so.
- **Values swing.** Cheap money raises values and equity; a bust leaves some owners owing more
  than the home is worth.
- **The stake moves households, one by one.** As an offer rises, owners join a few at a time, and
  the count changes as equity grows. A fixed cut-off put in on purpose must make this test fail.
- **Nation decides nothing by itself.** With every policy of H2 set equal, exchanging the
  memberships of two groups that have the same figures changes no outcome. With the policies on,
  the two places come apart, and each difference is traced to a named policy.
- **Nation adds up.** Each nation's counts match the census as published, overlap shown.
- **The law's limits.** In the records, every stage lasts at least the law's minimum.
- **A real choice.** Paying, falling behind, escrow and striking end differently for the same
  household, and none is best in every state of the accounts.
- **Every rent change has a record** naming its holding and its cause.
- **Exact money.** Every dollar is a transfer between two accounts, in every period.
- **Size and speed.** The country's counts with tenure in every place are pinned, and a period is
  timed against today's, before the opening is built on it.

## 10. Calls made here, for the Director to check

1. An owner buys the upkeep of its own home, so the housing trade keeps its customers.
2. Out of its take a holder pays its tax and its debt.
3. The asking rent never falls below upkeep and tax; debt is left out of that floor.
4. Rented homes may open with mortgages, about four properties in ten.
5. A lender may foreclose on a household's home, by Michigan's process.
6. Equity builds as on a real loan; upper-band loans open at their real ages, bottom-half loans
   open new.
7. A home's value moves by steps from the census value, with rents and with the going rate.
8. The eviction clock is the law's stages, counted in days and never shortened.
9. Removals are carried out by the court's officers, as in Detroit, not by the city's police; their
   hours belong to the opponent's capacity.
10. Whether a holding without a certificate can win in court is policy, open to struggle.
11. Rent relief is paid to the holding against the arrears, as real rent relief is.
12. Tenant bodies open only where public records show them.
13. The year is the horizon of the weighing, of a holding in a strike and of an employer in a
    stoppage (ADR314 A16).
14. The lean of owners is shown and counted; what it does to outlook belongs to the game's rules
    of outlook.
15. The policies of H2 at the opening are two: home loans by the make-up of a place, and the
    taxing of cheap homes above their worth. Others are added only with their public record.
16. The player's organization may come to hold homes, and is then read as a landlord.
17. Tenure about doubles the household accounts. The live country is small (187 places with a
    handful of groups in each), so no size limit of the engine is expected to be met. Corrected on
    21 November: an earlier figure of some 15,000 accounts was from before the counties were
    folded into places.
18. Tenure, income and rent by nation and county come from the project's own reference database
    (its latest year is 2023; its shares are applied to the 2024 totals, and the table's record
    says so). The census tables it lacks are fetched only when the rule that needs them is built:
    tenure by income, home value, mortgage status, year moved in, empty homes by kind, rented homes
    by size of building. Where the census does not cross nation, tenure and income, the cross is
    filled from the published margins by a declared rule. Lending comes from the federal mortgage
    record, and the law's figures by state.
19. A nation's members are the household nodes the game's graph already has, and every group is a
    member from the opening, with a count that may be zero.
20. The count lives on the membership itself. The engine does not serve that yet (issue 653); this
    build serves it, and the hypergraph library gets the two fixes it needs, in the library, as the
    Director ruled.
21. A group's nation counts rise and fall in proportion with the group, as its households are
    born, die and move, by largest remainder.
22. Chicano households are counted by the census's Hispanic origin, as the project's ruling on the
    national question already does, with its disclosure.
23. Within a band, jobs are dealt by pay as between bands: the owner group first.

## 11. Build order

1. **Tenure in the accounts**: tenant and owner groups in each band in every place, with the two
   held tasks of the twelve trades plan, and a test of size and speed.
2. **Nation written as hyperedges** (H1) from the census, with what each nation is shown.
3. **Homes, holdings and rent** (H3 to H10).
4. **Losing a home** (H11, H12) and **the County Review's tenant claim** (H17).
5. **Mortgages, values and equity** (H13 to H16) and **the policies of H2**, after the banks of
   ADR314.
6. **The places of struggle** (H18 to H20), with what is shown (H21).

Records (H22) are carried with those of ADR314. The opening is rebuilt (stage 5 of ADR313) after
this design and ADR314 are built, so that it is built once.
