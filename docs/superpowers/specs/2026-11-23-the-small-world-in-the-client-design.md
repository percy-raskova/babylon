# The Small World in the Client: Design

Date: 2026-11-23. Issue: PER-371. Decision record: ADR320. Status: the Director's six answers of
23 November are in section 2; the rest is the lead's, written once, and section 9 lists every call
of the lead's for the Director to check. Corrections are small amendments while the build runs.

## 1. What this is, and why

The Director, 23 November 2026: "i want to make sure that we get this into a game system people
can see in bevy with the hypergraph visualizations and what not".

Nothing of the new economy could be seen that day. The tick refuses every period that has market
clearings or tier rows (`babylon-tick/src/material_world/register.rs`), every campaign catalog is
compiled with no market policy (`babylon-persistence/src/economic_catalog/compile.rs`), and the
scene of hours, goods and money (ADR317) had its geometry in the hypergraph library and nothing in
the game. The rules measured over ten rounds lived only where the engine's tests reach.

This design puts the small test economy on screen, as a scene of the Bevy client that people can
step, watch and push. It is the first place where the new economy is seen, and later the place
where each rule of the closest form is seen when it lands.

## 2. What is ruled

All of it on 23 November 2026, in the question dialog. The labels are the Director's picks, word
for word.

1. **The order: "Screen first".** Then, after the sizing in section 3, the road below changed that
   order in one point: the bridge moved to second place.
2. **The first world: "The small world, to poke".** "The test economy as a scene in the client,
   drawn by its ties as a hypergraph, with buttons for the pushes: fail the harvest, cut the
   power."
3. **The road: "In the client now, saved later".** "The client runs the engine itself for this one
   world: step, auto-play, push at any period, no save. No bridge needed [...] After the bridge it
   moves onto the tick's records, and later becomes a real saved campaign. About 3 to 4 tasks of
   it are rebuilt on the way."
4. **The world: "The doubled world".** "Two copies, eighty people. A harvest can fail in one copy
   while the other goes on, which is the run that decided the verdict."
5. **A push is "A labelled shock, this scene only".** "A control of the small world's scene, marked
   as a shock, with the figure it changes printed beside it: 'the farm makes 9 a batch, not 10,
   from period N'. Not a player's action, and not part of Wayne's game."
6. **Sets: "Workforces, owners, the fund".** "Three kinds of real hyperedge, declared with the
   membership values built last week: the people of each workplace with their hours, an owner with
   what they hold, and the households the fund pays with what it pays. Each gets a membrane."

The order of the one build machine that follows from 1 and 3:

- **Now:** the library's Bevy crate is finished; the small world runs in the client.
- **Then:** the bridge (`docs/superpowers/plans/2026-11-20-opening-stage-4b-records.md`).
- **Then:** the small world moves onto the tick's records; the rules of the closest form land,
  each one visible in this scene.
- **Later:** a real saved campaign.

The scene itself is ruled by ADR317 and its design
(`2026-11-21-field-and-particles-design.md`): hours and money are two streams with no rate between
them; bone for living work, crimson for work stored in goods, gold for money; three beats a
period; a set is a hatched membrane, never a dot with spokes; nothing is hidden in the first
build. One of its rulings is amended here: its R8 made the whole country the first scene with real
numbers. The first scene people see is now this one. The whole country stays the first scene with
the country's own numbers.

## 3. What exists today

- **The client opens a campaign through a runtime process and PostgreSQL.** It draws what it reads
  back from stored views. It has no way to run a world itself, and no command that changes a
  world. A saved campaign fixes its catalog: the stored-hours ledger refuses a period whose catalog
  changed (`babylon-persistence/src/recorded_labor/period.rs`).
- **The small world lives in the engine's tests.** On the branch it is one place: four workplaces
  and forty people (`babylon-material-circuit/tests/small_world/support.rs`). The doubled world,
  and the two shocks the Director named (the harvest that fails for ten periods and returns; less
  power), exist only on the scratch branches of the measurement rounds.
- **Every shock is a change of a figure in the catalog.** A lower yield, a dearer hour, a tax rate.
  The state is not touched. That is why a shock cannot enter a saved campaign as things stand, and
  why it is plain code when the client runs the engine itself.
- **The engine's own period is enough.** `close_material_period`, `staffing_requests`,
  `advance_staffing`, `distribute_staffing_members`, `finish_with_staffing`: the loop the bench
  ran, all of it engine code on the branch. Each period's result names the household, the
  workplace and the hours by kind for every member, and every payment with its purpose and both
  ends. So the two gaps that the country's scene must close in the stored records (the household
  kept on attendance; a household's hours published) do not arise here.
- **The hours stored in goods are not available.** They are worked out by the stored-hours ledger
  from the tick's register, and the tick refuses this economy until the bridge is built.
- **The library.** Geometry is merged. Of the Bevy crate's thirteen tasks, six are built and
  pushed on its branch, and the plugin that draws arrives with tasks seven to nine. The game pins
  the library at a revision from before the geometry, and locks Bevy 0.20.0 where the crate asks
  for 0.20.1.

## 4. Goals

- A person opens the client, picks the small world and sees eighty people, eight workplaces, two
  owners, a treasury and a fund, drawn by their ties.
- They step a period and see three beats: work goes in, goods move through, money comes back.
- They strike the world with a shock at a period they choose, in one place or in both, and see
  what the economy does: who is sent home, which workplace stops, where money piles up.
- Hours and money are read side by side in one table, by workplace, by class and by place.
- The picture is the engine's own figures. The same run gives the same picture on every machine.

**Not goals.** A saved game. Wayne. The country. The player's own view with things hidden. The
rules of the closest form (they arrive later, each as a switch in this scene). The arrangement on
the land and the wells: the small world has no map and no shares of world view.

**What would make it a failure even if it runs.** A figure on screen that the engine did not
produce. A shock that looks like something the player did, or that reaches Wayne. Marks that
relate hours to money. A scene that needs a database to open. A picture that differs between two
runs of the same steps.

## 5. Approaches

Four roads were sized (the sizing is in the job's records; its table is in ADR320).

| Road | The player can | New work | Lost later |
| --- | --- | --- | --- |
| A real saved campaign | open, save, reopen, push | 9 to 14 tasks after the bridge and the scene's sums | nothing |
| **The engine in the client** | step, auto-play, push; no save | 7 to 9 tasks | 3 to 4 tasks |
| A recorded run played back | pick a run and watch it | 5 to 7 tasks | the player |
| In the client on the tick's register | as the second | 7 to 9 tasks after the bridge | the runner |

The Director picked the second. It is on screen about thirteen tasks sooner than the others. Its
cost is stated: for a while there is a second path to the figures beside the stored records, and
the runner, the entry and the frame builder from raw results are rebuilt when the world moves onto
the tick's records. A recorded run cannot be poked, so it was not offered.

## 6. The design

### 6.1 The world

The doubled world of the measurement rounds, with taxes and the benefits fund.

- **Two places, A and B.** Each holds a utility, a farm, a clinic and a shop. The utility makes
  power. The farm makes food from power and work. The clinic gives care from power and work. The
  shop buys food from the farm and sells it. Opening prices: power $12, farm food $25, care $30,
  shop food $38. Every hour is paid $10.
- **Eighty people, forty a place:** twelve at the utility, four each at the farm, the clinic and
  the shop; eight in the owner's household; eight who are supported. A person works ten hours a
  period. Each person needs one food, one power and one care a period.
- **One owner household a place** holds its four workplaces whole and takes their profit.
- **One treasury and one fund for both places.** A tax on wages and one on operating income feed
  them; the fund pays the supported and those laid off.
- A place is a copy. In the engine's data both carry Wayne's county code, because a location must
  be a county there. On screen they are "Place A" and "Place B", and the scene says that this is a
  test economy and no real place.
- The figures are the measured ones, at the small set (a price moves by $1; a workplace opens with
  one period of its outlay in cash). Every identity is the prototype's, so that the bench of the
  closest form's plan can later prove this same world against the measured rows.

### 6.2 How it runs

- In the client's own process. No runtime process, no database, no save. The scene is reached by
  one command (`mise run play:small-world`), by a flag of the client, and from a button on the
  title screen. The observer's window cannot open without a campaign and cannot shed its own
  parts while it runs, so the button opens the scene in a window of its own. The scene says on
  screen that it is not saved.
- One period is the engine's own period, as section 3 names it. The scene never changes the
  engine's state from outside.
- **Step** advances one period and plays its three beats. **Play** steps on a timer. **Again**
  replays the last period's beats. **Start over** rebuilds the opening.
- The scene keeps every period's result of the session in memory, so the table can show a history.
- The catalog asks for the market rules and for plans from spare money (rule A6): the engine as it
  is today. The closest form's rules are added later as named switches, off by default.

### 6.3 What is drawn

The arrangement is "by their ties" (the scene design's section 6.7). No force acts over time. A
position is worked out from the period's figures, once a period.

- **Bodies.** The eight workplaces stand along the bottom, Place A's four on the left and Place
  B's on the right, the two places apart. The treasury and the fund stand together at the top. A
  workplace carries two rings that are never merged: a dashed bone ring for the hours that
  reached it, a gold ring for its money. An owner here is a household, so it is a particle and not
  a body; its set shows what it holds.
- **The view** looks straight down with no perspective, fitted to the plane, so the picture fills
  its part of the window and a dot stays round.
- **Particles.** By the scene design's rule a particle stands between its employers and whoever
  holds a claim on it, nearer the larger share of its income. So a worker stands near their
  workplace, a person on benefits toward the fund, and an owner's household among the workplaces
  that pay it. Wages and profit lean to different sides: workers stand above their workplace and
  an owner below the four it holds. A particle is a household group, as ADR317 rules, and its dot
  grows with the people it holds. A switch shows a closer look, one dot a person (section 9,
  call 1).
- **Sets,** as ruled. Each is a real hyperedge whose memberships carry a number, and each gets a
  hatched membrane, thicker where the number is larger.
  - A workforce: the people of one workplace, with the hours each gave it this period.
  - An owner: the owner's household and the four workplaces it holds, each workplace with the
    capital the owner has in it.
  - The fund: the households it paid this period, with what it paid.
  A membership of zero is outside. Where two sets overlap, both hatchings show.
- **Marks and beats.**
  1. *Work goes in.* Bone dots from people to the workplace they worked at. Hours that went into
     goods, services, handling and upkeep are full dots. Hours paid and not used are hollow dots
     that stop at the workplace's edge.
  2. *Goods move through.* Crimson squares along the goods' own path: power from the utility to
     the farm, the clinic and homes; food from the farm to the shop and from the shop to homes;
     care from the clinic to homes. **They are hollow in this build.** A hollow square stands for
     goods and for no number of hours (the scene design's ruling 18). A standing line says why:
     the hours stored in goods are not measured here until the world runs on the tick's records.
  3. *Money comes back.* Gold streaks from payer to payee, by kind of payment: wages, purchases,
     taxes, benefits, profit paid out.
  One mark stands for a fixed amount, printed on screen, one figure for hours and one for money.
  No line of code relates the two.
- **The table.** Work given; paid, not used (ADR317's ruling 17 gives idle hours their own
  column); stored work got back; money in; money out. "Stored work got back" reads "not measured
  yet" in this build. Grouped by workplace; by class (owner or not, earner or not); by place.
- **The words on screen.** "ADMIN · MATERIAL TRUTH · UNFOGGED", as ADR217 has it. "A test economy.
  Not Wayne. Not saved."
- **A declared surface.** The client keeps a manifest of everything it shows, and a test holds
  every shipped visual to it. The scene is entered there as a sixth surface, an administrative
  one, with the manifest's own line: "unfogged material truth; no player knowledge state".
- **Still marks.** A switch shows the three beats as still paths, for reduced motion.
- **Selection.** Picking a body, a particle or a set shows its own figures of the period.

### 6.4 Shocks

A shock is a control of this scene, marked as a shock. It is nobody's action. Each one changes one
named figure of the catalog from the next period on, and prints that figure before it is struck
and while it holds.

| Shock | The figure | Lasts |
| --- | --- | --- |
| The harvest fails | a farm makes 9 food a batch, not 10 | ten periods, then it returns; or until lifted |
| The power is cut | a utility makes 9 power for 10 hours, not 10 | until the run is started over |

- Each is struck in Place A, in Place B or in both.
- A shock that holds is listed with the period it began. Lifting the harvest's shock restores the
  opening's yield from the next period on.
- **The power cut is not lifted in this build.** It changes the size of a batch (ten hours and nine
  units, where the opening has one hour and one unit), and the engine keeps its plans in batches.
  Lifted in the middle of a run, a plan made under the cut would be read in the old size for one
  period, and power would fall to about a tenth for a reason that is no part of the economy. So it
  holds until the run is started over, and the scene says so.
- **Two more shocks were meant and are left out:** a pay rise at the clinic and a cut of the
  fund's taxes. The plan found that a wage and a tax rate live in the state, not in the catalog,
  and the scene never changes the state from outside (the last point below).
- The bench's other pushes change the number of people or the money a workplace opens with. They
  are openings, not shocks: struck in the middle of a run they would create or destroy people or
  money. They are left out (section 9, call 4).
- The scene keeps the list of what was struck and when, so a run can be told and repeated.
- A shock is offered only if its figure is the catalog's. If the plan finds that one of the four
  lives in the state instead, that shock is left out and the plan says so.

### 6.5 Where the code lives

| Part | Home |
| --- | --- |
| The doubled world, its opening and its shocks | A crate of small worlds, `babylon-circuit-worlds`, which the bridge's plan already names. An ordinary crate with nothing a test alone needs, so the client may depend on it. |
| The runner, the frame builder, the scene, the controls, the table | The client, a new scene beside the observer's. The frame builder is a pure function from a period's result to a picture, tested without a window. |
| Meshes, membranes, marks, beats | The library's Bevy crate, pinned by revision. |

The game's pin of the library is raised to the revision that holds the plugin, and its Bevy lock
moves to 0.20.1. Until the Director orders the library's merge, the pin names a commit of the
library's branch.

### 6.6 What changes later

- **After the bridge:** each step goes through the tick's register. The crimson squares become
  full where hours are recorded, and "stored work got back" is measured. The runner and the entry
  are rebuilt; the frame builder then reads the receipts the stored records carry.
- **With the closest form:** each rule is a named switch in the scene, with its own marks: a move
  of people between workplaces, a workplace that rests, an owner's money going in.
- **Later:** a real saved campaign. How a shock enters a saved campaign is its own design.

## 7. How we will know it works

- The quiet world stays still: 34 periods in the scene's runner, every period equal to the first,
  480 hours attended, total money and people equal to the opening's in every period.
- Under every shock, struck in one place and in both, total money and people stay exact for 60
  periods.
- The frame builder gives exact figures for the quiet world's first period: the dots, squares and
  streaks drawn and "not drawn" add up to the period's hours, goods and payments.
- The same steps give the same frames twice.
- The real client is driven by script: open the scene, step, fail the harvest in Place A, step
  ten periods. Farm A then makes 36 food a period and farm B 40, and every workplace's hours in A
  and in B are written down as the client reports them. A picture is kept for the Director. (The
  first wording asked that the farm's hours fall in A. The plan counted the bench's rows: with the
  harvest failed in A, farm A worked its full 40 hours for the first 46 periods, and the fall
  showed at the clinic and the utility. A line of mine that had not been counted.)
- The frame time is measured on the build machine and stated.

## 8. Left to the builder

The layout in scene units. The sizes of marks and the amount one mark stands for. The controls'
look, within the client's own theme. How the history table pages. The names of types and modules.

## 9. Calls of the lead's, for the Director to check

1. **What a particle is here.** ADR317 rules that a particle is a household group, and that is
   what the scene opens on. This world has twelve household groups: one for each workplace's
   workers, one of owners and one of supported people in each place. Drawn so, each workforce is a
   ring around one particle, and the picture is thin until people can change workplace. So the
   scene also has a closer look, by a switch: one dot a person. Eighty dots then stand in their
   membranes, and a layoff is seen as people leaving one. A standing line says what that look is:
   the record counts people; it does not follow a person, and the people of one group share one
   purse. Both are built. Which one the scene opens on is the Director's to change.
2. **An owner's set** holds the owner's household and its workplaces, the workplaces with the
   capital the owner has in them.
3. **Goods are drawn hollow** until the tick's records carry this economy.
4. **Two shocks are offered** (section 6.4): the harvest and the power cut, the two the Director
   named. The power cut holds until the run is started over. A pay rise and a tax cut are left
   out because their figures live in the state. Fewer mouths, more mouths and a shop that opens
   with half its money are left out because struck mid-run they would create or destroy people
   or money.
5. **The scene is reached** by `mise run play:small-world`, by a flag of the client, and from a
   button on the title screen, which opens it in a window of its own.
6. **The two copies are named** Place A and Place B.
7. **The fund world** is the one shown, because the ruled sets include the fund.
