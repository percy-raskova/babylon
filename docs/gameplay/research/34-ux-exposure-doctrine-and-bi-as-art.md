# 34 — Two-tier exposure: the honest BI surface and the unnumbered one

Design research, 2026-10-26. Question: **the game has two kinds of truth — public statistics a
literate outsider could read in the *Financial Times*, and engine magnitudes (Heat, legitimacy
gradient, control, QRF calculus, fog-masked quantities) that must never print as numbers. What
does the design canon actually prescribe for showing one exactly and the other only as rate,
acceleration, or pure visual qualia — and what makes the exact surface beautiful as an object
rather than merely correct?**

Read for this briefing: Tufte, *The Visual Display of Quantitative Information* (VDQI, second
edition), *Envisioning Information* (EI), *Visual Explanations* (ViE); Norman, *The Design of
Everyday Things* (revised and expanded, 2013); Krug, *Don't Make Me Think, Revisited*; Shneiderman,
"Direct Manipulation: A Step Beyond Programming Languages" (1983); Salen and Zimmerman, *Rules of
Play*; Sylvester, *Designing Games*; Debord and Becker-Ho, *A Game of War*; Lidwell, Holden and
Butler, *Universal Principles of Design* (epub, parsed).

Every claim carries a class. **O** = stated in the cited source. **D** = my mapping to Babylon,
which no source endorses. Page numbers for VDQI come from the printed page headers of a scanned
facsimile, so they are read, not OCR'd; *Rules of Play* was extracted from a CHM-derived PDF that
carries no printed folios, so it is cited by chapter.

---

## 0. Thesis

1. The game already has two epistemologies — the visibility rule in `2026-10-25-porch-01.md`
   separates the material layer from the political layer — and the interface needs a notation for
   each, because one notation for both is how a simulation becomes a spreadsheet.
2. **Tier 1 is Tufte's surface.** Money, headcount, hours, votes, casualties: exact numbers, tables,
   small multiples, Lie Factor 1.0, no chartjunk. It must survive being screenshotted into a
   newspaper.
3. **Tier 2 is never a number, and never a unit.** Heat, legitimacy gradient, control, QRF pressure:
   only derivatives (rate, then acceleration) and pure qualia (pulse, glow, density, jitter). A
   printed magnitude is a formula the player will play, and the spell breaks.
4. **No Tier 2 channel may be invertible.** Every cue must be lossy, quantized, hysteretic, and
   cross-coupled so that no screenshot can be solved back into a scalar. Fog hides the world; it
   never hides the outcome of the player's own act.
5. **Allocation is a physical act.** Scarce hours are a fixed 672-hour pot you drag, not a field you
   type; the engine's invariants appear as walls you hit, not warnings you dismiss.

---

## 1. Where this briefing sits in the live doctrine

It does not create a parallel rule set. It supplies the missing *rendering* rules for six
statements already in force.

| In force | Where | What it leaves open |
| --- | --- | --- |
| Two-layer read model: material layer is public record, political layer is fogged; unknown renders as honest unknown | `2026-10-25-porch-01.md` §"Fog and the leak problem" | how a fogged quantity is *shown* without becoming a number |
| "Concrete countable world-events may show; engine-computed abstractions stay buried" | same file, §"The visibility rule" | which pixels carry the buried quantity, if any |
| Fog that lies: unorganized terrain is masked, not uncertain; stage never stored or displayed | `2026-10-26-combat-design.md` C3, C4 | how the mask looks different from the veil and from absence |
| Locked instruments visible-but-veiled *with a path*, never hidden | porch-01, "The Veil of Money" | how a veiled control differs from an absent one at the pixel level |
| The player writes the plan inside an engine-enforced structure | `2026-10-26-combat-design.md` §4 "Transition" | the input grammar for the plan |
| Every game display answers a decision question; an administrative display cannot pass a milestone | `AGENTS.md` §Constitutional compact | — (this briefing treats it as a veto) |

Briefing 33 covers the *instrument*: what the engine records and how the player learns it. This
briefing covers the *display*: what reaches the eye once the record exists. They meet at one point,
the honest unknown, and neither may soften it.

---

## 2. The tier boundary, and the third state

### 2.1 The test

A quantity is Tier 1 if a participant in the fiction could read it off a wire service, a party
balance sheet, a police blotter, or a newspaper of the period. The repo's existing working test —
*would Mao have put it in the treatise?* — is the same test with the same edge. Money seized is a
fact; a "cohesion modifier" is the author's desk drawer.

Add the mechanical form of the test, because it decides cases the fiction test leaves ambiguous:

> **The FT test.** If the number appeared in a newspaper, would a reader be able to check it against
> another source? If yes, Tier 1. If its only possible source is the engine's private arithmetic,
> Tier 2.

> **The unit test.** If the interface would ever need to write a unit after it — points, per cent,
> multiplier, index — it is Tier 1 or it is a lie. **No Tier 2 quantity may acquire a unit.** This
> is checkable in review: a Tier 2 label with a `%` or a `×` beside it is a defect.

### 2.2 Three states, three renderings

The doctrine most often fails at the boundary between "I am not allowed to know" and "nobody knows".
They are different facts and must not share a pixel.

| State | Meaning | Rendering | Never |
| --- | --- | --- | --- |
| **Exact** | public statistic, Tier 1 | number, table, small multiple, dated | blurred, rounded to a lie, animated |
| **Qualitative** | engine magnitude the player may feel, Tier 2 | derivative shape, pulse, glow, density, jitter; ordinal at most | a number, a unit, a legend that names the scale |
| **Unknown** | outside organizing reach, or not yet learned | honest unknown: a hole with a name, the price of finding out, and the date it was last true | zero, stale value, greyed-out number, "?" alone |

The third state is the one that already has a rule (porch-01: "Unknowns render as honest unknown —
never zero, never stale") and the one most easily broken by a well-meaning dashboard, because a
table with a blank cell looks like a bug while a table with a zero looks finished.

### 2.3 Why Tier 2 must be lossy

Two sources converge on this and neither is about fog.

Tufte's first rule for data displays is that they "avoid distorting what the data have to say"
(VDQI p.13), and his Lie Factor measures the distortion (VDQI p.57). A Tier 2 cue that can be
inverted — scrub the pulse curve until it reads 43 — is a display with a Lie Factor near 1.0 that
was never meant to be measured. Salen and Zimmerman supply the mechanism: they treat the game as an
information channel and describe "noise" as interference that "affects the amount of information in
a message" (*Rules of Play*, ch.16, "Games as Information Theory Systems", §"Noise in the Channel").
A noiseless Tier 2 channel carries full information and therefore defeats its own purpose.

> **T2-1 (lossy).** Every Tier 2 cue is deliberately low-bandwidth: at most five ordinally distinct
> levels, no axis, no tick marks, no hover value.
>
> **T2-2 (cross-coupled).** No cue encodes one latent variable alone. Pulse rate answers Heat *and*
> local organization density; glow answers legitimacy gradient *and* the age of the last receipt.
> The player learns to read the combination; nobody can solve the system from a screenshot.
>
> **T2-3 (hysteretic).** Cue state changes lag the underlying value and do not oscillate at a
> boundary. A cue that flickers between two states at a threshold hands the player the threshold.

The failure T2-1 through T2-3 prevent has a name in this repository already: **"the player will play
the formula"** (porch-01, §"The visibility rule"). Tufte's name for the general disease is
chartjunk's opposite number — not too much ink, but ink that *claims* precision it does not have
(VDQI pp.56–57, the Lie Factor).

### 2.4 The derivative ladder

Tier 2 cues answer at the first and second derivative, never at the level. The corpus supports the
first rung directly: ViE's opening sentence makes rate part of the definition of understanding
("by what means, **at what rate**", p.9), and Norman's ambient-signal criteria require a cue to
orient — "a rough idea of its speed, and whether it is moving toward or away" (p.160). The second
rung is my extension, and it is where the doctrine earns its keep.

| Rung | What the cue carries | How it renders | What it prevents |
| --- | --- | --- | --- |
| **Level** | the engine's value now | *nothing — forbidden* | the spreadsheet |
| **Rate** | direction and rough speed | the shape of a short trace: slope of a sparkline, the period of a pulse, the direction of a drift | a player who cannot tell whether the base is cooling or heating |
| **Acceleration** | whether the rate itself is changing | a change in *rhythm* rather than in amplitude: the pulse spacing stretches, the jitter coarsens, the breath shortens | the turn, which is the only thing worth knowing |

The acceleration rung is the one that matters politically. A base that is cooling slowly and a base
that is cooling and *slowing* are different situations — the second is a floor, the first is a
collapse — and neither is a number. Tufte's "at what rate" gets you the first; the second is the
question a player actually asks before deciding whether to spend the period's hours.

Two guards. **The integration guard**: a rate cue must not be visually integrable by eye — no
cumulative fill that grows as the trace is watched, because a player who can add up the trace has
reconstructed the level. **The unit guard** applies again: acceleration has no unit here, so it may
never be labeled ("rising faster" is a sentence; "+0.3/period²" is a leak).

---

## 3. Per-book: principle, rule per tier, failure prevented

Each entry gives the principle as the book states it, then the two rules it implies, then the
failure it prevents in the book's own vocabulary.

### 3.1 Tufte, *The Visual Display of Quantitative Information*

**Principle (O).** "Excellence in statistical graphics consists of complex ideas communicated with
clarity, precision, and efficiency." The list that follows is the whole Tier 1 charter: show the
data; induce the viewer to think about the substance rather than the methodology; avoid distorting
what the data have to say; present many numbers in a small space; make large data sets coherent;
encourage the eye to compare; reveal the data at several levels of detail; serve a clear purpose;
and stay integrated with the verbal description (VDQI p.13).

**Tier 1 rule.** Every Tier 1 panel is a *table or a comparison*, not a dashboard tile. Three
specific obligations:
- **Lie Factor 1.0.** Tufte defines it as the size of the effect shown divided by the size of the
  effect in the data, calls anything outside 0.95–1.05 "substantial distortion", and notes that in
  practice almost all distortion is overstatement (p.57). The rule for us is arithmetic: any bar,
  area, or radius scaling must be linear in the underlying quantity; no 3-D perspective on a
  two-variable comparison; no truncated baseline. His example of the disappearing baseline and the
  "pseudo-decline" created by comparing six months to a full year (p.54) is exactly what a
  period-over-period money chart does by accident when the current period is incomplete.
- **Data-ink.** "Data-ink is the non-erasable core of a graphic, the non-redundant ink arranged in
  response to variation in the numbers represented" (p.91). Tufte's erasure sequence — erase the
  box, then the axis except ticks, then part of the data measures themselves into a white grid
  (pp.126–127) — is the review method: take the panel, delete one element at a time, stop when
  information is lost.
- **Data density over decoration.** "Present many numbers in a small space" (p.13) is not a
  preference; it is the reason a *Financial Times* page beats a corporate dashboard.

**Tier 2 rule.** Tufte's *multifunctioning graphical elements* chapter is the licence and the limit
for Tier 2 glyphs. He shows Chernoff faces doing exactly what our county glyphs must do: encode
several measures in one small element, keep the ordinary X-Y reading, and then "turn to the
within-scatter detail, seeking clusters of similar observations... Outlying faces and those
inconsistent with others in their neighborhood — they are, of course, *strangers* — should be
identified" (p.142). Our version: one glyph per county or per organization, carrying at most four
Tier 2 dimensions in its own geometry (fill density, edge pulse rate, halo radius, jitter), with
outliers visible at rest and without a hover. Tufte's own closing line on the faces is the warning
label: with such encoding "we would appear to have reached the limit of graphical economy of
presentation, imagination, and, let it be admitted, eccentricity" (p.142). Four dimensions, not
nine.

**Failure prevented.** *Chartjunk* — "vibrating" hatching and moiré (pp.109–110), the fake
perspective that "clutters many graphics... now at high fashion in the world of Boutique Data
Graphics" and "abounds in corporate annual reports" (p.118); and the *duck*, the graphic "taken over
by decorative forms" where "the overall design purveys Graphical Style rather than quantitative
information" (p.116). The corporate annual report is the precise negative image of the surface we
want: it is decorative, evasive, and the numbers are subordinate.

### 3.2 Tufte, *Envisioning Information*

**Principle (O).** "Clutter and confusion are failures of design, not attributes of information."
Stripping detail out "is a style based on personal preference and fashion, considerations utterly
indifferent to substantive content" (EI ch.2, p.51). The remedy he names is not deletion but
stratification: "layering and separation, visually stratifying various aspects of the data"
(same page; ch.3 is devoted to it).

**Tier 1 rule.** Do not simplify the economy to make the screen calm. The material layer is
genuinely dense — thirty commodities, hundreds of counties, dozens of firms — and density is the
honest answer. Separate by layer, not by omission: background (geography), midground (structure),
foreground (the number under discussion), with secondary elements muted so the figure-ground
hierarchy does the work (the mechanism is stated in ViE p.74, quoted below).

**Tier 2 rule.** Stratify the cue layer *out of* the number layer. This is the single most important
mechanical consequence of the whole briefing:

> **T1/T2-1 (channel separation).** A Tier 2 cue may never borrow a channel that a Tier 1 number
> uses for a Tier 1 meaning. If money is encoded as bar height, Heat may not be bar colour. If
> county area encodes population, county tint may not encode control — area and tint carry
> population and, at most, unknown-state.

Tufte's "1 + 1 = 3 or more" is the reason. Two marks generate a third visual activity — "a bright
white path between the lines" — and "most of the time, that surplus visual activity is
non-information, noise, and clutter" (EI ch.3, p.61). Superimpose a cue on a statistic and you have
manufactured a third, unintended reading that neither field owns.

**Tier 1 rule (second).** *Small multiples* for every time series with a peer set: "At the heart of
quantitative reasoning is a single question: Compared to what?" (EI ch.4, p.67). The Ticker's
numbers are meaningless without their own history beside them and their peers beside that, on
shared scales, no re-learning per panel.

**Failure prevented.** *1 + 1 = 3* (surplus noise from superimposed marks); *clutter by
decoration*; and its twin, the over-simplified display that hides real complexity and thereby
misleads — which Tufte treats as a failure of the same family, since both fault the wrong party.

### 3.3 Tufte, *Visual Explanations*

**Principle (O).** "Assessments of change, dynamics, and cause and effect are at the heart of
thinking and explanation. To understand is to know what cause provokes what effect, by what means,
**at what rate**" (ViE Introduction, p.9). ViE is the book about mechanism — arrows, sequences,
before-and-after — and the rate clause is the theoretical basis for Tier 2's derivative encoding:
the engine's magnitudes are exactly "by what means, at what rate".

**Principle (O), the constraint that governs every Tier 2 cue.** *The smallest effective
difference*: "Make all visual distinctions as subtle as possible, but still clear and effective."
Tufte calls it "the Occam's razor... of information design" and adds that "small differences allow
more differences" (ViE ch.4, p.73). Then the caveat that decides our calibration: Ad Reinhardt's
paintings work at the threshold of perception, "this is fine for art but not for data. Rather than
operating at such an exquisite threshold of perceptual acuity... displays must be clear, assured,
reliable, sturdy" (same page).

**Tier 1 rule.** Use the smallest effective difference downward: muting grids, rules, frames,
labels, and fills until the data is the only assertive thing on the page (ViE pp.73–74 lists
exactly the secondary elements — "arrows, pointer lines, dimension lines, tic marks, scales...
grids, meshes, rules, underlines, frames, boxes, compartments, codes, legends, highlights, accents").
The justification is a hierarchy argument: "when everything (background, structure, content) is
emphasized, nothing is emphasized" (p.74).

**Tier 2 rule.** Tier 2 lives in the band Tufte reserves for art, and only there. Two consequences:
- **T2-4 (floor).** A cue must be perceptible at normal viewing distance *without* the player
  hunting, because Sylvester's rule applies (a game "is no more than what it communicates", §3.7).
  Tufte sets the ceiling; playtest sets the floor.
- **T2-5 (no measurement claim).** A cue must never sit where a number sits. If a value is
  positioned on a scale with ticks, the eye will read a value. Tier 2 cues therefore live in
  qualities — pulse, luminance, density, jitter, halo, breath — and never in position or length,
  which are the two channels the eye measures automatically.

That last point is a genuinely derived constraint rather than a borrowed one, and it is the
cleanest way to separate the tiers without a legend: **Tier 1 may use position and length; Tier 2
may not.**

**Failure prevented.** *Explaining-magic* failure — ViE ch.3 is titled "Explaining Magic: Pictorial
Instructions and Disinformation Design", and its subject is how an illusion is constructed and then
explained. A Tier 2 cue that can be decoded is disinformation design running in the wrong
direction: the game becomes the magician working against its own audience. Also prevented: the
*sub-threshold* failure, a cue so subtle it carries nothing, which Tufte explicitly says is fine
for Reinhardt and not for us.

### 3.4 Norman, *The Design of Everyday Things*

**Principle (O).** Every action runs through two gulfs. "The Gulf of Execution, where they try to
figure out how to use it, and the Gulf of Evaluation, where they try to figure out what state it is
in and whether their actions got them to their goal." The gulf "is small when the device provides
information about its state in a form that is easy to get, is easy to interpret, and matches the way
the person thinks about the system" (p.39). The design elements that close it: "Feedback and a good
conceptual model" (p.39).

This is the load-bearing sentence for the entire Tier 2 doctrine, and it is worth stating plainly
because it is counter-intuitive: **Norman does not ask for numbers.** He asks for state information
in a form that matches the user's model. A player's model of legitimacy is not "0.42"; it is "the
base is cooling" or "the room is turning". Tier 2 cues satisfy Norman's requirement *better* than
numbers would, provided they are interpretable and consistent.

**Principle (O).** The seven questions any design must let the user answer: what do I want to
accomplish; what are the alternative action sequences; what action can I do now; how do I do it;
what happened; what does it mean; is this okay (p.71). "The information that helps answer questions
of execution (doing) is feedforward. The information that aids in understanding what has happened
is feedback" (p.72).

**Tier 1 rule.** Tier 1 answers questions 5 and 7 — what happened, is this okay — with numbers, dated
and sourced. Every Tier 1 number carries its period and its provenance, because an undated statistic
cannot answer "what happened".

**Tier 2 rule.** Tier 2 answers questions 6 and 7 — what does it mean, is this okay — where a number
would be a false answer. The exact rule:

> **T2-6 (evaluation without measurement).** For every Tier 2 quantity, the screen must let the
> player say which way it is moving and how fast, and must not let them say what it is. Shape
> answers "what does it mean"; a value would answer a question the fiction forbids.

**Principle (O), and the doctrine for sealed controls.** Constraints and forcing functions:
"Forcing functions are the extreme case of strong constraints that can prevent inappropriate
behavior", and Norman names three — interlocks ("force operations to take place in proper
sequence"), lock-ins, and lockouts (p.142).

**Rule for absent, veiled and disabled.** The repo has two rules that look contradictory: locked
instruments are "visible-but-veiled *with a path*" (porch-01) and unavailable violence "is not greyed
out — it is absent" (combat design §6). Norman resolves the conflict by asking *whose constraint it
is*:

| Constraint | Render as | Because |
| --- | --- | --- |
| The world refuses (population will not, terrain will not hold) | **absent**, with the reason discoverable elsewhere (the county's own page, the Wiki) | there is no action to signpost; a greyed button promises an action that does not exist |
| The player has not learned it (Veil of Money, Tier 0→2) | **veiled**, present, inert, with its price and its path | this is a knowledge constraint, and Norman's signifier is what makes a possibility discoverable at all |
| The engine does not know (unorganized, unreceptive) | **unknown**, a hole with a name | it is neither refusal nor ignorance of the player |
| Temporarily impossible this period (hours already committed) | **blocked**, with the interlock visible | this is a lock-in; the player must see *what* holds it |

The failure this prevents is the Gulf of Execution in its quiet form: a possibility the player never
learns exists is the same as a possibility that does not exist, and a greyed control with no reason
is worse than either because it teaches helplessness.

**Principle (O), ambient signals.** Norman's treatment of electric-vehicle sounds gives the criteria
for a persistent cue layer: it must **alert**, **orient** ("a rough idea of its speed, and whether it
is moving toward or away"), and **not annoy** — he contrasts this with sirens, "deliberately
unpleasant" but tolerable because "they are infrequent and for relatively short duration" (p.160).

**Tier 2 rule.** Every ambient Tier 2 cue is scored against those three criteria, in that order:
does it draw the eye when it matters (alert), does it say which way and how fast (orient), and can
it run for two hundred periods without becoming noise (not annoy). A cue that fails the third is
chartjunk with a job.

**Failure prevented.** *Gulf of Evaluation* (a state the player cannot read); *Gulf of Execution*
(an action the player cannot find); and *knowledge in the head*, Norman's term for what a display
forces the player to memorise because it will not show it (ch.3, p.95 and throughout).

### 3.5 Krug, *Don't Make Me Think, Revisited*

**Principle (O).** "When I look at a Web page it should be self-evident. Obvious. Self-explanatory"
(p.11). And the fallback: "If you can't make something self-evident, you at least need to make it
self-explanatory" (p.18). His six levers for a screen read at speed: take advantage of conventions;
create effective visual hierarchies; break pages into clearly defined areas; make it obvious what is
clickable; eliminate distractions; format content to support scanning (p.29). His acid test is the
*trunk test*: squint at the screen from arm's length and find, in seconds, where you are, what this
is, what the sections are, and where you can go (pp.82–83).

**The reconciliation this doctrine needs.** Krug's law and Babylon's visibility rule appear to
collide. The game must never explain *why* (porch-01: "the game never explains *why* mechanistically
... Causes are for the player to infer, argue about, and post"), while Krug demands no thinking.

They govern different objects:

> **Navigation is self-evident; interpretation is earned.** A player must never spend thought
> working out where they are, what a panel is, whether a thing is clickable, or what a printed
> number counts. A player must always spend thought working out what a sequence of events meant.

Krug's failure is *incidental* cognitive load — load spent on the interface rather than the
problem. Babylon's rule forbids removing *intrinsic* load — the work of interpretation, which is
the game. A screen that explains why legitimacy fell is not user-friendly; it is a spoiler with a
tooltip.

**Tier 1 rule.** Tier 1 panels pass the trunk test at arm's length: title, period, unit, source,
comparison, all findable by squinting. Tables carry their own headers; no number appears without a
unit and a date.

**Tier 2 rule.** Tier 2 cues must be *self-explanatory* (Krug's fallback, p.18), not self-evident.
The player is allowed one unit of thought to "get" a cue the first time, and the cue must then be
consistent forever. This is also why a Tier 2 cue needs a home in the Wiki — a reference page that
shows the cue beside its meaning, once, and never again on the play surface.

**Failure prevented.** Krug's own: the *trunk test* failure (a screen you cannot orient in), and
"happy talk" and "instructions must die" (pp.48–49) — explanatory prose on a working surface, which
in our case is the spoiler.

### 3.6 Shneiderman, "Direct Manipulation" (1983)

**Principle (O).** Direct manipulation has four properties: "Continuous representation of the object
of interest"; "Physical actions (movement and selection by mouse, joystick, touch screen, etc.) or
labeled button presses instead of complex syntax"; "Rapid, incremental, reversible operations whose
impact on the object of interest is immediately visible"; "Layered or spiral approach to learning
that permits usage with minimal knowledge" (PDF p.8; the scan carries no journal folios, so this is
cited to the PDF page).

Shneiderman also supplies the honest counter-argument, which any allocation spec must answer:
graphic representations "may take excessive screen display space. For experienced users, a tabular
textual display of 50 document names is far more appealing than only 10 document graphic icons";
and "using spatial or graphic representations of the problem does not necessarily improve
performance... The wrong information, or a cluttered presentation, can lead to greater confusion"
(PDF p.8).

**Tier 1 rule.** Do not iconify statistics. Where the task is comparing many named quantities —
thirty commodities, twelve firms, forty counties — a table beats a graphic, and Shneiderman says so
explicitly. Direct manipulation belongs on the *decision* surfaces, not on the reading surfaces.

**Tier 2 rule.** The "continuous representation" property is what makes Tier 2 legible without
numbers: a world that is continuously represented (a living map, a breathing graph) can carry
graded state that a table of numbers cannot. It also sets a limit: the representation must be the
*object of interest*, not a metaphor for it. Shneiderman warns that "mixing metaphors from two
sources adds complexity", and that the metaphor's emotional tone must be fitting (PDF p.8). A
heat-map of the county is the object; a thermometer icon of the county is a metaphor that will
acquire a scale.

**Failure prevented.** *Complex syntax* — the typed command where a gesture would do; and its
inverse, the decorative graphic that costs screen space and delivers less than the table it
replaced.

### 3.7 Salen and Zimmerman, *Rules of Play*

**Principle (O).** *Meaningful play*: "the relationships between actions and outcomes in a game are
both discernible and integrated into the larger context of the game." Their gloss: "Discernability
means that a player can perceive the immediate outcome of an action. Integration means that the
outcome of an action is woven into the game system as a whole" (ch.3).

**The rule this forces on the fog.** Fog may hide the world; it may not hide the player's own act.

> **T2-7 (discernibility floor).** Every committed action returns a discernible, immediate receipt:
> what was spent, what was risked, what is now unknown. The *magnitude* of a Tier 2 consequence may
> be unreadable; its *occurrence* may not.

This is consistent with combat design's receipt discipline ("Known prices debited visibly on the
spot. Unknowns marked unknown") and it is what keeps fog from becoming a slot machine.

**Principle (O).** *The magic circle*: following Huizinga, the game occupies "a 'temporary world
within the ordinary world, dedicated to the performance of an act apart'", and "it is within the
magic circle that the authority of the rules hold sway" (ch.9). And *systems of meaning*: "games are
systems of meaning"; "the meaning of any one sign can only be understood in relation to a larger set
of signs, which together form the densely woven fabric of meaning in a game" — their worked example
is the fighting-game health bar, a sign that means nothing alone (ch.25).

**Tier 1 rule.** The screen is inside the circle: it is the ritual surface, not an instrument panel
bolted onto a model. The magic circle is why the BI surface can be beautiful without being
corporate — it is framed as an artifact *of the world*, printed in the world's typography, dated in
the world's calendar.

**Tier 2 rule.** A cue is a sign in a system of signs; it means nothing on its first appearance and
everything by the twentieth. Therefore:
- cues are introduced one at a time, each with one Wiki page and one in-world introduction;
- the cue grammar is fixed for the campaign (no per-scenario relearning);
- a cue never changes meaning when a system is rebalanced.

**Principle (O).** *Perfect and imperfect information* is a designed axis, not a defect: "In games of
imperfect information, some of the information may be hidden from players during the game", and
their cited examples include "Stratego, **Kriegspiel**" (ch.15, quoting J. Mark Thompson).

**Principle (O).** *Transformative play*: "a special case of play that occurs when the free movement
of play alters the more rigid structure in which it takes shape" (ch.22).

**Failure prevented.** *Opacity without discernibility* — the state where the player cannot tell
whether their action did anything, which RoP treats as a failure of design rather than a difficulty
setting; and *sign drift*, where a cue's meaning moves under the player.

### 3.8 Sylvester, *Designing Games*

**Principle (O).** "Events only have emotional value if players perceive and understand them. That
which is never communicated might as well never have occurred at all" (ch.9 "Interface", p.219).
And: "If we succeed at these challenges, the interface vanishes... But if we fail, the game is
buried behind its interface... a game is no more than what it communicates" (p.220).

This is the strongest statement in the corpus against the temptation to leave Tier 2 unrendered. A
massacre the player cannot feel is not a mechanic; it is a column in a database. The Tier 2 layer is
not decoration on top of the simulation — it is the only channel through which most of the
simulation reaches a human at all.

**Principle (O).** *Elegance*: "Good design means maximizing the emotional power and variety of play
experiences while minimizing players' comprehension burden and developer effort. This form of
efficiency is called elegance" (ch.2, p.49). Note what the second cost is: **player attention**.
Sylvester lists the price of every mechanic — design effort, machine resources, friction with the
fiction, and "player attention" — before he names elegance as getting the most experience for the
least of it. *Decisions* are the unit of interactivity: "To
understand interactivity well enough to craft it, we need to examine the individual units of
interactivity. Those units are decisions" (ch.5, p.119).

**Tier 1 rule.** Every Tier 1 panel must terminate in a decision, or it is the administrative
display `AGENTS.md` already vetoes. Elegance is the test: the panel earns its pixels by changing
what the player will do next period.

**Tier 2 rule.** Tier 2 is where elegance actually lives, because it compresses a large state space
into a small perceptual surface. The design obligation: a cue that has never influenced a decision in
playtest is either miscalibrated (too subtle, T2-4) or unnecessary. Sylvester's test — does the
player act differently because of it — is the acceptance criterion for every cue.

**Failure prevented.** Sylvester's own: the game "buried behind its interface" (a Tier 2 layer so
elaborate it must be studied), and its opposite, the *uncommunicated event* — a consequence with
emotional weight that never reaches the player.

### 3.9 Debord and Becker-Ho, *A Game of War*

**Principle (O).** Debord's Kriegspiel publishes its arithmetic completely. The "Table of Forces in
Play, with their Characteristics" (p.12) lists every unit, its offensive and defensive factors, its
range and mobility — infantry 4/6, rising to 8 in a pass and 10 in a fort (p.14); artillery 5/8,
to 10 and 12 (p.15). The initial deployment, however, "must be conceived in ignorance of the
adversary's arrangements, so one or both players should plan out the precise disposition of their
forces on paper in advance" (p.13).

That is a two-tier exposure doctrine in 1977, and its axis is instructive: **the rules and the
factors are public; the situation is hidden.** Our axis is different — public statistics versus
engine internals — but the structural lesson transfers exactly: *publish the coefficients, hide the
position*. A player who knows the cost of an hour and cannot see the state of the county is playing
a game; a player who cannot see either is reading a manual.

**Principle (O), and the charge that authorises Tier 2.** Debord names what his own game omits, in
a section titled "Some Under-Represented or Absent Factors": weather and the alternation of day and
night; "the morale and degree of fatigue of troops"; and "uncertainty with regard to enemy positions
and movements". He is explicit that the omission is a loss: "this game falls far short of being a
complete representation of real warfare in that it leaves no room for doubt about the enemy's
positions and movements... From the moment hostilities open, exact and certain knowledge of all
enemy movements is vouchsafed instantly" (p.25).

Babylon's Tier 2 exists to answer that critique. Heat, legitimacy gradient, control and QRF
pressure are morale-and-fatigue-and-uncertainty, and the reason they cannot be numbers is the reason
Debord could not put them on a flat chequered board: a number would restore the certainty he is
lamenting.

**Principle (O).** The game's subject is contradiction: it "tends to demand the simultaneous
consideration of contradictory requirements" (p.21); "the number of obviously ill-advised
dispositions of forces and manœuvres is very great; yet even among moves that may be considered well
chosen, none... is assured of success" (p.23); "Though the basic principles are certain, their
application is always a matter of doubt" (p.24). And the claim of the artwork: "we may say that this
game accurately portrays all the factors at work in real war, and, more generally, the dialectics of
all conflict" (p.26).

**Tier 1 rule.** Publish the certain principles: factors, costs, ranges, the wage, the rent, the
price of bread. Tier 1 is the rulebook's table — exact, complete, unhedged.

**Tier 2 rule.** Render the doubt. Tier 2 is where "the application is always a matter of doubt"
becomes pixels: not a score that resolves the contradiction, but a surface that displays both sides
of it at once. A single composite index of "revolutionary situation" is the anti-pattern; a screen
where the base is cooling while the state's attention is rising is the design.

**Failure prevented.** *False certainty* — Debord's own diagnosis of his game — and its commercial
form, the single score that answers a question the world does not answer.

### 3.10 Lidwell, Holden and Butler, *Universal Principles of Design*

The epub parses cleanly. Entries are cited by title, since the conversion drops folios.

**Principle (O).** *Signal-to-Noise Ratio*: "The ratio of relevant to irrelevant information in a
display. The highest possible signal-to-noise ratio is desirable in design." Increase signal by
simplicity and by "redundant coding and highlighting"; minimise noise "by removing unnecessary
elements, and minimizing the expression of elements" (entry, §Guidelines). The entry names Tufte's
VDQI as a seminal source.

**Principle (O).** *Aesthetic-Usability Effect*: "Aesthetic designs are perceived as easier to use
than less-aesthetic designs", and they "have a higher probability of being used, whether or not they
actually are easier to use" (entry).

**Tier 1 rule.** The aesthetic-usability effect is not permission to decorate; it is the reason the
Tier 1 surface must be *both* beautiful and honest. A beautiful dashboard is believed. A beautiful
dashboard with a Lie Factor of 1.4 is a more effective lie than an ugly one, which is why Tufte's
integrity rules are not optional polish here — they are the counterweight to the effect.

**Tier 2 rule.** *Progressive Disclosure*: "separating information into multiple layers and only
presenting layers that are necessary or relevant", which "keeps displays clean and uncluttered and
helps people manage complexity" (entry). This is the mechanism of the Veil of Money at the level of
*pixels*: the layer exists, is present, and discloses on the player's advance rather than on a
tutorial's schedule.

**Tier 1/Tier 2 rule.** *Layering* is the structural form of the stratification in §3.2: "Layering
involves organizing information into related groupings and then presenting or making available only
certain groupings at any one time... primarily used to manage complexity, but can also be used to
reinforce relationships in information" (entry). Two-dimensional layering is the plate and the
overlay; three-dimensional layering is depth, and depth is what makes a cue layer readable *as* a
layer rather than as a value.

**Failure prevented.** Low signal-to-noise (the general case of chartjunk); and the *aesthetic
shield*, the design that is forgiven its faults because it is handsome.

---

## 4. Direct manipulation for Allocate and the loadout

The plan is not a form. Combat design already says the transition is authored "through constrained
allocation — pointing, clicking, scales, a planning mini-game with anchors" (§4), and porch-01
already allows "a slider or typed number when allocating people or money" (§"The decision moment is
ceremony"). This section replaces "slider or typed number" with a spec, because a slider is a number
with a handle and a typed number is the exact failure the visibility rule names.

### 4.1 The object: the hour pot

The engine already has the right object, and it is better than anything we would invent. From
`research/23`, `HouseholdTimeReceipt::validate` enforces, per household per period:

```
endowment_hours = 672
attended_hours + protected_hours + unpaid_allocated_hours + contribution_available_hours = 672
protected_unresolved_hours != 0  ⇒  unpaid_allocated = 0 ∧ contribution_available = 0
```

> **DM-1.** The allocation surface is a fixed-length strip of 672 hours, divided into four segments
> in the engine's priority order, with draggable boundaries. The player never types an hour; they
> move a boundary. The strip cannot exceed its own length, because it is a length.

The invariant becomes a physical fact rather than a validation message. The `⇒` in the receipt is
the reason the pot is the perfect direct-manipulation object: it is conservative, integer, and has a
cliff.

### 4.2 Six rules, each from a named principle

| Rule | Spec | Source |
| --- | --- | --- |
| **DM-2 continuous representation** | the strip is continuous on screen; the handle moves in sub-hour increments with a visible snap to integer hours on release | Shneiderman, PDF p.8, property 1 |
| **DM-3 physical action** | drag, not syntax: no field, no spinner, no "apply"; keyboard arrows nudge one hour, which is the same operation, not a second syntax | Shneiderman, property 2 |
| **DM-4 feedforward** | while the handle is held, the consequences show *before* release: the derived exposure `E`, the households pushed to the cliff, the downstream segment that goes to zero | Norman p.72 (feedforward); p.39 (Gulf of Evaluation) |
| **DM-5 reversibility until seal** | every drag is undoable; the seal commits the period and the plan becomes history | Shneiderman, property 3 |
| **DM-6 the cliff is a wall** | at the invariant the handle *stops*; it does not warn, flash, or ask for confirmation. The blocked state shows what holds it | Norman p.142, interlocks; combat design §6 |
| **DM-7 layered learning** | period 1 shows two segments and one boundary; later periods reveal the remaining segments and the derived exposure; the formula never appears | Shneiderman, property 4; UPD *Progressive Disclosure* |

### 4.3 The loadout

Combat design's early stage is squad-scale, with cadre as "personified slots — representations of
aggregates, classes, organizations — never simulation individuals" (§4). Direct manipulation fits
because the pool is small and the constraints are geometric.

- **DM-8 (tokens carry capacity, not numbers).** Cadre are tokens whose *area* is their labour
  capacity; a drop target accepts a token only if it fits. Over-allocation is impossible by physics,
  not by validation. No token displays a number until the loss receipt mints its name (combat design
  §7).
- **DM-9 (three refusals, never one).** A drop target that refuses must say which refusal it is:
  *absent* (the world will not — the action does not exist here), *veiled* (not learned — with its
  price), *unknown* (fog — with the price of finding out). See §3.4's table. A single greyed slot
  for all three destroys the game's central distinction between "cannot", "have not learned", and
  "do not know".
- **DM-10 (the receipt is the receipt).** On seal, the plan prints: hours committed per claim, what
  was risked, what remains unknown, the period, the seal. This is both the record and the shareable
  artifact (porch-01, "The answer comes in three layers").

### 4.4 One honest doubt

Shneiderman's own counter-argument applies to the hour pot: a continuous strip costs screen space,
and if the player's real task is comparing forty households across four claims, a table is better.
The specification above assumes the pot is used at the *collective or cadre* scale, where there are
one to five pots on screen. If it is ever needed for hundreds of households, the correct answer is
the table plus the `HouseholdTimeReceipt` numbers, and the pot is the detail view for the one
household selected. Do not scale the drag surface by scaling the number of strips on screen.

---

## 5. What makes the exact surface beautiful *as an object*

The direction "the artwork is the metric" is older than the software tradition, and the corpus is
unusually direct about it.

**5.1 Beauty is the revelation of complexity, not its reduction.** Tufte's epilogue opens "Design is
choice", doubts that principles should be applied "rigidly or in a peevish spirit", and states the
goal: "What is to be sought in designs for the display *of information* is the clear portrayal of
complexity. Not the complication of the simple; rather the task of the designer is to give visual
access to the subtle and the difficult — that is, **the revelation of the complex**" (VDQI p.191).
And the sentence that sets the standard for a game about political economy: "Graphical elegance is
often found in simplicity of design and complexity of data... Beautiful graphics do not traffic with
the trivial" (p.177).

Babylon's subject is not trivial. The material for gravity is already in the data: rent, wages,
hours, casualties, the price of bread. The design does not need to supply seriousness; it needs to
stop diluting it.

**5.2 A page, not a tray.** "Data graphics are paragraphs about data and should be treated as
such" (VDQI p.181). Tufte's objection is to segregation: "Imagine if graphics were replaced by
paragraphs of words and those paragraphs scattered over the pages out of sequence with the rest of
the text — that is how graphical and tabular information is now treated in the layout of many
published pages" (p.181). The consequence for us is compositional: the period-close artifact is a
*spread* with an argument — a sentence, the number that supports it, the comparison that qualifies
it, the receipt that dates it — not a grid of tiles each shouting at equal volume. His caution also
applies: words around graphics "are highly effective — sometimes all too effective — in telling
viewers how to allocate their attention"; words should say *how* to read, "and not *what* to read in
terms of content" (p.182). That is precisely the line between a legend and a spoiler.

**5.3 The shareable artifact is a confection.** ViE's seventh chapter is about *visual confections*:
"uniquely concocted mixtures of images" that "illustrate an argument, present and enforce visual
comparisons, combine the real and the imagined" (pp.121–126). This is the form for the reckoning
page and the chronicle spread: real evidence, juxtaposed, arranged to argue. The confection is where
"artwork as metric" stops being a slogan — the beauty is in the *arrangement of true things*, which
is also Tufte's definition of insight: "When principles of design replicate principles of thought,
the act of arranging information becomes an act of insight" (ViE p.9).

**5.4 The precedent, and its warning.** Debord's board is an aesthetic object whose beauty is
compression: fifteen units, five moves a turn, one map, and "the dialectics of all conflict" (p.26).
It is beautiful because nothing on it is decoration — every mark is a rule. The warning is VDQI
p.118's "Boutique Data Graphics": the corporate annual report is also a designed object, and it is
the exact failure mode — perspective, decoration, and evasion, with the numbers subordinate. The
difference between the two is not taste. It is whether every mark carries information.

**5.5 The one-sentence criterion.** A Tier 1 surface is beautiful as an object when a stranger could
frame it, and a player could act on it, and neither would be misled.

---

## 6. Anti-patterns

| Anti-pattern | What it looks like | Why it fails | Name and source |
| --- | --- | --- | --- |
| Spreadsheet popup | visible formula, multiplier, "+2.25×" on an option | the player plays the formula; the fiction dies | porch-01, §"The visibility rule" |
| Chartjunk | 3-D bars, gradient fills, drop shadows, animated counters on statistics | ink that does not vary with data | VDQI pp.107–110 |
| The duck | a panel whose ornament *is* the design | "the overall design purveys Graphical Style rather than quantitative information" | VDQI p.116 |
| Lie Factor ≠ 1 | truncated baseline, area-scaled radius, six months against twelve | overstatement; the reader is misled by arithmetic | VDQI pp.54, 57 |
| Boutique Data Graphics | the corporate annual-report look | decoration over data, in the register of authority | VDQI p.118 |
| 1 + 1 = 3 | a Tier 2 tint on a Tier 1 bar | surplus visual activity is "non-information, noise, and clutter" | EI p.61 |
| Invertible cue | a pulse you can scrub to a value; a hover that names the heat | turns fog into a lookup table | RoP ch.16 (noise); T2-1 |
| Invented unit | "Heat 43", "Legitimacy 0.61", "% control" | a Tier 2 quantity acquired a unit | this briefing, §2.1 |
| Single composite score | one index for "revolutionary situation" | resolves the contradiction the game is about | Debord p.21; combat design §8 |
| Uncommunicated event | a Tier 2 consequence with no receipt | "might as well never have occurred" | Sylvester p.219 |
| Opacity without discernibility | the player cannot tell whether the act did anything | fails meaningful play | RoP ch.3 |
| Greyed control with no reason | a dead button, no explanation | teaches helplessness; hides which refusal it is | Norman p.39; DM-9 |
| Trunk-test failure | unlabelled panel; no period; no unit | incidental load spent on the interface | Krug pp.29, 82–83 |
| Spoiler prose | "legitimacy fell because you…" | removes intrinsic load; violates the visibility rule | Krug pp.48–49 + porch-01 |
| Admin display | a panel that changes no decision | does not pass a game milestone | `AGENTS.md` |
| Dark-pattern reveal | the interface knows and withholds for effect | disinformation design aimed at the player | ViE ch.3 |
| Dashboard as a tray of tiles | equal visual weight, no argument | a page is a paragraph | VDQI p.181 |

---

## 7. Evidence table

**O** = stated in the source. **D** = my inference or game mapping; no source endorses it.

| # | Claim | Class | Source (file, chapter/page) | Game consequence |
| --- | --- | --- | --- | --- |
| 1 | Graphical excellence = complex ideas with clarity, precision, efficiency; nine obligations including "avoid distorting" and "encourage comparison" | O | VDQI ch.1, p.13 | Tier 1 charter |
| 2 | Lie Factor = effect shown ÷ effect in data; outside 0.95–1.05 is substantial distortion; distortion is nearly always overstatement | O | VDQI ch.2, p.57 | linear scales; no truncated baselines |
| 3 | Six months against a full year fabricates a "pseudo-decline" | O | VDQI ch.2, p.54 | incomplete periods must not be charted against complete ones |
| 4 | Data-ink = non-erasable, non-redundant ink responding to the numbers | O | VDQI ch.4, p.91 | erasure test for every panel |
| 5 | Erase box, then axis except ticks, then part of the measures into a white grid | O | VDQI ch.6, pp.126–127 | review method |
| 6 | Vibrating/moiré chartjunk is common even in major journals | O | VDQI ch.5, pp.109–110 | ban pattern fills on data |
| 7 | The duck: design taken over by decoration; data become design elements | O | VDQI ch.5, p.116 | veto ornament that is the panel |
| 8 | Fake perspective and "Boutique Data Graphics" abound in corporate annual reports | O | VDQI ch.5, p.118 | the negative reference for the BI surface |
| 9 | Multifunctioning elements encode several measures per mark; outliers ("strangers") must be identifiable | O | VDQI ch.7, p.142 | county glyph, ≤4 dimensions |
| 10 | Such elaborate encoding reaches "the limit of graphical economy... and, let it be admitted, eccentricity" | O | VDQI ch.7, p.142 | cap the glyph; no faces |
| 11 | "Graphical elegance is often found in simplicity of design and complexity of data"; "Beautiful graphics do not traffic with the trivial" | O | VDQI ch.9, p.177 | beauty criterion for Tier 1 |
| 12 | Seven guides for attractive statistical displays, incl. balance/proportion/scale, narrative quality, no content-free decoration | O | VDQI ch.9, p.177 | design checklist |
| 13 | "Data graphics are paragraphs about data and should be treated as such"; segregation is the historical error | O | VDQI ch.9, p.181 | page composition, not tile trays |
| 14 | Words around graphics should say *how* to read, not *what* to read | O | VDQI ch.9, p.182 | legend yes, spoiler no |
| 15 | "Design is choice"; principles applied rigidly become "a peevish spirit"; goal is "the revelation of the complex" | O | VDQI Epilogue, p.191 | thesis for BI-as-art |
| 16 | Clutter and confusion are failures of design, not attributes of information; stripping detail is fashion | O | EI ch.2, p.51 | do not simplify the economy |
| 17 | Remedy is layering and separation, stratifying aspects of the data | O | EI ch.2–3, pp.51–53 | tier stratification |
| 18 | 1 + 1 = 3: two marks create a third visual activity, usually noise and clutter | O | EI ch.3, p.61 | no Tier 2 cue on a Tier 1 channel |
| 19 | Small multiples answer "Compared to what?" for a wide range of problems | O | EI ch.4, p.67 | every series with history and peers |
| 20 | Data density is information per unit area; low density is a design failure | O | EI ch.1, p.13 | dense Tier 1 pages are correct |
| 21 | "To understand is to know what cause provokes what effect, by what means, at what rate" | O | ViE Introduction, p.9 | derivative encoding is explanatory, not decorative |
| 22 | Arranging information can be an act of insight | O | ViE Introduction, p.9 | the composed page |
| 23 | Smallest effective difference: as subtle as possible but still clear; Occam's razor of information design; small differences allow more differences | O | ViE ch.4, p.73 | ceiling for cue subtlety |
| 24 | Reinhardt's sub-threshold distinctions are "fine for art but not for data"; displays must be "clear, assured, reliable, sturdy" | O | ViE ch.4, p.73 | floor for cue amplitude (playtest) |
| 25 | Muting secondary elements produces a visual hierarchy; when everything is emphasized, nothing is | O | ViE ch.4, p.74 | the Tier 1 default |
| 26 | Visual confections juxtapose images to illustrate an argument and enforce comparisons | O | ViE ch.7, pp.121–126 | the reckoning page as artifact |
| 27 | Chapter on "Explaining Magic: Pictorial Instructions and Disinformation Design" | O | ViE ch.3, p.55 | withholding must be systemic, not performed |
| 28 | Gulf of Execution / Gulf of Evaluation; the gulf is small when state is shown "in a form that is easy to get, is easy to interpret, and matches the way the person thinks about the system" | O | Norman ch.2, p.39 | licence for qualitative state |
| 29 | Feedback and a good conceptual model bridge the gulf of evaluation | O | Norman ch.2, p.39 | receipts plus model |
| 30 | Seven questions any design must answer; feedforward serves execution, feedback serves evaluation | O | Norman ch.2, pp.71–72 | per-screen checklist |
| 31 | Forcing functions are the extreme case of strong constraints; interlocks, lock-ins, lockouts | O | Norman ch.4, p.142 | the hour pot's wall; period lock-in |
| 32 | Ambient signals must alert, orient, and not annoy; sirens are tolerable only because infrequent | O | Norman ch.4, p.160 | three criteria for ambient cues |
| 33 | Affordance vs signifier: affordances define possible actions, signifiers make them discoverable | O | Norman ch.1, pp.9–14 | veiled controls need signifiers |
| 34 | Self-evident is the goal; self-explanatory is the fallback | O | Krug ch.1, pp.11, 18 | two standards, two objects |
| 35 | Six levers, incl. conventions, visual hierarchy, defined areas, obvious clickability, no distractions | O | Krug ch.3, p.29 | Tier 1 layout |
| 36 | Trunk test: squint and find site ID, page name, sections, local nav, "you are here", search | O | Krug ch.6, pp.82–83 | arm's-length test |
| 37 | "Omit needless words"; "instructions must die" | O | Krug ch.5, pp.48–49 | no explanatory prose on working surfaces |
| 38 | Direct manipulation: continuous representation; physical actions; rapid incremental reversible operations with immediately visible impact; layered learning | O | Shneiderman 1983, PDF p.8 | the allocation spec |
| 39 | Graphic representations may waste space; a 50-name table can beat 10 icons; wrong or cluttered graphics increase confusion | O | Shneiderman 1983, PDF p.8 | tables for Tier 1 comparisons |
| 40 | Mixing metaphors adds complexity; the metaphor's tone must fit | O | Shneiderman 1983, PDF p.8 | glyph is the object, not a thermometer icon |
| 41 | Meaningful play requires discernible **and** integrated action-outcome relations; discernible = the player can perceive the immediate outcome | O | RoP ch.3 | fog may not hide the player's own act |
| 42 | The magic circle: a temporary world within the ordinary world where the rules hold sway | O | RoP ch.9 | the screen as ritual artifact |
| 43 | Games are systems of meaning; a sign's meaning depends on the whole set of signs (health-bar example) | O | RoP ch.25 | cue grammar taught once, fixed forever |
| 44 | Perfect and imperfect information is a designed axis; Kriegspiel is named as imperfect-information | O | RoP ch.15 | fog is a genre feature |
| 45 | Noise in the channel reduces the information carried | O | RoP ch.16 | cues must be lossy by design |
| 46 | Transformative play: free movement of play alters the structure it takes shape in | O | RoP ch.22 | player-authored plans change the system |
| 47 | Events have emotional value only if perceived and understood; the uncommunicated might as well not have occurred; a game is no more than what it communicates | O | Sylvester ch.9, pp.219–220 | Tier 2 must be rendered |
| 48 | If the interface succeeds it vanishes; if it fails the game is buried behind it | O | Sylvester ch.9, p.220 | incidental load is the enemy |
| 49 | Elegance = maximising emotional power and variety of play while minimising players' comprehension burden and developer effort | O | Sylvester ch.2, p.49 | dense data, minimal means |
| 50 | Decisions are the unit of interactivity | O | Sylvester ch.5, p.119 | allocation is the canonical decision unit |
| 51 | The Table of Forces publishes every factor, range and mobility | O | Debord, *A Game of War*, p.12 | publish the coefficients |
| 52 | Initial deployment is planned in ignorance of the adversary's arrangements | O | Debord, p.13 | hide the position |
| 53 | Strategy concerns movement against communications more than attrition | O | Debord, p.19 | interdiction economics, not body counts |
| 54 | Fewer than a third of the force may move in one turn (five of fifteen), standing for friction | O | Debord, p.21 | scarce action budget as the aesthetic act |
| 55 | The game demands "simultaneous consideration of contradictory requirements" | O | Debord, p.21 | no composite score |
| 56 | None of the well-chosen moves is assured of success; "the basic principles are certain, their application is always a matter of doubt" | O | Debord, pp.23–24 | Tier 1 principles, Tier 2 doubt |
| 57 | Three absent factors: weather/day-night; morale and fatigue; uncertainty about enemy positions and movements | O | Debord, p.25 | the charge that authorises Tier 2 |
| 58 | "No room for doubt about the enemy's positions" is named as the game's chief shortfall | O | Debord, p.25 | the state's knowledge must not be perfect |
| 59 | The game "accurately portrays all the factors at work in real war, and, more generally, the dialectics of all conflict" | O | Debord, p.26 | the artwork-as-metric claim |
| 60 | Signal-to-noise: maximise relevant, minimise irrelevant; redundant coding and highlighting raise signal | O | UPD, *Signal-to-Noise Ratio* | Tier 1 review test |
| 61 | Aesthetic-usability effect: aesthetic designs are perceived as easier to use and are more readily used | O | UPD, *Aesthetic-Usability Effect* | beauty is functional; also a hazard |
| 62 | Progressive disclosure separates information into layers, presenting only what is necessary | O | UPD, *Progressive Disclosure* | the Veil's pixel mechanism |
| 63 | Ockham's razor and layering reduce complexity without deleting content | O | UPD, *Ockham's Razor*, *Layering* | stratify, do not delete |
| 64 | Material layer public, political layer fogged; unknown is honest unknown | O (repo) | porch-01, §"Fog and the leak problem" | the three-state display |
| 65 | Unavailable violence is absent, not greyed out | O (repo) | combat design §6 | refusal taxonomy |
| 66 | Locked instruments are visible-but-veiled with a path | O (repo) | porch-01, *The Veil of Money* | refusal taxonomy |
| 67 | The game never explains why mechanistically | O (repo) | porch-01, §"The visibility rule" | navigation self-evident, interpretation earned |
| 68 | 672-hour endowment with a protected-hours cliff | O (repo) | research/23, §2.2 | the hour pot's object |
| 69 | Every game display answers a decision question; admin displays fail a milestone | O (repo) | `AGENTS.md` §Constitutional compact | veto on telemetry panels |
| 70 | Tier 1 may use position and length; Tier 2 may not | D | from #18, #23, #25 | channel separation rule |
| 71 | Cross-couple Tier 2 cues so inversion is underdetermined | D | from #9, #45 | T2-2 |
| 72 | Hysteresis on cue state changes | D | inference from player optimisation | T2-3 |
| 73 | No Tier 2 quantity may acquire a unit | D | from #67 plus the FT test | reviewable defect |
| 74 | Absent / veiled / unknown / blocked as four distinct renderings | D | from #28, #31, #64, #65, #66 | refusal taxonomy |
| 75 | The period-close page is a composed argument, not a tile grid | D | from #13, #15, #26 | shareable artifact |
| 76 | Hour pot at collective scale; table plus detail at household scale | D | from #39 | scope limit on drag surfaces |
| 77 | Cue at first derivative (rate), then second (acceleration), never level | D | from #21, #32 | the derivative ladder |
| 78 | Acceleration renders as rhythm change, not amplitude change | D | from #77 | the turn is visible without a value |
| 79 | No cumulative or integrable visual on a rate cue | D | from #45, #77 | blocks by-eye reconstruction of the level |

---

## 8. Open questions for the Director

1. **Does the Ticker show derivatives of Tier 2 quantities?** A price series is Tier 1. "The market
   is nervous" is Tier 2. Is a *direction* arrow on a Tier 1 number a legal way to carry a Tier 2
   signal, or does it smuggle a unit back in? My reading of `T2-5` says the arrow is legal only if
   the underlying quantity is Tier 2 and the arrow has no scale.
2. **Where does the endgame screen sit?** Combat design grants the narrator the full view once
   (§3 C2, §8). Is the reckoning therefore allowed to print Heat as a number in the retrospective?
   Tufte's integrity rules argue yes (it is now a historical statistic, checkable in the record);
   the visibility rule argues no (the fiction never had that number). Recorded, not resolved.
3. **Cue amplitude is an empirical question.** `T2-4` and ViE p.73 pull in opposite directions and
   only playtest settles it. Every cue needs a named acceptance test before it ships.
4. **Does the whistle-blower screen exist?** If Tier 2 cues are the only channel for the political
   layer, then a player who cannot read cues is locked out of the game. That is an accessibility
   problem, and the honest answer (a text mode with ordinals: "the base is cooling") may be the
   right one, at the cost of a slightly flatter experience.

---

## 9. Sources and reading log

**Read with page-level extraction.**

- Tufte, *The Visual Display of Quantitative Information*, 2nd ed. Scanned facsimile; the text layer
  is empty, so pages were rendered and read as images. Pages cited from printed folios: 13, 53, 54,
  57, 91, 109–110, 116, 118, 126–127, 142, 177, 181–182, 191. Chapter titles and the contents page
  (ch.1 p.13, ch.2 p.53, ch.4 p.91, ch.5 p.107, ch.6 p.123, ch.7 p.139, ch.8 p.161, ch.9 p.177,
  epilogue p.191) were read directly.
- Tufte, *Envisioning Information*. Text layer present. Pages cited: 13, 37, 51, 53, 61, 67.
- Tufte, *Visual Explanations*. Text layer present. Pages cited: 9, 55 (chapter title), 73–74,
  121–126.
- Norman, *The Design of Everyday Things*, revised and expanded ed. Pages cited from printed footers:
  9–14, 39, 71–72, 95, 142, 160.
- Krug, *Don't Make Me Think, Revisited*, 3rd ed. Pages cited from printed bracketed folios: 11, 18,
  29, 48–49, 82–83.
- Shneiderman, "Direct Manipulation: A Step Beyond Programming Languages", *IEEE Computer* 16(8),
  1983. The scan carries no journal folios; cited to PDF pages 5, 7, 8 of 13.
- Salen and Zimmerman, *Rules of Play*. CHM-derived PDF without printed folios; cited by chapter
  (3, 9, 15, 16, 22, 25). Chapter numbers taken from the book's contents listing in the same file.
- Sylvester, *Designing Games*. Pages cited: 49, 119, 219–220.
- Debord and Becker-Ho, *A Game of War*, Atlas Press 2007 (trans. Nicholson-Smith). Pages cited:
  12–13, 19, 21, 23–26.
- Lidwell, Holden and Butler, *Universal Principles of Design*. Epub parsed with pandoc; the
  conversion drops folios, so entries are cited by title (*Signal-to-Noise Ratio*,
  *Aesthetic-Usability Effect*, *Progressive Disclosure*, *Ockham's Razor*, *Layering*).

**Read only as search excerpts, not relied on.** Krug's chapters on animal/vegetable/mineral
classification and usability testing; Sylvester's chapters on multiplayer, the market, and balance;
*Rules of Play* ch.11–21 and ch.26–30; VDQI ch.3 and ch.8.

**Repo documents read.** `docs/gameplay/2026-10-25-porch-01.md` (visibility rule, five screens,
Veil of Money, the three-layer answer, fog and the leak problem); `docs/gameplay/2026-10-26-combat-design.md`
(§3 constraints, §4 stages and transition, §6 violence menu, §7 invoices, §8 long memory);
`docs/gameplay/00-overview.md` (session index); `docs/gameplay/research/23-...` (§2.2 the 672-hour
receipt and its cliff); `docs/gameplay/research/33-...` (the instrument side of the same boundary).

**Limits of this briefing.** No playtest exists, so every amplitude and threshold here is a
hypothesis. The page numbers for the scanned Tufte volume are read from the images by eye; a printed
edition should be checked before this is cited outside the repository. The tier assignment of
individual engine fields (which of Heat, legitimacy, control, QRF pressure is Tier 2 in *every*
context) is not settled here and belongs to the screen specs, not to this briefing.
