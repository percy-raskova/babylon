# Field and particles: how the economy, homes and nations are drawn

**Status:** approved by the Director on 2026-11-21, by dialog, with rulings 17 to 21 written in.
The decision record is ADR317. The build plans follow this document.
**Date:** 2026-11-21.
**Sketch:** a moving page with invented numbers, shown to the Director on 2026-11-21. It is not the
client and is kept outside the repository.
**Behind every "today" in this document:** the findings of six readers of the code, 2026-11-21,
kept with the session's notes, and one outside check of this draft.

## 1. What this is, and why

The client shows the country as a map of counties raised by one number at a time. It cannot show
what the game is about: whose work goes where, who is fed by it, and who stands together.

This design draws the same households three ways, with the same three things moving through all
of them.

- **On the land.** The country as ground. Work, goods and money move across it.
- **By their ties.** The same households set between the bodies that employ them and hold claims
  on them, with every set that belongs together drawn around its members.
- **In the wells.** The same households placed by the world view that holds them.

The Director's words for it: "a gravitational field and its effect on particles (acting units)",
"hypergraphs and graph theory with the geography as an index", and, of the first sketch, "exactly
what i envision", missing only "the flow of value in accumulated labor hours through the
production process, money, labor-time, and they're relation in all three of those ways".

It is for the player, who is an organizer. The first build is the unhidden view, so that every
shape can be checked against the engine. The player's view comes after and is designed here only
as a rule.

## 2. What is already ruled

### 2.1 The Director's answers of 2026-11-21

| # | Ruling |
| --- | --- |
| 1 | Hours and money are two streams. There is no rate between them, ever. The Director's note: "it should be place by place, and how these things aggregate is how we want to group-by or visualize them so to speak". |
| 2 | Living labor time is bone white. Work stored in goods is crimson. Money is gold and runs against both. |
| 3 | The wells are a reading of real numbers, worked out for display. The engine is not touched. |
| 4 | A particle is a household group. Employers and holders of claims are bodies. Classes and nations are drawn around particles, never as particles. |
| 5 | Groupings: by place, by class and home, by nation, by workplace and company. Each shows hours and money side by side. |
| 6 | The July map rules are amended, so the county map itself may bend and flow. |
| 7 | The September fence is lifted. Build as soon as the economy build frees the machine. |
| 8 | The first scene with real numbers is the whole country. |
| 9 | Height is hours. Colour is money. |
| 10 | Both surfaces, with a switch: one bending surface, and blocks that rise and sink. |
| 11 | Nothing is hidden in the first build. The player's view is the next step. |
| 12 | National liberation is a fourth well. (Open again: see 6.8.) |
| 13 | Three beats a period: work goes in, goods move through, money comes back. Nothing else moves except what the player touches. |
| 14 | What the four wells are was open for brainstorming. Settled by ruling 19. |
| 15 | The new reading is the map's default. The other lenses stay and can raise and colour the same ground. Flows can show over any of them. |
| 16 | The integration for Bevy is a crate in the public library's repository: general parts only, nothing of the game. Same Bevy version as the game. |
| 17 | Work given is only the hours that went into goods and services. Idle hours on the clock are drawn apart and have their own column. |
| 18 | Hours never measured: the height is drawn from the first period and the scene says so. Goods with unmeasured hours are drawn hollow, never as zero, and a standing line counts them. The engine is not changed. |
| 19 | The wells have four corners, as a reading: REVOLUTIONARY and NATIONAL LIBERATION at the top, LIBERAL and FASCIST at the base. The engine keeps its three shares and August stands. Both top corners are the revolutionary side. |
| 20 | Asked again with the true count of household groups (15,696, not "about 3,000"): the whole country still comes first. |
| 21 | A place's height is measured against the whole world, not against the country alone. |

Rulings 17 to 21 were given by dialog on the evening of 2026-11-21, with the approval of this
design. In the same dialog the Director kept every call listed in section 13.

### 2.2 The August rulings that bind the wells

Spec 034 and ADR204 (twelve rulings, 2026-08-14) already say how ideology is represented.

- One representation: a three-way share (revolutionary, liberal, fascist) that sums to one. "The
  one canonical representation ... nothing in spec 034's frame is re-opened." Every other surface
  is a reading of it.
- Its picture is a triangle. The base runs from liberal to fascist: "two tactical faces" of one
  order. "Height above the base" is revolutionary and is "the only axis of qualitative change".
- The share is worked out, never set: from which organizations are active among a population.
  "Unorganized population defaults to liberal."
- A community (each nation among them) has its own point in the triangle, and a floor from its
  history of resistance that outlasts any organization.
- "An ideology is like a gravitational pull that commands labor viz a viz hegemony."
- Organizations carry lines. Populations carry shares.
- Reserved to the Director: the names and content of the poles, the floor values, any collapse of
  the share to one number.

## 3. What exists today

**The client.** Bevy 0.20.0 on Rust 1.99.1. One perspective camera that orbits. Each of the 3,144
counties is its own entity with its own mesh and its own material: about 6,300 meshes and
materials. Height is the entity's scale. Colour is the material's base colour. One system sets
both at once when the period or the lens changes. Nothing is eased. Five lenses, one enum,
matched in at least eight files. Ribbons and networks are meshes that are torn down and rebuilt
whole on every change. There is no particle crate and no 3D shader. The slowest measured frames
(RTX 3060, 300-frame windows, 95th percentile): money map 15.4 ms at 1366x768 and 18.4 ms at
1920x1080. No measurement names the whole-country map.

**What the client is sent.** It reads PostgreSQL itself, read-only, through views. A separate
process publishes money and labor facts after each period. The client then asks for one selected
county at a time, twenty rows a page. Every such read is for the unhidden observer only. No read
exists for household groups, hyperedges or memberships. Adding a view changes the database's
identity, and a runtime refuses any identity but its own.

**What the engine records.** Every attended hour, exact, never derived from wages. Hours follow
goods through stock, freight and equipment to their last use, under one law: opening hours plus
direct work equal closing hours plus what left. Every payment, by kind, with both ends. Hours and
money share only the period and the owner; a movement of hours has no price and a payment has no
hours. The recorder runs for the whole country: 7,463 workplaces, 99 companies and 15,696 household
groups. A household group is one kind of household in one county. There are five kinds: with an
earner or without, owner or not, and collective residences. A sixth, pooled, kind stands for
residents abroad. Per period: about 40,000 movements of hours and 35,000 payments.

Four gaps matter here.

1. **A worker's household is dropped.** The receipt names it; the record of attendance does not
   keep it. So "whose hours went to which workplace" cannot be summed today.
2. **A household's hours are not published.** They exist only while a period is being worked
   out, not in the database.
3. **Detail lasts 13 periods.** After that only totals remain.
4. **Opening stock has no measured hours.** It carries a flag, "unknown", that follows it into
   everything made with it. Equipment lasts 100 periods, so the flag stays for years. Recorded
   hours are a lower bound that grows.

There is no rent, interest, bank, home or nation in any record yet. Those come with the build
that ADR314 and ADR315 describe.

**The library.** A pure Rust workspace, public, at Rust 1.90 or newer, with its own gates. It
lays out hypergraphs in 2D, draws a convex hull around a set, and can read the number on a
membership. It has no weighted outline, no hull that is not convex, no layout with fixed points,
and nothing for Bevy.

**The world-view share.** Built as rules for classes and communities, loaded only by test worlds.
The country loads none of it. It has no solidarity ties, no wages by class, no nations and no
lines on its five or six organizations. The guard that must ship before any such wiring (an
oppressed nation's own bourgeois nationalism) is not built.

## 4. Goals

**Goals.**

1. Show, each period, where work goes, where it comes back as goods, where money goes, and how
   the two differ, for the whole country at once.
2. Never turn hours into money or money into hours, on screen or in code.
3. Let any figure be regrouped: by place, by class and home, by nation, by workplace and company.
4. Draw sets (a nation, an organization's members) as bodies around their members.
5. Put the general parts in the public library, usable without the game.
6. Draw only what the engine records. What it does not record shows as missing.

**Not goals.**

- No change to any rule of the simulation. This reads records.
- No world-view share for the country. That is its own piece of work on the theory line.
- No player's (hidden) view in the first build.
- No rent, debt or nation records. This draws them when the economy build makes them.

**What would make it a failure even if it runs.**

- A picture that moves because moving looks good. Every mark must be an amount from the records.
- A rate between hours and money appearing anywhere, even as a helper.
- A shape that lets a count be read which the player has not earned (once the player's view
  exists).
- A set drawn as a dot with spokes.
- A scene so heavy that the map is slower than today.

## 5. Approaches

**A. Grow the map in place.** Add the new reading as a sixth lens. Let the county blocks sink.
Draw flows the way ribbons are drawn today. Leave ties and wells to separate screens later.
It is the least new structure. But every county is its own entity and material, lenses are
matched in eight files, and overlays are rebuilt whole on every change. Two readings at once,
easing, three beats and thousands of moving marks all fight that structure. The three
arrangements could not share their particles, and little of it would be general enough for the
library.

**B. One field scene, three arrangements.** A new scene beside the map: one surface for the
country, particles for household groups, marks for the three streams, and outlines from the
library. The same particles move between the three arrangements. The old lenses are carried onto
the new ground one at a time, and the old map of separate blocks is retired when every lens has
moved.
It is what the sketch shows and what the Director confirmed. It costs a new scene and a move of
the old lenses.

**C. Everything in shaders.** Height, colour, marks and outlines all worked out on the graphics
card.
It is the cheapest per frame. But it is the part of Bevy that changes most between versions, the
library must follow Bevy's newest by standing rule, it is hard to test without a screen, and the
country is small: 3,144 counties, about 16,000 groups, a few tens of thousands of marks.

**Chosen: B**, built with ordinary meshes. One exception is allowed: the moving marks may be
drawn by one small shader that moves them along their paths by a clock, if a measured trial
shows that plain batched marks miss the frame time (see 11).

## 6. The design

### 6.1 Three arrangements of the same things

Four kinds of thing are on screen in every arrangement.

| Thing | What it is | In the records today? |
| --- | --- | --- |
| Particle | One household group: one household node of the country (15,696 today, more after the economy build). | Yes. |
| Body | An employer, or a holder of claims: a workplace, a company, a public account; later a landlord's holding and a bank. | Workplaces, companies, public accounts: yes. The rest: after the build. |
| Set | A native hyperedge, drawn around its members: an organization's body today; a nation after the build. | Organizations: yes, five or six, but see below. Nations: after the build. |
| Mark | A fixed amount of one stream, moving once along one path. | Yes (6.2). |

**Who is inside an organization today.** An organization's body holds the organization and three
or four bodies of participants. It holds no household group yet. So a body of participants is
drawn as a particle of its own kind (a ring, not a dot), standing in its county, and the
membrane goes around those. Household groups join a membrane when memberships carry a value
(issue 653) and the County Review writes them. This is my call.

**Size.** The scene is built to hold 25,000 particles. Nothing in it may grow with the square of
their number.

An arrangement only says where particles and bodies stand. Changing arrangement moves them; it
never changes what they are. Selection, the inspector and the side-by-side table (6.5) stay the
same across all three.

### 6.2 What moves

| Mark | Stands for | From, to | Source in the records |
| --- | --- | --- | --- |
| Bone dot | A fixed number of hours of work that went into goods and services (ruling 17). An idle hour is a hollow dot. | A household group to the place where it worked. | The household's hours, and attendance. Needs gaps 1 and 2 closed. |
| Crimson square | A fixed number of recorded hours, stored in goods or in a service. | Workplace to workplace along the goods' own path, then to the household that takes them. What stays in production does not leave it. | Movements of hours between positions. Built, 13 periods deep. |
| Gold streak | A fixed amount of money. | Payer to payee, by kind of payment. It runs against the goods and against the work. | Payments. Built. |

- The amount one mark stands for is fixed for a session and printed on screen. One for hours,
  one for money. They are two scales and no line of code relates them.
- Marks are summed along a path before they are drawn. On the whole country a path joins two
  counties. Paths are drawn in order of size until 95 of every 100 units of each stream are
  shown. The rest is printed as one figure, "not drawn", never dropped in silence.
- **Which hours are "work given" (ruling 17).** The record of attendance splits a worker's
  hours: production, upkeep, handling, fitting equipment, and idle. Only the first four enter
  goods and services, and only they count as given. They set the height and they are the dots
  that enter a workplace. Idle hours are their own dots, hollow, which reach the workplace and
  stop at its edge, and they have their own column in the table. So what is given and what comes
  back are the same kind of hour, and time bought and not used is seen, not hidden. Work a
  household does outside a workplace that the record counts as direct (collecting for an
  organization, work for an agency) counts as given, to that body.
- **Unknown hours (ruling 18).** Goods from opening stock carry recorded hours of zero and the
  flag "unknown". A full crimson square is drawn only for recorded hours. A path whose goods
  carry the flag gets a hollow square, which stands for goods and for no number of hours, and the
  count is shown beside the stream ("of these goods, N movements carry hours never measured").
  Nothing unknown is drawn as zero and nothing is guessed.

### 6.3 On the land

**The ground is the county map.** County outlines never move in plan. Two forms, with a switch:
one continuous surface that bends, and one block per county that may sink below the ground as
well as rise.

**Height is hours.** For each place, each period:

- *given*: hours of work its households gave (6.2 says which hours count);
- *back*: recorded hours in the goods and services that reached its households (each hour
  counted once, when it reaches a household).

The world as a whole always gets back less than it gives, because production keeps part of
every hour in stock and equipment. So the plain difference would make almost every place a hill.
The height is therefore measured against the whole world (ruling 21):

> short or ahead = back − (world's back ÷ world's given) × given

- The world is every place the record holds, at home and abroad.
- A place that is short stands high. A place that is ahead lies low.
- Summed over the world it is zero. Summed over the United States it is whatever the record
  shows, and that figure is printed: the country as a whole can be seen drawing hours from
  abroad, or giving them. No rate between hours and money is used anywhere.
- It is a number of hours, so it is a mass, which the map rules send to shape.
- Places abroad stand on the rail (below) and carry their own figure there.
- The reading against the country alone, which the tension lens uses, was offered and not
  chosen. The tension lens keeps its own ratio and its own legend.

**Unknown hours and the height (ruling 18).** Hours in opening stock and opening equipment were
never measured. Wear passes that gap into everything made with old equipment, for up to 100
periods. Goods from abroad may carry the same gap. Measuring against the world's share removes
the gap from the world as a whole, but not between places: a place fed from older plant will look
short for a reason that is not about whose work went where. So the scene shows it and says so.
The height uses recorded hours from the first period. A standing line gives, for the world, the
country and the place in hand, how many of every hundred movements of goods still carry hours
never measured. The picture grows truer as old stock and plant are used up, and it never claims
more than the record holds. Two other ways were offered and not chosen: holding a place's height
back until most of what reaches it is measured, and giving opening stock the hours its recipe
takes today.

**Parties with no place.** A company's treasury, a national account and anything abroad have no
county. They stand as named bodies on a rail along the map's edge. Marks run to and from the
rail. A place's colour counts money to and from them as money that left or arrived. How the
world's parts are drawn (core, rivals, periphery) gets its own design when the build of borders
lands. This is my call, and the Director kept it.

**Colour is money.** For each place: money that reached it from outside, against money that left
it, as a share of both together. It runs from crimson (pays out) to gold (takes in), the same
ramp as the tension lens. The existing county reading already gives inflow, outflow and money
that stayed inside.

- Both scales are fixed for a session. Neither is rescaled between periods.
- Large fills stay muted. Full crimson and gold are kept for marks.
- Crimson and gold differ in lightness as well as hue, so the reading does not rest on hue alone.
- **Before anything is measured**, back is zero everywhere and the ground is flat. It grows in as
  recorded production reaches households. A standing line says so.
- A place with no households, or with no record, is gray and at rest. Gray means "no reading",
  as it does in the client today. Zero means a measured zero.

**Work stored in production.** Where recorded hours stay in a workplace's stock and equipment at
the end of a period, the ground under it sinks by that amount, on the same scale as the height.
It deepens only as the record shows hours staying. This is the Director's "accumulated labor
hours", drawn as what it is.

**The other lenses.** Each existing lens gives one number per county. On the new ground it sets
height and colour together, as it does today. The new reading is the default. Flows may be
switched on over any lens.

### 6.4 Three beats a period

When a period's records arrive, the scene plays once:

1. **Work goes in.** Bone dots, from households to where they worked.
2. **Goods move through.** Crimson squares, along the goods' path and out to households.
3. **Money comes back.** Gold streaks, against both.

Then it rests on a still frame. Heights and colours ease to their new values during the third
beat and are still afterwards. A control plays the period again. Nothing drifts, shakes or pulses
between periods. With reduced motion the three beats are three still frames, each with its paths
drawn as lines.

(The sketch still shakes its particles with the squeeze. That predates ruling 13 and is not in
this design. A squeezed group is marked, not moved.)

### 6.5 Hours and money, side by side

One table, always at hand, with four columns: work given, stored work got back, money in, money
out. Two scales of bars, hours and money, never one. It can be grouped:

| Grouping | Rows | Ready when |
| --- | --- | --- |
| By place | County, then state, then country. | First build. |
| By workplace and company | Workplace, company, industry. Here the columns are hours that reach it, stored work sent on, money in, money out. | First build. |
| By class and home | Owner or not, earner or not; income band; tenant, owner with a mortgage, owner without. | Owner or not, earner or not: first build (the household kinds carry it). Bands: with the household units. Mortgages and tenants: with the homes build. |
| By nation | Each nation, and "in none". A group counts toward a nation by the number on its membership. Overlap is shown, never netted. | With the nations (ADR315) and memberships that carry a value (issue 653). |
| By world view | Each corner (6.8). | With the wells. |

A sum is always the sum of the rows' own figures. A ratio, where one is shown, is the ratio of
two sums in the same unit. A grouping that is not ready is shown as not ready, by name.

"By world view" is my addition. It is the August line about a pull that commands labor, read as
a table.

### 6.6 What is a body at which distance

- **The whole country.** The place is the body. Work marks end in the county where the work was
  done. No single workplace is drawn. Companies appear in the table, not on the ground.
- **A state or a region.** The largest workplaces of each county appear as bodies with two rings:
  a dashed bone ring for the hours that reach them, a gold ring for the money. The rings are
  never merged.
- **A county.** Every workplace is a body. Household groups are single particles. This is where
  Wayne's single households will appear after the household units are built.

On the land a household group stands at a fixed spot inside its county: each kind of household
always in the same place around the county's centre, so the same kind is found in the same place
everywhere.

Distance changes what is summed, never what is true: a path between two counties is the sum of
the paths between their workplaces and households.

### 6.7 By their ties

- **Where a particle stands.** Bodies are fixed anchors: holders of claims along the top,
  production along the bottom. A particle stands between its employers and whoever holds a claim
  on it, nearer the larger share of its income. Particles that would overlap are spread by a
  fixed number of steps in a fixed order.
- **It is a measurement, not a simulation.** No force acts over time. The same records give the
  same picture on every machine. Positions change once a period, eased, and never between.
- **Sets.** A native hyperedge is a hatched membrane around its members, thicker where the
  number on the membership is larger: one member a ring, two a capsule, three or more a
  membrane. Where two sets overlap, both hatchings show. A set is never a dot with spokes.
- **A membership of zero is outside.** Every household group is a member of every nation from
  the opening, with a number that may be zero. The outline follows the numbers, not the bare
  membership. It is drawn around the smallest area that holds nine tenths of the set's people,
  and may be in several pieces. The share is stated on screen. This rule is my call.
- **Nations on the land.** Off until switched on. Then a nation is the same hatched outline,
  over the counties where its people live.
- **Groupings that are not hyperedges.** "All tenants of one landlord" or "everyone who owes the
  bank" are read from pairwise ties. They are drawn as plain outlines, in a different line, and
  named as groupings. Only a real hyperedge gets a membrane.
- **What is there on the first day.** Workplaces, companies, public accounts, and the five or six
  organizations with their members. Nations, landlords and banks appear as the economy build
  makes them.

### 6.8 In the wells

**The wells read the August share.** No second formula exists at display time. The engine keeps
its three shares: revolutionary, liberal, fascist.

**Four corners, as a reading (ruling 19).** REVOLUTIONARY and NATIONAL LIBERATION stand at the
top, LIBERAL and FASCIST at the base.

- A group's height is its revolutionary share, as in August.
- The top is one side drawn in two parts. How far a group stands toward NATIONAL LIBERATION is
  the part of its height that its nations carry, against the part its class carries. The scene
  reads two carriers the law already has: the class, and the community.
- The ridge between the two top corners is the united front.
- Both top corners are the revolutionary side. The picture must not read as two separate ends,
  and the legend says so.
- A particle stands at its own mix: all liberal stands on the liberal corner, half and half
  stands halfway. It is placed, not pulled.
- The base is drawn as one line from liberal to fascist. Moving along it changes which face
  rules. Moving up is the only real change. A period's move is drawn as a short tail, so
  "sideways" and "up" can be told apart.
- **What a corner weighs.** The hours of work and the money of the groups it holds, as two
  figures. The ground sinks at a corner by the hours it holds. This is "a pull that commands
  labor", measured.
- A nation is a hatched body around its people, wherever they stand.
- An organization is not a particle. It has a line, shown in the inspector.

Two other ways were offered and not chosen: three corners only, with a nation as a hatched body
and a floor; and a fourth world view in the engine, which would amend August. Nothing in the
engine changes.

**Until the share exists for the country,** this arrangement shows the triangle, empty, with the
line the client already carries: the country has "no nation, no solidarity and no consciousness"
yet. No particle is placed by a guess. Carrying the share onto the country is a separate piece of
work on the theory line, with its guard first, and is not part of this design.

### 6.9 What is hidden

The first build is the unhidden view and says so on screen, in the words ADR217 uses: "ADMIN ·
MATERIAL TRUTH · UNFOGGED". It cannot count toward a gameplay milestone.

The rule for the player's view, fixed now so that nothing has to be undone later: **every
position, size, thickness, depth and hit area is worked out only from what the player has been
shown.** The scene is handed its numbers; it never reaches for more. A number the player has not
earned is drawn as not known, never as zero and never as a smaller shape. Where the existence of
a tie is itself secret, nothing is drawn at all. Hiding is done before the numbers reach the
client, as ADR182 rules.

Proposed decision question for the player's view, for the Director to rule when that view is
designed: *"Where does this place's work go, who is fed by it, and where would organizing
bite?"*

## 7. The records it needs

| Need | Today | What is added |
| --- | --- | --- |
| Hours a household group gave | Worked out each period, not published. | Publish it, per household group and period. |
| Which workplace those hours went to | The receipt names the household; the record drops it. | Keep the household on the attendance record. Publish hours by household group and workplace. |
| Hours that reached a household in goods and services | Published as movements, 13 periods deep. | A sum per household group and period. |
| Hours held by a workplace at the period's end | Published as positions, 13 periods deep. | A sum per workplace and period. |
| Money in and out, by kind | Published as payments. Read for one county at a time. | A sum per household group, per workplace and per place, each period. |
| Paths for marks | Not summed. | For each stream: the sums between pairs of places, largest first, with the remainder. |
| A history longer than 13 periods | Totals only. | The sums above are small and are kept for every period. |
| Household groups, sets and memberships | Views exist. No reader. | A typed reader. |

Rules for this part.

- Sums are made where the facts are published, after a period commits, outside the tick. A world
  that asks for none of this gives the bytes it gave before.
- Hours stay exact micro-hours and money exact millionths, as decimal strings. No float, no rate.
- Each hour is counted once. Movements are successive postings of the same hours; the period's
  own law is the check: what the scene shows as given must equal the period's direct work.
- Every read is tied to the frame on screen, as today.
- New tables and views change the database's identity. Play databases made before it are refused
  afterwards. This lands together with the other changes of identity already planned (issue 653,
  stage 4b), so that it happens once.
- The publisher already runs over its storage limit for a period (76.6 MB against 40 MB). The new
  sums are a few thousand rows a period. Their size is measured and stated before they land.
- The reads are for the unhidden observer only, like every economic read today.

**The world's totals (ruling 21).** Hours given and hours back are summed over every location
the record holds, the foreign and dependency ones included, and each place abroad gets its own
figure. Where work abroad is not in the record of attendance, the goods it made are flagged as
never measured, and the standing line counts them (ruling 18).

## 8. Where the code lives

| Part | Home | Why |
| --- | --- | --- |
| Outline around weighted members; ring, capsule, membrane. Placement between fixed anchors. Placement by shares over corners. Spreading by fixed steps. | The library's core crate, no Bevy. | Pure geometry. Any user of the library can use it and test it without a screen. |
| Meshes for outlines. The hatching. Marks that move along paths by a clock. A plugin that keeps them in step with a hypergraph, and tells a change of membership from a change of number. An example program. | A new crate in the library's repository, on the game's Bevy version. | Ruling 16. General, public, nothing of the game. |
| The country's surface, bodies, particles, the three beats, the table, the inspector, the labels. | The game's client, a new scene. | It knows the game's records and words. |
| The sums and their readers. | The game's persistence crate and its publisher. | That is where facts are published today. |

For the library:

- The Bevy crate states its own lowest Rust version (Bevy's), so the core keeps 1.90.
- Its Bevy features are the smallest set that draws meshes. It builds in its own CI job.
- Its licences are added to the library's allow list by name, each one read first.
- When Bevy moves, the library follows at once (standing rule). The game then moves with it or
  stays on an older revision of the library until it does. Both are pinned by revision.
- The set of outline shapes becomes open to additions, so a new shape does not break users.
- Nothing is published to crates.io without asking.

## 9. Rules to amend

These are the Director's to approve. Approval of this design approves this list; each is then
recorded in one decision record, and the old text is marked as superseded, not erased.

| Rule today | Where | Proposed |
| --- | --- | --- |
| "Curvature is terrain, not decoration. Geometry deforms only when someone ACTS ... do not fake terrain from anything else." | Design Bible 11, law 4 | Height is a reading, never terrain. The ground may rise and sink by the measured quantity of the reading in force. Curvature stays held until it is live. |
| "Geometry never animates; claims do." "camera, projection, geometry identical pre/post switch" | Design Bible 2.2 | Camera and projection stay identical before and after a switch of lens. County outlines never move in plan. Height may change between periods and between readings, and is eased. |
| "One motion budget per tick. Only the principal contradiction pulses." | Design Bible 11, law 3 | One motion budget per period: three beats. Work goes in, goods move through, money comes back. Nothing else moves except what the player touches. With reduced motion, three still frames. |
| "One lens = one dominant variable = one legend. No blended heatmaps." | Design Bible 3.2 | A reading may pair two variables on two channels, height and colour, each with its own legend. Two variables are never blended in one channel. |
| "Extensive renders as stuff, intensive renders as color." | Design Bible 11, law 1 | Stands. Height carries a mass of hours; colour carries a share of money. Stated so the new reading is seen to obey it. |
| "no fake-3D" | Design Bible 6 | Stands for charts. The field is a real scene with a camera, not a chart drawn to look deep. |
| "no texture fills in data surfaces" | Design Bible 6 | Stands. Hatching marks sets, never the ground. |
| "v1.0 visual scope is the 2D county-map game with selective 3D moments (Patches the tutorial guide; the topology view)" | ADR186, Amendment AF (i) | Not amended. Read as: the land is the county map, which the client already raises in 3D; ties and wells are forms of the topology view. Recorded so. |
| "No universal faction, ideological gravity or large-scale renderer expansion before #831's result." | Issue 825 only | Lifted for this scene by the ruling of 2026-11-21. Issue 831 still judges the Wayne organizer scene. Recorded in the repository for the first time. |
| "stable positions across scalar-only ticks" | Issue 824 | For this scene a position is a measurement. It moves once a period, eased, and never between. |
| "every force on screen must map 1:1 to a named engine quantity"; absence is shown, not decorated | Issue 618 only | Stands, and is written into the repository as a rule of this scene. |

The same amendments reach four other places in the Design Bible that restate these rules: the
default lens named in sections 3.1, 8 and 9 (ruling 15); the marker colours of section 9b (ruling
2); the lens-switch gate of section 10 (the row on section 2.2); and the corollary on reduced
motion in section 11 (the row on law 3). ADR317 lists them. They were found when the record was
written, after the approval, and they follow from it.

One thing the readers found that this design does not settle: the client's map uses a blue and
yellow ramp and three typefaces that the palette and type rulings do not name. The new scene uses
the ruled palette. The older mismatch is listed here so that it is known, not fixed by stealth.

## 10. Build order

Each step ends with something that can be looked at or measured. A step starts when the one
build machine is free.

1. **The record of the rulings.** One decision record (ADR317) with section 2.1, section 9
   and the reading of 6.8. The Design Bible edited in place with pointers. Notes on issues 618,
   637, 824, 825 and 831.
2. **Geometry in the library's core.** Outlines, the two placements, spreading. Tested without a
   screen, against small hypergraphs with numbers on their memberships.
3. **The Bevy crate in the library.** Meshes, hatching, moving marks, the plugin, the example.
4. **The sums.** First what the land needs for its height and colour (a household group's hours;
   what came back; money by place). Then the paths for marks, which need the household kept on
   attendance.
5. **On the land, the whole country.** Surface in both forms, particles, three beats, the table
   by place and by workplace, the unhidden label, the frame measurement. *First look with real
   numbers.*
6. **The old lenses on the new ground.** One at a time. When all five are there and measured, the
   map of separate blocks is retired with its tests.
7. **By their ties.** With what exists on the day: workplaces, companies, public accounts,
   organizations. Nations, landlords and banks join as the economy build makes them.
8. **In the wells.** When the share exists for the country's groups. Until then the arrangement
   states the absence.
9. **The player's view.** Its own design, on the rule in 6.9.

Steps 4 and 5 are built against the records as they are on the day, and follow them through
each change of the economy build. Kinds of payment are read as data, never as a fixed list, so
rent and interest appear when they exist.

Steps 2 and 3 do not need the game. Step 4 touches the same identity change as issue 653 and
stage 4b and is planned with them.

## 11. How we will know it works

- **Hours add up.** For every period shown: hours attended equal hours worked plus idle hours;
  hours worked at workplaces plus work done outside them equal the period's direct work; and
  hours given, held and released satisfy the period's own law. A test fails the build otherwise.
- **No rate.** A check over the scene's code and the sums' code finds no place where an amount of
  money and an amount of hours meet in one expression.
- **Nothing dropped in silence.** For each stream, marks drawn plus the printed remainder equal
  the stream's total.
- **The same picture twice.** The same records give the same positions, outlines and marks, bit
  for bit, on two runs.
- **Frame time.** With the whole country on screen, measured by the client's own sampler in
  300-frame windows on the reference machine: the slowest window's 95th percentile is no worse
  than today's money map (15.4 ms at 1366x768, 18.4 ms at 1920x1080), with the beats playing.
  The trial of plain marks against a shader for marks is judged by this figure.
- **Played, not only tested.** The scripted play check drives the real client over its control
  socket through three periods and keeps the frames.
- **Reduced motion.** With it on, no frame differs from the one before except at a beat.
- **In the library.** The example runs. The core's tests pass with and without each feature and
  on the lowest Rust version each crate names.

**The world sums to zero.** In every period the heights of all places, at home and abroad, sum to
zero to the hour, and the sum over the United States is printed with its sign. A test holds both.

## 12. Left to the builder

- How the surface is meshed (one mesh, or one per state), as long as outlines never move in plan
  and both forms share one set of county shapes.
- Whether marks are plain batched meshes or one mesh moved by a clock in a shader, by the trial
  in 11.
- The shape of the new tables, views and readers, within the rules of section 7.
- The exact families of movements that count as "reached a household", within "each hour once".
- Easing curves and durations, within the Design Bible's floors (200 ms to answer, 600 ms or more
  for a change that carries meaning).
- The names of crates, modules and types.
- How labels avoid one another.

## 13. Settled with the Director on 2026-11-21

Asked by dialog, answered the same evening.

1. **Which hours are "work given":** hours that went into goods and services, with idle hours
   shown apart (ruling 17, section 6.2).
2. **Unknown hours and the height:** show it and say so (ruling 18, section 6.3).
3. **National liberation in the wells:** four corners, as a reading (ruling 19, section 6.8).
4. **What the height is measured against:** the whole world (ruling 21, section 6.3).
5. **The whole country still comes first** (ruling 20).

One correction to a figure I gave. I said "about 3,000" household groups when asking about the
whole country. The country has 15,696 today (five kinds of household in every county), and more
after the economy build. The design holds 25,000. Ruling 8 stands unless the Director says
otherwise.

My calls. The Director kept them all (the first one is now ruling 21, against the world).

- The height is a mass of hours measured against a share (6.3). Ruled: the world's share.
- At the size of the whole country the place is the body (6.6).
- Parties with no place stand on a rail at the map's edge (6.3).
- A body of participants is drawn as a particle of its own kind until household groups join
  organizations (6.1).
- Only real hyperedges get a membrane; groupings read from pairwise ties get a plain outline. A
  membership of zero is outside, and the outline holds nine tenths of the set's people (6.7).
- The wells show absence until the share exists for the country, and carrying it there is
  separate work (6.8).
- Amendment AF is read, not amended (9).
- The old map of separate blocks is retired once every lens is on the new ground (10).
- The grouping "by world view" (6.5).

Known and not settled here: two captures of the country disagree on the number of workplaces
(7,463 in November's reports, 60,634 in October's). The design uses November's.
