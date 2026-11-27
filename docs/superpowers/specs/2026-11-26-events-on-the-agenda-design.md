# Events on the agenda: design

**Date:** 26 November 2026. **Status:** draft for the Director's approval. Nothing here is built,
and nothing is built from it before it is approved.

**In one paragraph.** The world keeps a record of everything that happens in a period, with its
cause. Most of it is news. When a piece of news touches your organization, it goes on the agenda of
your next monthly meeting, and the game stops there. The item is decided in the decision ceremony
that the porch sessions describe. No outcome is written for an event. Each option is an act your
organization can really take, aimed at one of the parties the event names, with what it stakes. If
you carry on and answer nothing, the need or the fight is still there, and whoever else can reach
those people answers it. What followed comes back at the next close and over later periods, and is
kept as the event's page in the wiki. Storms and floods are drawn from the campaign's seed, once,
when the campaign is made, at the rates real places have. They may only destroy or burden things. A
financial panic is nothing anyone fires: it is what bank runs look like once the banks are built.

**Why.** The design for how the economy adjusts promised the player an economy that is "weather with
causes", where "every turn of it is an event the player can trace to its cause and act on". The
record and the causes are being built. What is missing is the acting: a way for the world's events
to reach the player as decisions worth making, and never as a spreadsheet or a script.

## 1. What was asked

**The Director, 26 November 2026, morning,** while the country's numbers were being built:

> is there a coherent logic emerging for a push/pull event queue type system where external events
> triggered "push onto" the game state from outside, while 'internal' events "emerge from" the game
> state and fluctuations as a result of the internal mechanisms of the market? like say there is a
> stock market panic, i want that to emerge in the game. but also say we want a tornado, we could
> set that up as an event that manifests in destroyed economioc infrastructure or things needing
> repair etc. that's kind of what i'm going for to keep it directed towards a game engine. right now
> i dont want code or modifications, i just want to think this through

**The Director, the same evening:**

> Lets design these in such a way as to enable meaningful and entertaining gameplay decisions in a
> menu style game

**Four answers in one dialog, the same evening.** Each is the option the lead recommended. Labels
and descriptions are word for word.

1. What the player decides with. **"A card with aimed plays (Recommended)"**: "The game pauses on a
   card: what happened, who is hit, who the people there blame, and up to four plays. Each play is
   one of the nine verbs already aimed: target, cost in your members' hours and money, how long the
   chance lasts. All nine verbs stay one key away. It plays like an event pop-up, but every option
   is a real act that any organization could take." Not picked: "The verb plate only"; "Options
   written per event".
2. What happens if the player does nothing. **"It closes, others take it (Recommended)"**: "An
   opening lasts a few periods. If you pass, the nearest hand acts: the county, a church, the
   landlords, a rival organization, a fascist group. The card later shows who acted and what they
   gained among those people. Passing is a decision with a cost. It needs other organizations that
   act on openings, which is more to build." Not picked: "It closes, nobody takes it"; "It stays
   open".
3. How often nature strikes. **"Real kinds and rates, one dial (Recommended)"**: "Each place gets
   the hazards it really has (Wayne: floods, ice, heat; the plains: tornadoes; the Gulf:
   hurricanes), near their real rates. One declared dial in the scenario raises or lowers all of
   them. Across 187 places something happens somewhere most periods; in your own county it is rare
   and heavy." Not picked: "Heightened for drama"; "No nature at first".
4. What a financial panic is made of. **"Credit first, shares later (Recommended)"**: "The first
   panics are runs and loan calls: a bank short of capital stops renewing loans, workplaces shut,
   losses spread. Shares, bonds and land titles with prices come as a later step of the financial
   system; a share crash then hits loans through what was pledged for them." Not picked: "Design a
   stock exchange now"; "Credit only".

**Five things the lead got wrong that day.** The first three were told to the Director the same
evening. The last two are told here.

- The morning's question was already ruled. Rules A22 and A23 of the design for how the economy
  adjusts (approved 21 November, ADR314) are the push and the pull: the economy moves by its own
  tendencies, by outside events, and by what organized people do to it; and every act leaves a
  record shown as news with its cause. The lead answered from the rule roles of August and missed
  its own approved design.
- The dialog's third question said "Your law rules out a calendar". It does not. A22 lets a scenario
  date an outside event on a calendar. The Director's own answer of 21 November named "a calendar of
  world events" beside "shocks drawn from the campaign's seed". The pick for nature stands on its
  own; E22 keeps the calendar in the record for dated world events.
- The dialog was written without the porch sessions of 25 and 26 October (`docs/gameplay/`). They
  already rule the form of a decision. This design is built on them (section 2). The dialog also
  called the chance to act "an opening"; this design says **occasion**, the pay fight's word,
  because "the opening" already means the economy's first period.
- The dialog said that options written for each event would need a constitutional amendment because
  they break the set of nine verbs. Under Constitution v4 a new act is a governed addition to the
  vocabulary (ADR177), not an amendment. What rules written outcomes out is Article III: every
  action needs an eligible actor, a target and a cost, through the same machinery as everyone's. The
  porch sessions' own ceremonies are written scenes over real acts; section 4 follows them.
- The third question offered storms drawn from the seed and did not say what the law makes of that.
  Amendment AJ gives chance no seat in an outside event. ADR224 forbids a shock to pass as a
  Mechanic. ADR248 authorizes no "stochastic shock". A22's own words are "drawn once from the
  campaign's seed". Section 5 reads them to the letter (E20): nature is drawn once, when the
  campaign is made.

## 2. What is already ruled, and binds this design

Read on 26 November at commit `9912d98f5`. Words in quotation marks are the texts' own.

**The form of a decision: the porch sessions (`docs/gameplay/2026-10-25-porch-01.md`).**

- **The ceremony.** "Deliberation lives in the five screens (poring, weighing, wiki-diving). The
  decision itself is a moment of drama: a split-pane event popup (HOIV4-event energy, nicer face)
  laying the options side by side with honest summaries of what each *means* — never what each
  *yields*. The click is the gavel, not the deliberation. Physically: click, sometimes a slider or
  typed number when allocating people or money."
- **The answer in three layers.** The seal, at once: "Known prices debited visibly on the spot.
  Unknowns marked unknown, honestly ... Outcomes are never previewed. The game states what is
  staked, which mechanisms engage, and what it does not know." The reckoning, at the period's close:
  "*story first, numbers second*". The long tail, periods later: "The wiki backfills; the player
  *discovers*."
- **The hard rule.** "the game never explains *why* mechanistically. It shows what happened, who did
  what, what it cost. Causes are for the player to infer, argue about, and post." A23, newer, has
  every record carry its cause and the client show it. E16 reads the two together, and call 3 of
  section 11 flags the reading.
- **The visibility rule.** "Show only what a participant could learn from reading a communist
  history book ... *would Mao have put it in the treatise?* Funds seized — yes, a fact in the world.
  Cohesion modifier — no ... **Failure mode:** spreadsheet popups. Visible math. Gameable
  multipliers."
- **Fog.** The material layer "is public record"; the political layer "is visible only within
  organizing reach"; "Unknowns render as honest unknown — never zero, never stale. Clicking an
  unknown names what you don't know and how to learn it".

**Where events come from: the adjust design (ADR314, approved 21 November).**

- **A22.** The economy is moved by "Its own tendencies, always"; by "Outside events, built as one
  kind of record that the scenario can fill three ways: fired when the world's state meets a
  condition; dated on a calendar in the scenario; or drawn once from the campaign's seed, so that
  the same seed replays the same history"; and by "What organized people do. A stoppage withholds
  hours, a rent or debt strike withholds payments, a blockade closes a route, a boycott withholds
  buying. The economy takes each as a push like any other, whoever starts it."
- **A23.** "Every act leaves a record ... each is a record the tick carries and the client shows as
  news with its cause."
- **A13.** "Every rescue is an event the player sees, with its sum and its terms."
- What it left open: "The content of outside events: the record and its three sources are built; the
  events are written later", and "The player's own verbs: the places to act are built; the verbs
  come with the player's organization."

**An event the player can answer: the pay fight (ADR323, approved 24 November).** "An event is news
your organization could act on. It carries a forecast" (PF15). A measure "does nothing by itself"
(PF14). You "decide what yours calls, asks, takes up and pays, and whom it invites"; a call "cannot
make anyone stop, go back or join" (PF10, PF16). "Others act, yours waits" (F5). After a win the
payer is shown (PF17). The plan puts `Event`, `Forecast`, `EventChoice` and the event's buttons in
its second part (P2-1).

**The Constitution (v4).**

- Article III. "Player and non-player actors act through the same declared causal machinery. Actions
  must have an eligible actor, a target, and a cost or constraint. They must also give a preview of
  what the actor can know and a later receipt that shows what occurred. All material effects become
  next-period intents".
- Article III. "External events can introduce only their declared exogenous burden, capacity change,
  or pressure. They must not directly author downstream unemployment, shortages, deaths, migration,
  consciousness, firm failure, bank failure, or a winner."
- Article III. "A dominant zero-cost choice, an action with no legible consequence, or an outcome
  that cannot respond to counterfactual play is a design defect."
- Article V. "Every finite-kernel choice must use the governed replay key, consume one exact integer
  ticket draw, and publish a hash-bound transactional choice receipt."
- Article VII. Every gameplay surface declares a `DecisionSurfaceContract`: its decision question,
  visible signals and their uncertainty, knowledge and fog requirements, available actions, expected
  feedback receipts, linked Archive subjects. "The core Archive loop is evidence to decision to
  action to consequence to an updated dossier."
- Amendment AJ. "An event declaration owns no probability." No "arbitrary event forecast". Chance
  belongs to a Mechanic rule's finite kernel and to nothing else.

**The order of the gates (ADR250, 4 September).** The circuit, then player agency, then the pandemic
benchmark, then "systemic credit and 2008". In the benchmark, shocks enter "only as governed
external-event rows adding allowed pressure, burden, or capacity effects".

**The rule roles (ADR224).** A rule is a Mechanic, a Recognizer, an ExternalEvent or an Intent. The
restricted roles may write only what an exact row allows. Today the code allows three intents (the
organizer's practice, City PD's visit, the County Review) and three recognizers, and no external
event at all. "A governed production shock or action cannot regain mechanic authority by relabeling
itself". The gates that bring shocks and player actions "must extend the empty restricted-role
allowance tables through their own named mechanics and verification."

**Chance (ADR248, the record of Amendment AJ), item 14.** "One shared cause uses one joint kernel
over its complete carrier ... Recognizer, ExternalEvent, and Intent remain deterministic. No
universal sigmoid, empirical sampler, alternate RNG, stochastic recognizer, stochastic shock,
stochastic intent, or authored terminal route is authorized."

**The order of work (ADR325, 25 November).** After the country's numbers: "the pay fight's first
part ... Then the game's own turn carries the rules, so that a campaign runs, saves and shows them."
"Its first decision for the player is the pay fight." "Banks and credit, homes and rent, and nations
drawn over household groups are designed and come after it." The adjust design's own order (its
section 10) says: "Outside events and the pushes of organized people (A22) are built with piece 3",
which is work and pay.

**Other rulings used below.** Capacity belongs to organizations; "repression and revolutionary
action are the same allocation" (ADR184). "STRUCTURE IS THE PREMISE; MAGNITUDES ARE EARNED ...
organizing buys the QUANTITY, not the FACT" (ADR182, R2). Standing orders are in scope, "with
material interrupts" (ADR176, 22). Pacing is tuned without coefficients (ADR176, 24). The pacing
gates of the Game Design Standard (section 3), written when a tick was a week. Elections run on
their own dated calendar (onboarding, R10). Fog never enters the tick's hash (ruling of 18 July).

## 3. What the player sees

Everything in this section is a sketch of the form. No figure in it is a measurement. The acts are
the ones the game has today. The church stands for an organization that the engine runs; none exists
yet (section 12, step 4).

**Most periods, nothing stops.** Play runs. The standing work goes on. The Ticker and the wiki fill
with the period's news, each item with its cause: a price that moved, a plant in another state that
shut, a flood two counties away.

**Then something touches you.** At the next monthly meeting it is the first item on the agenda, and
it is decided in a ceremony. The ceremony has the four parts every porch ceremony has.

**Trigger.** Period 38 has closed. The committee at the stamping plant, which your organizers meet
at its public desk under the agreement of period 31, reports work lost.

**Pane left.**

> **WORK LOST AT THE STAMPING PLANT, WAYNE**
>
> The afternoon shift did not start on the third. The committee counts 1,240 people let go. The
> owner gave the committee no reason. The committee's own account: the bank did not renew the
> owner's loan.
>
> A household there has about three periods of savings and benefit before its needs go unmet, if
> prices hold. The county's list takes them from next period. The church on Michigan Avenue has
> opened its hall.
>
> Not known to us: who holds the plant's debts, and whether other plants owe the same bank.

**Options,** side by side on the screen: up to four acts, and "Carry on" beside them.

- **Carry our food run to the plant's people.** *Sixty of our hours and $9,000 of the fund go to the
  pantry on Michigan Avenue for four weeks. The Thursday contact at the axle plant is not made this
  period, and that agreement runs out in two. The run is made in the open. What the plant's people
  do afterwards is theirs to decide.*
- **Ask the committee what it knows of the bank.** *Twenty-five of our hours at the committee's
  desk. The committee answers, or it does not. Nothing reaches the households this period.*
- **Bring their claim to the county's hearing.** *Forty of our hours on the hearing day. The claim
  is heard with ours or beside it. The county decides what it pays, by its own list.*
- **Carry on.** *The standing work continues and nothing is spent. The need stays. The county, the
  church and whoever else is there will answer it or not.*

**The seal.** One option is chosen. The click is the gavel.

> *Staked: sixty hours, $9,000, and the Thursday contact at the axle plant. Unknown: how many of the
> 1,240 the run reaches, whether the pantry's people take part, and who else is feeding them.*

**The reckoning,** at the next close, on the event's page in the wiki. Story first, numbers under
it.

```text
WORK LOST AT THE STAMPING PLANT, WAYNE           opened period 38 . open
Period 39  Our run reached 410 households through the pantry. 60 hours, $9,000.
           The county paid relief to 520 of them. 310 were ranked too low to be paid.
           The church fed about 300 we did not reach.
           The owner sold the presses to a buyer in Ohio.
           The axle plant's agreement has one period left.
Period 40  We brought the item back and asked the committee about the bank. 25 hours.
Period 41  The committee's report came in: the bank holds the loans of four more
           plants in Wayne. (Happened in period 38. Learned in period 41.)
Period 44  Of the 1,240: 380 have work again, 150 have left Wayne, 710 are on the list.
WHO ANSWERED  us: 410 households, 6 joined . the county: 520 on its list . the church: about 300
```

**The long tail.** Three periods later a second plant that owes the same bank shuts. It is filed on
the same page, because the record names the same cause. It hits people the page has not named
before, so it is on the agenda again. This time you knew it could come.

**A storm.** In period 52 a tornado strikes Wayne. It was drawn from the campaign's seed when the
campaign was made, like all its weather. The record says what it destroyed: a third of the machines
at two workplaces, the stock of one warehouse, the road past the rail yard for some periods. Nothing
else is written by the storm. What follows is the economy's and the organizations' own doing: work
lost at the two workplaces, a market short of what the warehouse held, the county's fund drawn down.
Each is an ordinary event with its ordinary ceremony. The chain on its page ends at the storm, which
is nobody's hand.

**A run.** Once banks exist: a bank short of capital stops renewing loans, a business that misses
three payments is taken by its lender, the large depositors of that lender leave, the federal level
lends to the bank and to the largest companies, and to no household and no small business. Each step
is a record with its cause, and each is news. Where one of them touches your people it is on your
agenda. The page that links them is what the papers call a panic.

**The menus this adds.** Five, and each is a list.

- *The news* on the Ticker, each line with its cause. Any line can be put on the agenda by hand.
- *The agenda* of the monthly meeting: the events to decide, before anything else in the meeting.
- *The ceremony*: the scene, up to four acts, and "Carry on".
- *The event's page* in the wiki: the seal, the reckoning, the long tail, and who answered.
- *Standing answers and stops*: for each kind of event, the act that answers it without asking, and
  whether the kind stops play.

## 4. Today

Read at commit `9912d98f5`. Paths are under `rust/crates/`.

**The player's loop that runs.** The organizer's workspace in the client
(`babylon-client/src/organizer/`) and its rules (`babylon-practice-contract/src/organizer/`).

- The organization does **one practice a period**. The choices are an inquiry (work lost,
  maintenance received), a contact (reinforce, hold), a collection, local or remote aid, an
  invitation to the relief hearing, a contact at the County Review, and pausing or resuming the
  standing work.
- The player chooses, asks for a **preview** (hours needed, hours at hand, what it replaces, a
  refusal with its reason), and confirms. The act is resolved in the next period and returns a
  **receipt** with one of eighteen outcomes. "No outcome is credited until the period commits."
- The limit is **organizers' hours**, promised by contributors and bound to their households' time.
  Cash is spent only by gifts and collections.
- If the player admits nothing, the **standing work** runs (the routine contact). It pauses by the
  player's word or when the hours are not there.
- **Knowledge is earned.** A report comes from an inquiry. A contact becomes an agreement that lasts
  a set number of periods. While an agreement holds and the partner permits it, a drop in work hours
  at that workplace is published to the organization without being asked for (`ReducedWork`).
- Partners answer by fixed policies. City PD is the one organization besides the player's that
  decides anything: one visit a period when it has the money, to a case it knows from public record.
- The surface declares its `DecisionSurfaceContract` (`babylon-client/src/decision_surface.rs`). Its
  question: "How should our organization use its time, and whose demands can our partners take to
  the relief hearing?"

**What already stops play.** The client pauses on a new City PD notice, a hearing notice, an updated
dispatch, a disclosed freight loss, and a delivery when "Stop on delivery" is on. It also pauses
when the player reads a report or asks for a preview. Each is a separate call to `pause_playback()`.
There is no list of reasons, and none of them offers a choice.

**What does not exist.** No event of the world asks the player for an answer. Searched and not found
in the client: an event card, a ceremony, an agenda, a news list beyond the county's strip and the
production log, a menu of the nine verbs. The October plan's `ceremony_modal.rs` is not built. Of
the nine practices the contract names, three run (organize, mutual aid, investigate); strike,
blockade, occupation, damage, capital strike and agitate are contracts with no caller.

**The records.** The economy engine (`babylon-material-circuit`) writes a receipt for nearly
everything the first events need: a workplace that stops or restarts, hires and separations, a
market that cleared above its quote, a need that went unmet, a program or budget left unfunded,
goods lost on a route, machines installed and worn. It writes no receipt for a change of pay (the
pay fight adds it) or for a household moving home.

**What can come from outside.** The economy's close takes five typed inputs from outside it: aid, a
collection, an agency's attendance, a company's choice of portfolio, a workplace's standing. The
small worlds have two labelled shocks (a failed harvest, a power cut) that change a figure of a
recipe and never the state. Nothing removes stock, machines or capacity except loss on a route and
wear by use. Neither economy crate draws a random number.

**Chance and roles.** The rule language has `choose`: one per Mechanic rule, over a finite list with
exact weights, with a receipt that records what was drawn and what was not. Two rules use it. The
roles are enforced by a table of exact rows (`babylon-bsl/src/causal_contract.rs`): three intents,
three recognizers, and for external events nothing: "External events remain default-deny."

**The scene.** The small world in the client is an administrative view: its header reads "ADMIN ·
MATERIAL TRUTH · UNFOGGED". It shows figures, a list of struck shocks and a refusal banner, and no
news as text.

**Data.** The data trove holds no table of natural hazards. Checked 26 November: none of the
reference database's 82 tables is named for a hazard, and a reader found none in the trove's
folders.

## 5. The design

Rules are numbered E1 to E23. Words used as the earlier designs use them: a **record** is what a
period wrote, with its cause (A23). **News** is a record shown. An **event** is news your
organization could act on (PF15). An **occasion** is what an event gives an organization: a need or
a fight among people it can reach, for as long as it lasts (the pay fight's word). The **agenda** is
the list of events before your monthly meeting. A **ceremony** decides one item (porch 01). An
**act** is a practice of the registry, aimed. The **seal**, the **reckoning** and the **long tail**
are the answer's three layers (porch 01). The event's **page** is its page in the wiki.

### Part one: from the record to the agenda

**E1. An event is read from the record, and changes nothing.** A kind of event is declared as
content. The declaration names four things: the records it reads; its parties; the acts it offers,
with a line on what each means; and the words of its scene. A kind owns no chance and no effect: "An
event declaration owns no probability" (Amendment AJ). The first kinds, and what each is read from:

| Kind | Read from | Exists today |
|------|-----------|--------------|
| Work lost at a workplace | separations, a stop, a restart; `ReducedWork` | yes |
| A market short | a market cleared above its quote; a need unmet | yes |
| Relief or a public budget unpaid | a program's or budget's unfunded sum; the county's session | yes |
| Goods lost on a route | a freight loss; an aid run lost | yes (pauses play today) |
| The state's visit | City PD's notice | yes (a note today) |
| A hearing or a session called | the hearing's notice; the county's first session | yes (a note today) |
| A pay cut, a stoppage, an offer, a contract's end | the pay fight's records | with the pay fight |
| A burden from outside | the outside event's record (E18 to E20) | no |
| A loan not renewed, a business taken, a run, a rescue | the banks' records (ADR314, A7 to A13) | no |

**E2. An event names its parties from the record.** *The people hit*: a counted group, such as the
people of a workplace or the households of a place and band. Never one person: "the finest detail
that's still an aggregate" (porch 02). *The hand*: the actor whose act the record is: the employer
that cut the hours, the seller that raised the price, the fund that left relief unpaid, the lender
that took the business. This is what the Director's pick called "who the people there blame": the
nearest hand, the one a hurt household sees act on it. *The next link*: the cause the record names
for the hand's own act, if it names one. *The public body* with a duty to those people. *The
organizations present*: those with a body among the people hit. A storm's record has no hand. A
person is named only from the organization's own roster, or by a name minted when a loss or a
defection is recorded, as the peacetime design rules (R3).

**E3. One reading, two uses.** The occasions of a period are worked out once, inside the period's
adjudication, from committed records. Organizations that the engine runs decide on that list. The
player's agenda and an event's page are views: the same list, seen through the reports and
observations the organization holds and through public record. They have no store of their own, and
a replay makes them again. What an organization has earned is part of its own committed record, as
its reports are today. What the player has looked at, the setting of E6 and an item put on the
agenda by hand belong to the session and never enter the tick (the fog ruling of 18 July).

**E4. What reaches you.** The material layer is public record, so a material event is news for
everyone, with its public figures. The fact of each link of its chain is shown as the record has it;
its quantity is earned: "organizing buys the QUANTITY, not the FACT" (ADR182, R2). So a page shows
that the owner shut the plant, and that a cause stands behind the owner's act. How much was owed, to
which lender and why it was refused are private particulars, earned as today: by an agreement in
force, by an inquiry, by a contact. What is not known is shown as not known, with how to learn it.
The structure the game holds public from the first period stays public on every page: who employs
whom, who taxes and pays whom, and the imperial rent that reaches the place. A scene uses no
instrument that the organization's study has not yet unveiled (the Veil of Money, porch 01). This
design adds no rule on where a dossier lies; porch 02's rule stands.

**E5. What goes on your agenda.** No score decides it. Your *reach* is made of things that exist:
the households of your members and contributors; the workplaces, partners and venues you hold an
agreement with; the households a program of yours serves; the sessions where you hold a seat. An
event is put on the agenda of your next meeting when one of three things is true.

1. Its people or its place are within your reach, and it is the first event of its kind for those
   people, or a new kind of event on a page that is already open, or a larger one of its kind than
   any yet on that page.
2. It stops your standing work or a standing answer (E17): the "material interrupt" of ADR176 (22).
3. Another organization acts on yours: a visit, a summons, an offer.

Everything else is news. The ceremonies the porch sessions wrote (the offer, the audit, the lease
and the rest) keep their own triggers and their own words; this design does not touch them. Any
other record of the same kind for the same people is added to the open page with its count and its
age, and does not come back to the agenda: "first occurrence or escalation, never repeats" (the July
rule). An escalation is a new kind or a new largest, so no number has to be chosen. The player may
put any news item on the agenda by hand.

**E6. Whether an event stops play is the player's to set,** kind by kind: hold the ceremony and
stop; put it on the agenda without stopping; news only. The default is E5. Cases 2 and 3 of E5
always stop.

**E7. Never in the middle of a period.** The events of period N's close are decided at the meeting
of period N+1, before its seal, as its first items. "ceremonies never suspend mid-tick" (peacetime,
R2). In today's game the meeting is the organizer's one decision of the period, in the workspace:
this design builds on that and does not wait for the monthly meeting's four verbs.

### Part two: the ceremony

**E8. The four parts.** The trigger (the record, cited), the pane on the left (the scene in prose,
with countable facts only), the options side by side, and the seal. The title is the kind and the
place. The porch designs number their written ceremonies; an event's ceremony takes no number. The
seal is heard as well as seen, as porch 01 has it: "Music sting, popup closes, receipt stub". The
colour of rupture is kept for rupture, and is never the colour of an ordinary item (the July rule on
severity). In the scene a ceremony moves nothing on the screen: it is held between periods, outside
the three beats (ADR317, R13).

**E9. An option is an act.** Each option is one practice of the registry, aimed at one of the
event's parties, with its allocation: the same choice the workspace offers, already aimed. It is
admitted like any practice: previewed, then confirmed. The kind declares which acts it offers and at
whom, and one line on what each means. The preview supplies what it stakes. An option that would be
refused for want of hours, cash or standing is shown all the same, with the reason and the remedy
(the Standard, section 3). Up to four acts are laid side by side, in the kind's order. Every other
act of the workspace is one key away. "Carry on" is always there beside them, and is not one of the
four.

**E10. What an option says.** What it means, in a sentence or two. What it stakes: whose hours and
how many, cash and from which book, the supporter labor it needs, what it displaces, and what is
done in the open. Which mechanisms engage, in plain words (each household decides for itself; the
county pays by its own list). What is not known. For a fight, the pay fight's forecast (what a
stoppage costs each side a period, how long each can hold), written as the peacetime design writes a
larder, in a sentence with its condition: "The larder holds eleven periods, if nothing changes and
the price holds." A forecast is made only from what the organization has earned (ADR182). An option
never shows a percentage, odds, a score, a multiplier or a result.

**E11. One act, sealed.** One option is chosen in a ceremony. How much an organization can do in a
period is the practice rules' own bound, not this design's. Today that is one practice a period, so
the act chosen in a ceremony is the period's practice, and with two items on the agenda one of them
gets "Carry on". Under the monthly meeting the bound becomes cadre hours and cash, "not by slots"
(the combat design). Either way an answer displaces something: the standing work, a program's
staffing, or the other item. An item that got "Carry on" stays on its page, and while its occasion
lasts the player may bring it back to a later meeting. Known prices are debited at the seal. The act
is an intent of the next period (Article III).

### Part three: the others

**E12. Nothing waits for you.** Every organization with reach to the people hit has the same
occasion from the same close, through the same machinery (Article III). One that the engine runs
ranks its own acts by its own rule and funds them down its list under its own budget (ADR184).
Public bodies answer by their programs, as they already do. All of them decide for the next period
on the same records, in the pay fight's order: organizations in the order of their ids, yours among
them, then households. There is no branch for "the player passed": not acting is being absent from
the list of those who came. Where nobody organized is among the people squeezed, porch 02 already
says what happens: "every squeezed household defaults to the best offer *actually disbursed* in that
county", and it names the two that offer: the buffer that promises to restore the bribe through
public transfers, and the militias and posses.

**E13. An occasion has no timer.** A need lasts until somebody meets it, or the people leave, or
their own means cover it again. A fight lasts until it is won, lost or withdrawn. The ceremony says
how long in a sentence with its condition (about three periods of savings and benefit, if prices
hold), and the game enforces no countdown. The supporter labor that a crisis brings "surges during
crises and decays when idle" (porch 02): an occasion left alone loses the people it moved.

**E14. Who came is a record, not a score.** What an act leaves is what the registry writes for it: a
tie, a membership, a household served by a program, an agreement. Long memory lives in objects (the
combat design). The page lists who answered, with what, and what each gained among those people, in
things that can be counted: households served, members joined, a program opened. That is the pick's
"who acted and what they gained", as far as the organization can know it.

### Part four: the answer

**E15. The event's page holds the three layers.** *The seal*: the act you chose, what it staked,
what was not known. *The reckoning*, at the next close: the receipt of your act; what the people hit
did; what the hand did; who else answered, with what, and what each gained among those people (E14).
Story first, numbers under it; the three feeds tell it at the close, as porch 01 has it. *The long
tail*: later records that name the same cause, or that are the same parties' next acts, are filed on
the same page, each with the period it happened in and the period you learned of it. A page closes
when its occasion has ended and its tail has run. Where the pay fight applies, the tail is its
payer's six periods (PF17). A closed page stays in the wiki.

**E16. No mechanical why.** Porch 01: "the game never explains *why* mechanistically. It shows what
happened, who did what, what it cost. Causes are for the player to infer, argue about, and post."
A23, a month newer, has every record carry its cause. This design reads them together. A page links
acts and actors in the order the record gives them: the owner shut the plant after the bank did not
renew the loan. It never shows a formula, a weight or a share of blame, and it never says why an
actor chose as it did: that is the player's to work out. A quantity or a private particular that the
organization has not earned is a named unknown, with how to learn it.

### Part five: repetition

**E17. A standing answer.** After a kind of event has been answered once, the player may make that
act the standing answer for the kind, within stated bounds: which people, and up to how many hours
and how much cash a period. This is ADR176 (22): "declared deterministic verb repetition with
material interrupts". A standing answer is one act, admitted each time like any other; it is no
chain of acts ("verbs are atomic", the combat design). It stops, and the event comes back to the
agenda, when the act is refused, when a new kind of event reaches the organization for that page, or
when the organization learns that another has begun to answer the same people. All three are judged
on the organization's own receipts and observations, so a standing answer never tells the player
something the organization does not know. It is part of the organization's committed record, as
today's standing work is. Standing work is its first form: it already pauses when the hours are not
there.

### Part six: what comes from outside

**E18. One record, three sources.** A22 stands as ruled. An outside event is one kind of record,
filled from the world's state, from a calendar in the scenario, or from the campaign's seed. In the
rule language it is an ExternalEvent. This design gives the record its content: the burdens it may
carry (E19) and nature (E20). It writes no event for the first two sources. Two things that look
like outside events are not: a Crisis Bookmark changes only the first period's starting figures
(onboarding, R5), and elections run on their own statutory calendar (onboarding, R10).

**E19. An outside event carries burdens and nothing else.** ADR224 leaves external events with no
row at all, and says the gate that brings shocks "must extend the empty restricted-role allowance
tables through their own named mechanics and verification". These are the rows proposed. Each names
a place, a kind, a size and, where it lasts, a length. There are two sorts.

*A loss* destroys something once, at the close of the period it falls in, with its own receipt, as
loss on a route has today:

1. **Stock lost**: a share of the stored goods at the workplaces and shops of a place.
2. **Machines lost**: a share of what the machines of a place's workplaces have left to give.
3. **Homes lost**: a share of a place's homes, once homes exist (ADR315).

*A strain* changes a figure for a time and is then lifted, as the scene's labelled shocks do today:

4. **A route cut**: a stage of a route carries less, or loses more, for some periods or until it is
   repaired.
5. **A yield cut**: a recipe makes less per batch for some periods (the harvest; power).
6. **A need raised**: the households of a place need more of a good for some periods.
7. **Hours kept away**: the hours that can be attended in a place are capped for some periods.

No row writes a layoff, a shortage, a price, a death, a move, an outlook or a failure. Those "must
emerge through the shared systems" (Article III). A storm therefore kills nobody by its own record.

**E20. Nature is drawn once, when the campaign is made.** A22's words are "drawn once from the
campaign's seed, so that the same seed replays the same history". When a campaign is made, the seed
fills the outside-event record with all of that campaign's weather: for each event its period, its
kind, the places it strikes, how heavy it is, and its burdens. In play each arrives as a dated
outside event of its period. Nothing is drawn inside a period.

This is the only reading that the present law allows. Amendment AJ gives chance no seat in an
outside event. ADR224 forbids a shock to "regain mechanic authority by relabeling itself", so a
hazard cannot be dressed as a Mechanic. ADR248 authorizes no "stochastic shock" and wants "one joint
kernel" for one shared cause, and a hurricane over forty places is one cause. Drawn once, a storm is
one event with its footprint, and the period's adjudication stays free of chance. A seeded set-up of
a campaign is already ruled for its opening figures (onboarding, R6).

It also serves play. Every branch of a campaign's timeline meets the same weather, so "what if we
had been ready before the flood" compares like with like (Article III wants outcomes that "respond
to counterfactual play"). The record is the engine's truth. The player never sees it, and the game
offers no forecast of it.

- *Kinds:* flood, hurricane, tornado, severe storm, ice and winter storm, heat wave, drought,
  wildfire, earthquake.
- *What each may carry* (a designed mapping, declared as such):

| Kind | Losses | Strains |
|------|--------|---------|
| Tornado; severe storm | stock, machines, homes | a route cut |
| Flood; hurricane | stock, machines, homes | a route cut, a yield cut (power), hours kept away |
| Ice and winter storm | none | a yield cut (power), a route cut, hours kept away |
| Heat wave | none | a need raised (power), hours kept away |
| Drought | none | a yield cut (the harvest) |
| Wildfire | stock, machines, homes | hours kept away |
| Earthquake | stock, machines, homes | a route cut, a yield cut |

- *The one dial:* a figure of the scenario multiplies every kind's rate when the record is filled.
  At its opening value the rates are the real ones.
- *The table:* for each of the 187 places, each kind and each of two severities: a yearly rate, the
  places one event of that kind strikes together, and the share each burden takes. A yearly rate is
  spread over the thirteen periods of a year (Amendment AK asks that a rate be stated in periods).
  The rates are Observed. The shares are Derived from the source's own loss figures where it has
  them. The severities, the mapping above and the dial are Designed. The source proposed is the
  federal National Risk Index, which is public and gives a yearly frequency for each county and
  hazard; the plan checks it before anything is fetched. The trove holds no such table today.
- *The filling:* a declared, deterministic procedure with three inputs: the seed, the table, the
  dial. Its output is part of the campaign's opening and carries a digest. The same three inputs
  give the same record.

**E21. Repair.** Machines are replaced by their owner's own investment rule, which exists. A cut
route is repaired as a public work: the place's public body buys the materials and the hours from
its budget, and the cut lasts until that is paid. A public body that cannot pay leaves the route
cut, and that is an event of the kind "a public budget unpaid". This says nothing on how a stopped
public provider reopens: ADR325 keeps "A public body's own restart" for "a later design". Homes come
with the housing design.

**E22. The shipped scenario carries no authored date.** In the national scenario every outside event
is nature's, filled from the seed. The calendar and the state-fired source stay in the record for
scenario authors and for the benchmark of ADR250, whose shocks are "a historical shock envelope".
The October onboarding design ruled "zero scripted shock schedules", on the premise that "executable
shocks remain absent". A22 and the Director's pick of 26 November are newer and set that premise
aside for nature. What this design keeps of the October rule is that nobody writes a date into the
shipped game.

### Part seven: panic

**E23. A panic is a chain, not a kind.** Nothing fires a panic and no number defines one. When the
banks of ADR314 are built, four kinds of event read their records: a loan not renewed, a business
taken by its lender (A11), depositors leaving a bank (A12), and a rescue with its sum and its terms
(A13). A panic is those events filed on one page because each names the one before as its cause. The
feeds may call it a panic. Shares, bonds and land titles with prices come later, as agreed on 20
November; a fall in their price then reaches the same chain through what was pledged for loans.

### The ceremony as a decision surface

Article VII asks every gameplay surface for a contract. The ceremony's:

- *Decision question:* "This happened to people within our reach. What does our organization do
  about it this period, if anything?"
- *Visible signals:* the record's countable facts, the parties, who else is present, each act's
  stake. *Uncertainty:* the links of the chain not yet earned, the magnitudes not yet earned, what
  the people hit will decide, what the others will do.
- *Knowledge and fog:* E4, enforced where the agenda is made, not in the client.
- *Available actions:* the acts offered; carry on; set a standing answer; open the workspace and the
  screens.
- *Expected receipts:* the seal, the act's receipt at the next close, the event's page.
- *Archive subjects:* the event's page, the workplace, the place, the organizations named, the
  practice's receipt.
- *Exempt as an administrative view:* no. The scene's version of the ceremony is exempt and says so
  on its face, and cannot meet a gameplay milestone.

## 6. The line

- **The default is reaction.** Porch 02 says what squeezed households do when nobody organized is
  among them, and calls it a matter of starting conditions. This design gives no act a reward of its
  own. What aid brings is what the other designs say it brings. Run as a service it makes no cadre:
  the peacetime design's kitchen in service mode "converts **`0` beneficiaries into `Cadre
  Labor`**". It frees supporter labor, and in the pay fight what a fund paid a household counts when
  that household weighs joining (PF8). A raft counts as proven only after it "survived a State raid
  or militia attack and rebuilt" (porch 02). So an event can bring supporters and members. It builds
  no cadre and no proven raft by being answered.
- **Relief is not neutral.** The first default porch 02 names is the buffer "promising to restore
  the imperial bribe via municipal/federal transfers". When a county answers an event, that is what
  its answer is, and the page says what was paid and from which fund. ADR184 lets imperial rent fund
  the state's capacity, and ADR182 keeps the imperial-rent structure public from the first period. A
  page links the hours ledger of the people hit (ADR322), which is where the bribe shows. It adds no
  reading of its own: the game "never editorializes mid-run" (the Standard).
- **Whose hand.** A page names the hand the record names. That "organizing shows the chain, and
  reaction names the nearest hand" is a direction the Director gave on 23 November (recorded in
  ADR322 as a direction, not a design). What a hurt household comes to think caused its hurt is its
  outlook, and nothing here writes an outlook. This design supplies only the record: who acted on
  them, and who came. The rest is the outlook's own design, and the Director's to rule.
- **A storm has no hand, and that is not the whole truth of a disaster.** Three things this design
  does not settle, and says so. Who rebuilds, who is paid first and whose budget is cut are acts of
  owners and public bodies, filed on the storm's page like any other act. A burden falls on "a share
  of a place's homes" with no regard to whose homes stand where, though floods and heat fall hardest
  on the poor and on oppressed nations: that belongs to the design of homes and nations, and is the
  Director's. And the rates are the past's: nothing the world does to its land changes its weather
  here. A disaster that the world brings on itself is an event fired by the world's state, A22's
  first source, and belongs to the design of the ecological metabolism.
- **No win is promised.** "It cannot make anyone stop, go back or join" (PF10). "A fight you cannot
  win is yours to start" (PF16). No option is hidden because it cannot succeed.
- **Who answers when you do not.** The county, a church, a union, a landlord, the buffer, a militia.
  Each has its own line and its own rule of decision, and each needs its own design. For reactionary
  cells and opportunists the research briefs 20 and 21 are briefings, not rulings. ADR208 records as
  the Director's standing direction that "fascism is parameter values on shared faction machinery,
  never a special-cased code path". Nothing here gives any of them a script.

## 7. What it does not do

- It adds no act. Strike, blockade, occupation, negotiation and the rest come with their own
  designs, and an event offers them from the day they exist.
- It does not design the monthly meeting's four verbs, the Line and Doctrine screen, the voices of
  the three feeds, repression, combat or elections.
- It writes nothing about outlook or consciousness.
- It gives no organization that the engine runs a line or a rule of decision. It gives them the same
  occasions as the player.
- It builds no bank, loan or share.
- It lets nothing from outside write a death, a move or a failure.
- It writes no dated world event and no event fired by the world's state: tariffs, wars and a
  pandemic keep their own designs.
- It does not change where a dossier lies.

## 8. What would make it a failure

- One option is plainly the best. Then the item is a standing answer and should never have been a
  ceremony.
- The game stops too often, or twice for the same thing.
- A ceremony reads like a spreadsheet: the player can rank its options by a number.
- A page whose reckoning says nothing: an act with no consequence that can be read.
- An event that writes its own sequel: a storm that lays people off.
- The client makes the agenda: a scripted play and the window disagree, or a figure the organization
  has not earned reaches the client.
- In the finished game, carrying on costs nothing, because nobody else ever comes.
- A kind of event with no road to the real game.

## 9. Approaches

Three shapes were put to the Director on 26 November.

1. **A card with aimed plays. Picked.** As built here it is the porch's ceremony. The scene and the
   line on what each option means are written for the kind. The options themselves are acts of the
   registry, and the outcome is nobody's to write.
2. **The verb plate only.** Events would be news that changes what the acts can do, with no
   ceremony. It is the purest form of "the sandbox is the game". It leaves a new player to find
   every occasion alone, and the porch sessions rule a ceremony for the moment of decision.
3. **Options written for each event,** with their effects, as in Paradox games. Article III rules
   out written effects. What that shape does well is kept in the first: a scene with a voice, and
   options that read as choices of meaning.

Two choices of construction, the lead's.

- The agenda is made where the organization's view is made, in the runtime, and not in the client,
  where today's notices are made. Article VII wants fog enforced at the data, and a scripted play
  must see what the window sees.
- Nature is drawn once, when the campaign is made (E20), and not period by period. A draw inside
  each period would need three texts changed: Amendment AJ (chance in an outside event), ADR224 (a
  shock passing as a Mechanic) and ADR248 (a stochastic shock; draws that assert independence
  between places). The player sees no difference between the two. The first draft of this design had
  the draw inside the period; its one check found the conflict.

## 10. How we know it works

1. **The storm writes only its burdens.** Twin runs on one seed, with the record of outside events
   and with an empty one. An audit of direct writes lists every row an outside event wrote: only the
   seven of E19. Every other difference between the twins is downstream of them (Article VIII).
2. **Play changes the page.** One seed, one event, three runs: one act, another act, carry on. At
   the reckoning the three pages differ in recorded facts beyond the act's own receipt.
3. **Somebody else comes.** In the run that carries on, the page lists another answer wherever an
   organization with reach exists, and none where none exists. Until step 4 of the build the only
   others are public bodies and partners; the check is counted with them and again when the first
   organization that the engine runs arrives.
4. **One agenda for the window and the script.** A scripted play over the control socket reads the
   items the window shows. A test proves that a figure the organization has not earned is not in the
   bytes the client receives.
5. **Nothing to rank by.** A check over every scene and every line of meaning: no percentage, no
   multiplier, no score.
6. **Pace, counted.** Recorded campaigns count the stops by the game in a hundred years and the
   longest stretch without one. It is tuned by what counts as reach, by E5's rule on repeats and by
   standing answers, and by no coefficient (ADR176, 24).
7. **No two identical ceremonies in a row** (the July gate).
8. **The weather replays.** The same seed, table and dial give the same record of outside events,
   byte for byte, and every branch of a campaign meets it.
9. **The window is looked at.** The ceremony is driven in the real client, and its picture is shown
   to the Director beside porch 01's words before anything is built on it.
10. **Each kind names its road to the screen:** its line on the Ticker, its item on the agenda, its
    ceremony, its page.

## 11. Calls made here, for the Director to check

Each is the lead's, not the Director's, until they say so. The first six touch what the Director
picked or ruled, and come first.

1. **How the picks are met.** The pick's "who the people there blame" is the hand (E2). Its "who
   acted and what they gained among those people" is on the page, in things that can be counted
   (E14). Its "up to four plays" are up to four acts, with "Carry on" beside them (E9). "All nine
   verbs stay one key away" is every other act of the workspace, one key away: the code has a
   registry of practices, of which three run today, and no menu of nine verbs.
2. **An occasion has no timer (E13).** This departs from the words of the picks, which said the card
   shows "how long the chance lasts" and that "An opening lasts a few periods". What the player sees
   is the same: the card says how long it looks to be, and what would end it. What differs is that
   no number of periods is written for a kind: the occasion ends when the books say the need is met
   or the fight is over, sometimes sooner than it looked. A written number would be a constant of
   the sort the standing rules forbid. If the Director wants one all the same, it is theirs to say.
3. **Causes are shown as the record has them (E16).** Porch 01 says "Causes are for the player to
   infer". A23 says news is shown "with its cause". Read together here: the page links acts and
   actors in order, and never says why an actor chose as it did. If the Director reads porch 01 more
   strictly, the next link of E2, the filing by cause of E15 and the chain of E23 change.
4. **The fact is public, the quantity is earned (E4).** The direction of 23 November says that
   "organizing shows the chain". ADR182 rules that "organizing buys the QUANTITY, not the FACT". E4
   follows the ruling: a page shows that a cause stands behind an act, and organizing buys its
   particulars.
5. **Nature is drawn once, when the campaign is made (E20).** It is the lead's reading of A22's
   "drawn once", and the only one the present law allows. It still needs a governed decision: the
   allowance rows for the seven burdens (ADR224), and the seeded filling of the record, which sets
   aside the October premise that "executable shocks remain absent". Both are the Director's.
6. **The shipped scenario carries no authored date (E22).** The lead told the Director on 26
   November that their law ruled a calendar out; A22 admits one. This call keeps the calendar in the
   record and out of the shipped game. It is the Director's to overturn.
7. The word is "occasion", not "opening".
8. An event kind's scene and lines of meaning are written; its options are acts of the registry
   aimed at its parties; no outcome is written (E9). When the Line and Doctrine screen exists, the
   organization's line may order the options. It never hides one.
9. One act a ceremony. How many acts a period allows is the practice rules' bound, not this design's
   (E11).
10. Reach, and the three cases of E5, decide what stops play. No score, and no number: an escalation
    is a new kind or a new largest.
11. The player may change, kind by kind, whether an event stops play (E6).
12. The seven burdens of E19 are the whole of what an outside event may write.
13. A storm kills nobody by its own record. Article III says so; if the Director wants a disaster's
    deaths written, that is a change to the Constitution and not to this design.
14. Nature's kinds, its two severities, and which burdens each kind may carry (E20). All Designed.
    The National Risk Index as the table's source, to be checked when the plan is written.
15. A burden takes a share of a place's homes or stock with no regard to whose they are (section 6).
    It is stated, not defended.
16. Repair of a route is a public work with a bill (E21). It does not touch how a public provider
    reopens.
17. A panic is a chain of events on one page, defined by no number (E23).
18. The Standard's pacing gates were written when a tick was a week. Read in calendar time: the game
    stops for an event at most 150 times in a hundred years. This design is counted against that.
    The Standard's other gate, a decision in every twenty weeks, belongs to the monthly meeting's
    own verbs.
19. The scene's ceremony is an administrative view, with everything known, and says so on its face.
20. This design asks for no change in the order of work, and does not say when the outside-event
    record is built (section 12).

## 12. Build order

The order the Director ruled on 25 November stands (ADR325): the country's numbers, then the pay
fight's first part, then "the game's own turn carries the rules, so that a campaign runs, saves and
shows them". "Its first decision for the player is the pay fight." Banks, homes and nations "are
designed and come after it". This design attaches to that order and asks for no change in it.

1. **With the pay fight's first part** (ruled next): nothing new. Its news, with a cause for each
   item, is this design's record in the scene.
2. **With the pay fight's second part** (P2-1 and P2-7, at the Director's word after the first
   part's count is read): the event in the scene takes this design's form: the agenda, the ceremony
   with your organization's acts as its options (back it, widen it, or let it be: F5), the seal, and
   the page with its reckoning and long tail. An administrative view. Its road to the real game is
   step 3.
3. **With the game's own turn** (stage 4b, where the records are carried once): the occasions of a
   period; the agenda in the organization's view; the ceremony as a declared gameplay surface in the
   organizer's workspace; the event's page in the Archive; the standing answer, grown from standing
   work; the rule on repeats; the player's setting of what stops play. Its first ceremonies are the
   pay fight's, as ADR325 has it, and the notices the game has today take the same form (work lost
   at a workplace under agreement, an aid run lost, City PD's visit, the hearing's notice, relief
   unpaid at the county's session). The bound stays one practice a period. The others who answer are
   the ones that exist: the county by its list, the partners by their fixed policies, City PD.
   Proved by a scripted play in the real client and a look at the window.
4. **Organizations that the engine runs** take occasions by their own rules in the campaign when
   their own designs arrive (player agency, the gate after the circuit in ADR250); more acts
   likewise. The scene has its first such organization earlier, a union, from the pay fight's second
   part (P2-6).
5. **With the outside-event record:** its three sources, the seven burdens with their receipts and
   their allowance rows, nature with its table, its filling and its dial, and repair as a public
   work. When the record itself is built is not this design's to say, and the ruled texts differ:
   the adjust design builds "Outside events and the pushes of organized people (A22) ... with piece
   3", which is work and pay; ADR250 needs the rows by its benchmark, the gate after player agency.
   That order is the Director's.
6. **With the banks** (ADR314, A7 to A13), which ADR325 puts after this branch: the four kinds of
   credit event, and the rescue's ceremony.

This design gets no plan of its own now. Each step is planned with the work it attaches to.

## 13. Left to the plan

Where the reading of occasions sits in the period, and whether a kind is a Recognizer rule or is
read beside the economy's close. The types and their names. The words of each scene. The table's
build and its exact shares. The procedure that fills nature's record. Which figures of the catalog
each strain moves. How a page is linked from the records. The keys.
