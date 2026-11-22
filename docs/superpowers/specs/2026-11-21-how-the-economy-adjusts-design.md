# How the economy adjusts: design

Date: 21 November 2026. Issue: PER-371. Status: approved by the Director on 21 November 2026
("Approve: plan and build"), after one check by a second reader against the engine. Decision
record: ADR314.

## 1. What was asked

Three rounds of measurement on the small test economy (21 November 2026, section 3) showed that the
engine never recovers from a shock and that no single rule cures it. The Director then asked for
every open question at once, with this steer:

> ask me all the questions you need answers from me on and lets keep in mind that we're making a
> game so we want to orient all this design towards dynamic, emergent, engaging, and invigorating
> gameplay

Twenty answers followed in five rounds of the question dialog. This design carries them out.

| Asked | Answered |
| --- | --- |
| Design how the economy adjusts now, before the opening? | Design it now, as one thing, proven on the small test economy first |
| After a shock | Cycles that leave scars: slumps end by themselves, at about the pace of real ones, through layoffs, pay cuts, bankruptcies and buyouts |
| Pay | Both ways, fought over |
| Prices or jobs in a slump | Depends on the trade: raw goods and energy swing in price, factories and services cut jobs |
| People | Change jobs, move slowly between places; the benefit moves with them |
| Companies shifting work | Yes, borders included now |
| What brings work back after a closure | A buyer; a public body; its workers; new workplaces founded (all four) |
| Rent | "do some deep research into how landlords handle market pricing and how rental markets work and make it an engaging gameplay dynamic that leaves room for political struggle as a gameplay option" |
| Banks | Banks create money |
| Who can borrow | Businesses to keep running; businesses to grow; households; public bodies (all four) |
| A business that cannot pay | The lender takes it |
| The state in a crash | "The government should default to rescuing the big companies but this itself is another opportunity for interesting gameplay and political struggle" |
| What holds work in the core | The kind of work |
| Who can found a workplace | Companies and big owners; middle households; public bodies; workers and organizations (all four) |
| Who resists a pay cut at the opening | Today's unions, from data |
| A failed bank | As in today's law |
| What sets the economy moving | Its own tendencies; events from the world's state; a calendar of world events; shocks drawn from the campaign's seed; and "the players political organizing and decisions can also lead to crises for example if there is a call for a general strike, a union organizing effort, a tenant rent strike, a mass protest that disrupts commerce and roads, etc" |
| Which regions are core | Core, rivals and periphery, "but also australia, new zealand are imperialist core. and then there are comprador states like kingdom of saudi arabia, bahrain, taiwan is interesting dynamic with china, ukraine and its war deserves ongoing consideration, also comprador states like el salvador" |
| What keeps machine work in the core | Machine-making stays |
| The rescue's terms at the start | "i say by default 1, but through political struggle if the player goes the DSA/electoral/new deal route they could get number 2" (1: as in 2008; 2: the state takes a stake) |

The Director also added: "the equity building properties of paying a mortgage for homeowners are
also somethign that will lead to their class dyanmics and outlook and alignment, it is the level of
settler colonialism". Rent, homes and equity get their own design, after the research the Director
asked for. This design builds what that one will stand on (debt, banks, people who move) and names
where the two join (rules A11 and A21).

This design takes the place of step 3 of the order agreed on 20 November ("capital for expansion,
with debt and bank credit") and brings forward the heart of step 4 ("trade by kind of product, with
different techniques in core and periphery"), because the Director chose that companies move work
across borders from the start.

## 2. What the player sees

The economy becomes weather with causes. It moves without the player, each slump leaves the county
changed, and every turn of it is an event the player can trace to its cause and act on.

A sketch of play, not a measurement:

```text
Year 1  A poor harvest. Food is dearer by a seventh within three months.
        Wayne households buy less of everything else. Two parts makers lay off.
Year 2  One in ten in Wayne is looking for work. The axle plant, losing money, cuts pay.
        Nobody is organized there: the cut sticks. At the stamping plant the union stops
        work for three weeks and the cut is withdrawn.
        A parts maker misses three payments. Its bank takes it and sells it to a rival.
        The bank's losses mount. Big depositors pull out. Washington lends to the bank.
        Nothing is lent to the households who owe it money.
Year 3  Food is back near its old price. Pay is lower, machines are cheap, money is cheap.
        The rival restarts the parts maker with fewer people. A carmaker puts its new line
        in a low-pay region abroad. Some who are looking for work leave Wayne.
Year 5  Output is back. Fewer owners hold more. The east-side plant never reopened.
```

What the player can see at any time: prices and pay by trade and place, who is looking for work,
each workplace's owner, cash, debts and state (running, on strike, shut), each bank's health, and
the news of the period with the cause of each item.

Where the player's organization will later act. This design builds the places, not the player's
verbs: a pay cut and the stoppage that answers it; the body of people looking for work in a place;
a shut plant that stays on the map; a debt and the lender who holds it; a rescue and its terms; a
public body's budget when lenders refuse it. It also makes the economy take what organized people
do to it: hours withheld, payments withheld and routes blocked are pushes like any other (A22).

## 3. Today

Measured on the small test economy (four workplaces, 40 people; the records of rounds one to three
are under `reports/economy-repair-2026-11-20/restoring-forces/`):

- Left alone it is exactly still. Pushed once, every run ends in ruin within 200 periods, at the
  small world's figures and at the country's.
- Twelve rules were tried alone and seventeen sets together. A push on the side of demand (a pay
  rise, a tax cut) can be cured. A push that takes something real away (a poor harvest, scarce
  power) cannot.
- The one rule that helped in every round: a workplace with spare money plans for what was asked of
  it, not only for what was paid for (rule A6 here).

Why, in the code:

- A goods price is judged after the seller has restocked, so a seller that refills to its target
  can only hold or raise it. It stays silent while its own stock drains. A service's price is cut
  whenever it works under its full capacity, which in a slump is always.
- Every plan is made from the period that just closed. A supplier is one period behind its buyers.
- A buyer is bound to one named seller. A second seller of the same product would get no buyers.
- A workplace's workforce can only shrink. None is ever created or retired. One with no cash has no
  way back.
- A person is tied for life to one workplace.
- Nothing can be owed. Money is a fixed total. Idle cash cannot reach a workplace that needs it.
- Pay never changes.

## 4. The rules

Rules are numbered A1 to A23. Where a rule changes an earlier one, it says so. Every figure named
as "a policy row" is a number in the scenario file, set coarsely from public data and proven on the
test economy; none is tuned toward a wished result. No outcome is decided by dice or by a curve
drawn in advance: accounts, steps and rank order under a budget decide.

### Part one: prices, buyers and plans

**A1. One test for every price: the seller's buffer and what was sold.** A price steps up when
buyers were turned away or priced out, when the seller's stock stands under its buffer, or when its
cost has risen above the price. It steps down when goods or hours it offered beyond its buffer went
unsold and nobody was turned away. Capacity it did not plan to use is no reason to move a price.
This replaces two rules of today: the cut of a service's price for running under its full capacity,
and the goods price that waits until stock is gone.

**A2. Raw goods and energy swing.** Food at the farm, materials, fuel and power move in large
steps. After a short market the next period opens at the price where the market closed. When what
was offered goes unsold, the price falls a large step, never below the seller's direct cost. This
changes the one-step rule of the price of a short market (ADR312) for these products only.

**A3. Made goods and services hold their price and cut work first.** A factory, a shop or a service
moves its price one small step at a time by the test of A1. In a short market the price still rises
within the period, as ruled (ADR312). So when sales fall, it lays off before it cuts its price, and
a price that went up in a shortage comes down slowly.

**A4. A buyer takes from the cheapest seller it can reach.** No buyer is bound to one seller. It
buys from the cheapest seller of the product within its reach first, its own place before others,
with freight added for the others; equal prices share buyers in proportion. This is what lets a
second workplace, a new one or work abroad win buyers, and what makes a seller that holds its price
lose them. It changes rule P1 of ADR312: a market is one product in one place, with all its
sellers.

**A5. Plans are made through the whole chain of supply.** At the close each workplace plans, places
its orders for the next period, and its suppliers take those orders into their own plans. This is
repeated a bounded number of times until the plans rest, because recipes run in circles (power
needs fuel, and fuel needs power). The engine already carries orders for a later period and uses
none. This changes rule P14 of ADR312 for buyers that are businesses.

**A6. A workplace with spare money does not cut at once.** A workplace that holds more money than
one period of what it pays out plans for what was asked of it, not only for what was paid for, as
far as its spare money carries. One without spare money plans for what was paid for. Measured as
the one rule that helped in every round. What gives a sound workplace that money is a loan that
stands for its term (A10) or its owner's own money (A19). A loan repaid at the close of the period
it was drawn in leaves none, as round 7b measured.

### Part two: money, banks and debt

**A7. Banks.** A bank is a business that keeps accounts' money and lends. Every account keeps its
money at one bank. A bank has its own capital, holds reserves of base money, and has owners, costs
and profit like any business. Banks are few: a handful of national ones and one local bank for each
place, sized from public figures.

**A8. A loan is new money.** When a bank lends, the borrower's account grows and a debt is written
down. When principal is repaid, that money is gone again. Interest is paid to the bank. Interest
not paid is a claim, not money. A debt written off comes out of the bank's capital. At every moment
the money in all accounts, the banks' own capital included, equals base money plus the principal
outstanding, to the cent. Base money changes only by a recorded act of the federal level (A13).

**A9. Four kinds of borrower, one kind of debt.** One record serves all: who owes, to whom, how
much, at what rate, for what, what is pledged, and when it falls due.

- A business, to keep running. At the opening of a period, before wages, a business short of money
  for its planned wages and supplies draws on its bank, when what the loan pays for will sell above
  its cost and the interest. It repays from its sales at the close, before any profit is paid out.
- A business, to grow. For machines, for a new workplace, for buying another business. What was
  bought is pledged.
- A household. For needs in a period when its money is short. Repayment comes after needs and
  before comforts.
- A public body. When its taxes fall short of its budget. When lenders refuse, its budget is cut in
  proportion, as built.

Existing mortgages are held by banks once banks exist, in place of the stand-in lender of the homes
design. New mortgages come with the housing design.

**A10. How much a bank lends, and at what rate.** A bank lends up to a multiple of its own capital,
the law's figure. Each loan is also bounded by the borrower's own books: a loan to grow by the price
of the thing bought, a household's by its income, a public body's by its taxes. A loan to keep
running is not bounded by the borrower's last sales (ruled on 22 November 2026, ADR318): the bank's
test (A9) and the bank's own bound hold it. Every such loan has a term and falls due at its end; the
length of the term is a policy row, set by measurement. These bounds, and a legal highest rate, are
policy rows. The rate is a price and follows the price rules: the bank posts it; when more is asked
than the bank can lend, it rises within the period until what borrowers will pay for fits; when room
to lend stands unused, it steps down, never below the bank's own cost. A borrower already deep in
debt pays a step more for each further share of its bound that it uses. A business borrows to grow
only below its own rate of profit, so the rate stays under the rate of profit, as ruled in July
2026.

**A11. Not paying.** What is not paid stays owed, in both books, and interest runs. What is unpaid
of a loan at its due date counts as not paying from that date, whatever smaller sums the borrower
pays (ADR318).

- A business that has paid nothing for three periods (about 90 days, the banks' own standard) is
  taken by its lender. The old owners' claims end, the debt is written down, and the business is
  put up for sale (A17). The bank bears the loss.
- A household: for a home, the homes design rules. For other debts the law's own process and clocks
  apply; they are set out with the housing design, together with the mortgage.
- A public body that cannot borrow cuts. What politics does with a broke city is a hook.

**A12. A failing bank.** A bank whose losses use up its capital fails, as in today's law. Deposits
up to the insured sum for each household are paid by a federal fund that banks pay into. Larger
deposits lose their share of what is missing. The bank's owners lose everything. Its sound loans
and its insured deposits pass to another bank. Depositors above the insured sum move their money
out of a bank whose capital has fallen under the legal minimum; a bank that runs out of reserves
must borrow them or fail: that is the run. When the fund runs short it draws on the federal budget,
and that is politics.

**A13. The rescue is a policy, and a fight.** At the opening the terms are those of 2008. The
federal level lends new base money to failing banks, whatever it takes, and to the largest
companies in order of size, as far as a voted sum goes. Their owners keep everything. Nothing is
asked on jobs, pay or lending. No household and no small business is lent to. Who is rescued, how
much, and on what terms are named policy that politics can change: the state taking a stake in what
it rescues is a term that an electoral, reforming route can win. Every rescue is an event the
player sees, with its sum and its terms.

### Part three: work and pay

**A14. People looking for work belong to their place.** Someone laid off looks for work at every
workplace of their place, not only at the one that let them go. A workplace that needs hands takes
them from the place's seekers; where several are hiring, the one that pays most is served first.
The layoff record and the benefit stay as built.

**A15. Pay moves by steps.**

- New hands are taken on at the going rate for seekers in the place. That rate falls one step when
  more people are looking for work than the period before, and rises one step when fewer are. A
  place where the number holds keeps its rate. (Capital I, chapter 25: the movements of wages
  follow the expansion and contraction of the reserve army.)
- A workplace that cannot fill its hours raises its pay one step, and a raise draws hands: seekers
  first, then people from the workplaces of the place that pay least.
- Cutting the pay of people already at work is an act. A workplace does it when it is losing money
  at its price and the place has seekers who could replace them. Where nobody is organized, the cut
  sticks.
- Nobody takes work for less than their benefit, or for less than the law's minimum wage.

**A16. Organized workers fight it.** Each trade in each place opens with its observed share of
union members. A union is an organization with a fund from dues. It answers a cut with a stoppage,
and asks for a rise where hands are short, when its fund would outlast the employer's money. In a
stoppage its members give no hours and draw strike pay; the employer loses output and may take on
seekers if there are any. The accounts end it as they change: the employer gives way when the
stoppage has cost it more than the cut would save in a year; the union gives way when its fund and
its members' money run out. A loan to the employer, hands that cross the line, or money sent to the
strikers can each turn it. These unions defend their own members' pay, not the class.

### Part four: workplaces and capital

**A17. A shut workplace stays on the map.** A workplace with no money and no credit stops. It keeps
its place, its name and its machines, which wear. Its people become seekers. It can come back in
three ways, and a fourth way brings new work (A18):

- A buyer. A company or an owner bids for it, at most what it would earn, valued at the going rate
  of interest. The buyer restarts it when its product sells above its cost at today's pay.
- A public body, by policy. Off at the opening.
- Its workers, who occupy it and run it. A place for the player's organization to act.

**A18. New workplaces are founded where buyers are.** In every place each trade has standing room
for new workplaces. One is started, or an existing one is added to, only as far as there are buyers
who could pay and went unserved, or buyers whom a cheaper seller would win. Founders:

- Companies and big owners, with their own money or a loan.
- Households of the next 40%, who put savings and a loan into a small business. The small
  businesses of one trade in one place are counted together, as pooled households are. One that
  fails sends its household back to wage work.
- Public bodies, by policy. Off at the opening.
- Workers and organizations, the player's included. A place for the player to act.

**A19. Capital goes where profit is.** A company or an owner puts earnings and credit into uses in
order of their rate of profit: adding to a workplace that sold out, buying a shut or failing one,
founding a new one, in any place, at home or abroad. The order and the budget decide. Nothing is
put where it would earn less than money costs. A workplace that earns less than its owner's other
uses gets no new machines and runs down. This ranking takes the place of the weighted draw in the
companies' script; the choice stays in the script.

An owner's own money follows the same order (ruled on 22 November 2026, ADR318). An owner puts
money into a workplace that is losing only while that workplace is the best use the owner has for
that money. A company has other uses, so it puts in nothing and cuts its losses: it sheds hands,
cuts pay, shuts the workplace or sells it. A household whose one small business is the only use it
has for its savings covers the loss from them until they are gone; then the business fails and the
household goes back to wage work (A18). No rule names the two kinds of owner: the difference
follows from what each has.

**A20. The kind of work holds the core.**

- Regions abroad are core (Canada, Japan, the European Union, the rest of Europe, and Australia
  with New Zealand), rivals (China and Russia) or periphery (the rest). The United States is core.
- Machines are made only in the core and by the rivals: their owners hold the know-how. Everyone
  else buys machines from them.
- Each trade can be worked two ways: with many machines and few hands, or with many hands and few
  machines. A workplace uses the cheaper way at its place's pay and the price of machines.
- Services are sold where they are worked and cannot leave. Every other goods trade may leave for
  low-pay regions, under core ownership, with the profit flowing home. Rivals take machine work
  too, at lower pay, and compete with the core.
- Distance costs freight, and nothing moves faster than plants are built.

So the core becomes owners, machine-makers and services, living on profit from abroad. Comprador
states (the Director names Saudi Arabia, Bahrain and El Salvador), Taiwan beside China, and
Ukraine's war need a finer map of states than the scenario's twelve regions; that map is later
work.

### Part five: people and places

**A21. People move toward work, slowly.** Someone looking for work may leave for another place:
those who have looked longest go first, to the nearest places first, and only as many as that place
has work for and, once homes are built, homes for. Their benefit moves with them, and so does their
share of their group's money and debts. Places that lose work empty; places that gain it fill up.

### Part six: what moves it, and what is recorded

**A22. What sets the economy moving.**

- Its own tendencies, always: capital leaving for low-pay regions, credit building up and breaking,
  machines wearing out, people born, dying and moving, unions pushing.
- Outside events, built as one kind of record that the scenario can fill three ways: fired when the
  world's state meets a condition; dated on a calendar in the scenario; or drawn once from the
  campaign's seed, so that the same seed replays the same history.
- What organized people do. A stoppage withholds hours, a rent or debt strike withholds payments, a
  blockade closes a route, a boycott withholds buying. The economy takes each as a push like any
  other, whoever starts it.

**A23. Every act leaves a record, and the records are carried once.** A price that moved and why, a
loan, a missed payment, a business taken and sold, a bank failed, a rescue, a pay cut, a stoppage
and how it ended, a workplace shut, bought, reopened or founded, people who left, an outside event:
each is a record the tick carries and the client shows as news with its cause. Each piece is built
behind a campaign setting, so shipped worlds keep their bytes until one change of the stored format
carries everything; the records plan (stage 4b) is widened for it.

## 5. What it does not do

- Rent, homes, mortgages and equity: their own design, after the research the Director asked for.
  Until then housing keeps today's price rule.
- Shares, bonds and land titles that are bought and sold: later, as agreed on 20 November.
- Exchange rates: there is one money for the whole world.
- A federal interest-rate policy: the federal level acts only in a rescue.
- A finer map of states abroad, tariffs, wars and other politics of trade: hooks only.
- The player's own verbs: the places to act are built; the verbs come with the player's
  organization.
- The content of outside events: the record and its three sources are built; the events are written
  later.
- New kinds of household: the three bands in every place stay; Wayne's household units come with
  PER-369.

## 6. What would make it a failure

- A stabilizer that hides the economy. It has to swing.
- Ruin as the only ending. A slump has to end by itself, changed.
- An economy that comes back exactly as it was. A slump has to leave marks.
- An outcome decided by dice or by a curve drawn in advance. Accounts decide.
- News the player cannot trace to a cause.
- A rescue that works silently.
- Rules that add motion of their own: the small test economy, balanced and with every source of
  motion switched off, must stay still.

## 7. Approaches

1. **One design, built in pieces, each proven on the test economy before the next.** Chosen. Three
   rounds showed that guessed cures fail and that no piece works alone, so each piece is measured
   on long runs before it becomes product code.
2. **Build everything, then measure the country.** Rejected: the country takes hours to run and
   hides causes that the small world shows in minutes.
3. **Add stabilizers until the collapse stops.** Rejected: the best pair cured only pushes on the
   side of demand and failed at the country's figures, and the Director asked for an economy that
   swings.

## 8. How we know it works

The small test economy grows with the pieces: a second seller of each product in piece 1; a bank in
piece 2; people looking for work at the opening, births and deaths in piece 3; a second place and
regions abroad in pieces 4 and 5. Every piece is first a throwaway prototype behind a switch,
measured for 400 periods at the small world's figures and at the country's, and checked by a second
reader against the rows. Then it is planned and built.

What each piece must show, on the rows of the last 20 periods and never on a short run:

- **Still when quiet.** The balanced world, with every source of motion off, does not move. The
  same holds with people looking for work, births and deaths at the opening, as the country has.
- **Back after a shock that ends.** A poor harvest of ten periods: work, output and needs met in
  each band are back to nineteen twentieths of the opening within five years (65 periods) and stay;
  prices settle.
- **Settled after a lasting loss.** A harvest poor for good, or scarce power: the economy rests near
  what the loss allows; no price climbs without end; nothing ends in ruin.
- **Marks.** After a slump something has changed hands, shut for good or moved, in at least the
  runs with banks.
- **A cycle with no outside push.** With banks and capital that moves: a boom on credit turns into
  a slump and the slump ends by itself. With the rescue switched off it is deeper.
- **Pay both ways.** Cuts happen, stoppages start and end on the accounts, and pay rises again when
  hands are short.
- **Sellers compete.** A cheaper seller wins buyers; a seller that holds its price loses them and
  then cuts.
- **News.** Every event in a run can be read from the records with its cause.
- **The pace.** A slump takes one to two years to its low and up to five back. The pace is a
  result; if it is far off, policy rows are changed once, within what public data allows, and the
  numbers are brought to the Director.
- **Exact money.** In every period, the money in all accounts equals base money plus principal.
- **The rate under the rate of profit.** Checked in every run.

**How these are judged (ruled on 22 November 2026, ADR319).** The Director: "not every shock is a
failure. capitalism is inherently unstable. what we want is to ensure the gameplay is interesting
and well paced". A round of measurement passes when three things hold at the small figures and at
the country's. A calm world stays still, with money and people exact. After the harvest that fails
for ten periods and returns, work and output are back within five years. After a loss that lasts, no
place is left without a product for good and no price climbs without end. Swings and cycles, what
shut, reopened or changed hands, who ends up poorer, and the pace are reported and not scored:
section 6 asks for an economy that swings and for slumps that leave marks. The pace named above
stays.

## 9. Calls made here, for the Director to check

1. Raw goods and energy move in large steps and open where the market closed; they are not sold by
   an auction downward, because buyers of raw goods do not buy more when the price falls.
2. A buyer takes from the cheapest seller it can reach. Without this no second seller would ever
   have a buyer.
3. A workplace with spare money plans for what was asked, as measured (A6).
4. Banks are few: national ones and one local bank for each place.
5. A loan's size is bounded by the borrower's own books, by policy rows; a borrower deep in debt
   pays more, by steps; there is a legal highest rate. Changed on 22 November 2026 for a loan to
   keep running: the bank's capital and its test bound it, and it has a term (ADR318).
6. A business is in default after three periods without payment.
7. The insured sum counts for each household of a pooled group.
8. Only a rescue creates base money. The deposit fund draws on the federal budget.
9. Existing mortgages are held by banks, not by the stand-in lender of the homes design.
10. Pay for new hands follows the change in the number looking for work, not the number itself.
11. A union stops work when its fund would outlast the employer's money; the accounts end it, with
    one year as the employer's horizon.
12. The small businesses of one trade in one place are counted together.
13. Founding and adding go only as far as buyers unserved or buyers to be won.
14. The companies' weighted draw is replaced by a ranking by rate of profit, kept in the script.
15. Anyone may buy machines; only the core and the rivals make them. Know-how is not tied to who
    owns the workplace that uses the machines.
16. Australia with New Zealand becomes a region of its own. The finer map of states is later work.
17. People stay in their income group when they change jobs.
18. One money for the world, and the same rules in every region.
19. The opening carries observed bank debts, banks, unions and core-owned workplaces abroad, coarse,
    from public figures. Business and public debts roll over at the opening. How much money the
    opening holds is set with its builder and brought with numbers.
20. No bound on a price spike; it is watched on the test economy and brought with numbers.
21. The pace named in section 8. Kept by the Director on 22 November 2026 (ADR319).

## 10. Build order

1. **Prices, buyers and plans** (A1 to A6). The fourth round of measurement tests their core first.
2. **Banks and credit** (A7 to A13), with loans to keep running first.
3. **Work and pay** (A14 to A16).
4. **Workplaces and capital** (A17 to A20). Borders open together with the two ways of working and
   the rule on machines, not before.
5. **People and places** (A21), with household and public borrowing, and then the housing design.
6. **The opening, rebuilt on it** (stage 5 of ADR313), with the new public tables.
7. **The country, measured** (stage 6).

Outside events and the pushes of organized people (A22) are built with piece 3. The records (A23)
are carried once, after piece 5. The reference tables and the twelve trades (stages 1 and 2 of
ADR313) go on meanwhile and do not depend on this design.
