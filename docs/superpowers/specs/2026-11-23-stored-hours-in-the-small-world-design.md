# Stored Hours in the Small World: Design

Date: 2026-11-23. Decision record: ADR322. Status: the Director's five answers of 23 November are
below, word for word; the rest is the lead's, written once. The calls of the lead's are listed for
the Director to check. Corrections are small amendments while the build runs.

## What was asked

The small world is on screen. It draws hours of work as bone dots, goods as crimson squares and
money as gold streaks, with no rate between hours and money. Every square is hollow today, and the
scene says that the hours stored in goods are not measured. This design measures them, in the
scene, before the bridge.

In the brainstorm of 23 November the Director ruled three things, each the lead's recommended
option.

1. **"By the claim (Recommended)".** "Split each group's hours back by its own kinds of money:
   hours that came for work (wages), by owning (profit, rent, interest), and as support (benefits,
   kin). No national rate, only the group's own sums. Three things are then seen and never mixed:
   who is fed for working, who takes by owning, who is supported. The bribe is hours that come
   through wages beyond the hours given."
2. **"No: they store nothing (Recommended)".** "Hours spent lending, collecting rent or guarding
   are drawn as hours given that store nothing. They are fed from the hours of those who make,
   carry and care. The screen shows how many hours a place spends on them, and that number grows
   when the fight sharpens. On your line, which already speaks of productive-sector workers. You
   rule a short list of which trades these are; a shop keeps its hours in the food, since it
   carries it."
3. **"After the six rules (Recommended)".** "About five tasks, between the six rules and the
   bridge. The scene runs the ledger's own sums with no database. Two of the five are work the
   bridge needs anyway. The bridge starts about five tasks later. I write a short design and plan
   first, one draft and one check, and show you the first window."

Two more answers came an hour later, when this design had been checked against the code.

4. **"Yes, after the six rules (Recommended)".** The check sized the work at about seven tasks,
   not five, and found that the bridge shares a proof with it, not work. Told this, the Director
   kept the order.
5. **"Hours on the clock (Recommended)".** "The bribe is hours back for work beyond the hours the
   worker was on the clock, worked or idle. A worker paid to stand idle gave the time; the owner
   failed to use it, and that is the owner's loss, not a bribe. In the small world the bribe is
   then never above nothing, so nothing is drawn there. It shows when the country has a core and a
   periphery." The Director's note with it, in their words: "the bribe is in a combination of
   inflated wages and commodities imbued with third world labor consumed by the first world".

The order of the one build machine is now: (1) the scene, done; (2) the six rules of the closest
form, each a switch in the scene; (3) stored hours in the scene; (4) the bridge; (5) the world on
the tick's records.

## What the player sees

In the quiet world a worker gives 10 hours a period. Over time a worker gets close to 6 hours back
in the goods and services that reach their household: 3 in a unit of food, 2 in a unit of care, 1
in a unit of power. An owner gives none and also gets close to 6 back. So does a person the fund
pays. By hours alone the owner and the supported person look the same. By the claim they do not:
the worker's hours came **for work**, the owner's came **by owning**, the supported person's came
**as support**. The bribe is hours back for work beyond the hours a worker was on the clock. In
the small world a worker gets back about 6 for 10, so no bribe is drawn here. It shows when the
country has a core and a periphery.

- **Goods squares fill.** A square is full where the hours in its goods are measured, and hollow
  for the share that still comes from the opening stock, whose hours were never measured. In the
  first period all the food that reaches homes is the shop's opening stock, so its squares are
  hollow. The next period half of it is; then a quarter. The unknown share is seen to shrink.
- **A standing line** counts it: how many of every hundred units moved this period still come
  from the opening stock. In one place: 25 in period 1, then 12.5, 6.25, and on.
- **The table** keeps today's columns and gains a second set behind a small switch at the right
  end of its pager's row: **Given, Back, For work, By owning, Support**.
- **The details panel.** For a household group: hours given, hours back, the split of back by
  claim, and how many units it received that still come from the opening stock. For a workplace:
  the measured hours in a unit of what it handed over this period, with the share from the
  opening beside it.
- **Hours back climb from the opening.** A place gives 240 hours a period. The measured hours that
  reach its households are 160 in period 1, then 200, 220, 230, 235, 237.5, nearing 240. What is
  not yet back sits in the stocks of the farm and the shop.

## Today

- **The ledger exists** in the stored-records crate
  (`rust/crates/babylon-persistence/src/recorded_labor/`). It follows hours through stock,
  services, freight and equipment to their last use, with an exact law each period: opening hours
  plus direct work equal closing hours plus what left (`period.rs`). A stock is a pool: a
  withdrawal takes its share by floor, and the last unit carries the rest (`book.rs`). Opening
  stock carries 0 hours and a flag, "unknown opening", that any mix keeps for ever (`model.rs`).
- **It reads only the tick's register** and the tick's receipts, checks digests, attendance and
  one unchanged catalog, and the tick refuses this economy until the bridge.
- **The runner** of the small worlds (`rust/crates/babylon-circuit-worlds/src/runner/`) has the
  engine's whole transition inside each step, keeps each period's result, and keeps one catalog
  for each set of figures a shock brings.
- **The scene** (`rust/crates/babylon-client/src/small_world/`) draws every goods move hollow
  (`frame.rs`), says why (`controls.rs`, `panel.rs`), and its table has four columns: "Work
  given", "Paid, not used", "Money in", "Money out" (`panel.rs`, `table.rs`). The rail is 400
  pixels wide.

## The design

**S1. One ledger.** The fold, the step that carries hours through one period, moves out of the
stored-records crate into a crate that needs only the engine. The stored-records crate keeps its
register checks, its checkpoint codec, its check of attendance and its binding to one catalog. Its
stored formats, its refusals and their order do not change. The tests that go through the
ledger's public entry, and the live database tests, pass unchanged. Tests of the fold's inner parts
keep their checks and change only where they find those parts. The new crate shows the codec what
it needs of the stock book. The live database tests start a throwaway database of their own.

**S2. A period at a time, with that period's catalog.** The fold's new entry takes one period's
transition with the states before and after it, and the catalog that period closed under. A shock
or a rule turned on changes the catalog in this scene, and the fold follows it. The stored-records
entry keeps refusing a changed catalog for saved campaigns.

**S3. The runner folds.** The ledger is asked for when a runner is opened: the scene asks for it,
and the bench's reference tests do not. The runner opens the ledger from its opening state, every
stock not measured, keeps its stocks of hours from period to period, and opens the second run
(S5) the same way, each opening unit carrying one. It folds each period as it advances and keeps
the period's record of hours with its result. If the ledger refuses a period (a movement it has
never seen, so the closing stocks differ), the runner refuses the period with an error that says
the hours ledger refused it, and the run stops as for any refusal. It refuses rather than lies.

**S4. The stock rule is the ledger's own:** the pooled average, unchanged.

**S5. The unknown share is followed by a second run of the same fold.** The flag cannot clear in a
pool that never empties, so food would be hollow for ever. Instead the runner runs the fold twice
on the same moves: once in hours (opening units carry none, work adds its hours) and once in
opening units: each opening unit carries one unit, counted in millionths like hours, and work adds
none. The fold never decides a movement by what it carries, so the second run is the same law on
a second figure, with the same rounding, and conserves exactly on its own. The stored type does
not change; the second run is never stored. In the small world no opening stock goes into a
recipe, so its count is a true share of units.

**S6. Given is ruling 17:** the hours that went into goods and services, by the household that
gave them; idle hours apart. A good holds its recipe's hours.

**S7. Back is what reached the household** in the period (ADR317's words): the measured hours in
the goods and services that arrived at its home, not what it used up.

**S8. By the claim.** A household group's purse is followed by kind of money as a mix, by the same
average rule as a stock. The kinds are: for work (wages); by owning (profit; later rent and
interest); support (benefits and the treasury's payments; later kin and aid); and "not recorded"
for money held at the opening. A purchase draws the mix of the money that paid for it, and the
hours that reach the group through it are split by that mix. Taxes and other payments out draw the
mix too. Money set aside for an order keeps its mix until the order is paid or refunded. Three
cases arise and follow the same rule: the fund's laid-off program pays worker households, so
their purse mixes wages and support; wage taxes, taken at the close, draw the mix; and under the
six rules an owner's payment into a workplace draws the mix. The sums are exact whole numbers in
the ledger's own rounding: floor shares, the last carries the rest. No national rate is used
anywhere.

It lives with the runner, as a part of the new crate that the runner calls each period: the tests
of the small worlds can then check it against the engine's own cash.

The bribe is read against the hours a worker was on the clock, worked or idle (ADR322, H4). In a
slump a worker group is paid for idle hours, so its back for work can pass its hours into goods;
that is the owner's loss, not a bribe. It is counted over the run so far, not period by period:
wages paid for one period's hours can be spent in a later one. In the quiet world a worker gets
about 6 hours back for 10 on the clock, so no bribe is drawn here. Tests count it in every run
tested; the running scene does not check it. The figure itself is built with the country, where
the hours in a group's goods can come from abroad.

**S9. Hours that store nothing are a ruled direction, not built here.** Lending, collecting rent
and guarding will be hours given that go into no good. The ledger already sends an organizer's and
an agency's hours straight to their own ends; those trades' hours will enter the same way, as
direct work posted to an end of their own, and the screen will count them by place. The Director
rules the list of trades when banks, landlords' companies and police are designed. In the small
world nothing changes: the shop carries the food, so its hours stay in it.

**S10. What is drawn.** A goods move is drawn part full and part hollow by its share of opening
units. The standing line of ruling 18 counts, of every hundred units moved in the period, how many
come from the opening stock. The line rounds to a whole number of a hundred; a part too small to
draw is drawn full. The table's switch shows Given, Back, For work, By owning, Support. By
workplace, Given is the hours given there, and Back and the three claims show a dash. By class and
by place they are the sums of the households' own figures; the shared row shows dashes. The
details panel shows what "What the player sees" lists. For a workplace: the measured hours in the
units it handed over this period, divided by those units, with the share from the opening beside
it. In period 1 the shop's food holds 1 measured hour a unit, and every unit is from the opening.
Sizes and places on screen are set by the lead at the real window.

**S11. The words change.** "Goods are drawn hollow: the hours stored in goods are not measured
here..." becomes a line that says a hollow part is goods from the opening, whose hours were never
measured. "Stored work got back: not measured yet." goes.

## What it does not do

Not the country, not the tick, not saved campaigns. Not the stored record of attendance, which
lacks the household (the runner's receipts carry it). Not hours by place of origin abroad. Not the
rules of outlook, which may later read the split by claim. No hours inside the engine; the engine
is not changed. No rate between hours and money. Hours that expire unsold are counted in this sum
and not drawn.

## What would make it a failure

A figure of hours that the ledger did not produce. Two sums for one quantity. A period the ledger
refused that the scene still draws. Food hollow for ever. A split by claim that does not add up to
back, or kinds of a purse that do not add up to the purse. Any expression where an amount of money
and an amount of hours meet, beyond splitting hours by the shares of a group's own purse. A change
in the stored formats or in the stored-records crate's behaviour.

## Approaches

| Road | New work | Cost later |
| --- | --- | --- |
| **Reuse the ledger: split the fold out** | about 7 tasks | the runner's fold is replaced when the world moves onto the tick's records |
| A second sum in the client | 4 to 5 tasks | two laws for one quantity, which drift; rebuilt later |
| Hours carried inside the engine | 10 to 14 tasks | every stored format, digest and golden changes |

Reuse was taken: one law, already checked, and the cheapest exact road. The bridge must show that
the same fold accepts this economy's periods anyway, so that proof is made early, not twice.

## How we know it works

One place of the quiet world, from the real opening (both places are the same):

| Figure | Pinned value |
| --- | --- |
| Hours in a unit, from period 1 | power 1; care 2; farm food 2 a unit as made |
| Shop food, the limit | 3 hours a unit (2 from the farm, 1 of handling); never reached exactly |
| Given a period | each worker 10; owners and supported 0; the place 240 |
| Back in period p | 80 short of 240 in period 1, and the gap halves each period: 240 − 80 ÷ 2^(p−1), so 160, 200, 220, 230, 235, 237.5; exact to the millionth through period 11 |
| Back, the limit | each person 6; the place 240; never reached exactly |
| Food reaching homes from the opening stock | 100, 50, 25, 12.5 of every hundred units |
| All units moved from the opening stock | 25, 12.5, 6.25, 3.125 of every hundred |
| The harvest fails | a unit of farm food made under the failed harvest holds 20/9 hours |
| The power is cut | a unit of power made under the cut holds 10/9 hours |

- Every period, in every place: back, plus the change in the hours held at workplaces, plus the
  hours that left unsold or lost, equals the hours given; the hours run and the opening-units run
  each keep the ledger's law; the ledger's direct work equals the hours given in the runner's
  receipts.
- Under both shocks, struck in one place and in both, the law holds for 60 periods.
- People who work at another workplace: given follows the household, not the workplace.
- By the claim, in the quiet world: workers and supported people open with no money, so from
  period 1 a worker's back is all for work and a supported person's all support; an owner's is
  all by owning from period 2. In every period the splits of a group's back add up to its back,
  and the kinds of each purse, with those held for its open orders, add up to its cash and its
  reserves in the engine's book.
- In every run tested, counted from the opening up to each period, no group's hours back for work
  pass its hours on the clock. If one does, the builder stops and the lead brings it to the
  Director: the scene would be hiding a bribe.
- One long test folds every reference run of the closest form's bench, in every form built: the
  ledger refuses no period, and its law holds in each. The bench's reference tests themselves step
  the runner without the ledger, so their rows and their time do not change.
- The stored-records crate keeps its formats, its refusals and their order; the tests through
  the ledger's public entry and the live database tests pass unchanged.
- The real client is driven by script for twelve periods and a picture is kept for the Director.

## Calls made here, for the Director to check

1. A hollow part of a square is goods from the opening stock, on the pooled average; the fill is
   the share of units, not of hours.
2. Back is what reached a home, so the climb is 160, 200, 220, and not what was eaten.
3. Treasury payments to supported people count as support, with the fund's benefits.
4. Money held at the opening is its own kind, "not recorded", and is shown in the panel.
5. The table's second set has no column for "not recorded"; while it lasts the three claims add
   up to less than back, and the panel shows the rest.
6. A good holds its recipe's hours; extra hours on the clock are idle, drawn apart.
7. The stock rule stays the pooled average.
8. The ledger moves into a crate of its own; the stored records keep their checks.
9. A refused period stops the run, and the scene says the hours ledger refused it.
10. The bench's reference tests step the runner without the ledger, so their rows and their time
    do not change. One long test folds every reference run of every form built.
11. The split by claim lives with the runner, so the tests of the small worlds can check it
    against the engine's cash.
12. The bribe is not drawn in the small world. It is counted over the run so far, not period by
    period, since wages paid for one period's hours can be spent in a later one. That it does not
    arise here is reasoned from the quiet world and not yet counted: tests count it in every run
    tested before the scene is shown. The running scene does not check it.
13. In the second run each opening unit carries one whole unit, counted in millionths like hours.
14. The work is about seven tasks. The lead first said five; the Director kept the order at
    seven.
15. In the table's second set a workplace row shows Given only, with dashes for Back and the
    claims; class and place rows sum the households; the shared row shows dashes. (The other way:
    show the workplace's own workers' households.)
16. The standing line adds units of power, care and food together, though only food carries
    opening units. The other reading is "of every hundred units of food moved".

## Build order

Each task proven before the next.

1. The view of one period, still inside the stored-records crate: the fold reads the view, and
   the stored-records entry maps its receipts into it (the agency rows become hours by household);
   behaviour unchanged.
2. The fold moves into its own crate, with an entry that takes each period's catalog. The
   stored-records crate keeps its formats, its refusals and their order.
3. The runner folds, both runs; tested on the figures above, both shocks, and work elsewhere;
   the long test over the bench's reference runs.
4. By the claim: purses by kind, the split of back; tested on the identities.
5. The scene, first part: goods part full, the standing line, the words.
6. The scene, second part: the table's switch with the second set in its three groupings, and the
   details panel.
7. A scripted run on the real display; the lead looks at the window and shows the Director.
